import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import prepare_road_snow_receiver_assets as prsra


MAP_PATH = "/Game/Maps/MoscowEA5"
SAFE_PARENT_PATH = "/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_SnowReceiver"
TEST_INSTANCE_PATH = "/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_Inst_SnowReceiver_Test"


def _write_result(payload: dict) -> str:
    output_dir = os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "offline_road_receiver_recovery.json")
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    unreal.log(f"[offline_recover_road_receiver] Wrote file: {output_path}")
    return output_path


def _save_level_state() -> dict:
    result = {"save_dirty_packages": None, "save_map_only": None}
    try:
        saved = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        result["save_dirty_packages"] = bool(saved)
    except Exception as error:
        result["save_dirty_packages"] = str(error)
    try:
        saved_level = unreal.EditorLoadingAndSavingUtils.save_current_level()
        result["save_map_only"] = bool(saved_level)
    except Exception as error:
        result["save_map_only"] = str(error)
    return result


def main():
    global prsra
    prsra = importlib.reload(prsra)

    load_result = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    if load_result is None:
        raise RuntimeError(f"Failed to load map: {MAP_PATH}")

    parent_result = prsra.reparent_material_instance(TEST_INSTANCE_PATH, SAFE_PARENT_PATH)
    actor_result = prsra.restore_original_material_on_test_actor()
    save_result = _save_level_state()

    result = {
        "map_path": MAP_PATH,
        "load_result": str(load_result),
        "parent_result": parent_result,
        "actor_result": actor_result,
        "save_result": save_result,
    }
    output_path = _write_result(result)
    result["output_path"] = output_path
    unreal.log(f"[offline_recover_road_receiver] {result}")


if __name__ == "__main__":
    main()
