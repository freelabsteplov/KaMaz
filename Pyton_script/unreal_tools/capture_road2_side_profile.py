import json
import os
import time

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
ROAD_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
CARRIER_LABEL = "SnowHeightBridgeSurface_Road2"
TRAIL_LABEL = "SnowRuntimeTrailBridgeActor"
OUTPUT_BASENAME = "capture_road2_side_profile"
CAPTURE_SIZE = 1280
STAMP_COUNT = 7
STAMP_STEP_CM = 40.0
CAMERA_OFFSET = unreal.Vector(-450.0, -1700.0, 120.0)
CAMERA_LOOK_OFFSET = unreal.Vector(0.0, 0.0, 10.0)
MAP_LOAD_WARMUP_SECONDS = 2.0
PRE_CAPTURE_SETTLE_SECONDS = 0.35
POST_STAMP_SETTLE_SECONDS = 0.75
STAMP_STEP_SETTLE_SECONDS = 0.06
CAPTURE_WARMUP_PASSES = 4

RENDER_LIB = unreal.RenderingLibrary


def _saved_output_dir():
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return path


def _object_path(value):
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _safe_property(obj, property_name, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(property_name)
        except Exception:
            pass
    return getattr(obj, property_name, default)


def _get_editor_world():
    try:
        return unreal.EditorLevelLibrary.get_editor_world()
    except Exception:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        return subsystem.get_editor_world()


def _find_actor_by_path(actor_path):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        if _object_path(actor) == actor_path:
            return actor
    return None


def _find_actor_by_label(actor_label):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        try:
            if actor.get_actor_label() == actor_label:
                return actor
        except Exception:
            continue
    return None


def _first_scene_component(actor):
    if actor is None:
        return None
    root = _safe_property(actor, "root_component")
    if root is not None:
        return root
    components = list(actor.get_components_by_class(unreal.SceneComponent) or [])
    return components[0] if components else None


def _rotator_towards(from_location, to_location):
    delta = to_location - from_location
    yaw = unreal.MathLibrary.atan2(delta.y, delta.x)
    distance_xy = unreal.MathLibrary.sqrt((delta.x * delta.x) + (delta.y * delta.y))
    pitch = unreal.MathLibrary.atan2(delta.z, max(distance_xy, 1.0))
    return unreal.Rotator(unreal.MathLibrary.radians_to_degrees(pitch), unreal.MathLibrary.radians_to_degrees(yaw), 0.0)


def _create_capture_rt(world):
    fmt = getattr(unreal.TextureRenderTargetFormat, "RTF_RGBA8", None)
    if fmt is not None:
        try:
            return RENDER_LIB.create_render_target2d(world, CAPTURE_SIZE, CAPTURE_SIZE, fmt)
        except TypeError:
            pass
    return RENDER_LIB.create_render_target2d(world, CAPTURE_SIZE, CAPTURE_SIZE)


def _export_rt(world, render_target, output_dir, base_filename):
    os.makedirs(output_dir, exist_ok=True)
    RENDER_LIB.export_render_target(world, render_target, output_dir, base_filename)
    for candidate in (
        os.path.join(output_dir, base_filename),
        os.path.join(output_dir, f"{base_filename}.png"),
        os.path.join(output_dir, f"{base_filename}.hdr"),
    ):
        if os.path.exists(candidate):
            return candidate
    return ""


def _invalidate_viewports():
    try:
        unreal.EditorLevelLibrary.editor_invalidate_viewports()
    except Exception:
        pass


def _settle_scene(seconds, pulses=4):
    total_seconds = max(float(seconds), 0.0)
    pulse_count = max(int(pulses), 1)
    if total_seconds <= 0.0:
        _invalidate_viewports()
        return
    sleep_slice = total_seconds / float(pulse_count)
    for _ in range(pulse_count):
        _invalidate_viewports()
        time.sleep(sleep_slice)


def _capture_perspective(world, focus_origin, output_dir, suffix):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    camera_location = focus_origin + CAMERA_OFFSET
    camera_rotation = _rotator_towards(camera_location, focus_origin + CAMERA_LOOK_OFFSET)
    capture_actor = actor_subsystem.spawn_actor_from_class(
        unreal.SceneCapture2D,
        camera_location,
        camera_rotation,
    )
    if capture_actor is None:
        raise RuntimeError("Failed to spawn side-profile SceneCapture2D")

    capture_component = capture_actor.get_component_by_class(unreal.SceneCaptureComponent2D)
    if capture_component is None:
        actor_subsystem.destroy_actor(capture_actor)
        raise RuntimeError("SceneCapture2D missing component")

    capture_rt = _create_capture_rt(world)
    capture_component.set_editor_property("texture_target", capture_rt)
    capture_component.set_editor_property("capture_every_frame", False)
    capture_component.set_editor_property("capture_on_movement", False)
    capture_source = getattr(unreal.SceneCaptureSource, "SCS_FINAL_COLOR_LDR", None)
    if capture_source is not None:
        capture_component.set_editor_property("capture_source", capture_source)

    _settle_scene(PRE_CAPTURE_SETTLE_SECONDS, CAPTURE_WARMUP_PASSES)
    for _ in range(CAPTURE_WARMUP_PASSES):
        capture_component.capture_scene()
        time.sleep(0.05)
    capture_component.capture_scene()

    exported_path = _export_rt(world, capture_rt, output_dir, f"{OUTPUT_BASENAME}_{suffix}")
    try:
        actor_subsystem.destroy_actor(capture_actor)
    except Exception:
        pass

    return {
        "exported_image_path": exported_path,
        "camera_location": {
            "x": float(camera_location.x),
            "y": float(camera_location.y),
            "z": float(camera_location.z),
        },
        "camera_rotation": {
            "pitch": float(camera_rotation.pitch),
            "yaw": float(camera_rotation.yaw),
            "roll": float(camera_rotation.roll),
        },
    }


def run(output_dir=None):
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    _settle_scene(MAP_LOAD_WARMUP_SECONDS, 8)

    world = _get_editor_world()
    road_actor = _find_actor_by_path(ROAD_ACTOR_PATH)
    carrier_actor = _find_actor_by_label(CARRIER_LABEL)
    trail_actor = _find_actor_by_label(TRAIL_LABEL)
    if road_actor is None or carrier_actor is None or trail_actor is None:
        raise RuntimeError("Missing Road2/carrier/trail actors")

    trail_component_class = unreal.load_class(None, "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent")
    trail_component = trail_actor.get_component_by_class(trail_component_class) if trail_component_class else None
    if trail_component is None:
        raise RuntimeError("Trail component not found")

    focus_origin = carrier_actor.get_actor_location()
    trail_source_component = _first_scene_component(trail_actor)
    original_actor_location = trail_actor.get_actor_location()
    original_enable_runtime_trail = bool(_safe_property(trail_component, "bEnableRuntimeTrail", False))
    original_enable_rvt_stamp = bool(_safe_property(trail_component, "bEnableRvtVisualStamp", False))
    original_use_source_height_gate = bool(_safe_property(trail_component, "bUseSourceHeightGate", True))
    original_source_component_override = _safe_property(trail_component, "SourceComponentOverride", None)
    original_stamp_spacing = float(_safe_property(trail_component, "StampSpacingCm", 5.0))

    result = {
        "success": False,
        "road_actor_path": _object_path(road_actor),
        "carrier_actor_path": _object_path(carrier_actor),
        "trail_actor_path": _object_path(trail_actor),
        "before": {},
        "after": {},
        "error": "",
    }

    try:
        result["before"] = _capture_perspective(world, focus_origin, output_dir, "before")

        trail_component.set_editor_property("bEnableRuntimeTrail", True)
        trail_component.set_editor_property("bEnableRvtVisualStamp", True)
        trail_component.set_editor_property("bUseSourceHeightGate", False)
        trail_component.set_editor_property("SourceComponentOverride", trail_source_component)
        trail_component.set_editor_property("StampSpacingCm", 5.0)

        start_location = unreal.Vector(
            float(focus_origin.x - ((STAMP_COUNT - 1) * STAMP_STEP_CM * 0.5)),
            float(focus_origin.y),
            float(focus_origin.z),
        )
        for stamp_index in range(STAMP_COUNT):
            location = unreal.Vector(
                float(start_location.x + (stamp_index * STAMP_STEP_CM)),
                float(start_location.y),
                float(start_location.z),
            )
            trail_actor.set_actor_location(location, False, False)
            trail_component.record_trail_stamp_now()
            _settle_scene(STAMP_STEP_SETTLE_SECONDS, 2)

        _settle_scene(POST_STAMP_SETTLE_SECONDS, 6)
        result["after"] = _capture_perspective(world, focus_origin, output_dir, "after")
        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        try:
            trail_actor.set_actor_location(original_actor_location, False, False)
        except Exception:
            pass
        try:
            trail_component.set_editor_property("bEnableRuntimeTrail", original_enable_runtime_trail)
            trail_component.set_editor_property("bEnableRvtVisualStamp", original_enable_rvt_stamp)
            trail_component.set_editor_property("bUseSourceHeightGate", original_use_source_height_gate)
            trail_component.set_editor_property("SourceComponentOverride", original_source_component_override)
            trail_component.set_editor_property("StampSpacingCm", original_stamp_spacing)
        except Exception:
            pass

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run()
