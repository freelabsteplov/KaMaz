#include "Snow/SnowRuntimeTrailBridgeComponent.h"

#include "Components/InstancedStaticMeshComponent.h"
#include "Components/MeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SceneComponent.h"
#include "DrawDebugHelpers.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "LandscapeProxy.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstance.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"
#include "UObject/UnrealType.h"
#include "Snow/SnowReceiverSurfaceComponent.h"
#include "Snow/SnowReceiverSurfaceTags.h"
#include "Snow/SnowStateBlueprintLibrary.h"
#include "Snow/SnowStateRuntimeSettings.h"
#include "VT/RuntimeVirtualTexture.h"
#include "Engine/StaticMesh.h"

namespace
{
    static const TCHAR* DefaultStampMeshPath = TEXT("/Engine/BasicShapes/Plane.Plane");
    static const TCHAR* DefaultStampMaterialPath = TEXT("/Game/CityPark/SnowSystem/RVT_MVP/M_RVT_DebugWriter_MVP.M_RVT_DebugWriter_MVP");
    static const TCHAR* DefaultTargetRvtPath = TEXT("/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP.RVT_SnowMask_MVP");
    constexpr float DebugSourceSphereRadiusCm = 28.0f;
    constexpr float DebugPlowBoxHeightCm = 18.0f;
    constexpr float DebugDrawLifetime = 0.0f;
    constexpr TCHAR PlowBrushNameTokenA[] = TEXT("PlowBrush");
    constexpr TCHAR PlowBrushNameTokenB[] = TEXT("BP_PlowBrush");
    constexpr TCHAR KamazNameToken[] = TEXT("Kamaz");
    constexpr TCHAR HeightReceiverMaterialToken[] = TEXT("SnowReceiver_RVT_Height_MVP");
    constexpr TCHAR SnowSplineRoadToken[] = TEXT("SnowSplineRoad");
    constexpr TCHAR SplineRoadSegmentToken[] = TEXT("SplineRoadSegment");
    constexpr TCHAR BridgeSurfaceToken[] = TEXT("SnowHeightBridgeSurface");
    constexpr float LegacyAlwaysActiveMaxRelativeZ = 95.0f;
    constexpr float DefaultPlowActiveMaxRelativeZ = -0.5f;
    constexpr float LegacyKamazTrailLengthCm = 120.0f;
    constexpr float LegacyKamazTrailWidthCmA = 320.0f;
    constexpr float LegacyKamazTrailWidthCmB = 340.0f;
    constexpr float DefaultKamazTrailLengthCm = 50.0f;
    constexpr float DefaultKamazTrailWidthCm = 350.0f;
    constexpr float LegacyTrailFootprintToleranceCm = 1.0f;
    constexpr float SplineRoadRuntimeHeightScale = 0.0f;
    constexpr float RoadCarrierRuntimeHeightScale = 1.0f;
    constexpr float BridgeSurfaceRuntimeHeightScale = 0.06f;
    constexpr float LandscapeRuntimeHeightScale = 0.0f;
    constexpr float ReceiverFallbackSearchMarginCm = 220.0f;
    constexpr int32 EngagementBandCount = 3;
    constexpr float EngagementBandStrengths[EngagementBandCount] = { 0.35f, 0.7f, 1.0f };
    static const FName PlowLiftHeightPropertyName(TEXT("PlowLiftHeight"));
    static const FName PlowClearingEnabledPropertyName(TEXT("bEnablePlowClearing"));
    static const FName VisualClearMaskStrengthParamName(TEXT("VisualClearMaskStrength"));
    static const FName DepthMaskBoostParamName(TEXT("DepthMaskBoost"));
    static const FName ThinSnowMinVisualOpacityParamName(TEXT("ThinSnowMinVisualOpacity"));
    static const FName EdgeDustingStrengthParamName(TEXT("EdgeDustingStrength"));
    static const FName WheelTrackMaskAmplifyParamName(TEXT("WheelTrackMaskAmplify"));
    static const FName WheelTrackContrastParamName(TEXT("WheelTrackContrast"));
    static const FName WheelTrackStrengthParamName(TEXT("WheelTrackStrength"));
    static const FName WheelTrackAsphaltRoughnessParamName(TEXT("WheelTrackAsphaltRoughness"));
    static const FName WheelTrackSnowRoughnessParamName(TEXT("WheelTrackSnowRoughness"));
    static const FName RightBermRaiseParamName(TEXT("RightBermRaise"));
    static const FName RepeatAccumulationDepthParamName(TEXT("RepeatAccumulationDepth"));
    static const FName PressedSnowColorParamName(TEXT("PressedSnowColor"));
    static const FName ThinSnowUnderColorParamName(TEXT("ThinSnowUnderColor"));
    constexpr float RuntimeVisualClearMaskStrength = 1.0f;
    constexpr float RuntimeDepthMaskBoost = 1.0f;
    constexpr float RuntimeThinSnowMinVisualOpacity = 0.38f;
    constexpr float RuntimeEdgeDustingStrength = 0.0f;
    constexpr float RuntimeWheelTrackMaskAmplify = 0.0f;
    constexpr float RuntimeWheelTrackContrast = 1.0f;
    constexpr float RuntimeWheelTrackStrength = 0.0f;
    constexpr float RuntimeWheelTrackAsphaltRoughness = 0.46f;
    constexpr float RuntimeWheelTrackSnowRoughness = 0.68f;
    constexpr float RuntimeRightBermRaise = 0.0f;
    constexpr float RuntimeRepeatAccumulationDepth = 0.0f;
    const FLinearColor RuntimePressedSnowColor(0.28f, 0.29f, 0.31f, 1.0f);
    const FLinearColor RuntimeThinSnowUnderColor(0.38f, 0.39f, 0.41f, 1.0f);

    bool IsHeightReceiverMaterial(const UMaterialInterface* Material)
    {
        if (!Material)
        {
            return false;
        }

        auto MatchesHeightReceiverToken = [](const UMaterialInterface* CandidateMaterial)
        {
            if (!CandidateMaterial)
            {
                return false;
            }

            const FString Path = CandidateMaterial->GetPathName();
            const FString Name = CandidateMaterial->GetName();
            return Path.Contains(HeightReceiverMaterialToken) || Name.Contains(HeightReceiverMaterialToken);
        };

        if (MatchesHeightReceiverToken(Material))
        {
            return true;
        }

        const UMaterialInstance* MaterialInstance = Cast<UMaterialInstance>(Material);
        while (MaterialInstance)
        {
            const UMaterialInterface* Parent = MaterialInstance->Parent;
            if (!Parent)
            {
                break;
            }

            if (MatchesHeightReceiverToken(Parent))
            {
                return true;
            }

            MaterialInstance = Cast<UMaterialInstance>(Parent);
        }

        return false;
    }

    int32 GetPlowSourcePreferenceScore(const USceneComponent* Component)
    {
        if (!Component)
        {
            return INDEX_NONE;
        }

        const FString Name = Component->GetName();
        const FString ClassName = Component->GetClass() ? Component->GetClass()->GetName() : FString();

        if (Name.Contains(TEXT("BP_PlowBrush_Component")) || ClassName.Contains(TEXT("BP_PlowBrush_Component")))
        {
            return 3;
        }

        // The visible child actor is useful for artist alignment, but SnowTest still relies on
        // the BP plow brush component as the authoritative runtime clearing source.
        if (Name.Equals(TEXT("PlowBrush")) || (Name.Contains(TEXT("PlowBrush")) && !Name.Contains(TEXT("BP_PlowBrush_Component"))))
        {
            return 2;
        }

        if (Name.Contains(PlowBrushNameTokenA) || Name.Contains(PlowBrushNameTokenB))
        {
            return 1;
        }

        return INDEX_NONE;
    }

