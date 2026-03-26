#include "Snow/RuntimeV1/SnowWheelTelemetryV1Component.h"

#include "ChaosVehicleWheel.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Actor.h"
#include "LandscapeProxy.h"
#include "Snow/RuntimeV1/SnowStateManagerV1.h"
#include "Snow/SnowReceiverSurfaceComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "WheeledVehiclePawn.h"

namespace
{
    constexpr float SurfaceTraceUpCm = 80.0f;
    constexpr float SurfaceTraceDownCm = 220.0f;
    constexpr float MinimumContactWeight = 0.08f;
}

USnowWheelTelemetryV1Component::USnowWheelTelemetryV1Component()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.bStartWithTickEnabled = true;
    PrimaryComponentTick.TickGroup = TG_PostPhysics;

    SnowEnabledSurfaceFamilies = {
        ESnowReceiverSurfaceFamily::Road,
        ESnowReceiverSurfaceFamily::Shoulder,
        ESnowReceiverSurfaceFamily::Landscape,
        ESnowReceiverSurfaceFamily::Sidewalk,
    };
}

void USnowWheelTelemetryV1Component::BeginPlay()
{
    Super::BeginPlay();
    CaptureTimeAccumulator = CaptureIntervalSeconds;
}

void USnowWheelTelemetryV1Component::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

    UWorld* World = GetWorld();
    if (!World || !World->IsGameWorld() || !bCaptureEveryTick)
    {
        return;
    }

    CaptureTimeAccumulator += FMath::Max(0.0f, DeltaTime);
    if (CaptureTimeAccumulator < CaptureIntervalSeconds)
    {
        return;
    }

    CaptureTimeAccumulator = 0.0f;
    CaptureWheelTelemetryAndQueueStamps(true);
}

int32 USnowWheelTelemetryV1Component::CaptureWheelTelemetryAndQueueStamps(const bool bFlushAfterQueue)
{
    LastWheelSamples.Reset();
    LastResolvedWheelCount = 0;
    LastInContactWheelCount = 0;
    LastQueuedStampCount = 0;
    bLastFlushSucceeded = false;

    UChaosWheeledVehicleMovementComponent* VehicleMovement = ResolveVehicleMovement();
    ASnowStateManagerV1* StateManager = ResolveStateManager();
    if (!VehicleMovement || !StateManager)
    {
        return 0;
    }

    if (bCenterStateMappingOnOwner)
    {
        if (const AActor* Owner = GetOwner())
        {
            StateManager->CenterMappingOnWorldLocation(Owner->GetActorLocation());
        }
    }

    int32 WheelCount = VehicleMovement->GetNumWheels();
    if (WheelCount <= 0)
    {
        if (USkeletalMeshComponent* SkeletalMesh = GetOwner() ? GetOwner()->FindComponentByClass<USkeletalMeshComponent>() : nullptr)
        {
            SkeletalMesh->RecreatePhysicsState();
        }

        VehicleMovement->RecreatePhysicsState();
        VehicleMovement->ResetVehicleState();
        WheelCount = VehicleMovement->GetNumWheels();
    }

    LastResolvedWheelCount = WheelCount;

    int32 QueuedCount = 0;
    for (int32 WheelIndex = 0; WheelIndex < WheelCount; ++WheelIndex)
    {
        FSnowWheelTelemetrySampleV1 Sample;
        if (!TryBuildWheelSample(VehicleMovement, WheelIndex, Sample))
        {
            continue;
        }

        ++LastInContactWheelCount;
        LastWheelSamples.Add(Sample);

        FSnowStateStampRequestV1 StampRequest;
        StampRequest.WorldLocation = Sample.ContactPoint;
        StampRequest.RadiusCm = ComputeStampRadiusCm(Sample.WheelRadiusCm, Sample.WheelWidthCm);
        StampRequest.RemainingSnowDepthDelta = Sample.RemainingSnowDepthDelta;
        StampRequest.CompactionRutDepthDelta = Sample.CompactionRutDepthDelta;
        StampRequest.ClearedExposeRoadDelta = Sample.ClearedExposeRoadDelta;
        StampRequest.BermSidePileDelta = 0.0f;
        StampRequest.FalloffPower = FMath::Max(0.01f, StampFalloffPower);

        StateManager->QueueWheelStamp(StampRequest);
        ++QueuedCount;
    }

    LastQueuedStampCount = QueuedCount;

    if (QueuedCount > 0 && bFlushAfterQueue)
    {
        bLastFlushSucceeded = StateManager->FlushQueuedStateWrites();
    }

    return QueuedCount;
}

