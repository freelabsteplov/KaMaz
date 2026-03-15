#include "BlueprintGraphAutomationService.h"

#include "BlueprintActionAutomationService.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Components/ActorComponent.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraph/EdGraphSchema.h"
#include "EdGraphSchema_K2.h"
#include "Engine/Blueprint.h"
#include "Engine/MemberReference.h"
#include "JsonObjectConverter.h"
#include "K2Node_CustomEvent.h"
#include "K2Node_CallFunction.h"
#include "K2Node_DynamicCast.h"
#include "K2Node_Event.h"
#include "K2Node_Variable.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Logging/LogMacros.h"
#include "Policies/PrettyJsonPrintPolicy.h"
#include "ScopedTransaction.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UObject/Field.h"
#include "UObject/UnrealType.h"

DEFINE_LOG_CATEGORY_STATIC(LogBlueprintGraphAutomationEditor, Log, All);

namespace BlueprintGraphAutomationServicePrivate
{
	thread_local FBlueprintGraphTransactionScope* GActiveScope = nullptr;

	static FString ResultCodeToString(const EBlueprintAutomationResultCode Code)
	{
		switch (Code)
		{
		case EBlueprintAutomationResultCode::Success:
			return TEXT("Success");
		case EBlueprintAutomationResultCode::InvalidArgument:
			return TEXT("InvalidArgument");
		case EBlueprintAutomationResultCode::NotFound:
			return TEXT("NotFound");
		case EBlueprintAutomationResultCode::AlreadyExists:
			return TEXT("AlreadyExists");
		case EBlueprintAutomationResultCode::Unsupported:
			return TEXT("Unsupported");
		case EBlueprintAutomationResultCode::Failed:
		default:
			return TEXT("Failed");
		}
	}

	static void LogResult(const FBlueprintGraphAutomationResult& Result)
	{
		const FString Prefix = FString::Printf(TEXT("[%s] "), *ResultCodeToString(Result.Code));
		if (Result.IsSuccess())
		{
			UE_LOG(LogBlueprintGraphAutomationEditor, Display, TEXT("%s%s"), *Prefix, *Result.Message);
		}
		else
		{
			UE_LOG(LogBlueprintGraphAutomationEditor, Error, TEXT("%s%s"), *Prefix, *Result.Message);
		}
	}

	template <typename NodeType>
	static NodeType* CreateNodeInGraph(UEdGraph* Graph, const FVector2D& NodePosition)
	{
		FGraphNodeCreator<NodeType> NodeCreator(*Graph);
		NodeType* Node = NodeCreator.CreateNode(false);
		Node->SetNodePosX(NodePosition.X);
		Node->SetNodePosY(NodePosition.Y);
		NodeCreator.Finalize();
		return Node;
	}

	static TSharedPtr<FJsonObject> BuildPinJson(UEdGraphPin* Pin, const bool bIncludeLinkedPins)
	{
		TSharedPtr<FJsonObject> PinObject = MakeShared<FJsonObject>();
		PinObject->SetStringField(TEXT("name"), Pin ? Pin->PinName.ToString() : FString());
		PinObject->SetNumberField(TEXT("direction"), Pin ? static_cast<int32>(Pin->Direction) : -1);

		if (Pin)
		{
			PinObject->SetStringField(TEXT("category"), Pin->PinType.PinCategory.ToString());
			PinObject->SetStringField(TEXT("subcategory"), Pin->PinType.PinSubCategory.ToString());
			PinObject->SetStringField(TEXT("default_value"), Pin->DefaultValue);
			PinObject->SetStringField(TEXT("default_object"), Pin->DefaultObject ? Pin->DefaultObject->GetPathName() : FString());
			PinObject->SetStringField(TEXT("default_text"), Pin->DefaultTextValue.IsEmpty() ? FString() : Pin->DefaultTextValue.ToString());

			if (Pin->PinType.PinSubCategoryObject.IsValid())
			{
				PinObject->SetStringField(TEXT("subcategory_object"), Pin->PinType.PinSubCategoryObject->GetPathName());
			}

			if (bIncludeLinkedPins)
			{
				TArray<TSharedPtr<FJsonValue>> LinkedPins;
				for (UEdGraphPin* LinkedPin : Pin->LinkedTo)
				{
					if (!LinkedPin)
					{
						continue;
					}

					TSharedPtr<FJsonObject> LinkedPinObject = MakeShared<FJsonObject>();
					LinkedPinObject->SetStringField(TEXT("node_name"), LinkedPin->GetOwningNode() ? LinkedPin->GetOwningNode()->GetName() : FString());
					LinkedPinObject->SetStringField(TEXT("node_path"), LinkedPin->GetOwningNode() ? LinkedPin->GetOwningNode()->GetPathName() : FString());
					LinkedPinObject->SetStringField(TEXT("pin_name"), LinkedPin->PinName.ToString());
					LinkedPins.Add(MakeShared<FJsonValueObject>(LinkedPinObject));
				}

				PinObject->SetArrayField(TEXT("linked_to"), LinkedPins);
			}
		}

		return PinObject;
	}

	static TSharedPtr<FJsonObject> BuildNodeJson(UEdGraphNode* Node, const bool bIncludePins, const bool bIncludeLinkedPins)
	{
		TSharedPtr<FJsonObject> NodeObject = MakeShared<FJsonObject>();
		if (!Node)
		{
			return NodeObject;
		}

		NodeObject->SetStringField(TEXT("name"), Node->GetName());
		NodeObject->SetStringField(TEXT("path"), Node->GetPathName());
		NodeObject->SetStringField(TEXT("class"), Node->GetClass()->GetPathName());
		NodeObject->SetStringField(TEXT("title"), Node->GetNodeTitle(ENodeTitleType::ListView).ToString());
		NodeObject->SetStringField(TEXT("guid"), Node->NodeGuid.ToString(EGuidFormats::DigitsWithHyphensLower));
		NodeObject->SetNumberField(TEXT("pos_x"), Node->NodePosX);
		NodeObject->SetNumberField(TEXT("pos_y"), Node->NodePosY);
		NodeObject->SetStringField(TEXT("comment"), Node->NodeComment);

		if (bIncludePins)
		{
			TArray<TSharedPtr<FJsonValue>> PinArray;
			for (UEdGraphPin* Pin : Node->Pins)
			{
				PinArray.Add(MakeShared<FJsonValueObject>(BuildPinJson(Pin, bIncludeLinkedPins)));
			}
			NodeObject->SetArrayField(TEXT("pins"), PinArray);
		}

		return NodeObject;
	}

	static FString SerializeJsonObject(const TSharedPtr<FJsonObject>& JsonObject)
	{
		FString Output;
		const TSharedRef<TJsonWriter<TCHAR, TPrettyJsonPrintPolicy<TCHAR>>> Writer =
			TJsonWriterFactory<TCHAR, TPrettyJsonPrintPolicy<TCHAR>>::Create(&Output);
		FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);
		return Output;
	}

	static FString SerializeGraphJson(UEdGraph* Graph, const bool bIncludePins, const bool bIncludeLinkedPins)
	{
		TSharedPtr<FJsonObject> GraphObject = MakeShared<FJsonObject>();
		if (!Graph)
		{
			return SerializeJsonObject(GraphObject);
		}

		GraphObject->SetStringField(TEXT("name"), Graph->GetName());
		GraphObject->SetStringField(TEXT("path"), Graph->GetPathName());
		GraphObject->SetStringField(TEXT("class"), Graph->GetClass()->GetPathName());
		GraphObject->SetStringField(TEXT("schema"), Graph->GetSchema() ? Graph->GetSchema()->GetClass()->GetPathName() : FString());

		TArray<TSharedPtr<FJsonValue>> Nodes;
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			if (!Node)
			{
				continue;
			}
			Nodes.Add(MakeShared<FJsonValueObject>(BuildNodeJson(Node, bIncludePins, bIncludeLinkedPins)));
		}
		GraphObject->SetArrayField(TEXT("nodes"), Nodes);

		return SerializeJsonObject(GraphObject);
	}

	static bool ParseBatchNodeKind(const FString& InValue, EBlueprintGraphBatchNodeKind& OutKind)
	{
		if (InValue == TEXT("custom_event"))
		{
			OutKind = EBlueprintGraphBatchNodeKind::CustomEvent;
			return true;
		}
		if (InValue == TEXT("custom_event_signature"))
		{
			OutKind = EBlueprintGraphBatchNodeKind::CustomEventFromSignature;
			return true;
		}
		if (InValue == TEXT("event_signature"))
		{
			OutKind = EBlueprintGraphBatchNodeKind::EventBySignature;
			return true;
		}
		if (InValue == TEXT("action") || InValue == TEXT("action_signature"))
		{
			OutKind = EBlueprintGraphBatchNodeKind::ActionBySignature;
			return true;
		}
		if (InValue == TEXT("call_function"))
		{
			OutKind = EBlueprintGraphBatchNodeKind::CallFunction;
			return true;
		}
		if (InValue == TEXT("dynamic_cast"))
		{
			OutKind = EBlueprintGraphBatchNodeKind::DynamicCast;
			return true;
		}
		if (InValue == TEXT("variable_get"))
		{
			OutKind = EBlueprintGraphBatchNodeKind::VariableGet;
			return true;
		}
		if (InValue == TEXT("variable_set"))
		{
			OutKind = EBlueprintGraphBatchNodeKind::VariableSet;
			return true;
		}

		return false;
	}

	static bool ParsePrimitiveType(const FString& InValue, EBlueprintPrimitiveVariableType& OutType)
	{
		if (InValue == TEXT("float"))
		{
			OutType = EBlueprintPrimitiveVariableType::Float;
			return true;
		}
		if (InValue == TEXT("bool"))
		{
			OutType = EBlueprintPrimitiveVariableType::Bool;
			return true;
		}
		if (InValue == TEXT("int") || InValue == TEXT("int32"))
		{
			OutType = EBlueprintPrimitiveVariableType::Int32;
			return true;
		}
		if (InValue == TEXT("string") || InValue == TEXT("fstring"))
		{
			OutType = EBlueprintPrimitiveVariableType::String;
			return true;
		}
		if (InValue == TEXT("name") || InValue == TEXT("fname"))
		{
			OutType = EBlueprintPrimitiveVariableType::Name;
			return true;
		}

		return false;
	}

	static FString SanitizeObjectPath(const FString& InPath, const TCHAR* Prefix)
	{
		FString Path = InPath.TrimStartAndEnd();
		const FString PrefixString = FString::Printf(TEXT("%s'"), Prefix);
		if (Path.RemoveFromStart(PrefixString) && Path.EndsWith(TEXT("'")))
		{
			Path.LeftChopInline(1, EAllowShrinking::No);
		}
		else
		{
			Path = FPackageName::ExportTextPathToObjectPath(Path);
		}
		return Path;
	}

	static UEdGraphNode* FindNodeByName(UEdGraph* Graph, const FString& NodeName)
	{
		if (!Graph || NodeName.IsEmpty())
		{
			return nullptr;
		}

		for (UEdGraphNode* Node : Graph->Nodes)
		{
			if (Node && Node->GetName() == NodeName)
			{
				return Node;
			}
		}

		return nullptr;
	}

	static UEdGraphNode* FindNodeByPath(UEdGraph* Graph, const FString& NodePath)
	{
		if (!Graph || NodePath.IsEmpty())
		{
			return nullptr;
		}

		for (UEdGraphNode* Node : Graph->Nodes)
		{
			if (Node && Node->GetPathName() == NodePath)
			{
				return Node;
			}
		}

		return nullptr;
	}

	static UEdGraphNode* ResolveBatchLinkNodeReference(
		const FBlueprintGraphBatchLinkDefinition& LinkDefinition,
		const bool bResolveFromNode,
		const TMap<FString, UEdGraphNode*>& CreatedNodesById,
		UEdGraph* Graph,
		FString& OutResolvedReference)
	{
		const FString& NodeId = bResolveFromNode ? LinkDefinition.FromNodeId : LinkDefinition.ToNodeId;
		const FString& NodeName = bResolveFromNode ? LinkDefinition.FromNodeName : LinkDefinition.ToNodeName;
		const FString& NodePath = bResolveFromNode ? LinkDefinition.FromNodePath : LinkDefinition.ToNodePath;

		if (!NodeId.IsEmpty())
		{
			OutResolvedReference = FString::Printf(TEXT("id '%s'"), *NodeId);
			if (UEdGraphNode* const* ExistingNode = CreatedNodesById.Find(NodeId))
			{
				return *ExistingNode;
			}
		}

		if (!NodePath.IsEmpty())
		{
			OutResolvedReference = FString::Printf(TEXT("path '%s'"), *NodePath);
			if (UEdGraphNode* ExistingNode = FindNodeByPath(Graph, NodePath))
			{
				return ExistingNode;
			}
		}

		if (!NodeName.IsEmpty())
		{
			OutResolvedReference = FString::Printf(TEXT("name '%s'"), *NodeName);
			if (UEdGraphNode* ExistingNode = FindNodeByName(Graph, NodeName))
			{
				return ExistingNode;
			}
		}

		if (OutResolvedReference.IsEmpty())
		{
			OutResolvedReference = TEXT("<empty reference>");
		}

		return nullptr;
	}
}

