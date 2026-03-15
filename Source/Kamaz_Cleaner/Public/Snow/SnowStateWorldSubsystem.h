#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Snow/PersistentSnowStateTypes.h"
#include "SnowStateWorldSubsystem.generated.h"

class USnowStateRuntimeSettings;

UCLASS()
class KAMAZ_CLEANER_API USnowStateWorldSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()

public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    UFUNCTION(BlueprintPure, Category = "Snow State")
    bool IsPersistentSnowStateEnabled() const;

    UFUNCTION(BlueprintPure, Category = "Snow State")
    FSnowWorldCellId ResolveCellIdFromWorldLocation(FVector WorldLocation) const;

    UFUNCTION(BlueprintPure, Category = "Snow State")
    FVector2D ResolveCellUvFromWorldLocation(FVector WorldLocation) const;

    UFUNCTION(BlueprintPure, Category = "Snow State")
    FSnowCellBounds2D GetCellBoundsFromId(const FSnowWorldCellId& CellId) const;

    UFUNCTION(BlueprintPure, Category = "Snow State")
    TArray<FSnowWorldCellId> GetCellsOverlappingWorldBox(FVector2D WorldMin, FVector2D WorldMax) const;

    UFUNCTION(BlueprintCallable, Category = "Snow State")
    FSnowCellSnapshot FindOrAddCellAtWorldLocation(FVector WorldLocation, ESnowReceiverSurfaceFamily SurfaceFamily = ESnowReceiverSurfaceFamily::Unknown);

    UFUNCTION(BlueprintCallable, Category = "Snow State")
    FSnowCellSnapshot MarkWorldLocationDirty(
        FVector WorldLocation,
        ESnowReceiverSurfaceFamily SurfaceFamily = ESnowReceiverSurfaceFamily::Unknown,
        int32 PixelHintX = -1,
        int32 PixelHintY = -1
    );

    UFUNCTION(BlueprintCallable, Category = "Snow State")
    TArray<FSnowCellSnapshot> MarkWorldBoxDirty(FVector2D WorldMin, FVector2D WorldMax, ESnowReceiverSurfaceFamily SurfaceFamily = ESnowReceiverSurfaceFamily::Unknown);

    UFUNCTION(BlueprintPure, Category = "Snow State")
    TArray<FSnowWorldCellId> GetActiveCellIds() const;

    UFUNCTION(BlueprintPure, Category = "Snow State")
    FString BuildCellSaveRelativePath(const FSnowWorldCellId& CellId) const;

    UFUNCTION(BlueprintPure, Category = "Snow State")
    FString BuildCellSaveAbsolutePath(const FSnowWorldCellId& CellId) const;

    UFUNCTION(BlueprintCallable, Category = "Snow State")
    TArray<FSnowCellSnapshot> FlushDirtyCellsToDisk();

    UFUNCTION(BlueprintCallable, Category = "Snow State")
    bool FlushCellToDisk(const FSnowWorldCellId& CellId, FSnowCellSnapshot& OutSnapshot, FString& OutAbsolutePath);

private:
    struct FCellRuntimeEntry
    {
        FSnowCellSnapshot Snapshot;
    };

    const USnowStateRuntimeSettings* GetSettings() const;
    float GetCellWorldSizeCm() const;
    int32 GetCellResolution() const;
    FCellRuntimeEntry& FindOrAddCellInternal(const FSnowWorldCellId& CellId, ESnowReceiverSurfaceFamily SurfaceFamily);
    FIntPoint WorldToPixelHint(const FVector& WorldLocation) const;
    FSnowDirtyRect WorldBoxToDirtyRect(const FSnowWorldCellId& CellId, const FVector2D& WorldMin, const FVector2D& WorldMax) const;
    void MaybeAutoFlushDirtyCells();
    bool FlushCellEntryToDisk(const FSnowWorldCellId& CellId, FCellRuntimeEntry& Entry, FString* OutAbsolutePath = nullptr);

    TMap<FSnowWorldCellId, FCellRuntimeEntry> ActiveCells;
    double LastDirtyFlushTimeSeconds = 0.0;
};
