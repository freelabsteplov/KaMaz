import json
import os

import unreal

import prepare_road_snow_receiver_assets as prsra


MAP_PATH = "/Game/Maps/MoscowEA5"
RECEIVER_INSTANCE_PATH = "/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_Inst_SnowReceiver_Test"
TARGET_ACTOR_PATHS = [
    "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208",
    "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_188",
    "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_142",
]
OUTPUT_BASENAME = "apply_receiver_to_spawn_zone_roads"


def _log(message: str) -> None:
    unreal.log(f"[apply_receiver_to_spawn_zone_roads] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    apply_results = []
    total_components_updated = 0
    for actor_path in TARGET_ACTOR_PATHS:
        apply_result = prsra.apply_material_to_actor_slot0(actor_path, RECEIVER_INSTANCE_PATH)
        total_components_updated += int(apply_result.get("num_components_updated", 0))
        apply_results.append(apply_result)

    save_result = {
        "saved_current_level": False,
        "error": "",
    }
    try:
        save_result["saved_current_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    except Exception as exc:
        save_result["error"] = str(exc)

    result = {
        "success": total_components_updated > 0,
        "map_path": MAP_PATH,
        "receiver_instance_path": RECEIVER_INSTANCE_PATH,
        "target_actor_paths": TARGET_ACTOR_PATHS,
        "total_components_updated": int(total_components_updated),
        "apply_results": apply_results,
        "save_result": save_result,
    }
    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(run())
