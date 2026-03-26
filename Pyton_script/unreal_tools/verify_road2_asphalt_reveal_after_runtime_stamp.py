import hashlib
import json
import os
import time

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
ROAD_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
CARRIER_LABEL = "SnowHeightBridgeSurface_Road2"
TRAIL_LABEL = "SnowRuntimeTrailBridgeActor"
OUTPUT_BASENAME = "verify_road2_asphalt_reveal_after_runtime_stamp"
CAPTURE_SIZE = 1024
TOPDOWN_ORTHO_WIDTH_CM = 2600.0
PERSPECTIVE_OFFSET = unreal.Vector(-900.0, -1400.0, 260.0)
STAMP_COUNT = 7
STAMP_STEP_CM = 40.0
MAP_LOAD_WARMUP_SECONDS = 2.0
PRE_CAPTURE_SETTLE_SECONDS = 0.35
POST_STAMP_SETTLE_SECONDS = 0.75
STAMP_STEP_SETTLE_SECONDS = 0.06
CAPTURE_WARMUP_PASSES = 4

RENDER_LIB = unreal.RenderingLibrary
ASSET_LIB = unreal.EditorAssetLibrary


def _saved_output_dir():
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    unreal.log(f"[{OUTPUT_BASENAME}] Wrote file: {path}")
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


def _file_sha256(path):
    if not path or not os.path.exists(path):
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _first_component_by_class(actor, cls):
    if actor is None:
        return None
    try:
        return actor.get_component_by_class(cls)
    except Exception:
        return None


def _first_scene_component(actor):
    if actor is None:
        return None
    root = _safe_property(actor, "root_component")
    if root is not None:
        return root
    try:
        components = list(actor.get_components_by_class(unreal.SceneComponent) or [])
    except Exception:
        components = []
    return components[0] if components else None


def _get_actor_bounds(actor):
    get_bounds = getattr(actor, "get_actor_bounds", None)
    if callable(get_bounds):
        try:
            return get_bounds(True)
        except Exception:
            pass
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
    for name in (
        "SCS_FINAL_COLOR_LDR",
        "SCS_FINAL_COLOR_HDR",
        "SCS_BASE_COLOR",
        "SCS_BASE_COLOR_LDR",
        "SCS_BASECOLOR",
        "SCS_BASECOLOR_LDR",
    ):
        value = getattr(enum_cls, name, None)
        if value is not None:
            return value, name
    return None, ""


def _rotator_towards(from_location, to_location):
    return unreal.MathLibrary.find_look_at_rotation(from_location, to_location)


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


def _sample_rgb(world, render_target, u, v):
    sample = RENDER_LIB.read_render_target_raw_uv(world, render_target, float(u), float(v))
    return {
        "r": float(getattr(sample, "r", 0.0)),
        "g": float(getattr(sample, "g", 0.0)),
        "b": float(getattr(sample, "b", 0.0)),
        "a": float(getattr(sample, "a", 0.0)),
    }


def _luma(rgb):
    return (0.2126 * float(rgb["r"])) + (0.7152 * float(rgb["g"])) + (0.0722 * float(rgb["b"]))


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


def _configure_show_only(capture_component, show_only_actors):
    if not show_only_actors:
        return
    primitive_mode = getattr(unreal.SceneCapturePrimitiveRenderMode, "PRM_UseShowOnlyList", None)
    if primitive_mode is not None:
        capture_component.set_editor_property("primitive_render_mode", primitive_mode)
    try:
        capture_component.clear_show_only_components()
    except Exception:
        pass
    for actor in show_only_actors:
        if actor is None:
            continue
        primitive_components = []
        try:
            primitive_components = list(actor.get_components_by_class(unreal.PrimitiveComponent) or [])
        except Exception:
            primitive_components = []
        for component in primitive_components:
            added = False
            for method_name in ("show_only_component", "add_show_only_component"):
                method = getattr(capture_component, method_name, None)
                if not callable(method):
                    continue
                try:
                    method(component)
                    added = True
                    break
                except TypeError:
                    try:
                        method(component, False)
                        added = True
                        break
                    except Exception:
                        pass
                except Exception:
                    pass
            if not added:
                try:
                    show_only_components = list(_safe_property(capture_component, "show_only_components", []) or [])
                    show_only_components.append(component)
                    capture_component.set_editor_property("show_only_components", show_only_components)
                except Exception:
                    pass
        try:
            capture_component.show_only_actor_components(actor, False)
            continue
        except Exception:
            pass
        try:
            show_only_list = list(_safe_property(capture_component, "show_only_actors", []) or [])
            show_only_list.append(actor)
            capture_component.set_editor_property("show_only_actors", show_only_list)
        except Exception:
            pass


