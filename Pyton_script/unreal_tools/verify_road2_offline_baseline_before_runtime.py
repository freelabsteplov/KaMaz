import hashlib
import json
import math
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
ROAD_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
CARRIER_LABEL = "SnowHeightBridgeSurface_Road2"
MI_PATH = "/Game/CityPark/SnowSystem/Receivers/MI_SnowRoadCarrier_Road2"
EXPECTED_PARENT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP"
OUTPUT_BASENAME = "verify_road2_offline_baseline_before_runtime"
CAPTURE_SIZE = 1024
TOPDOWN_ORTHO_WIDTH_CM = 2600.0
PERSPECTIVE_OFFSET = unreal.Vector(-900.0, -1400.0, 260.0)
SIDE_PROFILE_OFFSET = unreal.Vector(-450.0, -1700.0, 120.0)
SIDE_PROFILE_LOOK_OFFSET = unreal.Vector(0.0, 0.0, 10.0)

RENDER_LIB = unreal.RenderingLibrary


def _saved_output_dir():
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return path


def _object_path(obj):
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _safe_get(obj, prop_name, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(prop_name)
        except Exception:
            pass
    return getattr(obj, prop_name, default)


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


def _make_rotator(pitch, yaw, roll=0.0):
    rotator = unreal.Rotator()
    rotator.pitch = float(pitch)
    rotator.yaw = float(yaw)
    rotator.roll = float(roll)
    return rotator


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


def _sample_grid(world, render_target, uv_points):
    samples = []
    for u, v in uv_points:
        rgb = _sample_rgb(world, render_target, u, v)
        samples.append(
            {
                "u": float(u),
                "v": float(v),
                "rgba": rgb,
                "luma": _luma(rgb),
            }
        )
    return samples


def _max_sample_delta(samples_a, samples_b):
    max_delta = 0.0
    for sample_a, sample_b in zip(samples_a or [], samples_b or []):
        rgba_a = sample_a.get("rgba", {})
        rgba_b = sample_b.get("rgba", {})
        for key in ("r", "g", "b", "a"):
            max_delta = max(max_delta, abs(float(rgba_a.get(key, 0.0)) - float(rgba_b.get(key, 0.0))))
    return max_delta


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
        try:
            capture_component.show_only_actor_components(actor, False)
            continue
        except Exception:
            pass
        try:
            show_only_list = list(_safe_get(capture_component, "show_only_actors", []) or [])
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
        raise RuntimeError("Topdown SceneCapture2D missing SceneCaptureComponent2D")

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

    capture_component.capture_scene()
    capture_component.capture_scene()

    exported_path = _export_rt(world, capture_rt, output_dir, f"{OUTPUT_BASENAME}_{suffix}_topdown")
    center = _sample_rgb(world, capture_rt, 0.50, 0.50)
    left = _sample_rgb(world, capture_rt, 0.32, 0.50)
    right = _sample_rgb(world, capture_rt, 0.68, 0.50)
    sample_grid = _sample_grid(
        world,
        capture_rt,
        (
            (0.25, 0.25),
            (0.50, 0.25),
            (0.75, 0.25),
            (0.25, 0.50),
            (0.50, 0.50),
            (0.75, 0.50),
            (0.25, 0.75),
            (0.50, 0.75),
            (0.75, 0.75),
        ),
    )

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
        "sample_grid": sample_grid,
    }


def _capture_perspective(world, focus_origin, output_dir, suffix, show_only_actors=None):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    camera_location = focus_origin + PERSPECTIVE_OFFSET
    camera_rotation = _rotator_towards(camera_location, focus_origin + unreal.Vector(0.0, 0.0, 35.0))
    capture_actor = actor_subsystem.spawn_actor_from_class(unreal.SceneCapture2D, camera_location, camera_rotation)
    if capture_actor is None:
        raise RuntimeError("Failed to spawn perspective SceneCapture2D")

    capture_component = capture_actor.get_component_by_class(unreal.SceneCaptureComponent2D)
    if capture_component is None:
        actor_subsystem.destroy_actor(capture_actor)
        raise RuntimeError("Perspective SceneCapture2D missing SceneCaptureComponent2D")

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

    capture_component.capture_scene()
    capture_component.capture_scene()

    exported_path = _export_rt(world, capture_rt, output_dir, f"{OUTPUT_BASENAME}_{suffix}_perspective")
    center = _sample_rgb(world, capture_rt, 0.50, 0.58)
    sample_grid = _sample_grid(
        world,
        capture_rt,
        (
            (0.40, 0.48),
            (0.50, 0.48),
            (0.60, 0.48),
            (0.40, 0.58),
            (0.50, 0.58),
            (0.60, 0.58),
            (0.40, 0.68),
            (0.50, 0.68),
            (0.60, 0.68),
        ),
    )

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
        "sample_grid": sample_grid,
    }


