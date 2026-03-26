import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
SOURCE_MI_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_Landscape"
TARGET_MI_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_Landscape_SoftSeam"
LANDSCAPE_LABEL = "Landscape"
OUTPUT_BASENAME = "apply_snowtest_landscape_soft_seam"

TARGET_SCALARS = {
    "SnowTexUVScale": 16.0,
    "HeightAmplitude": -35.0,
    "EdgeRaiseAmplitude": 6.0,
    "HeightContrast": 0.9,
    "EdgeSharpness": 0.65,
}


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return path


def _load_asset(asset_path: str):
    return unreal.EditorAssetLibrary.load_asset(asset_path)


def _ensure_material_instance(target_path: str, source_path: str):
    existing = _load_asset(target_path)
    if existing:
        return existing, False

    package_path, asset_name = target_path.rsplit("/", 1)
    duplicated = unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(
        asset_name,
        package_path,
        _load_asset(source_path),
    )
    if not duplicated:
        raise RuntimeError(f"Failed to duplicate material instance to {target_path}")
    return duplicated, True


def _scalar_value(instance, name: str):
    try:
        return float(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(instance, name))
    except Exception:
        return None


def _set_scalar(instance, name: str, value: float) -> dict:
    before = _scalar_value(instance, name)
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instance, name, value)
    after = _scalar_value(instance, name)
    return {
        "before": before,
        "after": after,
        "target": value,
    }


def _find_landscape_actor():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_subsystem.get_all_level_actors():
        if actor.get_actor_label() == LANDSCAPE_LABEL or "Landscape" in actor.get_class().get_path_name():
            return actor
    return None


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    result = {
        "map_path": MAP_PATH,
        "source_mi_path": SOURCE_MI_PATH,
        "target_mi_path": TARGET_MI_PATH,
        "created_new_mi": False,
        "scalar_changes": {},
        "landscape_actor_path": "",
        "before_landscape_material": "",
        "after_landscape_material": "",
        "saved_mi": False,
        "saved_level": False,
        "error": "",
        "notes": [
            "Safe visual refinement only for SnowTest_Level landscape.",
            "Parent material graph is not changed.",
            "This pass reduces harsh WPO and increases snow detail tiling to hide coarse landscape stepping near the road seam.",
        ],
    }

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

        source_mi = _load_asset(SOURCE_MI_PATH)
        if not source_mi:
            raise RuntimeError(f"Could not load source material instance: {SOURCE_MI_PATH}")

        target_mi, created_new = _ensure_material_instance(TARGET_MI_PATH, SOURCE_MI_PATH)
        result["created_new_mi"] = bool(created_new)

        for param_name, target_value in TARGET_SCALARS.items():
            result["scalar_changes"][param_name] = _set_scalar(target_mi, param_name, target_value)

        result["saved_mi"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(target_mi, False))

        landscape_actor = _find_landscape_actor()
        if not landscape_actor:
            raise RuntimeError("Could not find Landscape actor in SnowTest_Level")

        result["landscape_actor_path"] = landscape_actor.get_path_name()
        try:
            before_material = landscape_actor.get_editor_property("landscape_material")
        except Exception:
            before_material = None
        result["before_landscape_material"] = before_material.get_path_name() if before_material else ""

        landscape_actor.modify()
        landscape_actor.set_editor_property("landscape_material", target_mi)
        try:
            landscape_actor.post_edit_change()
        except Exception:
            pass

        try:
            after_material = landscape_actor.get_editor_property("landscape_material")
        except Exception:
            after_material = None
        result["after_landscape_material"] = after_material.get_path_name() if after_material else ""

        result["saved_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())

        try:
            unreal.EditorLevelLibrary.editor_invalidate_viewports()
        except Exception:
            pass

    except Exception as exc:
        result["error"] = str(exc)

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(run())
