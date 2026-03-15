#include "BlueprintActionAutomationService.h"

#include "BlueprintGraphAutomationService.h"

#include "BlueprintActionDatabase.h"
#include "BlueprintActionFilter.h"
#include "BlueprintNodeSpawner.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "Engine/Blueprint.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/CompilerResultsLog.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Logging/LogMacros.h"
#include "Logging/TokenizedMessage.h"
#include "Policies/PrettyJsonPrintPolicy.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Templates/SharedPointer.h"
#include "UObject/Class.h"
#include "UObject/Object.h"
#include "UObject/ObjectKey.h"
#include "UObject/UObjectGlobals.h"
#include "UObject/UnrealType.h"

DEFINE_LOG_CATEGORY_STATIC(LogBlueprintActionAutomationEditor, Log, All);

namespace BlueprintActionAutomationServicePrivate
{
	struct FCachedBlueprintActionEntry
	{
		FString Signature;
		TWeakObjectPtr<UBlueprintNodeSpawner> Action;
		TWeakObjectPtr<UObject> ActionOwner;
	};

	static TMap<FString, FCachedBlueprintActionEntry> GIndexedActions;
	static bool bIndexInitialized = false;

	static FBlueprintActionIndexEntry BuildIndexEntry(
		UBlueprintNodeSpawner* Action,
		UObject* ActionOwner,
		UBlueprint* ContextBlueprint,
		UEdGraph* ContextGraph,
		const FBlueprintActionScanOptions* Options);
	static TSharedPtr<FJsonObject> BuildActionJsonObject(const FBlueprintActionIndexEntry& Entry);
	static TSharedPtr<FJsonObject> BuildCompileJson(const FBlueprintCompileReport& Report);
	static FBlueprintCompileReport BuildCompileReport(UBlueprint* Blueprint, const FCompilerResultsLog& ResultsLog);

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

	static void LogResult(const FBlueprintActionAutomationResult& Result)
	{
		const FString Prefix = FString::Printf(TEXT("[%s] "), *ResultCodeToString(Result.Code));
		if (Result.IsSuccess())
		{
			UE_LOG(LogBlueprintActionAutomationEditor, Display, TEXT("%s%s"), *Prefix, *Result.Message);
		}
		else
		{
			UE_LOG(LogBlueprintActionAutomationEditor, Error, TEXT("%s%s"), *Prefix, *Result.Message);
		}
	}

	static FString SeverityToString(const EMessageSeverity::Type Severity)
	{
		switch (Severity)
		{
		case EMessageSeverity::Error:
			return TEXT("error");
		case EMessageSeverity::PerformanceWarning:
			return TEXT("performance_warning");
		case EMessageSeverity::Warning:
			return TEXT("warning");
		case EMessageSeverity::Info:
			return TEXT("info");
		default:
			return TEXT("unknown");
		}
	}

	static FString BlueprintStatusToString(const EBlueprintStatus Status)
	{
		switch (Status)
		{
		case BS_Unknown:
			return TEXT("unknown");
		case BS_Dirty:
			return TEXT("dirty");
		case BS_Error:
			return TEXT("error");
		case BS_UpToDate:
			return TEXT("up_to_date");
		case BS_BeingCreated:
			return TEXT("being_created");
		case BS_UpToDateWithWarnings:
			return TEXT("up_to_date_with_warnings");
		default:
			return TEXT("unhandled");
		}
	}