def _capture_side_profile(world, focus_origin, output_dir, suffix, show_only_actors=None):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    camera_location = focus_origin + SIDE_PROFILE_OFFSET
    camera_rotation = _rotator_towards(camera_location, focus_origin + SIDE_PROFILE_LOOK_OFFSET)
    capture_actor = actor_subsystem.spawn_actor_from_class(unreal.SceneCapture2D, camera_location, camera_rotation)
    if capture_actor is None:
        raise RuntimeError("Failed to spawn side profile SceneCapture2D")

    capture_component = capture_actor.get_component_by_class(unreal.SceneCaptureComponent2D)
    if capture_component is None:
        actor_subsystem.destroy_actor(capture_actor)
        raise RuntimeError("Side profile SceneCapture2D missing SceneCaptureComponent2D")

    capture_rt = _create_capture_rt(world)
    capture_component.set_editor_property("texture_target", capture_rt)
    capture_component.set_editor_property("capture_every_frame", False)
    capture_component.set_editor_property("capture_on_movement", False)
    capture_source, capture_source_name = _resolve_capture_source()
    if capture_source is not None:
        capture_component.set_editor_property("capture_source", capture_source)
    _configure_show_only(capture_component, show_only_actors)

    capture_component.capture_scene()
    capture_component.capture_scene()

    exported_path = _export_rt(world, capture_rt, output_dir, f"{OUTPUT_BASENAME}_{suffix}_side")
    center = _sample_rgb(world, capture_rt, 0.50, 0.60)
    sample_grid = _sample_grid(
        world,
        capture_rt,
        (
            (0.40, 0.50),
            (0.50, 0.50),
            (0.60, 0.50),
            (0.40, 0.60),
            (0.50, 0.60),
            (0.60, 0.60),
            (0.40, 0.70),
            (0.50, 0.70),
            (0.60, 0.70),
        ),
    )

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
        "sample_grid": sample_grid,
    }


def _material_scalar(material, param_name):
    try:
        return float(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material, param_name))
    except Exception:
        return None


def _matches_asset_path(object_path, expected_asset_path):
    if not object_path or not expected_asset_path:
        return False
    return object_path == expected_asset_path or object_path.startswith(f"{expected_asset_path}.")


