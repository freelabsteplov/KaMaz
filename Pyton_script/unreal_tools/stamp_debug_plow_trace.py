import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
TEST_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
MPC_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"
BRUSH_MATERIAL_PATH = "/Game/CityPark/SnowSystem/BrushMaterials/MI_Snow_PlowBrush_BoxSafe_350x50x100"
OUTPUT_BASENAME = "stamp_debug_plow_trace"
RENDER_LIB = getattr(unreal, "RenderingLibrary", None)
STAMP_BRUSH_LENGTH_CM = 6000.0
STAMP_BRUSH_WIDTH_CM = 18000.0
STAMP_BRUSH_HEIGHT_CM = 3000.0
STAMP_BRUSH_STRENGTH = 64.0


def _log(message: str) -> None:
    unreal.log(f"[stamp_debug_plow_trace] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[stamp_debug_plow_trace] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_path(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_path_name()
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


def _load_asset(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Could not load asset: {asset_path}")
    return asset


def _get_render_lib():
    if RENDER_LIB is None:
        raise RuntimeError("unreal.RenderingLibrary is unavailable in this UE Python build")
    return RENDER_LIB


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


def _vector_to_dict(value):
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def _get_actor_bounds(actor):
    get_bounds = getattr(actor, "get_actor_bounds", None)
    if callable(get_bounds):
        try:
            origin, extent = get_bounds(True)
            return origin, extent
        except Exception:
            pass

    component = None
    try:
        components = list(actor.get_components_by_class(unreal.PrimitiveComponent) or [])
        if components:
            component = components[0]
    except Exception:
        component = None

    if component is None:
        raise RuntimeError(f"Could not resolve bounds for actor: {_object_path(actor)}")

    bounds = _safe_property(component, "bounds")
    if bounds is None:
        raise RuntimeError(f"Primitive component has no bounds: {_object_path(component)}")
    return bounds.origin, bounds.box_extent


def _get_mpc_vector_default(mpc_asset, parameter_name: str):
    for entry in list(_safe_property(mpc_asset, "vector_parameters", []) or []):
        name = _safe_property(entry, "parameter_name")
        if str(name) != parameter_name:
            continue
        value = _safe_property(entry, "default_value")
        if value is not None:
            return value
    raise RuntimeError(f"Missing vector parameter '{parameter_name}' on {_object_path(mpc_asset)}")


def _set_vector_parameter_default(mpc_asset, parameter_name: str, value) -> bool:
    vector_parameters = list(_safe_property(mpc_asset, "vector_parameters", []) or [])
    for entry in vector_parameters:
        name = _safe_property(entry, "parameter_name")
        if str(name) != parameter_name:
            continue
        entry.set_editor_property("default_value", value)
        mpc_asset.set_editor_property("vector_parameters", vector_parameters)
        mark_dirty = getattr(mpc_asset, "mark_package_dirty", None)
        if callable(mark_dirty):
            mark_dirty()
        return bool(unreal.EditorAssetLibrary.save_loaded_asset(mpc_asset, False))
    raise RuntimeError(f"Missing vector parameter '{parameter_name}' on {_object_path(mpc_asset)}")


def _clear_rt(world, render_target) -> None:
    _get_render_lib().clear_render_target2d(world, render_target, unreal.LinearColor(0.0, 0.0, 0.0, 0.0))


def _draw_rt(world, render_target, material) -> None:
    _get_render_lib().draw_material_to_render_target(world, render_target, material)


def _export_rt(world, render_target, export_dir: str, base_filename: str) -> str:
    os.makedirs(export_dir, exist_ok=True)
    _get_render_lib().export_render_target(world, render_target, export_dir, base_filename)
    png_path = os.path.join(export_dir, f"{base_filename}.png")
    exr_path = os.path.join(export_dir, f"{base_filename}.hdr")
    if os.path.exists(png_path):
        return png_path
    if os.path.exists(exr_path):
        return exr_path
    return ""


def _color_to_dict(value):
    if value is None:
        return None
    return {
        "r": float(getattr(value, "r", 0.0)),
        "g": float(getattr(value, "g", 0.0)),
        "b": float(getattr(value, "b", 0.0)),
        "a": float(getattr(value, "a", 0.0)),
    }


def _sample_rt_at_uv(world, render_target, u: float, v: float):
    try:
        return _get_render_lib().read_render_target_raw_uv(world, render_target, float(u), float(v))
    except Exception as exc:
        _warn(f"read_render_target_raw_uv failed: {exc}")
        return None


def _set_runtime_scalar(mid, parameter_name: str, value: float) -> None:
    setter = getattr(mid, "set_scalar_parameter_value", None)
    if callable(setter):
        setter(parameter_name, float(value))
        return
    raise RuntimeError(f"MaterialInstanceDynamic has no scalar setter for {parameter_name}")


def _create_runtime_stamp_material(parent_material):
    create_fn = getattr(unreal.MaterialInstanceDynamic, "create", None)
    if not callable(create_fn):
        _warn("MaterialInstanceDynamic.create is unavailable; falling back to provided material asset")
        return parent_material
    mid = create_fn(parent_material, None)
    if mid is None:
        raise RuntimeError("Failed to create runtime MaterialInstanceDynamic for stamp")
    _set_runtime_scalar(mid, "BrushLengthCm", STAMP_BRUSH_LENGTH_CM)
    _set_runtime_scalar(mid, "BrushWidthCm", STAMP_BRUSH_WIDTH_CM)
    _set_runtime_scalar(mid, "BrushHeightCm", STAMP_BRUSH_HEIGHT_CM)
    _set_runtime_scalar(mid, "BrushStrength", STAMP_BRUSH_STRENGTH)
    return mid


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    world = _get_editor_world()
    actor = _find_actor(TEST_ACTOR_PATH)
    if actor is None:
        raise RuntimeError(f"Could not find test actor: {TEST_ACTOR_PATH}")

    render_target = _load_asset(RT_PATH)
    mpc_asset = _load_asset(MPC_PATH)
    brush_material = _load_asset(BRUSH_MATERIAL_PATH)
    runtime_brush_material = _create_runtime_stamp_material(brush_material)

    bounds_min = _get_mpc_vector_default(mpc_asset, "WorldBoundsMin")
    bounds_max = _get_mpc_vector_default(mpc_asset, "WorldBoundsMax")
    origin, extent = _get_actor_bounds(actor)

    brush_uv_x = (float(origin.x) - float(bounds_min.r)) / (float(bounds_max.r) - float(bounds_min.r))
    brush_uv_y = (float(origin.y) - float(bounds_min.g)) / (float(bounds_max.g) - float(bounds_min.g))
    brush_uv = unreal.LinearColor(float(brush_uv_x), float(brush_uv_y), 0.0, 0.0)

    mpc_saved = _set_vector_parameter_default(mpc_asset, "BrushUV", brush_uv)
    _clear_rt(world, render_target)
    _draw_rt(world, render_target, runtime_brush_material)
    sampled_color = _sample_rt_at_uv(world, render_target, brush_uv_x, brush_uv_y)

    export_base = OUTPUT_BASENAME
    exported_image_path = _export_rt(world, render_target, output_dir, export_base)

    result = {
        "success": True,
        "map_path": MAP_PATH,
        "actor_path": TEST_ACTOR_PATH,
        "actor_bounds_origin": _vector_to_dict(origin),
        "actor_bounds_extent": _vector_to_dict(extent),
        "render_target_path": _object_path(render_target),
        "brush_material_path": _object_path(brush_material),
        "runtime_brush_material_path": _object_path(runtime_brush_material),
        "runtime_brush_dimensions_cm": {
            "length": STAMP_BRUSH_LENGTH_CM,
            "width": STAMP_BRUSH_WIDTH_CM,
            "height": STAMP_BRUSH_HEIGHT_CM,
        },
        "runtime_brush_strength": STAMP_BRUSH_STRENGTH,
        "mpc_path": _object_path(mpc_asset),
        "mpc_saved": mpc_saved,
        "world_bounds_min": {
            "x": float(bounds_min.r),
            "y": float(bounds_min.g),
            "z": float(bounds_min.b),
        },
        "world_bounds_max": {
            "x": float(bounds_max.r),
            "y": float(bounds_max.g),
            "z": float(bounds_max.b),
        },
        "brush_uv": {
            "x": float(brush_uv_x),
            "y": float(brush_uv_y),
        },
        "sampled_color_at_brush_uv": _color_to_dict(sampled_color),
        "exported_image_path": exported_image_path,
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary() -> str:
    result = run()
    summary = (
        f"Stamped debug plow trace into {_object_path(_load_asset(RT_PATH))} "
        f"at uv=({result['brush_uv']['x']:.4f}, {result['brush_uv']['y']:.4f}) "
        f"export={result.get('exported_image_path', '')}"
    )
    _log(summary)
    _log(f"summary_path={result.get('output_path', '')}")
    return summary


if __name__ == "__main__":
    print(run())
