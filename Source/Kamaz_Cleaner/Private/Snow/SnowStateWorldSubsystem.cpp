#include "Snow/SnowStateWorldSubsystem.h"

#include "Containers/UnrealString.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformTime.h"
#include "Json.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Snow/SnowStateRuntimeSettings.h"

namespace
{
    FString SurfaceFamilyToString(const ESnowReceiverSurfaceFamily SurfaceFamily)
    {
        if (const UEnum* Enum = StaticEnum<ESnowReceiverSurfaceFamily>())
        {
            return Enum->GetNameStringByValue(static_cast<int64>(SurfaceFamily));
        }

        return TEXT("Unknown");
    }
}

bool USnowStateWorldSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
    const UWorld* World = Cast<UWorld>(Outer);
    if (World == nullptr)
    {
        return false;
    }

    return World->IsGameWorld() || World->WorldType == EWorldType::Editor;
}

void USnowStateWorldSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    ActiveCells.Reset();
    LastDirtyFlushTimeSeconds = FPlatformTime::Seconds();
}

void USnowStateWorldSubsystem::Deinitialize()
{
    FlushDirtyCellsToDisk();
    ActiveCells.Reset();
    Super::Deinitialize();
}

bool USnowStateWorldSubsystem::IsPersistentSnowStateEnabled() const
{
    const USnowStateRuntimeSettings* Settings = GetSettings();
    return Settings != nullptr && Settings->bEnablePersistentSnowStateV1;
}

FSnowWorldCellId USnowStateWorldSubsystem::ResolveCellIdFromWorldLocation(const FVector WorldLocation) const
{
    const float CellWorldSizeCm = GetCellWorldSizeCm();
    return FSnowWorldCellId(
        FMath::FloorToInt(WorldLocation.X / CellWorldSizeCm),
        FMath::FloorToInt(WorldLocation.Y / CellWorldSizeCm)
    );
}

FVector2D USnowStateWorldSubsystem::ResolveCellUvFromWorldLocation(const FVector WorldLocation) const
{
    const FSnowWorldCellId CellId = ResolveCellIdFromWorldLocation(WorldLocation);
    const FSnowCellBounds2D Bounds = GetCellBoundsFromId(CellId);
    const FVector2D CellSize = Bounds.WorldMax - Bounds.WorldMin;

    if (CellSize.X <= KINDA_SMALL_NUMBER || CellSize.Y <= KINDA_SMALL_NUMBER)
    {
        return FVector2D::ZeroVector;
    }

    const double U = (static_cast<double>(WorldLocation.X) - Bounds.WorldMin.X) / CellSize.X;
    const double V = (static_cast<double>(WorldLocation.Y) - Bounds.WorldMin.Y) / CellSize.Y;
    return FVector2D(FMath::Clamp(U, 0.0, 1.0), FMath::Clamp(V, 0.0, 1.0));
}

FSnowCellBounds2D USnowStateWorldSubsystem::GetCellBoundsFromId(const FSnowWorldCellId& CellId) const
{
    const float CellWorldSizeCm = GetCellWorldSizeCm();
    const FVector2D WorldMin(CellId.X * CellWorldSizeCm, CellId.Y * CellWorldSizeCm);
    FSnowCellBounds2D Bounds;
    Bounds.WorldMin = WorldMin;
    Bounds.WorldMax = WorldMin + FVector2D(CellWorldSizeCm, CellWorldSizeCm);
    return Bounds;
}

