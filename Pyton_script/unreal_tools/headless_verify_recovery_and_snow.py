import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import inspect_level_surface_materials as ilsm
import inspect_snow_receivers as isr
import snow_bounds_tools as sbt


MAP_PATH = "/Game/Maps/MoscowEA5"
MPC_SNOW_SYSTEM_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"
OUTPUT_BASENAME = "headless_recovery_startup_verify"


def _log(message: str) -> None:
    unreal.log(f"[headless_verify_recovery_and_snow] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_name(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _vec_to_dict(value):
    if value is None:
        return None
    return {
        "x": float(value.x),
        "y": float(value.y),
        "z": float(value.z),
    }


def _color_to_dict(value):
    if value is None:
        return None
    return {
        "r": float(value.r),
        "g": float(value.g),
        "b": float(value.b),
        "a": float(value.a),
    }


def _safe_get_editor_property(obj, property_name: str, default=None):
    getter = getattr(obj, "get_editor_property", None)
    if getter is None:
        return getattr(obj, property_name, default)
    try:
        return getter(property_name)
    except Exception:
        return getattr(obj, property_name, default)


def _inspect_mpc(collection) -> dict:
    vector_parameters = []
    scalar_parameters = []

    for parameter in _safe_get_editor_property(collection, "vector_parameters", []) or []:
        vector_parameters.append(
            {
                "parameter_name": str(_safe_get_editor_property(parameter, "parameter_name", "")),
                "default_value": _color_to_dict(_safe_get_editor_property(parameter, "default_value")),
            }
        )

    for parameter in _safe_get_editor_property(collection, "scalar_parameters", []) or []:
        scalar_parameters.append(
            {
                "parameter_name": str(_safe_get_editor_property(parameter, "parameter_name", "")),
                "default_value": float(_safe_get_editor_property(parameter, "default_value", 0.0)),
            }
        )

    current_min = sbt._get_mpc_vector(collection, "WorldBoundsMin")
    current_max = sbt._get_mpc_vector(collection, "WorldBoundsMax")

    return {
        "asset_path": MPC_SNOW_SYSTEM_PATH,
        "vector_parameters": vector_parameters,
        "scalar_parameters": scalar_parameters,
        "current_world_bounds_min": _vec_to_dict(current_min),
        "current_world_bounds_max": _vec_to_dict(current_max),
    }


def main() -> dict:
    global ilsm
    global isr
    global sbt

    ilsm = importlib.reload(ilsm)
    isr = importlib.reload(isr)
    sbt = importlib.reload(sbt)

    load_result = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    if load_result is None:
        raise RuntimeError(f"Failed to load map: {MAP_PATH}")

    world = unreal.EditorLevelLibrary.get_editor_world()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = actor_subsystem.get_all_level_actors() or []
    mpc_collection = unreal.EditorAssetLibrary.load_asset(MPC_SNOW_SYSTEM_PATH)

    bounds_result = sbt.inspect_snow_bounds()
    receivers_result = isr.inspect_current_level_snow_receivers()
    surfaces_result = ilsm.inspect_current_level_surface_materials()
    mpc_result = _inspect_mpc(mpc_collection) if mpc_collection else {"asset_path": MPC_SNOW_SYSTEM_PATH, "missing": True}

    result = {
        "map_path": MAP_PATH,
        "load_result": str(load_result),
        "world_name": _object_name(world),
        "actor_count": len(actors),
        "startup_ok": bool(world),
        "snow_bounds_output_path": bounds_result.get("output_path"),
        "snow_receivers_output_path": receivers_result.get("output_path"),
        "surface_materials_output_path": surfaces_result.get("output_path"),
        "snow_bounds": {
            "current_world_bounds_min": bounds_result.get("current_world_bounds_min"),
            "current_world_bounds_max": bounds_result.get("current_world_bounds_max"),
            "suggested_world_bounds_min": bounds_result.get("suggested_world_bounds_min"),
            "suggested_world_bounds_max": bounds_result.get("suggested_world_bounds_max"),
            "landscape_count": bounds_result.get("landscape_count"),
        },
        "snow_receivers": {
            "num_snow_receivers": receivers_result.get("num_snow_receivers"),
        },
        "mpc_snow_system": mpc_result,
        "surface_materials": {
            "num_landscape_candidates": surfaces_result.get("num_landscape_candidates"),
            "top_surface_materials": surfaces_result.get("top_surface_materials", [])[:10],
        },
    }

    output_path = os.path.join(_saved_output_dir(), f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    _log(f"startup_ok={result['startup_ok']} world={result['world_name']} receivers={result['snow_receivers']['num_snow_receivers']}")
    return result


if __name__ == "__main__":
    print(main())
