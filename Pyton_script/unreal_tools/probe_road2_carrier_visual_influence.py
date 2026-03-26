import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
ROAD_LABEL = "Road2"
CARRIER_LABEL = "SnowHeightBridgeSurface_Road2"
MI_PATH = "/Game/CityPark/SnowSystem/Receivers/MI_SnowRoadCarrier_Road2"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "probe_road2_carrier_visual_influence.json",
)


def _write_json(payload):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
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


def _safe_get(obj, name, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(name)
        except Exception:
            pass
    return getattr(obj, name, default)


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


def _set_scalar(mi, name, value):
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, name, float(value))


def _set_vector(mi, name, rgba):
    color = unreal.LinearColor(float(rgba[0]), float(rgba[1]), float(rgba[2]), float(rgba[3]))
    unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi, name, color)


def _get_editor_world():
    try:
        return unreal.EditorLevelLibrary.get_editor_world()
    except Exception:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        return subsystem.get_editor_world()


def _capture_center_luma(world, focus_origin):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    capture_actor = actor_subsystem.spawn_actor_from_class(
        unreal.SceneCapture2D,
        unreal.Vector(float(focus_origin.x), float(focus_origin.y), float(focus_origin.z + 2000.0)),
        unreal.Rotator(-90.0, 0.0, 0.0),
    )
    if capture_actor is None:
        raise RuntimeError("Failed to spawn SceneCapture2D")

    capture_component = capture_actor.get_component_by_class(unreal.SceneCaptureComponent2D)
    if capture_component is None:
        actor_subsystem.destroy_actor(capture_actor)
        raise RuntimeError("No SceneCaptureComponent2D")

    rt = unreal.RenderingLibrary.create_render_target2d(world, 1024, 1024, unreal.TextureRenderTargetFormat.RTF_RGBA8)
    capture_component.set_editor_property("texture_target", rt)
    capture_component.set_editor_property("capture_every_frame", False)
    capture_component.set_editor_property("capture_on_movement", False)
    projection_enum = getattr(unreal.CameraProjectionMode, "ORTHOGRAPHIC", None)
    if projection_enum is not None:
        capture_component.set_editor_property("projection_type", projection_enum)
    capture_component.set_editor_property("ortho_width", 2600.0)
    source = getattr(unreal.SceneCaptureSource, "SCS_FINAL_COLOR_LDR", None)
    if source is not None:
        capture_component.set_editor_property("capture_source", source)
    capture_component.capture_scene()
    capture_component.capture_scene()

    sample = unreal.RenderingLibrary.read_render_target_raw_uv(world, rt, 0.5, 0.5)
    rgb = {
        "r": float(getattr(sample, "r", 0.0)),
        "g": float(getattr(sample, "g", 0.0)),
        "b": float(getattr(sample, "b", 0.0)),
        "a": float(getattr(sample, "a", 0.0)),
    }
    luma = (0.2126 * rgb["r"]) + (0.7152 * rgb["g"]) + (0.0722 * rgb["b"])

    try:
        actor_subsystem.destroy_actor(capture_actor)
    except Exception:
        pass

    return {"sample": rgb, "luma": luma}


