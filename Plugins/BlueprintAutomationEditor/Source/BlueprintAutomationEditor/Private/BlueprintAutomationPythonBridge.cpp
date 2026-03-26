#include "BlueprintAutomationPythonBridge.h"

#include "BlueprintActionAutomationService.h"
#include "BlueprintAutomationService.h"
#include "BlueprintAutomationSmokeTest.h"
#include "BlueprintGraphAutomationService.h"

#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "Engine/Blueprint.h"
#include "Engine/Level.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/Actor.h"
#include "Dom/JsonObject.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Snow/PersistentSnowStateTypes.h"
#include "Snow/SnowReceiverSurfaceComponent.h"
#include "UObject/UnrealType.h"

class ULevel;

namespace BlueprintAutomationPythonBridgePrivate
{
	struct FSnowReceiverAttachActorResult
	{
		FString ActorPath;
		bool bFound = false;
		bool bCreatedComponent = false;
		FString CreationDetail;
		FString ComponentPath;
		bool bParticipatesInPersistentSnowState = false;
		FString SurfaceFamily;
		int32 ReceiverPriority = 0;
		FString ReceiverSetTag;
		int32 NumComponentsAfter = 0;
	};

	struct FSnowReceiverAttachBatchResult
	{
		bool bSuccess = false;
		FString MapPath;
		int32 CreatedCount = 0;
		int32 ConfiguredCount = 0;
		bool bSavedCurrentLevel = false;
		TArray<FSnowReceiverAttachActorResult> PerActorResults;
		TArray<FSnowReceiverAttachActorResult> VerificationResults;
	};

	static bool LoadBlueprint(const FString& BlueprintAssetPath, UBlueprint*& OutBlueprint, FString& OutSummary)
	{
		OutBlueprint = nullptr;

		const FBlueprintAutomationResult LoadResult =
			FBlueprintAutomationService::LoadBlueprintByAssetPath(BlueprintAssetPath);
		if (!LoadResult.IsSuccess() || !LoadResult.Blueprint)
		{
			OutSummary = FString::Printf(
				TEXT("LoadBlueprintByAssetPath failed for '%s': %s"),
				*BlueprintAssetPath,
				*LoadResult.Message);
			return false;
		}

		OutBlueprint = LoadResult.Blueprint.Get();
		OutSummary = LoadResult.Message;
		return true;
	}

	static bool ResolveEventGraph(UBlueprint* Blueprint, UEdGraph*& OutGraph, FString& OutSummary)
	{
		OutGraph = nullptr;

		const FBlueprintGraphAutomationResult GraphResult =
			FBlueprintGraphAutomationService::GetEventGraph(Blueprint);
		if (!GraphResult.IsSuccess() || !GraphResult.Graph)
		{
			OutSummary = FString::Printf(TEXT("GetEventGraph failed: %s"), *GraphResult.Message);
			return false;
		}

		OutGraph = GraphResult.Graph.Get();
		OutSummary = GraphResult.Message;
		return true;
	}

	static bool ResolveGraphByName(UBlueprint* Blueprint, const FString& GraphName, UEdGraph*& OutGraph, FString& OutSummary)
	{
		OutGraph = nullptr;

		const FBlueprintGraphAutomationResult GraphResult =
			FBlueprintGraphAutomationService::GetGraphByName(Blueprint, FName(*GraphName));
		if (!GraphResult.IsSuccess() || !GraphResult.Graph)
		{
			OutSummary = FString::Printf(TEXT("GetGraphByName failed: %s"), *GraphResult.Message);
			return false;
		}

		OutGraph = GraphResult.Graph.Get();
		OutSummary = GraphResult.Message;
		return true;
	}

	static AActor* FindActorByObjectPath(const FString& ActorObjectPath)
	{
		if (ActorObjectPath.IsEmpty())
		{
			return nullptr;
		}

		if (AActor* DirectActor = FindObject<AActor>(nullptr, *ActorObjectPath))
		{
			return DirectActor;
		}

		for (TObjectIterator<AActor> It; It; ++It)
		{
			if (It->GetPathName() == ActorObjectPath)
			{
				return *It;
			}
		}

		return nullptr;
	}

	static USnowReceiverSurfaceComponent* FindSnowReceiverComponent(AActor* Actor)
	{
		return Actor ? Actor->FindComponentByClass<USnowReceiverSurfaceComponent>() : nullptr;
	}

	static FString SurfaceFamilyToString(const ESnowReceiverSurfaceFamily SurfaceFamily)
	{
		if (const UEnum* Enum = StaticEnum<ESnowReceiverSurfaceFamily>())
		{
			return Enum->GetNameStringByValue(static_cast<int64>(SurfaceFamily));
		}

		return TEXT("Unknown");
	}

	static FSnowReceiverAttachActorResult MakeActorSnapshot(AActor* Actor, const FString& ActorPath)
	{
		FSnowReceiverAttachActorResult Snapshot;
		Snapshot.ActorPath = ActorPath;
		Snapshot.bFound = (Actor != nullptr);

		if (USnowReceiverSurfaceComponent* Component = FindSnowReceiverComponent(Actor))
		{
			Snapshot.ComponentPath = Component->GetPathName();
			Snapshot.bParticipatesInPersistentSnowState = Component->bParticipatesInPersistentSnowState;
			Snapshot.SurfaceFamily = SurfaceFamilyToString(Component->SurfaceFamily);
			Snapshot.ReceiverPriority = Component->ReceiverPriority;
			Snapshot.ReceiverSetTag = Component->ReceiverSetTag.ToString();

			TInlineComponentArray<USnowReceiverSurfaceComponent*> Components;
			Actor->GetComponents(Components);
			Snapshot.NumComponentsAfter = Components.Num();
		}

		return Snapshot;
	}

