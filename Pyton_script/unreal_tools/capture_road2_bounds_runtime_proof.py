import hashlib
import json
import os
import time

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
ROAD_LABEL = "Road2"
CARRIER_LABEL = "SnowHeightBridgeSurface_Road2"
TRAIL_LABEL = "SnowRuntimeTrailBridgeActor"
OUTPUT_BASENAME = "capture_road2_bounds_runtime_proof"
OUTPUT_DIR = os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")
CAPTURE_SIZE = 1280
STAMP_COUNT = 9
STAMP_STEP_CM = 120.0
MAP_WARMUP_SECONDS = 5.0
STAMP_SETTLE_SECONDS = 0.2
POST_STAMP_SETTLE_SECONDS = 1.0


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _obj_path(obj):
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _safe_property(obj, name, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(name)
        except Exception:
            pass
    return getattr(obj, name, default)


def _safe_set(obj, name, value):
    setter = getattr(obj, "set_editor_property", None)
    if callable(setter):
        try:
            setter(name, value)
            return
        except Exception:
            pass
    setattr(obj, name, value)


def _settle(seconds, ticks=1):
    end_time = time.time() + float(seconds)
    while time.time() < end_time:
        unreal.EditorLevelLibrary.editor_invalidate_viewports()
        for _ in range(max(int(ticks), 1)):
            unreal.SystemLibrary.collect_garbage()
        time.sleep(0.05)


def _find_actor_by_label(label):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        try:
            if actor.get_actor_label() == label:
                return actor
        except Exception:
            continue
    return None


def _get_editor_world():
    try:
        return unreal.EditorLevelLibrary.get_editor_world()
    except Exception:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        return subsystem.get_editor_world()


def _first_scene_component(actor):
    if actor is None:
        return None
    getter = getattr(actor, "get_root_component", None)
    if callable(getter):
        try:
            root = getter()
            if root:
                return root
        except Exception:
            pass
    for component in list(actor.get_components_by_class(unreal.SceneComponent) or []):
        return component
    return None


def _get_bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    return origin, extent


def _create_rt(world):
    fmt = getattr(unreal.TextureRenderTargetFormat, "RTF_RGBA8", None)
    if fmt is not None:
        try:
            return unreal.RenderingLibrary.create_render_target2d(world, CAPTURE_SIZE, CAPTURE_SIZE, fmt)
        except TypeError:
            pass
    return unreal.RenderingLibrary.create_render_target2d(world, CAPTURE_SIZE, CAPTURE_SIZE)


def _hash_file(path):
    if not path or not os.path.exists(path):
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _find_exported_path(base_name):
    for candidate in (
        os.path.join(OUTPUT_DIR, base_name),
        os.path.join(OUTPUT_DIR, f"{base_name}.png"),
        os.path.join(OUTPUT_DIR, f"{base_name}.hdr"),
    ):
        if os.path.exists(candidate):
            return candidate
    return ""


def _capture_topdown(world, focus_origin, ortho_width, name):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    location = unreal.Vector(float(focus_origin.x), float(focus_origin.y), float(focus_origin.z + 1800.0))
    rotation = unreal.MathLibrary.find_look_at_rotation(location, focus_origin)
    capture_actor = actor_subsystem.spawn_actor_from_class(unreal.SceneCapture2D, location, rotation)
    capture_component = capture_actor.get_component_by_class(unreal.SceneCaptureComponent2D)
    capture_rt = _create_rt(world)
    capture_component.set_editor_property("texture_target", capture_rt)
    projection = getattr(unreal.CameraProjectionMode, "ORTHOGRAPHIC", None)
    if projection is not None:
        capture_component.set_editor_property("projection_type", projection)
    capture_component.set_editor_property("ortho_width", float(ortho_width))
    capture_component.set_editor_property("capture_every_frame", False)
    capture_component.set_editor_property("capture_on_movement", False)
    source = getattr(unreal.SceneCaptureSource, "SCS_FINAL_COLOR_LDR", None)
    if source is not None:
        capture_component.set_editor_property("capture_source", source)
    capture_component.capture_scene()
    capture_component.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, capture_rt, OUTPUT_DIR, name)
    actor_subsystem.destroy_actor(capture_actor)
    final_path = _find_exported_path(name)
    return {
        "path": final_path if os.path.exists(final_path) else "",
        "sha256": _hash_file(final_path),
        "camera_location": {"x": float(location.x), "y": float(location.y), "z": float(location.z)},
        "camera_rotation": {"pitch": float(rotation.pitch), "yaw": float(rotation.yaw), "roll": float(rotation.roll)},
    }