TArray<FSnowWorldCellId> USnowStateWorldSubsystem::GetCellsOverlappingWorldBox(const FVector2D WorldMin, const FVector2D WorldMax) const
{
    const float MinX = FMath::Min(WorldMin.X, WorldMax.X);
    const float MinY = FMath::Min(WorldMin.Y, WorldMax.Y);
    const float MaxX = FMath::Max(WorldMin.X, WorldMax.X);
    const float MaxY = FMath::Max(WorldMin.Y, WorldMax.Y);

    const float CellWorldSizeCm = GetCellWorldSizeCm();
    const int32 CellMinX = FMath::FloorToInt(MinX / CellWorldSizeCm);
    const int32 CellMinY = FMath::FloorToInt(MinY / CellWorldSizeCm);
    const int32 CellMaxX = FMath::FloorToInt(MaxX / CellWorldSizeCm);
    const int32 CellMaxY = FMath::FloorToInt(MaxY / CellWorldSizeCm);

    TArray<FSnowWorldCellId> CellIds;
    for (int32 X = CellMinX; X <= CellMaxX; ++X)
    {
        for (int32 Y = CellMinY; Y <= CellMaxY; ++Y)
        {
            CellIds.Emplace(X, Y);
        }
    }
    return CellIds;
}

FSnowCellSnapshot USnowStateWorldSubsystem::FindOrAddCellAtWorldLocation(const FVector WorldLocation, const ESnowReceiverSurfaceFamily SurfaceFamily)
{
    const FSnowWorldCellId CellId = ResolveCellIdFromWorldLocation(WorldLocation);
    return FindOrAddCellInternal(CellId, SurfaceFamily).Snapshot;
}

FSnowCellSnapshot USnowStateWorldSubsystem::MarkWorldLocationDirty(
    const FVector WorldLocation,
    const ESnowReceiverSurfaceFamily SurfaceFamily,
    const int32 PixelHintX,
    const int32 PixelHintY
)
{
    const FSnowWorldCellId CellId = ResolveCellIdFromWorldLocation(WorldLocation);
    FCellRuntimeEntry& Entry = FindOrAddCellInternal(CellId, SurfaceFamily);

    Entry.Snapshot.bIsDirty = true;
    Entry.Snapshot.LastTouchedTimeSeconds = FPlatformTime::Seconds();
    Entry.Snapshot.PendingWriteCount += 1;
    if (SurfaceFamily != ESnowReceiverSurfaceFamily::Unknown)
    {
        Entry.Snapshot.DominantSurfaceFamily = SurfaceFamily;
    }

    const FIntPoint Pixel = (PixelHintX >= 0 && PixelHintY >= 0)
        ? FIntPoint(PixelHintX, PixelHintY)
        : WorldToPixelHint(WorldLocation);
    Entry.Snapshot.DirtyRect.IncludePixel(Pixel);
    MaybeAutoFlushDirtyCells();
    return Entry.Snapshot;
}

TArray<FSnowCellSnapshot> USnowStateWorldSubsystem::MarkWorldBoxDirty(
    const FVector2D WorldMin,
    const FVector2D WorldMax,
    const ESnowReceiverSurfaceFamily SurfaceFamily
)
{
    const TArray<FSnowWorldCellId> OverlappedCells = GetCellsOverlappingWorldBox(WorldMin, WorldMax);
    TArray<FSnowCellSnapshot> UpdatedSnapshots;
    UpdatedSnapshots.Reserve(OverlappedCells.Num());

    for (const FSnowWorldCellId& CellId : OverlappedCells)
    {
        FCellRuntimeEntry& Entry = FindOrAddCellInternal(CellId, SurfaceFamily);
        Entry.Snapshot.bIsDirty = true;
        Entry.Snapshot.LastTouchedTimeSeconds = FPlatformTime::Seconds();
        Entry.Snapshot.PendingWriteCount += 1;
        if (SurfaceFamily != ESnowReceiverSurfaceFamily::Unknown)
        {
            Entry.Snapshot.DominantSurfaceFamily = SurfaceFamily;
        }

        const FSnowDirtyRect Rect = WorldBoxToDirtyRect(CellId, WorldMin, WorldMax);
        if (Rect.bIsValid)
        {
            Entry.Snapshot.DirtyRect.IncludePixel(FIntPoint(Rect.MinX, Rect.MinY));
            Entry.Snapshot.DirtyRect.IncludePixel(FIntPoint(Rect.MaxX, Rect.MaxY));
        }

        UpdatedSnapshots.Add(Entry.Snapshot);
    }

    MaybeAutoFlushDirtyCells();
    return UpdatedSnapshots;
}