	static USnowReceiverSurfaceComponent* AttachSnowReceiverComponent(
		AActor* Actor,
		bool& bOutCreatedComponent,
		FString& OutCreationDetail)
	{
		bOutCreatedComponent = false;
		OutCreationDetail = TEXT("ActorNotFound");
		if (!Actor)
		{
			return nullptr;
		}

		if (USnowReceiverSurfaceComponent* Existing = FindSnowReceiverComponent(Actor))
		{
			OutCreationDetail = TEXT("ExistingComponent");
			return Existing;
		}

		Actor->Modify();
		if (ULevel* Level = Actor->GetLevel())
		{
			Level->Modify();
		}

		const FTransform IdentityTransform = FTransform::Identity;
		if (UActorComponent* AddedComponent = Actor->AddComponentByClass(
			USnowReceiverSurfaceComponent::StaticClass(),
			false,
			IdentityTransform,
			false))
		{
			if (USnowReceiverSurfaceComponent* SnowComponent = Cast<USnowReceiverSurfaceComponent>(AddedComponent))
			{
				SnowComponent->SetFlags(RF_Transactional | RF_Public);
				SnowComponent->Modify();
				SnowComponent->CreationMethod = EComponentCreationMethod::Instance;
				bOutCreatedComponent = true;
				OutCreationDetail = TEXT("AddComponentByClass");
				return SnowComponent;
			}
		}

		const FName ComponentName = MakeUniqueObjectName(
			Actor,
			USnowReceiverSurfaceComponent::StaticClass(),
			*FString::Printf(TEXT("SnowReceiverSurface_%s"), *Actor->GetName()));
		USnowReceiverSurfaceComponent* FallbackComponent = NewObject<USnowReceiverSurfaceComponent>(
			Actor,
			USnowReceiverSurfaceComponent::StaticClass(),
			ComponentName,
			RF_Transactional | RF_Public);
		if (!FallbackComponent)
		{
			OutCreationDetail = TEXT("NewObjectFailed");
			return nullptr;
		}

		Actor->AddInstanceComponent(FallbackComponent);
		Actor->AddOwnedComponent(FallbackComponent);
		FallbackComponent->CreationMethod = EComponentCreationMethod::Instance;
		FallbackComponent->OnComponentCreated();
		FallbackComponent->RegisterComponent();
		FallbackComponent->Modify();

		bOutCreatedComponent = true;
		OutCreationDetail = TEXT("NewObjectFallback");
		return FallbackComponent;
	}

	static void ConfigureSnowReceiverComponent(
		USnowReceiverSurfaceComponent* Component,
		const ESnowReceiverSurfaceFamily SurfaceFamily,
		const int32 ReceiverPriority,
		const FString& ReceiverSetTag)
	{
		if (!Component)
		{
			return;
		}

		Component->Modify();
		Component->bParticipatesInPersistentSnowState = true;
		Component->SurfaceFamily = SurfaceFamily;
		Component->ReceiverPriority = ReceiverPriority;
		Component->ReceiverSetTag = FName(*ReceiverSetTag);
		Component->MarkPackageDirty();
	}

	static void MarkActorAndLevelDirty(AActor* Actor)
	{
		if (!Actor)
		{
			return;
		}

		Actor->Modify();
		Actor->MarkPackageDirty();

		if (ULevel* Level = Actor->GetLevel())
		{
			Level->Modify();
			Level->MarkPackageDirty();
			if (UPackage* Package = Level->GetPackage())
			{
				Package->MarkPackageDirty();
			}
		}
	}

	static TSharedPtr<FJsonObject> ActorResultToJson(const FSnowReceiverAttachActorResult& Result)
	{
		TSharedPtr<FJsonObject> JsonObject = MakeShared<FJsonObject>();
		JsonObject->SetStringField(TEXT("actor_path"), Result.ActorPath);
		JsonObject->SetBoolField(TEXT("found"), Result.bFound);
		JsonObject->SetBoolField(TEXT("created_component"), Result.bCreatedComponent);
		JsonObject->SetStringField(TEXT("creation_detail"), Result.CreationDetail);
		JsonObject->SetStringField(TEXT("component_path"), Result.ComponentPath);
		JsonObject->SetBoolField(TEXT("participates_in_persistent_snow_state"), Result.bParticipatesInPersistentSnowState);
		JsonObject->SetStringField(TEXT("surface_family"), Result.SurfaceFamily);
		JsonObject->SetNumberField(TEXT("receiver_priority"), Result.ReceiverPriority);
		JsonObject->SetStringField(TEXT("receiver_set_tag"), Result.ReceiverSetTag);
		JsonObject->SetNumberField(TEXT("num_components_after"), Result.NumComponentsAfter);
		return JsonObject;
	}

