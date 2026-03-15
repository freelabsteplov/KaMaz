#pragma once

#include "BlueprintAutomationService.h"

#include "CoreMinimal.h"
#include "Kismet2/KismetEditorUtilities.h"

class UBlueprint;
class UBlueprintNodeSpawner;
class UClass;
class UEdGraph;
class UEdGraphNode;

enum class EBlueprintActionScanMode : uint8
{
	All,
	ContextSensitive
};

struct FBlueprintActionIndexPin
{
	FName Name = NAME_None;
	FString Direction;
	FString Type;
	bool bIsArray = false;
	bool bIsSet = false;
	bool bIsMap = false;
	bool bIsReference = false;
	bool bIsConst = false;
	bool bIsReturnValue = false;
};

struct FBlueprintActionIndexEntry
{
	FString SpawnerSignature;
	FString SignatureGuid;
	FString SpawnerClassPath;
	FString NodeClassPath;
	FString ActionOwnerPath;
	FString OwnerClassPath;
	FString FunctionPath;
	FString PropertyName;
	FString PropertyCppType;
	FString PropertyOwnerClassPath;
	FString MenuName;
	FString Category;
	FString Tooltip;
	FString Keywords;
	FString DocLink;
	FString DocExcerptTag;
	TArray<FBlueprintActionIndexPin> Pins;
};

struct FBlueprintActionIndexContext
{
	FString BlueprintPath;
	FString GraphPath;
	EBlueprintActionScanMode ScanMode = EBlueprintActionScanMode::ContextSensitive;
};

struct FBlueprintActionIndexDocument
{
	static constexpr int32 CurrentSchemaVersion = 1;

	int32 SchemaVersion = CurrentSchemaVersion;
	FBlueprintActionIndexContext Context;
	TArray<FBlueprintActionIndexEntry> Entries;
};

struct FBlueprintCompileMessage
{
	FString Severity;
	FString Text;
};

struct FBlueprintCompileReport
{
	FString BlueprintPath;
	FString Status;
	int32 NumErrors = 0;
	int32 NumWarnings = 0;
	TArray<FBlueprintCompileMessage> Messages;
};

struct FBlueprintActionScanOptions
{
	UBlueprint* ContextBlueprint = nullptr;
	UEdGraph* ContextGraph = nullptr;
	EBlueprintActionScanMode ScanMode = EBlueprintActionScanMode::ContextSensitive;
	bool bContextSensitive = true;
	bool bIncludeUiSpec = true;
	bool bIncludeFunctionDetails = true;
	bool bIncludePropertyDetails = true;
};

struct FBlueprintActionAutomationResult
{
	EBlueprintAutomationResultCode Code = EBlueprintAutomationResultCode::Failed;
	FString Message;
	FString JsonPayload;
	TObjectPtr<UBlueprint> Blueprint = nullptr;
	TObjectPtr<UEdGraph> Graph = nullptr;
	TObjectPtr<UEdGraphNode> Node = nullptr;
	TObjectPtr<UBlueprintNodeSpawner> Action = nullptr;

	bool IsSuccess() const
	{
		return Code == EBlueprintAutomationResultCode::Success;
	}

	static FBlueprintActionAutomationResult Ok(
		const FString& InMessage,
		UBlueprint* InBlueprint = nullptr,
		UEdGraph* InGraph = nullptr,
		UEdGraphNode* InNode = nullptr,
		UBlueprintNodeSpawner* InAction = nullptr,
		const FString& InJsonPayload = FString());

	static FBlueprintActionAutomationResult Error(
		EBlueprintAutomationResultCode InCode,
		const FString& InMessage,
		UBlueprint* InBlueprint = nullptr,
		UEdGraph* InGraph = nullptr,
		UEdGraphNode* InNode = nullptr,
		UBlueprintNodeSpawner* InAction = nullptr,
		const FString& InJsonPayload = FString());
};

class BLUEPRINTAUTOMATIONEDITOR_API FBlueprintActionAutomationService final
{
public:
	static FBlueprintActionAutomationResult RefreshNodeIndex();

	static FBlueprintActionAutomationResult ScanAvailableBlueprintActions(
		UBlueprint* Blueprint = nullptr,
		UEdGraph* Graph = nullptr,
		const FBlueprintActionScanOptions& Options = FBlueprintActionScanOptions());
	static FBlueprintActionAutomationResult ScanAvailableBlueprintActions(
		const FBlueprintActionScanOptions& Options,
		FBlueprintActionIndexDocument& OutDocument);

	static FBlueprintActionAutomationResult ExportBlueprintActionIndexToJson();
	static FBlueprintActionAutomationResult ExportBlueprintActionIndexToJson(
		const FBlueprintActionIndexDocument& Document,
		FString& OutJson);
	static FBlueprintActionAutomationResult ResolveActionBySignature(const FString& ActionSignature);
	static FBlueprintActionAutomationResult ResolveActionBySignature(
		const FBlueprintActionIndexDocument& Document,
		const FString& ActionSignature,
		FBlueprintActionIndexEntry& OutEntry);
	static FBlueprintActionAutomationResult ResolveActionsByTextQuery(
		const FBlueprintActionIndexDocument& Document,
		const FString& TextQuery,
		TArray<FBlueprintActionIndexEntry>& OutEntries);

	static FBlueprintActionAutomationResult SpawnActionBySignature(
		UBlueprint* Blueprint,
		UEdGraph* Graph,
		const FString& ActionSignature,
		const FVector2D& NodePosition);
	static FBlueprintActionAutomationResult ValidateActionInContext(
		UBlueprint* Blueprint,
		UEdGraph* Graph,
		const FString& ActionSignature,
		bool& bOutIsAllowed);

	static FBlueprintActionAutomationResult ValidateSpawnInSandboxBlueprint(
		const FString& ActionSignature,
		UClass* ParentClass = nullptr,
		const FVector2D& NodePosition = FVector2D::ZeroVector);

	static FBlueprintActionAutomationResult CompileBlueprintAndCollectMessages(
		UBlueprint* Blueprint,
		EBlueprintCompileOptions CompileOptions = EBlueprintCompileOptions::None);
	static FBlueprintActionAutomationResult CompileBlueprintAndCollectMessages(
		UBlueprint* Blueprint,
		FBlueprintCompileReport& OutReport,
		EBlueprintCompileOptions CompileOptions = EBlueprintCompileOptions::None);

private:
	static UBlueprint* ResolveBlueprintContext(UBlueprint* ExplicitBlueprint, UEdGraph* Graph);
	static UEdGraph* ResolveGraphContext(UBlueprint* Blueprint, UEdGraph* ExplicitGraph);
	static UBlueprintNodeSpawner* FindActionBySignature(const FString& ActionSignature);
	static bool EnsureActionIndex(bool bForceRefresh = false);
};