    bool IsPreferredPlowSource(const USceneComponent* Component)
    {
        return GetPlowSourcePreferenceScore(Component) >= 2;
    }

    USceneComponent* FindPlowComponentOnActor(AActor* Actor)
    {
        if (!Actor)
        {
            return nullptr;
        }

        USceneComponent* BestComponent = nullptr;
        int32 BestScore = INDEX_NONE;

        TInlineComponentArray<USceneComponent*> Components;
        Actor->GetComponents(Components);
        for (USceneComponent* Component : Components)
        {
            if (!Component)
            {
                continue;
            }

            const FString Name = Component->GetName();
            const int32 Score = GetPlowSourcePreferenceScore(Component);
            if (Score != INDEX_NONE)
            {
                if (Score > BestScore)
                {
                    BestScore = Score;
                    BestComponent = Component;
                }
                if (BestScore >= 3)
                {
                    break;
                }
            }
        }

        return BestComponent;
    }

    USceneComponent* FindPlowComponentOnPossessedPawn(UWorld* World)
    {
        if (!World)
        {
            return nullptr;
        }

        APlayerController* PlayerController = World->GetFirstPlayerController();
        if (!PlayerController)
        {
            return nullptr;
        }

        APawn* ControlledPawn = PlayerController->GetPawn();
        if (!ControlledPawn)
        {
            return nullptr;
        }

        return FindPlowComponentOnActor(ControlledPawn);
    }

    bool ActorLooksLikeKamaz(const AActor* Actor)
    {
        if (!Actor)
        {
            return false;
        }

        const FString Name = Actor->GetName();
        const FString ClassName = Actor->GetClass() ? Actor->GetClass()->GetName() : FString();
        return Name.Contains(KamazNameToken) || ClassName.Contains(KamazNameToken);
    }

    bool ComponentLooksLikePlowSource(const USceneComponent* Component)
    {
        if (!Component)
        {
            return false;
        }

        const FString Name = Component->GetName();
        if (Name.Contains(PlowBrushNameTokenA) || Name.Contains(PlowBrushNameTokenB))
        {
            return true;
        }

        const AActor* Owner = Component->GetOwner();
        return Owner && ActorLooksLikeKamaz(Owner) && Name.Contains(TEXT("Brush"));
    }

    bool IsSourceHeightActive(const USceneComponent* Source, const bool bUseHeightGate, const float MaxRelativeZ)
    {
        if (!Source)
        {
            return false;
        }

        if (!bUseHeightGate)
        {
            return true;
        }

        return Source->GetRelativeLocation().Z <= MaxRelativeZ;
    }

    bool MatchesLegacyKamazTrailFootprint(const float LengthCm, const float WidthCm)
    {
        return FMath::IsNearlyEqual(LengthCm, LegacyKamazTrailLengthCm, LegacyTrailFootprintToleranceCm)
            && (FMath::IsNearlyEqual(WidthCm, LegacyKamazTrailWidthCmA, LegacyTrailFootprintToleranceCm)
                || FMath::IsNearlyEqual(WidthCm, LegacyKamazTrailWidthCmB, LegacyTrailFootprintToleranceCm));
    }

    FVector2D ResolveEffectivePlowFootprintCm(
        const USceneComponent* Source,
        const AActor* SourceOwner,
        const float ConfiguredLengthCm,
        const float ConfiguredWidthCm)
    {
        if (!MatchesLegacyKamazTrailFootprint(ConfiguredLengthCm, ConfiguredWidthCm))
        {
            return FVector2D(ConfiguredLengthCm, ConfiguredWidthCm);
        }

        const AActor* EffectiveOwner = SourceOwner ? SourceOwner : (Source ? Source->GetOwner() : nullptr);
        if (ComponentLooksLikePlowSource(Source) || ActorLooksLikeKamaz(EffectiveOwner))
        {
            return FVector2D(DefaultKamazTrailLengthCm, DefaultKamazTrailWidthCm);
        }

        return FVector2D(ConfiguredLengthCm, ConfiguredWidthCm);
    }

    bool TryGetBoolPropertyValue(const UObject* Object, const FName PropertyName, bool& OutValue)
    {
        if (!Object || PropertyName.IsNone())
        {
            return false;
        }

        if (const FProperty* Property = Object->GetClass()->FindPropertyByName(PropertyName))
        {
            if (const FBoolProperty* BoolProperty = CastField<FBoolProperty>(Property))
            {
                OutValue = BoolProperty->GetPropertyValue_InContainer(Object);
                return true;
            }
        }

        return false;
    }

    bool TryGetFloatPropertyValue(const UObject* Object, const FName PropertyName, float& OutValue)
    {
        if (!Object || PropertyName.IsNone())
        {
            return false;
        }

        if (const FProperty* Property = Object->GetClass()->FindPropertyByName(PropertyName))
        {
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
        }

        return false;
    }

    bool ObjectLooksLikeSplineRoadReceiver(const UObject* Object)
    {
        const UObject* CurrentObject = Object;
        while (CurrentObject)
        {
            const FString Name = CurrentObject->GetName();
            const FString Path = CurrentObject->GetPathName();
            if (Name.Contains(SnowSplineRoadToken)
                || Name.Contains(SplineRoadSegmentToken)
                || Path.Contains(SnowSplineRoadToken)
                || Path.Contains(SplineRoadSegmentToken))
            {
                return true;
            }

            CurrentObject = CurrentObject->GetOuter();
        }

        return false;
    }

    bool ObjectLooksLikeBridgeSurfaceReceiver(const UObject* Object)
    {
        const UObject* CurrentObject = Object;
        while (CurrentObject)
        {
            const FString Name = CurrentObject->GetName();
            const FString Path = CurrentObject->GetPathName();
            if (Name.Contains(BridgeSurfaceToken) || Path.Contains(BridgeSurfaceToken))
            {
                return true;
            }

            CurrentObject = CurrentObject->GetOuter();
        }

        return false;
    }

    const USnowReceiverSurfaceComponent* FindReceiverSurfaceForObject(const UObject* Object)
    {
        const UObject* CurrentObject = Object;
        while (CurrentObject)
        {
            if (const AActor* Actor = Cast<AActor>(CurrentObject))
            {
                if (const USnowReceiverSurfaceComponent* ReceiverSurface = Actor->FindComponentByClass<USnowReceiverSurfaceComponent>())
                {
                    return ReceiverSurface;
                }
            }
            else if (const UActorComponent* ActorComponent = Cast<UActorComponent>(CurrentObject))
            {
                if (const AActor* Owner = ActorComponent->GetOwner())
                {
                    if (const USnowReceiverSurfaceComponent* ReceiverSurface = Owner->FindComponentByClass<USnowReceiverSurfaceComponent>())
                    {
                        return ReceiverSurface;
                    }
                }
            }

            CurrentObject = CurrentObject->GetOuter();
        }

        return nullptr;
    }

    bool ObjectHasRoadSnowCarrierHeightTag(const UObject* Object)
    {
        if (const USnowReceiverSurfaceComponent* ReceiverSurface = FindReceiverSurfaceForObject(Object))
        {
            return ReceiverSurface->ReceiverSetTag == SnowReceiverSurfaceTags::RoadSnowCarrierHeight();
        }

        return false;
    }