ASnowStateManagerV1* USnowWheelTelemetryV1Component::GetResolvedStateManager() const
{
    return StateManagerActor.Get();
}

ASnowStateManagerV1* USnowWheelTelemetryV1Component::ResolveStateManager()
{
    if (StateManagerActor && IsValid(StateManagerActor))
    {
        LastResolvedManagerPath = StateManagerActor->GetPathName();
        return StateManagerActor.Get();
    }

    if (!bAutoResolveStateManager)
    {
        LastResolvedManagerPath.Reset();
        return nullptr;
    }

    UWorld* World = GetWorld();
    if (!World)
    {
        LastResolvedManagerPath.Reset();
        return nullptr;
    }

    for (TActorIterator<ASnowStateManagerV1> It(World); It; ++It)
    {
        ASnowStateManagerV1* Candidate = *It;
        if (!Candidate || !IsValid(Candidate))
        {
            continue;
        }

        StateManagerActor = Candidate;
        LastResolvedManagerPath = Candidate->GetPathName();
        return Candidate;
    }

    LastResolvedManagerPath.Reset();
    return nullptr;
}

UChaosWheeledVehicleMovementComponent* USnowWheelTelemetryV1Component::ResolveVehicleMovement() const
{
    const AActor* Owner = GetOwner();
    if (!Owner)
    {
        return nullptr;
    }

    if (const AWheeledVehiclePawn* VehiclePawn = Cast<AWheeledVehiclePawn>(Owner))
    {
        return Cast<UChaosWheeledVehicleMovementComponent>(VehiclePawn->GetVehicleMovementComponent());
    }

    return Cast<UChaosWheeledVehicleMovementComponent>(Owner->GetComponentByClass(UChaosWheeledVehicleMovementComponent::StaticClass()));
}

bool USnowWheelTelemetryV1Component::TryBuildWheelSample(
    const UChaosWheeledVehicleMovementComponent* VehicleMovement,
    const int32 WheelIndex,
    FSnowWheelTelemetrySampleV1& OutSample
) const
{
    if (!VehicleMovement)
    {
        return false;
    }

    const FWheelStatus WheelStatus = VehicleMovement->GetWheelState(WheelIndex);
    if (!WheelStatus.bIsValid || !WheelStatus.bInContact)
    {
        return false;
    }

    const AActor* Owner = GetOwner();
    if (!Owner)
    {
        return false;
    }

    const FVector ContactPoint = !WheelStatus.ContactPoint.IsNearlyZero()
        ? WheelStatus.ContactPoint
        : WheelStatus.HitLocation;
    if (ContactPoint.IsNearlyZero())
    {
        return false;
    }

    UPhysicalMaterial* ResolvedPhysMaterial = WheelStatus.PhysMaterial.Get();
    const ESnowReceiverSurfaceFamily SurfaceFamily = ResolveSurfaceFamilyAtLocation(ContactPoint, ResolvedPhysMaterial);
    if (!IsSnowEnabledSurfaceFamily(SurfaceFamily))
    {
        return false;
    }

    const float SpringForce = FMath::Max(0.0f, WheelStatus.SpringForce);
    if (SpringForce < MinSpringForceForStamp)
    {
        return false;
    }

    float WheelRadiusCm = 0.0f;
    float WheelWidthCm = 0.0f;
    if (VehicleMovement->Wheels.IsValidIndex(WheelIndex) && VehicleMovement->Wheels[WheelIndex])
    {
        const UChaosVehicleWheel* Wheel = VehicleMovement->Wheels[WheelIndex];
        WheelRadiusCm = FMath::Max(0.0f, Wheel->GetWheelRadius());
        WheelWidthCm = FMath::Max(0.0f, Wheel->WheelWidth);
    }

    const float SpeedCmPerSec = Owner->GetVelocity().Size2D();
    const float LoadSignal = NormalizeSignal(SpringForce, LoadForFullSignal);
    const float SlipSignal = NormalizeSignal(FMath::Max(FMath::Abs(WheelStatus.SlipMagnitude), FMath::Abs(WheelStatus.SkidMagnitude)), SlipForFullSignal);
    const float SpeedSignal = NormalizeSignal(SpeedCmPerSec, SpeedForFullSignal);
    const float ContactWeight = FMath::Max(MinimumContactWeight, (LoadSignal * 0.65f) + (SpeedSignal * 0.20f) + (SlipSignal * 0.15f));

    OutSample.WheelIndex = WheelIndex;
    OutSample.bValid = true;
    OutSample.bInContact = true;
    OutSample.ContactPoint = ContactPoint;
    OutSample.SpringForce = SpringForce;
    OutSample.SlipMagnitude = FMath::Abs(WheelStatus.SlipMagnitude);
    OutSample.SkidMagnitude = FMath::Abs(WheelStatus.SkidMagnitude);
    OutSample.SpeedCmPerSec = SpeedCmPerSec;
    OutSample.WheelRadiusCm = WheelRadiusCm;
    OutSample.WheelWidthCm = WheelWidthCm;
    OutSample.SurfaceFamily = SurfaceFamily;
    OutSample.PhysMaterialPath = ResolvedPhysMaterial ? ResolvedPhysMaterial->GetPathName() : FString();
    OutSample.RemainingSnowDepthDelta = FMath::Clamp(ContactWeight * RemainingSnowDepthScale, 0.0f, 1.0f);
    OutSample.CompactionRutDepthDelta = FMath::Clamp(((LoadSignal * 0.60f) + (SlipSignal * 0.40f)) * CompactionRutDepthScale, 0.0f, 1.0f);
    OutSample.ClearedExposeRoadDelta = FMath::Clamp(((LoadSignal * 0.25f) + (SpeedSignal * 0.35f) + (SlipSignal * 0.40f)) * ClearedExposeRoadScale, 0.0f, 1.0f);
    return true;
}

