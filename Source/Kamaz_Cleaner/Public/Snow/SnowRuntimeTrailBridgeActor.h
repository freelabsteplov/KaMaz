#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

#include "SnowRuntimeTrailBridgeActor.generated.h"

class USceneComponent;
class USnowRuntimeTrailBridgeComponent;

UCLASS()
class KAMAZ_CLEANER_API ASnowRuntimeTrailBridgeActor : public AActor
{
    GENERATED_BODY()

public:
    ASnowRuntimeTrailBridgeActor();

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly)
    USceneComponent* Root;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly)
    USnowRuntimeTrailBridgeComponent* TrailComponent;
};
