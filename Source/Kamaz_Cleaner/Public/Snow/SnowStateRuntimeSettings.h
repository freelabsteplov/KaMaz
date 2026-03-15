#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "SnowStateRuntimeSettings.generated.h"

UCLASS(Config = Game, DefaultConfig, meta = (DisplayName = "Persistent Snow State"))
class KAMAZ_CLEANER_API USnowStateRuntimeSettings : public UDeveloperSettings
{
    GENERATED_BODY()

public:
    USnowStateRuntimeSettings();

    virtual FName GetCategoryName() const override;

    UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Persistent Snow State")
    bool bEnablePersistentSnowStateV1 = false;

    UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Persistent Snow State", meta = (ClampMin = "1.0"))
    float CellWorldSizeMeters = 64.0f;

    UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Persistent Snow State", meta = (ClampMin = "64"))
    int32 CellTextureResolution = 512;

    UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Persistent Snow State", meta = (ClampMin = "0"))
    int32 ActiveCellRadius = 1;

    UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Persistent Snow State", meta = (ClampMin = "1"))
    int32 MaxResidentCells = 16;

    UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Persistent Snow State", meta = (ClampMin = "0.1"))
    float DirtyFlushIntervalSeconds = 5.0f;

    UPROPERTY(Config, EditAnywhere, BlueprintReadOnly, Category = "Persistent Snow State")
    FString SavedTileRoot = TEXT("SnowState/MoscowEA5");
};
