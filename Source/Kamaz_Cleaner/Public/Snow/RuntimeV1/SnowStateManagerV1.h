#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

#include "SnowStateManagerV1.generated.h"

class UMaterialInstanceDynamic;
class UMaterialInterface;
class UTextureRenderTarget2D;

USTRUCT(BlueprintType)
struct KAMAZ_CLEANER_API FSnowStateStampRequestV1
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1")
    FVector WorldLocation = FVector::ZeroVector;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1", meta = (ClampMin = "1.0"))
    float RadiusCm = 120.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1")
    float RemainingSnowDepthDelta = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1")
    float CompactionRutDepthDelta = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1")
    float ClearedExposeRoadDelta = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1")
    float BermSidePileDelta = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1", meta = (ClampMin = "0.01"))
    float FalloffPower = 2.0f;
};

UCLASS(BlueprintType, Blueprintable)
class KAMAZ_CLEANER_API ASnowStateManagerV1 : public AActor
{
    GENERATED_BODY()

public:
    ASnowStateManagerV1();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|State")
    TObjectPtr<UTextureRenderTarget2D> StateRenderTargetA = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|State")
    TObjectPtr<UTextureRenderTarget2D> StateRenderTargetB = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|State")
    TObjectPtr<UMaterialInterface> WheelWriteMaterial = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|State")
    TObjectPtr<UMaterialInterface> PlowWriteMaterial = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Mapping")
    FVector WorldMappingOrigin = FVector::ZeroVector;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Mapping", meta = (ClampMin = "1.0"))
    FVector2D WorldMappingExtentCm = FVector2D(25000.0f, 25000.0f);

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1|Mapping", meta = (ClampMin = "1.0"))
    float ActiveAreaHalfExtentCm = 5000.0f;

    UFUNCTION(BlueprintCallable, Category = "Snow Runtime V1|Mapping")
    void CenterMappingOnWorldLocation(const FVector& WorldLocation);

    UFUNCTION(BlueprintCallable, Category = "Snow Runtime V1|State")
    void ResetStateRenderTargets(const FLinearColor& ClearColor = FLinearColor::Black);

    UFUNCTION(BlueprintCallable, Category = "Snow Runtime V1|State")
    void QueueWheelStamp(const FSnowStateStampRequestV1& StampRequest);

    UFUNCTION(BlueprintCallable, Category = "Snow Runtime V1|State")
    void QueuePlowStamp(const FSnowStateStampRequestV1& StampRequest);

    UFUNCTION(BlueprintCallable, Category = "Snow Runtime V1|State")
    bool FlushQueuedStateWrites();

    UFUNCTION(BlueprintPure, Category = "Snow Runtime V1|State")
    UTextureRenderTarget2D* GetAuthoritativeStateRenderTarget() const;

    UFUNCTION(BlueprintPure, Category = "Snow Runtime V1|State")
    UTextureRenderTarget2D* GetCurrentReadRenderTarget() const;

    UFUNCTION(BlueprintPure, Category = "Snow Runtime V1|State")
    UTextureRenderTarget2D* GetCurrentWriteRenderTarget() const;

    UFUNCTION(BlueprintPure, Category = "Snow Runtime V1|State")
    int32 GetPendingWheelStampCount() const;

    UFUNCTION(BlueprintPure, Category = "Snow Runtime V1|State")
    int32 GetPendingPlowStampCount() const;

protected:
    virtual void BeginPlay() override;

private:
    bool ApplyQueuedStamps(const TArray<FSnowStateStampRequestV1>& StampRequests, UMaterialInterface* BaseMaterial);
    bool ApplySingleStamp(const FSnowStateStampRequestV1& StampRequest, UMaterialInterface* BaseMaterial);
    UTextureRenderTarget2D* GetReadRenderTarget() const;
    UTextureRenderTarget2D* GetWriteRenderTarget() const;
    void SwapActiveRenderTarget();
    FVector2D ConvertWorldLocationToUv(const FVector& WorldLocation) const;
    float ConvertRadiusToUv(const float RadiusCm) const;
    FLinearColor BuildChannelDelta(const FSnowStateStampRequestV1& StampRequest) const;
    UMaterialInstanceDynamic* GetOrCreateWriteMaterialInstance(UMaterialInterface* BaseMaterial);

    UPROPERTY(Transient)
    bool bStateAIsAuthoritative = true;

    UPROPERTY(Transient)
    TMap<TObjectPtr<UMaterialInterface>, TObjectPtr<UMaterialInstanceDynamic>> CachedWriteMIDs;

    UPROPERTY(Transient)
    TArray<FSnowStateStampRequestV1> PendingWheelStamps;

    UPROPERTY(Transient)
    TArray<FSnowStateStampRequestV1> PendingPlowStamps;
};
