using UnrealBuildTool;

public class Kamaz_Cleaner : ModuleRules
{
    public Kamaz_Cleaner(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(
            new[]
            {
                "Core",
                "CoreUObject",
                "DeveloperSettings",
                "Engine",
                "Json"
            }
        );
    }
}
