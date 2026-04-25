#include "Snow/SnowMapKamazPlowCaptureDeformerActor.h"

#include "Components/PrimitiveComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/ChildActorComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/EngineTypes.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"
#include "UObject/UnrealType.h"

namespace
{
    static const TCHAR* DefaultPlowDeformerMeshPath = TEXT("/Engine/BasicShapes/Cube.Cube");
    static const TCHAR* DefaultWheelDeformerMeshPath = TEXT("/Engine/BasicShapes/Sphere.Sphere");
    static const TCHAR* DefaultPreviewMaterialPath = TEXT("/Game/LandscapeDeformation/Materials/M_SnowCaptureDeformer_Brown.M_SnowCaptureDeformer_Brown");
    static const TCHAR* FallbackPreviewMaterialPath = TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial");
    constexpr int32 FrontWheelCount = 2;

    FString ToSearchToken(const FName Name)
    {
        return Name.IsNone() ? FString() : Name.ToString();
    }

    int32 GetSourceScore(const USceneComponent* Component, const FName PreferredToken, const FName SecondaryToken, const FName FallbackToken)
    {
        if (!Component)
        {
            return INDEX_NONE;
        }

        const FString Name = Component->GetName();
        const FString ClassName = Component->GetClass() ? Component->GetClass()->GetName() : FString();
        const FString Preferred = ToSearchToken(PreferredToken);
        const FString Secondary = ToSearchToken(SecondaryToken);
        const FString Fallback = ToSearchToken(FallbackToken);

        if (!Preferred.IsEmpty() && (Name.Contains(Preferred) || ClassName.Contains(Preferred)))
        {
            return 3;
        }

        if (!Secondary.IsEmpty() && (Name.Contains(Secondary) || ClassName.Contains(Secondary)))
        {
            return 2;
        }

        if (!Fallback.IsEmpty() && (Name.Contains(Fallback) || ClassName.Contains(Fallback)))
        {
            return 1;
        }

        return INDEX_NONE;
    }

    USceneComponent* ResolveChildActorSource(UChildActorComponent* ChildActorComponent, const FName PreferredToken, const FName SecondaryToken, const FName FallbackToken)
    {
        if (!ChildActorComponent)
        {
            return nullptr;
        }

        AActor* ChildActor = ChildActorComponent->GetChildActor();
        if (!ChildActor)
        {
            return nullptr;
        }

        TInlineComponentArray<USceneComponent*> ChildComponents(ChildActor);
        USceneComponent* BestComponent = nullptr;
        int32 BestScore = INDEX_NONE;

        for (USceneComponent* Component : ChildComponents)
        {
            const int32 Score = GetSourceScore(Component, PreferredToken, SecondaryToken, FallbackToken);
            if (Score == INDEX_NONE)
            {
                continue;
            }

            if (Score > BestScore)
            {
                BestScore = Score;
                BestComponent = Component;
            }
        }

        if (BestComponent)
        {
            return BestComponent;
        }

        return ChildActor->GetRootComponent();
    }

    bool TryGetFloatPropertyValue(const UObject* Object, const FName PropertyName, float& OutValue)
    {
        if (!Object || PropertyName.IsNone())
        {
            return false;
        }

        const FProperty* Property = Object->GetClass()->FindPropertyByName(PropertyName);
        if (!Property)
        {
            return false;
        }

        if (const FFloatProperty* FloatProperty = CastField<FFloatProperty>(Property))
        {
            OutValue = FloatProperty->GetPropertyValue_InContainer(Object);
            return true;
        }

        if (const FDoubleProperty* DoubleProperty = CastField<FDoubleProperty>(Property))
        {
            OutValue = static_cast<float>(DoubleProperty->GetPropertyValue_InContainer(Object));
            return true;
        }

        if (const FNumericProperty* NumericProperty = CastField<FNumericProperty>(Property))
        {
            OutValue = static_cast<float>(NumericProperty->GetFloatingPointPropertyValue(Property->ContainerPtrToValuePtr<void>(Object)));
            return true;
        }

        return false;
    }

    void ConfigureDeformerMesh(UStaticMeshComponent* MeshComponent)
    {
        if (!MeshComponent)
        {
            return;
        }

        MeshComponent->SetMobility(EComponentMobility::Movable);
        MeshComponent->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
        MeshComponent->SetGenerateOverlapEvents(false);
        MeshComponent->SetCanEverAffectNavigation(false);
        MeshComponent->SetCastShadow(false);
        MeshComponent->SetRenderInMainPass(true);
        MeshComponent->SetRenderInDepthPass(true);
        MeshComponent->SetVisibleInSceneCaptureOnly(false);
        MeshComponent->SetHiddenInSceneCapture(false);
        MeshComponent->SetRenderCustomDepth(true);
        MeshComponent->SetVisibility(true, true);
    }
}