	static FString SerializeJsonObject(const TSharedPtr<FJsonObject>& JsonObject)
	{
		FString Output;
		const TSharedRef<TJsonWriter<TCHAR, TPrettyJsonPrintPolicy<TCHAR>>> Writer =
			TJsonWriterFactory<TCHAR, TPrettyJsonPrintPolicy<TCHAR>>::Create(&Output);
		FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);
		return Output;
	}

	static TSharedPtr<FJsonObject> ParseJsonObject(const FString& JsonString)
	{
		TSharedPtr<FJsonObject> JsonObject;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonString);
		if (FJsonSerializer::Deserialize(Reader, JsonObject) && JsonObject.IsValid())
		{
			return JsonObject;
		}

		return MakeShared<FJsonObject>();
	}

	static TSharedPtr<FJsonObject> BuildCompileJson(UBlueprint* Blueprint, const FCompilerResultsLog& ResultsLog)
	{
		return BuildCompileJson(BuildCompileReport(Blueprint, ResultsLog));
	}

	static TSharedPtr<FJsonObject> BuildActionJsonObject(
		UBlueprintNodeSpawner* Action,
		UObject* ActionOwner,
		UBlueprint* ContextBlueprint,
		UEdGraph* ContextGraph,
		const FBlueprintActionScanOptions* Options)
	{
		return BuildActionJsonObject(BuildIndexEntry(Action, ActionOwner, ContextBlueprint, ContextGraph, Options));
	}

	static bool IsActionAllowedInContext(
		UBlueprintNodeSpawner* Action,
		UObject* ActionOwner,
		UBlueprint* Blueprint,
		UEdGraph* Graph)
	{
		if (!Action || (!Blueprint && !Graph))
		{
			return true;
		}

		FBlueprintActionFilter Filter;
		if (Blueprint)
		{
			Filter.Context.Blueprints.Add(Blueprint);
		}
		if (Graph)
		{
			Filter.Context.Graphs.Add(Graph);
		}

		FBlueprintActionInfo ActionInfo(ActionOwner, Action);
		return !Filter.IsFiltered(ActionInfo);
	}

	static EBlueprintActionScanMode GetEffectiveScanMode(const FBlueprintActionScanOptions& Options)
	{
		if (!Options.bContextSensitive || Options.ScanMode == EBlueprintActionScanMode::All)
		{
			return EBlueprintActionScanMode::All;
		}

		return EBlueprintActionScanMode::ContextSensitive;
	}

	static FString ScanModeToString(const EBlueprintActionScanMode ScanMode)
	{
		switch (ScanMode)
		{
		case EBlueprintActionScanMode::All:
			return TEXT("all");
		case EBlueprintActionScanMode::ContextSensitive:
		default:
			return TEXT("context_sensitive");
		}
	}

	static FBlueprintActionIndexPin BuildIndexPin(const FProperty* Property)
	{
		FBlueprintActionIndexPin Pin;
		if (!Property)
		{
			return Pin;
		}

		Pin.Name = Property->GetFName();
		Pin.Type = Property->GetCPPType();
		Pin.bIsArray = CastField<FArrayProperty>(Property) != nullptr;
		Pin.bIsSet = CastField<FSetProperty>(Property) != nullptr;
		Pin.bIsMap = CastField<FMapProperty>(Property) != nullptr;
		Pin.bIsReference = Property->HasAnyPropertyFlags(CPF_ReferenceParm);
		Pin.bIsConst = Property->HasAnyPropertyFlags(CPF_ConstParm);
		Pin.bIsReturnValue = Property->HasAnyPropertyFlags(CPF_ReturnParm);

		if (Pin.bIsReturnValue)
		{
			Pin.Direction = TEXT("return");
		}
		else if (Property->HasAnyPropertyFlags(CPF_OutParm) && !Property->HasAnyPropertyFlags(CPF_ConstParm))
		{
			Pin.Direction = TEXT("output");
		}
		else
		{
			Pin.Direction = TEXT("input");
		}

		return Pin;
	}

	static FBlueprintActionIndexEntry BuildIndexEntry(
		UBlueprintNodeSpawner* Action,
		UObject* ActionOwner,
		UBlueprint* ContextBlueprint,
		UEdGraph* ContextGraph,
		const FBlueprintActionScanOptions* Options)
	{
		FBlueprintActionIndexEntry Entry;
		if (!Action)
		{
			return Entry;
		}

		const FBlueprintNodeSignature Signature = Action->GetSpawnerSignature();
		Entry.SpawnerSignature = Signature.ToString();
		Entry.SignatureGuid = Signature.AsGuid().ToString(EGuidFormats::DigitsWithHyphensLower);
		Entry.SpawnerClassPath = Action->GetClass()->GetPathName();
		Entry.NodeClassPath = Action->NodeClass ? Action->NodeClass->GetPathName() : FString();
		Entry.ActionOwnerPath = ActionOwner ? ActionOwner->GetPathName() : FString();

		FBlueprintActionInfo ActionInfo(ActionOwner, Action);
		if (const UClass* OwnerClass = ActionInfo.GetOwnerClass())
		{
			Entry.OwnerClassPath = OwnerClass->GetPathName();
		}

		if (Options == nullptr || Options->bIncludeFunctionDetails)
		{
			if (const UFunction* Function = ActionInfo.GetAssociatedFunction())
			{
				Entry.FunctionPath = Function->GetPathName();

				for (TFieldIterator<FProperty> It(Function); It; ++It)
				{
					const FProperty* Property = *It;
					if (!Property || !Property->HasAnyPropertyFlags(CPF_Parm))
					{
						continue;
					}

					Entry.Pins.Add(BuildIndexPin(Property));
				}
			}
		}

		if (Options == nullptr || Options->bIncludePropertyDetails)
		{
			if (const FProperty* Property = ActionInfo.GetAssociatedProperty())
			{
				Entry.PropertyName = Property->GetName();
				Entry.PropertyCppType = Property->GetCPPType();
				Entry.PropertyOwnerClassPath = Property->GetOwnerClass() ? Property->GetOwnerClass()->GetPathName() : FString();
			}
		}

		if (Options == nullptr || Options->bIncludeUiSpec)
		{
			FBlueprintActionContext Context;
			if (ContextBlueprint)
			{
				Context.Blueprints.Add(ContextBlueprint);
			}
			if (ContextGraph)
			{
				Context.Graphs.Add(ContextGraph);
			}

			const FBlueprintActionUiSpec UiSpec = Action->GetUiSpec(Context, IBlueprintNodeBinder::FBindingSet());
			Entry.MenuName = UiSpec.MenuName.ToString();
			Entry.Category = UiSpec.Category.ToString();
			Entry.Tooltip = UiSpec.Tooltip.ToString();
			Entry.Keywords = UiSpec.Keywords.ToString();
			Entry.DocLink = UiSpec.DocLink;
			Entry.DocExcerptTag = UiSpec.DocExcerptTag;
		}

		return Entry;
	}

	static TSharedPtr<FJsonObject> BuildActionJsonObject(const FBlueprintActionIndexEntry& Entry)
	{
		TSharedPtr<FJsonObject> ActionObject = MakeShared<FJsonObject>();
		ActionObject->SetStringField(TEXT("signature"), Entry.SpawnerSignature);
		ActionObject->SetStringField(TEXT("signature_guid"), Entry.SignatureGuid);
		ActionObject->SetStringField(TEXT("spawner_class"), Entry.SpawnerClassPath);
		ActionObject->SetStringField(TEXT("node_class"), Entry.NodeClassPath);
		ActionObject->SetStringField(TEXT("action_owner"), Entry.ActionOwnerPath);
		ActionObject->SetStringField(TEXT("owner_class"), Entry.OwnerClassPath);
		ActionObject->SetStringField(TEXT("function_path"), Entry.FunctionPath);
		ActionObject->SetStringField(TEXT("property_name"), Entry.PropertyName);
		ActionObject->SetStringField(TEXT("property_cpp_type"), Entry.PropertyCppType);
		ActionObject->SetStringField(TEXT("property_owner_class"), Entry.PropertyOwnerClassPath);
		ActionObject->SetStringField(TEXT("menu_name"), Entry.MenuName);
		ActionObject->SetStringField(TEXT("category"), Entry.Category);
		ActionObject->SetStringField(TEXT("tooltip"), Entry.Tooltip);
		ActionObject->SetStringField(TEXT("keywords"), Entry.Keywords);
		ActionObject->SetStringField(TEXT("doc_link"), Entry.DocLink);
		ActionObject->SetStringField(TEXT("doc_excerpt_tag"), Entry.DocExcerptTag);

		TArray<TSharedPtr<FJsonValue>> PinArray;
		for (const FBlueprintActionIndexPin& Pin : Entry.Pins)
		{
			TSharedPtr<FJsonObject> PinObject = MakeShared<FJsonObject>();
			PinObject->SetStringField(TEXT("name"), Pin.Name.ToString());
			PinObject->SetStringField(TEXT("direction"), Pin.Direction);
			PinObject->SetStringField(TEXT("type"), Pin.Type);
			PinObject->SetBoolField(TEXT("is_array"), Pin.bIsArray);
			PinObject->SetBoolField(TEXT("is_set"), Pin.bIsSet);
			PinObject->SetBoolField(TEXT("is_map"), Pin.bIsMap);
			PinObject->SetBoolField(TEXT("is_reference"), Pin.bIsReference);
			PinObject->SetBoolField(TEXT("is_const"), Pin.bIsConst);
			PinObject->SetBoolField(TEXT("is_return_value"), Pin.bIsReturnValue);
			PinArray.Add(MakeShared<FJsonValueObject>(PinObject));
		}

		ActionObject->SetArrayField(TEXT("pins"), PinArray);
		return ActionObject;
	}

	static TSharedPtr<FJsonObject> BuildDocumentJson(const FBlueprintActionIndexDocument& Document)
	{
		TSharedPtr<FJsonObject> RootObject = MakeShared<FJsonObject>();
		RootObject->SetNumberField(TEXT("schema_version"), Document.SchemaVersion);
		RootObject->SetStringField(TEXT("blueprint_path"), Document.Context.BlueprintPath);
		RootObject->SetStringField(TEXT("graph_path"), Document.Context.GraphPath);
		RootObject->SetStringField(TEXT("scan_mode"), ScanModeToString(Document.Context.ScanMode));
		RootObject->SetNumberField(TEXT("count"), Document.Entries.Num());

		TArray<TSharedPtr<FJsonValue>> ActionArray;
		for (const FBlueprintActionIndexEntry& Entry : Document.Entries)
		{
			ActionArray.Add(MakeShared<FJsonValueObject>(BuildActionJsonObject(Entry)));
		}

		RootObject->SetArrayField(TEXT("actions"), ActionArray);
		return RootObject;
	}

	static TSharedPtr<FJsonObject> BuildCompileJson(const FBlueprintCompileReport& Report)
	{
		TSharedPtr<FJsonObject> CompileObject = MakeShared<FJsonObject>();
		CompileObject->SetStringField(TEXT("blueprint_path"), Report.BlueprintPath);
		CompileObject->SetStringField(TEXT("status"), Report.Status);
		CompileObject->SetNumberField(TEXT("num_errors"), Report.NumErrors);
		CompileObject->SetNumberField(TEXT("num_warnings"), Report.NumWarnings);

		TArray<TSharedPtr<FJsonValue>> MessageArray;
		for (const FBlueprintCompileMessage& Message : Report.Messages)
		{
			TSharedPtr<FJsonObject> MessageObject = MakeShared<FJsonObject>();
			MessageObject->SetStringField(TEXT("severity"), Message.Severity);
			MessageObject->SetStringField(TEXT("text"), Message.Text);
			MessageArray.Add(MakeShared<FJsonValueObject>(MessageObject));
		}

		CompileObject->SetArrayField(TEXT("messages"), MessageArray);
		return CompileObject;
	}

	static FBlueprintCompileReport BuildCompileReport(UBlueprint* Blueprint, const FCompilerResultsLog& ResultsLog)
	{
		FBlueprintCompileReport Report;
		Report.BlueprintPath = Blueprint ? Blueprint->GetPathName() : FString();
		Report.Status = Blueprint ? BlueprintStatusToString(Blueprint->Status) : FString();
		Report.NumErrors = ResultsLog.NumErrors;
		Report.NumWarnings = ResultsLog.NumWarnings;

		for (const TSharedRef<FTokenizedMessage>& Message : ResultsLog.Messages)
		{
			FBlueprintCompileMessage CompileMessage;
			CompileMessage.Severity = SeverityToString(Message->GetSeverity());
			CompileMessage.Text = Message->ToText().ToString();
			Report.Messages.Add(MoveTemp(CompileMessage));
		}

		return Report;
	}

	static bool DoesEntryMatchTextQuery(const FBlueprintActionIndexEntry& Entry, const FString& Query)
	{
		if (Query.IsEmpty())
		{
			return false;
		}

		const TArray<const FString*> SearchFields = {
			&Entry.SpawnerSignature,
			&Entry.MenuName,
			&Entry.Category,
			&Entry.Tooltip,
			&Entry.Keywords,
			&Entry.FunctionPath,
			&Entry.PropertyName,
			&Entry.PropertyCppType,
			&Entry.OwnerClassPath,
			&Entry.NodeClassPath,
			&Entry.ActionOwnerPath
		};

		for (const FString* Field : SearchFields)
		{
			if (Field && Field->Contains(Query, ESearchCase::IgnoreCase))
			{
				return true;
			}
		}

		for (const FBlueprintActionIndexPin& Pin : Entry.Pins)
		{
			if (Pin.Name.ToString().Contains(Query, ESearchCase::IgnoreCase) ||
				Pin.Type.Contains(Query, ESearchCase::IgnoreCase) ||
				Pin.Direction.Contains(Query, ESearchCase::IgnoreCase))
			{
				return true;
			}
		}

		return false;
	}
}

