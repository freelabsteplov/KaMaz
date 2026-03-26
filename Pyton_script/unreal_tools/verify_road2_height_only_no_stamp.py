import hashlib
import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
ROAD_LABEL = "Road2"
CARRIER_LABEL = "SnowHeightBridgeSurface_Road2"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "verify_road2_height_only_no_stamp.json",
)
OUTPUT_DIR = os.path.dirname(OUTPUT_PATH)
CAPTURE_SIZE = 1024


def _write_json(payload):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


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


def _capture(world, focus_origin, road_extent, road_rotation, name):
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


def _mean_abs_channel_diff(path_a, path_b, step=32):
    if not path_a or not path_b or not os.path.exists(path_a) or not os.path.exists(path_b):
        return None
    try:
        import System.Drawing
    except Exception:
        return None

    bmp_a = System.Drawing.Bitmap(path_a)
    bmp_b = System.Drawing.Bitmap(path_b)
    try:
        total = 0.0
        count = 0
        for x in range(0, bmp_a.Width, step):
            for y in range(0, bmp_a.Height, step):
                ca = bmp_a.GetPixel(x, y)
                cb = bmp_b.GetPixel(x, y)
                total += abs(ca.R - cb.R) + abs(ca.G - cb.G) + abs(ca.B - cb.B)
                count += 1
        if count <= 0:
            return 0.0
        return float(total / (count * 3.0))
    finally:
        bmp_a.Dispose()
        bmp_b.Dispose()


def run():
    result = {"success": False, "error": ""}
    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        world = _get_editor_world()
        road_actor = _find_actor_by_label(ROAD_LABEL)
        carrier_actor = _find_actor_by_label(CARRIER_LABEL)
        if road_actor is None or carrier_actor is None:
            raise RuntimeError("Road2/carrier actors not found")

        carrier_component = carrier_actor.get_component_by_class(unreal.StaticMeshComponent)
        if carrier_component is None:
            raise RuntimeError("Carrier component missing")

        road_origin, road_extent = road_actor.get_actor_bounds(False)
        road_rotation = road_actor.get_actor_rotation()
        focus_origin = unreal.Vector(float(road_origin.x), float(road_origin.y), float(road_origin.z + 20.0))

        before_materials = []
        mids = []
        for material_index in range(int(carrier_component.get_num_materials())):
            before_materials.append(carrier_component.get_material(material_index))
            mid = carrier_component.create_and_set_material_instance_dynamic(material_index)
            if mid is None:
                raise RuntimeError(f"Could not create MID for slot {material_index}")
            mids.append(mid)

        for mid in mids:
            mid.set_scalar_parameter_value("HeightAmplitude", 0.0)
        before = _capture(world, focus_origin, road_extent, road_rotation, "verify_road2_height_only_no_stamp_before")

        for mid in mids:
            mid.set_scalar_parameter_value("HeightAmplitude", -50.0)
        after = _capture(world, focus_origin, road_extent, road_rotation, "verify_road2_height_only_no_stamp_after")

        for material_index, material in enumerate(before_materials):
            carrier_component.set_material(material_index, material)

        diff = _mean_abs_channel_diff(before["path"], after["path"])
        result.update(
            {
                "success": True,
                "road_actor_path": road_actor.get_path_name(),
                "carrier_actor_path": carrier_actor.get_path_name(),
                "before": before,
                "after": after,
                "analysis": {
                    "mean_abs_channel_diff": diff,
                    "height_only_changes_image": bool(diff and diff > 0.5),
                },
            }
        )
    except Exception as exc:
        result["error"] = str(exc)

    _write_json(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