def _capture_topdown(world, focus_origin, output_dir, suffix, show_only_actors=None):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    camera_location = unreal.Vector(float(focus_origin.x), float(focus_origin.y), float(focus_origin.z + 2400.0))
    capture_actor = actor_subsystem.spawn_actor_from_class(
        unreal.SceneCapture2D,
        camera_location,
        _rotator_towards(camera_location, focus_origin),
    )
    if capture_actor is None:
        raise RuntimeError("Failed to spawn topdown SceneCapture2D")

    capture_component = capture_actor.get_component_by_class(unreal.SceneCaptureComponent2D)
    if capture_component is None:
        actor_subsystem.destroy_actor(capture_actor)
        raise RuntimeError("Spawned topdown SceneCapture2D has no SceneCaptureComponent2D")

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
    _configure_show_only(capture_component, show_only_actors)

    _settle_scene(PRE_CAPTURE_SETTLE_SECONDS, CAPTURE_WARMUP_PASSES)
    for _ in range(CAPTURE_WARMUP_PASSES):
        capture_component.capture_scene()
        time.sleep(0.05)
    capture_component.capture_scene()

    exported_path = _export_rt(world, capture_rt, output_dir, f"{OUTPUT_BASENAME}_{suffix}_topdown")
    center = _sample_rgb(world, capture_rt, 0.50, 0.50)
    left = _sample_rgb(world, capture_rt, 0.32, 0.50)
    right = _sample_rgb(world, capture_rt, 0.68, 0.50)

    try:
        actor_subsystem.destroy_actor(capture_actor)
    except Exception:
        pass

    return {
        "capture_source_name": capture_source_name,
        "exported_image_path": exported_path,
        "exported_image_sha256": _file_sha256(exported_path),
        "samples": {
            "center": center,
            "left": left,
            "right": right,
        },
        "luma": {
            "center": _luma(center),
            "left": _luma(left),
            "right": _luma(right),
        },
    }


