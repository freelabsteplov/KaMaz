#pragma once

#include "BlueprintAutomationService.h"

#include "CoreMinimal.h"

class UBlueprint;
class UEdGraph;
class UEdGraphNode;
class UEdGraphPin;
class UFunction;
class UClass;
class FProperty;

class BLUEPRINTAUTOMATIONEDITOR_API FBlueprintGraphTransactionScope final
{
public:
	FBlueprintGraphTransactionScope(UBlueprint* InBlueprint, UEdGraph* InGraph, const FText& InTransactionText);
	~FBlueprintGraphTransactionScope();

	void MarkStructuralChange();
	void MarkModified();
	void RequestGraphNotification();

	UBlueprint* GetBlueprint() const { return Blueprint; }
	UEdGraph* GetGraph() const { return Graph; }

private:
	TUniquePtr<class FScopedTransaction> Transaction;
	TObjectPtr<UBlueprint> Blueprint = nullptr;
	TObjectPtr<UEdGraph> Graph = nullptr;
	FBlueprintGraphTransactionScope* PreviousScope = nullptr;
	bool bStructuralChange = false;
	bool bModified = false;
	bool bNotifyGraphChanged = false;
};

struct FBlueprintCustomEventPinDefinition
{
	FName Name = NAME_None;
	EBlueprintPrimitiveVariableType Type = EBlueprintPrimitiveVariableType::Float;
	FString DefaultValue;
};

struct FBlueprintGraphBatchPinDefaultDefinition
{
	FName PinName = NAME_None;
	FString DefaultValue;
	FString DefaultObjectPath;
	FString DefaultText;
};

enum class EBlueprintGraphBatchNodeKind : uint8
{
	CustomEvent,
	CustomEventFromSignature,
	EventBySignature,
	ActionBySignature,
	CallFunction,
	DynamicCast,
	VariableGet,
	VariableSet
};

struct FBlueprintGraphBatchNodeDefinition
{
	FString Id;
	EBlueprintGraphBatchNodeKind Kind = EBlueprintGraphBatchNodeKind::CallFunction;
	FString Name;
	FString OwnerClassPath;
	FString TargetClassPath;
	FString FunctionPath;
	FString ActionSignature;
	FName FunctionName = NAME_None;
	FName VariableName = NAME_None;
	FVector2D Position = FVector2D::ZeroVector;
	bool bPure = true;
	TArray<FBlueprintCustomEventPinDefinition> Pins;
	TArray<FBlueprintGraphBatchPinDefaultDefinition> PinDefaults;
};

struct FBlueprintGraphBatchLinkDefinition
{
	FString FromNodeId;
	FString FromNodeName;
	FString FromNodePath;
	FName FromPinName = NAME_None;
	FString ToNodeId;
	FString ToNodeName;
	FString ToNodePath;
	FName ToPinName = NAME_None;
};

struct FBlueprintGraphBatchDefinition
{
	TArray<FBlueprintGraphBatchNodeDefinition> Nodes;
	TArray<FBlueprintGraphBatchLinkDefinition> Links;
	TArray<TArray<FString>> ExecutionChains;
};

struct FBlueprintGraphAutomationResult
{
	EBlueprintAutomationResultCode Code = EBlueprintAutomationResultCode::Failed;
	FString Message;
	FString JsonPayload;
	TObjectPtr<UBlueprint> Blueprint = nullptr;
	TObjectPtr<UEdGraph> Graph = nullptr;
	TObjectPtr<UEdGraphNode> Node = nullptr;
	UEdGraphPin* Pin = nullptr;

	bool IsSuccess() const
	{
		return Code == EBlueprintAutomationResultCode::Success;
	}

	static FBlueprintGraphAutomationResult Ok(
		const FString& InMessage,
		UBlueprint* InBlueprint = nullptr,
		UEdGraph* InGraph = nullptr,
		UEdGraphNode* InNode = nullptr,
		UEdGraphPin* InPin = nullptr,
		const FString& InJsonPayload = FString());

	static FBlueprintGraphAutomationResult Error(
		EBlueprintAutomationResultCode InCode,
		const FString& InMessage,
		UBlueprint* InBlueprint = nullptr,
		UEdGraph* InGraph = nullptr,
		UEdGraphNode* InNode = nullptr,
		UEdGraphPin* InPin = nullptr,
		const FString& InJsonPayload = FString());
};

class BLUEPRINTAUTOMATIONEDITOR_API FBlueprintGraphAutomationService final
{
public:
	static FBlueprintGraphAutomationResult GetEventGraph(UBlueprint* Blueprint);
	static FBlueprintGraphAutomationResult GetGraphByName(UBlueprint* Blueprint, const FName GraphName);

	static FBlueprintGraphAutomationResult CreateCallFunctionNode(
		UEdGraph* Graph,
		const UFunction* Function,
		const FVector2D& NodePosition);

	static FBlueprintGraphAutomationResult CreateCallFunctionNodeByName(
		UEdGraph* Graph,
		UClass* FunctionOwnerClass,
		const FName FunctionName,
		const FVector2D& NodePosition);

	static FBlueprintGraphAutomationResult CreateCustomEventNode(
		UEdGraph* Graph,
		const FString& EventName,
		const FVector2D& NodePosition);

