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
TEST_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
RECEIVER_PARENT_PATH = "/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_SnowReceiver"
RECEIVER_INSTANCE_PATH = "/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_Inst_SnowReceiver_Test"
OUTPUT_BASENAME = "probe_receiver_parent_vs_instance"


def _log(message: str) -> None:
    unreal.log(f"[probe_receiver_parent_vs_instance] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _capture_for_actor(world, actor, output_dir: str, suffix: str) -> dict:
    origin, extent = crrs._get_actor_bounds(actor)
    capture = crrs._capture_view(
        world,
        origin,
        max(float(extent.x), float(extent.y), 20000.0),
        output_dir,
        f"{OUTPUT_BASENAME}_{suffix}",
        actor,
    )
    return {
        "actor_path": crrs._object_path(actor),
        "actor_name": actor.get_name(),
        "capture": capture,
        "magenta_like_samples": int(capture["capture_grid_stats"].get("magenta_like_samples", 0)),
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
    actor = crrs._find_actor(TEST_ACTOR_PATH)
    if actor is None:
        raise RuntimeError(f"Could not find actor: {TEST_ACTOR_PATH}")

    parent_apply = prsra.apply_material_to_actor_slot0(TEST_ACTOR_PATH, RECEIVER_PARENT_PATH)
    parent_capture = _capture_for_actor(world, actor, output_dir, "parent")

    instance_apply = prsra.apply_material_to_actor_slot0(TEST_ACTOR_PATH, RECEIVER_INSTANCE_PATH)
    instance_capture = _capture_for_actor(world, actor, output_dir, "instance")

    result = {
        "success": True,
        "map_path": MAP_PATH,
        "test_actor_path": TEST_ACTOR_PATH,
        "rebuild_result": rebuild_result,
        "parent_apply": parent_apply,
        "parent_capture": parent_capture,
        "instance_apply": instance_apply,
        "instance_capture": instance_capture,
    }
    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(run())
