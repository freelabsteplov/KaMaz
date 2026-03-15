using UnrealBuildTool;
using System.Collections.Generic;

public class Kamaz_CleanerEditorTarget : TargetRules
{
    public Kamaz_CleanerEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V6;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_7;

        ExtraModuleNames.Add("Kamaz_Cleaner");
    }
}