FBlueprintGraphTransactionScope::FBlueprintGraphTransactionScope(UBlueprint* InBlueprint, UEdGraph* InGraph, const FText& InTransactionText)
	: Transaction(MakeUnique<FScopedTransaction>(InTransactionText))
	, Blueprint(InBlueprint)
	, Graph(InGraph)
	, PreviousScope(BlueprintGraphAutomationServicePrivate::GActiveScope)
{
	if (Blueprint)
	{
		Blueprint->Modify();
		if (UPackage* Package = Blueprint->GetOutermost())
		{
			Package->Modify();
		}
	}

	if (Graph)
	{
		Graph->Modify();
	}

	BlueprintGraphAutomationServicePrivate::GActiveScope = this;
}

FBlueprintGraphTransactionScope::~FBlueprintGraphTransactionScope()
{
	if (bNotifyGraphChanged && Graph)
	{
		Graph->NotifyGraphChanged();
	}

	if (Blueprint)
	{
		if (bStructuralChange)
		{
			FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
		}
		else if (bModified)
		{
			FBlueprintEditorUtils::MarkBlueprintAsModified(Blueprint);
		}

		Blueprint->MarkPackageDirty();
	}

	BlueprintGraphAutomationServicePrivate::GActiveScope = PreviousScope;
}

void FBlueprintGraphTransactionScope::MarkStructuralChange()
{
	bStructuralChange = true;
	bModified = true;
}

void FBlueprintGraphTransactionScope::MarkModified()
{
	bModified = true;
}

