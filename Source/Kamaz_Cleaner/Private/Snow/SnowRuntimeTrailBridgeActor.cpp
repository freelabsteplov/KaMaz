#include "Snow/SnowRuntimeTrailBridgeActor.h"

#include "Components/SceneComponent.h"
#include "Snow/SnowRuntimeTrailBridgeComponent.h"

ASnowRuntimeTrailBridgeActor::ASnowRuntimeTrailBridgeActor()
{
    PrimaryActorTick.bCanEverTick = false;
    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    RootComponent = Root;

    TrailComponent = CreateDefaultSubobject<USnowRuntimeTrailBridgeComponent>(TEXT("TrailComponent"));
}
