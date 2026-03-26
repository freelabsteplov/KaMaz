import json
import math
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
RVT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP"
BASE_RECEIVER_M_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_MVP"
BASE_RECEIVER_MI_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_MVP"
HEIGHT_M_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP"
HEIGHT_MI_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP"

TARGET_LABEL = "SnowTestGround"
TARGET_SLOT = 0
WRITER_LABEL = "VT_MVP_DebugWriter"
HEIGHT_ACTOR_LABEL = "SnowHeightTestSurface_MVP"
HEIGHT_MESH_PATH = "/Engine/EditorMeshes/EditorSphere.EditorSphere"


ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
ASSET_LIB = unreal.EditorAssetLibrary
MATERIAL_LIB = unreal.MaterialEditingLibrary


def _log(msg: str):
    unreal.log(f"[phase3_real_height_mvp] {msg}")


def _safe_set(obj, prop, value) -> bool:
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception:
        return False


def _load_asset(path: str):
    return ASSET_LIB.load_asset(path)


def _object_path(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _get_saved_output_path() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation", "phase3_real_height_mvp.json")


def _write_output(payload: dict):
    path = _get_saved_output_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return path


def _find_actor_by_label(label: str):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_subsystem.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def _first_static_mesh_component(actor):
    if actor is None:
        return None
    return actor.get_component_by_class(unreal.StaticMeshComponent)


def _mesh_verts(mesh) -> int:
    if mesh is None:
        return -1
    sm_subsys = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    try:
        return int(sm_subsys.get_number_verts(mesh, 0))
    except Exception:
        return -1


def _surface_viability(actor) -> dict:
    result = {
        "actor_path": _object_path(actor),
        "component_path": "",
        "mesh_path": "",
        "lod0_verts": -1,
        "world_size_x": 0.0,
        "world_size_y": 0.0,
        "area_xy": 0.0,
        "spacing_estimate": 0.0,
        "viable": False,
    }

    comp = _first_static_mesh_component(actor)
    if comp is None:
        return result

    mesh = comp.get_editor_property("static_mesh")
    result["component_path"] = _object_path(comp)
    result["mesh_path"] = _object_path(mesh)
    result["lod0_verts"] = _mesh_verts(mesh)

    _, ext = actor.get_actor_bounds(False)
    world_size_x = float(ext.x) * 2.0
    world_size_y = float(ext.y) * 2.0
    area_xy = max(1.0, world_size_x * world_size_y)
    spacing = math.sqrt(area_xy / max(1.0, float(max(1, result["lod0_verts"]))))

    result["world_size_x"] = world_size_x
    result["world_size_y"] = world_size_y
    result["area_xy"] = area_xy
    result["spacing_estimate"] = spacing

    # Heuristic for visible local WPO in debug MVP.
    result["viable"] = bool(result["lod0_verts"] >= 500 and spacing <= 75.0)
    return result


def _ensure_material(asset_path: str):
    existing = _load_asset(asset_path)
    if existing is not None and isinstance(existing, unreal.Material):
        return existing, False

    package_path, asset_name = asset_path.rsplit("/", 1)
    if not ASSET_LIB.does_directory_exist(package_path):
        ASSET_LIB.make_directory(package_path)

    if ASSET_LIB.does_asset_exist(asset_path):
        ASSET_LIB.delete_asset(asset_path)

    created = ASSET_TOOLS.create_asset(
        asset_name,
        package_path,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if created is None:
        raise RuntimeError(f"Failed to create material: {asset_path}")
    return created, True


def _ensure_material_instance(asset_path: str):
    existing = _load_asset(asset_path)
    if existing is not None and isinstance(existing, unreal.MaterialInstanceConstant):
        return existing, False

    package_path, asset_name = asset_path.rsplit("/", 1)
    if not ASSET_LIB.does_directory_exist(package_path):
        ASSET_LIB.make_directory(package_path)

    if ASSET_LIB.does_asset_exist(asset_path):
        ASSET_LIB.delete_asset(asset_path)

    created = ASSET_TOOLS.create_asset(
        asset_name,
        package_path,
        unreal.MaterialInstanceConstant,
        unreal.MaterialInstanceConstantFactoryNew(),
    )
    if created is None:
        raise RuntimeError(f"Failed to create material instance: {asset_path}")
    return created, True


def _new_expr(material, class_name, x, y):
    cls = getattr(unreal, class_name, None)
    if cls is None:
        raise RuntimeError(f"Missing class: {class_name}")
    expr = MATERIAL_LIB.create_material_expression(material, cls, x, y)
    if expr is None:
        raise RuntimeError(f"Could not create expression: {class_name}")
    return expr


def _connect(source, source_names, target, target_names):
    if isinstance(source_names, str):
        source_names = [source_names]
    if isinstance(target_names, str):
        target_names = [target_names]
    for src in source_names:
        for dst in target_names:
            try:
                MATERIAL_LIB.connect_material_expressions(source, src, target, dst)
                return {"ok": True, "src": src, "dst": dst}
            except Exception:
                pass
    return {"ok": False, "src": "", "dst": ""}


def _new_scalar_param(material, x, y, name, default):
    expr = _new_expr(material, "MaterialExpressionScalarParameter", x, y)
    _safe_set(expr, "parameter_name", name)
    _safe_set(expr, "default_value", float(default))
    return expr


def _new_vector_param(material, x, y, name, rgb):
    expr = _new_expr(material, "MaterialExpressionVectorParameter", x, y)
    _safe_set(expr, "parameter_name", name)
    _safe_set(expr, "default_value", unreal.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))
    return expr


def build_height_material() -> dict:
    mat, created = _ensure_material(HEIGHT_M_PATH)
    rvt_asset = _load_asset(RVT_PATH)
    if rvt_asset is None:
        raise RuntimeError(f"Missing RVT asset: {RVT_PATH}")

    MATERIAL_LIB.delete_all_material_expressions(mat)
    _safe_set(mat, "material_domain", unreal.MaterialDomain.MD_SURFACE)
    _safe_set(mat, "blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    _safe_set(mat, "shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)

    sample = _new_expr(mat, "MaterialExpressionRuntimeVirtualTextureSampleParameter", -1400, -80)
    _safe_set(sample, "parameter_name", "SnowRVT")
    _safe_set(sample, "group", "RVT")
    _safe_set(sample, "sort_priority", 0)
    _safe_set(sample, "virtual_texture", rvt_asset)
    mt = getattr(unreal.RuntimeVirtualTextureMaterialType, "BASE_COLOR_NORMAL_SPECULAR_MASK_Y_CO_CG", None)
    if mt is not None:
        _safe_set(sample, "material_type", mt)

    mask_sat = _new_expr(mat, "MaterialExpressionSaturate", -1160, -80)
    c1 = _connect(sample, ["Mask", "mask", "A", ""], mask_sat, ["", "Input"])

    height_contrast = _new_scalar_param(mat, -1400, 80, "HeightContrast", 2.0)
    mask_pow = _new_expr(mat, "MaterialExpressionPower", -920, -20)
    c2 = _connect(mask_sat, [""], mask_pow, ["Base", "A"])
    c3 = _connect(height_contrast, [""], mask_pow, ["Exp", "B"])

    height_bias = _new_scalar_param(mat, -1400, 220, "HeightBias", 0.0)
    height_bias_sub = _new_expr(mat, "MaterialExpressionSubtract", -680, 40)
    c4 = _connect(mask_pow, [""], height_bias_sub, ["A"])
    c5 = _connect(height_bias, [""], height_bias_sub, ["B"])

    height_amp = _new_scalar_param(mat, -1400, 360, "HeightAmplitude", -25.0)
    height_scalar = _new_expr(mat, "MaterialExpressionMultiply", -460, 120)
    c6 = _connect(height_bias_sub, [""], height_scalar, ["A"])
    c7 = _connect(height_amp, [""], height_scalar, ["B"])

    world_up = _new_expr(mat, "MaterialExpressionConstant3Vector", -700, 260)
    _safe_set(world_up, "constant", unreal.LinearColor(0.0, 0.0, 1.0, 1.0))
    wpo_mul = _new_expr(mat, "MaterialExpressionMultiply", -240, 250)
    c8 = _connect(world_up, [""], wpo_mul, ["A"])
    c9 = _connect(height_scalar, [""], wpo_mul, ["B"])

    snow_color = _new_vector_param(mat, -1400, 560, "SnowColor", (1.0, 1.0, 1.0))
    pressed_color = _new_vector_param(mat, -1400, 720, "PressedSnowColor", (0.22, 0.22, 0.22))
    base_lerp = _new_expr(mat, "MaterialExpressionLinearInterpolate", -920, 640)
    c10 = _connect(snow_color, [""], base_lerp, ["A"])
    c11 = _connect(pressed_color, [""], base_lerp, ["B"])
    c12 = _connect(mask_pow, [""], base_lerp, ["Alpha"])

    snow_rough = _new_scalar_param(mat, -1400, 900, "SnowRoughness", 0.9)
    pressed_rough = _new_scalar_param(mat, -1400, 1020, "PressedRoughness", 0.45)
    rough_lerp = _new_expr(mat, "MaterialExpressionLinearInterpolate", -920, 960)
    c13 = _connect(snow_rough, [""], rough_lerp, ["A"])
    c14 = _connect(pressed_rough, [""], rough_lerp, ["B"])
    c15 = _connect(mask_pow, [""], rough_lerp, ["Alpha"])

    MATERIAL_LIB.connect_material_property(base_lerp, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MATERIAL_LIB.connect_material_property(rough_lerp, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MATERIAL_LIB.connect_material_property(wpo_mul, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)

    MATERIAL_LIB.recompile_material(mat)
    MATERIAL_LIB.layout_material_expressions(mat)
    saved = bool(ASSET_LIB.save_loaded_asset(mat, False))

    return {
        "material_path": HEIGHT_M_PATH,
        "created": created,
        "saved": saved,
        "connections": [c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14, c15],
        "num_expressions": int(MATERIAL_LIB.get_num_material_expressions(mat)),
    }


def build_height_instance() -> dict:
    inst, created = _ensure_material_instance(HEIGHT_MI_PATH)
    mat = _load_asset(HEIGHT_M_PATH)
    rvt = _load_asset(RVT_PATH)
    _safe_set(inst, "parent", mat)

    set_rvt = False
    try:
        set_rvt = bool(MATERIAL_LIB.set_material_instance_runtime_virtual_texture_parameter_value(inst, "SnowRVT", rvt))
    except Exception:
        set_rvt = False

    scalars = {
        "SnowRoughness": 0.9,
        "PressedRoughness": 0.45,
        "HeightAmplitude": -25.0,
        "HeightContrast": 2.0,
        "HeightBias": 0.0,
    }
    vectors = {
        "SnowColor": unreal.LinearColor(1.0, 1.0, 1.0, 1.0),
        "PressedSnowColor": unreal.LinearColor(0.22, 0.22, 0.22, 1.0),
    }

    scalar_set = {}
    for k, v in scalars.items():
        try:
            scalar_set[k] = bool(MATERIAL_LIB.set_material_instance_scalar_parameter_value(inst, k, float(v)))
        except Exception:
            scalar_set[k] = False

    vector_set = {}
    for k, v in vectors.items():
        try:
            vector_set[k] = bool(MATERIAL_LIB.set_material_instance_vector_parameter_value(inst, k, v))
        except Exception:
            vector_set[k] = False

    saved = bool(ASSET_LIB.save_loaded_asset(inst, False))
    return {
        "instance_path": HEIGHT_MI_PATH,
        "created": created,
        "saved": saved,
        "rvt_set_call_result": set_rvt,
        "scalar_set": scalar_set,
        "vector_set": vector_set,
    }


def _find_rvt_volume_for_asset(rvt_asset):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    best = None
    for actor in actor_subsystem.get_all_level_actors():
        cls_name = actor.get_class().get_name()
        if cls_name != "RuntimeVirtualTextureVolume":
            continue
        vt_comp = actor.get_component_by_class(unreal.RuntimeVirtualTextureComponent)
        if vt_comp is None:
            continue
        vol_rvt = vt_comp.get_editor_property("virtual_texture")
        if _object_path(vol_rvt) == _object_path(rvt_asset):
            best = actor
            break
    return best


def _spawn_or_get_height_actor(base_actor, writer_actor, rvt_asset) -> dict:
    actor = _find_actor_by_label(HEIGHT_ACTOR_LABEL)
    created = False
    if actor is None:
        loc = unreal.Vector(0.0, 0.0, 0.0)
        if writer_actor is not None:
            loc = writer_actor.get_actor_location()
        elif base_actor is not None:
            loc = base_actor.get_actor_location()
        loc = unreal.Vector(float(loc.x), float(loc.y), float(loc.z) + 10.0)
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, loc, unreal.Rotator(0.0, 0.0, 0.0))
        created = True
    actor.set_actor_label(HEIGHT_ACTOR_LABEL)

    comp = _first_static_mesh_component(actor)
    if comp is None:
        raise RuntimeError("Could not get StaticMeshComponent for height actor")

    mesh = _load_asset(HEIGHT_MESH_PATH)
    if mesh is None:
        raise RuntimeError(f"Missing dense mesh: {HEIGHT_MESH_PATH}")
    _safe_set(comp, "static_mesh", mesh)
    actor.set_actor_scale3d(unreal.Vector(10.0, 10.0, 0.03))
    actor.set_actor_rotation(unreal.Rotator(0.0, 0.0, 0.0), False)

    # Keep XY alignment with writer to maximize overlap with the debug stamp.
    if writer_actor is not None:
        writer_loc = writer_actor.get_actor_location()
        cur_loc = actor.get_actor_location()
        actor.set_actor_location(unreal.Vector(float(writer_loc.x), float(writer_loc.y), float(cur_loc.z)), False, False)

    # Keep inside RVT volume and near writer XY to guarantee local stamp overlap.
    vol = _find_rvt_volume_for_asset(rvt_asset)
    vol_path = _object_path(vol)
    inside_vol = False
    if vol is not None:
        vol_loc = vol.get_actor_location()
        _, vol_ext = vol.get_actor_bounds(False)
        cur = actor.get_actor_location()
        clamped = unreal.Vector(
            max(vol_loc.x - vol_ext.x * 0.8, min(vol_loc.x + vol_ext.x * 0.8, cur.x)),
            max(vol_loc.y - vol_ext.y * 0.8, min(vol_loc.y + vol_ext.y * 0.8, cur.y)),
            max(vol_loc.z - max(10.0, vol_ext.z * 0.8), min(vol_loc.z + max(10.0, vol_ext.z * 0.8), cur.z)),
        )
        actor.set_actor_location(clamped, False, False)
        a_loc = actor.get_actor_location()
        inside_vol = (
            abs(a_loc.x - vol_loc.x) <= max(1.0, vol_ext.x)
            and abs(a_loc.y - vol_loc.y) <= max(1.0, vol_ext.y)
            and abs(a_loc.z - vol_loc.z) <= max(1.0, vol_ext.z if vol_ext.z > 0 else 5000.0)
        )

    return {
        "actor_path": _object_path(actor),
        "component_path": _object_path(comp),
        "created": created,
        "mesh_path": _object_path(mesh),
        "actor_label": actor.get_actor_label(),
        "location": str(actor.get_actor_location()),
        "scale": str(actor.get_actor_scale3d()),
        "rvt_volume_path": vol_path,
        "inside_rvt_volume": inside_vol,
    }


def assign_instance_to_actor(actor, mi_asset) -> dict:
    comp = _first_static_mesh_component(actor)
    if comp is None:
        raise RuntimeError("Target actor has no StaticMeshComponent")
    num = int(comp.get_num_materials())
    if num <= TARGET_SLOT:
        raise RuntimeError(f"Target actor has {num} material slots; required slot {TARGET_SLOT}")
    comp.set_material(TARGET_SLOT, mi_asset)
    comp.modify()
    return {
        "actor_path": _object_path(actor),
        "component_path": _object_path(comp),
        "slot": TARGET_SLOT,
        "material_after": _object_path(comp.get_material(TARGET_SLOT)),
        "num_slots": num,
    }


def main():
    payload = {
        "map_path": MAP_PATH,
        "base_receiver_material_path": BASE_RECEIVER_M_PATH,
        "base_receiver_instance_path": BASE_RECEIVER_MI_PATH,
        "snowtestground_viability": {},
        "snowtestground_wpo_viable": False,
        "final_height_target_actor_path": "",
        "final_height_target_actor_label": "",
        "created_assets": {},
        "material_build": {},
        "instance_build": {},
        "height_actor": {},
        "assignment": {},
        "real_height_visible": False,
        "exact_blocker": "",
    }

    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    rvt_asset = _load_asset(RVT_PATH)
    if rvt_asset is None:
        raise RuntimeError(f"RVT asset missing: {RVT_PATH}")

    base_actor = _find_actor_by_label(TARGET_LABEL)
    if base_actor is None:
        raise RuntimeError(f"Could not find target actor: {TARGET_LABEL}")

    payload["snowtestground_viability"] = _surface_viability(base_actor)
    payload["snowtestground_wpo_viable"] = bool(payload["snowtestground_viability"]["viable"])

    payload["material_build"] = build_height_material()
    payload["instance_build"] = build_height_instance()

    if payload["snowtestground_wpo_viable"]:
        final_actor = base_actor
        payload["height_actor"] = {
            "actor_path": _object_path(final_actor),
            "actor_label": final_actor.get_actor_label(),
            "created": False,
            "mesh_path": payload["snowtestground_viability"]["mesh_path"],
            "inside_rvt_volume": True,
        }
    else:
        writer_actor = _find_actor_by_label(WRITER_LABEL)
        payload["height_actor"] = _spawn_or_get_height_actor(base_actor, writer_actor, rvt_asset)
        final_actor = _find_actor_by_label(HEIGHT_ACTOR_LABEL)
        if final_actor is None:
            raise RuntimeError("Failed to create/find height actor")

    mi_asset = _load_asset(HEIGHT_MI_PATH)
    payload["assignment"] = assign_instance_to_actor(final_actor, mi_asset)

    payload["final_height_target_actor_path"] = _object_path(final_actor)
    payload["final_height_target_actor_label"] = final_actor.get_actor_label()

    # Binary visibility confidence gate.
    target_viability = _surface_viability(final_actor)
    has_wpo_expr = payload["material_build"].get("num_expressions", 0) > 0
    assigned_ok = payload["assignment"].get("material_after", "") == _object_path(mi_asset)
    in_volume = bool(payload["height_actor"].get("inside_rvt_volume", False))
    payload["real_height_visible"] = bool(target_viability["viable"] and has_wpo_expr and assigned_ok and in_volume)
    if not payload["real_height_visible"]:
        payload["exact_blocker"] = (
            "Height target failed visibility gate (viability/assignment/volume overlap check)."
        )

    # Save assets + level.
    ASSET_LIB.save_loaded_asset(_load_asset(HEIGHT_M_PATH), False)
    ASSET_LIB.save_loaded_asset(_load_asset(HEIGHT_MI_PATH), False)
    unreal.EditorLoadingAndSavingUtils.save_current_level()

    payload["created_assets"] = {
        "height_material": HEIGHT_M_PATH,
        "height_instance": HEIGHT_MI_PATH,
        "height_surface_actor_label": payload["final_height_target_actor_label"],
    }

    output_path = _write_output(payload)
    payload["output_path"] = output_path
    print(payload)


if __name__ == "__main__":
    main()