def _capture_perspective(world, focus_origin, road_extent, road_rotation, name):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    offset = unreal.Vector(
        float(-max(road_extent.x, 350.0) * 0.85),
        float(-max(road_extent.y, 350.0) * 1.25),
        float(max(road_extent.z, 40.0) + 220.0),
    )
    transform = unreal.Transform(focus_origin, road_rotation, unreal.Vector(1.0, 1.0, 1.0))
    location = unreal.MathLibrary.transform_location(transform, offset)
    target = focus_origin + unreal.Vector(0.0, 0.0, 35.0)
    rotation = unreal.MathLibrary.find_look_at_rotation(location, target)
    capture_actor = actor_subsystem.spawn_actor_from_class(unreal.SceneCapture2D, location, rotation)
    capture_component = capture_actor.get_component_by_class(unreal.SceneCaptureComponent2D)
    capture_rt = _create_rt(world)
    capture_component.set_editor_property("texture_target", capture_rt)
    capture_component.set_editor_property("capture_every_frame", False)
    capture_component.set_editor_property("capture_on_movement", False)
    source = getattr(unreal.SceneCaptureSource, "SCS_FINAL_COLOR_LDR", None)
    if source is not None:
        capture_component.set_editor_property("capture_source", source)
    capture_component.capture_scene()
    capture_component.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, capture_rt, OUTPUT_DIR, name)
    actor_subsystem.destroy_actor(capture_actor)
    final_path = _find_exported_path(name)
    return {
        "path": final_path if os.path.exists(final_path) else "",
        "sha256": _hash_file(final_path),
        "camera_location": {"x": float(location.x), "y": float(location.y), "z": float(location.z)},
        "camera_rotation": {"pitch": float(rotation.pitch), "yaw": float(rotation.yaw), "roll": float(rotation.roll)},
    }


def _set_component_visible(component, visible):
    if component is None:
        return
    try:
        component.set_visibility(bool(visible), True)
    except Exception:
        pass
    _safe_set(component, "visible", bool(visible))
    for method_name in ("mark_render_state_dirty", "reregister_component", "post_edit_change"):
        method = getattr(component, method_name, None)
        if callable(method):
            try:
                method()
            except Exception:
                pass


