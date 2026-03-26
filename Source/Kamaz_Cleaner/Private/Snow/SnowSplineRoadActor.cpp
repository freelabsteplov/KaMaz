#include "Snow/SnowSplineRoadActor.h"

#include "Components/SceneComponent.h"
#include "Components/SplineComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Snow/SnowReceiverSurfaceComponent.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
const TCHAR* SegmentPrefix = TEXT("SplineRoadSegment_");

bool TryExtractSegmentIndex(const FString& Name, int32& OutIndex)
{
    if (!Name.StartsWith(SegmentPrefix))
    {
        return false;
    }

    FString Suffix = Name.RightChop(FCString::Strlen(SegmentPrefix));
    if (Suffix.IsEmpty())
    {
        return false;
    }

    // Support duplicated editor names like SplineRoadSegment_0_2.
    int32 UnderscoreIndex = INDEX_NONE;
    if (Suffix.FindChar(TEXT('_'), UnderscoreIndex))
    {
        Suffix = Suffix.Left(UnderscoreIndex);
    }

    int32 ParsedIndex = INDEX_NONE;
    if (!LexTryParseString(ParsedIndex, *Suffix) || ParsedIndex < 0)
    {
        return false;
    }

    OutIndex = ParsedIndex;
    return true;
}
}

ASnowSplineRoadActor::ASnowSplineRoadActor()
{
    PrimaryActorTick.bCanEverTick = false;

    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    RootComponent = Root;

    Spline = CreateDefaultSubobject<USplineComponent>(TEXT("Spline"));
    Spline->SetupAttachment(Root);
    Spline->SetClosedLoop(false);

    SnowReceiver = CreateDefaultSubobject<USnowReceiverSurfaceComponent>(TEXT("SnowReceiverSurfaceComponent"));
    SnowReceiver->bParticipatesInPersistentSnowState = true;
    SnowReceiver->SurfaceFamily = ESnowReceiverSurfaceFamily::Road;
    SnowReceiver->ReceiverPriority = 100;
    SnowReceiver->ReceiverSetTag = TEXT("SnowMVPRuntimeTrail");

    static ConstructorHelpers::FObjectFinder<UStaticMesh> PlaneMeshFinder(
        TEXT("/Engine/EditorMeshes/PlanarReflectionPlane.PlanarReflectionPlane"));
    if (PlaneMeshFinder.Succeeded())
    {
        SegmentMesh = PlaneMeshFinder.Object;
    }

    static ConstructorHelpers::FObjectFinder<UMaterialInterface> SnowMaterialFinder(
        TEXT("/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP.MI_SnowReceiver_RVT_Height_MVP"));
    if (SnowMaterialFinder.Succeeded())
    {
        SnowRoadMaterial = SnowMaterialFinder.Object;
    }

    Spline->ClearSplinePoints(false);
    Spline->AddSplinePoint(FVector::ZeroVector, ESplineCoordinateSpace::Local, false);
    Spline->AddSplinePoint(FVector(10000.0f, 0.0f, 0.0f), ESplineCoordinateSpace::Local, true);
}

void ASnowSplineRoadActor::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);

    // Width must be driven by RoadWidthCm, not actor scale.
    if (!GetActorScale3D().Equals(FVector::OneVector, 0.001f))
    {
        SetActorScale3D(FVector::OneVector);
    }

    RebuildSplineMeshes();
}

void ASnowSplineRoadActor::CacheExistingSegments()
{
    TMap<int32, TObjectPtr<USplineMeshComponent>> IndexedSegments;
    TArray<TObjectPtr<USplineMeshComponent>> DuplicateSegments;

    TInlineComponentArray<USplineMeshComponent*> ExistingSegments(this);
    GetComponents(ExistingSegments);

    for (USplineMeshComponent* Segment : ExistingSegments)
    {
        if (!IsValid(Segment))
        {
            continue;
        }

        int32 SegmentIndex = INDEX_NONE;
        if (!TryExtractSegmentIndex(Segment->GetName(), SegmentIndex))
        {
            continue;
        }

        if (IndexedSegments.Contains(SegmentIndex))
        {
            DuplicateSegments.Add(Segment);
            continue;
        }

        IndexedSegments.Add(SegmentIndex, Segment);
    }

    int32 MaxIndex = -1;
    for (const TPair<int32, TObjectPtr<USplineMeshComponent>>& Pair : IndexedSegments)
    {
        MaxIndex = FMath::Max(MaxIndex, Pair.Key);
    }

    if (MaxIndex >= 0)
    {
        GeneratedSegments.SetNumZeroed(MaxIndex + 1);
        SegmentMIDs.SetNumZeroed(MaxIndex + 1);
    }

    for (const TPair<int32, TObjectPtr<USplineMeshComponent>>& Pair : IndexedSegments)
    {
        const int32 SegmentIndex = Pair.Key;
        USplineMeshComponent* Segment = Pair.Value.Get();
        if (!IsValid(Segment))
        {
            continue;
        }

        GeneratedSegments[SegmentIndex] = Segment;
        if (!Segment->IsRegistered())
        {
            Segment->RegisterComponent();
        }

        if (UMaterialInstanceDynamic* MID = Cast<UMaterialInstanceDynamic>(Segment->GetMaterial(0)))
        {
            SegmentMIDs[SegmentIndex] = MID;
        }
    }

    // Keep duplicates inert instead of destroying during construction.
    for (TObjectPtr<USplineMeshComponent>& Segment : DuplicateSegments)
    {
        SetSegmentActive(Segment.Get(), false);
    }
}