	static FString BatchResultToJsonString(const FSnowReceiverAttachBatchResult& Result)
	{
		TSharedPtr<FJsonObject> RootObject = MakeShared<FJsonObject>();
		RootObject->SetBoolField(TEXT("success"), Result.bSuccess);
		RootObject->SetStringField(TEXT("map_path"), Result.MapPath);
		RootObject->SetNumberField(TEXT("created_count"), Result.CreatedCount);
		RootObject->SetNumberField(TEXT("configured_count"), Result.ConfiguredCount);
		RootObject->SetBoolField(TEXT("saved_current_level"), Result.bSavedCurrentLevel);

		TArray<TSharedPtr<FJsonValue>> PerActorValues;
		for (const FSnowReceiverAttachActorResult& Item : Result.PerActorResults)
		{
			PerActorValues.Add(MakeShared<FJsonValueObject>(ActorResultToJson(Item)));
		}
		RootObject->SetArrayField(TEXT("per_actor_results"), PerActorValues);

		TArray<TSharedPtr<FJsonValue>> VerificationValues;
		for (const FSnowReceiverAttachActorResult& Item : Result.VerificationResults)
		{
			VerificationValues.Add(MakeShared<FJsonValueObject>(ActorResultToJson(Item)));
		}
		RootObject->SetArrayField(TEXT("verification"), VerificationValues);

		FString JsonString;
		const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&JsonString);
		FJsonSerializer::Serialize(RootObject.ToSharedRef(), Writer);
		return JsonString;
	}

	struct FBlueprintPropertySetResult
	{
		bool bSuccess = false;
		FString BlueprintAssetPath;
		FString TargetMode;
		FString TargetObjectPath;
		FString ComponentName;
		FString PropertyName;
		FString ValueAsString;
		FString PropertyClass;
		FString BeforeValue;
		FString AfterValue;
		bool bCompiled = false;
		bool bSaved = false;
		FString CompileSummary;
		FString SaveSummary;
		FString Error;
	};

	struct FBlueprintPropertyBatchEntry
	{
		FString PropertyName;
		FString ValueAsString;
		FString PropertyClass;
		FString BeforeValue;
		FString AfterValue;
		bool bApplied = false;
		FString Error;
	};

	static FString NormalizeComponentNodeName(FString Name)
	{
		Name.TrimStartAndEndInline();
		static const FString GenVariableSuffix = TEXT("_GEN_VARIABLE");
		if (Name.EndsWith(GenVariableSuffix))
		{
			Name.LeftChopInline(GenVariableSuffix.Len(), EAllowShrinking::No);
		}
		return Name;
	}

	static USCS_Node* FindComponentNodeByName(const UBlueprint* Blueprint, const FName ComponentName)
	{
		if (!Blueprint || !Blueprint->SimpleConstructionScript)
		{
			return nullptr;
		}

		const FString RequestedName = ComponentName.ToString();
		const FString NormalizedRequestedName = NormalizeComponentNodeName(RequestedName);

		for (USCS_Node* Node : Blueprint->SimpleConstructionScript->GetAllNodes())
		{
			if (!Node)
			{
				continue;
			}

			const FString NodeVariableName = Node->GetVariableName().ToString();
			const FString NodeName = Node->GetName();
			const FString NormalizedVariableName = NormalizeComponentNodeName(NodeVariableName);
			const FString NormalizedNodeName = NormalizeComponentNodeName(NodeName);
			const FString TemplateName = Node->ComponentTemplate ? Node->ComponentTemplate->GetName() : FString();
			const FString NormalizedTemplateName = NormalizeComponentNodeName(TemplateName);

			if (Node->GetVariableName() == ComponentName
				|| NodeName == RequestedName
				|| NormalizedVariableName == NormalizedRequestedName
				|| NormalizedNodeName == NormalizedRequestedName
				|| (!NormalizedTemplateName.IsEmpty() && NormalizedTemplateName == NormalizedRequestedName))
			{
				return Node;
			}
		}

		return nullptr;
	}

	static FString PropertyValueToString(FProperty* Property, const UObject* Container)
	{
		if (!Property || !Container)
		{
			return FString();
		}

		if (const FObjectPropertyBase* ObjectProperty = CastField<FObjectPropertyBase>(Property))
		{
			if (const UObject* Value = ObjectProperty->GetObjectPropertyValue_InContainer(Container))
			{
				return Value->GetPathName();
			}
			return FString();
		}

		if (const FBoolProperty* BoolProperty = CastField<FBoolProperty>(Property))
		{
			return BoolProperty->GetPropertyValue_InContainer(Container) ? TEXT("true") : TEXT("false");
		}

		if (const FNumericProperty* NumericProperty = CastField<FNumericProperty>(Property))
		{
			if (NumericProperty->IsInteger())
			{
				return FString::Printf(TEXT("%lld"), NumericProperty->GetSignedIntPropertyValue(Property->ContainerPtrToValuePtr<void>(Container)));
			}

			return FString::Printf(TEXT("%.6f"), NumericProperty->GetFloatingPointPropertyValue(Property->ContainerPtrToValuePtr<void>(Container)));
		}

		if (const FStrProperty* StrProperty = CastField<FStrProperty>(Property))
		{
			return StrProperty->GetPropertyValue_InContainer(Container);
		}

		if (const FNameProperty* NameProperty = CastField<FNameProperty>(Property))
		{
			return NameProperty->GetPropertyValue_InContainer(Container).ToString();
		}

		if (const FTextProperty* TextProperty = CastField<FTextProperty>(Property))
		{
			return TextProperty->GetPropertyValue_InContainer(Container).ToString();
		}

		FString ExportedValue;
		Property->ExportText_InContainer(0, ExportedValue, Container, Container, const_cast<UObject*>(Container), PPF_None);
		return ExportedValue;
	}

	static bool ApplyPropertyValue(FProperty* Property, UObject* TargetObject, const FString& ValueAsString, FString& OutError)
	{
		OutError.Empty();

		if (!Property || !TargetObject)
		{
			OutError = TEXT("Invalid property target.");
			return false;
		}

		TargetObject->Modify();

		if (FObjectPropertyBase* ObjectProperty = CastField<FObjectPropertyBase>(Property))
		{
			UObject* LoadedObject = nullptr;
			if (!ValueAsString.IsEmpty() && !ValueAsString.Equals(TEXT("None"), ESearchCase::IgnoreCase))
			{
				LoadedObject = LoadObject<UObject>(nullptr, *ValueAsString);
				if (!LoadedObject)
				{
					OutError = FString::Printf(TEXT("Could not load object '%s'."), *ValueAsString);
					return false;
				}

				if (UClass* PropertyClass = ObjectProperty->PropertyClass)
				{
					if (!LoadedObject->IsA(PropertyClass))
					{
						OutError = FString::Printf(
							TEXT("Loaded object '%s' is not compatible with property class '%s'."),
							*LoadedObject->GetPathName(),
							*PropertyClass->GetPathName());
						return false;
					}
				}
			}

			ObjectProperty->SetObjectPropertyValue_InContainer(TargetObject, LoadedObject);
			return true;
		}

		if (FBoolProperty* BoolProperty = CastField<FBoolProperty>(Property))
		{
			const bool bValue =
				ValueAsString.Equals(TEXT("true"), ESearchCase::IgnoreCase) ||
				ValueAsString.Equals(TEXT("1"));
			BoolProperty->SetPropertyValue_InContainer(TargetObject, bValue);
			return true;
		}

		if (FNumericProperty* NumericProperty = CastField<FNumericProperty>(Property))
		{
			if (NumericProperty->IsInteger())
			{
				const int64 ParsedValue = FCString::Atoi64(*ValueAsString);
				NumericProperty->SetIntPropertyValue(Property->ContainerPtrToValuePtr<void>(TargetObject), ParsedValue);
				return true;
			}

			const double ParsedValue = FCString::Atod(*ValueAsString);
			NumericProperty->SetFloatingPointPropertyValue(Property->ContainerPtrToValuePtr<void>(TargetObject), ParsedValue);
			return true;
		}

		if (FStrProperty* StrProperty = CastField<FStrProperty>(Property))
		{
			StrProperty->SetPropertyValue_InContainer(TargetObject, ValueAsString);
			return true;
		}

		if (FNameProperty* NameProperty = CastField<FNameProperty>(Property))
		{
			NameProperty->SetPropertyValue_InContainer(TargetObject, FName(*ValueAsString));
			return true;
		}

		if (FTextProperty* TextProperty = CastField<FTextProperty>(Property))
		{
			TextProperty->SetPropertyValue_InContainer(TargetObject, FText::FromString(ValueAsString));
			return true;
		}

		if (!Property->ImportText_InContainer(*ValueAsString, TargetObject, TargetObject, PPF_None))
		{
			OutError = FString::Printf(
				TEXT("Property '%s' does not support ImportText for value '%s'."),
				*Property->GetName(),
				*ValueAsString);
			return false;
		}

		return true;
	}

	static UObject* ResolveBlueprintPropertyTarget(
		UBlueprint* Blueprint,
		const FString& TargetComponentName,
		const bool bTargetComponentTemplate,
		FString& OutTargetMode,
		FString& OutError)
	{
		OutTargetMode = bTargetComponentTemplate ? TEXT("component_template") : TEXT("class_default_object");
		OutError.Empty();

		if (!Blueprint)
		{
			OutError = TEXT("Blueprint is null.");
			return nullptr;
		}

		if (bTargetComponentTemplate)
		{
			if (TargetComponentName.IsEmpty())
			{
				OutError = TEXT("TargetComponentName is required for component template writes.");
				return nullptr;
			}

			USCS_Node* Node = FindComponentNodeByName(Blueprint, FName(*TargetComponentName));
			if (!Node)
			{
				OutError = FString::Printf(
					TEXT("Component template node '%s' was not found in blueprint '%s'."),
					*TargetComponentName,
					*Blueprint->GetPathName());
				return nullptr;
			}

			if (!Node->ComponentTemplate)
			{
				OutError = FString::Printf(
					TEXT("Component node '%s' has no component template."),
					*TargetComponentName);
				return nullptr;
			}

			Node->Modify();
			return Node->ComponentTemplate;
		}

		if (!Blueprint->GeneratedClass)
		{
			OutError = FString::Printf(TEXT("Blueprint '%s' has no generated class."), *Blueprint->GetPathName());
			return nullptr;
		}

		UObject* DefaultObject = Blueprint->GeneratedClass->GetDefaultObject();
		if (!DefaultObject)
		{
			OutError = FString::Printf(TEXT("Blueprint '%s' has no class default object."), *Blueprint->GetPathName());
			return nullptr;
		}

		return DefaultObject;
	}

	static FString PropertySetResultToJsonString(const FBlueprintPropertySetResult& Result)
	{
		TSharedPtr<FJsonObject> RootObject = MakeShared<FJsonObject>();
		RootObject->SetBoolField(TEXT("success"), Result.bSuccess);
		RootObject->SetStringField(TEXT("blueprint_asset_path"), Result.BlueprintAssetPath);
		RootObject->SetStringField(TEXT("target_mode"), Result.TargetMode);
		RootObject->SetStringField(TEXT("target_object_path"), Result.TargetObjectPath);
		RootObject->SetStringField(TEXT("component_name"), Result.ComponentName);
		RootObject->SetStringField(TEXT("property_name"), Result.PropertyName);
		RootObject->SetStringField(TEXT("property_class"), Result.PropertyClass);
		RootObject->SetStringField(TEXT("value_as_string"), Result.ValueAsString);
		RootObject->SetStringField(TEXT("before_value"), Result.BeforeValue);
		RootObject->SetStringField(TEXT("after_value"), Result.AfterValue);
		RootObject->SetBoolField(TEXT("compiled"), Result.bCompiled);
		RootObject->SetBoolField(TEXT("saved"), Result.bSaved);
		RootObject->SetStringField(TEXT("compile_summary"), Result.CompileSummary);
		RootObject->SetStringField(TEXT("save_summary"), Result.SaveSummary);
		RootObject->SetStringField(TEXT("error"), Result.Error);

		FString JsonString;
		const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&JsonString);
		FJsonSerializer::Serialize(RootObject.ToSharedRef(), Writer);
		return JsonString;
	}

	static FString PropertyBatchResultToJsonString(
		const FBlueprintPropertySetResult& Result,
		const TArray<FBlueprintPropertyBatchEntry>& Entries)
	{
		TSharedPtr<FJsonObject> RootObject = MakeShared<FJsonObject>();
		RootObject->SetBoolField(TEXT("success"), Result.bSuccess);
		RootObject->SetStringField(TEXT("blueprint_asset_path"), Result.BlueprintAssetPath);
		RootObject->SetStringField(TEXT("target_mode"), Result.TargetMode);
		RootObject->SetStringField(TEXT("target_object_path"), Result.TargetObjectPath);
		RootObject->SetStringField(TEXT("component_name"), Result.ComponentName);
		RootObject->SetBoolField(TEXT("compiled"), Result.bCompiled);
		RootObject->SetBoolField(TEXT("saved"), Result.bSaved);
		RootObject->SetStringField(TEXT("compile_summary"), Result.CompileSummary);
		RootObject->SetStringField(TEXT("save_summary"), Result.SaveSummary);
		RootObject->SetStringField(TEXT("error"), Result.Error);

		TArray<TSharedPtr<FJsonValue>> OperationValues;
		for (const FBlueprintPropertyBatchEntry& Entry : Entries)
		{
			TSharedPtr<FJsonObject> EntryObject = MakeShared<FJsonObject>();
			EntryObject->SetStringField(TEXT("property_name"), Entry.PropertyName);
			EntryObject->SetStringField(TEXT("value_as_string"), Entry.ValueAsString);
			EntryObject->SetStringField(TEXT("property_class"), Entry.PropertyClass);
			EntryObject->SetStringField(TEXT("before_value"), Entry.BeforeValue);
			EntryObject->SetStringField(TEXT("after_value"), Entry.AfterValue);
			EntryObject->SetBoolField(TEXT("applied"), Entry.bApplied);
			EntryObject->SetStringField(TEXT("error"), Entry.Error);
			OperationValues.Add(MakeShared<FJsonValueObject>(EntryObject));
		}
		RootObject->SetArrayField(TEXT("operations"), OperationValues);

		FString JsonString;
		const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&JsonString);
		FJsonSerializer::Serialize(RootObject.ToSharedRef(), Writer);
		return JsonString;
	}

}