TArray<FSnowWorldCellId> USnowStateWorldSubsystem::GetActiveCellIds() const
{
    TArray<FSnowWorldCellId> CellIds;
    ActiveCells.GetKeys(CellIds);
    CellIds.Sort([](const FSnowWorldCellId& A, const FSnowWorldCellId& B)
    {
        return (A.X == B.X) ? (A.Y < B.Y) : (A.X < B.X);
    });
    return CellIds;
}

FString USnowStateWorldSubsystem::BuildCellSaveRelativePath(const FSnowWorldCellId& CellId) const
{
    const USnowStateRuntimeSettings* Settings = GetSettings();
    const FString Root = Settings ? Settings->SavedTileRoot : FString(TEXT("SnowState/MoscowEA5"));
    return FString::Printf(TEXT("%s/Tile_%d_%d.json"), *Root, CellId.X, CellId.Y);
}

FString USnowStateWorldSubsystem::BuildCellSaveAbsolutePath(const FSnowWorldCellId& CellId) const
{
    return FPaths::Combine(FPaths::ProjectSavedDir(), BuildCellSaveRelativePath(CellId));
}

TArray<FSnowCellSnapshot> USnowStateWorldSubsystem::FlushDirtyCellsToDisk()
{
    TArray<FSnowCellSnapshot> FlushedSnapshots;

    TArray<FSnowWorldCellId> CellIds;
    ActiveCells.GetKeys(CellIds);
    CellIds.Sort([](const FSnowWorldCellId& A, const FSnowWorldCellId& B)
    {
        return (A.X == B.X) ? (A.Y < B.Y) : (A.X < B.X);
    });

    for (const FSnowWorldCellId& CellId : CellIds)
    {
        if (FCellRuntimeEntry* Entry = ActiveCells.Find(CellId))
        {
            if (Entry->Snapshot.bIsDirty && FlushCellEntryToDisk(CellId, *Entry))
            {
                FlushedSnapshots.Add(Entry->Snapshot);
            }
        }
    }

    LastDirtyFlushTimeSeconds = FPlatformTime::Seconds();
    return FlushedSnapshots;
}

bool USnowStateWorldSubsystem::FlushCellToDisk(const FSnowWorldCellId& CellId, FSnowCellSnapshot& OutSnapshot, FString& OutAbsolutePath)
{
    if (FCellRuntimeEntry* Entry = ActiveCells.Find(CellId))
    {
        const bool bSaved = FlushCellEntryToDisk(CellId, *Entry, &OutAbsolutePath);
        OutSnapshot = Entry->Snapshot;
        return bSaved;
    }

    OutSnapshot = FSnowCellSnapshot();
    OutAbsolutePath.Reset();
    return false;
}

const USnowStateRuntimeSettings* USnowStateWorldSubsystem::GetSettings() const
{
    return GetDefault<USnowStateRuntimeSettings>();
}

float USnowStateWorldSubsystem::GetCellWorldSizeCm() const
{
    const USnowStateRuntimeSettings* Settings = GetSettings();
    const float CellWorldSizeMeters = Settings ? Settings->CellWorldSizeMeters : 64.0f;
    return FMath::Max(CellWorldSizeMeters, 1.0f) * 100.0f;
}

int32 USnowStateWorldSubsystem::GetCellResolution() const
{
    const USnowStateRuntimeSettings* Settings = GetSettings();
    return Settings ? FMath::Max(Settings->CellTextureResolution, 1) : 512;
}

USnowStateWorldSubsystem::FCellRuntimeEntry& USnowStateWorldSubsystem::FindOrAddCellInternal(const FSnowWorldCellId& CellId, const ESnowReceiverSurfaceFamily SurfaceFamily)
{
    FCellRuntimeEntry* ExistingEntry = ActiveCells.Find(CellId);
    if (ExistingEntry != nullptr)
    {
        if (SurfaceFamily != ESnowReceiverSurfaceFamily::Unknown)
        {
            ExistingEntry->Snapshot.DominantSurfaceFamily = SurfaceFamily;
        }
        return *ExistingEntry;
    }

    FCellRuntimeEntry NewEntry;
    NewEntry.Snapshot.CellId = CellId;
    NewEntry.Snapshot.DominantSurfaceFamily = SurfaceFamily;
    NewEntry.Snapshot.SaveRelativePath = BuildCellSaveRelativePath(CellId);
    return ActiveCells.Add(CellId, MoveTemp(NewEntry));
}

