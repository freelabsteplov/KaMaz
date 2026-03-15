#include "BlueprintAutomationPythonBridge.h"

#include "BlueprintActionAutomationService.h"
#include "BlueprintAutomationService.h"
#include "BlueprintAutomationSmokeTest.h"
#include "BlueprintGraphAutomationService.h"

#include "EdGraph/EdGraph.h"
#include "Engine/Blueprint.h"
#include "Engine/Level.h"
#include "Engine/World.h"
#include "FileHelpers.h"
#include "GameFramework/Actor.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Snow/PersistentSnowStateTypes.h"
#include "Snow/SnowReceiverSurfaceComponent.h"

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