bool UBlueprintAutomationPythonBridge::RunSmokeTest(FString& OutSummary)
{
	return FBlueprintAutomationSmokeTest::Run(&OutSummary);
}

bool UBlueprintAutomationPythonBridge::RefreshActionIndex(FString& OutJson, FString& OutSummary)
{
	const FBlueprintActionAutomationResult RefreshResult =
		FBlueprintActionAutomationService::RefreshNodeIndex();
	OutJson = RefreshResult.JsonPayload;
	OutSummary = RefreshResult.Message;
	return RefreshResult.IsSuccess();
}

bool UBlueprintAutomationPythonBridge::InspectBlueprintEventGraph(
	const FString& BlueprintAssetPath,
	FString& OutGraphJson,
	FString& OutSummary,
	const bool bIncludePins,
	const bool bIncludeLinkedPins)
{
	OutGraphJson.Empty();

	UBlueprint* Blueprint = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::LoadBlueprint(BlueprintAssetPath, Blueprint, OutSummary))
	{
		return false;
	}

	UEdGraph* EventGraph = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::ResolveEventGraph(Blueprint, EventGraph, OutSummary))
	{
		return false;
	}

	const FBlueprintGraphAutomationResult InspectResult =
		FBlueprintGraphAutomationService::InspectGraphToJson(EventGraph, bIncludePins, bIncludeLinkedPins);
	OutGraphJson = InspectResult.JsonPayload;
	OutSummary = InspectResult.Message;
	return InspectResult.IsSuccess();
}

