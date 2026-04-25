import json
import math
import os
import time

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
EXPECTED_PLAYER_CONTROLLER = "/Game/BPs/BP_KamazPlayerController.BP_KamazPlayerController_C"
EXPECTED_PAWN_CLASS_SUFFIX = "KamazBP_C"
EXPECTED_CLUSTER_WIDGET_CLASS = "/Game/CityPark/Kamaz/UI/WBP_KamazCluster.WBP_KamazCluster_C"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "check_kamaz_startup_runtime_pie.json",
)


STATE = {
    "callback_handle": None,
    "phase": "init",
    "requested_begin_play": False,
    "requested_end_play": False,
    "finished": False,
    "phase_started_at": time.time(),
    "payload": {
        "map_path": MAP_PATH,
        "begin_play_request": {},
        "pie_world_path": "",
        "player_controller_path": "",
        "player_controller_class": "",
        "pawn_path": "",
        "pawn_class": "",
        "pawn_initial_location": None,
        "pawn_initial_rotation": None,
        "pawn_settled_location": None,
        "ground_probe_initial": {},
        "ground_probe_after_settle": {},
        "runtime_widget": {},
        "simulating_component_path": "",
        "movement_probe": {},
        "controller_matches_expected": False,
        "pawn_matches_expected": False,
        "spawn_on_ground": False,
        "physics_present": False,
        "cluster_widget_present": False,
        "hud_present": False,
        "movement_present": False,
        "error": "",
    },
}


def _log(message: str) -> None:
    unreal.log(f"[check_kamaz_startup_runtime_pie] {message}")