void FBlueprintGraphTransactionScope::RequestGraphNotification()
{
	bNotifyGraphChanged = true;
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationResult::Ok(
	const FString& InMessage,
	UBlueprint* InBlueprint,
	UEdGraph* InGraph,
	UEdGraphNode* InNode,
	UEdGraphPin* InPin,
	const FString& InJsonPayload)
{
	FBlueprintGraphAutomationResult Result;
	Result.Code = EBlueprintAutomationResultCode::Success;
	Result.Message = InMessage;
	Result.JsonPayload = InJsonPayload;
	Result.Blueprint = InBlueprint;
	Result.Graph = InGraph;
	Result.Node = InNode;
	Result.Pin = InPin;
	BlueprintGraphAutomationServicePrivate::LogResult(Result);
	return Result;
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationResult::Error(
	const EBlueprintAutomationResultCode InCode,
	const FString& InMessage,
	UBlueprint* InBlueprint,
	UEdGraph* InGraph,
	UEdGraphNode* InNode,
	UEdGraphPin* InPin,
	const FString& InJsonPayload)
{
	FBlueprintGraphAutomationResult Result;
	Result.Code = InCode;
	Result.Message = InMessage;
	Result.JsonPayload = InJsonPayload;
	Result.Blueprint = InBlueprint;
	Result.Graph = InGraph;
	Result.Node = InNode;
	Result.Pin = InPin;
	BlueprintGraphAutomationServicePrivate::LogResult(Result);
	return Result;
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::GetEventGraph(UBlueprint* Blueprint)
{
	if (!Blueprint)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Blueprint is null."));
	}

	UEdGraph* EventGraph = FBlueprintEditorUtils::FindEventGraph(Blueprint);
	if (!EventGraph)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::NotFound,
			FString::Printf(TEXT("Blueprint '%s' does not contain an EventGraph."), *Blueprint->GetPathName()),
			Blueprint);
	}

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Resolved EventGraph '%s' for Blueprint '%s'."), *EventGraph->GetName(), *Blueprint->GetPathName()),
		Blueprint,
		EventGraph);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::GetGraphByName(UBlueprint* Blueprint, const FName GraphName)
{
	if (!Blueprint)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Blueprint must not be null."));
	}

	if (GraphName.IsNone())
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("GraphName must not be None."),
			Blueprint);
	}

	TArray<UEdGraph*> Graphs;
	Blueprint->GetAllGraphs(Graphs);

	for (UEdGraph* Graph : Graphs)
	{
		if (!Graph)
		{
			continue;
		}

		if (Graph->GetFName() == GraphName)
		{
			return FBlueprintGraphAutomationResult::Ok(
				FString::Printf(TEXT("Resolved graph '%s' for Blueprint '%s'."), *GraphName.ToString(), *Blueprint->GetPathName()),
				Blueprint,
				Graph);
		}
	}

	return FBlueprintGraphAutomationResult::Error(
		EBlueprintAutomationResultCode::NotFound,
		FString::Printf(TEXT("Blueprint '%s' does not contain graph '%s'."), *Blueprint->GetPathName(), *GraphName.ToString()),
		Blueprint);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::CreateCallFunctionNode(
	UEdGraph* Graph,
	const UFunction* Function,
	const FVector2D& NodePosition)
{
	if (!Graph)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Graph is null."));
	}

	if (!Function)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Function is null."),
			nullptr,
			Graph);
	}

	UBlueprint* Blueprint = ResolveOwningBlueprint(nullptr, Graph);
	if (!Blueprint)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			FString::Printf(TEXT("Graph '%s' is not owned by a Blueprint."), *Graph->GetPathName()),
			nullptr,
			Graph);
	}

	UK2Node_CallFunction* CallNode = BlueprintGraphAutomationServicePrivate::CreateNodeInGraph<UK2Node_CallFunction>(Graph, NodePosition);
	CallNode->SetFromFunction(Function);
	CallNode->ReconstructNode();

	MarkGraphEdit(Blueprint, Graph, true);

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Created CallFunction node for '%s' in graph '%s'."), *Function->GetPathName(), *Graph->GetPathName()),
		Blueprint,
		Graph,
		CallNode);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::CreateCallFunctionNodeByName(
	UEdGraph* Graph,
	UClass* FunctionOwnerClass,
	const FName FunctionName,
	const FVector2D& NodePosition)
{
	if (!FunctionOwnerClass)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Function owner class is null."),
			nullptr,
			Graph);
	}

	if (FunctionName.IsNone())
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Function name is empty."),
			nullptr,
			Graph);
	}

	const UFunction* Function = FunctionOwnerClass->FindFunctionByName(FunctionName);
	if (!Function)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::NotFound,
			FString::Printf(TEXT("Function '%s' was not found on class '%s'."), *FunctionName.ToString(), *FunctionOwnerClass->GetPathName()),
			nullptr,
			Graph);
	}

	return CreateCallFunctionNode(Graph, Function, NodePosition);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::CreateCustomEventNode(
	UEdGraph* Graph,
	const FString& EventName,
	const FVector2D& NodePosition)
{
	if (!Graph)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Graph is null."));
	}

	UBlueprint* Blueprint = ResolveOwningBlueprint(nullptr, Graph);
	if (!Blueprint)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			FString::Printf(TEXT("Graph '%s' is not owned by a Blueprint."), *Graph->GetPathName()),
			nullptr,
			Graph);
	}

	const FName ResolvedName = EventName.IsEmpty()
		? FBlueprintEditorUtils::FindUniqueCustomEventName(Blueprint)
		: FName(*EventName);

	UK2Node_CustomEvent* CustomEventNode = BlueprintGraphAutomationServicePrivate::CreateNodeInGraph<UK2Node_CustomEvent>(Graph, NodePosition);
	CustomEventNode->CustomFunctionName = ResolvedName;
	CustomEventNode->bOverrideFunction = false;
	CustomEventNode->ReconstructNode();

	MarkGraphEdit(Blueprint, Graph, true);

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Created CustomEvent '%s' in graph '%s'."), *ResolvedName.ToString(), *Graph->GetPathName()),
		Blueprint,
		Graph,
		CustomEventNode);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::CreateCustomEventNodeWithPins(
	UEdGraph* Graph,
	const FString& EventName,
	const TArray<FBlueprintCustomEventPinDefinition>& Pins,
	const FVector2D& NodePosition)
{
	if (!Graph)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Graph is null."));
	}

	UBlueprint* Blueprint = ResolveOwningBlueprint(nullptr, Graph);
	if (!Blueprint)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			FString::Printf(TEXT("Graph '%s' is not owned by a Blueprint."), *Graph->GetPathName()),
			nullptr,
			Graph);
	}

	const FName ResolvedName = EventName.IsEmpty()
		? FBlueprintEditorUtils::FindUniqueCustomEventName(Blueprint)
		: FName(*EventName);

	UK2Node_CustomEvent* CustomEventNode = BlueprintGraphAutomationServicePrivate::CreateNodeInGraph<UK2Node_CustomEvent>(Graph, NodePosition);
	CustomEventNode->CustomFunctionName = ResolvedName;
	CustomEventNode->bOverrideFunction = false;

	const UEdGraphSchema_K2* Schema = GetDefault<UEdGraphSchema_K2>();

	for (const FBlueprintCustomEventPinDefinition& PinDefinition : Pins)
	{
		if (PinDefinition.Name.IsNone())
		{
			return FBlueprintGraphAutomationResult::Error(
				EBlueprintAutomationResultCode::InvalidArgument,
				FString::Printf(TEXT("CustomEvent '%s' received an empty pin name."), *ResolvedName.ToString()),
				Blueprint,
				Graph,
				CustomEventNode);
		}

		const FEdGraphPinType PinType = MakeEventPinType(PinDefinition.Type);
		FText ErrorMessage;
		if (!CustomEventNode->CanCreateUserDefinedPin(PinType, EGPD_Output, ErrorMessage))
		{
			return FBlueprintGraphAutomationResult::Error(
				EBlueprintAutomationResultCode::Unsupported,
				FString::Printf(TEXT("CustomEvent pin '%s' is not supported: %s"), *PinDefinition.Name.ToString(), *ErrorMessage.ToString()),
				Blueprint,
				Graph,
				CustomEventNode);
		}

		UEdGraphPin* NewPin = CustomEventNode->CreateUserDefinedPin(PinDefinition.Name, PinType, EGPD_Output, false);
		if (!NewPin)
		{
			return FBlueprintGraphAutomationResult::Error(
				EBlueprintAutomationResultCode::Failed,
				FString::Printf(TEXT("Failed to create user pin '%s' on CustomEvent '%s'."), *PinDefinition.Name.ToString(), *ResolvedName.ToString()),
				Blueprint,
				Graph,
				CustomEventNode);
		}

		if (!PinDefinition.DefaultValue.IsEmpty())
		{
			Schema->SetPinAutogeneratedDefaultValue(NewPin, PinDefinition.DefaultValue);
		}
	}

	MarkGraphEdit(Blueprint, Graph, true);

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Created CustomEvent '%s' with %d explicit pins in graph '%s'."), *ResolvedName.ToString(), Pins.Num(), *Graph->GetPathName()),
		Blueprint,
		Graph,
		CustomEventNode);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::CreateCustomEventNodeFromSignature(
	UEdGraph* Graph,
	const FString& EventName,
	const UFunction* SignatureFunction,
	const FVector2D& NodePosition)
{
	if (!Graph)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Graph is null."));
	}

	if (!SignatureFunction)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Signature function is null."),
			nullptr,
			Graph);
	}

	UBlueprint* Blueprint = ResolveOwningBlueprint(nullptr, Graph);
	if (!Blueprint)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			FString::Printf(TEXT("Graph '%s' is not owned by a Blueprint."), *Graph->GetPathName()),
			nullptr,
			Graph);
	}

	const FString ResolvedName = EventName.IsEmpty()
		? FString::Printf(TEXT("%s_Event"), *SignatureFunction->GetName())
		: EventName;

	UK2Node_CustomEvent* CustomEventNode =
		UK2Node_CustomEvent::CreateFromFunction(NodePosition, Graph, ResolvedName, SignatureFunction, false);

	if (!CustomEventNode)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::Failed,
			FString::Printf(TEXT("Failed to create CustomEvent from signature '%s'."), *SignatureFunction->GetPathName()),
			Blueprint,
			Graph);
	}

	MarkGraphEdit(Blueprint, Graph, true);

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Created CustomEvent '%s' from signature '%s'."), *ResolvedName, *SignatureFunction->GetPathName()),
		Blueprint,
		Graph,
		CustomEventNode);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::SpawnEventNodeBySignature(
	UEdGraph* Graph,
	const UFunction* SignatureFunction,
	const FVector2D& NodePosition)
{
	if (!Graph)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Graph is null."));
	}

	if (!SignatureFunction)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Signature function is null."),
			nullptr,
			Graph);
	}

	UClass* OwnerClass = Cast<UClass>(SignatureFunction->GetOuter());
	if (!OwnerClass)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			FString::Printf(TEXT("Function '%s' is not owned by a UClass."), *SignatureFunction->GetPathName()),
			nullptr,
			Graph);
	}

	UBlueprint* Blueprint = ResolveOwningBlueprint(nullptr, Graph);
	if (!Blueprint)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			FString::Printf(TEXT("Graph '%s' is not owned by a Blueprint."), *Graph->GetPathName()),
			nullptr,
			Graph);
	}

	UK2Node_Event* EventNode = BlueprintGraphAutomationServicePrivate::CreateNodeInGraph<UK2Node_Event>(Graph, NodePosition);
	EventNode->EventReference.SetExternalMember(SignatureFunction->GetFName(), OwnerClass->GetAuthoritativeClass());
	EventNode->bOverrideFunction = true;
	EventNode->ReconstructNode();

	MarkGraphEdit(Blueprint, Graph, true);

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Spawned Event node for signature '%s' in graph '%s'."), *SignatureFunction->GetPathName(), *Graph->GetPathName()),
		Blueprint,
		Graph,
		EventNode);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::SpawnEventNodeBySignatureName(
	UEdGraph* Graph,
	UClass* FunctionOwnerClass,
	const FName FunctionName,
	const FVector2D& NodePosition)
{
	if (!FunctionOwnerClass)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Function owner class is null."),
			nullptr,
			Graph);
	}

	if (FunctionName.IsNone())
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Function name is empty."),
			nullptr,
			Graph);
	}

	const UFunction* SignatureFunction = FunctionOwnerClass->FindFunctionByName(FunctionName);
	if (!SignatureFunction)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::NotFound,
			FString::Printf(TEXT("Function '%s' was not found on class '%s'."), *FunctionName.ToString(), *FunctionOwnerClass->GetPathName()),
			nullptr,
			Graph);
	}

	return SpawnEventNodeBySignature(Graph, SignatureFunction, NodePosition);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::CreateVariableGetNode(
	UBlueprint* Blueprint,
	UEdGraph* Graph,
	const FName VariableName,
	const FVector2D& NodePosition,
	const bool bIsPure,
	const FString& OwnerClassPath)
{
	if (!Graph)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Graph is null."),
			Blueprint);
	}

	if (VariableName.IsNone())
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Variable name is empty."),
			Blueprint,
			Graph);
	}

	if (!bIsPure)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			TEXT("Impure VariableGet nodes are not supported in v1 because UK2Node_VariableGet::SetPurity is not exported from BlueprintGraph."),
			Blueprint,
			Graph);
	}

	Blueprint = ResolveOwningBlueprint(Blueprint, Graph);
	if (!Blueprint)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			FString::Printf(TEXT("Graph '%s' is not owned by a Blueprint."), *Graph->GetPathName()),
			nullptr,
			Graph);
	}

	UClass* OwnerClass = nullptr;
	bool bOwnerClassIsSelfContext = false;
	FProperty* VariableProperty =
		ResolveVariableProperty(Blueprint, OwnerClassPath, VariableName, true, OwnerClass, bOwnerClassIsSelfContext);
	if (!VariableProperty)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::NotFound,
			OwnerClassPath.IsEmpty()
				? FString::Printf(TEXT("Variable '%s' was not resolved on Blueprint '%s'."), *VariableName.ToString(), *Blueprint->GetPathName())
				: FString::Printf(
					TEXT("Variable '%s' was not resolved on owner class '%s' for Blueprint '%s'."),
					*VariableName.ToString(),
					*OwnerClassPath,
					*Blueprint->GetPathName()),
			Blueprint,
			Graph);
	}

	UK2Node_VariableGet* VariableNode = BlueprintGraphAutomationServicePrivate::CreateNodeInGraph<UK2Node_VariableGet>(Graph, NodePosition);

	const bool bIsFunctionVariable = VariableProperty->GetOwner<UFunction>() != nullptr;

	VariableNode->SetFromProperty(VariableProperty, bOwnerClassIsSelfContext && !bIsFunctionVariable, OwnerClass);
	VariableNode->ReconstructNode();

	MarkGraphEdit(Blueprint, Graph, true);

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Created VariableGet node for '%s' in graph '%s'."), *VariableName.ToString(), *Graph->GetPathName()),
		Blueprint,
		Graph,
		VariableNode);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::CreateVariableSetNode(
	UBlueprint* Blueprint,
	UEdGraph* Graph,
	const FName VariableName,
	const FVector2D& NodePosition,
	const FString& OwnerClassPath)
{
	if (!Graph)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Graph is null."),
			Blueprint);
	}

	if (VariableName.IsNone())
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Variable name is empty."),
			Blueprint,
			Graph);
	}

	Blueprint = ResolveOwningBlueprint(Blueprint, Graph);
	if (!Blueprint)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			FString::Printf(TEXT("Graph '%s' is not owned by a Blueprint."), *Graph->GetPathName()),
			nullptr,
			Graph);
	}

	UClass* OwnerClass = nullptr;
	bool bOwnerClassIsSelfContext = false;
	FProperty* VariableProperty =
		ResolveVariableProperty(Blueprint, OwnerClassPath, VariableName, true, OwnerClass, bOwnerClassIsSelfContext);
	if (!VariableProperty)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::NotFound,
			OwnerClassPath.IsEmpty()
				? FString::Printf(TEXT("Variable '%s' was not resolved on Blueprint '%s'."), *VariableName.ToString(), *Blueprint->GetPathName())
				: FString::Printf(
					TEXT("Variable '%s' was not resolved on owner class '%s' for Blueprint '%s'."),
					*VariableName.ToString(),
					*OwnerClassPath,
					*Blueprint->GetPathName()),
			Blueprint,
			Graph);
	}

	UK2Node_VariableSet* VariableNode = BlueprintGraphAutomationServicePrivate::CreateNodeInGraph<UK2Node_VariableSet>(Graph, NodePosition);

	const bool bIsFunctionVariable = VariableProperty->GetOwner<UFunction>() != nullptr;

	VariableNode->SetFromProperty(VariableProperty, bOwnerClassIsSelfContext && !bIsFunctionVariable, OwnerClass);
	VariableNode->ReconstructNode();

	MarkGraphEdit(Blueprint, Graph, true);

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Created VariableSet node for '%s' in graph '%s'."), *VariableName.ToString(), *Graph->GetPathName()),
		Blueprint,
		Graph,
		VariableNode);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::CreateDynamicCastNode(
	UEdGraph* Graph,
	const FString& TargetClassPath,
	const FVector2D& NodePosition,
	const bool bPure)
{
	if (!Graph)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Graph is null."));
	}

	if (TargetClassPath.IsEmpty())
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Target class path is empty."),
			ResolveOwningBlueprint(nullptr, Graph),
			Graph);
	}

	UClass* TargetClass = ResolveClassByPath(TargetClassPath);
	if (!TargetClass)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::NotFound,
			FString::Printf(TEXT("Target class '%s' could not be resolved."), *TargetClassPath),
			ResolveOwningBlueprint(nullptr, Graph),
			Graph);
	}

	UK2Node_DynamicCast* DynamicCastNode =
		BlueprintGraphAutomationServicePrivate::CreateNodeInGraph<UK2Node_DynamicCast>(Graph, NodePosition);
	DynamicCastNode->TargetType = TargetClass;
	DynamicCastNode->SetPurity(bPure);
	DynamicCastNode->ReconstructNode();

	UBlueprint* Blueprint = ResolveOwningBlueprint(nullptr, Graph);
	MarkGraphEdit(Blueprint, Graph, true);

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Created DynamicCast node to '%s' in graph '%s'."), *TargetClass->GetPathName(), *Graph->GetPathName()),
		Blueprint,
		Graph,
		DynamicCastNode);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::FindPin(UEdGraphNode* Node, const FName PinName)
{
	if (!Node)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Node is null."));
	}

	if (PinName.IsNone())
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Pin name is empty."),
			FBlueprintEditorUtils::FindBlueprintForNode(Node),
			Node->GetGraph(),
			Node);
	}

	UEdGraphPin* Pin = Node->FindPin(PinName);
	if (!Pin)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::NotFound,
			FString::Printf(TEXT("Pin '%s' was not found on node '%s'."), *PinName.ToString(), *Node->GetPathName()),
			FBlueprintEditorUtils::FindBlueprintForNode(Node),
			Node->GetGraph(),
			Node);
	}

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Resolved pin '%s' on node '%s'."), *PinName.ToString(), *Node->GetPathName()),
		FBlueprintEditorUtils::FindBlueprintForNode(Node),
		Node->GetGraph(),
		Node,
		Pin);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::FindPinByDirection(UEdGraphNode* Node, const FName PinName, const EEdGraphPinDirection Direction)
{
	FBlueprintGraphAutomationResult PinResult = FindPin(Node, PinName);
	if (!PinResult.IsSuccess())
	{
		return PinResult;
	}

	if (PinResult.Pin->Direction != Direction)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			FString::Printf(TEXT("Pin '%s' on node '%s' has direction '%d', expected '%d'."), *PinName.ToString(), *Node->GetPathName(), static_cast<int32>(PinResult.Pin->Direction), static_cast<int32>(Direction)),
			PinResult.Blueprint.Get(),
			PinResult.Graph.Get(),
			PinResult.Node.Get(),
			PinResult.Pin);
	}

	return PinResult;
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::LinkPins(UEdGraphPin* OutputPin, UEdGraphPin* InputPin)
{
	if (!OutputPin || !InputPin)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Both pins must be non-null."));
	}

	UEdGraphNode* OutputNode = OutputPin->GetOwningNode();
	UEdGraphNode* InputNode = InputPin->GetOwningNode();
	UEdGraph* Graph = OutputNode ? OutputNode->GetGraph() : nullptr;

	if (!OutputNode || !InputNode || !Graph || Graph != InputNode->GetGraph())
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Pins must belong to nodes in the same graph."),
			ResolveOwningBlueprint(nullptr, Graph),
			Graph,
			OutputNode,
			OutputPin);
	}

	if (OutputPin->Direction != EGPD_Output || InputPin->Direction != EGPD_Input)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("LinkPins expects an output pin followed by an input pin."),
			ResolveOwningBlueprint(nullptr, Graph),
			Graph,
			OutputNode,
			OutputPin);
	}

	const UEdGraphSchema* Schema = Graph->GetSchema();
	if (!Schema)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			FString::Printf(TEXT("Graph '%s' has no schema."), *Graph->GetPathName()),
			ResolveOwningBlueprint(nullptr, Graph),
			Graph,
			OutputNode,
			OutputPin);
	}

	if (!Schema->TryCreateConnection(OutputPin, InputPin))
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::Failed,
			FString::Printf(TEXT("Failed to connect '%s.%s' to '%s.%s'."), *OutputNode->GetName(), *OutputPin->PinName.ToString(), *InputNode->GetName(), *InputPin->PinName.ToString()),
			ResolveOwningBlueprint(nullptr, Graph),
			Graph,
			OutputNode,
			OutputPin);
	}

	UBlueprint* Blueprint = ResolveOwningBlueprint(nullptr, Graph);
	MarkGraphEdit(Blueprint, Graph, false);

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Connected '%s.%s' to '%s.%s'."), *OutputNode->GetName(), *OutputPin->PinName.ToString(), *InputNode->GetName(), *InputPin->PinName.ToString()),
		Blueprint,
		Graph,
		OutputNode,
		OutputPin);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::LinkPinsByName(
	UEdGraphNode* FromNode,
	const FName FromPinName,
	UEdGraphNode* ToNode,
	const FName ToPinName)
{
	FBlueprintGraphAutomationResult OutputPinResult = FindPinByDirection(FromNode, FromPinName, EGPD_Output);
	if (!OutputPinResult.IsSuccess())
	{
		return OutputPinResult;
	}

	FBlueprintGraphAutomationResult InputPinResult = FindPinByDirection(ToNode, ToPinName, EGPD_Input);
	if (!InputPinResult.IsSuccess())
	{
		return InputPinResult;
	}

	return LinkPins(OutputPinResult.Pin, InputPinResult.Pin);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::CreateExecutionChain(const TArray<UEdGraphNode*>& ExecNodes)
{
	if (ExecNodes.Num() == 0)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Execution chain is empty."));
	}

	if (ExecNodes.Num() == 1)
	{
		return FBlueprintGraphAutomationResult::Ok(
			FString::Printf(TEXT("Execution chain contains a single node '%s'; nothing to connect."), *ExecNodes[0]->GetPathName()),
			FBlueprintEditorUtils::FindBlueprintForNode(ExecNodes[0]),
			ExecNodes[0]->GetGraph(),
			ExecNodes[0]);
	}

	UEdGraph* Graph = ExecNodes[0] ? ExecNodes[0]->GetGraph() : nullptr;
	UBlueprint* Blueprint = ExecNodes[0] ? FBlueprintEditorUtils::FindBlueprintForNode(ExecNodes[0]) : nullptr;

	for (int32 Index = 0; Index < ExecNodes.Num() - 1; ++Index)
	{
		UEdGraphNode* CurrentNode = ExecNodes[Index];
		UEdGraphNode* NextNode = ExecNodes[Index + 1];
		if (!CurrentNode || !NextNode)
		{
			return FBlueprintGraphAutomationResult::Error(
				EBlueprintAutomationResultCode::InvalidArgument,
				TEXT("Execution chain contains a null node."),
				Blueprint,
				Graph);
		}

		if (CurrentNode->GetGraph() != Graph || NextNode->GetGraph() != Graph)
		{
			return FBlueprintGraphAutomationResult::Error(
				EBlueprintAutomationResultCode::InvalidArgument,
				TEXT("All execution chain nodes must belong to the same graph."),
				Blueprint,
				Graph);
		}

		FBlueprintGraphAutomationResult LinkResult =
			LinkPinsByName(CurrentNode, UEdGraphSchema_K2::PN_Then, NextNode, UEdGraphSchema_K2::PN_Execute);
		if (!LinkResult.IsSuccess())
		{
			return LinkResult;
		}
	}

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Created execution chain across %d nodes in graph '%s'."), ExecNodes.Num(), *Graph->GetPathName()),
		Blueprint,
		Graph,
		ExecNodes.Last());
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::InspectNodeToJson(UEdGraphNode* Node, const bool bIncludeLinkedPins)
{
	if (!Node)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Node is null."));
	}

	const FString JsonPayload =
		BlueprintGraphAutomationServicePrivate::SerializeJsonObject(
			BlueprintGraphAutomationServicePrivate::BuildNodeJson(Node, true, bIncludeLinkedPins));

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Serialized node '%s' to JSON."), *Node->GetPathName()),
		FBlueprintEditorUtils::FindBlueprintForNode(Node),
		Node->GetGraph(),
		Node,
		nullptr,
		JsonPayload);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::InspectGraphToJson(
	UEdGraph* Graph,
	const bool bIncludePins,
	const bool bIncludeLinkedPins)
{
	if (!Graph)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Graph is null."));
	}

	const FString JsonPayload =
		BlueprintGraphAutomationServicePrivate::SerializeGraphJson(Graph, bIncludePins, bIncludeLinkedPins);

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Serialized graph '%s' to JSON."), *Graph->GetPathName()),
		ResolveOwningBlueprint(nullptr, Graph),
		Graph,
		nullptr,
		nullptr,
		JsonPayload);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::ResolveFunctionByPath(const FString& FunctionPath)
{
	FString Error;
	const UFunction* Function = ResolveFunctionInternal(FunctionPath, Error);
	if (!Function)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::NotFound,
			Error.IsEmpty() ? FString::Printf(TEXT("Could not resolve function '%s'."), *FunctionPath) : Error);
	}

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Resolved function '%s'."), *Function->GetPathName()),
		nullptr,
		nullptr,
		nullptr,
		nullptr,
		SerializeFunctionToJson(Function));
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::ResolveVariableByName(UBlueprint* Blueprint, const FName VariableName, const bool bCompileIfNeeded)
{
	if (!Blueprint)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Blueprint is null."));
	}

	if (VariableName.IsNone())
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Variable name is empty."),
			Blueprint);
	}

	const FBPVariableDescription* VariableDescription = FindVariableDescription(Blueprint, VariableName);
	FProperty* VariableProperty = ResolveVariableProperty(Blueprint, VariableName, bCompileIfNeeded);

	if (!VariableDescription && !VariableProperty)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::NotFound,
			FString::Printf(TEXT("Variable '%s' was not found on Blueprint '%s'."), *VariableName.ToString(), *Blueprint->GetPathName()),
			Blueprint);
	}

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Resolved variable '%s' on Blueprint '%s'."), *VariableName.ToString(), *Blueprint->GetPathName()),
		Blueprint,
		nullptr,
		nullptr,
		nullptr,
		SerializeVariableToJson(Blueprint, VariableDescription, VariableProperty));
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::ApplyBatchDefinition(
	UBlueprint* Blueprint,
	UEdGraph* Graph,
	const FBlueprintGraphBatchDefinition& BatchDefinition)
{
	Blueprint = ResolveOwningBlueprint(Blueprint, Graph);
	if (!Blueprint)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Blueprint is null and could not be resolved from graph."),
			Blueprint,
			Graph);
	}

	if (!Graph)
	{
		FBlueprintGraphAutomationResult EventGraphResult = GetEventGraph(Blueprint);
		if (!EventGraphResult.IsSuccess())
		{
			return EventGraphResult;
		}
		Graph = EventGraphResult.Graph.Get();
	}

	FBlueprintGraphTransactionScope TransactionScope(Blueprint, Graph, FText::FromString(TEXT("Apply Blueprint Graph Batch")));

	TMap<FString, UEdGraphNode*> CreatedNodesById;

	for (const FBlueprintGraphBatchNodeDefinition& NodeDefinition : BatchDefinition.Nodes)
	{
		FBlueprintGraphAutomationResult NodeResult;

		switch (NodeDefinition.Kind)
		{
		case EBlueprintGraphBatchNodeKind::CustomEvent:
			NodeResult = NodeDefinition.Pins.Num() > 0
				? CreateCustomEventNodeWithPins(Graph, NodeDefinition.Name, NodeDefinition.Pins, NodeDefinition.Position)
				: CreateCustomEventNode(Graph, NodeDefinition.Name, NodeDefinition.Position);
			break;

		case EBlueprintGraphBatchNodeKind::CustomEventFromSignature:
		{
			FString ResolveError;
			const UFunction* SignatureFunction = !NodeDefinition.FunctionPath.IsEmpty()
				? ResolveFunctionInternal(NodeDefinition.FunctionPath, ResolveError)
				: (ResolveClassByPath(NodeDefinition.OwnerClassPath)
					? ResolveClassByPath(NodeDefinition.OwnerClassPath)->FindFunctionByName(NodeDefinition.FunctionName)
					: nullptr);

			if (!SignatureFunction)
			{
				return FBlueprintGraphAutomationResult::Error(
					EBlueprintAutomationResultCode::NotFound,
					ResolveError.IsEmpty()
						? FString::Printf(TEXT("Failed to resolve signature function for batch node '%s'."), *NodeDefinition.Id)
						: ResolveError,
					Blueprint,
					Graph);
			}

			NodeResult = CreateCustomEventNodeFromSignature(Graph, NodeDefinition.Name, SignatureFunction, NodeDefinition.Position);
			break;
		}

		case EBlueprintGraphBatchNodeKind::EventBySignature:
		{
			FString ResolveError;
			const UFunction* SignatureFunction = !NodeDefinition.FunctionPath.IsEmpty()
				? ResolveFunctionInternal(NodeDefinition.FunctionPath, ResolveError)
				: (ResolveClassByPath(NodeDefinition.OwnerClassPath)
					? ResolveClassByPath(NodeDefinition.OwnerClassPath)->FindFunctionByName(NodeDefinition.FunctionName)
					: nullptr);

			if (!SignatureFunction)
			{
				return FBlueprintGraphAutomationResult::Error(
					EBlueprintAutomationResultCode::NotFound,
					ResolveError.IsEmpty()
						? FString::Printf(TEXT("Failed to resolve event signature for batch node '%s'."), *NodeDefinition.Id)
						: ResolveError,
					Blueprint,
					Graph);
			}

			NodeResult = SpawnEventNodeBySignature(Graph, SignatureFunction, NodeDefinition.Position);
			break;
		}

		case EBlueprintGraphBatchNodeKind::ActionBySignature:
		{
			const FBlueprintActionAutomationResult ActionResult =
				FBlueprintActionAutomationService::SpawnActionBySignature(
				Blueprint,
				Graph,
				NodeDefinition.ActionSignature,
				NodeDefinition.Position);
			NodeResult = ActionResult.IsSuccess()
				? FBlueprintGraphAutomationResult::Ok(
					ActionResult.Message,
					ActionResult.Blueprint.Get(),
					ActionResult.Graph.Get(),
					ActionResult.Node.Get(),
					nullptr,
					ActionResult.JsonPayload)
				: FBlueprintGraphAutomationResult::Error(
					ActionResult.Code,
					ActionResult.Message,
					ActionResult.Blueprint.Get(),
					ActionResult.Graph.Get(),
					ActionResult.Node.Get(),
					nullptr,
					ActionResult.JsonPayload);
			break;
		}

		case EBlueprintGraphBatchNodeKind::CallFunction:
			if (!NodeDefinition.FunctionPath.IsEmpty())
			{
				FString ResolveError;
				const UFunction* Function = ResolveFunctionInternal(NodeDefinition.FunctionPath, ResolveError);
				if (!Function)
				{
					return FBlueprintGraphAutomationResult::Error(
						EBlueprintAutomationResultCode::NotFound,
						ResolveError,
						Blueprint,
						Graph);
				}
				NodeResult = CreateCallFunctionNode(Graph, Function, NodeDefinition.Position);
			}
			else
			{
				NodeResult = CreateCallFunctionNodeByName(
					Graph,
					ResolveClassByPath(NodeDefinition.OwnerClassPath),
					NodeDefinition.FunctionName,
					NodeDefinition.Position);
			}
			break;

		case EBlueprintGraphBatchNodeKind::DynamicCast:
			NodeResult = CreateDynamicCastNode(
				Graph,
				NodeDefinition.TargetClassPath.IsEmpty() ? NodeDefinition.OwnerClassPath : NodeDefinition.TargetClassPath,
				NodeDefinition.Position,
				NodeDefinition.bPure);
			break;

		case EBlueprintGraphBatchNodeKind::VariableGet:
			NodeResult = CreateVariableGetNode(
				Blueprint,
				Graph,
				NodeDefinition.VariableName,
				NodeDefinition.Position,
				NodeDefinition.bPure,
				NodeDefinition.OwnerClassPath);
			break;

		case EBlueprintGraphBatchNodeKind::VariableSet:
			NodeResult = CreateVariableSetNode(
				Blueprint,
				Graph,
				NodeDefinition.VariableName,
				NodeDefinition.Position,
				NodeDefinition.OwnerClassPath);
			break;

		default:
			return FBlueprintGraphAutomationResult::Error(
				EBlueprintAutomationResultCode::Unsupported,
				FString::Printf(TEXT("Unsupported batch node kind for node id '%s'."), *NodeDefinition.Id),
				Blueprint,
				Graph);
		}

		if (!NodeResult.IsSuccess())
		{
			return NodeResult;
		}

		if (NodeDefinition.PinDefaults.Num() > 0)
		{
			FBlueprintGraphAutomationResult PinDefaultsResult =
				ApplyPinDefaults(Blueprint, Graph, NodeResult.Node.Get(), NodeDefinition.PinDefaults);
			if (!PinDefaultsResult.IsSuccess())
			{
				return PinDefaultsResult;
			}
		}

		if (!NodeDefinition.Id.IsEmpty())
		{
			CreatedNodesById.Add(NodeDefinition.Id, NodeResult.Node.Get());
		}
	}

	for (const FBlueprintGraphBatchLinkDefinition& LinkDefinition : BatchDefinition.Links)
	{
		FString FromReference;
		FString ToReference;
		UEdGraphNode* FromNode =
			BlueprintGraphAutomationServicePrivate::ResolveBatchLinkNodeReference(
				LinkDefinition,
				true,
				CreatedNodesById,
				Graph,
				FromReference);
		UEdGraphNode* ToNode =
			BlueprintGraphAutomationServicePrivate::ResolveBatchLinkNodeReference(
				LinkDefinition,
				false,
				CreatedNodesById,
				Graph,
				ToReference);

		if (!FromNode || !ToNode)
		{
			return FBlueprintGraphAutomationResult::Error(
				EBlueprintAutomationResultCode::NotFound,
				FString::Printf(TEXT("Batch link references unknown nodes %s -> %s."), *FromReference, *ToReference),
				Blueprint,
				Graph);
		}

		FBlueprintGraphAutomationResult LinkResult =
			LinkPinsByName(FromNode, LinkDefinition.FromPinName, ToNode, LinkDefinition.ToPinName);
		if (!LinkResult.IsSuccess())
		{
			return LinkResult;
		}
	}

	for (const TArray<FString>& Chain : BatchDefinition.ExecutionChains)
	{
		TArray<UEdGraphNode*> ChainNodes;
		for (const FString& NodeId : Chain)
		{
			UEdGraphNode* const* NodePtr = CreatedNodesById.Find(NodeId);
			if (!NodePtr)
			{
				return FBlueprintGraphAutomationResult::Error(
					EBlueprintAutomationResultCode::NotFound,
					FString::Printf(TEXT("Execution chain references unknown node id '%s'."), *NodeId),
					Blueprint,
					Graph);
			}

			ChainNodes.Add(*NodePtr);
		}

		FBlueprintGraphAutomationResult ChainResult = CreateExecutionChain(ChainNodes);
		if (!ChainResult.IsSuccess())
		{
			return ChainResult;
		}
	}

	TSharedPtr<FJsonObject> SummaryObject = MakeShared<FJsonObject>();
	TArray<TSharedPtr<FJsonValue>> CreatedNodeArray;
	for (const TPair<FString, UEdGraphNode*>& Pair : CreatedNodesById)
	{
		TSharedPtr<FJsonObject> Item = MakeShared<FJsonObject>();
		Item->SetStringField(TEXT("id"), Pair.Key);
		Item->SetStringField(TEXT("node_path"), Pair.Value ? Pair.Value->GetPathName() : FString());
		Item->SetStringField(TEXT("node_name"), Pair.Value ? Pair.Value->GetName() : FString());
		CreatedNodeArray.Add(MakeShared<FJsonValueObject>(Item));
	}
	SummaryObject->SetArrayField(TEXT("created_nodes"), CreatedNodeArray);

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Applied graph batch with %d nodes, %d links and %d execution chains."), BatchDefinition.Nodes.Num(), BatchDefinition.Links.Num(), BatchDefinition.ExecutionChains.Num()),
		Blueprint,
		Graph,
		nullptr,
		nullptr,
		BlueprintGraphAutomationServicePrivate::SerializeJsonObject(SummaryObject));
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::ApplyBatchJson(
	UBlueprint* Blueprint,
	UEdGraph* Graph,
	const FString& BatchJson)
{
	FBlueprintGraphBatchDefinition BatchDefinition;
	FString Error;
	if (!TryParseBatchJson(BatchJson, BatchDefinition, Error))
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			Error,
			Blueprint,
			Graph);
	}

	return ApplyBatchDefinition(Blueprint, Graph, BatchDefinition);
}

