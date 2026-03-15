#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Snow/PersistentSnowStateTypes.h"
#include "SnowReceiverSurfaceComponent.generated.h"

UCLASS(ClassGroup = (Snow), BlueprintType, Blueprintable, meta = (BlueprintSpawnableComponent))
class KAMAZ_CLEANER_API USnowReceiverSurfaceComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    USnowReceiverSurfaceComponent();

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow Receiver")
    bool bParticipatesInPersistentSnowState = true;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow Receiver")
    ESnowReceiverSurfaceFamily SurfaceFamily = ESnowReceiverSurfaceFamily::Road;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow Receiver")
    int32 ReceiverPriority = 0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow Receiver")
    FName ReceiverSetTag = NAME_None;
};