FBlueprintActionAutomationResult FBlueprintActionAutomationResult::Ok(
	const FString& InMessage,
	UBlueprint* InBlueprint,
	UEdGraph* InGraph,
	UEdGraphNode* InNode,
	UBlueprintNodeSpawner* InAction,
	const FString& InJsonPayload)
{
	FBlueprintActionAutomationResult Result;
	Result.Code = EBlueprintAutomationResultCode::Success;
	Result.Message = InMessage;
	Result.JsonPayload = InJsonPayload;
	Result.Blueprint = InBlueprint;
	Result.Graph = InGraph;
	Result.Node = InNode;
	Result.Action = InAction;
	BlueprintActionAutomationServicePrivate::LogResult(Result);
	return Result;
}

FBlueprintActionAutomationResult FBlueprintActionAutomationResult::Error(
	const EBlueprintAutomationResultCode InCode,
	const FString& InMessage,
	UBlueprint* InBlueprint,
	UEdGraph* InGraph,
	UEdGraphNode* InNode,
	UBlueprintNodeSpawner* InAction,
	const FString& InJsonPayload)
{
	FBlueprintActionAutomationResult Result;
	Result.Code = InCode;
	Result.Message = InMessage;
	Result.JsonPayload = InJsonPayload;
	Result.Blueprint = InBlueprint;
	Result.Graph = InGraph;
	Result.Node = InNode;
	Result.Action = InAction;
	BlueprintActionAutomationServicePrivate::LogResult(Result);
	return Result;
}