ASnowMapKamazPlowCaptureDeformerActor::ASnowMapKamazPlowCaptureDeformerActor()
{
    PrimaryActorTick.bCanEverTick = true;

    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    RootComponent = Root;
    // The SnowMap capture path is top-down. Keep the helper flat in world-space
    // so the plow footprint stays readable even if the source component pitches.
    Root->SetAbsolute(false, true, false);

    PlowDeformerMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PlowDeformerMesh"));
    PlowDeformerMesh->SetupAttachment(Root);
    ConfigureDeformerMesh(PlowDeformerMesh);
    PlowDeformerMesh->SetRelativeLocation(DeformerRelativeLocation);
    PlowDeformerMesh->SetRelativeRotation(DeformerRelativeRotation);
    PlowDeformerMesh->SetRelativeScale3D(DeformerRelativeScale);

    FrontLeftWheelDeformerMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FrontLeftWheelDeformerMesh"));
    FrontLeftWheelDeformerMesh->SetupAttachment(Root);
    ConfigureDeformerMesh(FrontLeftWheelDeformerMesh);
    FrontLeftWheelDeformerMesh->SetVisibility(false, true);
    FrontLeftWheelDeformerMesh->SetRelativeScale3D(FrontWheelDeformerScale);

    FrontRightWheelDeformerMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FrontRightWheelDeformerMesh"));
    FrontRightWheelDeformerMesh->SetupAttachment(Root);
    ConfigureDeformerMesh(FrontRightWheelDeformerMesh);
    FrontRightWheelDeformerMesh->SetVisibility(false, true);
    FrontRightWheelDeformerMesh->SetRelativeScale3D(FrontWheelDeformerScale);

    RearLeftWheelDeformerMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RearLeftWheelDeformerMesh"));
    RearLeftWheelDeformerMesh->SetupAttachment(Root);
    ConfigureDeformerMesh(RearLeftWheelDeformerMesh);
    RearLeftWheelDeformerMesh->SetVisibility(false, true);
    RearLeftWheelDeformerMesh->SetRelativeScale3D(RearWheelDeformerScale);

    RearRightWheelDeformerMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RearRightWheelDeformerMesh"));
    RearRightWheelDeformerMesh->SetupAttachment(Root);
    ConfigureDeformerMesh(RearRightWheelDeformerMesh);
    RearRightWheelDeformerMesh->SetVisibility(false, true);
    RearRightWheelDeformerMesh->SetRelativeScale3D(RearWheelDeformerScale);

    static ConstructorHelpers::FObjectFinder<UStaticMesh> PlowMeshFinder(DefaultPlowDeformerMeshPath);
    if (PlowMeshFinder.Succeeded())
    {
        PlowDeformerMesh->SetStaticMesh(PlowMeshFinder.Object);
    }

    static ConstructorHelpers::FObjectFinder<UStaticMesh> WheelMeshFinder(DefaultWheelDeformerMeshPath);
    if (WheelMeshFinder.Succeeded())
    {
        FrontLeftWheelDeformerMesh->SetStaticMesh(WheelMeshFinder.Object);
        FrontRightWheelDeformerMesh->SetStaticMesh(WheelMeshFinder.Object);
        RearLeftWheelDeformerMesh->SetStaticMesh(WheelMeshFinder.Object);
        RearRightWheelDeformerMesh->SetStaticMesh(WheelMeshFinder.Object);
    }

    UMaterialInterface* PreviewMaterial = nullptr;
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> PreviewMaterialFinder(DefaultPreviewMaterialPath);
    if (PreviewMaterialFinder.Succeeded())
    {
        PreviewMaterial = PreviewMaterialFinder.Object;
    }
    else
    {
        static ConstructorHelpers::FObjectFinder<UMaterialInterface> FallbackMaterialFinder(FallbackPreviewMaterialPath);
        if (FallbackMaterialFinder.Succeeded())
        {
            PreviewMaterial = FallbackMaterialFinder.Object;
        }
    }

    if (PreviewMaterial)
    {
        PlowDeformerMesh->SetMaterial(0, PreviewMaterial);
        FrontLeftWheelDeformerMesh->SetMaterial(0, PreviewMaterial);
        FrontRightWheelDeformerMesh->SetMaterial(0, PreviewMaterial);
        RearLeftWheelDeformerMesh->SetMaterial(0, PreviewMaterial);
        RearRightWheelDeformerMesh->SetMaterial(0, PreviewMaterial);
    }
}

