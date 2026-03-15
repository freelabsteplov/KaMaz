#include "BlueprintAutomationService.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EdGraphSchema_K2.h"
#include "Engine/Blueprint.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Logging/LogMacros.h"
#include "Misc/PackageName.h"
#include "UObject/Class.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"

DEFINE_LOG_CATEGORY_STATIC(LogBlueprintAutomationEditor, Log, All);

namespace BlueprintAutomationServicePrivate
{
	static FString SanitizePath(const FString& InPath)
	{
		FString Path = InPath.TrimStartAndEnd();
		if (Path.RemoveFromStart(TEXT("Blueprint'")) && Path.EndsWith(TEXT("'")))
		{
			Path.LeftChopInline(1, EAllowShrinking::No);
		}
		else if (Path.RemoveFromStart(TEXT("Class'")) && Path.EndsWith(TEXT("'")))
		{
			Path.LeftChopInline(1, EAllowShrinking::No);
		}
		else
		{
			Path = FPackageName::ExportTextPathToObjectPath(Path);
		}

		return Path;
	}

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

	static void LogResult(const FBlueprintAutomationResult& Result)
	{
		const FString Prefix = FString::Printf(TEXT("[%s] "), *ResultCodeToString(Result.Code));
		if (Result.IsSuccess())
		{
			UE_LOG(LogBlueprintAutomationEditor, Display, TEXT("%s%s"), *Prefix, *Result.Message);
		}
		else
		{
			UE_LOG(LogBlueprintAutomationEditor, Error, TEXT("%s%s"), *Prefix, *Result.Message);
		}
	}
}

FBlueprintAutomationResult FBlueprintAutomationResult::Ok(const FString& InMessage, UBlueprint* InBlueprint, USCS_Node* InComponentNode)
{
	FBlueprintAutomationResult Result;
	Result.Code = EBlueprintAutomationResultCode::Success;
	Result.Message = InMessage;
	Result.Blueprint = InBlueprint;
	Result.ComponentNode = InComponentNode;
	BlueprintAutomationServicePrivate::LogResult(Result);
	return Result;
}

FBlueprintAutomationResult FBlueprintAutomationResult::Error(const EBlueprintAutomationResultCode InCode, const FString& InMessage, UBlueprint* InBlueprint)
{
	FBlueprintAutomationResult Result;
	Result.Code = InCode;
	Result.Message = InMessage;
	Result.Blueprint = InBlueprint;
	BlueprintAutomationServicePrivate::LogResult(Result);
	return Result;
}

FBlueprintAutomationResult FBlueprintAutomationService::CreateBlueprintAsset(const FString& AssetPath, UClass* ParentClass)
{
	if (!ParentClass)
	{
		ParentClass = AActor::StaticClass();
	}

	FString LongPackageName;
	FString ObjectPath;
	FString AssetName;
	FString Error;
	if (!TryNormalizeAssetPath(AssetPath, LongPackageName, ObjectPath, AssetName, Error))
	{
		return FBlueprintAutomationResult::Error(EBlueprintAutomationResultCode::InvalidArgument, Error);
	}

	if (!FKismetEditorUtilities::CanCreateBlueprintOfClass(ParentClass))
	{
		return FBlueprintAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			FString::Printf(TEXT("Class '%s' does not support Blueprint creation."), *ParentClass->GetPathName()));
	}

	if (LoadObject<UBlueprint>(nullptr, *ObjectPath) != nullptr)
	{
		return FBlueprintAutomationResult::Error(
			EBlueprintAutomationResultCode::AlreadyExists,
			FString::Printf(TEXT("Blueprint asset already exists at '%s'."), *ObjectPath));
	}

	UPackage* Package = CreatePackage(*LongPackageName);
	if (!Package)
	{
		return FBlueprintAutomationResult::Error(
			EBlueprintAutomationResultCode::Failed,
			FString::Printf(TEXT("Failed to create package '%s'."), *LongPackageName));
	}

	UBlueprint* Blueprint = FKismetEditorUtilities::CreateBlueprint(
		ParentClass,
		Package,
		*AssetName,
		EBlueprintType::BPTYPE_Normal,
		UBlueprint::StaticClass(),
		UBlueprintGeneratedClass::StaticClass(),
		TEXT("BlueprintAutomationEditor"));

	if (!Blueprint)
	{
		return FBlueprintAutomationResult::Error(
			EBlueprintAutomationResultCode::Failed,
			FString::Printf(TEXT("CreateBlueprint failed for '%s'."), *ObjectPath));
	}

	FAssetRegistryModule::AssetCreated(Blueprint);
	Package->MarkPackageDirty();

	return FBlueprintAutomationResult::Ok(
		FString::Printf(TEXT("Created Blueprint '%s' with parent '%s'."), *ObjectPath, *ParentClass->GetPathName()),
		Blueprint);
}

