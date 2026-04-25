#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

#include "SnowMapKamazPlowCaptureDeformerActor.generated.h"

class APawn;
class USceneComponent;
class USkeletalMeshComponent;
class UStaticMeshComponent;

UCLASS()
class KAMAZ_CLEANER_API ASnowMapKamazPlowCaptureDeformerActor : public AActor
{
    GENERATED_BODY()

public:
    ASnowMapKamazPlowCaptureDeformerActor();

    virtual void BeginPlay() override;
    virtual void Tick(float DeltaTime) override;

protected:
    UPROPERTY(VisibleAnywhere, Category = "Snow")
    TObjectPtr<USceneComponent> Root;

    UPROPERTY(VisibleAnywhere, Category = "Snow")
    TObjectPtr<UStaticMeshComponent> PlowDeformerMesh;

    UPROPERTY(VisibleAnywhere, Category = "Snow|Wheel")
    TObjectPtr<UStaticMeshComponent> FrontLeftWheelDeformerMesh;

    UPROPERTY(VisibleAnywhere, Category = "Snow|Wheel")
    TObjectPtr<UStaticMeshComponent> FrontRightWheelDeformerMesh;

    UPROPERTY(VisibleAnywhere, Category = "Snow|Wheel")
    TObjectPtr<UStaticMeshComponent> RearLeftWheelDeformerMesh;

    UPROPERTY(VisibleAnywhere, Category = "Snow|Wheel")
    TObjectPtr<UStaticMeshComponent> RearRightWheelDeformerMesh;

    UPROPERTY(EditAnywhere, Category = "Snow")
    FName PreferredPlowComponentToken = FName(TEXT("PlowBrush"));

    UPROPERTY(EditAnywhere, Category = "Snow")
    FName SecondaryPlowComponentToken = FName(TEXT("SM_FrontHitch"));

    UPROPERTY(EditAnywhere, Category = "Snow")
    FName FallbackHitchComponentToken = FName(TEXT("BP_PlowBrush_Component"));

    UPROPERTY(EditAnywhere, Category = "Snow")
    FVector DeformerRelativeLocation = FVector(0.0f, 0.0f, -30.0f);

    UPROPERTY(EditAnywhere, Category = "Snow")
    FRotator DeformerRelativeRotation = FRotator::ZeroRotator;

    // Matches the documented 50x350x100 cm plow footprint on a 100 cm engine cube.
    UPROPERTY(EditAnywhere, Category = "Snow")
    FVector DeformerRelativeScale = FVector(0.5f, 3.2f, 0.45f);

    UPROPERTY(EditAnywhere, Category = "Snow")
    bool bUsePlowLiftVisibilityGate = true;

    UPROPERTY(EditAnywhere, Category = "Snow", meta = (ClampMin = "0.0"))
    float ActiveWhenPlowLiftHeightAtOrBelow = 0.5f;

    UPROPERTY(EditAnywhere, Category = "Snow")
    FName PlowLiftHeightPropertyName = FName(TEXT("PlowLiftHeight"));

    UPROPERTY(EditAnywhere, Category = "Snow|Wheel")
    bool bEnableWheelDeformers = true;

    UPROPERTY(EditAnywhere, Category = "Snow|Wheel")
    TArray<FName> WheelBoneNames = {
        FName(TEXT("WFL")),
        FName(TEXT("WFR")),
        FName(TEXT("WRL")),
        FName(TEXT("WRR"))
    };

    UPROPERTY(EditAnywhere, Category = "Snow|Wheel")
    FVector FrontWheelDeformerScale = FVector(0.60f, 0.28f, 0.18f);

    UPROPERTY(EditAnywhere, Category = "Snow|Wheel")
    FVector RearWheelDeformerScale = FVector(0.60f, 0.36f, 0.20f);

    UPROPERTY(EditAnywhere, Category = "Snow|Wheel", meta = (ClampMin = "0.0"))
    float WheelTraceUpCm = 60.0f;

    UPROPERTY(EditAnywhere, Category = "Snow|Wheel", meta = (ClampMin = "0.0"))
    float WheelTraceDownCm = 220.0f;

    UPROPERTY(EditAnywhere, Category = "Snow|Wheel", meta = (ClampMin = "0.0"))
    float WheelStampLiftAboveHitCm = 38.0f;

private:
    APawn* ResolvePlayerPawn() const;
    USceneComponent* ResolveBestSourceComponent(APawn* Pawn) const;
    USkeletalMeshComponent* ResolveVehicleMeshComponent(APawn* Pawn) const;
    float ResolvePlowLiftHeight(const USceneComponent* Source) const;
    void RefreshAttachment();
    void RefreshVisibility();
    void RefreshWheelTrackDeformers();
    void HideWheelTrackDeformers();

    TWeakObjectPtr<APawn> CachedPawn;
    TWeakObjectPtr<USceneComponent> CachedSourceComponent;
    TWeakObjectPtr<USkeletalMeshComponent> CachedVehicleMeshComponent;
};
