import json
import os

import unreal


OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "tmp_probe_physicsasset_save_api.json",
)


def _safe_str(value):
    try:
        return str(value)
    except Exception:
        return ""


def main():
    payload = {
        "physics_asset_path": "",
        "physics_asset_class": "",
        "outer": "",
        "outermost": "",
        "asset_subsystem_methods": [],
        "has_editor_loading_and_saving_utils": False,
        "editor_loading_and_saving_utils_methods": [],
        "error": "",
    }

    try:
        physics_asset = unreal.EditorAssetLibrary.load_asset("/Game/CityPark/Kamaz/model/kamaz_ue5_PhysicsAsset")
        if physics_asset is None:
            raise RuntimeError("Could not load kamaz_ue5_PhysicsAsset")

        payload["physics_asset_path"] = physics_asset.get_path_name()
        payload["physics_asset_class"] = physics_asset.get_class().get_name()
        payload["outer"] = _safe_str(physics_asset.get_outer())
        payload["outermost"] = _safe_str(physics_asset.get_outermost())

        asset_subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
        payload["asset_subsystem_methods"] = sorted(
            name for name in dir(asset_subsystem) if "save" in name.lower()
        )

        payload["has_editor_loading_and_saving_utils"] = hasattr(unreal, "EditorLoadingAndSavingUtils")
        if payload["has_editor_loading_and_saving_utils"]:
            payload["editor_loading_and_saving_utils_methods"] = sorted(
                name for name in dir(unreal.EditorLoadingAndSavingUtils) if "save" in name.lower()
            )
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