FBlueprintAutomationResult FBlueprintAutomationService::LoadBlueprintByAssetPath(const FString& AssetPath)
{
	FString LongPackageName;
	FString ObjectPath;
	FString AssetName;
	FString Error;
	if (!TryNormalizeAssetPath(AssetPath, LongPackageName, ObjectPath, AssetName, Error))
	{
		return FBlueprintAutomationResult::Error(EBlueprintAutomationResultCode::InvalidArgument, Error);
	}

	return LoadBlueprintByObjectPath(ObjectPath);
}

FBlueprintAutomationResult FBlueprintAutomationService::LoadBlueprintByObjectPath(const FString& ObjectPath)
{
	const FString SanitizedPath = BlueprintAutomationServicePrivate::SanitizePath(ObjectPath);
	if (SanitizedPath.IsEmpty())
	{
		return FBlueprintAutomationResult::Error(
			EBlueprintAutomationResultCode::InvalidArgument,
			TEXT("Blueprint object path is empty."));
	}

	UObject* LoadedObject = StaticLoadObject(UObject::StaticClass(), nullptr, *SanitizedPath);
	if (!LoadedObject)
	{
		return FBlueprintAutomationResult::Error(
			EBlueprintAutomationResultCode::NotFound,
			FString::Printf(TEXT("No asset found at '%s'."), *SanitizedPath));
	}

	if (UBlueprint* Blueprint = Cast<UBlueprint>(LoadedObject))
	{
		return FBlueprintAutomationResult::Ok(
			FString::Printf(TEXT("Loaded Blueprint '%s'."), *Blueprint->GetPathName()),
			Blueprint);
	}

	if (UClass* GeneratedClass = Cast<UClass>(LoadedObject))
	{
		if (UBlueprint* Blueprint = Cast<UBlueprint>(GeneratedClass->ClassGeneratedBy))
		{
			return FBlueprintAutomationResult::Ok(
				FString::Printf(TEXT("Loaded Blueprint '%s' from generated class '%s'."), *Blueprint->GetPathName(), *GeneratedClass->GetPathName()),
				Blueprint);
		}
	}

	return FBlueprintAutomationResult::Error(
		EBlueprintAutomationResultCode::Unsupported,
		FString::Printf(TEXT("Object at '%s' is not a Blueprint asset."), *SanitizedPath));
}

FBlueprintAutomationResult FBlueprintAutomationService::AddVariable(UBlueprint* Blueprint, const FBlueprintVariableDefinition& Definition)
{
	if (!Blueprint)
	{
		return FBlueprintAutomationResult::Error(EBlueprintAutomationResultCode::InvalidArgument, TEXT("Blueprint is null."));
	}

	if (Definition.Name.IsNone())
	{
		return FBlueprintAutomationResult::Error(EBlueprintAutomationResultCode::InvalidArgument, TEXT("Variable name is empty."), Blueprint);
	}

	for (const FBPVariableDescription& ExistingVariable : Blueprint->NewVariables)
	{
		if (ExistingVariable.VarName == Definition.Name)
		{
			return FBlueprintAutomationResult::Error(
				EBlueprintAutomationResultCode::AlreadyExists,
				FString::Printf(TEXT("Variable '%s' already exists on Blueprint '%s'."), *Definition.Name.ToString(), *Blueprint->GetPathName()),
				Blueprint);
		}
	}

	const bool bAdded = FBlueprintEditorUtils::AddMemberVariable(
		Blueprint,
		Definition.Name,
		MakePinType(Definition.Type),
		Definition.DefaultValue);

	if (!bAdded)
	{
		return FBlueprintAutomationResult::Error(
			EBlueprintAutomationResultCode::Failed,
			FString::Printf(TEXT("Failed to add variable '%s' to Blueprint '%s'."), *Definition.Name.ToString(), *Blueprint->GetPathName()),
			Blueprint);
	}

	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
	Blueprint->MarkPackageDirty();

	return FBlueprintAutomationResult::Ok(
		FString::Printf(TEXT("Added variable '%s' to Blueprint '%s'."), *Definition.Name.ToString(), *Blueprint->GetPathName()),
		Blueprint);
}