UBlueprint* FBlueprintGraphAutomationService::ResolveOwningBlueprint(UBlueprint* ExplicitBlueprint, UEdGraph* Graph)
{
	if (ExplicitBlueprint)
	{
		return ExplicitBlueprint;
	}

	if (!Graph)
	{
		return nullptr;
	}

	return FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
}

UClass* FBlueprintGraphAutomationService::ResolveClassByPath(const FString& ClassPath)
{
	if (ClassPath.IsEmpty())
	{
		return nullptr;
	}

	const FString SanitizedPath = BlueprintGraphAutomationServicePrivate::SanitizeObjectPath(ClassPath, TEXT("Class"));

	if (UClass* Class = FindObject<UClass>(nullptr, *SanitizedPath))
	{
		return Class;
	}

	return LoadObject<UClass>(nullptr, *SanitizedPath);
}

const UFunction* FBlueprintGraphAutomationService::ResolveFunctionInternal(const FString& FunctionPath, FString& OutError)
{
	if (FunctionPath.IsEmpty())
	{
		OutError = TEXT("Function path is empty.");
		return nullptr;
	}

	const FString SanitizedPath = BlueprintGraphAutomationServicePrivate::SanitizeObjectPath(FunctionPath, TEXT("Function"));

	if (UFunction* Function = FindObject<UFunction>(nullptr, *SanitizedPath))
	{
		return Function;
	}

	if (UFunction* LoadedFunction = LoadObject<UFunction>(nullptr, *SanitizedPath))
	{
		return LoadedFunction;
	}

	int32 SeparatorIndex = INDEX_NONE;
	if (!SanitizedPath.FindLastChar(TEXT(':'), SeparatorIndex))
	{
		SanitizedPath.FindLastChar(TEXT('.'), SeparatorIndex);
	}

	if (SeparatorIndex == INDEX_NONE)
	{
		OutError = FString::Printf(TEXT("Function path '%s' is not a direct UFunction path and does not contain class/member separator ':' or '.'."), *FunctionPath);
		return nullptr;
	}

	const FString ClassPath = SanitizedPath.Left(SeparatorIndex);
	const FString FunctionName = SanitizedPath.Mid(SeparatorIndex + 1);
	UClass* FunctionClass = ResolveClassByPath(ClassPath);
	if (!FunctionClass)
	{
		OutError = FString::Printf(TEXT("Failed to resolve class '%s' from function path '%s'."), *ClassPath, *FunctionPath);
		return nullptr;
	}

	if (const UFunction* Function = FunctionClass->FindFunctionByName(*FunctionName))
	{
		return Function;
	}

	OutError = FString::Printf(TEXT("Function '%s' was not found on class '%s'."), *FunctionName, *FunctionClass->GetPathName());
	return nullptr;
}

