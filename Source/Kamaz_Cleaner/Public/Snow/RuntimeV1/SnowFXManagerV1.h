#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

#include "SnowFXManagerV1.generated.h"

USTRUCT(BlueprintType)
struct KAMAZ_CLEANER_API FSnowFXEventV1
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1")
    FVector WorldLocation = FVector::ZeroVector;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1")
    FVector WorldVelocity = FVector::ZeroVector;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1")
    float Intensity = 0.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1")
    bool bIsPlowEvent = false;
};

UCLASS(BlueprintType, Blueprintable)
class KAMAZ_CLEANER_API ASnowFXManagerV1 : public AActor
{
    GENERATED_BODY()

public:
    ASnowFXManagerV1();

    UFUNCTION(BlueprintCallable, Category = "Snow Runtime V1|FX")
    void EnqueueFXEvent(const FSnowFXEventV1& FXEvent);

    UFUNCTION(BlueprintCallable, Category = "Snow Runtime V1|FX")
    void ClearQueuedFXEvents();

    UFUNCTION(BlueprintPure, Category = "Snow Runtime V1|FX")
    int32 GetQueuedFXEventCount() const;

private:
    UPROPERTY(Transient)
    TArray<FSnowFXEventV1> QueuedFXEvents;
};
