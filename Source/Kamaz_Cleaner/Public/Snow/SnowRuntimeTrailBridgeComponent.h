#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Snow/PersistentSnowStateTypes.h"

#include "SnowRuntimeTrailBridgeComponent.generated.h"

class USceneComponent;
class UInstancedStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UMeshComponent;
class URuntimeVirtualTexture;
class UStaticMesh;
class AActor;
class ALandscapeProxy;

UCLASS(ClassGroup = (Snow), meta = (BlueprintSpawnableComponent))
class KAMAZ_CLEANER_API USnowRuntimeTrailBridgeComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    USnowRuntimeTrailBridgeComponent();

    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

    UFUNCTION(BlueprintCallable, Category = "Snow|Runtime Trail")
    bool RecordTrailStampNow();

    UFUNCTION(BlueprintPure, Category = "Snow|Runtime Trail")
    int32 GetStampCount() const;

    UFUNCTION(BlueprintPure, Category = "Snow|Runtime Trail")
    int32 GetVisualStampCount() const;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Runtime Trail")
    bool bEnableRuntimeTrail = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Runtime Trail")
    float StampSpacingCm = 5.0f;

    // If enabled, stamping/cleaning works only while plow source is below this relative Z.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Runtime Trail")
    bool bUseSourceHeightGate = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Runtime Trail")
    float SourceActiveMaxRelativeZ = -0.5f;

    // Minimum plow engagement needed before a new stamp is written.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Runtime Trail", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float MinStampEngagementToWrite = 0.18f;

    // If the plow component exposes PlowLiftHeight, 0 means lowered / fully engaged
    // clearing and this value means raised / no snow effect.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Runtime Trail", meta = (ClampMin = "0.01"))
    float PlowLiftHeightForNoEffect = 1.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Persistent")
    bool bMarkPersistentSnowState = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Persistent", meta = (ClampMin = "1.0"))
    float PersistentPlowLengthCm = 120.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Persistent", meta = (ClampMin = "1.0"))
    float PersistentPlowWidthCm = 340.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Persistent", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float RightBermContinuationRatio = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Persistent")
    ESnowReceiverSurfaceFamily PersistentSurfaceFamily = ESnowReceiverSurfaceFamily::Road;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Persistent")
    UActorComponent* SourceComponentOverride = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|RVT Writer")
    bool bEnableRvtVisualStamp = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|RVT Writer", meta = (ClampMin = "1"))
    int32 MaxVisualStamps = 2048;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Repeat Accumulation")
    bool bEnableRepeatClearingAccumulation = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Repeat Accumulation", meta = (ClampMin = "10.0"))
    float RepeatAccumulationCellSizeCm = 80.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Repeat Accumulation", meta = (ClampMin = "1", ClampMax = "3"))
    int32 RepeatAccumulationMaxPasses = 3;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Repeat Accumulation", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float FirstPassClearStrength = 1.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Repeat Accumulation", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float RepeatPassClearStrengthStep = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Repeat Accumulation", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float MaxAccumulatedClearStrength = 1.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Repeat Accumulation", meta = (ClampMin = "0.0"))
    float RepeatTierZOffsetCm = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Repeat Accumulation", meta = (ClampMin = "0.0"))
    float RepeatAccumulationRearmSeconds = 1.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|RVT Writer")
    TObjectPtr<UStaticMesh> StampMeshAsset = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|RVT Writer")
    TObjectPtr<UMaterialInterface> StampMaterial = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|RVT Writer")
    TObjectPtr<URuntimeVirtualTexture> TargetRvt = nullptr;

    // Runtime receiver control: plow down -> active depth, plow up -> zero depth.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Runtime Height")
    bool bEnableRuntimeReceiverHeightControl = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Runtime Height")
    FName RuntimeHeightAmplitudeParameterName = FName(TEXT("HeightAmplitude"));

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Runtime Height")
    float RuntimeHeightAmplitudeWhenActive = -35.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow|Runtime Height")
    float RuntimeHeightAmplitudeWhenInactive = 0.0f;

private:
    ESnowReceiverSurfaceFamily ResolveActiveSurfaceFamily(const USceneComponent* Source) const;
    float ResolveSourceEngagementStrength(const USceneComponent* Source) const;
    int32 ResolveEngagementBandIndex(float SourceEngagementStrength) const;
    float ResolveEngagementBandStrength(int32 EngagementBandIndex) const;
    int32 ResolveTierBandFlatIndex(int32 TierIndex, int32 EngagementBandIndex) const;
    USceneComponent* ResolveSourceComponent();
    void MaybeStamp(float DeltaTime);
    void EnsureRvtStampComponent();
    float ResolveClearStrengthForTier(int32 TierIndex) const;
    float ResolveRepeatDepthStrengthForTier(int32 TierIndex) const;
    int32 ResolveRepeatTierForLocation(const FVector& WorldLocation);
    int32 GetTotalVisualStampCount() const;
    void AddRvtStampInstance(const FVector& WorldLocation, const FRotator& WorldRotation, const AActor* SourceOwner, float SourceEngagementStrength);
    void CacheRuntimeReceiverMaterialInstances();
    void ApplyRuntimeReceiverHeightAmplitude(float SourceEngagementStrength);

    int32 StampCount = 0;
    FVector LastStampLocation = FVector::ZeroVector;
    bool bHasLastLocation = false;
    TObjectPtr<UInstancedStaticMeshComponent> RvtStampInstances = nullptr;
    TArray<TObjectPtr<UInstancedStaticMeshComponent>> RvtStampTierInstances;
    TArray<TObjectPtr<UMaterialInstanceDynamic>> RvtStampTierMaterials;
    TArray<TObjectPtr<UInstancedStaticMeshComponent>> RvtBermTierInstances;
    TArray<TObjectPtr<UMaterialInstanceDynamic>> RvtBermTierMaterials;
    TMap<FIntPoint, int32> RepeatAccumulationCells;
    TMap<FIntPoint, double> RepeatAccumulationCellLastTouchTimes;
    TArray<TObjectPtr<UMaterialInstanceDynamic>> RuntimeReceiverDynamicMaterials;
    TArray<TWeakObjectPtr<ALandscapeProxy>> RuntimeLandscapeReceivers;
    bool bReceiverMaterialCacheInitialized = false;
    bool bLastAppliedRuntimeHeightValid = false;
    float LastAppliedRuntimeHeightAmplitude = 0.0f;
};