bool UBlueprintAutomationPythonBridge::InspectBlueprintGraph(
	const FString& BlueprintAssetPath,
	const FString& GraphName,
	FString& OutGraphJson,
	FString& OutSummary,
	const bool bIncludePins,
	const bool bIncludeLinkedPins)
{
	OutGraphJson.Empty();

	UBlueprint* Blueprint = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::LoadBlueprint(BlueprintAssetPath, Blueprint, OutSummary))
	{
		return false;
	}

	UEdGraph* Graph = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::ResolveGraphByName(Blueprint, GraphName, Graph, OutSummary))
	{
		return false;
	}

	const FBlueprintGraphAutomationResult InspectResult =
		FBlueprintGraphAutomationService::InspectGraphToJson(Graph, bIncludePins, bIncludeLinkedPins);
	OutGraphJson = InspectResult.JsonPayload;
	OutSummary = InspectResult.Message;
	return InspectResult.IsSuccess();
}

bool UBlueprintAutomationPythonBridge::ScanBlueprintActions(
	const FString& BlueprintAssetPath,
	FString& OutActionIndexJson,
	FString& OutSummary,
	const bool bContextSensitive)
{
	OutActionIndexJson.Empty();

	UBlueprint* Blueprint = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::LoadBlueprint(BlueprintAssetPath, Blueprint, OutSummary))
	{
		return false;
	}

	UEdGraph* EventGraph = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::ResolveEventGraph(Blueprint, EventGraph, OutSummary))
	{
		return false;
	}

	FBlueprintActionScanOptions Options;
	Options.ContextBlueprint = Blueprint;
	Options.ContextGraph = EventGraph;
	Options.bContextSensitive = bContextSensitive;
	Options.ScanMode = bContextSensitive ? EBlueprintActionScanMode::ContextSensitive : EBlueprintActionScanMode::All;

	const FBlueprintActionAutomationResult ScanResult =
		FBlueprintActionAutomationService::ScanAvailableBlueprintActions(Blueprint, EventGraph, Options);
	OutActionIndexJson = ScanResult.JsonPayload;
	OutSummary = ScanResult.Message;
	return ScanResult.IsSuccess();
}

bool UBlueprintAutomationPythonBridge::CompileBlueprint(
	const FString& BlueprintAssetPath,
	FString& OutCompileReportJson,
	FString& OutSummary)
{
	OutCompileReportJson.Empty();

	UBlueprint* Blueprint = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::LoadBlueprint(BlueprintAssetPath, Blueprint, OutSummary))
	{
		return false;
	}

	const FBlueprintActionAutomationResult CompileResult =
		FBlueprintActionAutomationService::CompileBlueprintAndCollectMessages(Blueprint);
	OutCompileReportJson = CompileResult.JsonPayload;
	OutSummary = CompileResult.Message;
	return CompileResult.IsSuccess();
}

bool UBlueprintAutomationPythonBridge::ApplyGraphBatchJson(
	const FString& BlueprintAssetPath,
	const FString& BatchJson,
	FString& OutResultJson,
	FString& OutSummary)
{
	OutResultJson.Empty();

	UBlueprint* Blueprint = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::LoadBlueprint(BlueprintAssetPath, Blueprint, OutSummary))
	{
		return false;
	}

	UEdGraph* EventGraph = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::ResolveEventGraph(Blueprint, EventGraph, OutSummary))
	{
		return false;
	}

	const FBlueprintGraphAutomationResult ApplyResult =
		FBlueprintGraphAutomationService::ApplyBatchJson(Blueprint, EventGraph, BatchJson);
	OutResultJson = ApplyResult.JsonPayload;
	OutSummary = ApplyResult.Message;
	return ApplyResult.IsSuccess();
}

bool UBlueprintAutomationPythonBridge::ApplyBlueprintGraphBatchJson(
	const FString& BlueprintAssetPath,
	const FString& GraphName,
	const FString& BatchJson,
	FString& OutResultJson,
	FString& OutSummary)
{
	OutResultJson.Empty();

	UBlueprint* Blueprint = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::LoadBlueprint(BlueprintAssetPath, Blueprint, OutSummary))
	{
		return false;
	}

	UEdGraph* Graph = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::ResolveGraphByName(Blueprint, GraphName, Graph, OutSummary))
	{
		return false;
	}

	const FBlueprintGraphAutomationResult ApplyResult =
		FBlueprintGraphAutomationService::ApplyBatchJson(Blueprint, Graph, BatchJson);
	OutResultJson = ApplyResult.JsonPayload;
	OutSummary = ApplyResult.Message;
	return ApplyResult.IsSuccess();
}

bool UBlueprintAutomationPythonBridge::SaveBlueprint(const FString& BlueprintAssetPath, FString& OutSummary)
{
	UBlueprint* Blueprint = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::LoadBlueprint(BlueprintAssetPath, Blueprint, OutSummary))
	{
		return false;
	}

	const FBlueprintAutomationResult SaveResult =
		FBlueprintAutomationService::SaveBlueprint(Blueprint);
	OutSummary = SaveResult.Message;
	return SaveResult.IsSuccess();
}