void ASnowMapKamazPlowCaptureDeformerActor::BeginPlay()
{
    Super::BeginPlay();
    RefreshAttachment();
    RefreshVisibility();
    RefreshWheelTrackDeformers();
}

void ASnowMapKamazPlowCaptureDeformerActor::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);
    RefreshAttachment();
    RefreshVisibility();
    RefreshWheelTrackDeformers();
}

APawn* ASnowMapKamazPlowCaptureDeformerActor::ResolvePlayerPawn() const
{
    return UGameplayStatics::GetPlayerPawn(this, 0);
}

USkeletalMeshComponent* ASnowMapKamazPlowCaptureDeformerActor::ResolveVehicleMeshComponent(APawn* Pawn) const
{
    if (!Pawn)
    {
        return nullptr;
    }

    if (USkeletalMeshComponent* MeshComponent = Pawn->FindComponentByClass<USkeletalMeshComponent>())
    {
        return MeshComponent;
    }

    TInlineComponentArray<USkeletalMeshComponent*> MeshComponents(Pawn);
    return MeshComponents.Num() > 0 ? MeshComponents[0] : nullptr;
}

USceneComponent* ASnowMapKamazPlowCaptureDeformerActor::ResolveBestSourceComponent(APawn* Pawn) const
{
    if (!Pawn)
    {
        return nullptr;
    }

    TInlineComponentArray<USceneComponent*> Components(Pawn);
    USceneComponent* BestComponent = nullptr;
    int32 BestScore = INDEX_NONE;

    for (USceneComponent* Component : Components)
    {
        int32 Score = GetSourceScore(Component, PreferredPlowComponentToken, SecondaryPlowComponentToken, FallbackHitchComponentToken);
        USceneComponent* CandidateComponent = Component;

        if (UChildActorComponent* ChildActorComponent = Cast<UChildActorComponent>(Component))
        {
            if (USceneComponent* ChildSource = ResolveChildActorSource(
                ChildActorComponent,
                PreferredPlowComponentToken,
                SecondaryPlowComponentToken,
                FallbackHitchComponentToken))
            {
                const int32 ChildScore = GetSourceScore(
                    ChildSource,
                    PreferredPlowComponentToken,
                    SecondaryPlowComponentToken,
                    FallbackHitchComponentToken);

                if (Score != INDEX_NONE || ChildScore != INDEX_NONE)
                {
                    CandidateComponent = ChildSource;
                    Score = FMath::Max(Score, ChildScore);
                }
            }
        }

        if (Score == INDEX_NONE)
        {
            continue;
        }

        if (Score > BestScore)
        {
            BestScore = Score;
            BestComponent = CandidateComponent;
        }
    }

    return BestComponent;
}

float ASnowMapKamazPlowCaptureDeformerActor::ResolvePlowLiftHeight(const USceneComponent* Source) const
{
    float LiftHeight = 0.0f;
    if (TryGetFloatPropertyValue(Source, PlowLiftHeightPropertyName, LiftHeight))
    {
        return LiftHeight;
    }

    if (const AActor* SourceOwner = Source ? Source->GetOwner() : nullptr)
    {
        if (TryGetFloatPropertyValue(SourceOwner, PlowLiftHeightPropertyName, LiftHeight))
        {
            return LiftHeight;
        }
    }

    return 0.0f;
}

