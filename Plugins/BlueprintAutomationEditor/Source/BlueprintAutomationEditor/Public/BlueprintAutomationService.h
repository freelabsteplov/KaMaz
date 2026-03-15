#pragma once

#include "CoreMinimal.h"
#include "EdGraph/EdGraphPin.h"

class UActorComponent;
class UBlueprint;
class USCS_Node;
class USceneComponent;
class UStaticMeshComponent;

enum class EBlueprintAutomationResultCode : uint8
{
	Success,
	InvalidArgument,
	NotFound,
	AlreadyExists,
	Unsupported,
	Failed
};

struct FBlueprintAutomationResult
{
	EBlueprintAutomationResultCode Code = EBlueprintAutomationResultCode::Failed;
	FString Message;
	TObjectPtr<UBlueprint> Blueprint = nullptr;
	TObjectPtr<USCS_Node> ComponentNode = nullptr;

	bool IsSuccess() const
	{
		return Code == EBlueprintAutomationResultCode::Success;
	}

	static FBlueprintAutomationResult Ok(const FString& InMessage, UBlueprint* InBlueprint = nullptr, USCS_Node* InComponentNode = nullptr);
	static FBlueprintAutomationResult Error(EBlueprintAutomationResultCode InCode, const FString& InMessage, UBlueprint* InBlueprint = nullptr);
};

enum class EBlueprintPrimitiveVariableType : uint8
{
	Float,
	Bool,
	Int32,
	String,
	Name
};

struct FBlueprintVariableDefinition
{
	FName Name = NAME_None;
	EBlueprintPrimitiveVariableType Type = EBlueprintPrimitiveVariableType::Float;
	FString DefaultValue;
};

class BLUEPRINTAUTOMATIONEDITOR_API FBlueprintAutomationService final
{
public:
	static FBlueprintAutomationResult CreateBlueprintAsset(const FString& AssetPath, UClass* ParentClass = nullptr);
	static FBlueprintAutomationResult LoadBlueprintByAssetPath(const FString& AssetPath);
	static FBlueprintAutomationResult LoadBlueprintByObjectPath(const FString& ObjectPath);

	static FBlueprintAutomationResult AddVariable(UBlueprint* Blueprint, const FBlueprintVariableDefinition& Definition);
	static FBlueprintAutomationResult AddFloatVariable(UBlueprint* Blueprint, const FName VariableName, const double DefaultValue = 0.0);
	static FBlueprintAutomationResult AddBoolVariable(UBlueprint* Blueprint, const FName VariableName, const bool bDefaultValue = false);
	static FBlueprintAutomationResult AddIntVariable(UBlueprint* Blueprint, const FName VariableName, const int32 DefaultValue = 0);
	static FBlueprintAutomationResult AddStringVariable(UBlueprint* Blueprint, const FName VariableName, const FString& DefaultValue = FString());
	static FBlueprintAutomationResult AddNameVariable(UBlueprint* Blueprint, const FName VariableName, const FName DefaultValue = NAME_None);

	static FBlueprintAutomationResult AddComponent(
		UBlueprint* Blueprint,
		TSubclassOf<UActorComponent> ComponentClass,
		const FName ComponentName,
		const FName AttachParentName = NAME_None,
		const bool bMakeRootIfNoRootExists = true);

	static FBlueprintAutomationResult AddSceneComponent(
		UBlueprint* Blueprint,
		const FName ComponentName,
		const FName AttachParentName = NAME_None,
		const bool bMakeRootIfNoRootExists = true);

	static FBlueprintAutomationResult AddStaticMeshComponent(
		UBlueprint* Blueprint,
		const FName ComponentName,
		const FName AttachParentName = NAME_None);

	static FBlueprintAutomationResult CompileBlueprint(UBlueprint* Blueprint);
	static FBlueprintAutomationResult SaveBlueprint(UBlueprint* Blueprint);

private:
	static FEdGraphPinType MakePinType(EBlueprintPrimitiveVariableType Type);
	static FString MakeBlueprintObjectPath(const FString& AssetPath);
	static bool TryNormalizeAssetPath(const FString& InPath, FString& OutLongPackageName, FString& OutObjectPath, FString& OutAssetName, FString& OutError);
	static USCS_Node* FindComponentNodeByName(const UBlueprint* Blueprint, const FName ComponentName);
};
