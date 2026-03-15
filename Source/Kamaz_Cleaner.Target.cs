using UnrealBuildTool;
using System.Collections.Generic;

public class Kamaz_CleanerTarget : TargetRules
{
    public Kamaz_CleanerTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V6;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_7;

        ExtraModuleNames.Add("Kamaz_Cleaner");
    }
}