def _capture_perspective(world, focus_origin, output_dir, suffix, show_only_actors=None):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    camera_location = focus_origin + PERSPECTIVE_OFFSET
    camera_rotation = _rotator_towards(camera_location, focus_origin + unreal.Vector(0.0, 0.0, 35.0))
    capture_actor = actor_subsystem.spawn_actor_from_class(
        unreal.SceneCapture2D,
        camera_location,
        camera_rotation,
    )
    if capture_actor is None:
        raise RuntimeError("Failed to spawn perspective SceneCapture2D")

    capture_component = capture_actor.get_component_by_class(unreal.SceneCaptureComponent2D)
    if capture_component is None:
        actor_subsystem.destroy_actor(capture_actor)
        raise RuntimeError("Spawned perspective SceneCapture2D has no SceneCaptureComponent2D")

    capture_rt = _create_capture_rt(world)
    capture_component.set_editor_property("texture_target", capture_rt)
    projection_enum = getattr(unreal.CameraProjectionMode, "PERSPECTIVE", None)
    if projection_enum is not None:
        capture_component.set_editor_property("projection_type", projection_enum)
    capture_component.set_editor_property("capture_every_frame", False)
    capture_component.set_editor_property("capture_on_movement", False)
    capture_source, capture_source_name = _resolve_capture_source()
    if capture_source is not None:
        capture_component.set_editor_property("capture_source", capture_source)
    _configure_show_only(capture_component, show_only_actors)

    _settle_scene(PRE_CAPTURE_SETTLE_SECONDS, CAPTURE_WARMUP_PASSES)
    for _ in range(CAPTURE_WARMUP_PASSES):
        capture_component.capture_scene()
        time.sleep(0.05)
    capture_component.capture_scene()

    exported_path = _export_rt(world, capture_rt, output_dir, f"{OUTPUT_BASENAME}_{suffix}_perspective")
    center = _sample_rgb(world, capture_rt, 0.50, 0.58)

    try:
        actor_subsystem.destroy_actor(capture_actor)
    except Exception:
        pass

    return {
        "capture_source_name": capture_source_name,
        "exported_image_path": exported_path,
        "exported_image_sha256": _file_sha256(exported_path),
        "center_sample": center,
        "center_luma": _luma(center),
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
    _settle_scene(MAP_LOAD_WARMUP_SECONDS, 8)

    world = _get_editor_world()
    road_actor = _find_actor_by_path(ROAD_ACTOR_PATH)
    carrier_actor = _find_actor_by_label(CARRIER_LABEL)
    trail_actor = _find_actor_by_label(TRAIL_LABEL)
    if road_actor is None:
        raise RuntimeError(f"Missing road actor: {ROAD_ACTOR_PATH}")
    if carrier_actor is None:
        raise RuntimeError(f"Missing carrier actor: {CARRIER_LABEL}")
    if trail_actor is None:
        raise RuntimeError(f"Missing trail actor: {TRAIL_LABEL}")

    trail_component_class = unreal.load_class(None, "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent")
    trail_component = trail_actor.get_component_by_class(trail_component_class) if trail_component_class else None
    if trail_component is None:
        raise RuntimeError("SnowRuntimeTrailBridgeComponent not found on SnowRuntimeTrailBridgeActor")

    road_origin, road_extent = _get_actor_bounds(road_actor)
    carrier_component = _first_component_by_class(carrier_actor, unreal.StaticMeshComponent)
    trail_source_component = _first_scene_component(trail_actor)
    if trail_source_component is None:
        raise RuntimeError("Trail actor has no usable SceneComponent root")
    road_and_carrier = [road_actor, carrier_actor]
    road_only = [road_actor]

    focus_origin = carrier_actor.get_actor_location()

    original_actor_location = trail_actor.get_actor_location()
    original_enable_runtime_trail = bool(_safe_property(trail_component, "bEnableRuntimeTrail", False))
    original_enable_rvt_stamp = bool(_safe_property(trail_component, "bEnableRvtVisualStamp", False))
    original_use_source_height_gate = bool(_safe_property(trail_component, "bUseSourceHeightGate", True))
    original_source_component_override = _safe_property(trail_component, "SourceComponentOverride", None)
    original_stamp_spacing = float(_safe_property(trail_component, "StampSpacingCm", 5.0))
    original_component_visible = bool(_safe_property(carrier_component, "visible", True))

    result = {
        "success": False,
        "map_path": MAP_PATH,
        "road_actor_path": _object_path(road_actor),
        "carrier_actor_path": _object_path(carrier_actor),
        "trail_actor_path": _object_path(trail_actor),
        "trail_component_path": _object_path(trail_component),
        "trail_source_component_path": _object_path(trail_source_component),
        "road_bounds_origin": {
            "x": float(road_origin.x),
            "y": float(road_origin.y),
            "z": float(road_origin.z),
        },
        "road_bounds_extent": {
            "x": float(road_extent.x),
            "y": float(road_extent.y),
            "z": float(road_extent.z),
        },
        "focus_origin": {
            "x": float(focus_origin.x),
            "y": float(focus_origin.y),
            "z": float(focus_origin.z),
        },
        "before": {},
        "after": {},
        "reference_without_carrier": {},
        "stamp_calls": [],
        "analysis": {},
        "error": "",
    }

    try:
        result["before"] = {
            "topdown": _capture_topdown(world, focus_origin, output_dir, "before", road_and_carrier),
            "perspective": _capture_perspective(world, focus_origin, output_dir, "before", road_and_carrier),
        }

        trail_component.set_editor_property("bEnableRuntimeTrail", True)
        trail_component.set_editor_property("bEnableRvtVisualStamp", True)
        trail_component.set_editor_property("bUseSourceHeightGate", False)
        trail_component.set_editor_property("SourceComponentOverride", trail_source_component)
        trail_component.set_editor_property("StampSpacingCm", 5.0)

        carrier_location = carrier_actor.get_actor_location()
        start_location = unreal.Vector(
            float(road_origin.x - ((STAMP_COUNT - 1) * STAMP_STEP_CM * 0.5)),
            float(road_origin.y),
            float(carrier_location.z),
        )

        for stamp_index in range(STAMP_COUNT):
            location = unreal.Vector(
                float(start_location.x + (stamp_index * STAMP_STEP_CM)),
                float(start_location.y),
                float(start_location.z),
            )
            trail_actor.set_actor_location(location, False, False)
            stamp_ok = bool(trail_component.record_trail_stamp_now())
            _settle_scene(STAMP_STEP_SETTLE_SECONDS, 2)
            result["stamp_calls"].append(
                {
                    "index": int(stamp_index),
                    "location": {
                        "x": float(location.x),
                        "y": float(location.y),
                        "z": float(location.z),
                    },
                    "record_trail_stamp_now": stamp_ok,
                }
            )

        _settle_scene(POST_STAMP_SETTLE_SECONDS, 6)
        result["after"] = {
            "topdown": _capture_topdown(world, focus_origin, output_dir, "after", road_and_carrier),
            "perspective": _capture_perspective(world, focus_origin, output_dir, "after", road_and_carrier),
        }

        _set_component_visible(carrier_component, False)
        _settle_scene(PRE_CAPTURE_SETTLE_SECONDS, CAPTURE_WARMUP_PASSES)
        result["reference_without_carrier"] = {
            "topdown": _capture_topdown(world, focus_origin, output_dir, "reference_without_carrier", road_only),
            "perspective": _capture_perspective(world, focus_origin, output_dir, "reference_without_carrier", road_only),
        }
        _set_component_visible(carrier_component, True)

        before_center = float(result["before"]["topdown"]["luma"]["center"])
        before_side = 0.5 * (
            float(result["before"]["topdown"]["luma"]["left"]) + float(result["before"]["topdown"]["luma"]["right"])
        )
        after_center = float(result["after"]["topdown"]["luma"]["center"])
        after_side = 0.5 * (
            float(result["after"]["topdown"]["luma"]["left"]) + float(result["after"]["topdown"]["luma"]["right"])
        )
        reference_center = float(result["reference_without_carrier"]["topdown"]["luma"]["center"])

        center_drop_from_before = before_center - after_center
        center_vs_side_after = after_side - after_center
        center_to_reference_gap = abs(after_center - reference_center)

        result["analysis"] = {
            "before_center_luma": before_center,
            "before_side_avg_luma": before_side,
            "after_center_luma": after_center,
            "after_side_avg_luma": after_side,
            "reference_center_luma": reference_center,
            "center_drop_from_before": center_drop_from_before,
            "center_vs_side_after": center_vs_side_after,
            "center_to_reference_gap": center_to_reference_gap,
            "stamp_success_count": int(sum(1 for entry in result["stamp_calls"] if entry["record_trail_stamp_now"])),
            "images_changed_after_stamp": (
                result["before"]["topdown"]["exported_image_sha256"] != result["after"]["topdown"]["exported_image_sha256"]
                or result["before"]["perspective"]["exported_image_sha256"] != result["after"]["perspective"]["exported_image_sha256"]
            ),
            "center_darkened_after_stamp": center_drop_from_before > 0.10,
            "center_darker_than_sides_after_stamp": center_vs_side_after > 0.08,
            "after_close_to_base_road_reference": center_to_reference_gap < 0.08,
        }

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
        except Exception:
            pass
        try:
            trail_component.set_editor_property("bEnableRvtVisualStamp", original_enable_rvt_stamp)
        except Exception:
            pass
        try:
            trail_component.set_editor_property("bUseSourceHeightGate", original_use_source_height_gate)
        except Exception:
            pass
        try:
            trail_component.set_editor_property("SourceComponentOverride", original_source_component_override)
        except Exception:
            pass
        try:
            trail_component.set_editor_property("StampSpacingCm", original_stamp_spacing)
        except Exception:
            pass
        _set_component_visible(carrier_component, original_component_visible)

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run()