FBlueprintAutomationResult FBlueprintAutomationService::AddFloatVariable(UBlueprint* Blueprint, const FName VariableName, const double DefaultValue)
{
	FBlueprintVariableDefinition Definition;
	Definition.Name = VariableName;
	Definition.Type = EBlueprintPrimitiveVariableType::Float;
	Definition.DefaultValue = FString::SanitizeFloat(DefaultValue);
	return AddVariable(Blueprint, Definition);
}

FBlueprintAutomationResult FBlueprintAutomationService::AddBoolVariable(UBlueprint* Blueprint, const FName VariableName, const bool bDefaultValue)
{
	FBlueprintVariableDefinition Definition;
	Definition.Name = VariableName;
	Definition.Type = EBlueprintPrimitiveVariableType::Bool;
	Definition.DefaultValue = bDefaultValue ? TEXT("true") : TEXT("false");
	return AddVariable(Blueprint, Definition);
}

FBlueprintAutomationResult FBlueprintAutomationService::AddIntVariable(UBlueprint* Blueprint, const FName VariableName, const int32 DefaultValue)
{
	FBlueprintVariableDefinition Definition;
	Definition.Name = VariableName;
	Definition.Type = EBlueprintPrimitiveVariableType::Int32;
	Definition.DefaultValue = FString::FromInt(DefaultValue);
	return AddVariable(Blueprint, Definition);
}

FBlueprintAutomationResult FBlueprintAutomationService::AddStringVariable(UBlueprint* Blueprint, const FName VariableName, const FString& DefaultValue)
{
	FBlueprintVariableDefinition Definition;
	Definition.Name = VariableName;
	Definition.Type = EBlueprintPrimitiveVariableType::String;
	Definition.DefaultValue = DefaultValue;
	return AddVariable(Blueprint, Definition);
}

FBlueprintAutomationResult FBlueprintAutomationService::AddNameVariable(UBlueprint* Blueprint, const FName VariableName, const FName DefaultValue)
{
	FBlueprintVariableDefinition Definition;
	Definition.Name = VariableName;
	Definition.Type = EBlueprintPrimitiveVariableType::Name;
	Definition.DefaultValue = DefaultValue.ToString();
	return AddVariable(Blueprint, Definition);
}

