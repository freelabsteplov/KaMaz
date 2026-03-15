import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import snow_bounds_tools as sbt


MAP_PATH = "/Game/Maps/MoscowEA5"
OUTPUT_BASENAME = "snow_bounds_asset_fix_result"
BRUSH_UV_PARAMETER = "BrushUV"
WORLD_BOUNDS_MIN_PARAMETER = "WorldBoundsMin"
WORLD_BOUNDS_MAX_PARAMETER = "WorldBoundsMax"


def _log(message: str) -> None:
    unreal.log(f"[persist_snow_bounds_to_mpc_asset] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


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


def _to_linear_color(value: unreal.Vector) -> unreal.LinearColor:
    return unreal.LinearColor(float(value.x), float(value.y), float(value.z), 0.0)


def _load_collection():
    collection = unreal.EditorAssetLibrary.load_asset(sbt.MPC_SNOW_SYSTEM_PATH)
    if collection is None:
        raise RuntimeError(f"Could not load MPC asset: {sbt.MPC_SNOW_SYSTEM_PATH}")
    return collection


def _vector_parameters_snapshot(collection) -> list[dict]:
    snapshot = []
    for parameter in collection.get_editor_property("vector_parameters") or []:
        snapshot.append(
            {
                "parameter_name": str(parameter.get_editor_property("parameter_name")),
                "default_value": _color_to_dict(parameter.get_editor_property("default_value")),
            }
        )
    return snapshot


def _ensure_vector_parameter(parameters, parameter_name: str, default_value: unreal.LinearColor) -> str:
    for parameter in parameters:
        if str(parameter.get_editor_property("parameter_name")) != parameter_name:
            continue
        parameter.set_editor_property("default_value", default_value)
        return "updated"

    parameter = unreal.CollectionVectorParameter()
    parameter.set_editor_property("parameter_name", parameter_name)
    parameter.set_editor_property("default_value", default_value)
    parameters.append(parameter)
    return "created"


def _choose_base_bounds(prefer_landscape_bounds: bool):
    bounds = sbt._compute_level_bounds()
    base_min = bounds["landscape_min"] if prefer_landscape_bounds and bounds["landscape_min"] is not None else bounds["overall_min"]
    base_max = bounds["landscape_max"] if prefer_landscape_bounds and bounds["landscape_max"] is not None else bounds["overall_max"]
    if base_min is None or base_max is None:
        raise RuntimeError("Failed to compute level bounds.")
    return bounds, base_min, base_max


def persist_snow_bounds_to_collection_asset(
    padding_xy: float = 2000.0,
    padding_z: float = 500.0,
    prefer_landscape_bounds: bool = True,
    output_dir: str | None = None,
) -> dict:
    output_dir = output_dir or _saved_output_dir()

    load_result = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    if load_result is None:
        raise RuntimeError(f"Failed to load map: {MAP_PATH}")

    collection = _load_collection()
    bounds, base_min, base_max = _choose_base_bounds(bool(prefer_landscape_bounds))
    target_min, target_max = sbt._add_padding(base_min, base_max, float(padding_xy), float(padding_z))

    vector_parameters = list(collection.get_editor_property("vector_parameters") or [])
    before_vector_parameters = _vector_parameters_snapshot(collection)

    collection.modify(True)
    min_status = _ensure_vector_parameter(vector_parameters, WORLD_BOUNDS_MIN_PARAMETER, _to_linear_color(target_min))
    max_status = _ensure_vector_parameter(vector_parameters, WORLD_BOUNDS_MAX_PARAMETER, _to_linear_color(target_max))
    brush_uv_status = _ensure_vector_parameter(
        vector_parameters,
        BRUSH_UV_PARAMETER,
        unreal.LinearColor(0.0, 0.0, 0.0, 0.0),
    )

    collection.set_editor_property("vector_parameters", vector_parameters)
    mark_dirty = getattr(collection, "mark_package_dirty", None)
    if callable(mark_dirty):
        mark_dirty()

    saved = bool(unreal.EditorAssetLibrary.save_loaded_asset(collection, False))
    after_vector_parameters = _vector_parameters_snapshot(collection)

    result = {
        "map_path": MAP_PATH,
        "load_result": str(load_result),
        "mpc_path": sbt.MPC_SNOW_SYSTEM_PATH,
        "prefer_landscape_bounds": bool(prefer_landscape_bounds),
        "padding_xy": float(padding_xy),
        "padding_z": float(padding_z),
        "landscape_count": bounds["landscape_count"],
        "base_bounds_min": _vec_to_dict(base_min),
        "base_bounds_max": _vec_to_dict(base_max),
        "target_world_bounds_min": _vec_to_dict(target_min),
        "target_world_bounds_max": _vec_to_dict(target_max),
        "before_vector_parameters": before_vector_parameters,
        "after_vector_parameters": after_vector_parameters,
        "parameter_results": {
            WORLD_BOUNDS_MIN_PARAMETER: min_status,
            WORLD_BOUNDS_MAX_PARAMETER: max_status,
            BRUSH_UV_PARAMETER: brush_uv_status,
        },
        "saved": saved,
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(persist_snow_bounds_to_collection_asset())
