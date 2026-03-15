#include "BlueprintAutomationEditorModule.h"

#include "BlueprintActionAutomationService.h"
#include "BlueprintAutomationService.h"
#include "BlueprintAutomationSmokeTest.h"
#include "BlueprintGraphAutomationService.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "EdGraph/EdGraph.h"
#include "Engine/Blueprint.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Logging/LogMacros.h"
#include "Modules/ModuleManager.h"
#include "Policies/PrettyJsonPrintPolicy.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace BlueprintAutomationEditorModulePrivate
{
	static FString SerializeJsonObject(const TSharedPtr<FJsonObject>& JsonObject)
	{
		FString Output;
		const TSharedRef<TJsonWriter<TCHAR, TPrettyJsonPrintPolicy<TCHAR>>> Writer =
			TJsonWriterFactory<TCHAR, TPrettyJsonPrintPolicy<TCHAR>>::Create(&Output);
		FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);
		return Output;
	}

	static bool WriteTextFile(const FString& AbsolutePath, const FString& Content, FString& OutError)
	{
		const FString Directory = FPaths::GetPath(AbsolutePath);
		if (!IFileManager::Get().MakeDirectory(*Directory, true))
		{
			OutError = FString::Printf(TEXT("Failed to create directory '%s'."), *Directory);
			return false;
		}

		if (!FFileHelper::SaveStringToFile(Content, *AbsolutePath))
		{
			OutError = FString::Printf(TEXT("Failed to write file '%s'."), *AbsolutePath);
			return false;
		}

		return true;
	}

	static FString MakeSnapshotDirectory()
	{
		return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("BlueprintAutomation"));
	}

	static FString MakeSnapshotPath(const FString& Prefix, const FString& Suffix)
	{
		return FPaths::Combine(MakeSnapshotDirectory(), FString::Printf(TEXT("%s_%s.json"), *Prefix, *Suffix));
	}

	static FString CollapseConsoleArgumentTail(const TArray<FString>& Args, const int32 StartIndex)
	{
		if (!Args.IsValidIndex(StartIndex))
		{
			return FString();
		}

		FString Collapsed;
		for (int32 Index = StartIndex; Index < Args.Num(); ++Index)
		{
			if (!Collapsed.IsEmpty())
			{
				Collapsed.AppendChar(TEXT(' '));
			}
			Collapsed.Append(Args[Index]);
		}

		Collapsed.TrimStartAndEndInline();
		Collapsed.RemoveFromStart(TEXT("\""));
		Collapsed.RemoveFromEnd(TEXT("\""));
		return Collapsed;
	}
}

IMPLEMENT_MODULE(FBlueprintAutomationEditorModule, BlueprintAutomationEditor)

void FBlueprintAutomationEditorModule::StartupModule()
{
	SmokeTestCommand = MakeUnique<FAutoConsoleCommand>(
		TEXT("BlueprintAutomation.RunSmokeTest"),
		TEXT("Runs a smoke test for BlueprintAutomationEditor by creating a generated Blueprint asset and exercising asset/graph/action services."),
		FConsoleCommandDelegate::CreateRaw(this, &FBlueprintAutomationEditorModule::RunSmokeTest));

	ExportKamazSnapshotCommand = MakeUnique<FAutoConsoleCommand>(
		TEXT("BlueprintAutomation.ExportKamazBPSnapshot"),
		TEXT("Exports graph/action/compile JSON snapshot for /Game/CityPark/Kamaz/model/KamazBP into Saved/BlueprintAutomation."),
		FConsoleCommandDelegate::CreateRaw(this, &FBlueprintAutomationEditorModule::ExportKamazBlueprintSnapshot));

	ExportBlueprintSnapshotCommand = MakeUnique<FAutoConsoleCommand>(
		TEXT("BlueprintAutomation.ExportBlueprintSnapshot"),
		TEXT("Exports graph/action/compile JSON snapshot for a Blueprint asset path. Usage: BlueprintAutomation.ExportBlueprintSnapshot /Game/Path/BP_Name [file_prefix]"),
		FConsoleCommandWithArgsDelegate::CreateRaw(this, &FBlueprintAutomationEditorModule::ExportBlueprintSnapshot));

	ExportBlueprintGraphCommand = MakeUnique<FAutoConsoleCommand>(
		TEXT("BlueprintAutomation.ExportBlueprintGraph"),
		TEXT("Exports a specific graph to JSON. Usage: BlueprintAutomation.ExportBlueprintGraph /Game/Path/BP_Name GraphName [file_prefix]"),
		FConsoleCommandWithArgsDelegate::CreateRaw(this, &FBlueprintAutomationEditorModule::ExportBlueprintGraph));

	ApplyBlueprintBatchFileCommand = MakeUnique<FAutoConsoleCommand>(
		TEXT("BlueprintAutomation.ApplyBlueprintBatchFile"),
		TEXT("Applies a graph batch JSON file to EventGraph, then compiles and saves it. Usage: BlueprintAutomation.ApplyBlueprintBatchFile /Game/Path/BP_Name C:/path/to/batch.json"),
		FConsoleCommandWithArgsDelegate::CreateRaw(this, &FBlueprintAutomationEditorModule::ApplyBlueprintBatchFile));

	ApplyBlueprintBatchFileToGraphCommand = MakeUnique<FAutoConsoleCommand>(
		TEXT("BlueprintAutomation.ApplyBlueprintBatchFileToGraph"),
		TEXT("Applies a graph batch JSON file to a specific graph, then compiles and saves it. Usage: BlueprintAutomation.ApplyBlueprintBatchFileToGraph /Game/Path/BP_Name GraphName C:/path/to/batch.json"),
		FConsoleCommandWithArgsDelegate::CreateRaw(this, &FBlueprintAutomationEditorModule::ApplyBlueprintBatchFileToGraph));
}