FBlueprintActionAutomationResult FBlueprintActionAutomationService::RefreshNodeIndex()
{
	FBlueprintActionDatabase::Get().RefreshAll();
	if (!EnsureActionIndex(true))
	{
		return FBlueprintActionAutomationResult::Error(
			EBlueprintAutomationResultCode::Failed,
			TEXT("Failed to rebuild Blueprint action index after RefreshAll()."));
	}

	TSharedPtr<FJsonObject> SummaryObject = MakeShared<FJsonObject>();
	SummaryObject->SetNumberField(TEXT("indexed_actions"), BlueprintActionAutomationServicePrivate::GIndexedActions.Num());

	return FBlueprintActionAutomationResult::Ok(
		FString::Printf(TEXT("Refreshed Blueprint action index with %d actions."), BlueprintActionAutomationServicePrivate::GIndexedActions.Num()),
		nullptr,
		nullptr,
		nullptr,
		nullptr,
		BlueprintActionAutomationServicePrivate::SerializeJsonObject(SummaryObject));
}

FBlueprintActionAutomationResult FBlueprintActionAutomationService::ScanAvailableBlueprintActions(
	UBlueprint* Blueprint,
	UEdGraph* Graph,
	const FBlueprintActionScanOptions& Options)
{
	FBlueprintActionScanOptions EffectiveOptions = Options;
	EffectiveOptions.ContextBlueprint = Blueprint ? Blueprint : Options.ContextBlueprint;
	EffectiveOptions.ContextGraph = Graph ? Graph : Options.ContextGraph;

	FBlueprintActionIndexDocument Document;
	FBlueprintActionAutomationResult ScanResult = ScanAvailableBlueprintActions(EffectiveOptions, Document);
	if (!ScanResult.IsSuccess())
	{
		return ScanResult;
	}

	FString Json;
	FBlueprintActionAutomationResult ExportResult = ExportBlueprintActionIndexToJson(Document, Json);
	if (!ExportResult.IsSuccess())
	{
		return ExportResult;
	}

	return FBlueprintActionAutomationResult::Ok(
		ScanResult.Message,
		ScanResult.Blueprint.Get(),
		ScanResult.Graph.Get(),
		nullptr,
		nullptr,
		Json);
}