    bool ShouldApplyLegacyRuntimeReceiverOverrides(const UObject* Object)
    {
        return !ObjectHasRoadSnowCarrierHeightTag(Object);
    }

    float ResolveRuntimeHeightScaleForReceiver(const UObject* Object)
    {
        if (ObjectHasRoadSnowCarrierHeightTag(Object))
        {
            // Explicit tagged road carriers use local RVT-driven height like SnowTest and must
            // keep their authored material defaults instead of receiving a whole-mesh runtime
            // height amplitude.
            return RoadCarrierRuntimeHeightScale;
        }

        // Legacy bridge surfaces still use the name-based token until they receive explicit tags.
        if (ObjectLooksLikeBridgeSurfaceReceiver(Object))
        {
            return BridgeSurfaceRuntimeHeightScale;
        }

        if (ObjectLooksLikeSplineRoadReceiver(Object))
        {
            return SplineRoadRuntimeHeightScale;
        }

        return 0.0f;
    }

    bool TryProjectToNearbySnowReceiverSurface(
        UWorld* World,
        const FVector& SourceLocation,
        const AActor* IgnoredActor,
        FVector& OutProjectedLocation,
        ESnowReceiverSurfaceFamily* OutSurfaceFamily = nullptr)
    {
        if (!World)
        {
            return false;
        }

        bool bFoundCandidate = false;
        float BestDistanceSq = TNumericLimits<float>::Max();
        int32 BestPriority = TNumericLimits<int32>::Lowest();
        float BestTopZ = -FLT_MAX;
        ESnowReceiverSurfaceFamily BestSurfaceFamily = ESnowReceiverSurfaceFamily::Road;
        FVector BestProjectedLocation = SourceLocation;

        for (TActorIterator<AActor> It(World); It; ++It)
        {
            AActor* Actor = *It;
            if (!Actor || Actor == IgnoredActor)
            {
                continue;
            }

            bool bCandidate = false;
            int32 CandidatePriority = 0;
            ESnowReceiverSurfaceFamily CandidateSurfaceFamily = ESnowReceiverSurfaceFamily::Road;

            if (Cast<ALandscapeProxy>(Actor))
            {
                bCandidate = true;
                CandidateSurfaceFamily = ESnowReceiverSurfaceFamily::Landscape;
            }

            if (const USnowReceiverSurfaceComponent* ReceiverSurface = Actor->FindComponentByClass<USnowReceiverSurfaceComponent>())
            {
                bCandidate = true;
                CandidatePriority = ReceiverSurface->ReceiverPriority;
                CandidateSurfaceFamily = ReceiverSurface->SurfaceFamily;
            }

            if (!bCandidate)
            {
                TInlineComponentArray<UMeshComponent*> MeshComponents;
                Actor->GetComponents(MeshComponents);
                for (const UMeshComponent* MeshComponent : MeshComponents)
                {
                    if (!MeshComponent)
                    {
                        continue;
                    }

                    const int32 MaterialCount = MeshComponent->GetNumMaterials();
                    for (int32 MaterialIndex = 0; MaterialIndex < MaterialCount; ++MaterialIndex)
                    {
                        if (IsHeightReceiverMaterial(MeshComponent->GetMaterial(MaterialIndex)))
                        {
                            bCandidate = true;
                            break;
                        }
                    }

                    if (bCandidate)
                    {
                        break;
                    }
                }
            }

            if (!bCandidate)
            {
                continue;
            }

            FVector BoundsOrigin = FVector::ZeroVector;
            FVector BoundsExtent = FVector::ZeroVector;
            Actor->GetActorBounds(false, BoundsOrigin, BoundsExtent);
            if (BoundsExtent.IsNearlyZero())
            {
                continue;
            }

            const float ExcessX = FMath::Max(
                FMath::Abs(SourceLocation.X - BoundsOrigin.X) - (BoundsExtent.X + ReceiverFallbackSearchMarginCm),
                0.0f);
            const float ExcessY = FMath::Max(
                FMath::Abs(SourceLocation.Y - BoundsOrigin.Y) - (BoundsExtent.Y + ReceiverFallbackSearchMarginCm),
                0.0f);
            const float DistanceSq = FMath::Square(ExcessX) + FMath::Square(ExcessY);
            const float CandidateTopZ = BoundsOrigin.Z + BoundsExtent.Z;
            const bool bPreferCandidate = !bFoundCandidate
                || DistanceSq < BestDistanceSq
                || (FMath::IsNearlyEqual(DistanceSq, BestDistanceSq, 1.0f)
                    && (CandidatePriority > BestPriority
                        || (CandidatePriority == BestPriority && CandidateTopZ > BestTopZ)));

            if (!bPreferCandidate)
            {
                continue;
            }

            bFoundCandidate = true;
            BestDistanceSq = DistanceSq;
            BestPriority = CandidatePriority;
            BestTopZ = CandidateTopZ;
            BestSurfaceFamily = CandidateSurfaceFamily;
            BestProjectedLocation = FVector(SourceLocation.X, SourceLocation.Y, CandidateTopZ);
        }

        if (!bFoundCandidate)
        {
            return false;
        }

        OutProjectedLocation = BestProjectedLocation;
        if (OutSurfaceFamily)
        {
            *OutSurfaceFamily = BestSurfaceFamily;
        }
        return true;
    }

    void ApplyRuntimeReceiverVisualProfile(UMaterialInstanceDynamic* DynamicMaterial)
    {
        if (!DynamicMaterial)
        {
            return;
        }

        DynamicMaterial->SetScalarParameterValue(VisualClearMaskStrengthParamName, RuntimeVisualClearMaskStrength);
        DynamicMaterial->SetScalarParameterValue(DepthMaskBoostParamName, RuntimeDepthMaskBoost);
        DynamicMaterial->SetScalarParameterValue(ThinSnowMinVisualOpacityParamName, RuntimeThinSnowMinVisualOpacity);
        DynamicMaterial->SetScalarParameterValue(EdgeDustingStrengthParamName, RuntimeEdgeDustingStrength);
        DynamicMaterial->SetScalarParameterValue(WheelTrackMaskAmplifyParamName, RuntimeWheelTrackMaskAmplify);
        DynamicMaterial->SetScalarParameterValue(WheelTrackContrastParamName, RuntimeWheelTrackContrast);
        DynamicMaterial->SetScalarParameterValue(WheelTrackStrengthParamName, RuntimeWheelTrackStrength);
        DynamicMaterial->SetScalarParameterValue(WheelTrackAsphaltRoughnessParamName, RuntimeWheelTrackAsphaltRoughness);
        DynamicMaterial->SetScalarParameterValue(WheelTrackSnowRoughnessParamName, RuntimeWheelTrackSnowRoughness);
        DynamicMaterial->SetScalarParameterValue(RightBermRaiseParamName, RuntimeRightBermRaise);
        DynamicMaterial->SetScalarParameterValue(RepeatAccumulationDepthParamName, RuntimeRepeatAccumulationDepth);
        DynamicMaterial->SetVectorParameterValue(PressedSnowColorParamName, RuntimePressedSnowColor);
        DynamicMaterial->SetVectorParameterValue(ThinSnowUnderColorParamName, RuntimeThinSnowUnderColor);
    }