FProperty* FBlueprintGraphAutomationService::ResolveVariableProperty(UBlueprint* Blueprint, const FName VariableName, const bool bCompileIfNeeded)
{
	if (!Blueprint || VariableName.IsNone())
	{
		return nullptr;
	}

	UClass* SearchClass = Blueprint->SkeletonGeneratedClass ? Blueprint->SkeletonGeneratedClass : Blueprint->GeneratedClass;
	if (SearchClass)
	{
		if (FProperty* Property = FindFProperty<FProperty>(SearchClass, VariableName))
		{
			return Property;
		}
	}

	if (bCompileIfNeeded && FindVariableDescription(Blueprint, VariableName) != nullptr)
	{
		FKismetEditorUtilities::CompileBlueprint(Blueprint);

		SearchClass = Blueprint->SkeletonGeneratedClass ? Blueprint->SkeletonGeneratedClass : Blueprint->GeneratedClass;
		if (SearchClass)
		{
			if (FProperty* Property = FindFProperty<FProperty>(SearchClass, VariableName))
			{
				return Property;
			}
		}
	}

	return nullptr;
}

FProperty* FBlueprintGraphAutomationService::ResolveVariableProperty(
	UBlueprint* Blueprint,
	const FString& OwnerClassPath,
	const FName VariableName,
	const bool bCompileIfNeeded,
	UClass*& OutOwnerClass,
	bool& bOutIsSelfContext)
{
	OutOwnerClass = nullptr;
	bOutIsSelfContext = false;

	if (VariableName.IsNone())
	{
		return nullptr;
	}

	if (!OwnerClassPath.IsEmpty())
	{
		OutOwnerClass = ResolveClassByPath(OwnerClassPath);
		if (!OutOwnerClass)
		{
			return nullptr;
		}

		if (Blueprint && Blueprint->SkeletonGeneratedClass)
		{
			bOutIsSelfContext =
				(Blueprint->SkeletonGeneratedClass->GetAuthoritativeClass() == OutOwnerClass) ||
				Blueprint->SkeletonGeneratedClass->IsChildOf(OutOwnerClass);
		}

		return FindFProperty<FProperty>(OutOwnerClass, VariableName);
	}

	FProperty* Property = ResolveVariableProperty(Blueprint, VariableName, bCompileIfNeeded);
	if (!Property)
	{
		return nullptr;
	}

	OutOwnerClass = Property->GetOwnerClass();
	if (Blueprint && Blueprint->SkeletonGeneratedClass && OutOwnerClass)
	{
		bOutIsSelfContext =
			(Blueprint->SkeletonGeneratedClass->GetAuthoritativeClass() == OutOwnerClass) ||
			Blueprint->SkeletonGeneratedClass->IsChildOf(OutOwnerClass);
	}

	return Property;
}