FBlueprintAutomationResult FBlueprintAutomationService::AddComponent(
	UBlueprint* Blueprint,
	TSubclassOf<UActorComponent> ComponentClass,
	const FName ComponentName,
	const FName AttachParentName,
	const bool bMakeRootIfNoRootExists)
{
	if (!Blueprint)
	{
		return FBlueprintAutomationResult::Error(EBlueprintAutomationResultCode::InvalidArgument, TEXT("Blueprint is null."));
	}

	if (!*ComponentClass)
	{
		return FBlueprintAutomationResult::Error(EBlueprintAutomationResultCode::InvalidArgument, TEXT("Component class is null."), Blueprint);
	}

	if (ComponentName.IsNone())
	{
		return FBlueprintAutomationResult::Error(EBlueprintAutomationResultCode::InvalidArgument, TEXT("Component name is empty."), Blueprint);
	}

	USimpleConstructionScript* SimpleConstructionScript = Blueprint->SimpleConstructionScript;
	if (!SimpleConstructionScript)
	{
		return FBlueprintAutomationResult::Error(
			EBlueprintAutomationResultCode::Unsupported,
			FString::Printf(TEXT("Blueprint '%s' does not expose a SimpleConstructionScript."), *Blueprint->GetPathName()),
			Blueprint);
	}

	if (FindComponentNodeByName(Blueprint, ComponentName) != nullptr)
	{
		return FBlueprintAutomationResult::Error(
			EBlueprintAutomationResultCode::AlreadyExists,
			FString::Printf(TEXT("Component '%s' already exists on Blueprint '%s'."), *ComponentName.ToString(), *Blueprint->GetPathName()),
			Blueprint);
	}

	USCS_Node* NewNode = SimpleConstructionScript->CreateNode(ComponentClass, ComponentName);
	if (!NewNode)
	{
		return FBlueprintAutomationResult::Error(
			EBlueprintAutomationResultCode::Failed,
			FString::Printf(TEXT("Failed to create component node '%s' on Blueprint '%s'."), *ComponentName.ToString(), *Blueprint->GetPathName()),
			Blueprint);
	}

	USCS_Node* AttachParent = nullptr;
	if (!AttachParentName.IsNone())
	{
		AttachParent = FindComponentNodeByName(Blueprint, AttachParentName);
		if (!AttachParent)
		{
			return FBlueprintAutomationResult::Error(
				EBlueprintAutomationResultCode::NotFound,
				FString::Printf(TEXT("Attach parent component '%s' was not found on Blueprint '%s'."), *AttachParentName.ToString(), *Blueprint->GetPathName()),
				Blueprint);
		}
	}

	const bool bIsSceneComponent = ComponentClass->IsChildOf(USceneComponent::StaticClass());
	if (AttachParent)
	{
		AttachParent->AddChildNode(NewNode);
	}
	else if (bIsSceneComponent)
	{
		const TArray<USCS_Node*>& RootNodes = SimpleConstructionScript->GetRootNodes();
		if (RootNodes.Num() == 0 && bMakeRootIfNoRootExists)
		{
			SimpleConstructionScript->AddNode(NewNode);
		}
		else if (RootNodes.Num() > 0)
		{
			RootNodes[0]->AddChildNode(NewNode);
		}
		else
		{
			SimpleConstructionScript->AddNode(NewNode);
		}
	}
	else
	{
		SimpleConstructionScript->AddNode(NewNode);
	}

	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
	Blueprint->MarkPackageDirty();

	return FBlueprintAutomationResult::Ok(
		FString::Printf(TEXT("Added component '%s' (%s) to Blueprint '%s'."), *ComponentName.ToString(), *ComponentClass->GetPathName(), *Blueprint->GetPathName()),
		Blueprint,
		NewNode);
}

FBlueprintAutomationResult FBlueprintAutomationService::AddSceneComponent(
	UBlueprint* Blueprint,
	const FName ComponentName,
	const FName AttachParentName,
	const bool bMakeRootIfNoRootExists)
{
	return AddComponent(Blueprint, USceneComponent::StaticClass(), ComponentName, AttachParentName, bMakeRootIfNoRootExists);
}

FBlueprintAutomationResult FBlueprintAutomationService::AddStaticMeshComponent(
	UBlueprint* Blueprint,
	const FName ComponentName,
	const FName AttachParentName)
{
	return AddComponent(Blueprint, UStaticMeshComponent::StaticClass(), ComponentName, AttachParentName, false);
}

FBlueprintAutomationResult FBlueprintAutomationService::CompileBlueprint(UBlueprint* Blueprint)
{
	if (!Blueprint)
	{
		return FBlueprintAutomationResult::Error(EBlueprintAutomationResultCode::InvalidArgument, TEXT("Blueprint is null."));
	}

	FKismetEditorUtilities::CompileBlueprint(Blueprint);

	if (Blueprint->Status == BS_Error)
	{
		return FBlueprintAutomationResult::Error(
			EBlueprintAutomationResultCode::Failed,
			FString::Printf(TEXT("Blueprint '%s' compiled with errors."), *Blueprint->GetPathName()),
			Blueprint);
	}

	return FBlueprintAutomationResult::Ok(
		FString::Printf(TEXT("Compiled Blueprint '%s'."), *Blueprint->GetPathName()),
		Blueprint);
}

