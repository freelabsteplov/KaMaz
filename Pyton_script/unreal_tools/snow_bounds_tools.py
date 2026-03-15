import json
import os

import unreal


MPC_SNOW_SYSTEM_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"
OUTPUT_BASENAME = "snow_bounds_report"


def _log(message: str) -> None:
    unreal.log(f"[snow_bounds_tools] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[snow_bounds_tools] {message}")


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
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def _load_asset(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not asset:
        raise RuntimeError(f"Failed to load asset: {asset_path}")
    return asset


def _get_editor_world():
    return unreal.EditorLevelLibrary.get_editor_world()


def _get_actor_bounds(actor):
    try:
        origin, extent = actor.get_actor_bounds(False)
        return origin, extent
    except Exception:
        return None, None


def _accumulate_bounds(current_min, current_max, origin, extent):
    actor_min = unreal.Vector(origin.x - extent.x, origin.y - extent.y, origin.z - extent.z)
    actor_max = unreal.Vector(origin.x + extent.x, origin.y + extent.y, origin.z + extent.z)

    if current_min is None:
        return actor_min, actor_max

    return (
        unreal.Vector(
            min(current_min.x, actor_min.x),
            min(current_min.y, actor_min.y),
            min(current_min.z, actor_min.z),
        ),
        unreal.Vector(
            max(current_max.x, actor_max.x),
            max(current_max.y, actor_max.y),
            max(current_max.z, actor_max.z),
        ),
    )


def _iter_relevant_actors():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_subsystem.get_all_level_actors():
        if actor is None:
            continue
        if getattr(actor, "is_editor_only_actor", lambda: False)():
            continue
        yield actor


def _compute_level_bounds():
    overall_min = None
    overall_max = None
    landscape_min = None
    landscape_max = None
    actor_count = 0
    landscape_count = 0

    for actor in _iter_relevant_actors():
        origin, extent = _get_actor_bounds(actor)
        if origin is None or extent is None:
            continue

        actor_count += 1
        overall_min, overall_max = _accumulate_bounds(overall_min, overall_max, origin, extent)

        class_name = actor.get_class().get_name()
        if "Landscape" in class_name:
            landscape_count += 1
            landscape_min, landscape_max = _accumulate_bounds(landscape_min, landscape_max, origin, extent)

    return {
        "actor_count": actor_count,
        "overall_min": overall_min,
        "overall_max": overall_max,
        "landscape_count": landscape_count,
        "landscape_min": landscape_min,
        "landscape_max": landscape_max,
    }


def _get_mpc_vector(collection, parameter_name: str):
    world = _get_editor_world()
    library = getattr(unreal, "KismetMaterialLibrary", None)
    if library is None:
        return None

    getter_names = (
        "get_vector_parameter_value",
        "get_vector_parameter_value_by_name",
    )

    for getter_name in getter_names:
        getter = getattr(library, getter_name, None)
        if getter is None:
            continue
        try:
            return getter(world, collection, parameter_name)
        except TypeError:
            try:
                return getter(collection, parameter_name)
            except Exception:
                continue
        except Exception:
            continue

    return None


def _set_mpc_vector(collection, parameter_name: str, value: unreal.Vector) -> bool:
    world = _get_editor_world()
    library = getattr(unreal, "KismetMaterialLibrary", None)
    if library is None:
        return False

    setter_names = (
        "set_vector_parameter_value",
        "set_vector_parameter_value_by_name",
    )

    for setter_name in setter_names:
        setter = getattr(library, setter_name, None)
        if setter is None:
            continue
        try:
            setter(world, collection, parameter_name, value)
            return True
        except TypeError:
            try:
                setter(collection, parameter_name, value)
                return True
            except Exception:
                continue
        except Exception:
            continue

    return False


def _add_padding(bounds_min: unreal.Vector, bounds_max: unreal.Vector, padding_xy: float, padding_z: float):
    return (
        unreal.Vector(bounds_min.x - padding_xy, bounds_min.y - padding_xy, bounds_min.z - padding_z),
        unreal.Vector(bounds_max.x + padding_xy, bounds_max.y + padding_xy, bounds_max.z + padding_z),
    )


def inspect_snow_bounds(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    collection = _load_asset(MPC_SNOW_SYSTEM_PATH)
    world = _get_editor_world()
    level_name = world.get_name()

    bounds = _compute_level_bounds()
    current_min = _get_mpc_vector(collection, "WorldBoundsMin")
    current_max = _get_mpc_vector(collection, "WorldBoundsMax")

    suggested_min = bounds["landscape_min"] or bounds["overall_min"]
    suggested_max = bounds["landscape_max"] or bounds["overall_max"]

    result = {
        "level_name": level_name,
        "mpc_path": MPC_SNOW_SYSTEM_PATH,
        "current_world_bounds_min": _vec_to_dict(current_min),
        "current_world_bounds_max": _vec_to_dict(current_max),
        "actor_count": bounds["actor_count"],
        "overall_bounds_min": _vec_to_dict(bounds["overall_min"]),
        "overall_bounds_max": _vec_to_dict(bounds["overall_max"]),
        "landscape_count": bounds["landscape_count"],
        "landscape_bounds_min": _vec_to_dict(bounds["landscape_min"]),
        "landscape_bounds_max": _vec_to_dict(bounds["landscape_max"]),
        "suggested_world_bounds_min": _vec_to_dict(suggested_min),
        "suggested_world_bounds_max": _vec_to_dict(suggested_max),
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def apply_snow_bounds_from_current_level(
    padding_xy: float = 2000.0,
    padding_z: float = 500.0,
    prefer_landscape_bounds: bool = True,
    output_dir: str | None = None,
) -> dict:
    output_dir = output_dir or _saved_output_dir()
    collection = _load_asset(MPC_SNOW_SYSTEM_PATH)

    bounds = _compute_level_bounds()
    base_min = bounds["landscape_min"] if prefer_landscape_bounds and bounds["landscape_min"] is not None else bounds["overall_min"]
    base_max = bounds["landscape_max"] if prefer_landscape_bounds and bounds["landscape_max"] is not None else bounds["overall_max"]

    if base_min is None or base_max is None:
        raise RuntimeError("Failed to compute level bounds.")

    target_min, target_max = _add_padding(base_min, base_max, float(padding_xy), float(padding_z))

    before_min = _get_mpc_vector(collection, "WorldBoundsMin")
    before_max = _get_mpc_vector(collection, "WorldBoundsMax")
    wrote_min = _set_mpc_vector(collection, "WorldBoundsMin", target_min)
    wrote_max = _set_mpc_vector(collection, "WorldBoundsMax", target_max)
    after_min = _get_mpc_vector(collection, "WorldBoundsMin")
    after_max = _get_mpc_vector(collection, "WorldBoundsMax")

    result = {
        "level_name": _get_editor_world().get_name(),
        "mpc_path": MPC_SNOW_SYSTEM_PATH,
        "prefer_landscape_bounds": bool(prefer_landscape_bounds),
        "padding_xy": float(padding_xy),
        "padding_z": float(padding_z),
        "before_world_bounds_min": _vec_to_dict(before_min),
        "before_world_bounds_max": _vec_to_dict(before_max),
        "target_world_bounds_min": _vec_to_dict(target_min),
        "target_world_bounds_max": _vec_to_dict(target_max),
        "after_world_bounds_min": _vec_to_dict(after_min),
        "after_world_bounds_max": _vec_to_dict(after_max),
        "wrote_min": bool(wrote_min),
        "wrote_max": bool(wrote_max),
    }

    output_path = os.path.join(output_dir, "snow_bounds_apply_result.json")
    _write_json(output_path, result)
    result["output_path"] = output_path

    if not (wrote_min and wrote_max):
        _warn("Could not update one or more MPC bounds parameters from Python.")

    return result


if __name__ == "__main__":
    print(inspect_snow_bounds())