FIntPoint USnowStateWorldSubsystem::WorldToPixelHint(const FVector& WorldLocation) const
{
    const FVector2D UV = ResolveCellUvFromWorldLocation(WorldLocation);
    const int32 Resolution = GetCellResolution();
    const int32 PixelX = FMath::Clamp(FMath::FloorToInt(UV.X * static_cast<double>(Resolution)), 0, Resolution - 1);
    const int32 PixelY = FMath::Clamp(FMath::FloorToInt(UV.Y * static_cast<double>(Resolution)), 0, Resolution - 1);
    return FIntPoint(PixelX, PixelY);
}

FSnowDirtyRect USnowStateWorldSubsystem::WorldBoxToDirtyRect(
    const FSnowWorldCellId& CellId,
    const FVector2D& WorldMin,
    const FVector2D& WorldMax
) const
{
    const FVector2D BoxMin(FMath::Min(WorldMin.X, WorldMax.X), FMath::Min(WorldMin.Y, WorldMax.Y));
    const FVector2D BoxMax(FMath::Max(WorldMin.X, WorldMax.X), FMath::Max(WorldMin.Y, WorldMax.Y));
    const FSnowCellBounds2D Bounds = GetCellBoundsFromId(CellId);

    const FVector2D OverlapMin(FMath::Max(BoxMin.X, Bounds.WorldMin.X), FMath::Max(BoxMin.Y, Bounds.WorldMin.Y));
    const FVector2D OverlapMax(FMath::Min(BoxMax.X, Bounds.WorldMax.X), FMath::Min(BoxMax.Y, Bounds.WorldMax.Y));

    FSnowDirtyRect Rect;
    if (OverlapMin.X > OverlapMax.X || OverlapMin.Y > OverlapMax.Y)
    {
        return Rect;
    }

    const int32 Resolution = GetCellResolution();
    const FVector2D CellSize = Bounds.WorldMax - Bounds.WorldMin;
    if (CellSize.X <= KINDA_SMALL_NUMBER || CellSize.Y <= KINDA_SMALL_NUMBER)
    {
        return Rect;
    }

    const auto ToPixelX = [&](const double Value)
    {
        return FMath::Clamp(FMath::FloorToInt(((Value - Bounds.WorldMin.X) / CellSize.X) * Resolution), 0, Resolution - 1);
    };

    const auto ToPixelY = [&](const double Value)
    {
        return FMath::Clamp(FMath::FloorToInt(((Value - Bounds.WorldMin.Y) / CellSize.Y) * Resolution), 0, Resolution - 1);
    };

    Rect.MinX = ToPixelX(OverlapMin.X);
    Rect.MinY = ToPixelY(OverlapMin.Y);
    Rect.MaxX = ToPixelX(OverlapMax.X);
    Rect.MaxY = ToPixelY(OverlapMax.Y);
    Rect.bIsValid = true;
    return Rect;
}

void USnowStateWorldSubsystem::MaybeAutoFlushDirtyCells()
{
    const USnowStateRuntimeSettings* Settings = GetSettings();
    const double FlushInterval = Settings ? FMath::Max(Settings->DirtyFlushIntervalSeconds, 0.1f) : 5.0;
    const double Now = FPlatformTime::Seconds();
    if ((Now - LastDirtyFlushTimeSeconds) < FlushInterval)
    {
        return;
    }

    FlushDirtyCellsToDisk();
}

