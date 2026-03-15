#pragma once

#include "CoreMinimal.h"
#include "PersistentSnowStateTypes.generated.h"

UENUM(BlueprintType)
enum class ESnowReceiverSurfaceFamily : uint8
{
    Unknown UMETA(DisplayName = "Unknown"),
    Road UMETA(DisplayName = "Road"),
    CurbTop UMETA(DisplayName = "Curb Top"),
    Sidewalk UMETA(DisplayName = "Sidewalk"),
    Shoulder UMETA(DisplayName = "Shoulder"),
    Landscape UMETA(DisplayName = "Landscape")
};

USTRUCT(BlueprintType)
struct KAMAZ_CLEANER_API FSnowWorldCellId
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    int32 X = 0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    int32 Y = 0;

    FSnowWorldCellId() = default;
    FSnowWorldCellId(const int32 InX, const int32 InY)
        : X(InX)
        , Y(InY)
    {
    }

    bool operator==(const FSnowWorldCellId& Other) const
    {
        return X == Other.X && Y == Other.Y;
    }
};

FORCEINLINE uint32 GetTypeHash(const FSnowWorldCellId& CellId)
{
    return HashCombine(::GetTypeHash(CellId.X), ::GetTypeHash(CellId.Y));
}

USTRUCT(BlueprintType)
struct KAMAZ_CLEANER_API FSnowDirtyRect
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    int32 MinX = 0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    int32 MinY = 0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    int32 MaxX = 0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    int32 MaxY = 0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    bool bIsValid = false;

    void IncludePixel(const FIntPoint& Pixel)
    {
        if (!bIsValid)
        {
            MinX = Pixel.X;
            MinY = Pixel.Y;
            MaxX = Pixel.X;
            MaxY = Pixel.Y;
            bIsValid = true;
            return;
        }

        MinX = FMath::Min(MinX, Pixel.X);
        MinY = FMath::Min(MinY, Pixel.Y);
        MaxX = FMath::Max(MaxX, Pixel.X);
        MaxY = FMath::Max(MaxY, Pixel.Y);
    }
};

USTRUCT(BlueprintType)
struct KAMAZ_CLEANER_API FSnowCellBounds2D
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    FVector2D WorldMin = FVector2D::ZeroVector;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    FVector2D WorldMax = FVector2D::ZeroVector;
};

USTRUCT(BlueprintType)
struct KAMAZ_CLEANER_API FSnowCellSnapshot
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    FSnowWorldCellId CellId;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    bool bIsDirty = false;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    double LastTouchedTimeSeconds = 0.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    int32 PendingWriteCount = 0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    FSnowDirtyRect DirtyRect;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    FString SaveRelativePath;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Snow")
    ESnowReceiverSurfaceFamily DominantSurfaceFamily = ESnowReceiverSurfaceFamily::Unknown;
};