FBlueprintActionAutomationResult FBlueprintActionAutomationService::ScanAvailableBlueprintActions(
	const FBlueprintActionScanOptions& Options,
	FBlueprintActionIndexDocument& OutDocument)
{
	OutDocument = FBlueprintActionIndexDocument();

	UBlueprint* Blueprint = ResolveBlueprintContext(Options.ContextBlueprint, Options.ContextGraph);
	UEdGraph* Graph = ResolveGraphContext(Blueprint, Options.ContextGraph);

	if (!EnsureActionIndex(false))
	{
		return FBlueprintActionAutomationResult::Error(
			EBlueprintAutomationResultCode::Failed,
			TEXT("Failed to initialize Blueprint action index."),
			Blueprint,
			Graph);
	}

	const EBlueprintActionScanMode EffectiveScanMode = BlueprintActionAutomationServicePrivate::GetEffectiveScanMode(Options);
	OutDocument.Context.BlueprintPath = Blueprint ? Blueprint->GetPathName() : FString();
	OutDocument.Context.GraphPath = Graph ? Graph->GetPathName() : FString();
	OutDocument.Context.ScanMode = EffectiveScanMode;

	TArray<FString> Signatures;
	BlueprintActionAutomationServicePrivate::GIndexedActions.GenerateKeyArray(Signatures);
	Signatures.Sort();

	for (const FString& Signature : Signatures)
	{
		const BlueprintActionAutomationServicePrivate::FCachedBlueprintActionEntry* Entry =
			BlueprintActionAutomationServicePrivate::GIndexedActions.Find(Signature);
		if (!Entry)
		{
			continue;
		}

		UBlueprintNodeSpawner* Action = Entry->Action.Get();
		if (!Action)
		{
			continue;
		}

		UObject* ActionOwner = Entry->ActionOwner.Get();
		if (EffectiveScanMode == EBlueprintActionScanMode::ContextSensitive &&
			!BlueprintActionAutomationServicePrivate::IsActionAllowedInContext(Action, ActionOwner, Blueprint, Graph))
		{
			continue;
		}

		OutDocument.Entries.Add(
			BlueprintActionAutomationServicePrivate::BuildIndexEntry(Action, ActionOwner, Blueprint, Graph, &Options));
	}

	return FBlueprintActionAutomationResult::Ok(
		FString::Printf(TEXT("Scanned %d Blueprint actions."), OutDocument.Entries.Num()),
		Blueprint,
		Graph);
}

FBlueprintActionAutomationResult FBlueprintActionAutomationService::ExportBlueprintActionIndexToJson()
{
	FBlueprintActionScanOptions Options;
	Options.bContextSensitive = false;
	Options.ScanMode = EBlueprintActionScanMode::All;

	FBlueprintActionIndexDocument Document;
	FBlueprintActionAutomationResult ScanResult = ScanAvailableBlueprintActions(Options, Document);
	if (!ScanResult.IsSuccess())
	{
		return ScanResult;
	}

	FString Json;
	FBlueprintActionAutomationResult ExportResult = ExportBlueprintActionIndexToJson(Document, Json);
	if (!ExportResult.IsSuccess())
	{
		return ExportResult;
	}

	return FBlueprintActionAutomationResult::Ok(
		ExportResult.Message,
		nullptr,
		nullptr,
		nullptr,
		nullptr,
		Json);
}

FBlueprintActionAutomationResult FBlueprintActionAutomationService::ExportBlueprintActionIndexToJson(
	const FBlueprintActionIndexDocument& Document,
	FString& OutJson)
{
	OutJson = BlueprintActionAutomationServicePrivate::SerializeJsonObject(
		BlueprintActionAutomationServicePrivate::BuildDocumentJson(Document));

	return FBlueprintActionAutomationResult::Ok(
		FString::Printf(TEXT("Exported Blueprint action index with %d actions."), Document.Entries.Num()),
		nullptr,
		nullptr,
		nullptr,
		nullptr,
		OutJson);
}

FBlueprintActionAutomationResult FBlueprintActionAutomationService::ResolveActionBySignature(const FString& ActionSignature)
{
	UBlueprintNodeSpawner* Action = FindActionBySignature(ActionSignature);
	if (!Action)
	{
		return FBlueprintActionAutomationResult::Error(
			EBlueprintAutomationResultCode::NotFound,
			FString::Printf(TEXT("Blueprint action '%s' was not found in the action index."), *ActionSignature));
	}

	const BlueprintActionAutomationServicePrivate::FCachedBlueprintActionEntry* Entry =
		BlueprintActionAutomationServicePrivate::GIndexedActions.Find(ActionSignature);

	const FBlueprintActionIndexEntry IndexEntry =
		BlueprintActionAutomationServicePrivate::BuildIndexEntry(
			Action,
			Entry ? Entry->ActionOwner.Get() : nullptr,
			nullptr,
			nullptr,
			nullptr);

	return FBlueprintActionAutomationResult::Ok(
		FString::Printf(TEXT("Resolved Blueprint action '%s'."), *ActionSignature),
		nullptr,
		nullptr,
		nullptr,
		Action,
		BlueprintActionAutomationServicePrivate::SerializeJsonObject(
			BlueprintActionAutomationServicePrivate::BuildActionJsonObject(IndexEntry)));
}