    void ApplyRuntimeLandscapeVisualProfile(ALandscapeProxy* LandscapeProxy)
    {
        if (!LandscapeProxy)
        {
            return;
        }

        LandscapeProxy->SetLandscapeMaterialScalarParameterValue(VisualClearMaskStrengthParamName, RuntimeVisualClearMaskStrength);
        LandscapeProxy->SetLandscapeMaterialScalarParameterValue(DepthMaskBoostParamName, RuntimeDepthMaskBoost);
        LandscapeProxy->SetLandscapeMaterialScalarParameterValue(ThinSnowMinVisualOpacityParamName, RuntimeThinSnowMinVisualOpacity);
        LandscapeProxy->SetLandscapeMaterialScalarParameterValue(EdgeDustingStrengthParamName, RuntimeEdgeDustingStrength);
        LandscapeProxy->SetLandscapeMaterialScalarParameterValue(WheelTrackMaskAmplifyParamName, RuntimeWheelTrackMaskAmplify);
        LandscapeProxy->SetLandscapeMaterialScalarParameterValue(WheelTrackContrastParamName, RuntimeWheelTrackContrast);
        LandscapeProxy->SetLandscapeMaterialScalarParameterValue(WheelTrackStrengthParamName, RuntimeWheelTrackStrength);
        LandscapeProxy->SetLandscapeMaterialScalarParameterValue(WheelTrackAsphaltRoughnessParamName, RuntimeWheelTrackAsphaltRoughness);
        LandscapeProxy->SetLandscapeMaterialScalarParameterValue(WheelTrackSnowRoughnessParamName, RuntimeWheelTrackSnowRoughness);
        LandscapeProxy->SetLandscapeMaterialScalarParameterValue(RightBermRaiseParamName, RuntimeRightBermRaise);
        LandscapeProxy->SetLandscapeMaterialScalarParameterValue(RepeatAccumulationDepthParamName, RuntimeRepeatAccumulationDepth);
        LandscapeProxy->SetLandscapeMaterialVectorParameterValue(PressedSnowColorParamName, RuntimePressedSnowColor);
        LandscapeProxy->SetLandscapeMaterialVectorParameterValue(ThinSnowUnderColorParamName, RuntimeThinSnowUnderColor);
    }

    void DrawTrailDebugSourceAndArea(
        UWorld* World,
        const USceneComponent* Source,
        const float PlowLengthCm,
        const float PlowWidthCm,
        const float RightBermRatio,
        const bool bSourceActive)
    {
        if (!World || !Source)
        {
            return;
        }

        const FVector SourceLocation = Source->GetComponentLocation();
        const AActor* SourceOwner = Source->GetOwner();
        const float ReferenceYaw = SourceOwner ? SourceOwner->GetActorRotation().Yaw : Source->GetComponentRotation().Yaw;
        const FRotator FlatRotation(0.0f, ReferenceYaw, 0.0f);
        const FQuat SourceRotation = FlatRotation.Quaternion();
        const FVector BoxExtent(
            FMath::Max(PlowLengthCm, 1.0f) * 0.5f,
            FMath::Max(PlowWidthCm, 1.0f) * 0.5f,
            DebugPlowBoxHeightCm * 0.5f
        );

        const FColor SourceColor = bSourceActive ? FColor::Yellow : FColor::Red;
        const FColor AreaColor = bSourceActive ? FColor::Cyan : FColor(255, 120, 0);
        DrawDebugSphere(World, SourceLocation, DebugSourceSphereRadiusCm, 12, SourceColor, false, DebugDrawLifetime, 0, 2.0f);
        DrawDebugBox(World, SourceLocation, BoxExtent, SourceRotation, AreaColor, false, DebugDrawLifetime, 0, 2.0f);

        if (RightBermRatio > KINDA_SMALL_NUMBER)
        {
            const float BermWidthCm = FMath::Max(PlowWidthCm * RightBermRatio, 1.0f);
            const FVector RightVector = FlatRotation.RotateVector(FVector::RightVector);
            const FVector BermCenter = SourceLocation + (RightVector * ((PlowWidthCm * 0.5f) + (BermWidthCm * 0.5f)));
            const FVector BermExtent(
                FMath::Max(PlowLengthCm, 1.0f) * 0.5f,
                BermWidthCm * 0.5f,
                DebugPlowBoxHeightCm * 0.5f
            );
            const FColor BermColor = bSourceActive ? FColor::Green : FColor(120, 255, 120);
            DrawDebugBox(World, BermCenter, BermExtent, SourceRotation, BermColor, false, DebugDrawLifetime, 0, 2.0f);
        }
    }
}

USnowRuntimeTrailBridgeComponent::USnowRuntimeTrailBridgeComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
}

void USnowRuntimeTrailBridgeComponent::BeginPlay()
{
    Super::BeginPlay();

    RepeatAccumulationCells.Reset();
    RepeatAccumulationCellLastTouchTimes.Reset();

    // Preserve per-map tuning and only migrate the old "always active" legacy threshold.
    if (bUseSourceHeightGate && FMath::IsNearlyEqual(SourceActiveMaxRelativeZ, LegacyAlwaysActiveMaxRelativeZ, KINDA_SMALL_NUMBER))
    {
        SourceActiveMaxRelativeZ = DefaultPlowActiveMaxRelativeZ;
    }

    if (USnowStateRuntimeSettings* Settings = GetMutableDefault<USnowStateRuntimeSettings>())
    {
        Settings->bEnablePersistentSnowStateV1 = true;
    }

    EnsureRvtStampComponent();
    CacheRuntimeReceiverMaterialInstances();
    ApplyRuntimeReceiverHeightAmplitude(0.0f);
}

void USnowRuntimeTrailBridgeComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    MaybeStamp(DeltaTime);
}

bool USnowRuntimeTrailBridgeComponent::RecordTrailStampNow()
{
    if (!bEnableRuntimeTrail)
    {
        return false;
    }

    USceneComponent* Source = ResolveSourceComponent();
    if (!Source)
    {
        ApplyRuntimeReceiverHeightAmplitude(0.0f);
        return false;
    }
    const AActor* SourceOwner = Source->GetOwner();
    const FVector2D EffectivePlowFootprintCm = ResolveEffectivePlowFootprintCm(Source, SourceOwner, PersistentPlowLengthCm, PersistentPlowWidthCm);
    const float SourceEngagementStrength = ResolveSourceEngagementStrength(Source);
    const bool bSourceActive = SourceEngagementStrength >= MinStampEngagementToWrite;
    ApplyRuntimeReceiverHeightAmplitude(SourceEngagementStrength);
    DrawTrailDebugSourceAndArea(GetWorld(), Source, EffectivePlowFootprintCm.X, EffectivePlowFootprintCm.Y, RightBermContinuationRatio, bSourceActive);
    if (!bSourceActive)
    {
        return false;
    }

    const FVector Location = Source->GetComponentLocation();
    // Keep runtime trail dense enough even if an overly large spacing value was serialized in the level.
    const float EffectiveStampSpacingCm = FMath::Clamp(StampSpacingCm, 5.0f, 40.0f);
    const float Distance = bHasLastLocation ? FVector::DistXY(Location, LastStampLocation) : EffectiveStampSpacingCm * 2.0f;
    if (Distance < EffectiveStampSpacingCm)
    {
        return false;
    }

    if (bMarkPersistentSnowState)
    {
        const ESnowReceiverSurfaceFamily EffectiveSurfaceFamily = ResolveActiveSurfaceFamily(Source);
        USnowStateBlueprintLibrary::MarkPersistentPlowWriter(
            Source,
            EffectivePlowFootprintCm.X,
            EffectivePlowFootprintCm.Y,
            EffectiveSurfaceFamily,
            false
        );
    }
    AddRvtStampInstance(Location, Source->GetComponentRotation(), SourceOwner, SourceEngagementStrength);

    LastStampLocation = Location;
    bHasLastLocation = true;
    ++StampCount;
    return true;
}

