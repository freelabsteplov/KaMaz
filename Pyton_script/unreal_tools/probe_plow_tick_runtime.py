import json
import os
import time

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
KAMAZ_BP_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
TEST_ROAD_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
OUTPUT_BASENAME = "probe_plow_tick_runtime"
TICK_DELTAS = (0.016, 0.016, 0.016)


def _log(message: str) -> None:
    unreal.log(f"[probe_plow_tick_runtime] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _snow_tile_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "SnowState", "MoscowEA5")


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


def _serialize_value(value):
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, unreal.Name):
        return str(value)
    if isinstance(value, unreal.Vector):
        return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}
    if isinstance(value, unreal.Rotator):
        return {"pitch": float(value.pitch), "yaw": float(value.yaw), "roll": float(value.roll)}
    if isinstance(value, unreal.LinearColor):
        return {"r": float(value.r), "g": float(value.g), "b": float(value.b), "a": float(value.a)}
    path_name = _object_path(value)
    if path_name:
        return path_name
    try:
        return str(value)
    except Exception:
        return "<unserializable>"


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


def _set_property(obj, property_name: str, value):
    setter = getattr(obj, "set_editor_property", None)
    if callable(setter):
        try:
            setter(property_name, value)
            return True, ""
        except Exception as exc:
            return False, str(exc)
    try:
        setattr(obj, property_name, value)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _load_asset(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Could not load asset: {asset_path}")
    return asset


def _resolve_generated_class(blueprint):
    candidate = getattr(blueprint, "generated_class", None)
    if callable(candidate):
        try:
            candidate = candidate()
        except Exception:
            candidate = None
    if candidate is None:
        try:
            candidate = blueprint.get_editor_property("generated_class")
        except Exception:
            candidate = None
    if candidate is None:
        raise RuntimeError(f"Could not resolve generated class for {_object_path(blueprint)}")
    return candidate


def _get_editor_world():
    try:
        return unreal.EditorLevelLibrary.get_editor_world()
    except Exception:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        return subsystem.get_editor_world()


def _find_actor(actor_path: str):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        if _object_path(actor) == actor_path:
            return actor
    return None


def _get_actor_bounds(actor):
    origin, extent = actor.get_actor_bounds(True)
    return origin, extent


def _list_saved_tiles() -> list[dict]:
    tile_dir = _snow_tile_dir()
    if not os.path.isdir(tile_dir):
        return []

    result = []
    for file_name in sorted(os.listdir(tile_dir)):
        absolute_path = os.path.join(tile_dir, file_name)
        if not os.path.isfile(absolute_path):
            continue
        result.append(
            {
                "file_name": file_name,
                "absolute_path": absolute_path,
                "size_bytes": int(os.path.getsize(absolute_path)),
            }
        )
    return result


def _get_render_lib():
    render_lib = getattr(unreal, "RenderingLibrary", None)
    if render_lib is None:
        raise RuntimeError("unreal.RenderingLibrary is unavailable")
    return render_lib


def _clear_rt(world, render_target) -> None:
    _get_render_lib().clear_render_target2d(world, render_target, unreal.LinearColor(0.0, 0.0, 0.0, 0.0))


def _sample_rt_grid(world, render_target) -> dict:
    render_lib = _get_render_lib()
    max_r = 0.0
    max_g = 0.0
    max_b = 0.0
    non_black_samples = 0
    for y_index in range(1, 16):
        for x_index in range(1, 16):
            u = float(x_index) / 16.0
            v = float(y_index) / 16.0
            sample = render_lib.read_render_target_raw_uv(world, render_target, u, v)
            r = float(getattr(sample, "r", 0.0))
            g = float(getattr(sample, "g", 0.0))
            b = float(getattr(sample, "b", 0.0))
            max_r = max(max_r, r)
            max_g = max(max_g, g)
            max_b = max(max_b, b)
            if r > 0.0 or g > 0.0 or b > 0.0:
                non_black_samples += 1
    return {
        "max_r": max_r,
        "max_g": max_g,
        "max_b": max_b,
        "non_black_samples": int(non_black_samples),
    }


def _find_plow_component(actor):
    candidates = []
    for component in list(actor.get_components_by_class(unreal.ActorComponent) or []):
        class_path = _object_path(component.get_class())
        name = _object_name(component)
        if "BP_PlowBrush_Component" in class_path or "PlowBrush" in name or "PlowBrush" in class_path:
            candidates.append(component)
    preferred = [comp for comp in candidates if "BP_PlowBrush_Component" in _object_path(comp.get_class())]
    if preferred:
        return preferred[0], candidates
    if candidates:
        return candidates[0], candidates
    return None, []


def _try_call_method(obj, function_name: str, args=None) -> dict:
    result = {
        "function_name": function_name,
        "attempted": True,
        "called": False,
        "path": "call_method",
        "args": _serialize_value(args),
        "error": "",
        "return_value": None,
    }
    method = getattr(obj, "call_method", None)
    if not callable(method):
        result["attempted"] = False
        result["error"] = "Method is not exposed on this object."
        return result
    try:
        if args is None:
            return_value = method(function_name)
        else:
            return_value = method(function_name, args)
        result["called"] = True
        result["return_value"] = _serialize_value(return_value)
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _run_tick_sequence(component, world, render_target, function_name: str, deltas=TICK_DELTAS) -> list[dict]:
    attempts = []
    for index, delta_seconds in enumerate(deltas):
        attempt = _try_call_method(component, function_name, (float(delta_seconds),))
        attempt["tick_index"] = index
        attempt["delta_seconds"] = float(delta_seconds)
        time.sleep(0.03)
        attempt["rt_after_call"] = _sample_rt_grid(world, render_target)
        attempts.append(attempt)
    return attempts


def _try_call_by_name(obj, command_text: str) -> dict:
    result = {
        "command_text": command_text,
        "attempted": True,
        "called": False,
        "path": "call_function_by_name_with_arguments",
        "error": "",
        "return_value": None,
    }
    method = getattr(obj, "call_function_by_name_with_arguments", None)
    if not callable(method):
        result["attempted"] = False
        result["error"] = "Method is not exposed on this object."
        return result
    try:
        return_value = method(command_text)
        result["called"] = bool(return_value) or return_value is None
        result["return_value"] = _serialize_value(return_value)
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _collect_state(component) -> dict:
    state = {}
    for property_name in (
        "BrushMaterial",
        "RenderTargetGlobal",
        "MPCSnowSystem",
        "bEnablePlowClearing",
        "MinPlowSpeed",
        "UpdateRate",
        "PlowLiftHeight",
        "OwnerVehicle",
        "relative_location",
        "relative_rotation",
        "relative_scale3d",
    ):
        state[property_name] = _serialize_value(_safe_property(component, property_name))
    return state


def _serialize_dirty_rect(dirty_rect) -> dict:
    return {
        "min_x": int(getattr(dirty_rect, "min_x", 0)),
        "min_y": int(getattr(dirty_rect, "min_y", 0)),
        "max_x": int(getattr(dirty_rect, "max_x", 0)),
        "max_y": int(getattr(dirty_rect, "max_y", 0)),
        "is_valid": bool(
            getattr(
                dirty_rect,
                "b_is_valid",
                getattr(dirty_rect, "is_valid", False),
            )
        ),
    }


def _serialize_snow_snapshot(snapshot) -> dict:
    return {
        "cell_id": {
            "x": int(snapshot.cell_id.x),
            "y": int(snapshot.cell_id.y),
        },
        "is_dirty": bool(snapshot.is_dirty),
        "last_touched_time_seconds": float(snapshot.last_touched_time_seconds),
        "pending_write_count": int(snapshot.pending_write_count),
        "save_relative_path": str(snapshot.save_relative_path),
        "dominant_surface_family": str(snapshot.dominant_surface_family),
        "dirty_rect": _serialize_dirty_rect(snapshot.dirty_rect),
    }


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    world = _get_editor_world()
    road_actor = _find_actor(TEST_ROAD_ACTOR_PATH)
    if road_actor is None:
        raise RuntimeError(f"Could not find road actor: {TEST_ROAD_ACTOR_PATH}")
    road_origin, road_extent = _get_actor_bounds(road_actor)

    bp_asset = _load_asset(KAMAZ_BP_PATH)
    generated_class = _resolve_generated_class(bp_asset)
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    spawn_location = unreal.Vector(float(road_origin.x), float(road_origin.y), float(road_origin.z + road_extent.z + 300.0))
    spawned_actor = actor_subsystem.spawn_actor_from_class(generated_class, spawn_location, unreal.Rotator(0.0, 0.0, 0.0))
    if spawned_actor is None:
        raise RuntimeError("Failed to spawn Kamaz actor")

    try:
        plow_component, _ = _find_plow_component(spawned_actor)
        if plow_component is None:
            raise RuntimeError("Could not find plow component on spawned Kamaz")

        render_target = _load_asset(RT_PATH)
        _clear_rt(world, render_target)

        before_state = _collect_state(plow_component)
        before_rt = _sample_rt_grid(world, render_target)

        beginplay_result = _try_call_method(plow_component, "ReceiveBeginPlay")
        time.sleep(0.05)

        _clear_rt(world, render_target)
        tick_before_rt = _sample_rt_grid(world, render_target)

        tick_attempts = []
        tick_attempts.extend(_run_tick_sequence(plow_component, world, render_target, "ReceiveTick"))
        if all(not attempt.get("rt_after_call", {}).get("non_black_samples") for attempt in tick_attempts):
            tick_attempts.extend(_run_tick_sequence(plow_component, world, render_target, "K2_ReceiveTick"))
        tick_attempts.append(_try_call_by_name(plow_component, "ReceiveTick 0.016"))
        tick_attempts.append(_try_call_by_name(plow_component, "K2_ReceiveTick 0.016"))

        time.sleep(0.15)
        tick_after_rt = _sample_rt_grid(world, render_target)
        flushed_snapshots = [
            _serialize_snow_snapshot(snapshot)
            for snapshot in list(unreal.SnowStateBlueprintLibrary.flush_persistent_snow_state(spawned_actor) or [])
        ]
        tile_files_after_flush = _list_saved_tiles()

        result = {
            "success": True,
            "map_path": MAP_PATH,
            "spawned_actor_path": _object_path(spawned_actor),
            "plow_component_path": _object_path(plow_component),
            "before_state": before_state,
            "beginplay_result": beginplay_result,
            "setters": {
                "MinPlowSpeed_default_note": {
                    "success": True,
                    "error": "Runtime probe does not edit instance-only defaults; use apply_plow_debug_overdrive.py for debug default overrides."
                }
            },
            "after_beginplay_state": _collect_state(plow_component),
            "before_rt": before_rt,
            "tick_before_rt": tick_before_rt,
            "tick_attempts": tick_attempts,
            "tick_after_rt": tick_after_rt,
            "tick_rt_changed": tick_before_rt != tick_after_rt,
            "flushed_snapshots": flushed_snapshots,
            "tile_files_after_flush": tile_files_after_flush,
        }
    finally:
        actor_subsystem.destroy_actor(spawned_actor)

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary() -> str:
    result = run()
    summary = (
        f"plow_tick_runtime beginplay_called={result.get('beginplay_result', {}).get('called')} "
        f"tick_rt_changed={result.get('tick_rt_changed')} "
        f"non_black_before={result.get('tick_before_rt', {}).get('non_black_samples')} "
        f"non_black_after={result.get('tick_after_rt', {}).get('non_black_samples')}"
    )
    _log(summary)
    _log(f"summary_path={result.get('output_path', '')}")
    return summary


if __name__ == "__main__":
    print(run())
