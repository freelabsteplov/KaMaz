import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import prepare_road_snow_receiver_assets as prsra
import rebuild_visible_road_snow_receiver as rvsr
import capture_road_receiver_after_stamp as crrs


MAP_PATH = "/Game/Maps/MoscowEA5"
RECEIVER_INSTANCE_PATH = "/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_Inst_SnowReceiver_Test"
PROBE_ACTOR_PATHS = [
    "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208",
    "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_188",
    "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_142",
]
OUTPUT_BASENAME = "probe_spawn_zone_receiver_candidates"


def _log(message: str) -> None:
    unreal.log(f"[probe_spawn_zone_receiver_candidates] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_path(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _capture_candidate(world, actor, output_dir: str, base_filename: str) -> dict:
    origin, extent = crrs._get_actor_bounds(actor)
    capture = crrs._capture_view(
        world,
        origin,
        max(float(extent.x), float(extent.y), 20000.0),
        output_dir,
        base_filename,
        actor,
    )
    return {
        "actor_path": _object_path(actor),
        "actor_name": actor.get_name(),
        "bounds_origin": {"x": float(origin.x), "y": float(origin.y), "z": float(origin.z)},
        "bounds_extent": {"x": float(extent.x), "y": float(extent.y), "z": float(extent.z)},
        "capture": capture,
    }


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    global prsra, rvsr, crrs
    prsra = importlib.reload(prsra)
    rvsr = importlib.reload(rvsr)
    crrs = importlib.reload(crrs)

    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    rebuild_result = rvsr.run(output_dir)
    world = crrs._get_editor_world()

    probes = []
    best_probe = None
    best_magenta = -1
    for index, actor_path in enumerate(PROBE_ACTOR_PATHS):
        apply_result = prsra.apply_material_to_actor_slot0(actor_path, RECEIVER_INSTANCE_PATH)
        actor = crrs._find_actor(actor_path)
        if actor is None:
            probes.append(
                {
                    "actor_path": actor_path,
                    "apply_result": apply_result,
                    "error": "actor_not_found",
                }
            )
            continue
        probe = _capture_candidate(world, actor, output_dir, f"{OUTPUT_BASENAME}_{index}")
        probe["apply_result"] = apply_result
        magenta_like = int(probe["capture"]["capture_grid_stats"].get("magenta_like_samples", 0))
        probe["magenta_like_samples"] = magenta_like
        probes.append(probe)
        if magenta_like > best_magenta:
            best_magenta = magenta_like
            best_probe = probe

    result = {
        "success": True,
        "map_path": MAP_PATH,
        "receiver_instance_path": RECEIVER_INSTANCE_PATH,
        "rebuild_result": rebuild_result,
        "probes": probes,
        "best_probe_actor_path": best_probe.get("actor_path") if best_probe else "",
        "best_probe_magenta_like_samples": int(best_magenta),
    }
    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(run())
