import json
import os
import time

import unreal


MAP_PATH = "/Game/LandscapeDeformation/Maps/SnowMap"
HELPER_CLASS_PATH = "/Script/Kamaz_Cleaner.SnowMapKamazPlowCaptureDeformerActor"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "tmp_inspect_snowmap_kamaz_cosmetics_runtime.json",
)

STATE = {
    "callback_handle": None,
    "phase": "init",
    "phase_started_at": time.time(),
    "requested_end_play": False,
    "finished": False,
    "payload": {
        "map_path": MAP_PATH,
        "pie_world_path": "",
        "pawn_path": "",
        "pawn_class": "",
        "pawn_location": None,
        "pawn_rotation": None,
        "ground_under_pawn": None,
        "vehicle_mesh_path": "",
        "vehicle_mesh_location": None,
        "vehicle_mesh_bounds_origin": None,
        "vehicle_mesh_bounds_extent": None,
        "bone_samples": {},
        "helper_actor_path": "",
        "helper_actor_location": None,
        "helper_actor_rotation": None,
        "helper_components": {},
        "error": "",
    },
}

WHEEL_BONE_CANDIDATES = [
    "WFL",
    "WFR",
    "WRL",
    "WRR",
    "Wheel_FL",
    "Wheel_FR",
    "Wheel_RL",
    "Wheel_RR",
]

HELPER_COMPONENT_NAMES = [
    "PlowDeformerMesh",
    "FrontLeftWheelDeformerMesh",
    "FrontRightWheelDeformerMesh",
    "RearLeftWheelDeformerMesh",
    "RearRightWheelDeformerMesh",
]


def _log(message: str) -> None:
    unreal.log(f"[tmp_inspect_snowmap_kamaz_cosmetics_runtime] {message}")


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


def _vec_dict(vec):
    if vec is None:
        return None
    return {"x": float(vec.x), "y": float(vec.y), "z": float(vec.z)}


def _rot_dict(rot):
    if rot is None:
        return None
    return {"pitch": float(rot.pitch), "yaw": float(rot.yaw), "roll": float(rot.roll)}


def _bounds_dict(bounds):
    if bounds is None:
        return None
    return {
        "origin": _vec_dict(bounds.origin),
        "box_extent": _vec_dict(bounds.box_extent),
        "sphere_radius": float(bounds.sphere_radius),
    }


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


def _write_json(payload):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _call_first(obj, names, *args):
    for name in names:
        fn = getattr(obj, name, None)
        if not callable(fn):
            continue
        try:
            return True, fn(*args)
        except Exception:
            continue
    return False, None


def _request_begin_play():
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    return _call_first(subsystem, ["editor_request_begin_play", "editor_request_begin_play_session"])[0]


def _request_end_play():
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    return _call_first(subsystem, ["editor_request_end_play", "editor_request_end_play_map"])[0]


def _is_in_pie():
    subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    ok, value = _call_first(subsystem, ["is_in_play_in_editor"])
    return bool(value) if ok else False


def _get_pie_world():
    try:
        worlds = list(unreal.EditorLevelLibrary.get_pie_worlds(False) or [])
        if worlds:
            return worlds[0]
    except Exception:
        pass
    return None


def _find_helper_actor(world):
    helper_class = unreal.load_class(None, HELPER_CLASS_PATH)
    if helper_class is None:
        return None
    try:
        actors = list(unreal.GameplayStatics.get_all_actors_of_class(world, helper_class) or [])
        if actors:
            return actors[0]
    except Exception:
        pass
    return None


def _get_player_pawn(world):
    try:
        return unreal.GameplayStatics.get_player_pawn(world, 0)
    except Exception:
        return None


def _line_trace(world, start, end, ignored_actor=None):
    system_lib = unreal.SystemLibrary
    trace_color = unreal.LinearColor(1.0, 0.0, 0.0, 1.0)
    trace_hit_color = unreal.LinearColor(0.0, 1.0, 0.0, 1.0)
    actors_to_ignore = [ignored_actor] if ignored_actor else []
    try:
        hit = system_lib.line_trace_single(
            world,
            start,
            end,
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
            False,
            actors_to_ignore,
            unreal.DrawDebugTrace.NONE,
            True,
            trace_color,
            trace_hit_color,
            0.0,
        )
        if isinstance(hit, tuple) and len(hit) >= 2:
            return bool(hit[0]), hit[1]
    except Exception:
        pass
    return False, None