int32 USnowRuntimeTrailBridgeComponent::GetStampCount() const
{
    return StampCount;
}

int32 USnowRuntimeTrailBridgeComponent::GetVisualStampCount() const
{
    return GetTotalVisualStampCount();
}

void USnowRuntimeTrailBridgeComponent::MaybeStamp(const float DeltaTime)
{
    if (!bEnableRuntimeTrail)
    {
        return;
    }

    RecordTrailStampNow();
}

ESnowReceiverSurfaceFamily USnowRuntimeTrailBridgeComponent::ResolveActiveSurfaceFamily(const USceneComponent* Source) const
{
    if (!Source)
    {
        return PersistentSurfaceFamily;
    }

    UWorld* World = GetWorld();
    if (!World)
    {
        return PersistentSurfaceFamily;
    }

    const FVector SourceLocation = Source->GetComponentLocation();
    const FVector TraceStart = SourceLocation + FVector(0.0f, 0.0f, 250.0f);
    const FVector TraceEnd = SourceLocation - FVector(0.0f, 0.0f, 1200.0f);

    FHitResult Hit;
    FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(SnowTrailResolveSurfaceFamily), false, GetOwner());
    if (const AActor* SourceOwner = Source->GetOwner())
    {
        QueryParams.AddIgnoredActor(SourceOwner);
    }

    bool bHit = World->LineTraceSingleByChannel(Hit, TraceStart, TraceEnd, ECC_Visibility, QueryParams);
    if (!bHit)
    {
        bHit = World->LineTraceSingleByChannel(Hit, TraceStart, TraceEnd, ECC_WorldStatic, QueryParams);
    }

    if (!bHit)
    {
        FVector ProjectedLocation = SourceLocation;
        ESnowReceiverSurfaceFamily ProjectedSurfaceFamily = PersistentSurfaceFamily;
        if (TryProjectToNearbySnowReceiverSurface(World, SourceLocation, GetOwner(), ProjectedLocation, &ProjectedSurfaceFamily))
        {
            return ProjectedSurfaceFamily;
        }

        return PersistentSurfaceFamily;
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

    return PersistentSurfaceFamily;
}

float USnowRuntimeTrailBridgeComponent::ResolveSourceEngagementStrength(const USceneComponent* Source) const
{
    if (!Source)
    {
        return 0.0f;
    }

    const AActor* SourceOwner = Source->GetOwner();

    bool bClearingEnabled = true;
    bool bFoundClearingEnabledFlag = false;
    auto ConsumeClearingEnabledFlag = [&](const UObject* Object)
    {
        bool bObjectClearingEnabled = true;
        if (TryGetBoolPropertyValue(Object, PlowClearingEnabledPropertyName, bObjectClearingEnabled))
        {
            bFoundClearingEnabledFlag = true;
            bClearingEnabled = bClearingEnabled && bObjectClearingEnabled;
        }
    };

    // KamazBP drives the live plow state on the owner actor and mirrors it to the brush component.
    // Prefer owner-level state so snow follows the actual animated plow even if the component mirror lags.
    ConsumeClearingEnabledFlag(SourceOwner);
    ConsumeClearingEnabledFlag(Source);
    if (bFoundClearingEnabledFlag && !bClearingEnabled)
    {
        return 0.0f;
    }

    float EngagementStrength = 1.0f;
    const float MaxLiftHeight = FMath::Max(PlowLiftHeightForNoEffect, 0.01f);
    static const FName TargetPlowHeightPropertyName(TEXT("TargetPlowHeight"));

    // KamazBP and BP_PlowBrush_Component can briefly disagree while the plow animation settles.
    // Prefer the most-engaged signal we can see so lowering the blade starts clearing reliably.
    float BestNormalizedLift = 1.0f;
    bool bFoundLiftSignal = false;
    auto ConsumeLiftSignal = [&](const UObject* Object, const FName PropertyName)
    {
        float LiftHeight = 0.0f;
        if (!TryGetFloatPropertyValue(Object, PropertyName, LiftHeight))
        {
            return;
        }

        bFoundLiftSignal = true;
        const float NormalizedLift = FMath::Clamp(LiftHeight / MaxLiftHeight, 0.0f, 1.0f);
        BestNormalizedLift = FMath::Min(BestNormalizedLift, NormalizedLift);
    };

    ConsumeLiftSignal(SourceOwner, TargetPlowHeightPropertyName);
    ConsumeLiftSignal(SourceOwner, PlowLiftHeightPropertyName);
    ConsumeLiftSignal(Source, TargetPlowHeightPropertyName);
    ConsumeLiftSignal(Source, PlowLiftHeightPropertyName);

    const bool bSourceHeightActive = IsSourceHeightActive(Source, bUseSourceHeightGate, SourceActiveMaxRelativeZ);

    if (bFoundLiftSignal)
    {
        // Keep the engagement binary to avoid depth flutter, but derive it from the lowest
        // currently observed plow height across owner/component signals.
        EngagementStrength = BestNormalizedLift < 0.5f ? 1.0f : 0.0f;
    }
    else
    {
        EngagementStrength = bSourceHeightActive ? 1.0f : 0.0f;
    }

    return FMath::Clamp(EngagementStrength, 0.0f, 1.0f);
}

int32 USnowRuntimeTrailBridgeComponent::ResolveEngagementBandIndex(const float SourceEngagementStrength) const
{
    if (SourceEngagementStrength >= 0.85f)
    {
        return 2;
    }

    if (SourceEngagementStrength >= 0.45f)
    {
        return 1;
    }

    return 0;
}

float USnowRuntimeTrailBridgeComponent::ResolveEngagementBandStrength(const int32 EngagementBandIndex) const
{
    const int32 ClampedIndex = FMath::Clamp(EngagementBandIndex, 0, EngagementBandCount - 1);
    return EngagementBandStrengths[ClampedIndex];
}

int32 USnowRuntimeTrailBridgeComponent::ResolveTierBandFlatIndex(const int32 TierIndex, const int32 EngagementBandIndex) const
{
    return (FMath::Max(TierIndex, 0) * EngagementBandCount) + FMath::Clamp(EngagementBandIndex, 0, EngagementBandCount - 1);
}

