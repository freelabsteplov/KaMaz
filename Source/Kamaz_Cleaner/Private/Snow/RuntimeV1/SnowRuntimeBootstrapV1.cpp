#include "Snow/RuntimeV1/SnowRuntimeBootstrapV1.h"

#include "Engine/World.h"
#include "EngineUtils.h"
#include "Snow/RuntimeV1/SnowFXManagerV1.h"
#include "Snow/RuntimeV1/SnowStateManagerV1.h"

ASnowRuntimeBootstrapV1::ASnowRuntimeBootstrapV1()
{
    PrimaryActorTick.bCanEverTick = false;
}

void ASnowRuntimeBootstrapV1::BeginPlay()
{
    Super::BeginPlay();

    if (bAutoRefreshOnBeginPlay)
    {
        RefreshRuntimeLinks();
    }
}

void ASnowRuntimeBootstrapV1::RefreshRuntimeLinks()
{
    UWorld* World = GetWorld();
    if (!World)
    {
        return;
    }

    if (!SnowStateManager)
    {
        for (TActorIterator<ASnowStateManagerV1> It(World); It; ++It)
        {
            SnowStateManager = *It;
            break;
        }
    }

    if (!SnowFXManager)
    {
        for (TActorIterator<ASnowFXManagerV1> It(World); It; ++It)
        {
            SnowFXManager = *It;
            break;
        }
    }

    if (SnowStateManager && TargetVehicle)
    {
        SnowStateManager->CenterMappingOnWorldLocation(TargetVehicle->GetActorLocation());
    }
}
