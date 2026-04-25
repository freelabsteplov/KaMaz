import json
import os
import time

import unreal


MAP_PATH = "/Game/LandscapeDeformation/Maps/SnowMap"
HELPER_CLASS_PATH = "/Script/Kamaz_Cleaner.SnowMapKamazPlowCaptureDeformerActor"
RT_PATH = "/Game/LandscapeDeformation/Textures/RenderTargets/RT_Persistent"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "validate_snowmap_kamaz_plow_capture_runtime.json",
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
        "helper_actor_path": "",
        "helper_actor_class": "",
        "helper_attach_parent_path": "",
        "helper_attach_parent_name": "",
        "helper_mesh_path": "",
        "helper_mesh_flags": {},
        "driver_probe_skipped": True,
        "movement_distance_xy": 0.0,
        "rt_before_drive": {},
        "rt_after_drive": {},
        "rt_changed": False,
        "error": "",
    },
}


def _log(message: str) -> None:
    unreal.log(f"[validate_snowmap_kamaz_plow_capture_runtime] {message}")


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
    return {"x": float(vec.x), "y": float(vec.y), "z": float(vec.z)}


def _write_json(payload: dict) -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {OUTPUT_PATH}")


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


def _get_level_editor_subsystem():
    return unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def _request_begin_play():
    subsystem = _get_level_editor_subsystem()
    return _call_first(subsystem, ["editor_request_begin_play", "editor_request_begin_play_session"])[0]


def _request_end_play():
    subsystem = _get_level_editor_subsystem()
    return _call_first(subsystem, ["editor_request_end_play", "editor_request_end_play_map"])[0]


def _is_in_pie() -> bool:
    subsystem = _get_level_editor_subsystem()
    ok, value = _call_first(subsystem, ["is_in_play_in_editor"])
    return bool(value) if ok else False


def _get_pie_world():
    try:
        worlds = list(unreal.EditorLevelLibrary.get_pie_worlds(False) or [])
        if worlds:
            return worlds[0]
    except Exception:
        pass

    try:
        world = unreal.EditorLevelLibrary.get_game_world()
        if world is not None:
            return world
    except Exception:
        pass

    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        world = subsystem.get_game_world()
        if world is not None:
            return world
    except Exception:
        pass

    return None


def _load_asset(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None and "." in asset_path:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path.rsplit(".", 1)[0])
    return asset


def _clear_rt(editor_world, render_target):
    unreal.RenderingLibrary.clear_render_target2d(
        editor_world,
        render_target,
        unreal.LinearColor(0.0, 0.0, 0.0, 1.0),
    )


def _sample_rt_grid(world, render_target):
    sample_count = 0
    non_black_samples = 0
    max_r = 0.0
    max_g = 0.0
    max_b = 0.0
    total_r = 0.0
    total_g = 0.0
    total_b = 0.0
    for y_index in range(1, 17):
        for x_index in range(1, 17):
            u = float(x_index) / 17.0
            v = float(y_index) / 17.0
            sample = unreal.RenderingLibrary.read_render_target_raw_uv(world, render_target, u, v)
            r = float(getattr(sample, "r", 0.0))
            g = float(getattr(sample, "g", 0.0))
            b = float(getattr(sample, "b", 0.0))
            sample_count += 1
            max_r = max(max_r, r)
            max_g = max(max_g, g)
            max_b = max(max_b, b)
            total_r += r
            total_g += g
            total_b += b
            if r > 0.0 or g > 0.0 or b > 0.0:
                non_black_samples += 1
    return {
        "sample_count": int(sample_count),
        "non_black_samples": int(non_black_samples),
        "max_r": max_r,
        "max_g": max_g,
        "max_b": max_b,
        "sum_r": total_r,
        "sum_g": total_g,
        "sum_b": total_b,
    }


def _get_player_pawn(world):
    try:
        return unreal.GameplayStatics.get_player_pawn(world, 0)
    except Exception:
        return None


def _find_vehicle_movement_component(actor):
    if actor is None:
        return None
    for component in list(actor.get_components_by_class(unreal.ActorComponent) or []):
        class_path = _safe_path(component.get_class())
        if "ChaosWheeledVehicleMovementComponent" in class_path or "ChaosVehicleMovementComponent" in class_path:
            return component
    return None


def _distance_xy(a, b) -> float:
    return (((float(a.x) - float(b.x)) ** 2) + ((float(a.y) - float(b.y)) ** 2)) ** 0.5


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