USplineMeshComponent* ASnowSplineRoadActor::GetOrCreateSegment(int32 SegmentIndex)
{
    if (GeneratedSegments.Num() <= SegmentIndex)
    {
        GeneratedSegments.SetNumZeroed(SegmentIndex + 1);
        SegmentMIDs.SetNumZeroed(SegmentIndex + 1);
    }

    USplineMeshComponent* Segment = GeneratedSegments[SegmentIndex].Get();
    if (IsValid(Segment))
    {
        return Segment;
    }

    const FName SegmentName(*FString::Printf(TEXT("%s%d"), SegmentPrefix, SegmentIndex));
    Segment = FindObjectFast<USplineMeshComponent>(this, SegmentName);
    bool bCreatedNewSegment = false;

    if (!IsValid(Segment))
    {
        Segment = NewObject<USplineMeshComponent>(this, SegmentName, RF_Transactional);
        bCreatedNewSegment = IsValid(Segment);
    }

    if (!IsValid(Segment))
    {
        return nullptr;
    }

    Segment->CreationMethod = EComponentCreationMethod::Instance;
    Segment->SetupAttachment(Spline);
    Segment->SetMobility(EComponentMobility::Movable);
    Segment->SetCastShadow(false);
    Segment->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);

    if (SegmentMesh)
    {
        Segment->SetStaticMesh(SegmentMesh);
    }

    Segment->SetForwardAxis(ForwardAxis, false);

    if (bCreatedNewSegment)
    {
        AddInstanceComponent(Segment);
    }
    if (!Segment->IsRegistered())
    {
        Segment->RegisterComponent();
    }

    GeneratedSegments[SegmentIndex] = Segment;
    return Segment;
}

UMaterialInstanceDynamic* ASnowSplineRoadActor::GetOrCreateSegmentMID(int32 SegmentIndex, USplineMeshComponent* Segment)
{
    if (!SnowRoadMaterial || !IsValid(Segment))
    {
        return nullptr;
    }

    if (SegmentMIDs.Num() <= SegmentIndex)
    {
        SegmentMIDs.SetNumZeroed(SegmentIndex + 1);
    }

    UMaterialInstanceDynamic* MID = SegmentMIDs[SegmentIndex].Get();
    if (!IsValid(MID))
    {
        MID = Cast<UMaterialInstanceDynamic>(Segment->GetMaterial(0));
    }

    if (!IsValid(MID))
    {
        MID = UMaterialInstanceDynamic::Create(SnowRoadMaterial, this);
    }

    if (!IsValid(MID))
    {
        return nullptr;
    }

    Segment->SetMaterial(0, MID);
    SegmentMIDs[SegmentIndex] = MID;
    return MID;
}

void ASnowSplineRoadActor::SetSegmentActive(USplineMeshComponent* Segment, bool bActive) const
{
    if (!IsValid(Segment))
    {
        return;
    }

    Segment->SetVisibility(bActive, true);
    Segment->SetHiddenInGame(!bActive, true);
    Segment->SetCollisionEnabled(bActive ? ECollisionEnabled::QueryAndPhysics : ECollisionEnabled::NoCollision);
}

float ASnowSplineRoadActor::ComputeWidthScale() const
{
    const float SafeReferenceWidth = FMath::Max(1.0f, MeshReferenceWidthCm);
    return RoadWidthCm / SafeReferenceWidth;
}

float ASnowSplineRoadActor::ComputeLengthTiling(float SegmentLengthCmValue) const
{
    const float SafeReferenceLength = FMath::Max(1.0f, MeshReferenceLengthCm);
    return (SegmentLengthCmValue / SafeReferenceLength) * FMath::Max(0.001f, LengthTiling);
}

