import json
import os

import unreal


MAP_PATH = "/Game/LandscapeDeformation/Maps/SnowMap"
LANDSCAPE_LABEL = "Landscape"
BP_CAPTURE_LABEL = "BP_Capture"
VHM_MI_PATH = "/Game/LandscapeDeformation/Material/MI_VHM_SnowLand"
RT_CAPTURE_PATH = "/Game/LandscapeDeformation/Textures/RenderTargets/RT_Capture"
RT_PERSISTENT_PATH = "/Game/LandscapeDeformation/Textures/RenderTargets/RT_Persistent"
TARGET_RT_SIZE = 2048
REFERENCE_CAPTURE_ORTHO_WIDTH_CM = 16400.0
REFERENCE_CAPTURE_RT_SIZE = 2048.0
TARGET_DISPLACEMENT_HEIGHT = 50.0
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "apply_snowmap_full_map_capture_and_height.json",
)


def _path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _label(actor):
    if not actor:
        return ""
    try:
        return actor.get_actor_label()
    except Exception:
        try:
            return actor.get_name()
        except Exception:
            return ""


def _safe_prop(obj, name, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(name)
        except Exception:
            pass
    try:
        return getattr(obj, name)
    except Exception:
        return default


def _scalar(material_interface, parameter_name):
    if not material_interface:
        return None
    try:
        return float(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material_interface, parameter_name))
    except Exception:
        return None


def _find_actor_by_label(target_label):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_subsystem.get_all_level_actors() or []:
        if _label(actor) == target_label:
            return actor
    return None


def _save_loaded(asset, asset_path=None):
    if not asset:
        return False
    try:
        if asset_path:
            return bool(unreal.EditorAssetLibrary.save_asset(asset_path, False))
    except Exception:
        pass
    try:
        return bool(unreal.EditorAssetLibrary.save_loaded_asset(asset, False))
    except Exception:
        return False


def _save_current_level():
    try:
        level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if level_editor:
            return bool(level_editor.save_current_level())
    except Exception:
        pass
    try:
        return bool(unreal.EditorLevelLibrary.save_current_level())
    except Exception:
        return False


def _configure_render_target(asset_path):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Missing render target: {asset_path}")

    before = {
        "path": _path(asset),
        "size_x": int(_safe_prop(asset, "size_x", 0) or 0),
        "size_y": int(_safe_prop(asset, "size_y", 0) or 0),
        "format": str(_safe_prop(asset, "render_target_format", None)),
    }

    asset.set_editor_property("size_x", TARGET_RT_SIZE)
    asset.set_editor_property("size_y", TARGET_RT_SIZE)

    post_edit_change = getattr(asset, "post_edit_change", None)
    if callable(post_edit_change):
        post_edit_change()

    after = {
        "size_x": int(_safe_prop(asset, "size_x", 0) or 0),
        "size_y": int(_safe_prop(asset, "size_y", 0) or 0),
        "saved": _save_loaded(asset, asset_path),
    }
    return before, after


def main():
    payload = {
        "map_path": MAP_PATH,
        "bp_capture": {},
        "rt_capture": {},
        "rt_persistent": {},
        "vhm_material": {},
        "save_ok": False,
        "error": "",
    }

    try:
        world = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        if not world:
            raise RuntimeError(f"Could not load map: {MAP_PATH}")

        landscape = _find_actor_by_label(LANDSCAPE_LABEL)
        bp_capture = _find_actor_by_label(BP_CAPTURE_LABEL)
        if landscape is None:
            raise RuntimeError(f"Landscape actor '{LANDSCAPE_LABEL}' not found")
        if bp_capture is None:
            raise RuntimeError(f"Capture actor '{BP_CAPTURE_LABEL}' not found")

        landscape_origin, landscape_extent = landscape.get_actor_bounds(False)
        landscape_max_span_cm = max(float(landscape_extent.x), float(landscape_extent.y)) * 2.0
        target_ortho_width = float(REFERENCE_CAPTURE_ORTHO_WIDTH_CM)

        scene_capture_component = None
        for component in bp_capture.get_components_by_class(unreal.ActorComponent) or []:
            if "SceneCaptureComponent2D" in component.get_class().get_name():
                scene_capture_component = component
                break
        if scene_capture_component is None:
            raise RuntimeError("BP_Capture has no SceneCaptureComponent2D")

        before_ortho = float(_safe_prop(scene_capture_component, "ortho_width", 0.0) or 0.0)
        scene_capture_component.set_editor_property("ortho_width", float(target_ortho_width))
        payload["bp_capture"] = {
            "path": _path(bp_capture),
            "scene_capture_component": _path(scene_capture_component),
            "landscape_span_cm": float(landscape_max_span_cm),
            "ortho_width_before": before_ortho,
            "ortho_width_after": float(_safe_prop(scene_capture_component, "ortho_width", 0.0) or 0.0),
        }

        rt_capture_before, rt_capture_after = _configure_render_target(RT_CAPTURE_PATH)
        rt_persistent_before, rt_persistent_after = _configure_render_target(RT_PERSISTENT_PATH)
        payload["rt_capture"] = {"before": rt_capture_before, "after": rt_capture_after}
        payload["rt_persistent"] = {"before": rt_persistent_before, "after": rt_persistent_after}

        vhm_material = unreal.EditorAssetLibrary.load_asset(VHM_MI_PATH)
        if vhm_material is None:
            raise RuntimeError(f"Missing VHM material instance: {VHM_MI_PATH}")

        displacement_before = _scalar(vhm_material, "DisplacementHeight")
        if displacement_before is None:
            raise RuntimeError("Could not read MI_VHM_SnowLand.DisplacementHeight")
        displacement_after = float(TARGET_DISPLACEMENT_HEIGHT)
        unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
            vhm_material,
            "DisplacementHeight",
            displacement_after,
        )
        payload["vhm_material"] = {
            "path": _path(vhm_material),
            "displacement_height_before": float(displacement_before),
            "displacement_height_after": float(_scalar(vhm_material, "DisplacementHeight") or 0.0),
            "saved": _save_loaded(vhm_material, VHM_MI_PATH),
        }

        payload["save_ok"] = _save_current_level()
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