def _capture_runtime_snapshot(world):
    payload = STATE["payload"]
    pawn = _get_player_pawn(world)
    helper_actor = _find_helper_actor(world)
    payload["pie_world_path"] = _safe_path(world)
    payload["pawn_path"] = _safe_path(pawn)
    payload["pawn_class"] = _safe_path(pawn.get_class()) if pawn else ""
    payload["helper_actor_path"] = _safe_path(helper_actor)
    payload["helper_actor_class"] = _safe_path(helper_actor.get_class()) if helper_actor else ""

    helper_mesh = helper_actor.get_component_by_class(unreal.StaticMeshComponent) if helper_actor else None
    attach_parent = None
    if helper_actor:
        root_component = _safe_prop(helper_actor, "root_component")
        get_attach_parent = getattr(root_component, "get_attach_parent", None)
        if callable(get_attach_parent):
            try:
                attach_parent = get_attach_parent()
            except Exception:
                attach_parent = None

    payload["helper_attach_parent_path"] = _safe_path(attach_parent)
    payload["helper_attach_parent_name"] = _safe_name(attach_parent)
    payload["helper_mesh_path"] = _safe_path(helper_mesh)
    payload["helper_mesh_flags"] = {
        "visible": bool(helper_mesh.is_visible()) if helper_mesh and hasattr(helper_mesh, "is_visible") else False,
        "render_custom_depth": bool(_safe_prop(helper_mesh, "bRenderCustomDepth", False)),
        "visible_in_scene_capture_only": bool(_safe_prop(helper_mesh, "bVisibleInSceneCaptureOnly", False)),
        "hidden_in_scene_capture": bool(_safe_prop(helper_mesh, "bHiddenInSceneCapture", False)),
        "render_in_main_pass": bool(_safe_prop(helper_mesh, "bRenderInMainPass", True)),
        "render_in_depth_pass": bool(_safe_prop(helper_mesh, "bRenderInDepthPass", True)),
    }
    return pawn


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
            editor_world = unreal.EditorLevelLibrary.get_editor_world()
            render_target = _load_asset(RT_PATH)
            if editor_world is not None and render_target is not None:
                _clear_rt(editor_world, render_target)
            if not _request_begin_play():
                _finish("Could not request PIE begin play")
                return
            _enter_phase("wait_for_pie")
            return

        if phase == "wait_for_pie":
            world = _get_pie_world()
            if world is not None and _is_in_pie():
                pawn = _capture_runtime_snapshot(world)
                if pawn is None:
                    _finish("No possessed Kamaz pawn found in PIE")
                    return
                if not STATE["payload"]["helper_actor_path"]:
                    _finish("SnowMap Kamaz plow capture helper actor not found in PIE")
                    return
                if not STATE["payload"]["helper_attach_parent_path"]:
                    _finish("SnowMap helper actor did not attach to a Kamaz plow component")
                    return

                render_target = _load_asset(RT_PATH)
                STATE["payload"]["rt_before_drive"] = _sample_rt_grid(world, render_target) if render_target else {}
                _finish()
                return
            if (now - STATE["phase_started_at"]) > 45.0:
                _finish("PIE world did not start")
            return

        if phase == "settle":
            world = _get_pie_world()
            if world is None:
                return
            pawn = _capture_runtime_snapshot(world)
            if pawn is None:
                if (now - STATE["phase_started_at"]) > 15.0:
                    _finish("No possessed Kamaz pawn found in PIE")
                return

            if not STATE["payload"]["helper_actor_path"]:
                if (now - STATE["phase_started_at"]) > 15.0:
                    _finish("SnowMap Kamaz plow capture helper actor not found in PIE")
                return

            if not STATE["payload"]["helper_attach_parent_path"]:
                if (now - STATE["phase_started_at"]) > 15.0:
                    _finish("SnowMap helper actor did not attach to a Kamaz plow component")
                return

            if (now - STATE["phase_started_at"]) < 0.35:
                return

            render_target = _load_asset(RT_PATH)
            STATE["payload"]["rt_before_drive"] = _sample_rt_grid(world, render_target) if render_target else {}
            _enter_phase("end_pie")
            return

        if phase == "drive":
            world = _get_pie_world()
            if world is None:
                _finish("PIE world ended during drive phase")
                return
            pawn = _capture_runtime_snapshot(world)
            if pawn is None:
                _finish("Kamaz pawn disappeared during drive phase")
                return
            if (now - STATE["phase_started_at"]) < 1.5:
                return

            movement_component = _find_vehicle_movement_component(pawn)
            if movement_component is not None and hasattr(movement_component, "set_throttle_input"):
                movement_component.set_throttle_input(0.0)

            after_location = pawn.get_actor_location()
            before_location = STATE.get("before_location", after_location)
            STATE["payload"]["movement_distance_xy"] = float(_distance_xy(before_location, after_location))

            render_target = _load_asset(RT_PATH)
            STATE["payload"]["rt_after_drive"] = _sample_rt_grid(world, render_target) if render_target else {}
            STATE["payload"]["rt_changed"] = STATE["payload"]["rt_before_drive"] != STATE["payload"]["rt_after_drive"]

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
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    register = getattr(unreal, "register_slate_post_tick_callback", None)
    if not callable(register):
        _finish("register_slate_post_tick_callback is unavailable")
        return

    STATE["callback_handle"] = register(_tick)
    _log(f"registered_callback={STATE['callback_handle']}")


if __name__ == "__main__":
    main()