FBlueprintActionAutomationResult FBlueprintActionAutomationService::ResolveActionBySignature(
	const FBlueprintActionIndexDocument& Document,
	const FString& ActionSignature,
	FBlueprintActionIndexEntry& OutEntry)
{
	for (const FBlueprintActionIndexEntry& Entry : Document.Entries)
	{
		if (Entry.SpawnerSignature == ActionSignature)
		{
			OutEntry = Entry;
			return FBlueprintActionAutomationResult::Ok(
				FString::Printf(TEXT("Resolved Blueprint action '%s' from typed index."), *ActionSignature));
		}
	}

	return FBlueprintActionAutomationResult::Error(
		EBlueprintAutomationResultCode::NotFound,
		FString::Printf(TEXT("Blueprint action '%s' was not found in the typed action index."), *ActionSignature));
}

FBlueprintActionAutomationResult FBlueprintActionAutomationService::ResolveActionsByTextQuery(
	const FBlueprintActionIndexDocument& Document,
	const FString& TextQuery,
	TArray<FBlueprintActionIndexEntry>& OutEntries)
{
	OutEntries.Reset();

	if (TextQuery.TrimStartAndEnd().IsEmpty())
	{
		return FBlueprintActionAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Text query is empty."));
	}

	for (const FBlueprintActionIndexEntry& Entry : Document.Entries)
	{
		if (BlueprintActionAutomationServicePrivate::DoesEntryMatchTextQuery(Entry, TextQuery))
		{
			OutEntries.Add(Entry);
		}
	}

	return FBlueprintActionAutomationResult::Ok(
		FString::Printf(TEXT("Resolved %d Blueprint actions for query '%s'."), OutEntries.Num(), *TextQuery));
}

FBlueprintActionAutomationResult FBlueprintActionAutomationService::SpawnActionBySignature(
	UBlueprint* Blueprint,
	UEdGraph* Graph,
	const FString& ActionSignature,
	const FVector2D& NodePosition)
{
	Blueprint = ResolveBlueprintContext(Blueprint, Graph);
	Graph = ResolveGraphContext(Blueprint, Graph);

	if (!Graph)
	{
		return FBlueprintActionAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Graph is null and could not be resolved from the Blueprint."),
			Blueprint,
			Graph);
	}

	UBlueprintNodeSpawner* Action = FindActionBySignature(ActionSignature);
	if (!Action)
	{
		return FBlueprintActionAutomationResult::Error(
			EBlueprintAutomationResultCode::NotFound,
			FString::Printf(TEXT("Blueprint action '%s' was not found in the action index."), *ActionSignature),
			Blueprint,
			Graph);
	}

	const BlueprintActionAutomationServicePrivate::FCachedBlueprintActionEntry* Entry =
		BlueprintActionAutomationServicePrivate::GIndexedActions.Find(ActionSignature);
	UObject* ActionOwner = Entry ? Entry->ActionOwner.Get() : nullptr;

	if (!BlueprintActionAutomationServicePrivate::IsActionAllowedInContext(Action, ActionOwner, Blueprint, Graph))
	{
		return FBlueprintActionAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			FString::Printf(TEXT("Blueprint action '%s' is not allowed in graph '%s'."), *ActionSignature, *Graph->GetPathName()),
			Blueprint,
			Graph,
			nullptr,
			Action,
			BlueprintActionAutomationServicePrivate::SerializeJsonObject(
				BlueprintActionAutomationServicePrivate::BuildActionJsonObject(Action, ActionOwner, Blueprint, Graph, nullptr)));
	}

	const int32 NodeCountBefore = Graph->Nodes.Num();
	UEdGraphNode* SpawnedNode = Action->Invoke(Graph, IBlueprintNodeBinder::FBindingSet(), NodePosition);
	if (!SpawnedNode)
	{
		return FBlueprintActionAutomationResult::Error(
			EBlueprintAutomationResultCode::Failed,
			FString::Printf(TEXT("Action '%s' failed to spawn a node in graph '%s'."), *ActionSignature, *Graph->GetPathName()),
			Blueprint,
			Graph,
			nullptr,
			Action);
	}

	const bool bGraphChanged = Graph->Nodes.Num() > NodeCountBefore;
	if (bGraphChanged && Blueprint)
	{
		FBlueprintGraphTransactionScope Scope(Blueprint, Graph, FText::FromString(TEXT("Spawn Blueprint Action")));
		Scope.MarkStructuralChange();
		Scope.RequestGraphNotification();
	}

	TSharedPtr<FJsonObject> RootObject = MakeShared<FJsonObject>();
	RootObject->SetStringField(TEXT("action_signature"), ActionSignature);
	RootObject->SetBoolField(TEXT("graph_changed"), bGraphChanged);
	RootObject->SetStringField(TEXT("spawned_node_path"), SpawnedNode->GetPathName());
	RootObject->SetStringField(TEXT("spawned_node_class"), SpawnedNode->GetClass()->GetPathName());
	RootObject->SetStringField(TEXT("spawned_node_title"), SpawnedNode->GetNodeTitle(ENodeTitleType::ListView).ToString());

	return FBlueprintActionAutomationResult::Ok(
		FString::Printf(TEXT("Spawned action '%s' into graph '%s'."), *ActionSignature, *Graph->GetPathName()),
		Blueprint,
		Graph,
		SpawnedNode,
		Action,
		BlueprintActionAutomationServicePrivate::SerializeJsonObject(RootObject));
}

