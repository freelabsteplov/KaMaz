#include "BlueprintAutomationSmokeTest.h"

#include "BlueprintActionAutomationService.h"
#include "BlueprintAutomationService.h"
#include "BlueprintGraphAutomationService.h"

#include "Engine/Blueprint.h"
#include "EdGraph/EdGraph.h"
#include "GameFramework/Actor.h"
#include "Logging/LogMacros.h"

DEFINE_LOG_CATEGORY_STATIC(LogBlueprintAutomationSmoke, Log, All);

bool FBlueprintAutomationSmokeTest::Run(FString* OutSummary)
{
	const FString AssetPath =
		FString::Printf(TEXT("/Game/Automation/BP_BlueprintAutomationSmoke_%s"), *FGuid::NewGuid().ToString(EGuidFormats::Digits));

	UE_LOG(LogBlueprintAutomationSmoke, Display, TEXT("Smoke test started. Target asset: %s"), *AssetPath);

	FBlueprintAutomationResult CreateResult =
		FBlueprintAutomationService::CreateBlueprintAsset(AssetPath, AActor::StaticClass());
	if (!CreateResult.IsSuccess() || !CreateResult.Blueprint)
	{
		const FString Message = FString::Printf(TEXT("CreateBlueprintAsset failed: %s"), *CreateResult.Message);
		UE_LOG(LogBlueprintAutomationSmoke, Error, TEXT("%s"), *Message);
		if (OutSummary)
		{
			*OutSummary = Message;
		}
		return false;
	}

	UBlueprint* Blueprint = CreateResult.Blueprint.Get();

	const TArray<FBlueprintAutomationResult> AssetOps = {
		FBlueprintAutomationService::AddFloatVariable(Blueprint, TEXT("MoveSpeed"), 650.0),
		FBlueprintAutomationService::AddBoolVariable(Blueprint, TEXT("bSnowMode"), true),
		FBlueprintAutomationService::AddIntVariable(Blueprint, TEXT("GearIndex"), 1),
		FBlueprintAutomationService::AddSceneComponent(Blueprint, TEXT("RootScene")),
		FBlueprintAutomationService::AddStaticMeshComponent(Blueprint, TEXT("BodyMesh"), TEXT("RootScene"))
	};

	for (const FBlueprintAutomationResult& Result : AssetOps)
	{
		if (!Result.IsSuccess())
		{
			const FString Message = FString::Printf(TEXT("Asset layer failed: %s"), *Result.Message);
			UE_LOG(LogBlueprintAutomationSmoke, Error, TEXT("%s"), *Message);
			if (OutSummary)
			{
				*OutSummary = Message;
			}
			return false;
		}
	}

	FBlueprintGraphAutomationResult EventGraphResult =
		FBlueprintGraphAutomationService::GetEventGraph(Blueprint);
	if (!EventGraphResult.IsSuccess() || !EventGraphResult.Graph)
	{
		const FString Message = FString::Printf(TEXT("GetEventGraph failed: %s"), *EventGraphResult.Message);
		UE_LOG(LogBlueprintAutomationSmoke, Error, TEXT("%s"), *Message);
		if (OutSummary)
		{
			*OutSummary = Message;
		}
		return false;
	}

	UEdGraph* EventGraph = EventGraphResult.Graph.Get();

	const FBlueprintGraphAutomationResult CustomEventResult =
		FBlueprintGraphAutomationService::CreateCustomEventNode(
			EventGraph,
			TEXT("OnAutomationSmoke"),
			FVector2D(100.0, 100.0));

	const FBlueprintGraphAutomationResult VariableSetResult =
		FBlueprintGraphAutomationService::CreateVariableSetNode(
			Blueprint,
			EventGraph,
			TEXT("MoveSpeed"),
			FVector2D(450.0, 100.0));

	if (!CustomEventResult.IsSuccess() || !VariableSetResult.IsSuccess())
	{
		const FString Message = FString::Printf(
			TEXT("Graph layer failed. CustomEvent=%s VariableSet=%s"),
			*CustomEventResult.Message,
			*VariableSetResult.Message);
		UE_LOG(LogBlueprintAutomationSmoke, Error, TEXT("%s"), *Message);
		if (OutSummary)
		{
			*OutSummary = Message;
		}
		return false;
	}

	FBlueprintActionScanOptions ScanOptions;
	ScanOptions.ContextBlueprint = Blueprint;
	ScanOptions.ContextGraph = EventGraph;

	FBlueprintActionIndexDocument ActionDocument;
	const FBlueprintActionAutomationResult ScanResult =
		FBlueprintActionAutomationService::ScanAvailableBlueprintActions(ScanOptions, ActionDocument);
	if (!ScanResult.IsSuccess())
	{
		const FString Message = FString::Printf(TEXT("Action scan failed: %s"), *ScanResult.Message);
		UE_LOG(LogBlueprintAutomationSmoke, Error, TEXT("%s"), *Message);
		if (OutSummary)
		{
			*OutSummary = Message;
		}
		return false;
	}

	TArray<FBlueprintActionIndexEntry> QueryMatches;
	const FBlueprintActionAutomationResult QueryResult =
		FBlueprintActionAutomationService::ResolveActionsByTextQuery(ActionDocument, TEXT("Print String"), QueryMatches);
	if (!QueryResult.IsSuccess())
	{
		const FString Message = FString::Printf(TEXT("Action query failed: %s"), *QueryResult.Message);
		UE_LOG(LogBlueprintAutomationSmoke, Error, TEXT("%s"), *Message);
		if (OutSummary)
		{
			*OutSummary = Message;
		}
		return false;
	}

	FBlueprintCompileReport CompileReport;
	const FBlueprintActionAutomationResult CompileResult =
		FBlueprintActionAutomationService::CompileBlueprintAndCollectMessages(Blueprint, CompileReport);
	if (!CompileResult.IsSuccess())
	{
		const FString Message = FString::Printf(TEXT("Compile failed: %s"), *CompileResult.Message);
		UE_LOG(LogBlueprintAutomationSmoke, Error, TEXT("%s"), *Message);
		if (OutSummary)
		{
			*OutSummary = Message;
		}
		return false;
	}

	const FBlueprintAutomationResult SaveResult = FBlueprintAutomationService::SaveBlueprint(Blueprint);
	if (!SaveResult.IsSuccess())
	{
		const FString Message = FString::Printf(TEXT("Save failed: %s"), *SaveResult.Message);
		UE_LOG(LogBlueprintAutomationSmoke, Error, TEXT("%s"), *Message);
		if (OutSummary)
		{
			*OutSummary = Message;
		}
		return false;
	}

	const FString Summary = FString::Printf(
		TEXT("Smoke test succeeded. Asset=%s Actions=%d PrintStringMatches=%d Errors=%d Warnings=%d"),
		*Blueprint->GetPathName(),
		ActionDocument.Entries.Num(),
		QueryMatches.Num(),
		CompileReport.NumErrors,
		CompileReport.NumWarnings);

	UE_LOG(LogBlueprintAutomationSmoke, Display, TEXT("%s"), *Summary);
	if (OutSummary)
	{
		*OutSummary = Summary;
	}
	return true;
}
