#include "Snow/SnowStateBlueprintLibrary.h"

#include "Components/ActorComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/Engine.h"
#include "GameFramework/Actor.h"
#include "Snow/SnowStateWorldSubsystem.h"

namespace
{
    USnowStateWorldSubsystem* ResolveSnowSubsystem(UObject* WorldContextObject)
    {
        if (!WorldContextObject)
        {
            return nullptr;
        }

        UWorld* World = WorldContextObject->GetWorld();
        if (!World && GEngine)
        {
            World = GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::ReturnNull);
        }

        return World ? World->GetSubsystem<USnowStateWorldSubsystem>() : nullptr;
    }

    FVector ResolveWriterWorldLocation(UActorComponent* SourceComponent)
    {
        if (const USceneComponent* SceneComponent = Cast<USceneComponent>(SourceComponent))
        {
            return SceneComponent->GetComponentLocation();
        }

        if (const AActor* Owner = SourceComponent ? SourceComponent->GetOwner() : nullptr)
        {
            return Owner->GetActorLocation();
        }

        return FVector::ZeroVector;
    }

    FRotator ResolveWriterWorldRotation(UActorComponent* SourceComponent)
    {
        if (const USceneComponent* SceneComponent = Cast<USceneComponent>(SourceComponent))
        {
            return SceneComponent->GetComponentRotation();
        }

        if (const AActor* Owner = SourceComponent ? SourceComponent->GetOwner() : nullptr)
        {
            return Owner->GetActorRotation();
        }

        return FRotator::ZeroRotator;
    }

    TArray<FSnowCellSnapshot> FlushIfRequested(USnowStateWorldSubsystem* Subsystem, const bool bFlushNow)
    {
        if (!Subsystem || !bFlushNow)
        {
            return {};
        }

        return Subsystem->FlushDirtyCellsToDisk();
    }
}

FSnowCellSnapshot USnowStateBlueprintLibrary::MarkPersistentWheelWriter(
    UActorComponent* SourceComponent,
    const ESnowReceiverSurfaceFamily SurfaceFamily,
    const bool bFlushNow
)
{
    if (!SourceComponent)
    {
        return FSnowCellSnapshot();
    }

    USnowStateWorldSubsystem* Subsystem = ResolveSnowSubsystem(SourceComponent);
    if (!Subsystem || !Subsystem->IsPersistentSnowStateEnabled())
    {
        return FSnowCellSnapshot();
    }

    const FVector WorldLocation = ResolveWriterWorldLocation(SourceComponent);
    FSnowCellSnapshot Snapshot = Subsystem->MarkWorldLocationDirty(WorldLocation, SurfaceFamily);
    const TArray<FSnowCellSnapshot> FlushedSnapshots = FlushIfRequested(Subsystem, bFlushNow);
    for (const FSnowCellSnapshot& Flushed : FlushedSnapshots)
    {
        if (Flushed.CellId == Snapshot.CellId)
        {
            Snapshot = Flushed;
            break;
        }
    }
    return Snapshot;
}

TArray<FSnowCellSnapshot> USnowStateBlueprintLibrary::MarkPersistentPlowWriter(
    UActorComponent* SourceComponent,
    const float LengthCm,
    const float WidthCm,
    const ESnowReceiverSurfaceFamily SurfaceFamily,
    const bool bFlushNow
)
{
    TArray<FSnowCellSnapshot> EmptyResult;
    if (!SourceComponent)
    {
        return EmptyResult;
    }

    USnowStateWorldSubsystem* Subsystem = ResolveSnowSubsystem(SourceComponent);
    if (!Subsystem || !Subsystem->IsPersistentSnowStateEnabled())
    {
        return EmptyResult;
    }

    const FVector WorldLocation = ResolveWriterWorldLocation(SourceComponent);
    const FRotator WorldRotation = ResolveWriterWorldRotation(SourceComponent);
    FVector Forward = WorldRotation.Vector();
    Forward.Z = 0.0f;
    Forward.Normalize();
    if (Forward.IsNearlyZero())
    {
        Forward = FVector::ForwardVector;
    }

    FVector Right = FVector::CrossProduct(FVector::UpVector, Forward);
    Right.Z = 0.0f;
    Right.Normalize();
    if (Right.IsNearlyZero())
    {
        Right = FVector::RightVector;
    }

    const float HalfLengthCm = FMath::Max(LengthCm * 0.5f, 1.0f);
    const float HalfWidthCm = FMath::Max(WidthCm * 0.5f, 1.0f);
    const TArray<FVector> Corners = {
        WorldLocation + (Forward * HalfLengthCm) + (Right * HalfWidthCm),
        WorldLocation + (Forward * HalfLengthCm) - (Right * HalfWidthCm),
        WorldLocation - (Forward * HalfLengthCm) + (Right * HalfWidthCm),
        WorldLocation - (Forward * HalfLengthCm) - (Right * HalfWidthCm),
    };

    FVector2D BoxMin(FLT_MAX, FLT_MAX);
    FVector2D BoxMax(-FLT_MAX, -FLT_MAX);
    for (const FVector& Corner : Corners)
    {
        BoxMin.X = FMath::Min(BoxMin.X, Corner.X);
        BoxMin.Y = FMath::Min(BoxMin.Y, Corner.Y);
        BoxMax.X = FMath::Max(BoxMax.X, Corner.X);
        BoxMax.Y = FMath::Max(BoxMax.Y, Corner.Y);
    }

    TArray<FSnowCellSnapshot> Snapshots = Subsystem->MarkWorldBoxDirty(BoxMin, BoxMax, SurfaceFamily);
    if (bFlushNow)
    {
        const TArray<FSnowCellSnapshot> FlushedSnapshots = Subsystem->FlushDirtyCellsToDisk();
        if (FlushedSnapshots.Num() > 0)
        {
            Snapshots = FlushedSnapshots;
        }
    }
    return Snapshots;
}

TArray<FSnowCellSnapshot> USnowStateBlueprintLibrary::FlushPersistentSnowState(UObject* WorldContextObject)
{
    if (USnowStateWorldSubsystem* Subsystem = ResolveSnowSubsystem(WorldContextObject))
    {
        return Subsystem->FlushDirtyCellsToDisk();
    }

    return {};
}