void FBlueprintAutomationEditorModule::ShutdownModule()
{
	ApplyBlueprintBatchFileToGraphCommand.Reset();
	ApplyBlueprintBatchFileCommand.Reset();
	ExportBlueprintGraphCommand.Reset();
	ExportBlueprintSnapshotCommand.Reset();
	ExportKamazSnapshotCommand.Reset();
	SmokeTestCommand.Reset();
}

void FBlueprintAutomationEditorModule::RunSmokeTest()
{
	FString Summary;
	const bool bSuccess = FBlueprintAutomationSmokeTest::Run(&Summary);
	UE_LOG(LogTemp, Display, TEXT("BlueprintAutomation.RunSmokeTest finished: %s"), *Summary);
	if (!bSuccess)
	{
		UE_LOG(LogTemp, Error, TEXT("BlueprintAutomation.RunSmokeTest failed."));
	}
}

void FBlueprintAutomationEditorModule::ExportKamazBlueprintSnapshot()
{
	FString Summary;
	const bool bSuccess = ExportBlueprintSnapshotToFiles(
		TEXT("/Game/CityPark/Kamaz/model/KamazBP"),
		TEXT("kamazbp"),
		Summary);

	UE_LOG(LogTemp, Display, TEXT("BlueprintAutomation.ExportKamazBPSnapshot finished: %s"), *Summary);
	if (!bSuccess)
	{
		UE_LOG(LogTemp, Error, TEXT("BlueprintAutomation.ExportKamazBPSnapshot failed."));
	}
}

void FBlueprintAutomationEditorModule::ExportBlueprintSnapshot(const TArray<FString>& Args)
{
	if (Args.IsEmpty())
	{
		UE_LOG(LogTemp, Error, TEXT("Usage: BlueprintAutomation.ExportBlueprintSnapshot /Game/Path/BP_Name [file_prefix]"));
		return;
	}

	const FString BlueprintAssetPath = Args[0];
	const FString FilePrefix = Args.Num() > 1 ? Args[1] : TEXT("blueprint_snapshot");

	FString Summary;
	const bool bSuccess = ExportBlueprintSnapshotToFiles(BlueprintAssetPath, FilePrefix, Summary);
	UE_LOG(LogTemp, Display, TEXT("BlueprintAutomation.ExportBlueprintSnapshot finished: %s"), *Summary);
	if (!bSuccess)
	{
		UE_LOG(LogTemp, Error, TEXT("BlueprintAutomation.ExportBlueprintSnapshot failed."));
	}
}

void FBlueprintAutomationEditorModule::ExportBlueprintGraph(const TArray<FString>& Args)
{
	if (Args.Num() < 2)
	{
		UE_LOG(LogTemp, Error, TEXT("Usage: BlueprintAutomation.ExportBlueprintGraph /Game/Path/BP_Name GraphName [file_prefix]"));
		return;
	}

	const FString BlueprintAssetPath = Args[0];
	const FString GraphName = Args[1];
	const FString FilePrefix = Args.Num() > 2 ? Args[2] : TEXT("blueprint_graph");

	FString Summary;
	const bool bSuccess = ExportBlueprintGraphToFile(BlueprintAssetPath, GraphName, FilePrefix, Summary);
	UE_LOG(LogTemp, Display, TEXT("BlueprintAutomation.ExportBlueprintGraph finished: %s"), *Summary);
	if (!bSuccess)
	{
		UE_LOG(LogTemp, Error, TEXT("BlueprintAutomation.ExportBlueprintGraph failed."));
	}
}