USceneComponent* USnowRuntimeTrailBridgeComponent::ResolveSourceComponent()
{
    AActor* Owner = GetOwner();
    if (!Owner)
    {
        return nullptr;
    }

    UWorld* World = GetWorld();
    USceneComponent* NonPreferredOverride = nullptr;
    if (SourceComponentOverride && IsValid(SourceComponentOverride))
    {
        if (USceneComponent* OverrideSceneComponent = Cast<USceneComponent>(SourceComponentOverride))
        {
            if (AActor* OverrideOwner = OverrideSceneComponent->GetOwner())
            {
                if (USceneComponent* BetterOwnerPlowComponent = FindPlowComponentOnActor(OverrideOwner))
                {
                    const int32 OverrideScore = GetPlowSourcePreferenceScore(OverrideSceneComponent);
                    const int32 BetterScore = GetPlowSourcePreferenceScore(BetterOwnerPlowComponent);
                    if (BetterScore > OverrideScore)
                    {
                        SourceComponentOverride = BetterOwnerPlowComponent;
                        return BetterOwnerPlowComponent;
                    }
                }
            }

            if (IsPreferredPlowSource(OverrideSceneComponent))
            {
                return OverrideSceneComponent;
            }

            if (ComponentLooksLikePlowSource(OverrideSceneComponent))
            {
                NonPreferredOverride = OverrideSceneComponent;
            }
        }
    }

    if (USceneComponent* PlayerControlledSource = FindPlowComponentOnPossessedPawn(World))
    {
        SourceComponentOverride = PlayerControlledSource;
        return PlayerControlledSource;
    }

    if (USceneComponent* OwnerPlowComponent = FindPlowComponentOnActor(Owner))
    {
        SourceComponentOverride = OwnerPlowComponent;
        return OwnerPlowComponent;
    }

    if (World)
    {
        // Prefer Kamaz-like actors, then fallback to any actor exposing PlowBrush-like component names.
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            AActor* CandidateActor = *It;
            if (!ActorLooksLikeKamaz(CandidateActor))
            {
                continue;
            }

            if (USceneComponent* CandidateSource = FindPlowComponentOnActor(CandidateActor))
            {
                SourceComponentOverride = CandidateSource;
                return CandidateSource;
            }
        }

        for (TActorIterator<AActor> It(World); It; ++It)
        {
            if (USceneComponent* CandidateSource = FindPlowComponentOnActor(*It))
            {
                SourceComponentOverride = CandidateSource;
                return CandidateSource;
            }
        }
    }

    if (NonPreferredOverride && IsValid(NonPreferredOverride))
    {
        SourceComponentOverride = NonPreferredOverride;
        return NonPreferredOverride;
    }

    SourceComponentOverride = nullptr;
    return Cast<USceneComponent>(Owner->GetComponentByClass(USceneComponent::StaticClass()));
}

void USnowRuntimeTrailBridgeComponent::CacheRuntimeReceiverMaterialInstances()
{
    RuntimeReceiverDynamicMaterials.Reset();
    RuntimeLandscapeReceivers.Reset();
    bReceiverMaterialCacheInitialized = true;

    if (!bEnableRuntimeReceiverHeightControl)
    {
        return;
    }

    UWorld* World = GetWorld();
    if (!World)
    {
        return;
    }

    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (!Actor)
        {
            continue;
        }

        if (ALandscapeProxy* LandscapeProxy = Cast<ALandscapeProxy>(Actor))
        {
            if (IsHeightReceiverMaterial(LandscapeProxy->GetLandscapeMaterial()))
            {
                RuntimeLandscapeReceivers.Add(LandscapeProxy);
                ApplyRuntimeLandscapeVisualProfile(LandscapeProxy);
            }
        }

        TInlineComponentArray<UMeshComponent*> MeshComponents;
        Actor->GetComponents(MeshComponents);
        for (UMeshComponent* MeshComponent : MeshComponents)
        {
            if (!MeshComponent)
            {
                continue;
            }

            const int32 MaterialCount = MeshComponent->GetNumMaterials();
            for (int32 MaterialIndex = 0; MaterialIndex < MaterialCount; ++MaterialIndex)
            {
                UMaterialInterface* Material = MeshComponent->GetMaterial(MaterialIndex);
                if (!IsHeightReceiverMaterial(Material))
                {
                    continue;
                }

                UMaterialInstanceDynamic* DynamicMaterial = MeshComponent->CreateAndSetMaterialInstanceDynamic(MaterialIndex);
                if (DynamicMaterial)
                {
                    if (ShouldApplyLegacyRuntimeReceiverOverrides(MeshComponent))
                    {
                        ApplyRuntimeReceiverVisualProfile(DynamicMaterial);
                    }
                    RuntimeReceiverDynamicMaterials.Add(DynamicMaterial);
                }
            }
        }
    }
}

void USnowRuntimeTrailBridgeComponent::ApplyRuntimeReceiverHeightAmplitude(const float SourceEngagementStrength)
{
    if (!bEnableRuntimeReceiverHeightControl)
    {
        return;
    }

    if (!bReceiverMaterialCacheInitialized)
    {
        CacheRuntimeReceiverMaterialInstances();
    }

    const float EngagementAlpha = FMath::Clamp(SourceEngagementStrength, 0.0f, 1.0f);
    const float TargetHeightAmplitude = FMath::Lerp(
        RuntimeHeightAmplitudeWhenInactive,
        RuntimeHeightAmplitudeWhenActive,
        EngagementAlpha
    );
    if (bLastAppliedRuntimeHeightValid && FMath::IsNearlyEqual(TargetHeightAmplitude, LastAppliedRuntimeHeightAmplitude, KINDA_SMALL_NUMBER))
    {
        return;
    }

    for (UMaterialInstanceDynamic* DynamicMaterial : RuntimeReceiverDynamicMaterials)
    {
        if (DynamicMaterial)
        {
            if (ShouldApplyLegacyRuntimeReceiverOverrides(DynamicMaterial))
            {
                ApplyRuntimeReceiverVisualProfile(DynamicMaterial);
            }
            const float ReceiverHeightScale = ResolveRuntimeHeightScaleForReceiver(DynamicMaterial);
            if (FMath::IsNearlyZero(ReceiverHeightScale, KINDA_SMALL_NUMBER))
            {
                continue;
            }
            const float PerReceiverTargetHeightAmplitude = TargetHeightAmplitude * ReceiverHeightScale;
            DynamicMaterial->SetScalarParameterValue(RuntimeHeightAmplitudeParameterName, PerReceiverTargetHeightAmplitude);
        }
    }

    for (const TWeakObjectPtr<ALandscapeProxy>& LandscapeProxyPtr : RuntimeLandscapeReceivers)
    {
        if (ALandscapeProxy* LandscapeProxy = LandscapeProxyPtr.Get())
        {
            ApplyRuntimeLandscapeVisualProfile(LandscapeProxy);
            LandscapeProxy->SetLandscapeMaterialScalarParameterValue(
                RuntimeHeightAmplitudeParameterName,
                TargetHeightAmplitude * LandscapeRuntimeHeightScale
            );
        }
    }

    LastAppliedRuntimeHeightAmplitude = TargetHeightAmplitude;
    bLastAppliedRuntimeHeightValid = true;
}