const FBPVariableDescription* FBlueprintGraphAutomationService::FindVariableDescription(const UBlueprint* Blueprint, const FName VariableName)
{
	if (!Blueprint || VariableName.IsNone())
	{
		return nullptr;
	}

	for (const FBPVariableDescription& Variable : Blueprint->NewVariables)
	{
		if (Variable.VarName == VariableName)
		{
			return &Variable;
		}
	}

	return nullptr;
}

UObject* FBlueprintGraphAutomationService::ResolveObjectByPath(const FString& ObjectPath)
{
	if (ObjectPath.IsEmpty())
	{
		return nullptr;
	}

	const FString SanitizedPath =
		BlueprintGraphAutomationServicePrivate::SanitizeObjectPath(ObjectPath, TEXT("Object"));

	if (UObject* Object = FindObject<UObject>(nullptr, *SanitizedPath))
	{
		return Object;
	}

	return LoadObject<UObject>(nullptr, *SanitizedPath);
}

FBlueprintGraphAutomationResult FBlueprintGraphAutomationService::ApplyPinDefaults(
	UBlueprint* Blueprint,
	UEdGraph* Graph,
	UEdGraphNode* Node,
	const TArray<FBlueprintGraphBatchPinDefaultDefinition>& PinDefaults)
{
	if (!Node)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Node is null."),
			Blueprint,
			Graph);
	}

	Graph = Graph ? Graph : Node->GetGraph();
	if (!Graph)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			FString::Printf(TEXT("Node '%s' does not belong to a graph."), *Node->GetPathName()),
			Blueprint,
			nullptr,
			Node);
	}

	const UEdGraphSchema* Schema = Graph->GetSchema();
	if (!Schema)
	{
		return FBlueprintGraphAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			FString::Printf(TEXT("Graph '%s' has no schema."), *Graph->GetPathName()),
			Blueprint,
			Graph,
			Node);
	}

	for (const FBlueprintGraphBatchPinDefaultDefinition& PinDefault : PinDefaults)
	{
		if (PinDefault.PinName.IsNone())
		{
			return FBlueprintGraphAutomationResult::Error(
				EBlueprintAutomationResultCode::InvalidArgument,
				FString::Printf(TEXT("Node '%s' contains a pin default with an empty pin name."), *Node->GetPathName()),
				Blueprint,
				Graph,
				Node);
		}

		FBlueprintGraphAutomationResult PinResult = FindPin(Node, PinDefault.PinName);
		if (!PinResult.IsSuccess())
		{
			return PinResult;
		}

		UEdGraphPin* Pin = PinResult.Pin;
		if (!Pin)
		{
			return FBlueprintGraphAutomationResult::Error(
				EBlueprintAutomationResultCode::Failed,
				FString::Printf(TEXT("Resolved pin '%s' on node '%s' is null."), *PinDefault.PinName.ToString(), *Node->GetPathName()),
				PinResult.Blueprint.Get(),
				PinResult.Graph.Get(),
				PinResult.Node.Get());
		}

		if (!PinDefault.DefaultObjectPath.IsEmpty())
		{
			UObject* DefaultObject = ResolveObjectByPath(PinDefault.DefaultObjectPath);
			if (!DefaultObject)
			{
				return FBlueprintGraphAutomationResult::Error(
					EBlueprintAutomationResultCode::NotFound,
					FString::Printf(
						TEXT("Default object '%s' for pin '%s' on node '%s' could not be resolved."),
						*PinDefault.DefaultObjectPath,
						*PinDefault.PinName.ToString(),
						*Node->GetPathName()),
					PinResult.Blueprint.Get(),
					PinResult.Graph.Get(),
					PinResult.Node.Get(),
					PinResult.Pin);
			}

			Schema->TrySetDefaultObject(*Pin, DefaultObject, false);
		}
		else if (!PinDefault.DefaultText.IsEmpty())
		{
			Schema->TrySetDefaultText(*Pin, FText::FromString(PinDefault.DefaultText), false);
		}
		else
		{
			Schema->TrySetDefaultValue(*Pin, PinDefault.DefaultValue, false);
		}
	}

	MarkGraphEdit(Blueprint, Graph, false);

	return FBlueprintGraphAutomationResult::Ok(
		FString::Printf(TEXT("Applied %d pin defaults on node '%s'."), PinDefaults.Num(), *Node->GetPathName()),
		Blueprint,
		Graph,
		Node);
}