	static FBlueprintGraphAutomationResult CreateCustomEventNodeWithPins(
		UEdGraph* Graph,
		const FString& EventName,
		const TArray<FBlueprintCustomEventPinDefinition>& Pins,
		const FVector2D& NodePosition);

	static FBlueprintGraphAutomationResult CreateCustomEventNodeFromSignature(
		UEdGraph* Graph,
		const FString& EventName,
		const UFunction* SignatureFunction,
		const FVector2D& NodePosition);

	static FBlueprintGraphAutomationResult SpawnEventNodeBySignature(
		UEdGraph* Graph,
		const UFunction* SignatureFunction,
		const FVector2D& NodePosition);

	static FBlueprintGraphAutomationResult SpawnEventNodeBySignatureName(
		UEdGraph* Graph,
		UClass* FunctionOwnerClass,
		const FName FunctionName,
		const FVector2D& NodePosition);

	static FBlueprintGraphAutomationResult CreateVariableGetNode(
		UBlueprint* Blueprint,
		UEdGraph* Graph,
		const FName VariableName,
		const FVector2D& NodePosition,
		const bool bIsPure = true,
		const FString& OwnerClassPath = FString());

	static FBlueprintGraphAutomationResult CreateVariableSetNode(
		UBlueprint* Blueprint,
		UEdGraph* Graph,
		const FName VariableName,
		const FVector2D& NodePosition,
		const FString& OwnerClassPath = FString());

	static FBlueprintGraphAutomationResult CreateDynamicCastNode(
		UEdGraph* Graph,
		const FString& TargetClassPath,
		const FVector2D& NodePosition,
		const bool bPure = false);

	static FBlueprintGraphAutomationResult FindPin(UEdGraphNode* Node, const FName PinName);
	static FBlueprintGraphAutomationResult FindPinByDirection(UEdGraphNode* Node, const FName PinName, EEdGraphPinDirection Direction);

	static FBlueprintGraphAutomationResult LinkPins(UEdGraphPin* OutputPin, UEdGraphPin* InputPin);
	static FBlueprintGraphAutomationResult LinkPinsByName(
		UEdGraphNode* FromNode,
		const FName FromPinName,
		UEdGraphNode* ToNode,
		const FName ToPinName);

	static FBlueprintGraphAutomationResult CreateExecutionChain(const TArray<UEdGraphNode*>& ExecNodes);

	static FBlueprintGraphAutomationResult InspectNodeToJson(UEdGraphNode* Node, bool bIncludeLinkedPins = true);
	static FBlueprintGraphAutomationResult InspectGraphToJson(UEdGraph* Graph, bool bIncludePins = true, bool bIncludeLinkedPins = true);

	static FBlueprintGraphAutomationResult ResolveFunctionByPath(const FString& FunctionPath);
	static FBlueprintGraphAutomationResult ResolveVariableByName(UBlueprint* Blueprint, const FName VariableName, bool bCompileIfNeeded = true);

	static FBlueprintGraphAutomationResult ApplyBatchDefinition(
		UBlueprint* Blueprint,
		UEdGraph* Graph,
		const FBlueprintGraphBatchDefinition& BatchDefinition);

	static FBlueprintGraphAutomationResult ApplyBatchJson(
		UBlueprint* Blueprint,
		UEdGraph* Graph,
		const FString& BatchJson);

private:
	static UBlueprint* ResolveOwningBlueprint(UBlueprint* ExplicitBlueprint, UEdGraph* Graph);
	static UClass* ResolveClassByPath(const FString& ClassPath);
	static const UFunction* ResolveFunctionInternal(const FString& FunctionPath, FString& OutError);
	static FProperty* ResolveVariableProperty(UBlueprint* Blueprint, const FName VariableName, bool bCompileIfNeeded);
	static FProperty* ResolveVariableProperty(
		UBlueprint* Blueprint,
		const FString& OwnerClassPath,
		const FName VariableName,
		bool bCompileIfNeeded,
		UClass*& OutOwnerClass,
		bool& bOutIsSelfContext);
	static const FBPVariableDescription* FindVariableDescription(const UBlueprint* Blueprint, const FName VariableName);
	static UObject* ResolveObjectByPath(const FString& ObjectPath);
	static FBlueprintGraphAutomationResult ApplyPinDefaults(
		UBlueprint* Blueprint,
		UEdGraph* Graph,
		UEdGraphNode* Node,
		const TArray<FBlueprintGraphBatchPinDefaultDefinition>& PinDefaults);
	static FEdGraphPinType MakeEventPinType(EBlueprintPrimitiveVariableType Type);
	static FString SerializeFunctionToJson(const UFunction* Function);
	static FString SerializeVariableToJson(UBlueprint* Blueprint, const FBPVariableDescription* VariableDescription, const FProperty* VariableProperty);
	static bool TryParseBatchJson(const FString& BatchJson, FBlueprintGraphBatchDefinition& OutBatchDefinition, FString& OutError);
	static void MarkGraphEdit(UBlueprint* Blueprint, UEdGraph* Graph, bool bStructuralChange, bool bNotifyGraphChanged = true);
};