def run(output_dir=None):
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    world = _get_editor_world()
    road_actor = _find_actor_by_path(ROAD_ACTOR_PATH)
    carrier_actor = _find_actor_by_label(CARRIER_LABEL)
    if road_actor is None:
        raise RuntimeError(f"Missing road actor: {ROAD_ACTOR_PATH}")
    if carrier_actor is None:
        raise RuntimeError(f"Missing carrier actor: {CARRIER_LABEL}")

    mi = unreal.EditorAssetLibrary.load_asset(MI_PATH)
    if mi is None:
        raise RuntimeError(f"Missing MI: {MI_PATH}")

    carrier_component = carrier_actor.get_component_by_class(unreal.StaticMeshComponent)
    if carrier_component is None:
        raise RuntimeError("Carrier StaticMeshComponent not found")

    road_origin, road_extent = _get_actor_bounds(road_actor)
    focus_origin = carrier_actor.get_actor_location()
    road_and_carrier = [road_actor, carrier_actor]
    road_only = [road_actor]
    carrier_only = [carrier_actor]

    carrier_material = carrier_component.get_material(0)
    result = {
        "success": False,
        "map_path": MAP_PATH,
        "road_actor_path": _object_path(road_actor),
        "carrier_actor_path": _object_path(carrier_actor),
        "mi_path": MI_PATH,
        "mi_parent_path": _object_path(_safe_get(mi, "parent", None)),
        "carrier_material_path": _object_path(carrier_material),
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
        "mi_scalars": {
            "HeightAmplitude": _material_scalar(mi, "HeightAmplitude"),
            "VisualClearMaskStrength": _material_scalar(mi, "VisualClearMaskStrength"),
            "DepthMaskBoost": _material_scalar(mi, "DepthMaskBoost"),
            "ThinSnowMinVisualOpacity": _material_scalar(mi, "ThinSnowMinVisualOpacity"),
            "RoadSnowVisualWhitenStrength": _material_scalar(mi, "RoadSnowVisualWhitenStrength"),
            "RoadSnowRecoveredBehavior": _material_scalar(mi, "RoadSnowRecoveredBehavior"),
        },
        "captures": {},
        "analysis": {},
        "error": "",
    }

    try:
        if not _matches_asset_path(result["mi_parent_path"], EXPECTED_PARENT_PATH):
            raise RuntimeError(
                f"Unexpected MI parent. Expected {EXPECTED_PARENT_PATH}, got {result['mi_parent_path']}"
            )

        result["captures"]["with_carrier"] = {
            "topdown": _capture_topdown(world, focus_origin, output_dir, "with_carrier", road_and_carrier),
            "perspective": _capture_perspective(world, focus_origin, output_dir, "with_carrier", road_and_carrier),
            "side_profile": _capture_side_profile(world, focus_origin, output_dir, "with_carrier", road_and_carrier),
        }
        result["captures"]["without_carrier"] = {
            "topdown": _capture_topdown(world, focus_origin, output_dir, "without_carrier", road_only),
            "perspective": _capture_perspective(world, focus_origin, output_dir, "without_carrier", road_only),
            "side_profile": _capture_side_profile(world, focus_origin, output_dir, "without_carrier", road_only),
        }
        result["captures"]["carrier_only"] = {
            "topdown": _capture_topdown(world, focus_origin, output_dir, "carrier_only", carrier_only),
            "perspective": _capture_perspective(world, focus_origin, output_dir, "carrier_only", carrier_only),
            "side_profile": _capture_side_profile(world, focus_origin, output_dir, "carrier_only", carrier_only),
        }

        with_carrier = result["captures"]["with_carrier"]
        without_carrier = result["captures"]["without_carrier"]
        carrier_only_capture = result["captures"]["carrier_only"]
        topdown_sample_delta = _max_sample_delta(
            with_carrier["topdown"]["sample_grid"],
            without_carrier["topdown"]["sample_grid"],
        )
        perspective_sample_delta = _max_sample_delta(
            with_carrier["perspective"]["sample_grid"],
            without_carrier["perspective"]["sample_grid"],
        )
        side_profile_sample_delta = _max_sample_delta(
            with_carrier["side_profile"]["sample_grid"],
            without_carrier["side_profile"]["sample_grid"],
        )

        result["analysis"] = {
            "topdown_hash_changed_vs_road_only": (
                with_carrier["topdown"]["exported_image_sha256"] != without_carrier["topdown"]["exported_image_sha256"]
            ),
            "perspective_hash_changed_vs_road_only": (
                with_carrier["perspective"]["exported_image_sha256"]
                != without_carrier["perspective"]["exported_image_sha256"]
            ),
            "side_profile_hash_changed_vs_road_only": (
                with_carrier["side_profile"]["exported_image_sha256"]
                != without_carrier["side_profile"]["exported_image_sha256"]
            ),
            "topdown_center_luma_delta": (
                float(with_carrier["topdown"]["luma"]["center"]) - float(without_carrier["topdown"]["luma"]["center"])
            ),
            "perspective_center_luma_delta": (
                float(with_carrier["perspective"]["center_luma"])
                - float(without_carrier["perspective"]["center_luma"])
            ),
            "side_profile_center_luma_delta": (
                float(with_carrier["side_profile"]["center_luma"])
                - float(without_carrier["side_profile"]["center_luma"])
            ),
            "topdown_max_sample_delta": topdown_sample_delta,
            "perspective_max_sample_delta": perspective_sample_delta,
            "side_profile_max_sample_delta": side_profile_sample_delta,
            "carrier_only_visible_in_topdown": bool(carrier_only_capture["topdown"]["exported_image_sha256"]),
            "carrier_only_visible_in_perspective": bool(carrier_only_capture["perspective"]["exported_image_sha256"]),
            "carrier_only_visible_in_side_profile": bool(carrier_only_capture["side_profile"]["exported_image_sha256"]),
            "visible_baseline_response_detected": any(
                (
                    topdown_sample_delta > 0.5,
                    perspective_sample_delta > 0.5,
                    side_profile_sample_delta > 0.5,
                )
            ),
        }
        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run()
