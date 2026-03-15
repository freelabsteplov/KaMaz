#pragma once

#include "HAL/IConsoleManager.h"
#include "Modules/ModuleManager.h"

class FBlueprintAutomationEditorModule final : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

private:
	void RunSmokeTest();
	void ExportKamazBlueprintSnapshot();
	void ExportBlueprintSnapshot(const TArray<FString>& Args);
	void ExportBlueprintGraph(const TArray<FString>& Args);
	void ApplyBlueprintBatchFile(const TArray<FString>& Args);
	void ApplyBlueprintBatchFileToGraph(const TArray<FString>& Args);
	bool ExportBlueprintSnapshotToFiles(const FString& BlueprintAssetPath, const FString& FilePrefix, FString& OutSummary) const;
	bool ExportBlueprintGraphToFile(const FString& BlueprintAssetPath, const FString& GraphName, const FString& FilePrefix, FString& OutSummary) const;
	bool ApplyBlueprintBatchFileInternal(
		const FString& BlueprintAssetPath,
		const FString& GraphName,
		const FString& BatchFilePath,
		FString& OutSummary) const;

	TUniquePtr<FAutoConsoleCommand> SmokeTestCommand;
	TUniquePtr<FAutoConsoleCommand> ExportKamazSnapshotCommand;
	TUniquePtr<FAutoConsoleCommand> ExportBlueprintSnapshotCommand;
	TUniquePtr<FAutoConsoleCommand> ExportBlueprintGraphCommand;
	TUniquePtr<FAutoConsoleCommand> ApplyBlueprintBatchFileCommand;
	TUniquePtr<FAutoConsoleCommand> ApplyBlueprintBatchFileToGraphCommand;
};
