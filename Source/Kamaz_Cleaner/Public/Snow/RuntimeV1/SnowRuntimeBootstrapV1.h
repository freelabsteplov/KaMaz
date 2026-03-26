#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

#include "SnowRuntimeBootstrapV1.generated.h"

class ASnowFXManagerV1;
class ASnowStateManagerV1;

UCLASS(BlueprintType, Blueprintable)
class KAMAZ_CLEANER_API ASnowRuntimeBootstrapV1 : public AActor
{
    GENERATED_BODY()

public:
    ASnowRuntimeBootstrapV1();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1")
    TObjectPtr<ASnowStateManagerV1> SnowStateManager = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1")
    TObjectPtr<ASnowFXManagerV1> SnowFXManager = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1")
    TObjectPtr<AActor> TargetVehicle = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Snow Runtime V1")
    bool bAutoRefreshOnBeginPlay = true;

    UFUNCTION(BlueprintCallable, Category = "Snow Runtime V1")
    void RefreshRuntimeLinks();

protected:
    virtual void BeginPlay() override;
};
