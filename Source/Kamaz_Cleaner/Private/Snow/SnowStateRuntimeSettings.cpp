#include "Snow/SnowStateRuntimeSettings.h"

USnowStateRuntimeSettings::USnowStateRuntimeSettings()
{
    CategoryName = TEXT("Game");
    SectionName = TEXT("PersistentSnowState");
}

FName USnowStateRuntimeSettings::GetCategoryName() const
{
    return TEXT("Game");
}
