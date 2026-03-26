#include "Snow/RuntimeV1/SnowStateManagerV1.h"

#include "Engine/TextureRenderTarget2D.h"
#include "Kismet/KismetRenderingLibrary.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

namespace
{
    constexpr TCHAR PreviousStateTextureParam[] = TEXT("PreviousStateTexture");
    constexpr TCHAR StampCenterUParam[] = TEXT("StampCenterU");
    constexpr TCHAR StampCenterVParam[] = TEXT("StampCenterV");
    constexpr TCHAR StampRadiusUvParam[] = TEXT("StampRadiusUV");
    constexpr TCHAR StampDeltaRParam[] = TEXT("StampDeltaR");
    constexpr TCHAR StampDeltaGParam[] = TEXT("StampDeltaG");
    constexpr TCHAR StampDeltaBParam[] = TEXT("StampDeltaB");
    constexpr TCHAR StampDeltaAParam[] = TEXT("StampDeltaA");
    constexpr TCHAR StampFalloffPowerParam[] = TEXT("StampFalloffPower");
}

ASnowStateManagerV1::ASnowStateManagerV1()
{
    PrimaryActorTick.bCanEverTick = false;
}

void ASnowStateManagerV1::BeginPlay()
{
    Super::BeginPlay();

    if (WorldMappingOrigin.IsNearlyZero())
    {
        WorldMappingOrigin = GetActorLocation();
    }
}

void ASnowStateManagerV1::CenterMappingOnWorldLocation(const FVector& WorldLocation)
{
    WorldMappingOrigin.X = WorldLocation.X;
    WorldMappingOrigin.Y = WorldLocation.Y;
}

void ASnowStateManagerV1::ResetStateRenderTargets(const FLinearColor& ClearColor)
{
    if (!StateRenderTargetA || !StateRenderTargetB)
    {
        return;
    }

    UKismetRenderingLibrary::ClearRenderTarget2D(this, StateRenderTargetA, ClearColor);
    UKismetRenderingLibrary::ClearRenderTarget2D(this, StateRenderTargetB, ClearColor);
    bStateAIsAuthoritative = true;
    PendingWheelStamps.Reset();
    PendingPlowStamps.Reset();
}

void ASnowStateManagerV1::QueueWheelStamp(const FSnowStateStampRequestV1& StampRequest)
{
    PendingWheelStamps.Add(StampRequest);
}

void ASnowStateManagerV1::QueuePlowStamp(const FSnowStateStampRequestV1& StampRequest)
{
    PendingPlowStamps.Add(StampRequest);
}

bool ASnowStateManagerV1::FlushQueuedStateWrites()
{
    bool bAnyWrites = false;
    bAnyWrites |= ApplyQueuedStamps(PendingWheelStamps, WheelWriteMaterial);
    bAnyWrites |= ApplyQueuedStamps(PendingPlowStamps, PlowWriteMaterial);
    PendingWheelStamps.Reset();
    PendingPlowStamps.Reset();
    return bAnyWrites;
}

UTextureRenderTarget2D* ASnowStateManagerV1::GetAuthoritativeStateRenderTarget() const
{
    return GetReadRenderTarget();
}

UTextureRenderTarget2D* ASnowStateManagerV1::GetCurrentReadRenderTarget() const
{
    return GetReadRenderTarget();
}

UTextureRenderTarget2D* ASnowStateManagerV1::GetCurrentWriteRenderTarget() const
{
    return GetWriteRenderTarget();
}

int32 ASnowStateManagerV1::GetPendingWheelStampCount() const
{
    return PendingWheelStamps.Num();
}

int32 ASnowStateManagerV1::GetPendingPlowStampCount() const
{
    return PendingPlowStamps.Num();
}

bool ASnowStateManagerV1::ApplyQueuedStamps(const TArray<FSnowStateStampRequestV1>& StampRequests, UMaterialInterface* BaseMaterial)
{
    bool bAnyWrites = false;
    for (const FSnowStateStampRequestV1& StampRequest : StampRequests)
    {
        bAnyWrites |= ApplySingleStamp(StampRequest, BaseMaterial);
    }
    return bAnyWrites;
}