bool UBlueprintAutomationPythonBridge::SetBlueprintPropertyValue(
	const FString& BlueprintAssetPath,
	const FString& TargetComponentName,
	const FString& PropertyName,
	const FString& ValueAsString,
	const bool bTargetComponentTemplate,
	FString& OutResultJson,
	FString& OutSummary)
{
	OutResultJson.Empty();

	BlueprintAutomationPythonBridgePrivate::FBlueprintPropertySetResult Result;
	Result.BlueprintAssetPath = BlueprintAssetPath;
	Result.ComponentName = TargetComponentName;
	Result.PropertyName = PropertyName;
	Result.ValueAsString = ValueAsString;

	UBlueprint* Blueprint = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::LoadBlueprint(BlueprintAssetPath, Blueprint, OutSummary))
	{
		Result.Error = OutSummary;
		OutResultJson = BlueprintAutomationPythonBridgePrivate::PropertySetResultToJsonString(Result);
		return false;
	}

	FString ResolveError;
	FString TargetMode;
	UObject* TargetObject = BlueprintAutomationPythonBridgePrivate::ResolveBlueprintPropertyTarget(
		Blueprint,
		TargetComponentName,
		bTargetComponentTemplate,
		TargetMode,
		ResolveError);
	Result.TargetMode = TargetMode;
	Result.TargetObjectPath = TargetObject ? TargetObject->GetPathName() : FString();

	if (!TargetObject)
	{
		Result.Error = ResolveError;
		OutSummary = ResolveError;
		OutResultJson = BlueprintAutomationPythonBridgePrivate::PropertySetResultToJsonString(Result);
		return false;
	}

	FProperty* Property = FindFProperty<FProperty>(TargetObject->GetClass(), *PropertyName);
	if (!Property)
	{
		Result.Error = FString::Printf(
			TEXT("Property '%s' was not found on target '%s'."),
			*PropertyName,
			*TargetObject->GetClass()->GetPathName());
		OutSummary = Result.Error;
		OutResultJson = BlueprintAutomationPythonBridgePrivate::PropertySetResultToJsonString(Result);
		return false;
	}

	Result.PropertyClass = Property->GetClass()->GetName();
	Result.BeforeValue = BlueprintAutomationPythonBridgePrivate::PropertyValueToString(Property, TargetObject);

	FString ApplyError;
	if (!BlueprintAutomationPythonBridgePrivate::ApplyPropertyValue(Property, TargetObject, ValueAsString, ApplyError))
	{
		Result.Error = ApplyError;
		OutSummary = Result.Error;
		OutResultJson = BlueprintAutomationPythonBridgePrivate::PropertySetResultToJsonString(Result);
		return false;
	}
	Result.AfterValue = BlueprintAutomationPythonBridgePrivate::PropertyValueToString(Property, TargetObject);

	if (UActorComponent* ComponentTemplate = Cast<UActorComponent>(TargetObject))
	{
		ComponentTemplate->Modify();
		ComponentTemplate->MarkPackageDirty();
	}
	else
	{
		TargetObject->MarkPackageDirty();
	}

	Blueprint->Modify();
	Blueprint->MarkPackageDirty();
	FBlueprintEditorUtils::MarkBlueprintAsModified(Blueprint);

	const FBlueprintAutomationResult CompileResult = FBlueprintAutomationService::CompileBlueprint(Blueprint);
	Result.bCompiled = CompileResult.IsSuccess();
	Result.CompileSummary = CompileResult.Message;

	const FBlueprintAutomationResult SaveResult = FBlueprintAutomationService::SaveBlueprint(Blueprint);
	Result.bSaved = SaveResult.IsSuccess();
	Result.SaveSummary = SaveResult.Message;
	Result.bSuccess = Result.bCompiled && Result.bSaved;
	if (!Result.bSuccess && Result.Error.IsEmpty())
	{
		Result.Error = FString::Printf(
			TEXT("Compile/save failed. compiled=%s saved=%s"),
			Result.bCompiled ? TEXT("true") : TEXT("false"),
			Result.bSaved ? TEXT("true") : TEXT("false"));
	}

	OutResultJson = BlueprintAutomationPythonBridgePrivate::PropertySetResultToJsonString(Result);
	OutSummary = FString::Printf(
		TEXT("SetBlueprintPropertyValue blueprint='%s' target='%s' property='%s' success=%s"),
		*BlueprintAssetPath,
		*Result.TargetObjectPath,
		*PropertyName,
		Result.bSuccess ? TEXT("true") : TEXT("false"));
	return Result.bSuccess;
}

bool UBlueprintAutomationPythonBridge::SetBlueprintPropertiesBatchJson(
	const FString& BlueprintAssetPath,
	const FString& TargetComponentName,
	const FString& BatchJson,
	const bool bTargetComponentTemplate,
	FString& OutResultJson,
	FString& OutSummary)
{
	OutResultJson.Empty();

	BlueprintAutomationPythonBridgePrivate::FBlueprintPropertySetResult Result;
	Result.BlueprintAssetPath = BlueprintAssetPath;
	Result.ComponentName = TargetComponentName;

	UBlueprint* Blueprint = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::LoadBlueprint(BlueprintAssetPath, Blueprint, OutSummary))
	{
		Result.Error = OutSummary;
		OutResultJson = BlueprintAutomationPythonBridgePrivate::PropertySetResultToJsonString(Result);
		return false;
	}

	FString ResolveError;
	FString TargetMode;
	UObject* TargetObject = BlueprintAutomationPythonBridgePrivate::ResolveBlueprintPropertyTarget(
		Blueprint,
		TargetComponentName,
		bTargetComponentTemplate,
		TargetMode,
		ResolveError);
	Result.TargetMode = TargetMode;
	Result.TargetObjectPath = TargetObject ? TargetObject->GetPathName() : FString();

	if (!TargetObject)
	{
		Result.Error = ResolveError;
		OutSummary = ResolveError;
		OutResultJson = BlueprintAutomationPythonBridgePrivate::PropertySetResultToJsonString(Result);
		return false;
	}

	TSharedPtr<FJsonObject> RootObject;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(BatchJson);
	if (!FJsonSerializer::Deserialize(Reader, RootObject) || !RootObject.IsValid())
	{
		Result.Error = TEXT("BatchJson is not a valid JSON object.");
		OutSummary = Result.Error;
		OutResultJson = BlueprintAutomationPythonBridgePrivate::PropertySetResultToJsonString(Result);
		return false;
	}

	const TArray<TSharedPtr<FJsonValue>>* Operations = nullptr;
	if (!RootObject->TryGetArrayField(TEXT("operations"), Operations) || !Operations)
	{
		Result.Error = TEXT("BatchJson must contain an 'operations' array.");
		OutSummary = Result.Error;
		OutResultJson = BlueprintAutomationPythonBridgePrivate::PropertySetResultToJsonString(Result);
		return false;
	}

	TArray<BlueprintAutomationPythonBridgePrivate::FBlueprintPropertyBatchEntry> Entries;
	Entries.Reserve(Operations->Num());

	bool bAnyApplied = false;
	bool bAllApplied = true;

	for (const TSharedPtr<FJsonValue>& Item : *Operations)
	{
		BlueprintAutomationPythonBridgePrivate::FBlueprintPropertyBatchEntry Entry;
		const TSharedPtr<FJsonObject>* ItemObject = nullptr;
		if (!Item.IsValid() || !Item->TryGetObject(ItemObject) || !ItemObject || !ItemObject->IsValid())
		{
			Entry.Error = TEXT("Invalid operation entry.");
			bAllApplied = false;
			Entries.Add(MoveTemp(Entry));
			continue;
		}

		(*ItemObject)->TryGetStringField(TEXT("property_name"), Entry.PropertyName);
		(*ItemObject)->TryGetStringField(TEXT("value_as_string"), Entry.ValueAsString);

		FProperty* Property = FindFProperty<FProperty>(TargetObject->GetClass(), *Entry.PropertyName);
		if (!Property)
		{
			Entry.Error = FString::Printf(
				TEXT("Property '%s' was not found on target '%s'."),
				*Entry.PropertyName,
				*TargetObject->GetClass()->GetPathName());
			bAllApplied = false;
			Entries.Add(MoveTemp(Entry));
			continue;
		}

		Entry.PropertyClass = Property->GetClass()->GetName();
		Entry.BeforeValue = BlueprintAutomationPythonBridgePrivate::PropertyValueToString(Property, TargetObject);

		FString ApplyError;
		Entry.bApplied = BlueprintAutomationPythonBridgePrivate::ApplyPropertyValue(Property, TargetObject, Entry.ValueAsString, ApplyError);
		Entry.AfterValue = BlueprintAutomationPythonBridgePrivate::PropertyValueToString(Property, TargetObject);
		Entry.Error = ApplyError;

		bAnyApplied |= Entry.bApplied;
		bAllApplied &= Entry.bApplied;
		Entries.Add(MoveTemp(Entry));
	}

	if (bAnyApplied)
	{
		if (UActorComponent* ComponentTemplate = Cast<UActorComponent>(TargetObject))
		{
			ComponentTemplate->Modify();
			ComponentTemplate->MarkPackageDirty();
		}
		else
		{
			TargetObject->MarkPackageDirty();
		}

		Blueprint->Modify();
		Blueprint->MarkPackageDirty();
		FBlueprintEditorUtils::MarkBlueprintAsModified(Blueprint);

		const FBlueprintAutomationResult CompileResult = FBlueprintAutomationService::CompileBlueprint(Blueprint);
		Result.bCompiled = CompileResult.IsSuccess();
		Result.CompileSummary = CompileResult.Message;

		const FBlueprintAutomationResult SaveResult = FBlueprintAutomationService::SaveBlueprint(Blueprint);
		Result.bSaved = SaveResult.IsSuccess();
		Result.SaveSummary = SaveResult.Message;
	}

	Result.bSuccess = bAllApplied && (!bAnyApplied || (Result.bCompiled && Result.bSaved));
	if (!Result.bSuccess && Result.Error.IsEmpty())
	{
		Result.Error = FString::Printf(
			TEXT("Batch apply failed. applied=%s compiled=%s saved=%s"),
			bAllApplied ? TEXT("true") : TEXT("false"),
			Result.bCompiled ? TEXT("true") : TEXT("false"),
			Result.bSaved ? TEXT("true") : TEXT("false"));
	}

	OutResultJson = BlueprintAutomationPythonBridgePrivate::PropertyBatchResultToJsonString(Result, Entries);
	OutSummary = FString::Printf(
		TEXT("SetBlueprintPropertiesBatchJson blueprint='%s' target='%s' operations=%d success=%s"),
		*BlueprintAssetPath,
		*Result.TargetObjectPath,
		Entries.Num(),
		Result.bSuccess ? TEXT("true") : TEXT("false"));
	return Result.bSuccess;
}