bool FBlueprintAutomationEditorModule::ExportBlueprintSnapshotToFiles(
	const FString& BlueprintAssetPath,
	const FString& FilePrefix,
	FString& OutSummary) const
{
	const FBlueprintAutomationResult LoadResult =
		FBlueprintAutomationService::LoadBlueprintByAssetPath(BlueprintAssetPath);
	if (!LoadResult.IsSuccess() || !LoadResult.Blueprint)
	{
		OutSummary = FString::Printf(TEXT("LoadBlueprintByAssetPath failed: %s"), *LoadResult.Message);
		return false;
	}

	UBlueprint* Blueprint = LoadResult.Blueprint.Get();
	const FBlueprintGraphAutomationResult GraphResult =
		FBlueprintGraphAutomationService::GetEventGraph(Blueprint);
	if (!GraphResult.IsSuccess() || !GraphResult.Graph)
	{
		OutSummary = FString::Printf(TEXT("GetEventGraph failed: %s"), *GraphResult.Message);
		return false;
	}

	UEdGraph* EventGraph = GraphResult.Graph.Get();

	const FBlueprintActionAutomationResult RefreshResult =
		FBlueprintActionAutomationService::RefreshNodeIndex();
	if (!RefreshResult.IsSuccess())
	{
		OutSummary = FString::Printf(TEXT("RefreshNodeIndex failed: %s"), *RefreshResult.Message);
		return false;
	}

	const FBlueprintGraphAutomationResult InspectResult =
		FBlueprintGraphAutomationService::InspectGraphToJson(EventGraph, true, true);
	if (!InspectResult.IsSuccess())
	{
		OutSummary = FString::Printf(TEXT("InspectGraphToJson failed: %s"), *InspectResult.Message);
		return false;
	}

	FBlueprintActionScanOptions ScanOptions;
	ScanOptions.ContextBlueprint = Blueprint;
	ScanOptions.ContextGraph = EventGraph;
	ScanOptions.bContextSensitive = true;
	ScanOptions.ScanMode = EBlueprintActionScanMode::ContextSensitive;

	const FBlueprintActionAutomationResult ScanResult =
		FBlueprintActionAutomationService::ScanAvailableBlueprintActions(Blueprint, EventGraph, ScanOptions);
	if (!ScanResult.IsSuccess())
	{
		OutSummary = FString::Printf(TEXT("ScanAvailableBlueprintActions failed: %s"), *ScanResult.Message);
		return false;
	}

	const FBlueprintActionAutomationResult CompileResult =
		FBlueprintActionAutomationService::CompileBlueprintAndCollectMessages(Blueprint);
	if (!CompileResult.IsSuccess())
	{
		OutSummary = FString::Printf(TEXT("CompileBlueprintAndCollectMessages failed: %s"), *CompileResult.Message);
		return false;
	}

	TSharedPtr<FJsonObject> SummaryObject = MakeShared<FJsonObject>();
	SummaryObject->SetStringField(TEXT("blueprint_asset_path"), BlueprintAssetPath);
	SummaryObject->SetStringField(TEXT("blueprint_object_path"), Blueprint->GetPathName());
	SummaryObject->SetStringField(TEXT("graph_object_path"), EventGraph->GetPathName());
	SummaryObject->SetStringField(TEXT("refresh_summary"), RefreshResult.Message);
	SummaryObject->SetStringField(TEXT("graph_summary"), InspectResult.Message);
	SummaryObject->SetStringField(TEXT("actions_summary"), ScanResult.Message);
	SummaryObject->SetStringField(TEXT("compile_summary"), CompileResult.Message);

	const FString SnapshotDirectory = BlueprintAutomationEditorModulePrivate::MakeSnapshotDirectory();
	SummaryObject->SetStringField(TEXT("output_directory"), SnapshotDirectory);

	const FString RefreshPath = BlueprintAutomationEditorModulePrivate::MakeSnapshotPath(FilePrefix, TEXT("refresh_action_index"));
	const FString GraphPath = BlueprintAutomationEditorModulePrivate::MakeSnapshotPath(FilePrefix, TEXT("graph"));
	const FString ActionsPath = BlueprintAutomationEditorModulePrivate::MakeSnapshotPath(FilePrefix, TEXT("actions"));
	const FString CompilePath = BlueprintAutomationEditorModulePrivate::MakeSnapshotPath(FilePrefix, TEXT("compile"));
	const FString SummaryPath = BlueprintAutomationEditorModulePrivate::MakeSnapshotPath(FilePrefix, TEXT("summary"));

	SummaryObject->SetStringField(TEXT("refresh_action_index_path"), RefreshPath);
	SummaryObject->SetStringField(TEXT("graph_path"), GraphPath);
	SummaryObject->SetStringField(TEXT("actions_path"), ActionsPath);
	SummaryObject->SetStringField(TEXT("compile_path"), CompilePath);
	SummaryObject->SetStringField(TEXT("summary_path"), SummaryPath);

	FString Error;
	if (!BlueprintAutomationEditorModulePrivate::WriteTextFile(RefreshPath, RefreshResult.JsonPayload, Error) ||
		!BlueprintAutomationEditorModulePrivate::WriteTextFile(GraphPath, InspectResult.JsonPayload, Error) ||
		!BlueprintAutomationEditorModulePrivate::WriteTextFile(ActionsPath, ScanResult.JsonPayload, Error) ||
		!BlueprintAutomationEditorModulePrivate::WriteTextFile(CompilePath, CompileResult.JsonPayload, Error))
	{
		OutSummary = Error;
		return false;
	}

	const FString SummaryJson = BlueprintAutomationEditorModulePrivate::SerializeJsonObject(SummaryObject);
	if (!BlueprintAutomationEditorModulePrivate::WriteTextFile(SummaryPath, SummaryJson, Error))
	{
		OutSummary = Error;
		return false;
	}

	OutSummary = FString::Printf(
		TEXT("Exported Blueprint snapshot for '%s' to '%s'."),
		*BlueprintAssetPath,
		*SnapshotDirectory);
	return true;
}

