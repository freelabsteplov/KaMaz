import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)


OUTPUT_BASENAME = "probe_active_pie_snow_rt"
RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks.RT_SnowTest_WheelTracks"
MPC_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"


def _log(message: str) -> None:
    unreal.log(f"[probe_active_pie_snow_rt] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_name(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_name()
    except Exception:
        return str(value)


def _object_path(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _serialize_color(sample) -> dict:
    return {
        "r": float(getattr(sample, "r", 0.0)),
        "g": float(getattr(sample, "g", 0.0)),
        "b": float(getattr(sample, "b", 0.0)),
        "a": float(getattr(sample, "a", 0.0)),
    }


def _load_asset(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Could not load asset: {asset_path}")
    return asset


def _get_pie_world():
    get_pie_worlds = getattr(unreal.EditorLevelLibrary, "get_pie_worlds", None)
    if callable(get_pie_worlds):
        try:
            worlds = list(get_pie_worlds(False) or [])
            if worlds:
                return worlds[0]
        except Exception:
            pass

    get_game_world = getattr(unreal.EditorLevelLibrary, "get_game_world", None)
    if callable(get_game_world):
        try:
            world = get_game_world()
            if world is not None:
                return world
        except Exception:
            pass

    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    getter = getattr(subsystem, "get_game_world", None)
    if callable(getter):
        try:
            world = getter()
            if world is not None:
                return world
        except Exception:
            pass

    raise RuntimeError("No active PIE world found. Start PIE first.")


def _iter_world_actors(world):
    persistent_level = getattr(world, "persistent_level", None)
    if persistent_level is not None:
        for actor in list(getattr(persistent_level, "actors", []) or []):
            if actor is not None:
                yield actor

    actor_cls = getattr(unreal, "Actor", None)
    if actor_cls is not None:
        try:
            for actor in list(unreal.GameplayStatics.get_all_actors_of_class(world, actor_cls) or []):
                if actor is not None:
                    yield actor
        except Exception:
            pass


def _find_kamaz_actor(world):
    seen = set()
    for actor in _iter_world_actors(world):
        actor_path = _object_path(actor)
        if actor_path in seen:
            continue
        seen.add(actor_path)
        name = _object_name(actor)
        class_path = _object_path(actor.get_class()) if hasattr(actor, "get_class") else ""
        if "KamazBP" in name or "KamazBP" in class_path:
            return actor
    return None


def _find_plow_component(actor):
    if actor is None:
        return None
    for component in list(actor.get_components_by_class(unreal.ActorComponent) or []):
        component_name = _object_name(component)
        class_path = _object_path(component.get_class()) if hasattr(component, "get_class") else ""
        if "BP_PlowBrush_Component" in class_path or "PlowBrush" in component_name or "PlowBrush" in class_path:
            return component
    return None


def _get_mpc_vector_default(mpc_asset, parameter_name: str):
    vector_parameters = list(getattr(mpc_asset, "vector_parameters", []) or [])
    for entry in vector_parameters:
        entry_name = str(getattr(entry, "parameter_name", ""))
        if entry_name != parameter_name:
            continue
        value = getattr(entry, "default_value", None)
        if value is not None:
            return value
    raise RuntimeError(f"Missing vector parameter '{parameter_name}' on {_object_path(mpc_asset)}")


def _compute_brush_uv(world_location, bounds_min, bounds_max) -> dict:
    span_x = float(bounds_max.r) - float(bounds_min.r)
    span_y = float(bounds_max.g) - float(bounds_min.g)
    return {
        "u": (float(world_location.x) - float(bounds_min.r)) / span_x if span_x else 0.0,
        "v": (float(world_location.y) - float(bounds_min.g)) / span_y if span_y else 0.0,
    }


def _sample_rt_grid(world, render_target) -> dict:
    render_lib = unreal.RenderingLibrary
    max_r = 0.0
    max_g = 0.0
    max_b = 0.0
    non_black_samples = 0
    sample_count = 0
    for y_index in range(1, 16):
        for x_index in range(1, 16):
            u = float(x_index) / 16.0
            v = float(y_index) / 16.0
            sample = render_lib.read_render_target_raw_uv(world, render_target, u, v)
            sample_count += 1
            r = float(getattr(sample, "r", 0.0))
            g = float(getattr(sample, "g", 0.0))
            b = float(getattr(sample, "b", 0.0))
            max_r = max(max_r, r)
            max_g = max(max_g, g)
            max_b = max(max_b, b)
            if r > 0.0 or g > 0.0 or b > 0.0:
                non_black_samples += 1
    return {
        "sample_count": int(sample_count),
        "max_r": max_r,
        "max_g": max_g,
        "max_b": max_b,
        "non_black_samples": int(non_black_samples),
    }


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()

    world = _get_pie_world()
    render_target = _load_asset(RT_PATH)
    mpc_asset = _load_asset(MPC_PATH)
    kamaz_actor = _find_kamaz_actor(world)
    plow_component = _find_plow_component(kamaz_actor)

    bounds_min = _get_mpc_vector_default(mpc_asset, "WorldBoundsMin")
    bounds_max = _get_mpc_vector_default(mpc_asset, "WorldBoundsMax")

    render_lib = unreal.RenderingLibrary
    grid_stats = _sample_rt_grid(world, render_target)

    brush_uv = None
    brush_sample = None
    plow_component_location = None
    if plow_component is not None:
        try:
            plow_component_location = plow_component.get_world_location()
        except Exception:
            owner = kamaz_actor
            plow_component_location = owner.get_actor_location() if owner is not None else None

    if plow_component_location is not None:
        brush_uv = _compute_brush_uv(plow_component_location, bounds_min, bounds_max)
        sample = render_lib.read_render_target_raw_uv(world, render_target, float(brush_uv["u"]), float(brush_uv["v"]))
        brush_sample = _serialize_color(sample)

    payload = {
        "success": True,
        "pie_world_path": _object_path(world),
        "rt_path": _object_path(render_target),
        "kamaz_actor_name": _object_name(kamaz_actor),
        "kamaz_actor_path": _object_path(kamaz_actor),
        "plow_component_name": _object_name(plow_component),
        "plow_component_path": _object_path(plow_component),
        "plow_component_world_location": {
            "x": float(plow_component_location.x),
            "y": float(plow_component_location.y),
            "z": float(plow_component_location.z),
        } if plow_component_location is not None else None,
        "world_bounds_min": {"x": float(bounds_min.r), "y": float(bounds_min.g), "z": float(bounds_min.b)},
        "world_bounds_max": {"x": float(bounds_max.r), "y": float(bounds_max.g), "z": float(bounds_max.b)},
        "grid_stats": grid_stats,
        "brush_uv": brush_uv,
        "brush_uv_sample": brush_sample,
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, payload)
    payload["output_path"] = output_path
    return payload


def print_summary(output_dir: str | None = None):
    payload = run(output_dir)
    summary = (
        f"pie_rt non_black={payload['grid_stats']['non_black_samples']} "
        f"max_g={payload['grid_stats']['max_g']} "
        f"brush_uv_sample_g={(payload.get('brush_uv_sample') or {}).get('g', None)}"
    )
    _log(summary)
    _log(f"summary_path={payload['output_path']}")
    return {
        "success": payload.get("success", False),
        "summary": summary,
        "output_path": payload.get("output_path", ""),
    }


if __name__ == "__main__":
    print(print_summary())