bool USnowStateWorldSubsystem::FlushCellEntryToDisk(const FSnowWorldCellId& CellId, FCellRuntimeEntry& Entry, FString* OutAbsolutePath)
{
    if (!Entry.Snapshot.bIsDirty)
    {
        return false;
    }

    const FString AbsolutePath = BuildCellSaveAbsolutePath(CellId);
    if (OutAbsolutePath)
    {
        *OutAbsolutePath = AbsolutePath;
    }

    if (!IFileManager::Get().MakeDirectory(*FPaths::GetPath(AbsolutePath), true))
    {
        return false;
    }

    const FSnowCellBounds2D Bounds = GetCellBoundsFromId(CellId);
    const double SavedAtSeconds = FPlatformTime::Seconds();

    TSharedRef<FJsonObject> RootObject = MakeShared<FJsonObject>();
    RootObject->SetStringField(TEXT("schema"), TEXT("persistent_snow_state_tile_v1"));
    RootObject->SetNumberField(TEXT("saved_at_seconds"), SavedAtSeconds);
    RootObject->SetNumberField(TEXT("cell_world_size_cm"), GetCellWorldSizeCm());
    RootObject->SetNumberField(TEXT("cell_resolution"), GetCellResolution());
    RootObject->SetStringField(TEXT("save_relative_path"), Entry.Snapshot.SaveRelativePath);
    RootObject->SetBoolField(TEXT("is_dirty"), Entry.Snapshot.bIsDirty);
    RootObject->SetNumberField(TEXT("last_touched_time_seconds"), Entry.Snapshot.LastTouchedTimeSeconds);
    RootObject->SetNumberField(TEXT("pending_write_count"), Entry.Snapshot.PendingWriteCount);
    RootObject->SetStringField(TEXT("dominant_surface_family"), SurfaceFamilyToString(Entry.Snapshot.DominantSurfaceFamily));

    TSharedRef<FJsonObject> CellIdObject = MakeShared<FJsonObject>();
    CellIdObject->SetNumberField(TEXT("x"), CellId.X);
    CellIdObject->SetNumberField(TEXT("y"), CellId.Y);
    RootObject->SetObjectField(TEXT("cell_id"), CellIdObject);

    TSharedRef<FJsonObject> DirtyRectObject = MakeShared<FJsonObject>();
    DirtyRectObject->SetBoolField(TEXT("is_valid"), Entry.Snapshot.DirtyRect.bIsValid);
    DirtyRectObject->SetNumberField(TEXT("min_x"), Entry.Snapshot.DirtyRect.MinX);
    DirtyRectObject->SetNumberField(TEXT("min_y"), Entry.Snapshot.DirtyRect.MinY);
    DirtyRectObject->SetNumberField(TEXT("max_x"), Entry.Snapshot.DirtyRect.MaxX);
    DirtyRectObject->SetNumberField(TEXT("max_y"), Entry.Snapshot.DirtyRect.MaxY);
    RootObject->SetObjectField(TEXT("dirty_rect"), DirtyRectObject);

    TSharedRef<FJsonObject> BoundsObject = MakeShared<FJsonObject>();
    BoundsObject->SetNumberField(TEXT("world_min_x"), Bounds.WorldMin.X);
    BoundsObject->SetNumberField(TEXT("world_min_y"), Bounds.WorldMin.Y);
    BoundsObject->SetNumberField(TEXT("world_max_x"), Bounds.WorldMax.X);
    BoundsObject->SetNumberField(TEXT("world_max_y"), Bounds.WorldMax.Y);
    RootObject->SetObjectField(TEXT("world_bounds"), BoundsObject);

    FString JsonOutput;
    const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&JsonOutput);
    if (!FJsonSerializer::Serialize(RootObject, Writer))
    {
        return false;
    }

    if (!FFileHelper::SaveStringToFile(JsonOutput, *AbsolutePath, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))
    {
        return false;
    }

    Entry.Snapshot.bIsDirty = false;
    Entry.Snapshot.PendingWriteCount = 0;
    Entry.Snapshot.DirtyRect = FSnowDirtyRect();
    Entry.Snapshot.LastTouchedTimeSeconds = SavedAtSeconds;
    return true;
}