bool FBlueprintAutomationEditorModule::ExportBlueprintGraphToFile(
	const FString& BlueprintAssetPath,
	const FString& GraphName,
	const FString& FilePrefix,
	FString& OutSummary) const
{
	const FBlueprintAutomationResult LoadResult =
		FBlueprintAutomationService::LoadBlueprintByAssetPath(BlueprintAssetPath);
	if (!LoadResult.IsSuccess() || !LoadResult.Blueprint)
	{
		OutSummary = FString::Printf(TEXT("LoadBlueprintByAssetPath failed: %s"), *LoadResult.Message);
		return false;
	}

	UBlueprint* Blueprint = LoadResult.Blueprint.Get();
	const FBlueprintGraphAutomationResult GraphResult =
		FBlueprintGraphAutomationService::GetGraphByName(Blueprint, FName(*GraphName));
	if (!GraphResult.IsSuccess() || !GraphResult.Graph)
	{
		OutSummary = FString::Printf(TEXT("GetGraphByName failed: %s"), *GraphResult.Message);
		return false;
	}

	const FBlueprintGraphAutomationResult InspectResult =
		FBlueprintGraphAutomationService::InspectGraphToJson(GraphResult.Graph.Get(), true, true);
	if (!InspectResult.IsSuccess())
	{
		OutSummary = FString::Printf(TEXT("InspectGraphToJson failed: %s"), *InspectResult.Message);
		return false;
	}

	const FString SnapshotDirectory = BlueprintAutomationEditorModulePrivate::MakeSnapshotDirectory();
	const FString GraphPath = BlueprintAutomationEditorModulePrivate::MakeSnapshotPath(FilePrefix, TEXT("graph"));

	FString Error;
	if (!BlueprintAutomationEditorModulePrivate::WriteTextFile(GraphPath, InspectResult.JsonPayload, Error))
	{
		OutSummary = Error;
		return false;
	}

	OutSummary = FString::Printf(
		TEXT("Exported graph '%s' for '%s' to '%s'."),
		*GraphName,
		*BlueprintAssetPath,
		*GraphPath);
	return true;
}

void FBlueprintAutomationEditorModule::ApplyBlueprintBatchFile(const TArray<FString>& Args)
{
	if (Args.Num() < 2)
	{
		UE_LOG(LogTemp, Error, TEXT("Usage: BlueprintAutomation.ApplyBlueprintBatchFile /Game/Path/BP_Name C:/path/to/batch.json"));
		return;
	}

	const FString BlueprintAssetPath = Args[0];
	const FString BatchFilePath = BlueprintAutomationEditorModulePrivate::CollapseConsoleArgumentTail(Args, 1);

	FString Summary;
	const bool bSuccess = ApplyBlueprintBatchFileInternal(BlueprintAssetPath, TEXT("EventGraph"), BatchFilePath, Summary);
	UE_LOG(LogTemp, Display, TEXT("BlueprintAutomation.ApplyBlueprintBatchFile finished: %s"), *Summary);
	if (!bSuccess)
	{
		UE_LOG(LogTemp, Error, TEXT("BlueprintAutomation.ApplyBlueprintBatchFile failed."));
	}
}