def run():
    output_path = os.path.join(OUTPUT_DIR, f"{OUTPUT_BASENAME}.json")
    result = {"success": False, "error": ""}
    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        _settle(MAP_WARMUP_SECONDS, 4)

        world = _get_editor_world()
        road_actor = _find_actor_by_label(ROAD_LABEL)
        carrier_actor = _find_actor_by_label(CARRIER_LABEL)
        trail_actor = _find_actor_by_label(TRAIL_LABEL)
        if road_actor is None or carrier_actor is None or trail_actor is None:
            raise RuntimeError("Road2/carrier/trail actors not found")

        trail_component_class = unreal.load_class(None, "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent")
        trail_component = trail_actor.get_component_by_class(trail_component_class) if trail_component_class else None
        carrier_component = carrier_actor.get_component_by_class(unreal.StaticMeshComponent)
        trail_source_component = _first_scene_component(trail_actor)
        if trail_component is None or carrier_component is None or trail_source_component is None:
            raise RuntimeError("Trail component, carrier component, or source component missing")

        road_origin, road_extent = _get_bounds(road_actor)
        road_rotation = road_actor.get_actor_rotation()
        focus_origin = unreal.Vector(float(road_origin.x), float(road_origin.y), float(road_origin.z + 20.0))
        ortho_width = float(max(road_extent.x, road_extent.y) * 2.6)

        original_trail_location = trail_actor.get_actor_location()
        original_trail_rotation = trail_actor.get_actor_rotation()
        original_runtime = bool(_safe_property(trail_component, "bEnableRuntimeTrail", False))
        original_visual = bool(_safe_property(trail_component, "bEnableRvtVisualStamp", False))
        original_gate = bool(_safe_property(trail_component, "bUseSourceHeightGate", False))
        original_override = _safe_property(trail_component, "SourceComponentOverride", None)
        original_spacing = float(_safe_property(trail_component, "StampSpacingCm", 5.0))
        original_visible = bool(_safe_property(carrier_component, "visible", True))

        result.update(
            {
                "road_actor_path": _obj_path(road_actor),
                "carrier_actor_path": _obj_path(carrier_actor),
                "trail_actor_path": _obj_path(trail_actor),
                "road_bounds_origin": {"x": float(road_origin.x), "y": float(road_origin.y), "z": float(road_origin.z)},
                "road_bounds_extent": {"x": float(road_extent.x), "y": float(road_extent.y), "z": float(road_extent.z)},
                "before": {},
                "after": {},
                "reference_without_carrier": {},
                "stamp_locations": [],
            }
        )

        result["before"]["topdown"] = _capture_topdown(world, focus_origin, ortho_width, f"{OUTPUT_BASENAME}_before_topdown")
        result["before"]["perspective"] = _capture_perspective(world, focus_origin, road_extent, road_rotation, f"{OUTPUT_BASENAME}_before_perspective")

        trail_actor.set_actor_rotation(road_rotation, False)
        trail_component.set_editor_property("bEnableRuntimeTrail", True)
        trail_component.set_editor_property("bEnableRvtVisualStamp", True)
        trail_component.set_editor_property("bUseSourceHeightGate", False)
        trail_component.set_editor_property("SourceComponentOverride", trail_source_component)
        trail_component.set_editor_property("StampSpacingCm", 5.0)

        start = unreal.Vector(
            float(road_origin.x - ((STAMP_COUNT - 1) * STAMP_STEP_CM * 0.5)),
            float(road_origin.y),
            float(carrier_actor.get_actor_location().z),
        )
        for stamp_index in range(STAMP_COUNT):
            location = unreal.Vector(float(start.x + (stamp_index * STAMP_STEP_CM)), float(start.y), float(start.z))
            trail_actor.set_actor_location(location, False, False)
            ok = bool(trail_component.record_trail_stamp_now())
            result["stamp_locations"].append({"index": int(stamp_index), "ok": ok, "x": float(location.x), "y": float(location.y), "z": float(location.z)})
            _settle(STAMP_SETTLE_SECONDS, 2)

        _settle(POST_STAMP_SETTLE_SECONDS, 4)
        result["after"]["topdown"] = _capture_topdown(world, focus_origin, ortho_width, f"{OUTPUT_BASENAME}_after_topdown")
        result["after"]["perspective"] = _capture_perspective(world, focus_origin, road_extent, road_rotation, f"{OUTPUT_BASENAME}_after_perspective")

        _set_component_visible(carrier_component, False)
        _settle(0.5, 2)
        result["reference_without_carrier"]["topdown"] = _capture_topdown(world, focus_origin, ortho_width, f"{OUTPUT_BASENAME}_reference_topdown")
        result["reference_without_carrier"]["perspective"] = _capture_perspective(world, focus_origin, road_extent, road_rotation, f"{OUTPUT_BASENAME}_reference_perspective")
        _set_component_visible(carrier_component, True)

        trail_actor.set_actor_location(original_trail_location, False, False)
        trail_actor.set_actor_rotation(original_trail_rotation, False)
        trail_component.set_editor_property("bEnableRuntimeTrail", original_runtime)
        trail_component.set_editor_property("bEnableRvtVisualStamp", original_visual)
        trail_component.set_editor_property("bUseSourceHeightGate", original_gate)
        trail_component.set_editor_property("SourceComponentOverride", original_override)
        trail_component.set_editor_property("StampSpacingCm", original_spacing)
        _set_component_visible(carrier_component, original_visible)

        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)

    _write_json(output_path, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
