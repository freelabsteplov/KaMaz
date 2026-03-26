import hashlib
import json
import math
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
ROAD_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
CARRIER_LABEL = "SnowHeightBridgeSurface_Road2"
OUTPUT_BASENAME = "inspect_road2_carrier_visibility_toggle"
CAPTURE_SIZE = 1024
TOPDOWN_ORTHO_WIDTH_CM = 2600.0

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


def _get_actor_bounds(actor):
    get_bounds = getattr(actor, "get_actor_bounds", None)
    if callable(get_bounds):
        return get_bounds(True)
    raise RuntimeError(f"Could not resolve bounds for actor: {_object_path(actor)}")


def _create_capture_rt(world):
    create_fn = getattr(RENDER_LIB, "create_render_target2d", None)
    if not callable(create_fn):
        raise RuntimeError("RenderingLibrary.create_render_target2d is unavailable")
    fmt = getattr(unreal.TextureRenderTargetFormat, "RTF_RGBA8", None)
    if fmt is not None:
        try:
            return create_fn(world, CAPTURE_SIZE, CAPTURE_SIZE, fmt)
        except TypeError:
            pass
    return create_fn(world, CAPTURE_SIZE, CAPTURE_SIZE)


def _resolve_capture_source():
    enum_cls = getattr(unreal, "SceneCaptureSource", None)
    if enum_cls is None:
        return None, ""
    for name in ("SCS_BASE_COLOR", "SCS_BASE_COLOR_LDR", "SCS_BASECOLOR", "SCS_BASECOLOR_LDR", "SCS_FINAL_COLOR_LDR", "SCS_FINAL_COLOR_HDR"):
        value = getattr(enum_cls, name, None)
        if value is not None:
            return value, name
    return None, ""


def _file_sha256(path):
    if not path or not os.path.exists(path):
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rotator_towards(from_location, to_location):
    delta = to_location - from_location
    yaw = math.degrees(math.atan2(float(delta.y), float(delta.x)))
    distance_xy = math.sqrt(float(delta.x) * float(delta.x) + float(delta.y) * float(delta.y))
    pitch = math.degrees(math.atan2(float(delta.z), max(distance_xy, 1.0)))
    return unreal.Rotator(pitch, yaw, 0.0)


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


def _capture_topdown(world, focus_origin, output_dir, suffix):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    capture_actor = actor_subsystem.spawn_actor_from_class(
        unreal.SceneCapture2D,
        unreal.Vector(float(focus_origin.x), float(focus_origin.y), float(focus_origin.z + 2400.0)),
        unreal.Rotator(-90.0, 0.0, 0.0),
    )
    if capture_actor is None:
        raise RuntimeError("Failed to spawn SceneCapture2D")

    capture_component = capture_actor.get_component_by_class(unreal.SceneCaptureComponent2D)
    if capture_component is None:
        actor_subsystem.destroy_actor(capture_actor)
        raise RuntimeError("SceneCapture2D missing component")

    capture_rt = _create_capture_rt(world)
    capture_component.set_editor_property("texture_target", capture_rt)
    projection_enum = getattr(unreal.CameraProjectionMode, "ORTHOGRAPHIC", None)
    if projection_enum is not None:
        capture_component.set_editor_property("projection_type", projection_enum)
    capture_component.set_editor_property("ortho_width", float(TOPDOWN_ORTHO_WIDTH_CM))
    capture_component.set_editor_property("capture_every_frame", False)
    capture_component.set_editor_property("capture_on_movement", False)
    capture_source, capture_source_name = _resolve_capture_source()
    if capture_source is not None:
        capture_component.set_editor_property("capture_source", capture_source)
    capture_component.capture_scene()
    capture_component.capture_scene()

    exported_path = _export_rt(world, capture_rt, output_dir, f"{OUTPUT_BASENAME}_{suffix}")
    center = RENDER_LIB.read_render_target_raw_uv(world, capture_rt, 0.50, 0.50)
    left = RENDER_LIB.read_render_target_raw_uv(world, capture_rt, 0.32, 0.50)
    right = RENDER_LIB.read_render_target_raw_uv(world, capture_rt, 0.68, 0.50)

    try:
        actor_subsystem.destroy_actor(capture_actor)
    except Exception:
        pass

    return {
        "capture_source_name": capture_source_name,
        "exported_image_path": exported_path,
        "exported_image_sha256": _file_sha256(exported_path),
        "center_sample": {
            "r": float(getattr(center, "r", 0.0)),
            "g": float(getattr(center, "g", 0.0)),
            "b": float(getattr(center, "b", 0.0)),
            "a": float(getattr(center, "a", 0.0)),
        },
        "left_sample": {
            "r": float(getattr(left, "r", 0.0)),
            "g": float(getattr(left, "g", 0.0)),
            "b": float(getattr(left, "b", 0.0)),
            "a": float(getattr(left, "a", 0.0)),
        },
        "right_sample": {
            "r": float(getattr(right, "r", 0.0)),
            "g": float(getattr(right, "g", 0.0)),
            "b": float(getattr(right, "b", 0.0)),
            "a": float(getattr(right, "a", 0.0)),
        },
    }


def _set_component_visible(component, visible):
    if component is None:
        return
    setter = getattr(component, "set_visibility", None)
    if callable(setter):
        try:
            setter(bool(visible), True)
        except Exception:
            pass
    try:
        component.set_editor_property("visible", bool(visible))
    except Exception:
        pass
    for method_name in ("mark_render_state_dirty", "reregister_component", "post_edit_change"):
        method = getattr(component, method_name, None)
        if callable(method):
            try:
                method()
            except Exception:
                pass


def run(output_dir=None):
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    world = _get_editor_world()
    road_actor = _find_actor_by_path(ROAD_ACTOR_PATH)
    carrier_actor = _find_actor_by_label(CARRIER_LABEL)
    if road_actor is None or carrier_actor is None:
        raise RuntimeError("Road2 or carrier actor is missing")

    road_component = road_actor.get_component_by_class(unreal.StaticMeshComponent)
    carrier_component = carrier_actor.get_component_by_class(unreal.StaticMeshComponent)
    if road_component is None or carrier_component is None:
        raise RuntimeError("Static mesh components missing on Road2 or carrier")

    focus_origin, _ = _get_actor_bounds(road_actor)
    original_road_visible = bool(_safe_property(road_component, "visible", True))
    original_carrier_visible = bool(_safe_property(carrier_component, "visible", True))

    result = {
        "success": False,
        "road_actor_path": _object_path(road_actor),
        "carrier_actor_path": _object_path(carrier_actor),
        "road_component_path": _object_path(road_component),
        "carrier_component_path": _object_path(carrier_component),
        "captures": {},
        "error": "",
    }

    try:
        _set_component_visible(road_component, True)
        _set_component_visible(carrier_component, True)
        result["captures"]["both_visible"] = _capture_topdown(world, focus_origin, output_dir, "both_visible")

        _set_component_visible(road_component, False)
        _set_component_visible(carrier_component, True)
        result["captures"]["carrier_only"] = _capture_topdown(world, focus_origin, output_dir, "carrier_only")

        _set_component_visible(road_component, True)
        _set_component_visible(carrier_component, False)
        result["captures"]["road_only"] = _capture_topdown(world, focus_origin, output_dir, "road_only")

        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        _set_component_visible(road_component, original_road_visible)
        _set_component_visible(carrier_component, original_carrier_visible)

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run()