void FBlueprintAutomationEditorModule::ApplyBlueprintBatchFileToGraph(const TArray<FString>& Args)
{
	if (Args.Num() < 3)
	{
		UE_LOG(
			LogTemp,
			Error,
			TEXT("Usage: BlueprintAutomation.ApplyBlueprintBatchFileToGraph /Game/Path/BP_Name GraphName C:/path/to/batch.json"));
		return;
	}

	const FString BlueprintAssetPath = Args[0];
	const FString GraphName = Args[1];
	const FString BatchFilePath = BlueprintAutomationEditorModulePrivate::CollapseConsoleArgumentTail(Args, 2);

	FString Summary;
	const bool bSuccess = ApplyBlueprintBatchFileInternal(BlueprintAssetPath, GraphName, BatchFilePath, Summary);
	UE_LOG(LogTemp, Display, TEXT("BlueprintAutomation.ApplyBlueprintBatchFileToGraph finished: %s"), *Summary);
	if (!bSuccess)
	{
		UE_LOG(LogTemp, Error, TEXT("BlueprintAutomation.ApplyBlueprintBatchFileToGraph failed."));
	}
}

bool FBlueprintAutomationEditorModule::ApplyBlueprintBatchFileInternal(
	const FString& BlueprintAssetPath,
	const FString& GraphName,
	const FString& BatchFilePath,
	FString& OutSummary) const
{
	if (BatchFilePath.IsEmpty())
	{
		OutSummary = TEXT("Batch file path is empty.");
		return false;
	}

	FString BatchJson;
	if (!FFileHelper::LoadFileToString(BatchJson, *BatchFilePath))
	{
		OutSummary = FString::Printf(TEXT("Failed to read batch file '%s'."), *BatchFilePath);
		return false;
	}

	const FBlueprintAutomationResult LoadResult =
		FBlueprintAutomationService::LoadBlueprintByAssetPath(BlueprintAssetPath);
	if (!LoadResult.IsSuccess() || !LoadResult.Blueprint)
	{
		OutSummary = FString::Printf(TEXT("LoadBlueprintByAssetPath failed: %s"), *LoadResult.Message);
		return false;
	}

	UBlueprint* Blueprint = LoadResult.Blueprint.Get();
	const FBlueprintGraphAutomationResult GraphResult =
		FBlueprintGraphAutomationService::GetGraphByName(Blueprint, FName(*GraphName));
	if (!GraphResult.IsSuccess() || !GraphResult.Graph)
	{
		OutSummary = FString::Printf(TEXT("GetGraphByName failed: %s"), *GraphResult.Message);
		return false;
	}

	const FBlueprintGraphAutomationResult ApplyResult =
		FBlueprintGraphAutomationService::ApplyBatchJson(Blueprint, GraphResult.Graph.Get(), BatchJson);
	if (!ApplyResult.IsSuccess())
	{
		OutSummary = FString::Printf(TEXT("ApplyBatchJson failed: %s"), *ApplyResult.Message);
		return false;
	}

	FBlueprintCompileReport CompileReport;
	const FBlueprintActionAutomationResult CompileResult =
		FBlueprintActionAutomationService::CompileBlueprintAndCollectMessages(Blueprint, CompileReport);
	if (!CompileResult.IsSuccess())
	{
		OutSummary = FString::Printf(TEXT("CompileBlueprintAndCollectMessages failed: %s"), *CompileResult.Message);
		return false;
	}

	const FBlueprintAutomationResult SaveResult =
		FBlueprintAutomationService::SaveBlueprint(Blueprint);
	if (!SaveResult.IsSuccess())
	{
		OutSummary = FString::Printf(TEXT("SaveBlueprint failed: %s"), *SaveResult.Message);
		return false;
	}

	OutSummary = FString::Printf(
		TEXT("Applied batch '%s' to graph '%s' on '%s'. Errors=%d Warnings=%d"),
		*BatchFilePath,
		*GraphName,
		*BlueprintAssetPath,
		CompileReport.NumErrors,
		CompileReport.NumWarnings);
	return true;
}