bool ASnowStateManagerV1::ApplySingleStamp(const FSnowStateStampRequestV1& StampRequest, UMaterialInterface* BaseMaterial)
{
    UTextureRenderTarget2D* ReadTarget = GetReadRenderTarget();
    UTextureRenderTarget2D* WriteTarget = GetWriteRenderTarget();
    if (!ReadTarget || !WriteTarget || !BaseMaterial)
    {
        return false;
    }

    UMaterialInstanceDynamic* WriteMID = GetOrCreateWriteMaterialInstance(BaseMaterial);
    if (!WriteMID)
    {
        return false;
    }

    WriteMID->SetTextureParameterValue(PreviousStateTextureParam, ReadTarget);
    const FVector2D StampUv = ConvertWorldLocationToUv(StampRequest.WorldLocation);
    const FLinearColor ChannelDelta = BuildChannelDelta(StampRequest);
    WriteMID->SetScalarParameterValue(StampCenterUParam, StampUv.X);
    WriteMID->SetScalarParameterValue(StampCenterVParam, StampUv.Y);
    WriteMID->SetScalarParameterValue(StampRadiusUvParam, ConvertRadiusToUv(StampRequest.RadiusCm));
    WriteMID->SetScalarParameterValue(StampDeltaRParam, ChannelDelta.R);
    WriteMID->SetScalarParameterValue(StampDeltaGParam, ChannelDelta.G);
    WriteMID->SetScalarParameterValue(StampDeltaBParam, ChannelDelta.B);
    WriteMID->SetScalarParameterValue(StampDeltaAParam, ChannelDelta.A);
    WriteMID->SetScalarParameterValue(StampFalloffPowerParam, FMath::Max(0.01f, StampRequest.FalloffPower));

    UKismetRenderingLibrary::DrawMaterialToRenderTarget(this, WriteTarget, WriteMID);
    SwapActiveRenderTarget();
    return true;
}

UTextureRenderTarget2D* ASnowStateManagerV1::GetReadRenderTarget() const
{
    return bStateAIsAuthoritative ? StateRenderTargetA : StateRenderTargetB;
}

UTextureRenderTarget2D* ASnowStateManagerV1::GetWriteRenderTarget() const
{
    return bStateAIsAuthoritative ? StateRenderTargetB : StateRenderTargetA;
}

void ASnowStateManagerV1::SwapActiveRenderTarget()
{
    bStateAIsAuthoritative = !bStateAIsAuthoritative;
}

FVector2D ASnowStateManagerV1::ConvertWorldLocationToUv(const FVector& WorldLocation) const
{
    const float ExtentX = FMath::Max(WorldMappingExtentCm.X, 1.0f);
    const float ExtentY = FMath::Max(WorldMappingExtentCm.Y, 1.0f);
    const float U = ((WorldLocation.X - WorldMappingOrigin.X) / (ExtentX * 2.0f)) + 0.5f;
    const float V = ((WorldLocation.Y - WorldMappingOrigin.Y) / (ExtentY * 2.0f)) + 0.5f;
    return FVector2D(FMath::Clamp(U, 0.0f, 1.0f), FMath::Clamp(V, 0.0f, 1.0f));
}

float ASnowStateManagerV1::ConvertRadiusToUv(const float RadiusCm) const
{
    const float MaxExtent = FMath::Max(FMath::Max(WorldMappingExtentCm.X, WorldMappingExtentCm.Y), 1.0f);
    return FMath::Clamp(RadiusCm / (MaxExtent * 2.0f), 0.0001f, 1.0f);
}

FLinearColor ASnowStateManagerV1::BuildChannelDelta(const FSnowStateStampRequestV1& StampRequest) const
{
    return FLinearColor(
        StampRequest.RemainingSnowDepthDelta,
        StampRequest.CompactionRutDepthDelta,
        StampRequest.ClearedExposeRoadDelta,
        StampRequest.BermSidePileDelta
    );
}

UMaterialInstanceDynamic* ASnowStateManagerV1::GetOrCreateWriteMaterialInstance(UMaterialInterface* BaseMaterial)
{
    if (!BaseMaterial)
    {
        return nullptr;
    }

    if (TObjectPtr<UMaterialInstanceDynamic>* Existing = CachedWriteMIDs.Find(BaseMaterial))
    {
        return Existing->Get();
    }

    UMaterialInstanceDynamic* NewMID = UMaterialInstanceDynamic::Create(BaseMaterial, this);
    if (!NewMID)
    {
        return nullptr;
    }

    CachedWriteMIDs.Add(BaseMaterial, NewMID);
    return NewMID;
}