FBlueprintActionAutomationResult FBlueprintActionAutomationService::ValidateActionInContext(
	UBlueprint* Blueprint,
	UEdGraph* Graph,
	const FString& ActionSignature,
	bool& bOutIsAllowed)
{
	bOutIsAllowed = false;
	Blueprint = ResolveBlueprintContext(Blueprint, Graph);
	Graph = ResolveGraphContext(Blueprint, Graph);

	UBlueprintNodeSpawner* Action = FindActionBySignature(ActionSignature);
	if (!Action)
	{
		return FBlueprintActionAutomationResult::Error(
			EBlueprintAutomationResultCode::NotFound,
			FString::Printf(TEXT("Blueprint action '%s' was not found in the action index."), *ActionSignature),
			Blueprint,
			Graph);
	}

	const BlueprintActionAutomationServicePrivate::FCachedBlueprintActionEntry* Entry =
		BlueprintActionAutomationServicePrivate::GIndexedActions.Find(ActionSignature);
	bOutIsAllowed = BlueprintActionAutomationServicePrivate::IsActionAllowedInContext(
		Action,
		Entry ? Entry->ActionOwner.Get() : nullptr,
		Blueprint,
		Graph);

	return FBlueprintActionAutomationResult::Ok(
		FString::Printf(TEXT("Validated Blueprint action '%s' in current context: %s."), *ActionSignature, bOutIsAllowed ? TEXT("allowed") : TEXT("blocked")),
		Blueprint,
		Graph,
		nullptr,
		Action);
}

FBlueprintActionAutomationResult FBlueprintActionAutomationService::ValidateSpawnInSandboxBlueprint(
	const FString& ActionSignature,
	UClass* ParentClass,
	const FVector2D& NodePosition)
{
	if (!ParentClass)
	{
		ParentClass = AActor::StaticClass();
	}

	if (!FKismetEditorUtilities::CanCreateBlueprintOfClass(ParentClass))
	{
		return FBlueprintActionAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			FString::Printf(TEXT("Class '%s' does not support Blueprint creation for sandbox validation."), *ParentClass->GetPathName()));
	}

	const FName SandboxName = MakeUniqueObjectName(GetTransientPackage(), UBlueprint::StaticClass(), TEXT("BP_ActionSandbox"));
	UBlueprint* SandboxBlueprint = FKismetEditorUtilities::CreateBlueprint(
		ParentClass,
		GetTransientPackage(),
		SandboxName,
		EBlueprintType::BPTYPE_Normal,
		UBlueprint::StaticClass(),
		UBlueprintGeneratedClass::StaticClass(),
		TEXT("BlueprintAutomationEditor"));

	if (!SandboxBlueprint)
	{
		return FBlueprintActionAutomationResult::Error(
			EBlueprintAutomationResultCode::Failed,
			TEXT("Failed to create transient sandbox Blueprint."));
	}

	UEdGraph* EventGraph = ResolveGraphContext(SandboxBlueprint, nullptr);
	if (!EventGraph)
	{
		return FBlueprintActionAutomationResult::Error(
			EBlueprintAutomationResultCode::Failed,
			FString::Printf(TEXT("Failed to resolve EventGraph for sandbox Blueprint '%s'."), *SandboxBlueprint->GetPathName()),
			SandboxBlueprint);
	}

	FBlueprintActionAutomationResult SpawnResult =
		SpawnActionBySignature(SandboxBlueprint, EventGraph, ActionSignature, NodePosition);

	TSharedPtr<FJsonObject> RootObject = MakeShared<FJsonObject>();
	RootObject->SetStringField(TEXT("action_signature"), ActionSignature);
	RootObject->SetStringField(TEXT("sandbox_blueprint"), SandboxBlueprint->GetPathName());
	RootObject->SetStringField(TEXT("sandbox_parent_class"), ParentClass->GetPathName());
	RootObject->SetBoolField(TEXT("spawn_succeeded"), SpawnResult.IsSuccess());

	if (SpawnResult.IsSuccess())
	{
		RootObject->SetObjectField(TEXT("spawn"), BlueprintActionAutomationServicePrivate::ParseJsonObject(SpawnResult.JsonPayload));
		FBlueprintActionAutomationResult CompileResult = CompileBlueprintAndCollectMessages(SandboxBlueprint);
		RootObject->SetObjectField(TEXT("compile"), BlueprintActionAutomationServicePrivate::ParseJsonObject(CompileResult.JsonPayload));

		return FBlueprintActionAutomationResult::Ok(
			FString::Printf(TEXT("Validated action '%s' in sandbox Blueprint '%s'."), *ActionSignature, *SandboxBlueprint->GetPathName()),
			SandboxBlueprint,
			EventGraph,
			SpawnResult.Node.Get(),
			SpawnResult.Action.Get(),
			BlueprintActionAutomationServicePrivate::SerializeJsonObject(RootObject));
	}

	if (!SpawnResult.JsonPayload.IsEmpty())
	{
		RootObject->SetObjectField(TEXT("spawn"), BlueprintActionAutomationServicePrivate::ParseJsonObject(SpawnResult.JsonPayload));
	}

	return FBlueprintActionAutomationResult::Error(
		SpawnResult.Code,
		FString::Printf(TEXT("Sandbox validation failed for action '%s': %s"), *ActionSignature, *SpawnResult.Message),
		SandboxBlueprint,
		EventGraph,
		nullptr,
		SpawnResult.Action.Get(),
		BlueprintActionAutomationServicePrivate::SerializeJsonObject(RootObject));
}