FEdGraphPinType FBlueprintGraphAutomationService::MakeEventPinType(const EBlueprintPrimitiveVariableType Type)
{
	FEdGraphPinType PinType;

	switch (Type)
	{
	case EBlueprintPrimitiveVariableType::Float:
		PinType.PinCategory = UEdGraphSchema_K2::PC_Real;
		PinType.PinSubCategory = UEdGraphSchema_K2::PC_Float;
		break;
	case EBlueprintPrimitiveVariableType::Bool:
		PinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
		break;
	case EBlueprintPrimitiveVariableType::Int32:
		PinType.PinCategory = UEdGraphSchema_K2::PC_Int;
		break;
	case EBlueprintPrimitiveVariableType::String:
		PinType.PinCategory = UEdGraphSchema_K2::PC_String;
		break;
	case EBlueprintPrimitiveVariableType::Name:
		PinType.PinCategory = UEdGraphSchema_K2::PC_Name;
		break;
	default:
		PinType.PinCategory = UEdGraphSchema_K2::PC_Wildcard;
		break;
	}

	return PinType;
}

FString FBlueprintGraphAutomationService::SerializeFunctionToJson(const UFunction* Function)
{
	TSharedPtr<FJsonObject> FunctionObject = MakeShared<FJsonObject>();
	if (!Function)
	{
		return BlueprintGraphAutomationServicePrivate::SerializeJsonObject(FunctionObject);
	}

	FunctionObject->SetStringField(TEXT("name"), Function->GetName());
	FunctionObject->SetStringField(TEXT("path"), Function->GetPathName());
	FunctionObject->SetStringField(TEXT("owner_class"), Function->GetOuterUClass() ? Function->GetOuterUClass()->GetPathName() : FString());
	FunctionObject->SetNumberField(TEXT("function_flags"), static_cast<double>(Function->FunctionFlags));

	TArray<TSharedPtr<FJsonValue>> Parameters;
	const UEdGraphSchema_K2* Schema = GetDefault<UEdGraphSchema_K2>();
	for (TFieldIterator<FProperty> PropIt(Function); PropIt && (PropIt->PropertyFlags & CPF_Parm); ++PropIt)
	{
		const FProperty* Param = *PropIt;
		FEdGraphPinType PinType;
		Schema->ConvertPropertyToPinType(Param, PinType);

		TSharedPtr<FJsonObject> ParamObject = MakeShared<FJsonObject>();
		ParamObject->SetStringField(TEXT("name"), Param->GetName());
		ParamObject->SetStringField(TEXT("cpp_type"), Param->GetCPPType());
		ParamObject->SetStringField(TEXT("pin_category"), PinType.PinCategory.ToString());
		ParamObject->SetStringField(TEXT("pin_subcategory"), PinType.PinSubCategory.ToString());
		ParamObject->SetBoolField(TEXT("is_out"), Param->HasAnyPropertyFlags(CPF_OutParm));
		ParamObject->SetBoolField(TEXT("is_ref"), Param->HasAnyPropertyFlags(CPF_ReferenceParm));
		Parameters.Add(MakeShared<FJsonValueObject>(ParamObject));
	}

	FunctionObject->SetArrayField(TEXT("parameters"), Parameters);

	return BlueprintGraphAutomationServicePrivate::SerializeJsonObject(FunctionObject);
}

FString FBlueprintGraphAutomationService::SerializeVariableToJson(UBlueprint* Blueprint, const FBPVariableDescription* VariableDescription, const FProperty* VariableProperty)
{
	TSharedPtr<FJsonObject> VariableObject = MakeShared<FJsonObject>();
	VariableObject->SetStringField(TEXT("blueprint"), Blueprint ? Blueprint->GetPathName() : FString());

	if (VariableDescription)
	{
		VariableObject->SetStringField(TEXT("name"), VariableDescription->VarName.ToString());
		VariableObject->SetStringField(TEXT("friendly_name"), VariableDescription->FriendlyName);
		VariableObject->SetStringField(TEXT("category"), VariableDescription->Category.ToString());
		VariableObject->SetStringField(TEXT("default_value"), VariableDescription->DefaultValue);
		VariableObject->SetStringField(TEXT("pin_category"), VariableDescription->VarType.PinCategory.ToString());
		VariableObject->SetStringField(TEXT("pin_subcategory"), VariableDescription->VarType.PinSubCategory.ToString());
	}

	if (VariableProperty)
	{
		VariableObject->SetStringField(TEXT("property_name"), VariableProperty->GetName());
		VariableObject->SetStringField(TEXT("cpp_type"), VariableProperty->GetCPPType());
		VariableObject->SetStringField(TEXT("owner_class"), VariableProperty->GetOwnerClass() ? VariableProperty->GetOwnerClass()->GetPathName() : FString());
	}

	return BlueprintGraphAutomationServicePrivate::SerializeJsonObject(VariableObject);
}