def _capture_snapshot(world):
    payload = STATE["payload"]
    pawn = _get_player_pawn(world)
    helper = _find_helper_actor(world)
    payload["pie_world_path"] = _safe_path(world)
    payload["pawn_path"] = _safe_path(pawn)
    payload["pawn_class"] = _safe_path(pawn.get_class()) if pawn else ""
    payload["pawn_location"] = _vec_dict(pawn.get_actor_location()) if pawn else None
    payload["pawn_rotation"] = _rot_dict(pawn.get_actor_rotation()) if pawn else None

    if pawn:
        start = pawn.get_actor_location() + unreal.Vector(0.0, 0.0, 200.0)
        end = pawn.get_actor_location() - unreal.Vector(0.0, 0.0, 500.0)
        hit_ok, hit = _line_trace(world, start, end, pawn)
        if hit_ok and hit:
            payload["ground_under_pawn"] = {
                "location": _vec_dict(hit.to_tuple()[4] if False else hit.location),
                "normal": _vec_dict(hit.normal),
            }

        vehicle_mesh = pawn.find_component_by_class(unreal.SkeletalMeshComponent)
        payload["vehicle_mesh_path"] = _safe_path(vehicle_mesh)
        if vehicle_mesh:
            payload["vehicle_mesh_location"] = _vec_dict(vehicle_mesh.get_world_location())
            bounds = vehicle_mesh.bounds
            payload["vehicle_mesh_bounds_origin"] = _vec_dict(bounds.origin)
            payload["vehicle_mesh_bounds_extent"] = _vec_dict(bounds.box_extent)

            for bone_name in WHEEL_BONE_CANDIDATES:
                try:
                    bone_index = vehicle_mesh.get_bone_index(unreal.Name(bone_name))
                except Exception:
                    bone_index = -1

                if bone_index is None or int(bone_index) < 0:
                    continue

                bone_location = None
                try:
                    bone_location = vehicle_mesh.get_socket_location(bone_name)
                except Exception:
                    bone_location = None
                if bone_location is None:
                    try:
                        bone_location = vehicle_mesh.get_bone_location_by_name(
                            bone_name,
                            unreal.BoneSpaces.WORLD_SPACE,
                        )
                    except Exception:
                        bone_location = None
                if bone_location is None:
                    try:
                        bone_location = vehicle_mesh.get_bone_location(unreal.Name(bone_name))
                    except Exception:
                        bone_location = None
                if bone_location is None:
                    continue

                start = bone_location + unreal.Vector(0.0, 0.0, 60.0)
                end = bone_location - unreal.Vector(0.0, 0.0, 260.0)
                hit_ok, hit = _line_trace(world, start, end, pawn)
                payload["bone_samples"][bone_name] = {
                    "bone_index": int(bone_index),
                    "bone_location": _vec_dict(bone_location),
                    "ground_hit": _vec_dict(hit.location) if hit_ok and hit else None,
                    "ground_distance_z": float(bone_location.z - hit.location.z) if hit_ok and hit else None,
                }

    payload["helper_actor_path"] = _safe_path(helper)
    payload["helper_actor_location"] = _vec_dict(helper.get_actor_location()) if helper else None
    payload["helper_actor_rotation"] = _rot_dict(helper.get_actor_rotation()) if helper else None
    if helper:
        components = list(helper.get_components_by_class(unreal.StaticMeshComponent) or [])
        by_name = {_safe_name(component): component for component in components}
        for name in HELPER_COMPONENT_NAMES:
            component = by_name.get(name)
            world_scale = None
            if component:
                get_world_scale = getattr(component, "get_component_scale", None)
                if callable(get_world_scale):
                    try:
                        world_scale = get_world_scale()
                    except Exception:
                        world_scale = None
                if world_scale is None:
                    try:
                        world_scale = component.get_world_scale()
                    except Exception:
                        world_scale = None
            payload["helper_components"][name] = {
                "path": _safe_path(component),
                "visible": bool(component.is_visible()) if component and hasattr(component, "is_visible") else False,
                "world_location": _vec_dict(component.get_world_location()) if component else None,
                "world_rotation": _rot_dict(component.get_world_rotation()) if component else None,
                "world_scale": _vec_dict(world_scale),
            }


def _finish(error=""):
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
        pass


def _enter_phase(name):
    STATE["phase"] = name
    STATE["phase_started_at"] = time.time()
    _log(f"phase={name}")


def _tick(_delta_time):
    if STATE["finished"]:
        return

    now = time.time()
    phase = STATE["phase"]

    try:
        if phase == "init":
            unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
            if not _request_begin_play():
                _finish("Could not request PIE begin play")
                return
            _enter_phase("wait_for_pie")
            return

        if phase == "wait_for_pie":
            world = _get_pie_world()
            if world is not None and _is_in_pie():
                _enter_phase("capture")
                return
            if (now - STATE["phase_started_at"]) > 45.0:
                _finish("PIE world did not start")
            return

        if phase == "capture":
            world = _get_pie_world()
            if world is None:
                _finish("PIE world disappeared before capture")
                return
            if (now - STATE["phase_started_at"]) < 1.5:
                return
            _capture_snapshot(world)
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
                _finish("PIE did not shut down cleanly")
            return

        _finish(f"Unexpected phase: {phase}")
    except Exception as exc:
        _finish(str(exc))


def main():
    register = getattr(unreal, "register_slate_post_tick_callback", None)
    if not callable(register):
        _finish("register_slate_post_tick_callback is unavailable")
        return
    STATE["callback_handle"] = register(_tick)
    _log(f"registered_callback={STATE['callback_handle']}")


if __name__ == "__main__":
    main()