void USnowRuntimeTrailBridgeComponent::EnsureRvtStampComponent()
{
    if (!bEnableRvtVisualStamp)
    {
        return;
    }

    AActor* Owner = GetOwner();
    if (!Owner)
    {
        return;
    }

    if (!StampMeshAsset)
    {
        StampMeshAsset = LoadObject<UStaticMesh>(nullptr, DefaultStampMeshPath);
    }
    if (!StampMaterial)
    {
        StampMaterial = LoadObject<UMaterialInterface>(nullptr, DefaultStampMaterialPath);
    }
    if (!TargetRvt)
    {
        TargetRvt = LoadObject<URuntimeVirtualTexture>(nullptr, DefaultTargetRvtPath);
    }

    const int32 TierCount = bEnableRepeatClearingAccumulation
        ? FMath::Clamp(RepeatAccumulationMaxPasses, 1, 3)
        : 1;

    const int32 FlattenedCount = TierCount * EngagementBandCount;
    RvtStampTierInstances.SetNum(FlattenedCount);
    RvtStampTierMaterials.SetNum(FlattenedCount);
    RvtBermTierInstances.SetNum(FlattenedCount);
    RvtBermTierMaterials.SetNum(FlattenedCount);

    for (int32 TierIndex = 0; TierIndex < TierCount; ++TierIndex)
    {
        for (int32 EngagementBandIndex = 0; EngagementBandIndex < EngagementBandCount; ++EngagementBandIndex)
        {
            const int32 FlatIndex = ResolveTierBandFlatIndex(TierIndex, EngagementBandIndex);
            TObjectPtr<UInstancedStaticMeshComponent>& TierComponent = RvtStampTierInstances[FlatIndex];
            if (!TierComponent && TierIndex == 0 && EngagementBandIndex == (EngagementBandCount - 1) && RvtStampInstances)
            {
                TierComponent = RvtStampInstances;
            }
            if (!TierComponent)
            {
                const FName ComponentName(*FString::Printf(TEXT("RVTTrailStampInstances_Tier%d_Band%d"), TierIndex, EngagementBandIndex));
                TierComponent = NewObject<UInstancedStaticMeshComponent>(Owner, ComponentName);
                if (!TierComponent)
                {
                    continue;
                }

                Owner->AddInstanceComponent(TierComponent);
                if (USceneComponent* RootComp = Owner->GetRootComponent())
                {
                    TierComponent->SetupAttachment(RootComp);
                }
                TierComponent->RegisterComponent();
            }

            if (StampMeshAsset)
            {
                TierComponent->SetStaticMesh(StampMeshAsset);
            }

            if (StampMaterial)
            {
                StampMaterial->CheckMaterialUsage_Concurrent(MATUSAGE_InstancedStaticMeshes);

                TObjectPtr<UMaterialInstanceDynamic>& TierMaterial = RvtStampTierMaterials[FlatIndex];
                if (!TierMaterial)
                {
                    TierMaterial = UMaterialInstanceDynamic::Create(StampMaterial, this);
                }

                if (TierMaterial)
                {
                    const float EngagementBandStrength = ResolveEngagementBandStrength(EngagementBandIndex);
                    TierMaterial->SetScalarParameterValue(TEXT("ClearStrength"), ResolveClearStrengthForTier(TierIndex) * EngagementBandStrength);
                    TierMaterial->SetScalarParameterValue(TEXT("RepeatDepthStrength"), ResolveRepeatDepthStrengthForTier(TierIndex) * EngagementBandStrength);
                    TierMaterial->SetScalarParameterValue(TEXT("BermOnly"), 0.0f);
                    TierMaterial->SetScalarParameterValue(TEXT("BermStrength"), 0.0f);
                    TierComponent->SetMaterial(0, TierMaterial);
                }
                else
                {
                    TierComponent->SetMaterial(0, StampMaterial);
                }
            }

            TierComponent->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            TierComponent->SetGenerateOverlapEvents(false);
            TierComponent->SetCastShadow(false);
            TierComponent->SetRenderInMainPass(false);
            TierComponent->SetReceivesDecals(false);
            TierComponent->bUseAsOccluder = false;
            TierComponent->SetMobility(EComponentMobility::Movable);
            TierComponent->NumCustomDataFloats = 0;
            TierComponent->RuntimeVirtualTextures.Reset();
            if (TargetRvt)
            {
                TierComponent->RuntimeVirtualTextures.Add(TargetRvt);
            }
            TierComponent->VirtualTextureRenderPassType = ERuntimeVirtualTextureMainPassType::Never;
            TierComponent->MarkRenderStateDirty();

            TObjectPtr<UInstancedStaticMeshComponent>& BermTierComponent = RvtBermTierInstances[FlatIndex];
            if (!BermTierComponent)
            {
                const FName ComponentName(*FString::Printf(TEXT("RVTTrailBermInstances_Tier%d_Band%d"), TierIndex, EngagementBandIndex));
                BermTierComponent = NewObject<UInstancedStaticMeshComponent>(Owner, ComponentName);
                if (!BermTierComponent)
                {
                    continue;
                }

                Owner->AddInstanceComponent(BermTierComponent);
                if (USceneComponent* RootComp = Owner->GetRootComponent())
                {
                    BermTierComponent->SetupAttachment(RootComp);
                }
                BermTierComponent->RegisterComponent();
            }

            if (StampMeshAsset)
            {
                BermTierComponent->SetStaticMesh(StampMeshAsset);
            }

            if (StampMaterial)
            {
                StampMaterial->CheckMaterialUsage_Concurrent(MATUSAGE_InstancedStaticMeshes);

                TObjectPtr<UMaterialInstanceDynamic>& BermTierMaterial = RvtBermTierMaterials[FlatIndex];
                if (!BermTierMaterial)
                {
                    BermTierMaterial = UMaterialInstanceDynamic::Create(StampMaterial, this);
                }

                if (BermTierMaterial)
                {
                    const float EngagementBandStrength = ResolveEngagementBandStrength(EngagementBandIndex);
                    BermTierMaterial->SetScalarParameterValue(TEXT("ClearStrength"), 0.0f);
                    BermTierMaterial->SetScalarParameterValue(TEXT("RepeatDepthStrength"), 0.0f);
                    BermTierMaterial->SetScalarParameterValue(TEXT("BermOnly"), 1.0f);
                    BermTierMaterial->SetScalarParameterValue(TEXT("BermStrength"), EngagementBandStrength);
                    BermTierComponent->SetMaterial(0, BermTierMaterial);
                }
                else
                {
                    BermTierComponent->SetMaterial(0, StampMaterial);
                }
            }

            BermTierComponent->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            BermTierComponent->SetGenerateOverlapEvents(false);
            BermTierComponent->SetCastShadow(false);
            BermTierComponent->SetRenderInMainPass(false);
            BermTierComponent->SetReceivesDecals(false);
            BermTierComponent->bUseAsOccluder = false;
            BermTierComponent->SetMobility(EComponentMobility::Movable);
            BermTierComponent->NumCustomDataFloats = 0;
            BermTierComponent->RuntimeVirtualTextures.Reset();
            if (TargetRvt)
            {
                BermTierComponent->RuntimeVirtualTextures.Add(TargetRvt);
            }
            BermTierComponent->VirtualTextureRenderPassType = ERuntimeVirtualTextureMainPassType::Never;
            BermTierComponent->MarkRenderStateDirty();
        }
    }

    RvtStampInstances = RvtStampTierInstances.Num() > 0
        ? RvtStampTierInstances[ResolveTierBandFlatIndex(0, EngagementBandCount - 1)]
        : nullptr;
}

