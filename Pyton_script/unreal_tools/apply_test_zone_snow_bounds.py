import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
TEST_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
MPC_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"
OUTPUT_BASENAME = "apply_test_zone_snow_bounds"
WORLD_BOUNDS_MIN_PARAMETER = "WorldBoundsMin"
WORLD_BOUNDS_MAX_PARAMETER = "WorldBoundsMax"
BRUSH_UV_PARAMETER = "BrushUV"

TEST_HALF_EXTENT_X_CM = 50000.0
TEST_HALF_EXTENT_Y_CM = 50000.0
TEST_HALF_EXTENT_Z_CM = 1000.0


def _log(message: str) -> None:
    unreal.log(f"[apply_test_zone_snow_bounds] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _load_asset(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Could not load asset: {asset_path}")
    return asset


def _object_path(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _vector_to_dict(value):
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


def _to_linear_color(vector_value: unreal.Vector) -> unreal.LinearColor:
    return unreal.LinearColor(float(vector_value.x), float(vector_value.y), float(vector_value.z), 0.0)


def _safe_property(obj, property_name: str, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(property_name)
        except Exception:
            pass
    return getattr(obj, property_name, default)


def _find_actor(actor_path: str):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        if _object_path(actor) == actor_path:
            return actor
    return None


def _get_actor_bounds(actor):
    get_bounds = getattr(actor, "get_actor_bounds", None)
    if callable(get_bounds):
        try:
            origin, extent = get_bounds(True)
            return origin, extent
        except Exception:
            pass
    raise RuntimeError(f"Could not read bounds for actor: {_object_path(actor)}")


def _snapshot_vector_params(collection) -> list[dict]:
    snapshot = []
    for parameter in list(_safe_property(collection, "vector_parameters", []) or []):
        snapshot.append(
            {
                "parameter_name": str(_safe_property(parameter, "parameter_name")),
                "default_value": _color_to_dict(_safe_property(parameter, "default_value")),
            }
        )
    return snapshot


def _set_vector_parameter_default(collection, parameter_name: str, value: unreal.LinearColor) -> str:
    vector_parameters = list(_safe_property(collection, "vector_parameters", []) or [])
    for entry in vector_parameters:
        if str(_safe_property(entry, "parameter_name")) != parameter_name:
            continue
        entry.set_editor_property("default_value", value)
        collection.set_editor_property("vector_parameters", vector_parameters)
        return "updated"

    new_parameter = unreal.CollectionVectorParameter()
    new_parameter.set_editor_property("parameter_name", parameter_name)
    new_parameter.set_editor_property("default_value", value)
    vector_parameters.append(new_parameter)
    collection.set_editor_property("vector_parameters", vector_parameters)
    return "created"


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    actor = _find_actor(TEST_ACTOR_PATH)
    if actor is None:
        raise RuntimeError(f"Could not find actor: {TEST_ACTOR_PATH}")

    mpc = _load_asset(MPC_PATH)
    origin, extent = _get_actor_bounds(actor)

    target_min = unreal.Vector(
        float(origin.x - TEST_HALF_EXTENT_X_CM),
        float(origin.y - TEST_HALF_EXTENT_Y_CM),
        float(origin.z - TEST_HALF_EXTENT_Z_CM),
    )
    target_max = unreal.Vector(
        float(origin.x + TEST_HALF_EXTENT_X_CM),
        float(origin.y + TEST_HALF_EXTENT_Y_CM),
        float(origin.z + TEST_HALF_EXTENT_Z_CM),
    )

    before_vector_parameters = _snapshot_vector_params(mpc)
    mpc.modify(True)
    min_status = _set_vector_parameter_default(mpc, WORLD_BOUNDS_MIN_PARAMETER, _to_linear_color(target_min))
    max_status = _set_vector_parameter_default(mpc, WORLD_BOUNDS_MAX_PARAMETER, _to_linear_color(target_max))
    brush_uv_status = _set_vector_parameter_default(
        mpc,
        BRUSH_UV_PARAMETER,
        unreal.LinearColor(0.5, 0.5, 0.0, 0.0),
    )
    mark_dirty = getattr(mpc, "mark_package_dirty", None)
    if callable(mark_dirty):
        mark_dirty()
    saved = bool(unreal.EditorAssetLibrary.save_loaded_asset(mpc, False))

    result = {
        "success": True,
        "map_path": MAP_PATH,
        "actor_path": TEST_ACTOR_PATH,
        "actor_bounds_origin": _vector_to_dict(origin),
        "actor_bounds_extent": _vector_to_dict(extent),
        "mpc_path": _object_path(mpc),
        "test_half_extent_cm": {
            "x": TEST_HALF_EXTENT_X_CM,
            "y": TEST_HALF_EXTENT_Y_CM,
            "z": TEST_HALF_EXTENT_Z_CM,
        },
        "target_world_bounds_min": _vector_to_dict(target_min),
        "target_world_bounds_max": _vector_to_dict(target_max),
        "parameter_results": {
            WORLD_BOUNDS_MIN_PARAMETER: min_status,
            WORLD_BOUNDS_MAX_PARAMETER: max_status,
            BRUSH_UV_PARAMETER: brush_uv_status,
        },
        "before_vector_parameters": before_vector_parameters,
        "after_vector_parameters": _snapshot_vector_params(mpc),
        "saved": saved,
    }
    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary() -> str:
    result = run()
    summary = (
        f"Applied test-zone snow bounds around {TEST_ACTOR_PATH} "
        f"half_extent=({TEST_HALF_EXTENT_X_CM:.0f},{TEST_HALF_EXTENT_Y_CM:.0f},{TEST_HALF_EXTENT_Z_CM:.0f}) "
        f"saved={result.get('saved')}"
    )
    _log(summary)
    return summary


if __name__ == "__main__":
    print(run())