void ASnowMapKamazPlowCaptureDeformerActor::RefreshAttachment()
{
    APawn* CurrentPawn = ResolvePlayerPawn();
    USceneComponent* CurrentSource = ResolveBestSourceComponent(CurrentPawn);
    CachedVehicleMeshComponent = ResolveVehicleMeshComponent(CurrentPawn);

    if (!CurrentSource)
    {
        CachedPawn = CurrentPawn;
        CachedSourceComponent = CurrentSource;
        return;
    }

    if (CurrentPawn != CachedPawn.Get() || CurrentSource != CachedSourceComponent.Get())
    {
        CachedPawn = CurrentPawn;
        CachedSourceComponent = CurrentSource;

        AttachToComponent(CurrentSource, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
        Root->SetRelativeLocation(FVector::ZeroVector);
        Root->SetRelativeRotation(FRotator::ZeroRotator);
        Root->SetRelativeScale3D(FVector::OneVector);
        PlowDeformerMesh->SetRelativeLocation(DeformerRelativeLocation);
        PlowDeformerMesh->SetRelativeRotation(DeformerRelativeRotation);
        PlowDeformerMesh->SetRelativeScale3D(DeformerRelativeScale);
    }

    const AActor* RotationOwner = CurrentSource->GetOwner();
    const float FlatYaw = RotationOwner
        ? RotationOwner->GetActorRotation().Yaw
        : CurrentSource->GetComponentRotation().Yaw;
    SetActorRotation(FRotator(0.0f, FlatYaw, 0.0f));
}

void ASnowMapKamazPlowCaptureDeformerActor::RefreshVisibility()
{
    const USceneComponent* Source = CachedSourceComponent.Get();
    bool bActive = Source != nullptr;
    if (bActive && bUsePlowLiftVisibilityGate)
    {
        bActive = ResolvePlowLiftHeight(Source) <= ActiveWhenPlowLiftHeightAtOrBelow;
    }

    PlowDeformerMesh->SetVisibility(bActive, true);
    PlowDeformerMesh->SetRenderCustomDepth(bActive);
}

void ASnowMapKamazPlowCaptureDeformerActor::HideWheelTrackDeformers()
{
    for (UStaticMeshComponent* WheelMesh : {
        FrontLeftWheelDeformerMesh.Get(),
        FrontRightWheelDeformerMesh.Get(),
        RearLeftWheelDeformerMesh.Get(),
        RearRightWheelDeformerMesh.Get()})
    {
        if (!WheelMesh)
        {
            continue;
        }

        WheelMesh->SetVisibility(false, true);
        WheelMesh->SetRenderCustomDepth(false);
    }
}

void ASnowMapKamazPlowCaptureDeformerActor::RefreshWheelTrackDeformers()
{
    if (!bEnableWheelDeformers)
    {
        HideWheelTrackDeformers();
        return;
    }

    UWorld* World = GetWorld();
    USkeletalMeshComponent* VehicleMeshComponent = CachedVehicleMeshComponent.Get();
    APawn* Pawn = CachedPawn.Get();
    if (!World || !VehicleMeshComponent || !Pawn)
    {
        HideWheelTrackDeformers();
        return;
    }

    TArray<UStaticMeshComponent*> WheelMeshes = {
        FrontLeftWheelDeformerMesh.Get(),
        FrontRightWheelDeformerMesh.Get(),
        RearLeftWheelDeformerMesh.Get(),
        RearRightWheelDeformerMesh.Get()
    };

    const float FlatYaw = Pawn->GetActorRotation().Yaw;
    FCollisionQueryParams TraceParams(SCENE_QUERY_STAT(SnowMapWheelDeformerTrace), false, this);
    TraceParams.AddIgnoredActor(this);
    TraceParams.AddIgnoredActor(Pawn);

    for (int32 WheelIndex = 0; WheelIndex < WheelMeshes.Num(); ++WheelIndex)
    {
        UStaticMeshComponent* WheelMesh = WheelMeshes[WheelIndex];
        if (!WheelMesh)
        {
            continue;
        }

        if (!WheelBoneNames.IsValidIndex(WheelIndex))
        {
            WheelMesh->SetVisibility(false, true);
            WheelMesh->SetRenderCustomDepth(false);
            continue;
        }

        const FName BoneName = WheelBoneNames[WheelIndex];
        if (BoneName.IsNone() || VehicleMeshComponent->GetBoneIndex(BoneName) == INDEX_NONE)
        {
            WheelMesh->SetVisibility(false, true);
            WheelMesh->SetRenderCustomDepth(false);
            continue;
        }

        const FVector BoneLocation = VehicleMeshComponent->GetBoneLocation(BoneName);
        FHitResult HitResult;
        const bool bHit = World->LineTraceSingleByChannel(
            HitResult,
            BoneLocation + FVector(0.0f, 0.0f, WheelTraceUpCm),
            BoneLocation - FVector(0.0f, 0.0f, WheelTraceDownCm),
            ECC_Visibility,
            TraceParams);

        if (!bHit)
        {
            WheelMesh->SetVisibility(false, true);
            WheelMesh->SetRenderCustomDepth(false);
            continue;
        }

        const FVector StampLocation = HitResult.Location + FVector(0.0f, 0.0f, WheelStampLiftAboveHitCm);
        const FVector StampScale = WheelIndex < FrontWheelCount
            ? FrontWheelDeformerScale
            : RearWheelDeformerScale;

        WheelMesh->SetWorldLocation(StampLocation);
        WheelMesh->SetWorldRotation(FRotator(0.0f, FlatYaw, 0.0f));
        WheelMesh->SetWorldScale3D(StampScale);
        WheelMesh->SetVisibility(true, true);
        WheelMesh->SetRenderCustomDepth(true);
    }
}
