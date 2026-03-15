import json
import os
import time

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
KAMAZ_BP_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
TEST_ROAD_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
MPC_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"
OUTPUT_BASENAME = "probe_spawned_plow_writer_runtime"


def _log(message: str) -> None:
    unreal.log(f"[probe_spawned_plow_writer_runtime] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[probe_spawned_plow_writer_runtime] {message}")


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
        return {
            "r": float(value.r),
            "g": float(value.g),
            "b": float(value.b),
            "a": float(value.a),
        }
    if isinstance(value, unreal.Array):
        return [_serialize_value(item) for item in value]
    path_name = _object_path(value)
    if path_name:
        return path_name
    try:
        return str(value)
    except Exception:
        return "<unserializable>"


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
    get_bounds = getattr(actor, "get_actor_bounds", None)
    if callable(get_bounds):
        try:
            origin, extent = get_bounds(True)
            return origin, extent
        except Exception:
            pass
    raise RuntimeError(f"Could not resolve bounds for actor: {_object_path(actor)}")


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


def _get_mpc_vector_default(mpc_asset, parameter_name: str):
    for entry in list(_safe_property(mpc_asset, "vector_parameters", []) or []):
        if str(_safe_property(entry, "parameter_name")) != parameter_name:
            continue
        value = _safe_property(entry, "default_value")
        if value is not None:
            return value
    return None


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


def _get_callable_names(obj) -> list[str]:
    names = []
    try:
        for name in dir(obj):
            lower = str(name).lower()
            if any(token in lower for token in ("plow", "brush", "draw", "snow", "clear", "call", "exec", "process")):
                names.append(str(name))
    except Exception:
        return []
    return sorted(set(names))


def _try_call(obj, function_name: str) -> dict:
    result = {
        "function_name": function_name,
        "attempted": False,
        "called": False,
        "error": "",
    }
    attr = getattr(obj, function_name, None)
    if not callable(attr):
        return result
    result["attempted"] = True
    try:
        attr()
        result["called"] = True
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _try_call_by_name_with_arguments(obj, function_name: str) -> list[dict]:
    results = []
    method = getattr(obj, "call_function_by_name_with_arguments", None)
    if not callable(method):
        results.append(
            {
                "function_name": function_name,
                "attempted": False,
                "called": False,
                "path": "call_function_by_name_with_arguments",
                "error": "Method is not exposed on this object.",
            }
        )
        return results

    output_device = None
    output_device_cls = getattr(unreal, "OutputDeviceNull", None)
    if output_device_cls is not None:
        try:
            output_device = output_device_cls()
        except Exception:
            output_device = None

    attempts = [
        ("cmd_only", (function_name,), {}),
        ("cmd_force", (function_name,), {"b_force_call_with_non_exec": True}),
        ("cmd_output_executor_force", (function_name, output_device, obj, True), {}),
        ("cmd_output_none_force", (function_name, output_device, None, True), {}),
        ("cmd_output_executor", (function_name, output_device, obj), {}),
        ("cmd_output_none", (function_name, output_device, None), {}),
        ("cmd_none_executor_force", (function_name, None, obj, True), {}),
        ("cmd_none_none_force", (function_name, None, None, True), {}),
    ]

    for label, args, kwargs in attempts:
        result = {
            "function_name": function_name,
            "attempted": True,
            "called": False,
            "path": f"call_function_by_name_with_arguments:{label}",
            "error": "",
        }
        try:
            return_value = method(*args, **kwargs)
            result["called"] = bool(return_value) or return_value is None
            result["return_value"] = _serialize_value(return_value)
        except Exception as exc:
            result["error"] = str(exc)
        results.append(result)
        if result["called"]:
            break

    return results


def _try_call_method(obj, function_name: str) -> list[dict]:
    results = []
    method = getattr(obj, "call_method", None)
    if not callable(method):
        results.append(
            {
                "function_name": function_name,
                "attempted": False,
                "called": False,
                "path": "call_method",
                "error": "Method is not exposed on this object.",
            }
        )
        return results

    attempts = [
        ("name_only", (function_name,), {}),
        ("name_args_empty_tuple", (function_name, ()), {}),
        ("name_args_empty_list", (function_name, []), {}),
        ("name_kwargs_empty_dict", (function_name,), {"kwargs": {}}),
    ]

    for label, args, kwargs in attempts:
        result = {
            "function_name": function_name,
            "attempted": True,
            "called": False,
            "path": f"call_method:{label}",
            "error": "",
        }
        try:
            return_value = method(*args, **kwargs)
            result["called"] = True
            result["return_value"] = _serialize_value(return_value)
        except Exception as exc:
            result["error"] = str(exc)
        results.append(result)
        if result["called"]:
            break

    return results


