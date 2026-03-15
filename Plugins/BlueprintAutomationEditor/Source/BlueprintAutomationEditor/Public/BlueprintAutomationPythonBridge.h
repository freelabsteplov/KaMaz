#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"

#include "BlueprintAutomationPythonBridge.generated.h"

UCLASS()
class BLUEPRINTAUTOMATIONEDITOR_API UBlueprintAutomationPythonBridge final : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable, Category = "BlueprintAutomation")
	static bool RunSmokeTest(FString& OutSummary);

	UFUNCTION(BlueprintCallable, Category = "BlueprintAutomation")
	static bool RefreshActionIndex(FString& OutJson, FString& OutSummary);

	UFUNCTION(BlueprintCallable, Category = "BlueprintAutomation")
	static bool InspectBlueprintEventGraph(
		const FString& BlueprintAssetPath,
		FString& OutGraphJson,
		FString& OutSummary,
		bool bIncludePins = true,
		bool bIncludeLinkedPins = true);

	UFUNCTION(BlueprintCallable, Category = "BlueprintAutomation")
	static bool InspectBlueprintGraph(
		const FString& BlueprintAssetPath,
		const FString& GraphName,
		FString& OutGraphJson,
		FString& OutSummary,
		bool bIncludePins = true,
		bool bIncludeLinkedPins = true);

	UFUNCTION(BlueprintCallable, Category = "BlueprintAutomation")
	static bool ScanBlueprintActions(
		const FString& BlueprintAssetPath,
		FString& OutActionIndexJson,
		FString& OutSummary,
		bool bContextSensitive = true);

	UFUNCTION(BlueprintCallable, Category = "BlueprintAutomation")
	static bool CompileBlueprint(
		const FString& BlueprintAssetPath,
		FString& OutCompileReportJson,
		FString& OutSummary);

	UFUNCTION(BlueprintCallable, Category = "BlueprintAutomation")
	static bool ApplyGraphBatchJson(
		const FString& BlueprintAssetPath,
		const FString& BatchJson,
		FString& OutResultJson,
		FString& OutSummary);

	UFUNCTION(BlueprintCallable, Category = "BlueprintAutomation")
	static bool ApplyBlueprintGraphBatchJson(
		const FString& BlueprintAssetPath,
		const FString& GraphName,
		const FString& BatchJson,
		FString& OutResultJson,
		FString& OutSummary);

	UFUNCTION(BlueprintCallable, Category = "BlueprintAutomation")
	static bool SaveBlueprint(
		const FString& BlueprintAssetPath,
		FString& OutSummary);

	UFUNCTION(BlueprintCallable, Category = "BlueprintAutomation")
	static bool EnsureSnowReceiverSurfacesOnActors(
		const FString& MapPath,
		const TArray<FString>& ActorObjectPaths,
		ESnowReceiverSurfaceFamily SurfaceFamily,
		int32 ReceiverPriority,
		const FString& ReceiverSetTag,
		bool bSaveCurrentLevel,
		bool bReloadMapForVerification,
		FString& OutResultJson,
		FString& OutSummary);
};
