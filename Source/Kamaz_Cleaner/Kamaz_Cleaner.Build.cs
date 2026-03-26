using UnrealBuildTool;

public class Kamaz_Cleaner : ModuleRules
{
    public Kamaz_Cleaner(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(
            new[]
            {
                "ChaosVehicles",
                "Core",
                "CoreUObject",
                "DeveloperSettings",
                "Engine",
                "InputCore",
                "Json",
                "Landscape"
            }
        );
    }
}