def main():
    result = {
        "success": False,
        "map_path": MAP_PATH,
        "mi_path": MI_PATH,
        "road_actor_path": "",
        "carrier_actor_path": "",
        "carrier_visible_before": None,
        "mi_values_before": {},
        "mi_values_test": {},
        "capture_carrier_on": {},
        "capture_carrier_off": {},
        "delta": {},
        "error": "",
    }

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        world = _get_editor_world()

        road_actor = _find_actor_by_label(ROAD_LABEL)
        carrier_actor = _find_actor_by_label(CARRIER_LABEL)
        if road_actor is None:
            raise RuntimeError(f"Road actor not found: {ROAD_LABEL}")
        if carrier_actor is None:
            raise RuntimeError(f"Carrier actor not found: {CARRIER_LABEL}")

        result["road_actor_path"] = road_actor.get_path_name()
        result["carrier_actor_path"] = carrier_actor.get_path_name()

        carrier_comp = carrier_actor.get_component_by_class(unreal.StaticMeshComponent)
        if carrier_comp is None:
            raise RuntimeError("Carrier has no StaticMeshComponent")

        result["carrier_visible_before"] = bool(_safe_get(carrier_comp, "visible", True))

        mi = unreal.EditorAssetLibrary.load_asset(MI_PATH)
        if mi is None:
            raise RuntimeError(f"MI not found: {MI_PATH}")

        old_height = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, "HeightAmplitude")
        old_clear = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, "VisualClearMaskStrength")
        old_thin = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, "ThinSnowMinVisualOpacity")
        old_pressed = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mi, "PressedSnowColor")
        old_under = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mi, "ThinSnowUnderColor")

        result["mi_values_before"] = {
            "HeightAmplitude": float(old_height),
            "VisualClearMaskStrength": float(old_clear),
            "ThinSnowMinVisualOpacity": float(old_thin),
            "PressedSnowColor": [float(old_pressed.r), float(old_pressed.g), float(old_pressed.b), float(old_pressed.a)],
            "ThinSnowUnderColor": [float(old_under.r), float(old_under.g), float(old_under.b), float(old_under.a)],
        }

        _set_scalar(mi, "HeightAmplitude", -50.0)
        _set_scalar(mi, "VisualClearMaskStrength", 0.0)
        _set_scalar(mi, "ThinSnowMinVisualOpacity", 1.0)
        _set_scalar(mi, "RoadSnowVisualWhitenStrength", 0.0)
        _set_scalar(mi, "RoadSnowRecoveredBehavior", 0.0)
        _set_vector(mi, "PressedSnowColor", (1.0, 0.0, 0.0, 1.0))
        _set_vector(mi, "ThinSnowUnderColor", (1.0, 0.0, 0.0, 1.0))
        _set_vector(mi, "RoadSnowVisualColor", (1.0, 0.0, 0.0, 1.0))
        unreal.MaterialEditingLibrary.update_material_instance(mi)

        result["mi_values_test"] = {
            "HeightAmplitude": float(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, "HeightAmplitude")),
            "VisualClearMaskStrength": float(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, "VisualClearMaskStrength")),
            "ThinSnowMinVisualOpacity": float(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, "ThinSnowMinVisualOpacity")),
        }

        road_origin, _ = road_actor.get_actor_bounds(True)
        _set_component_visible(carrier_comp, True)
        result["capture_carrier_on"] = _capture_center_luma(world, road_origin)

        _set_component_visible(carrier_comp, False)
        result["capture_carrier_off"] = _capture_center_luma(world, road_origin)

        _set_component_visible(carrier_comp, result["carrier_visible_before"])

        _set_scalar(mi, "HeightAmplitude", float(old_height))
        _set_scalar(mi, "VisualClearMaskStrength", float(old_clear))
        _set_scalar(mi, "ThinSnowMinVisualOpacity", float(old_thin))
        _set_vector(mi, "PressedSnowColor", (old_pressed.r, old_pressed.g, old_pressed.b, old_pressed.a))
        _set_vector(mi, "ThinSnowUnderColor", (old_under.r, old_under.g, old_under.b, old_under.a))
        unreal.MaterialEditingLibrary.update_material_instance(mi)

        on_luma = float(result["capture_carrier_on"]["luma"])
        off_luma = float(result["capture_carrier_off"]["luma"])
        result["delta"] = {
            "luma_delta_on_minus_off": on_luma - off_luma,
            "carrier_affects_frame": abs(on_luma - off_luma) > 0.5,
            "on_center_sample": result["capture_carrier_on"]["sample"],
            "off_center_sample": result["capture_carrier_off"]["sample"],
        }
        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)

    _write_json(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
