#pragma once

#include "CoreMinimal.h"

namespace SnowReceiverSurfaceTags
{
    inline const FName& RoadSnowCarrierHeight()
    {
        static const FName Tag(TEXT("RoadSnowCarrierHeight"));
        return Tag;
    }
}