bool UBlueprintAutomationPythonBridge::SetEnhancedInputActionsByNode(
	const FString& BlueprintAssetPath,
	const FString& NodeActionMapJson,
	FString& OutResultJson,
	FString& OutSummary)
{
	OutResultJson.Empty();

	UBlueprint* Blueprint = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::LoadBlueprint(BlueprintAssetPath, Blueprint, OutSummary))
	{
		return false;
	}

	UEdGraph* EventGraph = nullptr;
	if (!BlueprintAutomationPythonBridgePrivate::ResolveEventGraph(Blueprint, EventGraph, OutSummary))
	{
		return false;
	}

	TMap<FString, FString> NodeNameToActionPath;
	{
		TSharedPtr<FJsonObject> RootObject;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(NodeActionMapJson);
		if (!FJsonSerializer::Deserialize(Reader, RootObject) || !RootObject.IsValid())
		{
			OutSummary = TEXT("NodeActionMapJson is not a valid JSON object.");
			return false;
		}

		const TArray<TSharedPtr<FJsonValue>>* NodeActions = nullptr;
		if (RootObject->TryGetArrayField(TEXT("node_actions"), NodeActions) && NodeActions)
		{
			for (const TSharedPtr<FJsonValue>& Item : *NodeActions)
			{
				const TSharedPtr<FJsonObject>* ItemObject = nullptr;
				if (!Item.IsValid() || !Item->TryGetObject(ItemObject) || !ItemObject || !ItemObject->IsValid())
				{
					continue;
				}

				FString NodeName;
				FString ActionAssetPath;
				(*ItemObject)->TryGetStringField(TEXT("node_name"), NodeName);
				(*ItemObject)->TryGetStringField(TEXT("action_asset_path"), ActionAssetPath);
				if (!NodeName.IsEmpty() && !ActionAssetPath.IsEmpty())
				{
					NodeNameToActionPath.Add(NodeName, ActionAssetPath);
				}
			}
		}
	}

	struct FNodeApplyResult
	{
		FString NodeName;
		FString NodePath;
		FString ActionAssetPath;
		bool bApplied = false;
		FString Reason;
	};

	TArray<FNodeApplyResult> PerNodeResults;
	PerNodeResults.Reserve(NodeNameToActionPath.Num());

	TSet<FString> RequestedNodeNames;
	for (const TPair<FString, FString>& Pair : NodeNameToActionPath)
	{
		RequestedNodeNames.Add(Pair.Key);
	}

	int32 ScannedEnhancedNodes = 0;
	int32 AppliedCount = 0;
	bool bAnyChanged = false;

	for (UEdGraphNode* Node : EventGraph->Nodes)
	{
		if (!Node)
		{
			continue;
		}

		if (!Node->GetClass()->GetName().Equals(TEXT("K2Node_EnhancedInputAction")))
		{
			continue;
		}

		++ScannedEnhancedNodes;

		const FString NodeName = Node->GetName();
		const FString* ActionAssetPathPtr = NodeNameToActionPath.Find(NodeName);
		if (!ActionAssetPathPtr)
		{
			continue;
		}

		FNodeApplyResult Result;
		Result.NodeName = NodeName;
		Result.NodePath = Node->GetPathName();
		Result.ActionAssetPath = *ActionAssetPathPtr;

		UObject* ActionAsset = LoadObject<UObject>(nullptr, **ActionAssetPathPtr);
		if (!ActionAsset)
		{
			Result.Reason = FString::Printf(TEXT("action_asset_not_found: %s"), **ActionAssetPathPtr);
			PerNodeResults.Add(MoveTemp(Result));
			continue;
		}

		FObjectPropertyBase* InputActionProperty =
			FindFProperty<FObjectPropertyBase>(Node->GetClass(), TEXT("InputAction"));
		if (!InputActionProperty)
		{
			Result.Reason = TEXT("input_action_property_not_found");
			PerNodeResults.Add(MoveTemp(Result));
			continue;
		}

		Node->Modify();
		InputActionProperty->SetObjectPropertyValue_InContainer(Node, ActionAsset);
		Node->ReconstructNode();

		Result.bApplied = true;
		Result.Reason = TEXT("ok");
		PerNodeResults.Add(MoveTemp(Result));

		++AppliedCount;
		bAnyChanged = true;
		RequestedNodeNames.Remove(NodeName);
	}

	for (const FString& MissingNodeName : RequestedNodeNames)
	{
		FNodeApplyResult Result;
		Result.NodeName = MissingNodeName;
		Result.NodePath = TEXT("");
		Result.ActionAssetPath = NodeNameToActionPath.FindRef(MissingNodeName);
		Result.Reason = TEXT("node_not_found_in_event_graph");
		PerNodeResults.Add(MoveTemp(Result));
	}

	if (bAnyChanged)
	{
		EventGraph->Modify();
		EventGraph->NotifyGraphChanged();
		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
		Blueprint->MarkPackageDirty();
	}

	TSharedPtr<FJsonObject> RootObject = MakeShared<FJsonObject>();
	RootObject->SetStringField(TEXT("blueprint_asset_path"), BlueprintAssetPath);
	RootObject->SetNumberField(TEXT("requested"), NodeNameToActionPath.Num());
	RootObject->SetNumberField(TEXT("scanned_enhanced_nodes"), ScannedEnhancedNodes);
	RootObject->SetNumberField(TEXT("applied"), AppliedCount);

	TArray<TSharedPtr<FJsonValue>> PerNodeArray;
	for (const FNodeApplyResult& Item : PerNodeResults)
	{
		TSharedPtr<FJsonObject> ItemObject = MakeShared<FJsonObject>();
		ItemObject->SetStringField(TEXT("node_name"), Item.NodeName);
		ItemObject->SetStringField(TEXT("node_path"), Item.NodePath);
		ItemObject->SetStringField(TEXT("action_asset_path"), Item.ActionAssetPath);
		ItemObject->SetBoolField(TEXT("applied"), Item.bApplied);
		ItemObject->SetStringField(TEXT("reason"), Item.Reason);
		PerNodeArray.Add(MakeShared<FJsonValueObject>(ItemObject));
	}
	RootObject->SetArrayField(TEXT("results"), PerNodeArray);

	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutResultJson);
	FJsonSerializer::Serialize(RootObject.ToSharedRef(), Writer);

	const bool bSuccess = NodeNameToActionPath.Num() > 0 && AppliedCount == NodeNameToActionPath.Num();
	OutSummary = FString::Printf(
		TEXT("SetEnhancedInputActionsByNode requested=%d scanned=%d applied=%d success=%s"),
		NodeNameToActionPath.Num(),
		ScannedEnhancedNodes,
		AppliedCount,
		bSuccess ? TEXT("true") : TEXT("false"));
	return bSuccess;
}

