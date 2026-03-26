#pragma once

#include "Components/SplineMeshComponent.h"
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Snow/PersistentSnowStateTypes.h"

#include "SnowSplineRoadActor.generated.h"

class UMaterialInterface;
class UMaterialInstanceDynamic;
class USceneComponent;
class USnowReceiverSurfaceComponent;
class USplineComponent;
class USplineMeshComponent;
class UStaticMesh;

UCLASS(Blueprintable)
class KAMAZ_CLEANER_API ASnowSplineRoadActor : public AActor
{
    GENERATED_BODY()

public:
    ASnowSplineRoadActor();

    virtual void OnConstruction(const FTransform& Transform) override;

    UFUNCTION(CallInEditor, Category = "Snow|Spline Road")
    void RebuildSplineMeshes();

protected:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Snow|Spline")
    TObjectPtr<USceneComponent> Root = nullptr;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Snow|Spline")
    TObjectPtr<USplineComponent> Spline = nullptr;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Snow|Receiver")
    TObjectPtr<USnowReceiverSurfaceComponent> SnowReceiver = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow|Spline")
    TObjectPtr<UStaticMesh> SegmentMesh = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow|Material")
    TObjectPtr<UMaterialInterface> SnowRoadMaterial = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow|Spline", meta = (ClampMin = "100.0"))
    float SegmentLengthCm = 1000.0f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow|Spline", meta = (ClampMin = "100.0"))
    float RoadWidthCm = 1500.0f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow|Material", meta = (ClampMin = "1.0"))
    float MeshReferenceLengthCm = 1000.0f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow|Material", meta = (ClampMin = "1.0"))
    float MeshReferenceWidthCm = 100.0f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow|Material", meta = (ClampMin = "0.001"))
    float LengthTiling = 1.0f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow|Material", meta = (ClampMin = "0.001"))
    float WidthTiling = 1.0f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow|Spline", meta = (ClampMin = "0.1"))
    float ThicknessScale = 1.0f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow|Spline")
    bool bForceSingleSplineMeshSegment = false;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow|Spline")
    TEnumAsByte<ESplineMeshAxis::Type> ForwardAxis = ESplineMeshAxis::X;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow|Material")
    FName LengthTilingParameterName = TEXT("LengthTiling");

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow|Material")
    FName WidthTilingParameterName = TEXT("WidthTiling");

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow|Receiver")
    ESnowReceiverSurfaceFamily SurfaceFamily = ESnowReceiverSurfaceFamily::Road;

private:
    void CacheExistingSegments();
    USplineMeshComponent* GetOrCreateSegment(int32 SegmentIndex);
    UMaterialInstanceDynamic* GetOrCreateSegmentMID(int32 SegmentIndex, USplineMeshComponent* Segment);
    void ConfigureSegment(USplineMeshComponent* Segment, int32 SegmentIndex, float StartDistance, float EndDistance);
    void SetSegmentActive(USplineMeshComponent* Segment, bool bActive) const;
    float ComputeWidthScale() const;
    float ComputeLengthTiling(float SegmentLengthCmValue) const;
    float ComputeWidthTiling(float WidthScaleValue) const;

    UPROPERTY(Transient)
    TArray<TObjectPtr<USplineMeshComponent>> GeneratedSegments;

    UPROPERTY(Transient)
    TArray<TObjectPtr<UMaterialInstanceDynamic>> SegmentMIDs;
};