FBlueprintActionAutomationResult FBlueprintActionAutomationService::CompileBlueprintAndCollectMessages(
	UBlueprint* Blueprint,
	const EBlueprintCompileOptions CompileOptions)
{
	FBlueprintCompileReport Report;
	FBlueprintActionAutomationResult Result = CompileBlueprintAndCollectMessages(Blueprint, Report, CompileOptions);
	if (!Result.IsSuccess())
	{
		return Result;
	}

	return FBlueprintActionAutomationResult::Ok(
		Result.Message,
		Result.Blueprint.Get(),
		nullptr,
		nullptr,
		nullptr,
		Result.JsonPayload);
}

FBlueprintActionAutomationResult FBlueprintActionAutomationService::CompileBlueprintAndCollectMessages(
	UBlueprint* Blueprint,
	FBlueprintCompileReport& OutReport,
	const EBlueprintCompileOptions CompileOptions)
{
	OutReport = FBlueprintCompileReport();

	if (!Blueprint)
	{
		return FBlueprintActionAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Blueprint is null."));
	}

	FCompilerResultsLog ResultsLog;
	ResultsLog.SetSourcePath(Blueprint->GetPathName());

	FKismetEditorUtilities::CompileBlueprint(Blueprint, CompileOptions, &ResultsLog);
	OutReport = BlueprintActionAutomationServicePrivate::BuildCompileReport(Blueprint, ResultsLog);

	return FBlueprintActionAutomationResult::Ok(
		FString::Printf(TEXT("Compiled Blueprint '%s' and collected %d messages."), *Blueprint->GetPathName(), ResultsLog.Messages.Num()),
		Blueprint,
		nullptr,
		nullptr,
		nullptr,
		BlueprintActionAutomationServicePrivate::SerializeJsonObject(
			BlueprintActionAutomationServicePrivate::BuildCompileJson(OutReport)));
}

UBlueprint* FBlueprintActionAutomationService::ResolveBlueprintContext(UBlueprint* ExplicitBlueprint, UEdGraph* Graph)
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

UEdGraph* FBlueprintActionAutomationService::ResolveGraphContext(UBlueprint* Blueprint, UEdGraph* ExplicitGraph)
{
	if (ExplicitGraph)
	{
		return ExplicitGraph;
	}

	if (!Blueprint)
	{
		return nullptr;
	}

	return FBlueprintEditorUtils::FindEventGraph(Blueprint);
}

UBlueprintNodeSpawner* FBlueprintActionAutomationService::FindActionBySignature(const FString& ActionSignature)
{
	if (!EnsureActionIndex(false))
	{
		return nullptr;
	}

	if (BlueprintActionAutomationServicePrivate::FCachedBlueprintActionEntry* Entry =
		BlueprintActionAutomationServicePrivate::GIndexedActions.Find(ActionSignature))
	{
		if (UBlueprintNodeSpawner* Action = Entry->Action.Get())
		{
			return Action;
		}
	}

	if (!EnsureActionIndex(true))
	{
		return nullptr;
	}

	if (BlueprintActionAutomationServicePrivate::FCachedBlueprintActionEntry* Entry =
		BlueprintActionAutomationServicePrivate::GIndexedActions.Find(ActionSignature))
	{
		return Entry->Action.Get();
	}

	return nullptr;
}

bool FBlueprintActionAutomationService::EnsureActionIndex(const bool bForceRefresh)
{
	if (BlueprintActionAutomationServicePrivate::bIndexInitialized && !bForceRefresh)
	{
		return true;
	}

	if (bForceRefresh)
	{
		BlueprintActionAutomationServicePrivate::GIndexedActions.Reset();
	}

	const FBlueprintActionDatabase::FActionRegistry& ActionRegistry = FBlueprintActionDatabase::Get().GetAllActions();
	for (const TPair<FObjectKey, FBlueprintActionDatabase::FActionList>& Pair : ActionRegistry)
	{
		UObject* ActionOwner = Pair.Key.ResolveObjectPtr();
		for (UBlueprintNodeSpawner* Action : Pair.Value)
		{
			if (!Action)
			{
				continue;
			}

			const FString Signature = Action->GetSpawnerSignature().ToString();
			if (Signature.IsEmpty())
			{
				continue;
			}

			BlueprintActionAutomationServicePrivate::FCachedBlueprintActionEntry& Entry =
				BlueprintActionAutomationServicePrivate::GIndexedActions.FindOrAdd(Signature);
			Entry.Signature = Signature;
			Entry.Action = Action;
			Entry.ActionOwner = ActionOwner;
		}
	}

	BlueprintActionAutomationServicePrivate::bIndexInitialized = true;
	return BlueprintActionAutomationServicePrivate::GIndexedActions.Num() > 0;
}