def _safe_path(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _safe_name(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _safe_prop(obj, prop_name: str, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(prop_name)
        except Exception:
            pass
    try:
        return getattr(obj, prop_name)
    except Exception:
        return default


def _vec_dict(vec):
    if vec is None:
        return None
    return {
        "x": float(vec.x),
        "y": float(vec.y),
        "z": float(vec.z),
    }


def _rot_dict(rot):
    if rot is None:
        return None
    return {
        "pitch": float(rot.pitch),
        "yaw": float(rot.yaw),
        "roll": float(rot.roll),
    }


def _write_json(payload: dict) -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {OUTPUT_PATH}")


def _call_first(obj, names: list[str], *args):
    attempts = []
    for name in names:
        fn = getattr(obj, name, None)
        if not callable(fn):
            attempts.append({"name": name, "available": False, "error": ""})
            continue
        try:
            value = fn(*args)
            return {
                "success": True,
                "name": name,
                "value": value,
                "attempts": attempts,
            }
        except Exception as exc:
            attempts.append({"name": name, "available": True, "error": str(exc)})
    return {
        "success": False,
        "name": "",
        "value": None,
        "attempts": attempts,
    }


def _get_level_editor_subsystem():
    return unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def _request_begin_play():
    subsystem = _get_level_editor_subsystem()
    return _call_first(
        subsystem,
        ["editor_request_begin_play", "editor_request_begin_play_session"],
    )


def _request_end_play():
    subsystem = _get_level_editor_subsystem()
    return _call_first(
        subsystem,
        ["editor_request_end_play", "editor_request_end_play_map"],
    )


def _is_in_pie() -> bool:
    subsystem = _get_level_editor_subsystem()
    result = _call_first(subsystem, ["is_in_play_in_editor"])
    return bool(result.get("value")) if result.get("success") else False


def _get_pie_world():
    try:
        worlds = list(unreal.EditorLevelLibrary.get_pie_worlds(False) or [])
    except Exception:
        worlds = []
    for world in worlds:
        if world is not None:
            return world

    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        world = subsystem.get_game_world()
        if world is not None:
            return world
    except Exception:
        pass

    try:
        world = unreal.EditorLevelLibrary.get_game_world()
        if world is not None:
            return world
    except Exception:
        pass

    return None


def _get_controller_and_pawn(world):
    try:
        controller = unreal.GameplayStatics.get_player_controller(world, 0)
    except Exception:
        controller = None
    try:
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
    except Exception:
        pawn = None
    return controller, pawn


def _load_widget_class():
    try:
        widget_class = unreal.load_class(None, EXPECTED_CLUSTER_WIDGET_CLASS)
        if widget_class is not None:
            return widget_class
    except Exception:
        pass
    try:
        return unreal.EditorAssetLibrary.load_blueprint_class(
            "/Game/CityPark/Kamaz/UI/WBP_KamazCluster"
        )
    except Exception:
        return None


def _get_cluster_widgets(world, widget_class):
    widget_lib = getattr(unreal, "WidgetBlueprintLibrary", None)
    if widget_lib is None or widget_class is None:
        return [], {"available": widget_lib is not None, "attempts": []}

    attempts = []
    for top_level_only in (True, False):
        try:
            widgets = widget_lib.get_all_widgets_of_class(world, widget_class, top_level_only)
            return list(widgets or []), {
                "available": True,
                "attempts": attempts,
                "call": f"get_all_widgets_of_class(top_level_only={top_level_only})",
            }
        except Exception as exc:
            attempts.append(
                {
                    "call": f"get_all_widgets_of_class(top_level_only={top_level_only})",
                    "error": str(exc),
                }
            )
    return [], {"available": True, "attempts": attempts}


def _find_vehicle_movement_component(actor):
    if actor is None:
        return None
    for component in list(actor.get_components_by_class(unreal.ActorComponent) or []):
        class_path = _safe_path(component.get_class())
        if "ChaosWheeledVehicleMovementComponent" in class_path or "ChaosVehicleMovementComponent" in class_path:
            return component
    return None


def _find_simulating_component(actor):
    if actor is None:
        return None
    for component in list(actor.get_components_by_class(unreal.PrimitiveComponent) or []):
        is_simulating = getattr(component, "is_simulating_physics", None)
        if callable(is_simulating):
            try:
                if is_simulating():
                    return component
            except Exception:
                continue
    return None


def _trace_ground_distance(world, location, ignore_actors):
    start = location + unreal.Vector(0.0, 0.0, 500.0)
    end = location - unreal.Vector(0.0, 0.0, 5000.0)
    trace_result = unreal.SystemLibrary.line_trace_single(
        world,
        start,
        end,
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
        False,
        ignore_actors,
        unreal.DrawDebugTrace.NONE,
        False,
        unreal.LinearColor(1.0, 0.0, 0.0, 1.0),
        unreal.LinearColor(0.0, 1.0, 0.0, 1.0),
        0.0,
    )
    if isinstance(trace_result, tuple):
        hit = trace_result[1] if len(trace_result) > 1 else None
    else:
        hit = trace_result

    if hit is None or not hit.is_valid_blocking_hit():
        return {
            "has_hit": False,
            "distance_to_ground": None,
            "hit_actor_path": "",
            "hit_location": None,
        }

    hit_location = hit.location
    distance = math.sqrt(
        ((float(location.x) - float(hit_location.x)) ** 2)
        + ((float(location.y) - float(hit_location.y)) ** 2)
        + ((float(location.z) - float(hit_location.z)) ** 2)
    )
    return {
        "has_hit": True,
        "distance_to_ground": float(distance),
        "hit_actor_path": _safe_path(hit.get_actor()),
        "hit_location": _vec_dict(hit_location),
    }


def _distance_xy(a, b) -> float:
    return math.sqrt(
        ((float(a.x) - float(b.x)) ** 2)
        + ((float(a.y) - float(b.y)) ** 2)
    )


def _runtime_widget_info(controller, world):
    widget_class = _load_widget_class()
    widgets, widget_query = _get_cluster_widgets(world, widget_class)
    cluster_widget = _safe_prop(controller, "ClusterWidget", None)
    cluster_widget_class = _safe_prop(controller, "ClusterWidgetClass", None)
    get_hud = getattr(controller, "get_hud", None)
    hud = get_hud() if callable(get_hud) else None
    return {
        "cluster_widget_property_path": _safe_path(cluster_widget),
        "cluster_widget_property_name": _safe_name(cluster_widget),
        "cluster_widget_class_property_path": _safe_path(cluster_widget_class),
        "cluster_widget_class_expected": EXPECTED_CLUSTER_WIDGET_CLASS,
        "cluster_widget_count": len(widgets),
        "cluster_widget_paths": [_safe_path(widget) for widget in widgets],
        "widget_query": widget_query,
        "hud_path": _safe_path(hud),
        "hud_name": _safe_name(hud),
        "hud_present": hud is not None,
        "cluster_widget_present": bool(cluster_widget) or bool(widgets),
    }


def _capture_runtime_snapshot(world):
    payload = STATE["payload"]
    controller, pawn = _get_controller_and_pawn(world)
    payload["pie_world_path"] = _safe_path(world)
    payload["player_controller_path"] = _safe_path(controller)
    payload["player_controller_class"] = _safe_path(controller.get_class()) if controller else ""
    payload["pawn_path"] = _safe_path(pawn)
    payload["pawn_class"] = _safe_path(pawn.get_class()) if pawn else ""
    payload["controller_matches_expected"] = payload["player_controller_class"] == EXPECTED_PLAYER_CONTROLLER
    payload["pawn_matches_expected"] = payload["pawn_class"].endswith(EXPECTED_PAWN_CLASS_SUFFIX)

    if pawn is None:
        return controller, pawn

    if payload["pawn_initial_location"] is None:
        payload["pawn_initial_location"] = _vec_dict(pawn.get_actor_location())
        payload["pawn_initial_rotation"] = _rot_dict(pawn.get_actor_rotation())
        payload["ground_probe_initial"] = _trace_ground_distance(world, pawn.get_actor_location(), [pawn])

    settled_location = pawn.get_actor_location()
    payload["pawn_settled_location"] = _vec_dict(settled_location)
    payload["ground_probe_after_settle"] = _trace_ground_distance(world, settled_location, [pawn])

    simulating_component = _find_simulating_component(pawn)
    payload["simulating_component_path"] = _safe_path(simulating_component)
    payload["physics_present"] = simulating_component is not None

    if controller is not None:
        payload["runtime_widget"] = _runtime_widget_info(controller, world)
        payload["cluster_widget_present"] = bool(payload["runtime_widget"].get("cluster_widget_present"))
        payload["hud_present"] = bool(payload["runtime_widget"].get("hud_present"))

    ground_distance = payload["ground_probe_after_settle"].get("distance_to_ground")
    payload["spawn_on_ground"] = bool(
        payload["ground_probe_after_settle"].get("has_hit") and ground_distance is not None and ground_distance < 400.0
    )
    return controller, pawn


def _finish(error: str = ""):
    if STATE["finished"]:
        return
    STATE["finished"] = True
    if error:
        STATE["payload"]["error"] = error
        _log(f"ERROR: {error}")

    handle = STATE.get("callback_handle")
    if handle is not None:
        try:
            unreal.unregister_slate_post_tick_callback(handle)
        except Exception:
            pass
        STATE["callback_handle"] = None

    _write_json(STATE["payload"])
    print(OUTPUT_PATH)

    try:
        unreal.SystemLibrary.execute_console_command(None, "QUIT_EDITOR")
    except Exception:
        try:
            unreal.SystemLibrary.quit_editor()
        except Exception:
            pass


def _enter_phase(name: str):
    STATE["phase"] = name
    STATE["phase_started_at"] = time.time()
    _log(f"phase={name}")


def _tick(_delta_time: float):
    if STATE["finished"]:
        return

    now = time.time()
    phase = STATE["phase"]

    try:
        if phase == "init":
            unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
            STATE["payload"]["begin_play_request"] = _request_begin_play()
            STATE["requested_begin_play"] = True
            _enter_phase("wait_for_pie")
            return

        if phase == "wait_for_pie":
            world = _get_pie_world()
            if world is not None and _is_in_pie():
                _enter_phase("wait_for_pawn")
                return
            if (now - STATE["phase_started_at"]) > 45.0:
                _finish("PIE world did not start")
            return

        if phase == "wait_for_pawn":
            world = _get_pie_world()
            if world is None:
                return
            _capture_runtime_snapshot(world)
            if STATE["payload"]["pawn_path"]:
                _enter_phase("settle")
                return
            if (now - STATE["phase_started_at"]) > 15.0:
                _finish("No possessed Kamaz pawn found in PIE")
            return

        if phase == "settle":
            world = _get_pie_world()
            if world is None:
                _finish("PIE world ended before settle phase completed")
                return
            _, pawn = _capture_runtime_snapshot(world)
            if pawn is None:
                _finish("Pawn disappeared during settle phase")
                return
            if (now - STATE["phase_started_at"]) < 1.5:
                return

            movement_component = _find_vehicle_movement_component(pawn)
            if movement_component is None:
                STATE["payload"]["movement_probe"] = {
                    "movement_component_path": "",
                    "probe_method": "",
                    "moved_distance_xy": 0.0,
                    "before_location": None,
                    "after_location": None,
                    "success": False,
                    "error": "Chaos vehicle movement component not found",
                }
                _enter_phase("end_pie")
                return

            before_location = pawn.get_actor_location()
            STATE["payload"]["movement_probe"] = {
                "movement_component_path": _safe_path(movement_component),
                "probe_method": "vehicle_movement.set_throttle_input",
                "moved_distance_xy": 0.0,
                "before_location": _vec_dict(before_location),
                "after_location": None,
                "success": False,
                "error": "",
            }
            try:
                if hasattr(movement_component, "set_handbrake_input"):
                    movement_component.set_handbrake_input(False)
                if hasattr(movement_component, "set_brake_input"):
                    movement_component.set_brake_input(0.0)
                if hasattr(movement_component, "set_throttle_input"):
                    movement_component.set_throttle_input(1.0)
                else:
                    STATE["payload"]["movement_probe"]["error"] = "set_throttle_input is unavailable"
                    _enter_phase("end_pie")
                    return
            except Exception as exc:
                STATE["payload"]["movement_probe"]["error"] = str(exc)
                _enter_phase("end_pie")
                return

            _enter_phase("drive")
            return

        if phase == "drive":
            world = _get_pie_world()
            if world is None:
                _finish("PIE world ended during drive phase")
                return
            _, pawn = _capture_runtime_snapshot(world)
            if pawn is None:
                _finish("Pawn disappeared during drive phase")
                return
            if (now - STATE["phase_started_at"]) < 1.25:
                return

            movement_component = _find_vehicle_movement_component(pawn)
            if movement_component is not None and hasattr(movement_component, "set_throttle_input"):
                try:
                    movement_component.set_throttle_input(0.0)
                except Exception:
                    pass

            after_location = pawn.get_actor_location()
            before_dict = STATE["payload"]["movement_probe"].get("before_location") or {}
            before_location = unreal.Vector(
                float(before_dict.get("x", after_location.x)),
                float(before_dict.get("y", after_location.y)),
                float(before_dict.get("z", after_location.z)),
            )
            moved_distance_xy = _distance_xy(before_location, after_location)
            STATE["payload"]["movement_probe"]["after_location"] = _vec_dict(after_location)
            STATE["payload"]["movement_probe"]["moved_distance_xy"] = float(moved_distance_xy)
            STATE["payload"]["movement_probe"]["success"] = moved_distance_xy > 25.0
            STATE["payload"]["movement_present"] = bool(STATE["payload"]["movement_probe"]["success"])
            _enter_phase("end_pie")
            return

        if phase == "end_pie":
            if not STATE["requested_end_play"] and _is_in_pie():
                _request_end_play()
                STATE["requested_end_play"] = True
                return
            if not _is_in_pie():
                _finish()
                return
            if (now - STATE["phase_started_at"]) > 10.0:
                _finish("PIE did not shut down cleanly after runtime probe")
            return

        _finish(f"Unexpected phase: {phase}")

    except Exception as exc:
        _finish(str(exc))


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    register = getattr(unreal, "register_slate_post_tick_callback", None)
    if not callable(register):
        _finish("register_slate_post_tick_callback is unavailable")
        return

    STATE["callback_handle"] = register(_tick)
    _log(f"registered_callback={STATE['callback_handle']}")


if __name__ == "__main__":
    main()