def _invoke_function_candidates(obj, function_names: tuple[str, ...]) -> list[dict]:
    all_results = []
    for function_name in function_names:
        direct_result = _try_call(obj, function_name)
        if direct_result["attempted"]:
            all_results.append(direct_result)
            if direct_result["called"]:
                break

        method_results = _try_call_method(obj, function_name)
        all_results.extend(method_results)
        if any(item.get("called") for item in method_results):
            break

        fallback_results = _try_call_by_name_with_arguments(obj, function_name)
        all_results.extend(fallback_results)
        if any(item.get("called") for item in fallback_results):
            break

    return all_results


def _collect_component_state(component) -> dict:
    state = {
        "name": _object_name(component),
        "path": _object_path(component),
        "class": _object_path(component.get_class()),
        "callable_candidates": _get_callable_names(component),
    }
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

    for method_name, output_name in (
        ("get_component_location", "world_location"),
        ("get_component_rotation", "world_rotation"),
        ("get_component_scale", "world_scale"),
    ):
        method = getattr(component, method_name, None)
        if callable(method):
            try:
                state[output_name] = _serialize_value(method())
            except Exception as exc:
                state[output_name] = f"<error: {exc}>"
        else:
            state[output_name] = None
    return state


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
    spawned_actor = actor_subsystem.spawn_actor_from_class(
        generated_class,
        spawn_location,
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    if spawned_actor is None:
        raise RuntimeError("Failed to spawn Kamaz actor")

    try:
        plow_component, all_candidates = _find_plow_component(spawned_actor)
        if plow_component is None:
            raise RuntimeError("Could not find runtime plow component on spawned Kamaz")

        render_target = _load_asset(RT_PATH)
        mpc_asset = _load_asset(MPC_PATH)
        _clear_rt(world, render_target)

        owner_vehicle_before_beginplay = _serialize_value(_safe_property(plow_component, "OwnerVehicle"))
        beginplay_call_results = _invoke_function_candidates(
            plow_component,
            (
                "ReceiveBeginPlay",
                "K2_ReceiveBeginPlay",
                "BeginPlay",
            ),
        )
        time.sleep(0.05)
        owner_vehicle_after_beginplay = _serialize_value(_safe_property(plow_component, "OwnerVehicle"))

        before_brush_uv = _serialize_value(_get_mpc_vector_default(mpc_asset, "BrushUV"))
        before_rt_stats = _sample_rt_grid(world, render_target)

        call_results = _invoke_function_candidates(
            plow_component,
            (
            "DrawPlowClearance",
            "draw_plow_clearance",
            "K2_DrawPlowClearance",
            "k2_draw_plow_clearance",
            ),
        )
        if not call_results:
            call_results.append(
                {
                    "function_name": "",
                    "attempted": False,
                    "called": False,
                    "error": "No callable DrawPlowClearance-style method found on component.",
                }
            )

        # Give the world a brief moment so the RT write can settle before sampling.
        time.sleep(0.15)

        after_brush_uv = _serialize_value(_get_mpc_vector_default(mpc_asset, "BrushUV"))
        after_rt_stats = _sample_rt_grid(world, render_target)

        result = {
            "success": True,
            "map_path": MAP_PATH,
            "kamaz_blueprint_path": KAMAZ_BP_PATH,
            "spawned_actor_path": _object_path(spawned_actor),
            "spawned_actor_name": _object_name(spawned_actor),
            "spawn_location": _serialize_value(spawn_location),
            "test_road_actor_path": TEST_ROAD_ACTOR_PATH,
            "test_road_origin": _serialize_value(road_origin),
            "test_road_extent": _serialize_value(road_extent),
            "owner_vehicle_before_beginplay": owner_vehicle_before_beginplay,
            "owner_vehicle_after_beginplay": owner_vehicle_after_beginplay,
            "beginplay_call_results": beginplay_call_results,
            "plow_component_state": _collect_component_state(plow_component),
            "all_plowish_candidates": [_collect_component_state(candidate) for candidate in all_candidates],
            "draw_call_results": call_results,
            "brush_uv_before": before_brush_uv,
            "brush_uv_after": after_brush_uv,
            "rt_stats_before": before_rt_stats,
            "rt_stats_after": after_rt_stats,
            "rt_changed": before_rt_stats != after_rt_stats,
        }
    finally:
        actor_subsystem.destroy_actor(spawned_actor)

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary() -> str:
    result = run()
    first_call = result.get("draw_call_results", [{}])[0]
    summary = (
        f"runtime_plow_writer called={first_call.get('called')} "
        f"rt_changed={result.get('rt_changed')} "
        f"non_black_before={result.get('rt_stats_before', {}).get('non_black_samples')} "
        f"non_black_after={result.get('rt_stats_after', {}).get('non_black_samples')}"
    )
    _log(summary)
    _log(f"summary_path={result.get('output_path', '')}")
    return summary


if __name__ == "__main__":
    print(run())
