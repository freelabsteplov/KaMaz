#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Snow/PersistentSnowStateTypes.h"
#include "SnowStateBlueprintLibrary.generated.h"

class UActorComponent;

UCLASS()
class KAMAZ_CLEANER_API USnowStateBlueprintLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category = "Snow State", meta = (DefaultToSelf = "SourceComponent"))
    static FSnowCellSnapshot MarkPersistentWheelWriter(
        UActorComponent* SourceComponent,
        ESnowReceiverSurfaceFamily SurfaceFamily = ESnowReceiverSurfaceFamily::Road,
        bool bFlushNow = false
    );

    UFUNCTION(BlueprintCallable, Category = "Snow State", meta = (DefaultToSelf = "SourceComponent"))
    static TArray<FSnowCellSnapshot> MarkPersistentPlowWriter(
        UActorComponent* SourceComponent,
        float LengthCm = 50.0f,
        float WidthCm = 350.0f,
        ESnowReceiverSurfaceFamily SurfaceFamily = ESnowReceiverSurfaceFamily::Road,
        bool bFlushNow = false
    );

    UFUNCTION(BlueprintCallable, Category = "Snow State", meta = (WorldContext = "WorldContextObject"))
    static TArray<FSnowCellSnapshot> FlushPersistentSnowState(UObject* WorldContextObject);
};