ESnowReceiverSurfaceFamily USnowWheelTelemetryV1Component::ResolveSurfaceFamilyAtLocation(const FVector& WorldLocation, UPhysicalMaterial*& OutPhysMaterial) const
{
    UWorld* World = GetWorld();
    if (!World)
    {
        return ESnowReceiverSurfaceFamily::Unknown;
    }

    const FVector TraceStart = WorldLocation + FVector(0.0f, 0.0f, SurfaceTraceUpCm);
    const FVector TraceEnd = WorldLocation - FVector(0.0f, 0.0f, SurfaceTraceDownCm);

    FHitResult Hit;
    FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(SnowWheelTelemetrySurfaceFamily), false, GetOwner());
    if (const AActor* Owner = GetOwner())
    {
        QueryParams.AddIgnoredActor(Owner);
    }

    bool bHit = World->LineTraceSingleByChannel(Hit, TraceStart, TraceEnd, ECC_Visibility, QueryParams);
    if (!bHit)
    {
        bHit = World->LineTraceSingleByChannel(Hit, TraceStart, TraceEnd, ECC_WorldStatic, QueryParams);
    }

    if (!bHit)
    {
        return ESnowReceiverSurfaceFamily::Unknown;
    }

    if (UPhysicalMaterial* HitPhysMaterial = Hit.PhysMaterial.Get())
    {
        OutPhysMaterial = HitPhysMaterial;
    }

    if (AActor* HitActor = Hit.GetActor())
    {
        if (Cast<ALandscapeProxy>(HitActor))
        {
            return ESnowReceiverSurfaceFamily::Landscape;
        }

        if (const USnowReceiverSurfaceComponent* Receiver = HitActor->FindComponentByClass<USnowReceiverSurfaceComponent>())
        {
            return Receiver->SurfaceFamily;
        }
    }

    if (const UPrimitiveComponent* HitComponent = Hit.GetComponent())
    {
        if (const AActor* HitOwner = HitComponent->GetOwner())
        {
            if (Cast<ALandscapeProxy>(HitOwner))
            {
                return ESnowReceiverSurfaceFamily::Landscape;
            }

            if (const USnowReceiverSurfaceComponent* Receiver = HitOwner->FindComponentByClass<USnowReceiverSurfaceComponent>())
            {
                return Receiver->SurfaceFamily;
            }
        }
    }

    return OutPhysMaterial ? ESnowReceiverSurfaceFamily::Road : ESnowReceiverSurfaceFamily::Unknown;
}

bool USnowWheelTelemetryV1Component::IsSnowEnabledSurfaceFamily(const ESnowReceiverSurfaceFamily SurfaceFamily) const
{
    return SnowEnabledSurfaceFamilies.Contains(SurfaceFamily);
}

float USnowWheelTelemetryV1Component::NormalizeSignal(const float Value, const float FullSignalValue) const
{
    return FMath::Clamp(Value / FMath::Max(FullSignalValue, 0.01f), 0.0f, 1.0f);
}

float USnowWheelTelemetryV1Component::ComputeStampRadiusCm(const float WheelRadiusCm, const float WheelWidthCm) const
{
    const float RadiusFromWidth = WheelWidthCm * 0.55f;
    const float RadiusFromWheel = WheelRadiusCm * 0.40f;
    return FMath::Max(MinimumStampRadiusCm, FMath::Max(RadiusFromWidth, RadiusFromWheel));
}