FBlueprintAutomationResult FBlueprintAutomationService::SaveBlueprint(UBlueprint* Blueprint)
{
	if (!Blueprint)
	{
		return FBlueprintAutomationResult::Error(EBlueprintAutomationResultCode::InvalidArgument, TEXT("Blueprint is null."));
	}

	UPackage* Package = Blueprint->GetOutermost();
	if (!Package)
	{
		return FBlueprintAutomationResult::Error(
			EBlueprintAutomationResultCode::Failed,
			FString::Printf(TEXT("Blueprint '%s' has no outer package."), *Blueprint->GetPathName()),
			Blueprint);
	}

	const FString PackageName = Package->GetName();
	const FString PackageFilename = FPackageName::LongPackageNameToFilename(PackageName, FPackageName::GetAssetPackageExtension());
	Package->MarkPackageDirty();

	FSavePackageArgs SaveArgs;
	SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
	SaveArgs.Error = GError;
	SaveArgs.SaveFlags = SAVE_None;

	const bool bSaved = UPackage::SavePackage(Package, Blueprint, *PackageFilename, SaveArgs);
	if (!bSaved)
	{
		return FBlueprintAutomationResult::Error(
			EBlueprintAutomationResultCode::Failed,
			FString::Printf(TEXT("Failed to save Blueprint package '%s' to '%s'."), *PackageName, *PackageFilename),
			Blueprint);
	}

	return FBlueprintAutomationResult::Ok(
		FString::Printf(TEXT("Saved Blueprint '%s'."), *Blueprint->GetPathName()),
		Blueprint);
}

FEdGraphPinType FBlueprintAutomationService::MakePinType(const EBlueprintPrimitiveVariableType Type)
{
	FEdGraphPinType PinType;

	switch (Type)
	{
	case EBlueprintPrimitiveVariableType::Float:
		// UE5 uses PC_Real + PC_Float. Older engines may accept PC_Float directly.
		PinType.PinCategory = UEdGraphSchema_K2::PC_Real;
		PinType.PinSubCategory = UEdGraphSchema_K2::PC_Float;
		break;
	case EBlueprintPrimitiveVariableType::Bool:
		PinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
		break;
	case EBlueprintPrimitiveVariableType::Int32:
		PinType.PinCategory = UEdGraphSchema_K2::PC_Int;
		break;
	case EBlueprintPrimitiveVariableType::String:
		PinType.PinCategory = UEdGraphSchema_K2::PC_String;
		break;
	case EBlueprintPrimitiveVariableType::Name:
		PinType.PinCategory = UEdGraphSchema_K2::PC_Name;
		break;
	default:
		PinType.PinCategory = UEdGraphSchema_K2::PC_Wildcard;
		break;
	}

	return PinType;
}

FString FBlueprintAutomationService::MakeBlueprintObjectPath(const FString& AssetPath)
{
	const FString AssetName = FPackageName::GetLongPackageAssetName(AssetPath);
	return FString::Printf(TEXT("%s.%s"), *AssetPath, *AssetName);
}

bool FBlueprintAutomationService::TryNormalizeAssetPath(
	const FString& InPath,
	FString& OutLongPackageName,
	FString& OutObjectPath,
	FString& OutAssetName,
	FString& OutError)
{
	FString Sanitized = BlueprintAutomationServicePrivate::SanitizePath(InPath);
	if (Sanitized.IsEmpty())
	{
		OutError = TEXT("Asset path is empty.");
		return false;
	}

	if (FPackageName::IsValidObjectPath(Sanitized))
	{
		OutLongPackageName = FPackageName::ObjectPathToPackageName(Sanitized);
	}
	else
	{
		OutLongPackageName = Sanitized;
	}

	if (!FPackageName::IsValidLongPackageName(OutLongPackageName))
	{
		OutError = FString::Printf(TEXT("'%s' is not a valid long package or object path."), *InPath);
		return false;
	}

	OutAssetName = FPackageName::GetLongPackageAssetName(OutLongPackageName);
	if (OutAssetName.IsEmpty())
	{
		OutError = FString::Printf(TEXT("Could not resolve asset name from '%s'."), *InPath);
		return false;
	}

	OutObjectPath = MakeBlueprintObjectPath(OutLongPackageName);
	return true;
}

USCS_Node* FBlueprintAutomationService::FindComponentNodeByName(const UBlueprint* Blueprint, const FName ComponentName)
{
	if (!Blueprint || !Blueprint->SimpleConstructionScript)
	{
		return nullptr;
	}

	for (USCS_Node* Node : Blueprint->SimpleConstructionScript->GetAllNodes())
	{
		if (!Node)
		{
			continue;
		}

		if (Node->GetVariableName() == ComponentName || Node->GetName() == ComponentName.ToString())
		{
			return Node;
		}
	}

	return nullptr;
}
