import json
import os

import unreal


OUT = os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation", "_tmp_probe_menu_api.json")


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    payload = {
        "classes": {},
        "functions": {},
    }

    class_names = [
        "WidgetBlueprint",
        "WidgetBlueprintFactory",
        "EditorUtilityWidgetBlueprintFactory",
        "WidgetTree",
        "BlueprintFactory",
        "DataAssetFactory",
        "PrimaryDataAsset",
        "EditorAssetLibrary",
        "EditorLoadingAndSavingUtils",
        "AssetToolsHelpers",
        "UMGEditorProjectSettings",
    ]

    for name in class_names:
        payload["classes"][name] = hasattr(unreal, name)

    if hasattr(unreal, "EditorAssetLibrary"):
        payload["functions"]["make_directory"] = hasattr(unreal.EditorAssetLibrary, "make_directory")
        payload["functions"]["duplicate_asset"] = hasattr(unreal.EditorAssetLibrary, "duplicate_asset")
        payload["functions"]["save_loaded_asset"] = hasattr(unreal.EditorAssetLibrary, "save_loaded_asset")

    if hasattr(unreal, "EditorLoadingAndSavingUtils"):
        cls = unreal.EditorLoadingAndSavingUtils
        for fn in [
            "new_blank_map",
            "save_dirty_packages",
            "load_map",
            "save_map",
            "new_map_from_template",
        ]:
            payload["functions"][f"EditorLoadingAndSavingUtils.{fn}"] = hasattr(cls, fn)

    if hasattr(unreal, "WidgetBlueprintLibrary"):
        cls = unreal.WidgetBlueprintLibrary
        for fn in ["create", "set_input_mode_game_and_ui"]:
            payload["functions"][f"WidgetBlueprintLibrary.{fn}"] = hasattr(cls, fn)

    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    print(payload)


if __name__ == "__main__":
    main()
