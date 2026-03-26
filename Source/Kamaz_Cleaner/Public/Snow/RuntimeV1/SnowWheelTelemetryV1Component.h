#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Snow/PersistentSnowStateTypes.h"
#include "SnowWheelTelemetryV1Component.generated.h"

class ASnowStateManagerV1;
class UChaosWheeledVehicleMovementComponent;
class UPhysicalMaterial;

USTRUCT(BlueprintType)
struct KAMAZ_CLEANER_API FSnowWheelTelemetrySampleV1
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    int32 WheelIndex = INDEX_NONE;

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    bool bValid = false;

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    bool bInContact = false;

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    FVector ContactPoint = FVector::ZeroVector;

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    float SpringForce = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    float SlipMagnitude = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    float SkidMagnitude = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    float SpeedCmPerSec = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    float WheelRadiusCm = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    float WheelWidthCm = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    ESnowReceiverSurfaceFamily SurfaceFamily = ESnowReceiverSurfaceFamily::Unknown;

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    FString PhysMaterialPath;

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    float RemainingSnowDepthDelta = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    float CompactionRutDepthDelta = 0.0f;

    UPROPERTY(BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    float ClearedExposeRoadDelta = 0.0f;
};

UCLASS(ClassGroup = (Snow), BlueprintType, Blueprintable, meta = (BlueprintSpawnableComponent))
class KAMAZ_CLEANER_API USnowWheelTelemetryV1Component : public UActorComponent
{
    GENERATED_BODY()

public:
    USnowWheelTelemetryV1Component();

    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

    UFUNCTION(BlueprintCallable, Category = "Snow Runtime V1|Wheel Telemetry")
    int32 CaptureWheelTelemetryAndQueueStamps(bool bFlushAfterQueue = true);

    UFUNCTION(BlueprintPure, Category = "Snow Runtime V1|Wheel Telemetry")
    ASnowStateManagerV1* GetResolvedStateManager() const;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry")
    TObjectPtr<ASnowStateManagerV1> StateManagerActor = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry")
    bool bAutoResolveStateManager = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry")
    bool bCenterStateMappingOnOwner = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry")
    bool bCaptureEveryTick = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry", meta = (ClampMin = "0.0"))
    float CaptureIntervalSeconds = 0.05f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry", meta = (ClampMin = "0.0"))
    float MinSpringForceForStamp = 250.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry", meta = (ClampMin = "1.0"))
    float LoadForFullSignal = 120000.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry", meta = (ClampMin = "0.01"))
    float SlipForFullSignal = 20.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry", meta = (ClampMin = "1.0"))
    float SpeedForFullSignal = 1800.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry", meta = (ClampMin = "1.0"))
    float MinimumStampRadiusCm = 28.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry", meta = (ClampMin = "0.01"))
    float StampFalloffPower = 1.8f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float RemainingSnowDepthScale = 0.28f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float CompactionRutDepthScale = 0.42f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float ClearedExposeRoadScale = 0.18f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Wheel Telemetry")
    TArray<ESnowReceiverSurfaceFamily> SnowEnabledSurfaceFamilies;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    int32 LastResolvedWheelCount = 0;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    int32 LastInContactWheelCount = 0;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    int32 LastQueuedStampCount = 0;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    bool bLastFlushSucceeded = false;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    FString LastResolvedManagerPath;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Snow Runtime V1|Wheel Telemetry")
    TArray<FSnowWheelTelemetrySampleV1> LastWheelSamples;

private:
    ASnowStateManagerV1* ResolveStateManager();
    UChaosWheeledVehicleMovementComponent* ResolveVehicleMovement() const;
    bool TryBuildWheelSample(const UChaosWheeledVehicleMovementComponent* VehicleMovement, int32 WheelIndex, FSnowWheelTelemetrySampleV1& OutSample) const;
    ESnowReceiverSurfaceFamily ResolveSurfaceFamilyAtLocation(const FVector& WorldLocation, UPhysicalMaterial*& OutPhysMaterial) const;
    bool IsSnowEnabledSurfaceFamily(ESnowReceiverSurfaceFamily SurfaceFamily) const;
    float NormalizeSignal(float Value, float FullSignalValue) const;
    float ComputeStampRadiusCm(float WheelRadiusCm, float WheelWidthCm) const;

    float CaptureTimeAccumulator = 0.0f;
};
