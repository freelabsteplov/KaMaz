#include "Snow/RuntimeV1/SnowFXManagerV1.h"

ASnowFXManagerV1::ASnowFXManagerV1()
{
    PrimaryActorTick.bCanEverTick = false;
}

void ASnowFXManagerV1::EnqueueFXEvent(const FSnowFXEventV1& FXEvent)
{
    QueuedFXEvents.Add(FXEvent);
}

void ASnowFXManagerV1::ClearQueuedFXEvents()
{
    QueuedFXEvents.Reset();
}

int32 ASnowFXManagerV1::GetQueuedFXEventCount() const
{
    return QueuedFXEvents.Num();
}
