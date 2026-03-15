using UnrealBuildTool;

public class BlueprintAutomationEditor : ModuleRules
{
	public BlueprintAutomationEditor(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(
			new string[]
			{
				"Core",
				"CoreUObject",
				"Engine"
			}
		);

		PrivateDependencyModuleNames.AddRange(
			new string[]
			{
				"AssetRegistry",
				"BlueprintGraph",
				"Json",
				"JsonUtilities",
				"Kamaz_Cleaner",
				"Kismet",
				"KismetCompiler",
				"Projects",
				"UnrealEd"
			}
		);
	}
}