void USnowRuntimeTrailBridgeComponent::AddRvtStampInstance(const FVector& WorldLocation, const FRotator& WorldRotation, const AActor* SourceOwner, const float SourceEngagementStrength)
{
    if (!bEnableRvtVisualStamp)
    {
        return;
    }

    EnsureRvtStampComponent();
    if (RvtStampTierInstances.Num() == 0)
    {
        return;
    }

    const int32 TierIndex = ResolveRepeatTierForLocation(WorldLocation);
    const int32 EngagementBandIndex = ResolveEngagementBandIndex(SourceEngagementStrength);
    const int32 FlatIndex = ResolveTierBandFlatIndex(TierIndex, EngagementBandIndex);
    UInstancedStaticMeshComponent* TierComponent = RvtStampTierInstances.IsValidIndex(FlatIndex)
        ? RvtStampTierInstances[FlatIndex]
        : RvtStampInstances;
    UInstancedStaticMeshComponent* BermTierComponent = RvtBermTierInstances.IsValidIndex(FlatIndex)
        ? RvtBermTierInstances[FlatIndex]
        : nullptr;
    if (!TierComponent || !TierComponent->GetStaticMesh())
    {
        return;
    }

    if (MaxVisualStamps > 0 && GetTotalVisualStampCount() >= MaxVisualStamps)
    {
        for (UInstancedStaticMeshComponent* ExistingComponent : RvtStampTierInstances)
        {
            if (ExistingComponent && ExistingComponent->GetInstanceCount() > 0)
            {
                ExistingComponent->RemoveInstance(0);
                break;
            }
        }
        for (UInstancedStaticMeshComponent* ExistingBermComponent : RvtBermTierInstances)
        {
            if (ExistingBermComponent && ExistingBermComponent->GetInstanceCount() > 0)
            {
                ExistingBermComponent->RemoveInstance(0);
                break;
            }
        }
    }

    const FVector2D EffectivePlowFootprintCm = ResolveEffectivePlowFootprintCm(nullptr, SourceOwner, PersistentPlowLengthCm, PersistentPlowWidthCm);
    const float EffectivePlowLengthCm = EffectivePlowFootprintCm.X;
    const float EffectivePlowWidthCm = EffectivePlowFootprintCm.Y;
    const float ReferenceYaw = SourceOwner ? SourceOwner->GetActorRotation().Yaw : WorldRotation.Yaw;
    const FRotator FlatWorldRotation(0.0f, ReferenceYaw, 0.0f);
    const FVector RightVector = FlatWorldRotation.RotateVector(FVector::RightVector);
    const float BermWidthCm = FMath::Max(EffectivePlowWidthCm * RightBermContinuationRatio, 0.0f);

    const FVector WorldOffset(0.0f, 0.0f, 1.0f + (RepeatTierZOffsetCm * TierIndex));
    FVector ClearStampLocation = WorldLocation + WorldOffset;
    FVector BermStampLocation = WorldLocation + WorldOffset + (RightVector * ((EffectivePlowWidthCm * 0.5f) + (BermWidthCm * 0.5f)));
    if (UWorld* World = GetWorld())
    {
        const FVector TraceStart = WorldLocation + FVector(0.0f, 0.0f, 300.0f);
        const FVector TraceEnd = WorldLocation - FVector(0.0f, 0.0f, 900.0f);

        FHitResult Hit;
        FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(SnowTrailStampSurfaceTrace), false, GetOwner());
        if (SourceOwner)
        {
            QueryParams.AddIgnoredActor(SourceOwner);
        }

        bool bHit = World->LineTraceSingleByChannel(Hit, TraceStart, TraceEnd, ECC_Visibility, QueryParams);
        if (!bHit)
        {
            bHit = World->LineTraceSingleByChannel(Hit, TraceStart, TraceEnd, ECC_WorldStatic, QueryParams);
        }

        if (bHit)
        {
            ClearStampLocation = Hit.ImpactPoint + WorldOffset;
            BermStampLocation = Hit.ImpactPoint + WorldOffset + (RightVector * ((EffectivePlowWidthCm * 0.5f) + (BermWidthCm * 0.5f)));
        }
        else
        {
            FVector ProjectedLocation = WorldLocation;
            if (TryProjectToNearbySnowReceiverSurface(World, WorldLocation, GetOwner(), ProjectedLocation))
            {
                ClearStampLocation = ProjectedLocation + WorldOffset;
                BermStampLocation = ProjectedLocation + WorldOffset + (RightVector * ((EffectivePlowWidthCm * 0.5f) + (BermWidthCm * 0.5f)));
            }
        }
    }

    const FVector ClearInstanceScale(
        FMath::Max(EffectivePlowLengthCm, 1.0f) / 100.0f,
        FMath::Max(EffectivePlowWidthCm, 1.0f) / 100.0f,
        1.0f
    );
    const FTransform ClearInstanceTransform(FlatWorldRotation, ClearStampLocation, ClearInstanceScale);
    TierComponent->AddInstance(ClearInstanceTransform, true);

    if (BermTierComponent && BermTierComponent->GetStaticMesh() && BermWidthCm > KINDA_SMALL_NUMBER)
    {
        const FVector BermInstanceScale(
            FMath::Max(EffectivePlowLengthCm, 1.0f) / 100.0f,
            FMath::Max(BermWidthCm, 1.0f) / 100.0f,
            1.0f
        );
        const FTransform BermInstanceTransform(FlatWorldRotation, BermStampLocation, BermInstanceScale);
        BermTierComponent->AddInstance(BermInstanceTransform, true);
    }
}

float USnowRuntimeTrailBridgeComponent::ResolveClearStrengthForTier(const int32 TierIndex) const
{
    return 1.0f;
}

float USnowRuntimeTrailBridgeComponent::ResolveRepeatDepthStrengthForTier(const int32 TierIndex) const
{
    const float UnclampedStrength = FirstPassClearStrength + (RepeatPassClearStrengthStep * TierIndex);
    return FMath::Clamp(UnclampedStrength, 0.0f, MaxAccumulatedClearStrength);
}

int32 USnowRuntimeTrailBridgeComponent::ResolveRepeatTierForLocation(const FVector& WorldLocation)
{
    if (!bEnableRepeatClearingAccumulation)
    {
        return 0;
    }

    const float CellSizeCm = FMath::Max(RepeatAccumulationCellSizeCm, 10.0f);
    const FIntPoint CellId(
        FMath::FloorToInt(WorldLocation.X / CellSizeCm),
        FMath::FloorToInt(WorldLocation.Y / CellSizeCm)
    );

    const double NowSeconds = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
    const int32 MaxPasses = FMath::Clamp(RepeatAccumulationMaxPasses, 1, 3);
    const int32 ExistingPassCount = RepeatAccumulationCells.FindRef(CellId);
    const double LastTouchSeconds = RepeatAccumulationCellLastTouchTimes.FindRef(CellId);

    int32 EffectivePassCount = ExistingPassCount;
    if (EffectivePassCount <= 0)
    {
        EffectivePassCount = 1;
    }
    else if ((NowSeconds - LastTouchSeconds) >= RepeatAccumulationRearmSeconds)
    {
        EffectivePassCount = FMath::Min(ExistingPassCount + 1, MaxPasses);
    }

    RepeatAccumulationCells.Add(CellId, EffectivePassCount);
    RepeatAccumulationCellLastTouchTimes.Add(CellId, NowSeconds);
    return FMath::Clamp(EffectivePassCount - 1, 0, MaxPasses - 1);
}

int32 USnowRuntimeTrailBridgeComponent::GetTotalVisualStampCount() const
{
    int32 TotalCount = 0;
    for (const UInstancedStaticMeshComponent* TierComponent : RvtStampTierInstances)
    {
        if (TierComponent)
        {
            TotalCount += TierComponent->GetInstanceCount();
        }
    }
    for (const UInstancedStaticMeshComponent* BermTierComponent : RvtBermTierInstances)
    {
        if (BermTierComponent)
        {
            TotalCount += BermTierComponent->GetInstanceCount();
        }
    }

    if (TotalCount == 0 && RvtStampInstances)
    {
        TotalCount = RvtStampInstances->GetInstanceCount();
    }

    return TotalCount;
}