float ASnowSplineRoadActor::ComputeWidthTiling(float WidthScaleValue) const
{
    return WidthScaleValue * FMath::Max(0.001f, WidthTiling);
}

void ASnowSplineRoadActor::ConfigureSegment(
    USplineMeshComponent* Segment,
    int32 SegmentIndex,
    float StartDistance,
    float EndDistance)
{
    if (!IsValid(Segment) || !Spline || !SegmentMesh)
    {
        return;
    }

    const FVector StartPos = Spline->GetLocationAtDistanceAlongSpline(StartDistance, ESplineCoordinateSpace::Local);
    const FVector StartTangent = Spline->GetTangentAtDistanceAlongSpline(StartDistance, ESplineCoordinateSpace::Local);
    const FVector EndPos = Spline->GetLocationAtDistanceAlongSpline(EndDistance, ESplineCoordinateSpace::Local);
    const FVector EndTangent = Spline->GetTangentAtDistanceAlongSpline(EndDistance, ESplineCoordinateSpace::Local);

    const float WidthScale = ComputeWidthScale();
    const FVector2D CrossSectionScale(WidthScale, FMath::Max(0.1f, ThicknessScale));

    Segment->SetStaticMesh(SegmentMesh);
    Segment->SetForwardAxis(ForwardAxis, false);
    Segment->SetStartAndEnd(StartPos, StartTangent, EndPos, EndTangent, false);
    Segment->SetStartScale(CrossSectionScale, false);
    Segment->SetEndScale(CrossSectionScale, false);
    Segment->UpdateMesh();
    SetSegmentActive(Segment, true);

    if (SnowRoadMaterial)
    {
        if (UMaterialInstanceDynamic* MID = GetOrCreateSegmentMID(SegmentIndex, Segment))
        {
            const float SegmentWorldLength = FMath::Max(1.0f, EndDistance - StartDistance);
            MID->SetScalarParameterValue(LengthTilingParameterName, ComputeLengthTiling(SegmentWorldLength));
            MID->SetScalarParameterValue(WidthTilingParameterName, ComputeWidthTiling(WidthScale));
        }
        else
        {
            Segment->SetMaterial(0, SnowRoadMaterial);
        }
    }
}

void ASnowSplineRoadActor::RebuildSplineMeshes()
{
    if (!Spline)
    {
        return;
    }

    if (SnowReceiver)
    {
        SnowReceiver->bParticipatesInPersistentSnowState = true;
        SnowReceiver->SurfaceFamily = SurfaceFamily;
        SnowReceiver->ReceiverPriority = 100;
        SnowReceiver->ReceiverSetTag = TEXT("SnowMVPRuntimeTrail");
    }

    CacheExistingSegments();

    if (!SegmentMesh || Spline->GetNumberOfSplinePoints() < 2)
    {
        for (TObjectPtr<USplineMeshComponent>& Segment : GeneratedSegments)
        {
            SetSegmentActive(Segment.Get(), false);
        }
        return;
    }

    const float TotalLength = Spline->GetSplineLength();
    if (TotalLength <= KINDA_SMALL_NUMBER)
    {
        for (TObjectPtr<USplineMeshComponent>& Segment : GeneratedSegments)
        {
            SetSegmentActive(Segment.Get(), false);
        }
        return;
    }

    const float SafeSegmentLength = FMath::Max(100.0f, SegmentLengthCm);
    const int32 SegmentCount = bForceSingleSplineMeshSegment
        ? 1
        : FMath::Max(1, FMath::CeilToInt(TotalLength / SafeSegmentLength));

    for (int32 SegmentIndex = 0; SegmentIndex < SegmentCount; ++SegmentIndex)
    {
        USplineMeshComponent* Segment = GetOrCreateSegment(SegmentIndex);
        if (!IsValid(Segment))
        {
            continue;
        }

        const float StartDistance = bForceSingleSplineMeshSegment
            ? 0.0f
            : SegmentIndex * SafeSegmentLength;
        const float EndDistance = bForceSingleSplineMeshSegment
            ? TotalLength
            : FMath::Min((SegmentIndex + 1) * SafeSegmentLength, TotalLength);

        if (EndDistance - StartDistance <= KINDA_SMALL_NUMBER)
        {
            SetSegmentActive(Segment, false);
            continue;
        }

        ConfigureSegment(Segment, SegmentIndex, StartDistance, EndDistance);
    }

    for (int32 SegmentIndex = SegmentCount; SegmentIndex < GeneratedSegments.Num(); ++SegmentIndex)
    {
        SetSegmentActive(GeneratedSegments[SegmentIndex].Get(), false);
    }
}