bool FBlueprintGraphAutomationService::TryParseBatchJson(
	const FString& BatchJson,
	FBlueprintGraphBatchDefinition& OutBatchDefinition,
	FString& OutError)
{
	TSharedPtr<FJsonObject> RootObject;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(BatchJson);
	if (!FJsonSerializer::Deserialize(Reader, RootObject) || !RootObject.IsValid())
	{
		OutError = TEXT("Batch JSON is not a valid JSON object.");
		return false;
	}

	const TArray<TSharedPtr<FJsonValue>>* NodesArray = nullptr;
	if (RootObject->TryGetArrayField(TEXT("nodes"), NodesArray))
	{
		for (int32 Index = 0; Index < NodesArray->Num(); ++Index)
		{
			const TSharedPtr<FJsonObject>* NodeObject = nullptr;
			if (!(*NodesArray)[Index].IsValid() || !(*NodesArray)[Index]->TryGetObject(NodeObject) || !NodeObject || !NodeObject->IsValid())
			{
				OutError = FString::Printf(TEXT("Batch node at index %d is not a JSON object."), Index);
				return false;
			}

			FBlueprintGraphBatchNodeDefinition NodeDefinition;
			(*NodeObject)->TryGetStringField(TEXT("id"), NodeDefinition.Id);
			(*NodeObject)->TryGetStringField(TEXT("name"), NodeDefinition.Name);
			(*NodeObject)->TryGetStringField(TEXT("owner_class"), NodeDefinition.OwnerClassPath);
			(*NodeObject)->TryGetStringField(TEXT("target_class"), NodeDefinition.TargetClassPath);
			(*NodeObject)->TryGetStringField(TEXT("function_path"), NodeDefinition.FunctionPath);
			(*NodeObject)->TryGetStringField(TEXT("action_signature"), NodeDefinition.ActionSignature);

			FString KindString;
			if (!(*NodeObject)->TryGetStringField(TEXT("type"), KindString) ||
				!BlueprintGraphAutomationServicePrivate::ParseBatchNodeKind(KindString, NodeDefinition.Kind))
			{
				OutError = FString::Printf(TEXT("Batch node '%s' has unsupported or missing type."), *NodeDefinition.Id);
				return false;
			}

			FString FunctionName;
			if ((*NodeObject)->TryGetStringField(TEXT("function"), FunctionName))
			{
				NodeDefinition.FunctionName = FName(*FunctionName);
			}

			FString VariableName;
			if ((*NodeObject)->TryGetStringField(TEXT("variable"), VariableName))
			{
				NodeDefinition.VariableName = FName(*VariableName);
			}

			(*NodeObject)->TryGetBoolField(TEXT("pure"), NodeDefinition.bPure);

			double X = 0.0;
			double Y = 0.0;
			(*NodeObject)->TryGetNumberField(TEXT("x"), X);
			(*NodeObject)->TryGetNumberField(TEXT("y"), Y);
			NodeDefinition.Position = FVector2D(X, Y);

			const TArray<TSharedPtr<FJsonValue>>* PinsArray = nullptr;
			if ((*NodeObject)->TryGetArrayField(TEXT("pins"), PinsArray))
			{
				for (int32 PinIndex = 0; PinIndex < PinsArray->Num(); ++PinIndex)
				{
					const TSharedPtr<FJsonObject>* PinObject = nullptr;
					if (!(*PinsArray)[PinIndex].IsValid() || !(*PinsArray)[PinIndex]->TryGetObject(PinObject) || !PinObject || !PinObject->IsValid())
					{
						OutError = FString::Printf(TEXT("Batch node '%s' pin at index %d is not a JSON object."), *NodeDefinition.Id, PinIndex);
						return false;
					}

					FBlueprintCustomEventPinDefinition PinDefinition;
					FString PinName;
					FString PinTypeString;
					(*PinObject)->TryGetStringField(TEXT("default"), PinDefinition.DefaultValue);

					if (!(*PinObject)->TryGetStringField(TEXT("name"), PinName) || PinName.IsEmpty())
					{
						OutError = FString::Printf(TEXT("Batch node '%s' contains a pin with empty name."), *NodeDefinition.Id);
						return false;
					}

					if (!(*PinObject)->TryGetStringField(TEXT("type"), PinTypeString) ||
						!BlueprintGraphAutomationServicePrivate::ParsePrimitiveType(PinTypeString, PinDefinition.Type))
					{
						OutError = FString::Printf(TEXT("Batch node '%s' pin '%s' has unsupported type '%s'."), *NodeDefinition.Id, *PinName, *PinTypeString);
						return false;
					}

					PinDefinition.Name = FName(*PinName);
					NodeDefinition.Pins.Add(PinDefinition);
				}
			}

			const TArray<TSharedPtr<FJsonValue>>* PinDefaultsArray = nullptr;
			if ((*NodeObject)->TryGetArrayField(TEXT("pin_defaults"), PinDefaultsArray))
			{
				for (int32 PinDefaultIndex = 0; PinDefaultIndex < PinDefaultsArray->Num(); ++PinDefaultIndex)
				{
					const TSharedPtr<FJsonObject>* PinDefaultObject = nullptr;
					if (!(*PinDefaultsArray)[PinDefaultIndex].IsValid() ||
						!(*PinDefaultsArray)[PinDefaultIndex]->TryGetObject(PinDefaultObject) ||
						!PinDefaultObject ||
						!PinDefaultObject->IsValid())
					{
						OutError = FString::Printf(
							TEXT("Batch node '%s' pin_default at index %d is not a JSON object."),
							*NodeDefinition.Id,
							PinDefaultIndex);
						return false;
					}

					FBlueprintGraphBatchPinDefaultDefinition PinDefaultDefinition;
					FString PinName;
					if (!(*PinDefaultObject)->TryGetStringField(TEXT("pin"), PinName) || PinName.IsEmpty())
					{
						OutError = FString::Printf(
							TEXT("Batch node '%s' pin_default at index %d is missing 'pin'."),
							*NodeDefinition.Id,
							PinDefaultIndex);
						return false;
					}

					PinDefaultDefinition.PinName = FName(*PinName);
					(*PinDefaultObject)->TryGetStringField(TEXT("default_value"), PinDefaultDefinition.DefaultValue);
					(*PinDefaultObject)->TryGetStringField(TEXT("default_object"), PinDefaultDefinition.DefaultObjectPath);
					(*PinDefaultObject)->TryGetStringField(TEXT("default_text"), PinDefaultDefinition.DefaultText);

					if (PinDefaultDefinition.DefaultValue.IsEmpty() &&
						PinDefaultDefinition.DefaultObjectPath.IsEmpty() &&
						PinDefaultDefinition.DefaultText.IsEmpty())
					{
						OutError = FString::Printf(
							TEXT("Batch node '%s' pin_default '%s' must specify one of default_value, default_object or default_text."),
							*NodeDefinition.Id,
							*PinName);
						return false;
					}

					NodeDefinition.PinDefaults.Add(MoveTemp(PinDefaultDefinition));
				}
			}

			OutBatchDefinition.Nodes.Add(MoveTemp(NodeDefinition));
		}
	}

	const TArray<TSharedPtr<FJsonValue>>* LinksArray = nullptr;
	if (RootObject->TryGetArrayField(TEXT("links"), LinksArray))
	{
		for (int32 Index = 0; Index < LinksArray->Num(); ++Index)
		{
			const TSharedPtr<FJsonObject>* LinkObject = nullptr;
			if (!(*LinksArray)[Index].IsValid() || !(*LinksArray)[Index]->TryGetObject(LinkObject) || !LinkObject || !LinkObject->IsValid())
			{
				OutError = FString::Printf(TEXT("Batch link at index %d is not a JSON object."), Index);
				return false;
			}

			FBlueprintGraphBatchLinkDefinition LinkDefinition;
			FString FromPin;
			FString ToPin;

			(*LinkObject)->TryGetStringField(TEXT("from_node"), LinkDefinition.FromNodeId);
			(*LinkObject)->TryGetStringField(TEXT("from_node_name"), LinkDefinition.FromNodeName);
			(*LinkObject)->TryGetStringField(TEXT("from_node_path"), LinkDefinition.FromNodePath);
			(*LinkObject)->TryGetStringField(TEXT("to_node"), LinkDefinition.ToNodeId);
			(*LinkObject)->TryGetStringField(TEXT("to_node_name"), LinkDefinition.ToNodeName);
			(*LinkObject)->TryGetStringField(TEXT("to_node_path"), LinkDefinition.ToNodePath);

			if ((LinkDefinition.FromNodeId.IsEmpty() && LinkDefinition.FromNodeName.IsEmpty() && LinkDefinition.FromNodePath.IsEmpty()) ||
				(LinkDefinition.ToNodeId.IsEmpty() && LinkDefinition.ToNodeName.IsEmpty() && LinkDefinition.ToNodePath.IsEmpty()) ||
				!(*LinkObject)->TryGetStringField(TEXT("from_pin"), FromPin) ||
				!(*LinkObject)->TryGetStringField(TEXT("to_pin"), ToPin))
			{
				OutError = FString::Printf(TEXT("Batch link at index %d is missing required fields."), Index);
				return false;
			}

			LinkDefinition.FromPinName = FName(*FromPin);
			LinkDefinition.ToPinName = FName(*ToPin);
			OutBatchDefinition.Links.Add(MoveTemp(LinkDefinition));
		}
	}

	const TArray<TSharedPtr<FJsonValue>>* ChainsArray = nullptr;
	if (RootObject->TryGetArrayField(TEXT("execution_chains"), ChainsArray))
	{
		for (int32 ChainIndex = 0; ChainIndex < ChainsArray->Num(); ++ChainIndex)
		{
			const TArray<TSharedPtr<FJsonValue>>* ChainValues = nullptr;
			if (!(*ChainsArray)[ChainIndex].IsValid() || !(*ChainsArray)[ChainIndex]->TryGetArray(ChainValues) || !ChainValues)
			{
				OutError = FString::Printf(TEXT("Execution chain at index %d is not an array."), ChainIndex);
				return false;
			}

			TArray<FString> Chain;
			for (int32 ValueIndex = 0; ValueIndex < ChainValues->Num(); ++ValueIndex)
			{
				FString NodeId;
				if (!(*ChainValues)[ValueIndex].IsValid() || !(*ChainValues)[ValueIndex]->TryGetString(NodeId))
				{
					OutError = FString::Printf(TEXT("Execution chain %d contains non-string node id at index %d."), ChainIndex, ValueIndex);
					return false;
				}
				Chain.Add(MoveTemp(NodeId));
			}
			OutBatchDefinition.ExecutionChains.Add(MoveTemp(Chain));
		}
	}

	return true;
}

void FBlueprintGraphAutomationService::MarkGraphEdit(UBlueprint* Blueprint, UEdGraph* Graph, const bool bStructuralChange, const bool bNotifyGraphChanged)
{
	if (FBlueprintGraphTransactionScope* ActiveScope = BlueprintGraphAutomationServicePrivate::GActiveScope)
	{
		if ((Blueprint == nullptr || ActiveScope->GetBlueprint() == Blueprint) &&
			(Graph == nullptr || ActiveScope->GetGraph() == Graph))
		{
			if (bStructuralChange)
			{
				ActiveScope->MarkStructuralChange();
			}
			else
			{
				ActiveScope->MarkModified();
			}

			if (bNotifyGraphChanged)
			{
				ActiveScope->RequestGraphNotification();
			}
			return;
		}
	}

	if (bNotifyGraphChanged && Graph)
	{
		Graph->NotifyGraphChanged();
	}

	if (Blueprint)
	{
		if (bStructuralChange)
		{
			FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
		}
		else
		{
			FBlueprintEditorUtils::MarkBlueprintAsModified(Blueprint);
		}
		Blueprint->MarkPackageDirty();
	}
}
