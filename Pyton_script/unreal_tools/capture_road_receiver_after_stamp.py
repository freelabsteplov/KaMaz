import json
import os
import hashlib

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
TEST_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
TEST_COMPONENT_NAME = "StaticMeshComponent0"
SNOW_RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
MPC_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"
BRUSH_MATERIAL_PATH = "/Game/CityPark/SnowSystem/BrushMaterials/MI_Snow_PlowBrush_BoxSafe_350x50x100"
FULLSCREEN_GREEN_MATERIAL_PATH = "/Game/CityPark/SnowSystem/BrushMaterials/M_RT_FullscreenGreen_Test"
OUTPUT_BASENAME = "capture_road_receiver_after_stamp"

RENDER_LIB = unreal.RenderingLibrary
ASSET_LIB = unreal.EditorAssetLibrary


def _log(message: str) -> None:
    unreal.log(f"[capture_road_receiver_after_stamp] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _load_asset(asset_path: str):
    asset = ASSET_LIB.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Could not load asset: {asset_path}")
    return asset


def _object_path(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _object_name(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_name()
    except Exception:
        return str(value)


def _safe_property(obj, property_name: str, default=None):
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


def _find_actor(actor_path: str):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        if _object_path(actor) == actor_path:
            return actor
    return None


def _get_actor_bounds(actor):
    get_bounds = getattr(actor, "get_actor_bounds", None)
    if callable(get_bounds):
        try:
            origin, extent = get_bounds(True)
            return origin, extent
        except Exception:
            pass
    raise RuntimeError(f"Could not resolve bounds for actor: {_object_path(actor)}")


def _get_actor_mesh_materials(actor):
    materials = []
    for component in list(actor.get_components_by_class(unreal.MeshComponent) or []):
        component_entry = {
            "component_path": _object_path(component),
            "materials": [],
        }
        try:
            num_materials = int(component.get_num_materials())
        except Exception:
            num_materials = 0
        for slot_index in range(num_materials):
            try:
                material = component.get_material(slot_index)
            except Exception:
                material = None
            component_entry["materials"].append(
                {
                    "slot_index": int(slot_index),
                    "material_path": _object_path(material),
                }
            )
        materials.append(component_entry)
    return materials


def _find_named_mesh_component(actor, component_name: str):
    for component in list(actor.get_components_by_class(unreal.MeshComponent) or []):
        if str(_object_name(component)) == component_name:
            return component
    mesh_components = list(actor.get_components_by_class(unreal.MeshComponent) or [])
    if mesh_components:
        return mesh_components[0]
    return None


def _disable_nanite_for_component_mesh_in_memory(component) -> dict:
    result = {
        "component_path": _object_path(component),
        "mesh_path": "",
        "found": False,
        "was_enabled": None,
        "updated": False,
        "actions": [],
    }
    mesh = _safe_property(component, "static_mesh")
    if mesh is None or type(mesh).__name__ != "StaticMesh":
        return result

    result["found"] = True
    result["mesh_path"] = _object_path(mesh)
    nanite_settings = _safe_property(mesh, "nanite_settings")
    if nanite_settings is None:
        return result

    was_enabled = _safe_property(nanite_settings, "enabled")
    result["was_enabled"] = bool(was_enabled)
    if not was_enabled:
        return result

    try:
        mesh.modify()
        result["actions"].append("mesh.modify")
    except Exception:
        pass
    try:
        nanite_settings.set_editor_property("enabled", False)
        mesh.set_editor_property("nanite_settings", nanite_settings)
        result["actions"].append("nanite_settings.enabled=False")
        result["updated"] = True
    except Exception:
        return result

    for method_name in ("post_edit_change",):
        method = getattr(mesh, method_name, None)
        if not callable(method):
            continue
        try:
            method()
            result["actions"].append(f"mesh.{method_name}")
        except Exception:
            pass

    for method_name in ("mark_render_state_dirty", "reregister_component", "post_edit_change"):
        method = getattr(component, method_name, None)
        if not callable(method):
            continue
        try:
            method()
            result["actions"].append(f"component.{method_name}")
        except Exception:
            pass

    return result


def _get_mpc_vector_default(mpc_asset, parameter_name: str):
    for entry in list(_safe_property(mpc_asset, "vector_parameters", []) or []):
        if str(_safe_property(entry, "parameter_name")) != parameter_name:
            continue
        value = _safe_property(entry, "default_value")
        if value is not None:
            return value
    raise RuntimeError(f"Missing vector parameter '{parameter_name}' on {_object_path(mpc_asset)}")


def _set_vector_parameter_default(mpc_asset, parameter_name: str, value) -> bool:
    vector_parameters = list(_safe_property(mpc_asset, "vector_parameters", []) or [])
    for entry in vector_parameters:
        if str(_safe_property(entry, "parameter_name")) != parameter_name:
            continue
        entry.set_editor_property("default_value", value)
        mpc_asset.set_editor_property("vector_parameters", vector_parameters)
        mark_dirty = getattr(mpc_asset, "mark_package_dirty", None)
        if callable(mark_dirty):
            mark_dirty()
        return bool(ASSET_LIB.save_loaded_asset(mpc_asset, False))
    raise RuntimeError(f"Missing vector parameter '{parameter_name}' on {_object_path(mpc_asset)}")


def _create_capture_rt(world):
    create_fn = getattr(RENDER_LIB, "create_render_target2d", None)
    if not callable(create_fn):
        raise RuntimeError("RenderingLibrary.create_render_target2d is unavailable")
    fmt = getattr(unreal.TextureRenderTargetFormat, "RTF_RGBA8", None)
    if fmt is not None:
        try:
            return create_fn(world, 1024, 1024, fmt)
        except TypeError:
            pass
    return create_fn(world, 1024, 1024)


def _resolve_capture_source():
    enum_cls = getattr(unreal, "SceneCaptureSource", None)
    if enum_cls is None:
        return None, ""
    for name in (
        "SCS_BASE_COLOR",
        "SCS_BASE_COLOR_LDR",
        "SCS_BASECOLOR",
        "SCS_BASECOLOR_LDR",
        "SCS_FINAL_COLOR_LDR",
        "SCS_FINAL_COLOR_HDR",
        "SCS_FINAL_TONE_CURVE_HDR",
    ):
        value = getattr(enum_cls, name, None)
        if value is not None:
            return value, name
    return None, ""


def _export_rt(world, render_target, output_dir: str, base_filename: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    RENDER_LIB.export_render_target(world, render_target, output_dir, base_filename)
    candidates = (
        os.path.join(output_dir, base_filename),
        os.path.join(output_dir, f"{base_filename}.png"),
        os.path.join(output_dir, f"{base_filename}.hdr"),
    )
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return ""


def _file_sha256(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _capture_view(
    world,
    focus_origin,
    ortho_width: float,
    output_dir: str,
    base_filename: str,
    show_only_actor=None,
    show_only_component=None,
) -> dict:
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    capture_actor = actor_subsystem.spawn_actor_from_class(
        unreal.SceneCapture2D,
        unreal.Vector(float(focus_origin.x), float(focus_origin.y), float(focus_origin.z + 8000.0)),
        unreal.Rotator(-90.0, 0.0, 0.0),
    )
    if capture_actor is None:
        raise RuntimeError("Failed to spawn SceneCapture2D")

    capture_component = capture_actor.get_component_by_class(unreal.SceneCaptureComponent2D)
    if capture_component is None:
        actor_subsystem.destroy_actor(capture_actor)
        raise RuntimeError("Spawned SceneCapture2D has no SceneCaptureComponent2D")

    capture_rt = _create_capture_rt(world)
    try:
        capture_rt.set_editor_property("clear_color", unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
    except Exception:
        pass
    capture_component.set_editor_property("texture_target", capture_rt)
    projection_enum = getattr(unreal.CameraProjectionMode, "ORTHOGRAPHIC", None)
    if projection_enum is not None:
        capture_component.set_editor_property("projection_type", projection_enum)
    capture_component.set_editor_property("ortho_width", float(ortho_width))
    capture_component.set_editor_property("capture_every_frame", False)
    capture_component.set_editor_property("capture_on_movement", False)
    capture_source, capture_source_name = _resolve_capture_source()
    if capture_source is not None:
        capture_component.set_editor_property("capture_source", capture_source)
    if show_only_actor is not None or show_only_component is not None:
        primitive_mode = getattr(unreal.SceneCapturePrimitiveRenderMode, "PRM_UseShowOnlyList", None)
        if primitive_mode is not None:
            capture_component.set_editor_property("primitive_render_mode", primitive_mode)
        try:
            capture_component.clear_show_only_components()
        except Exception:
            pass
        component_added = False
        if show_only_component is not None:
            for method_name in ("show_only_component", "add_show_only_component"):
                method = getattr(capture_component, method_name, None)
                if not callable(method):
                    continue
                try:
                    method(show_only_component)
                    component_added = True
                    break
                except TypeError:
                    try:
                        method(show_only_component, False)
                        component_added = True
                        break
                    except Exception:
                        pass
                except Exception:
                    pass
            if not component_added:
                try:
                    show_only_components = list(_safe_property(capture_component, "show_only_components", []) or [])
                    show_only_components.append(show_only_component)
                    capture_component.set_editor_property("show_only_components", show_only_components)
                    component_added = True
                except Exception:
                    pass
        if not component_added and show_only_actor is not None:
            try:
                capture_component.show_only_actor_components(show_only_actor, False)
            except Exception:
                show_only_list = list(_safe_property(capture_component, "show_only_actors", []) or [])
                show_only_list.append(show_only_actor)
                capture_component.set_editor_property("show_only_actors", show_only_list)

    capture_component.capture_scene()
    capture_component.capture_scene()
    exported_path = _export_rt(world, capture_rt, output_dir, base_filename)
    center_sample = RENDER_LIB.read_render_target_raw_uv(world, capture_rt, 0.5, 0.5)
    quarter_sample = RENDER_LIB.read_render_target_raw_uv(world, capture_rt, 0.5, 0.7)

    grid_max_r = 0.0
    grid_max_g = 0.0
    grid_max_b = 0.0
    grid_min_r = 1.0
    grid_min_g = 1.0
    grid_min_b = 1.0
    magenta_like_samples = 0
    grid_samples = 0
    for y_index in range(1, 16):
        for x_index in range(1, 16):
            u = float(x_index) / 16.0
            v = float(y_index) / 16.0
            sample = RENDER_LIB.read_render_target_raw_uv(world, capture_rt, u, v)
            r = float(getattr(sample, "r", 0.0))
            g = float(getattr(sample, "g", 0.0))
            b = float(getattr(sample, "b", 0.0))
            grid_samples += 1
            grid_max_r = max(grid_max_r, r)
            grid_max_g = max(grid_max_g, g)
            grid_max_b = max(grid_max_b, b)
            grid_min_r = min(grid_min_r, r)
            grid_min_g = min(grid_min_g, g)
            grid_min_b = min(grid_min_b, b)
            if r >= 0.95 and b >= 0.95 and g <= 0.25:
                magenta_like_samples += 1

    try:
        actor_subsystem.destroy_actor(capture_actor)
    except Exception:
        pass

    return {
        "capture_source_name": capture_source_name,
        "show_only_actor_path": _object_path(show_only_actor),
        "show_only_component_path": _object_path(show_only_component),
        "capture_rt_path": _object_path(capture_rt),
        "exported_image_path": exported_path,
        "exported_image_sha256": _file_sha256(exported_path),
        "exported_image_size_bytes": int(os.path.getsize(exported_path)) if exported_path and os.path.exists(exported_path) else 0,
        "capture_center_sample": {
            "r": float(getattr(center_sample, "r", 0.0)),
            "g": float(getattr(center_sample, "g", 0.0)),
            "b": float(getattr(center_sample, "b", 0.0)),
            "a": float(getattr(center_sample, "a", 0.0)),
        },
        "capture_quarter_sample": {
            "r": float(getattr(quarter_sample, "r", 0.0)),
            "g": float(getattr(quarter_sample, "g", 0.0)),
            "b": float(getattr(quarter_sample, "b", 0.0)),
            "a": float(getattr(quarter_sample, "a", 0.0)),
        },
        "capture_grid_stats": {
            "sample_count": int(grid_samples),
            "magenta_like_samples": int(magenta_like_samples),
            "max_r": float(grid_max_r),
            "max_g": float(grid_max_g),
            "max_b": float(grid_max_b),
            "min_r": float(grid_min_r),
            "min_g": float(grid_min_g),
            "min_b": float(grid_min_b),
        },
    }


def _apply_brush_uv_from_actor(mpc_asset, actor_origin):
    bounds_min = _get_mpc_vector_default(mpc_asset, "WorldBoundsMin")
    bounds_max = _get_mpc_vector_default(mpc_asset, "WorldBoundsMax")
    brush_uv_x = (float(actor_origin.x) - float(bounds_min.r)) / (float(bounds_max.r) - float(bounds_min.r))
    brush_uv_y = (float(actor_origin.y) - float(bounds_min.g)) / (float(bounds_max.g) - float(bounds_min.g))
    brush_uv = unreal.LinearColor(float(brush_uv_x), float(brush_uv_y), 0.0, 0.0)
    saved = _set_vector_parameter_default(mpc_asset, "BrushUV", brush_uv)
    return saved, brush_uv_x, brush_uv_y


def _stamp_material(world, render_target, material) -> None:
    RENDER_LIB.clear_render_target2d(world, render_target, unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
    RENDER_LIB.draw_material_to_render_target(world, render_target, material)


def _clear_rt(world, render_target) -> None:
    RENDER_LIB.clear_render_target2d(world, render_target, unreal.LinearColor(0.0, 0.0, 0.0, 0.0))


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    world = _get_editor_world()
    actor = _find_actor(TEST_ACTOR_PATH)
    if actor is None:
        raise RuntimeError(f"Could not find test actor: {TEST_ACTOR_PATH}")
    mesh_component = _find_named_mesh_component(actor, TEST_COMPONENT_NAME)
    if mesh_component is None:
        raise RuntimeError(f"Could not find mesh component '{TEST_COMPONENT_NAME}' on {TEST_ACTOR_PATH}")
    nanite_override = _disable_nanite_for_component_mesh_in_memory(mesh_component)

    render_target = _load_asset(SNOW_RT_PATH)
    mpc_asset = _load_asset(MPC_PATH)
    brush_material = _load_asset(BRUSH_MATERIAL_PATH)
    fullscreen_material = _load_asset(FULLSCREEN_GREEN_MATERIAL_PATH)
    origin, extent = _get_actor_bounds(actor)
    mpc_saved, brush_uv_x, brush_uv_y = _apply_brush_uv_from_actor(mpc_asset, origin)

    brush_sample = {}
    fullscreen_sample = {}

    _stamp_material(world, render_target, brush_material)
    brush_sample["rt_sample_center"] = {
        "r": float(RENDER_LIB.read_render_target_raw_uv(world, render_target, brush_uv_x, brush_uv_y).r),
        "g": float(RENDER_LIB.read_render_target_raw_uv(world, render_target, brush_uv_x, brush_uv_y).g),
        "b": float(RENDER_LIB.read_render_target_raw_uv(world, render_target, brush_uv_x, brush_uv_y).b),
        "a": float(RENDER_LIB.read_render_target_raw_uv(world, render_target, brush_uv_x, brush_uv_y).a),
    }
    brush_sample.update(
        _capture_view(
            world,
            origin,
            max(float(extent.x), float(extent.y), 20000.0),
            output_dir,
            f"{OUTPUT_BASENAME}_brush",
            actor,
            mesh_component,
        )
    )

    _clear_rt(world, render_target)
    fullscreen_sample["rt_sample_center"] = {
        "r": float(RENDER_LIB.read_render_target_raw_uv(world, render_target, 0.5, 0.5).r),
        "g": float(RENDER_LIB.read_render_target_raw_uv(world, render_target, 0.5, 0.5).g),
        "b": float(RENDER_LIB.read_render_target_raw_uv(world, render_target, 0.5, 0.5).b),
        "a": float(RENDER_LIB.read_render_target_raw_uv(world, render_target, 0.5, 0.5).a),
    }
    fullscreen_sample.update(
        _capture_view(
            world,
            origin,
            max(float(extent.x), float(extent.y), 20000.0),
            output_dir,
            f"{OUTPUT_BASENAME}_fullscreen",
            actor,
            mesh_component,
        )
    )

    result = {
        "success": True,
        "map_path": MAP_PATH,
        "actor_path": TEST_ACTOR_PATH,
        "actor_bounds_origin": {
            "x": float(origin.x),
            "y": float(origin.y),
            "z": float(origin.z),
        },
        "actor_bounds_extent": {
            "x": float(extent.x),
            "y": float(extent.y),
            "z": float(extent.z),
        },
        "brush_uv": {"x": float(brush_uv_x), "y": float(brush_uv_y)},
        "mpc_saved": mpc_saved,
        "snow_rt_path": _object_path(render_target),
        "brush_material_path": _object_path(brush_material),
        "fullscreen_material_path": _object_path(fullscreen_material),
        "control_mode": "clear_rt_zero",
        "target_component_name": TEST_COMPONENT_NAME,
        "target_component_path": _object_path(mesh_component),
        "nanite_override": nanite_override,
        "actor_mesh_materials": _get_actor_mesh_materials(actor),
        "brush_capture": brush_sample,
        "fullscreen_capture": fullscreen_sample,
        "capture_exports_equal": bool(
            brush_sample.get("exported_image_sha256")
            and brush_sample.get("exported_image_sha256") == fullscreen_sample.get("exported_image_sha256")
        ),
        "capture_center_equal": bool(
            brush_sample.get("capture_center_sample") == fullscreen_sample.get("capture_center_sample")
        ),
        "capture_quarter_equal": bool(
            brush_sample.get("capture_quarter_sample") == fullscreen_sample.get("capture_quarter_sample")
        ),
    }
    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary() -> str:
    result = run()
    summary = (
        f"brush_capture={result['brush_capture'].get('exported_image_path','')} "
        f"fullscreen_capture={result['fullscreen_capture'].get('exported_image_path','')}"
    )
    _log(summary)
    return summary


if __name__ == "__main__":
    print(run())