bool UBlueprintAutomationPythonBridge::EnsureSnowReceiverSurfacesOnActors(
	const FString& MapPath,
	const TArray<FString>& ActorObjectPaths,
	const ESnowReceiverSurfaceFamily SurfaceFamily,
	const int32 ReceiverPriority,
	const FString& ReceiverSetTag,
	const bool bSaveCurrentLevel,
	const bool bReloadMapForVerification,
	FString& OutResultJson,
	FString& OutSummary)
{
	OutResultJson.Empty();

	BlueprintAutomationPythonBridgePrivate::FSnowReceiverAttachBatchResult BatchResult;
	BatchResult.MapPath = MapPath;

	if (!MapPath.IsEmpty())
	{
		UEditorLoadingAndSavingUtils::LoadMap(MapPath);
	}

	for (const FString& ActorPath : ActorObjectPaths)
	{
		AActor* Actor = BlueprintAutomationPythonBridgePrivate::FindActorByObjectPath(ActorPath);
		BlueprintAutomationPythonBridgePrivate::FSnowReceiverAttachActorResult ActorResult;
		ActorResult.ActorPath = ActorPath;
		ActorResult.bFound = (Actor != nullptr);

		if (Actor)
		{
			bool bCreatedComponent = false;
			FString CreationDetail;
			USnowReceiverSurfaceComponent* Component =
				BlueprintAutomationPythonBridgePrivate::AttachSnowReceiverComponent(
					Actor,
					bCreatedComponent,
					CreationDetail);
			if (Component)
			{
				BlueprintAutomationPythonBridgePrivate::ConfigureSnowReceiverComponent(
					Component,
					SurfaceFamily,
					ReceiverPriority,
					ReceiverSetTag);
				BlueprintAutomationPythonBridgePrivate::MarkActorAndLevelDirty(Actor);
				Actor->RerunConstructionScripts();

				ActorResult =
					BlueprintAutomationPythonBridgePrivate::MakeActorSnapshot(Actor, ActorPath);
				ActorResult.bCreatedComponent = bCreatedComponent;
				ActorResult.CreationDetail = CreationDetail;

				BatchResult.CreatedCount += bCreatedComponent ? 1 : 0;
				BatchResult.ConfiguredCount += 1;
			}
			else
			{
				ActorResult.CreationDetail = CreationDetail;
			}
		}

		BatchResult.PerActorResults.Add(ActorResult);
	}

	BatchResult.bSavedCurrentLevel = bSaveCurrentLevel
		? UEditorLoadingAndSavingUtils::SaveCurrentLevel()
		: false;

	if (bReloadMapForVerification && !MapPath.IsEmpty())
	{
		UEditorLoadingAndSavingUtils::LoadMap(MapPath);
	}

	for (const FString& ActorPath : ActorObjectPaths)
	{
		AActor* Actor = BlueprintAutomationPythonBridgePrivate::FindActorByObjectPath(ActorPath);
		BatchResult.VerificationResults.Add(
			BlueprintAutomationPythonBridgePrivate::MakeActorSnapshot(Actor, ActorPath));
	}

	bool bAllVerified = true;
	for (const BlueprintAutomationPythonBridgePrivate::FSnowReceiverAttachActorResult& Item : BatchResult.VerificationResults)
	{
		bAllVerified &= Item.bFound && Item.NumComponentsAfter >= 1;
	}

	BatchResult.bSuccess =
		(!bSaveCurrentLevel || BatchResult.bSavedCurrentLevel) &&
		bAllVerified;

	OutResultJson = BlueprintAutomationPythonBridgePrivate::BatchResultToJsonString(BatchResult);
	OutSummary = FString::Printf(
		TEXT("EnsureSnowReceiverSurfacesOnActors map='%s' created=%d configured=%d saved=%s success=%s"),
		*MapPath,
		BatchResult.CreatedCount,
		BatchResult.ConfiguredCount,
		BatchResult.bSavedCurrentLevel ? TEXT("true") : TEXT("false"),
		BatchResult.bSuccess ? TEXT("true") : TEXT("false"));
	return BatchResult.bSuccess;
}
