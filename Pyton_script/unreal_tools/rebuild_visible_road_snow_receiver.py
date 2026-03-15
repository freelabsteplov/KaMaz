import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import prepare_road_snow_receiver_assets as prsra


OUTPUT_BASENAME = "rebuild_visible_road_snow_receiver"
SOURCE_INSTANCE_PATH = "/Game/SnappyRoads/Materials/Old/M_SR_RoadSection001_Inst"
RECEIVER_PARENT_PATH = "/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_SnowReceiver"
RECEIVER_INSTANCE_PATH = "/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_Inst_SnowReceiver_Test"
TEST_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
SNOW_RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
MPC_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"
SNOW_DIFFUSE_PATH = "/Game/CAA_SnowV2/SnowV2P3/TexturesP3/T_SnowV2P3_2K_Diffuse"
SNOW_NORMAL_PATH = "/Game/CAA_SnowV2/SnowV2P3/TexturesP3/T_SnowV2P3_2K_Normal"
SNOW_ROUGHNESS_PATH = "/Game/CAA_SnowV2/SnowV2P3/TexturesP3/T_SnowV2P3_2K_Roughness"

BASE_SNOW_AMOUNT = 0.72
SNOW_TINT_STRENGTH = 1.0
SNOW_COLOR_TINT = (1.28, 1.28, 1.34)
CLEAR_MASK_AMPLIFY = 1024.0
ROAD_UV_SCALE = 1.0
SNOW_UV_SCALE = 4.0
BASE_ROAD_ROUGHNESS = 0.38
TRACE_DEBUG_EMISSIVE_MULTIPLIER = 12.0
DEBUG_DIRECT_RT_VIS = False
DEBUG_RT_TINT = (0.0, 1.0, 0.0)
DEBUG_EMISSIVE_MULTIPLIER = 25.0
DEBUG_FORCE_SOLID_COLOR = False
DEBUG_SOLID_COLOR = (1.0, 0.0, 1.0)
DEBUG_DIRECT_TEXCOORD_RT_VIS = False
DEBUG_PURE_TEXCOORD_RT_VIS = False
DEBUG_USE_TEXCOORD_CLEAR_MASK = False
DEBUG_WORLD_UV_FLIP_Y = False
UP_FACING_NORMAL_THRESHOLD = 0.55
UP_FACING_MASK_SHARPNESS = 8.0
ROAD_DARK_MASK_THRESHOLD = 0.45
ROAD_DARK_MASK_SHARPNESS = 4.0

ASSET_LIB = unreal.EditorAssetLibrary
MATERIAL_LIB = unreal.MaterialEditingLibrary
ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def _log(message: str) -> None:
    unreal.log(f"[rebuild_visible_road_snow_receiver] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[rebuild_visible_road_snow_receiver] {message}")


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


def _object_name(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_name()
    except Exception:
        return str(value)


def _object_class_name(value) -> str:
    if value is None:
        return ""
    try:
        return _object_name(value.get_class())
    except Exception:
        return ""


def _load_asset(asset_path: str):
    asset = ASSET_LIB.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Could not load asset: {asset_path}")
    return asset


def _ensure_directory(path: str) -> None:
    if not ASSET_LIB.does_directory_exist(path):
        ASSET_LIB.make_directory(path)


def _delete_asset_if_exists(asset_path: str) -> bool:
    if not ASSET_LIB.does_asset_exist(asset_path):
        return False
    if not ASSET_LIB.delete_asset(asset_path):
        raise RuntimeError(f"Could not delete existing asset: {asset_path}")
    return True


def _recreate_material_asset(asset_path: str):
    existing = ASSET_LIB.load_asset(asset_path)
    if existing is not None and type(existing).__name__ == "Material":
        return existing

    package_path, asset_name = asset_path.rsplit("/", 1)
    _ensure_directory(package_path)
    _delete_asset_if_exists(asset_path)
    material = ASSET_TOOLS.create_asset(
        asset_name,
        package_path,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if material is None:
        raise RuntimeError(f"Failed to create material: {asset_path}")
    return material


def _load_or_create_material_instance_asset(asset_path: str):
    existing = ASSET_LIB.load_asset(asset_path)
    if existing is not None:
        return existing

    package_path, asset_name = asset_path.rsplit("/", 1)
    _ensure_directory(package_path)
    instance = ASSET_TOOLS.create_asset(
        asset_name,
        package_path,
        unreal.MaterialInstanceConstant,
        unreal.MaterialInstanceConstantFactoryNew(),
    )
    if instance is None:
        raise RuntimeError(f"Failed to create material instance: {asset_path}")
    return instance


def _resolve_expr_class(class_name: str):
    expr_class = getattr(unreal, class_name, None)
    if expr_class is None:
        raise RuntimeError(f"Required Unreal Python class is missing: {class_name}")
    return expr_class


def _set_if_present(obj, property_name: str, value) -> bool:
    try:
        obj.set_editor_property(property_name, value)
        return True
    except Exception:
        return False


def _connect(source_expr, target_expr, input_name: str, source_output_name: str = "") -> None:
    resolved_input_name = input_name
    class_name = _object_class_name(target_expr)
    if class_name in ("MaterialExpressionComponentMask", "MaterialExpressionAbs") and input_name == "Input":
        resolved_input_name = ""
    MATERIAL_LIB.connect_material_expressions(source_expr, source_output_name, target_expr, resolved_input_name)


def _new_expr(material, class_name: str, x: int, y: int):
    expr_class = _resolve_expr_class(class_name)
    expr = MATERIAL_LIB.create_material_expression(material, expr_class, x, y)
    if expr is None:
        raise RuntimeError(f"Could not create material expression: {class_name}")
    return expr


def _new_scalar_param(material, x: int, y: int, name: str, value: float, desc: str = ""):
    expr = _new_expr(material, "MaterialExpressionScalarParameter", x, y)
    expr.set_editor_property("parameter_name", name)
    expr.set_editor_property("default_value", float(value))
    if desc:
        _set_if_present(expr, "desc", desc)
    return expr


def _new_collection_param(material, x: int, y: int, collection, parameter_name: str):
    expr = _new_expr(material, "MaterialExpressionCollectionParameter", x, y)
    expr.set_editor_property("collection", collection)
    expr.set_editor_property("parameter_name", parameter_name)
    return expr


def _new_component_mask(material, x: int, y: int, r: bool, g: bool, b: bool, a: bool):
    expr = _new_expr(material, "MaterialExpressionComponentMask", x, y)
    expr.set_editor_property("r", bool(r))
    expr.set_editor_property("g", bool(g))
    expr.set_editor_property("b", bool(b))
    expr.set_editor_property("a", bool(a))
    return expr


def _new_constant(material, x: int, y: int, value: float):
    expr = _new_expr(material, "MaterialExpressionConstant", x, y)
    expr.set_editor_property("r", float(value))
    return expr


def _new_color(material, x: int, y: int, rgb: tuple[float, float, float]):
    expr = _new_expr(material, "MaterialExpressionConstant3Vector", x, y)
    expr.set_editor_property("constant", unreal.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))
    return expr


def _new_color4(material, x: int, y: int, rgba: tuple[float, float, float, float]):
    expr = _new_expr(material, "MaterialExpressionConstant4Vector", x, y)
    expr.set_editor_property(
        "constant",
        unreal.LinearColor(float(rgba[0]), float(rgba[1]), float(rgba[2]), float(rgba[3])),
    )
    return expr


def _new_texture_param(material, x: int, y: int, name: str, texture_asset):
    expr = _new_expr(material, "MaterialExpressionTextureSampleParameter2D", x, y)
    expr.set_editor_property("parameter_name", name)
    expr.set_editor_property("texture", texture_asset)
    return expr


def _set_sampler_type(expr, enum_name: str) -> None:
    sampler_type = getattr(unreal.MaterialSamplerType, enum_name, None)
    if sampler_type is not None:
        _set_if_present(expr, "sampler_type", sampler_type)


def _resolve_nanite_usage_enum():
    enum_type = getattr(unreal, "MaterialUsage", None)
    if not enum_type:
        return None
    for name in dir(enum_type):
        if name.lower() == "matusage_nanite":
            return getattr(enum_type, name)
    for name in dir(enum_type):
        if "nanite" in name.lower():
            return getattr(enum_type, name)
    return None


def _enable_nanite_usage(material) -> dict:
    result = {
        "usage_set_result": None,
        "needs_recompile": None,
        "property_set": False,
        "errors": [],
    }

    try:
        material.modify()
    except Exception as exc:
        result["errors"].append(f"modify_failed:{exc}")

    nanite_usage = _resolve_nanite_usage_enum()
    if nanite_usage is not None:
        try:
            usage_response = MATERIAL_LIB.set_material_usage(material, nanite_usage)
            if isinstance(usage_response, tuple):
                result["usage_set_result"] = bool(usage_response[0])
                result["needs_recompile"] = bool(usage_response[1])
            else:
                result["usage_set_result"] = bool(usage_response)
        except Exception as exc:
            result["errors"].append(f"set_material_usage_failed:{exc}")
    else:
        result["errors"].append("nanite_usage_enum_not_found")

    for prop_name in ("used_with_nanite", "b_used_with_nanite", "bUsedWithNanite"):
        if _set_if_present(material, prop_name, True):
            result["property_set"] = True
            break

    return result


def _save_current_level() -> dict:
    result = {"saved_current_level": False, "error": ""}
    try:
        result["saved_current_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _get_instance_texture(instance, parameter_name: str):
    getter = getattr(MATERIAL_LIB, "get_material_instance_texture_parameter_value", None)
    if getter is None:
        return None
    try:
        return getter(instance, parameter_name)
    except Exception:
        return None


def _prepare_receiver_assets() -> dict:
    global prsra
    prsra = importlib.reload(prsra)
    return prsra.prepare_road_snow_receiver_assets(
        source_instance_path=SOURCE_INSTANCE_PATH,
        target_package="/Game/CityPark/SnowSystem/Receivers",
    )


def _rebuild_parent_material(parent_material, road_texture, road_normal_texture, snow_rt, mpc, snow_diffuse, snow_normal, snow_roughness) -> dict:
    MATERIAL_LIB.delete_all_material_expressions(parent_material)

    parent_material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    parent_material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    parent_material.set_editor_property("material_domain", unreal.MaterialDomain.MD_SURFACE)

    road_tex = _new_texture_param(parent_material, -3000, -900, "Road", road_texture)
    texcoord = _new_expr(parent_material, "MaterialExpressionTextureCoordinate", -3300, -1000)
    road_uv_scale = _new_scalar_param(parent_material, -3300, -820, "RoadUVScale", ROAD_UV_SCALE)
    road_scaled_uv = _new_expr(parent_material, "MaterialExpressionMultiply", -2700, -900)
    _connect(texcoord, road_scaled_uv, "A")
    _connect(road_uv_scale, road_scaled_uv, "B")
    _connect(road_scaled_uv, road_tex, "Coordinates")

    luminance_weights = _new_color(parent_material, -2400, -1120, (0.2126, 0.7152, 0.0722))
    road_luminance = _new_expr(parent_material, "MaterialExpressionDotProduct", -2100, -1020)
    _connect(road_tex, road_luminance, "A")
    _connect(luminance_weights, road_luminance, "B")

    one_for_darkness = _new_constant(parent_material, -2100, -840, 1.0)
    road_darkness = _new_expr(parent_material, "MaterialExpressionSubtract", -1800, -960)
    _connect(one_for_darkness, road_darkness, "A")
    _connect(road_luminance, road_darkness, "B")

    road_dark_mask_threshold = _new_scalar_param(
        parent_material,
        -2400,
        -760,
        "RoadDarkMaskThreshold",
        ROAD_DARK_MASK_THRESHOLD,
        "Heuristic road-only mask: keeps snow off bright curb/checker regions baked into the shared road texture.",
    )
    road_dark_mask_sub = _new_expr(parent_material, "MaterialExpressionSubtract", -1500, -960)
    _connect(road_darkness, road_dark_mask_sub, "A")
    _connect(road_dark_mask_threshold, road_dark_mask_sub, "B")

    road_dark_mask_sharpness = _new_scalar_param(
        parent_material,
        -2400,
        -580,
        "RoadDarkMaskSharpness",
        ROAD_DARK_MASK_SHARPNESS,
        "Sharpens the road-only mask from the shared road texture.",
    )
    road_dark_mask_scaled = _new_expr(parent_material, "MaterialExpressionMultiply", -1200, -960)
    _connect(road_dark_mask_sub, road_dark_mask_scaled, "A")
    _connect(road_dark_mask_sharpness, road_dark_mask_scaled, "B")

    road_dark_mask_non_negative = _new_expr(parent_material, "MaterialExpressionMax", -900, -960)
    _connect(road_dark_mask_scaled, road_dark_mask_non_negative, "A")
    _connect(_new_constant(parent_material, -1200, -1160, 0.0), road_dark_mask_non_negative, "B")

    road_surface_mask = _new_expr(parent_material, "MaterialExpressionMin", -600, -960)
    _connect(road_dark_mask_non_negative, road_surface_mask, "A")
    _connect(_new_constant(parent_material, -900, -1160, 1.0), road_surface_mask, "B")

    using_flat_road_normal = road_normal_texture is None
    if using_flat_road_normal:
        road_normal_source = _new_color(parent_material, -3000, -620, (0.5, 0.5, 1.0))
    else:
        road_normal_source = _new_texture_param(parent_material, -3000, -620, "Road_N", road_normal_texture)
        _set_sampler_type(road_normal_source, "SAMPLERTYPE_NORMAL")
        _connect(road_scaled_uv, road_normal_source, "Coordinates")

    axis3_x = _new_color(parent_material, -3300, -320, (1.0, 0.0, 0.0))
    axis3_y = _new_color(parent_material, -3300, -180, (0.0, 1.0, 0.0))
    axis3_z = _new_color(parent_material, -3300, -40, (0.0, 0.0, 1.0))
    axis2_x = _new_expr(parent_material, "MaterialExpressionConstant2Vector", -3300, -480)
    axis2_x.set_editor_property("r", 1.0)
    axis2_x.set_editor_property("g", 0.0)
    axis2_y = _new_expr(parent_material, "MaterialExpressionConstant2Vector", -3300, -620)
    axis2_y.set_editor_property("r", 0.0)
    axis2_y.set_editor_property("g", 1.0)
    axis4_x = _new_color4(parent_material, -3300, 120, (1.0, 0.0, 0.0, 0.0))
    axis4_y = _new_color4(parent_material, -3300, 280, (0.0, 1.0, 0.0, 0.0))

    world_pos = _new_expr(parent_material, "MaterialExpressionWorldPosition", -3300, -60)
    world_pos_x = _new_expr(parent_material, "MaterialExpressionDotProduct", -3000, -120)
    world_pos_y = _new_expr(parent_material, "MaterialExpressionDotProduct", -3000, 80)
    _connect(world_pos, world_pos_x, "A")
    _connect(axis3_x, world_pos_x, "B")
    _connect(world_pos, world_pos_y, "A")
    _connect(axis3_y, world_pos_y, "B")
    world_pos_rg = _new_expr(parent_material, "MaterialExpressionAppendVector", -2700, -20)
    _connect(world_pos_x, world_pos_rg, "A")
    _connect(world_pos_y, world_pos_rg, "B")

    bounds_min = _new_collection_param(parent_material, -3300, 240, mpc, "WorldBoundsMin")
    bounds_max = _new_collection_param(parent_material, -3300, 520, mpc, "WorldBoundsMax")
    bounds_min_x = _new_expr(parent_material, "MaterialExpressionDotProduct", -3000, 220)
    bounds_min_y = _new_expr(parent_material, "MaterialExpressionDotProduct", -3000, 420)
    bounds_max_x = _new_expr(parent_material, "MaterialExpressionDotProduct", -3000, 560)
    bounds_max_y = _new_expr(parent_material, "MaterialExpressionDotProduct", -3000, 760)
    _connect(bounds_min, bounds_min_x, "A")
    _connect(axis4_x, bounds_min_x, "B")
    _connect(bounds_min, bounds_min_y, "A")
    _connect(axis4_y, bounds_min_y, "B")
    _connect(bounds_max, bounds_max_x, "A")
    _connect(axis4_x, bounds_max_x, "B")
    _connect(bounds_max, bounds_max_y, "A")
    _connect(axis4_y, bounds_max_y, "B")
    bounds_min_rg = _new_expr(parent_material, "MaterialExpressionAppendVector", -2700, 320)
    bounds_max_rg = _new_expr(parent_material, "MaterialExpressionAppendVector", -2700, 660)
    _connect(bounds_min_x, bounds_min_rg, "A")
    _connect(bounds_min_y, bounds_min_rg, "B")
    _connect(bounds_max_x, bounds_max_rg, "A")
    _connect(bounds_max_y, bounds_max_rg, "B")

    bounds_span = _new_expr(parent_material, "MaterialExpressionSubtract", -2400, 500)
    _connect(bounds_max_rg, bounds_span, "A")
    _connect(bounds_min_rg, bounds_span, "B")

    world_delta = _new_expr(parent_material, "MaterialExpressionSubtract", -2100, 120)
    _connect(world_pos_rg, world_delta, "A")
    _connect(bounds_min_rg, world_delta, "B")

    snow_uv = _new_expr(parent_material, "MaterialExpressionDivide", -1800, 120)
    _connect(world_delta, snow_uv, "A")
    _connect(bounds_span, snow_uv, "B")

    snow_uv_sample = snow_uv
    if DEBUG_WORLD_UV_FLIP_Y:
        one_uv = _new_constant(parent_material, -1800, -260, 1.0)
        snow_uv_x = _new_expr(parent_material, "MaterialExpressionDotProduct", -1560, -120)
        _connect(snow_uv, snow_uv_x, "A")
        _connect(axis2_x, snow_uv_x, "B")

        snow_uv_y = _new_expr(parent_material, "MaterialExpressionDotProduct", -1560, 20)
        _connect(snow_uv, snow_uv_y, "A")
        _connect(axis2_y, snow_uv_y, "B")

        snow_uv_y_flipped = _new_expr(parent_material, "MaterialExpressionSubtract", -1320, 20)
        _connect(one_uv, snow_uv_y_flipped, "A")
        _connect(snow_uv_y, snow_uv_y_flipped, "B")

        snow_uv_sample = _new_expr(parent_material, "MaterialExpressionAppendVector", -1080, -40)
        _connect(snow_uv_x, snow_uv_sample, "A")
        _connect(snow_uv_y_flipped, snow_uv_sample, "B")

    snow_rt_sample = _new_texture_param(parent_material, -1500, 120, "SnowRT", snow_rt)
    _connect(snow_uv_sample, snow_rt_sample, "Coordinates")

    rt_r = _new_expr(parent_material, "MaterialExpressionDotProduct", -1200, 0)
    rt_g = _new_expr(parent_material, "MaterialExpressionDotProduct", -1200, 220)
    _connect(snow_rt_sample, rt_r, "A")
    _connect(axis4_x, rt_r, "B")
    _connect(snow_rt_sample, rt_g, "A")
    _connect(axis4_y, rt_g, "B")

    clear_mask = _new_expr(parent_material, "MaterialExpressionMax", -900, 100)
    _connect(rt_r, clear_mask, "A")
    _connect(rt_g, clear_mask, "B")

    clear_mask_amplify = _new_scalar_param(
        parent_material,
        -1200,
        760,
        "ClearMaskAmplify",
        CLEAR_MASK_AMPLIFY,
        "Debug receiver: amplifies weak RT writes so road reveal becomes obvious during validation.",
    )
    clear_mask_scaled = _new_expr(parent_material, "MaterialExpressionMultiply", -900, 760)
    _connect(clear_mask, clear_mask_scaled, "A")
    _connect(clear_mask_amplify, clear_mask_scaled, "B")

    zero = _new_constant(parent_material, -600, 700, 0.0)
    one = _new_constant(parent_material, -600, 880, 1.0)

    clear_mask_non_negative = _new_expr(parent_material, "MaterialExpressionMax", -600, 760)
    _connect(clear_mask_scaled, clear_mask_non_negative, "A")
    _connect(zero, clear_mask_non_negative, "B")

    clear_mask_clamped = _new_expr(parent_material, "MaterialExpressionMin", -300, 760)
    _connect(clear_mask_non_negative, clear_mask_clamped, "A")
    _connect(one, clear_mask_clamped, "B")

    effective_clear_mask_clamped = clear_mask_clamped
    if DEBUG_USE_TEXCOORD_CLEAR_MASK:
        texcoord_clear_rt = _new_texture_param(parent_material, -120, 1320, "SnowRT_TexcoordClear", snow_rt)
        _connect(texcoord, texcoord_clear_rt, "Coordinates")

        texcoord_clear_r = _new_expr(parent_material, "MaterialExpressionDotProduct", 180, 1280)
        texcoord_clear_g = _new_expr(parent_material, "MaterialExpressionDotProduct", 180, 1440)
        _connect(texcoord_clear_rt, texcoord_clear_r, "A")
        _connect(axis4_x, texcoord_clear_r, "B")
        _connect(texcoord_clear_rt, texcoord_clear_g, "A")
        _connect(axis4_y, texcoord_clear_g, "B")

        texcoord_clear_mask = _new_expr(parent_material, "MaterialExpressionMax", 420, 1360)
        _connect(texcoord_clear_r, texcoord_clear_mask, "A")
        _connect(texcoord_clear_g, texcoord_clear_mask, "B")

        texcoord_clear_scaled = _new_expr(parent_material, "MaterialExpressionMultiply", 660, 1360)
        _connect(texcoord_clear_mask, texcoord_clear_scaled, "A")
        _connect(clear_mask_amplify, texcoord_clear_scaled, "B")

        texcoord_clear_non_negative = _new_expr(parent_material, "MaterialExpressionMax", 900, 1360)
        _connect(texcoord_clear_scaled, texcoord_clear_non_negative, "A")
        _connect(zero, texcoord_clear_non_negative, "B")

        texcoord_clear_clamped = _new_expr(parent_material, "MaterialExpressionMin", 1140, 1360)
        _connect(texcoord_clear_non_negative, texcoord_clear_clamped, "A")
        _connect(one, texcoord_clear_clamped, "B")

        effective_clear_mask_clamped = texcoord_clear_clamped

    vertex_normal_ws = _new_expr(parent_material, "MaterialExpressionVertexNormalWS", -1200, 1100)
    up_facing_dot = _new_expr(parent_material, "MaterialExpressionDotProduct", -900, 1100)
    _connect(vertex_normal_ws, up_facing_dot, "A")
    _connect(axis3_z, up_facing_dot, "B")

    up_facing_threshold = _new_scalar_param(
        parent_material,
        -1200,
        1260,
        "UpFacingNormalThreshold",
        UP_FACING_NORMAL_THRESHOLD,
        "Restricts snow/debug visualization to upward-facing road polygons.",
    )
    up_facing_sub = _new_expr(parent_material, "MaterialExpressionSubtract", -600, 1100)
    _connect(up_facing_dot, up_facing_sub, "A")
    _connect(up_facing_threshold, up_facing_sub, "B")

    up_facing_sharpness = _new_scalar_param(
        parent_material,
        -1200,
        1420,
        "UpFacingMaskSharpness",
        UP_FACING_MASK_SHARPNESS,
        "Sharpens the top-surface-only mask for road snow visualization.",
    )
    up_facing_scaled = _new_expr(parent_material, "MaterialExpressionMultiply", -300, 1100)
    _connect(up_facing_sub, up_facing_scaled, "A")
    _connect(up_facing_sharpness, up_facing_scaled, "B")

    up_facing_non_negative = _new_expr(parent_material, "MaterialExpressionMax", 0, 1100)
    _connect(up_facing_scaled, up_facing_non_negative, "A")
    _connect(zero, up_facing_non_negative, "B")

    up_facing_mask = _new_expr(parent_material, "MaterialExpressionMin", 300, 1100)
    _connect(up_facing_non_negative, up_facing_mask, "A")
    _connect(one, up_facing_mask, "B")

    if DEBUG_DIRECT_RT_VIS:
        if DEBUG_FORCE_SOLID_COLOR:
            solid_color = _new_color(parent_material, 40, 180, DEBUG_SOLID_COLOR)
            solid_emissive_multiplier = _new_scalar_param(
                parent_material,
                40,
                460,
                "DebugEmissiveMultiplier",
                DEBUG_EMISSIVE_MULTIPLIER,
                "Temporary isolated road receiver debug: force a solid emissive color on the road actor.",
            )
            solid_emissive = _new_expr(parent_material, "MaterialExpressionMultiply", 360, 420)
            _connect(solid_color, solid_emissive, "A")
            _connect(solid_emissive_multiplier, solid_emissive, "B")

            nanite_usage_result = _enable_nanite_usage(parent_material)
            MATERIAL_LIB.connect_material_property(solid_color, "", unreal.MaterialProperty.MP_BASE_COLOR)
            MATERIAL_LIB.connect_material_property(solid_emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

            MATERIAL_LIB.recompile_material(parent_material)
            MATERIAL_LIB.layout_material_expressions(parent_material)

            saved = bool(ASSET_LIB.save_loaded_asset(parent_material, False))
            return {
                "parent_material_path": _object_path(parent_material),
                "road_texture_path": _object_path(road_texture),
                "road_normal_texture_path": _object_path(road_normal_texture),
                "using_flat_road_normal": using_flat_road_normal,
                "snow_rt_path": _object_path(snow_rt),
                "mpc_path": _object_path(mpc),
                "snow_diffuse_path": _object_path(snow_diffuse),
                "snow_normal_path": _object_path(snow_normal),
                "snow_roughness_path": _object_path(snow_roughness),
                "saved": saved,
                "nanite_usage_result": nanite_usage_result,
                "debug_direct_rt_vis": True,
                "debug_force_solid_color": True,
                "parameters": {
                    "DebugEmissiveMultiplier": DEBUG_EMISSIVE_MULTIPLIER,
                    "DebugSolidColor": list(DEBUG_SOLID_COLOR),
                },
            }

        if DEBUG_PURE_TEXCOORD_RT_VIS:
            debug_rt_sample = _new_texture_param(parent_material, -120, 980, "SnowRT_PureDebugUV", snow_rt)
            _connect(texcoord, debug_rt_sample, "Coordinates")

            debug_rt_g = _new_expr(parent_material, "MaterialExpressionDotProduct", 180, 980)
            _connect(debug_rt_sample, debug_rt_g, "A")
            _connect(axis4_y, debug_rt_g, "B")

            debug_rt_scaled = _new_expr(parent_material, "MaterialExpressionMultiply", 420, 980)
            _connect(debug_rt_g, debug_rt_scaled, "A")
            _connect(clear_mask_amplify, debug_rt_scaled, "B")

            debug_rt_non_negative = _new_expr(parent_material, "MaterialExpressionMax", 660, 980)
            _connect(debug_rt_scaled, debug_rt_non_negative, "A")
            _connect(zero, debug_rt_non_negative, "B")

            debug_rt_clamped = _new_expr(parent_material, "MaterialExpressionMin", 900, 980)
            _connect(debug_rt_non_negative, debug_rt_clamped, "A")
            _connect(one, debug_rt_clamped, "B")

            debug_tint = _new_color(parent_material, 40, 180, DEBUG_RT_TINT)
            debug_base_color = _new_expr(parent_material, "MaterialExpressionMultiply", 360, 180)
            _connect(debug_rt_clamped, debug_base_color, "A")
            _connect(debug_tint, debug_base_color, "B")

            debug_emissive_multiplier = _new_scalar_param(
                parent_material,
                40,
                460,
                "DebugEmissiveMultiplier",
                DEBUG_EMISSIVE_MULTIPLIER,
                "Temporary isolated road receiver debug: visualize SnowRT directly through pure TexCoord sampling without road masks.",
            )
            debug_emissive = _new_expr(parent_material, "MaterialExpressionMultiply", 360, 420)
            _connect(debug_base_color, debug_emissive, "A")
            _connect(debug_emissive_multiplier, debug_emissive, "B")

            nanite_usage_result = _enable_nanite_usage(parent_material)
            MATERIAL_LIB.connect_material_property(debug_base_color, "", unreal.MaterialProperty.MP_BASE_COLOR)
            MATERIAL_LIB.connect_material_property(debug_emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

            MATERIAL_LIB.recompile_material(parent_material)
            MATERIAL_LIB.layout_material_expressions(parent_material)

            saved = bool(ASSET_LIB.save_loaded_asset(parent_material, False))
            return {
                "parent_material_path": _object_path(parent_material),
                "road_texture_path": _object_path(road_texture),
                "road_normal_texture_path": _object_path(road_normal_texture),
                "using_flat_road_normal": using_flat_road_normal,
                "snow_rt_path": _object_path(snow_rt),
                "mpc_path": _object_path(mpc),
                "snow_diffuse_path": _object_path(snow_diffuse),
                "snow_normal_path": _object_path(snow_normal),
                "snow_roughness_path": _object_path(snow_roughness),
                "saved": saved,
                "nanite_usage_result": nanite_usage_result,
                "debug_direct_rt_vis": True,
                "debug_force_solid_color": False,
                "debug_direct_texcoord_rt_vis": True,
                "debug_pure_texcoord_rt_vis": True,
                "parameters": {
                    "ClearMaskAmplify": CLEAR_MASK_AMPLIFY,
                    "DebugEmissiveMultiplier": DEBUG_EMISSIVE_MULTIPLIER,
                },
            }

        if DEBUG_DIRECT_TEXCOORD_RT_VIS:
            debug_rt_sample = _new_texture_param(parent_material, -120, 980, "SnowRT_DebugUV", snow_rt)
            _connect(texcoord, debug_rt_sample, "Coordinates")

            debug_rt_g = _new_expr(parent_material, "MaterialExpressionDotProduct", 180, 980)
            _connect(debug_rt_sample, debug_rt_g, "A")
            _connect(axis4_y, debug_rt_g, "B")

            debug_rt_scaled = _new_expr(parent_material, "MaterialExpressionMultiply", 420, 980)
            _connect(debug_rt_g, debug_rt_scaled, "A")
            _connect(clear_mask_amplify, debug_rt_scaled, "B")

            debug_rt_non_negative = _new_expr(parent_material, "MaterialExpressionMax", 660, 980)
            _connect(debug_rt_scaled, debug_rt_non_negative, "A")
            _connect(zero, debug_rt_non_negative, "B")

            debug_rt_clamped = _new_expr(parent_material, "MaterialExpressionMin", 900, 980)
            _connect(debug_rt_non_negative, debug_rt_clamped, "A")
            _connect(one, debug_rt_clamped, "B")

            debug_rt_top_only = _new_expr(parent_material, "MaterialExpressionMultiply", 1140, 980)
            _connect(debug_rt_clamped, debug_rt_top_only, "A")
            _connect(up_facing_mask, debug_rt_top_only, "B")

            debug_rt_road_only = _new_expr(parent_material, "MaterialExpressionMultiply", 1380, 980)
            _connect(debug_rt_top_only, debug_rt_road_only, "A")
            _connect(road_surface_mask, debug_rt_road_only, "B")

            debug_tint = _new_color(parent_material, 40, 180, DEBUG_RT_TINT)
            debug_base_color = _new_expr(parent_material, "MaterialExpressionMultiply", 360, 180)
            _connect(debug_rt_road_only, debug_base_color, "A")
            _connect(debug_tint, debug_base_color, "B")

            debug_emissive_multiplier = _new_scalar_param(
                parent_material,
                40,
                460,
                "DebugEmissiveMultiplier",
                DEBUG_EMISSIVE_MULTIPLIER,
                "Temporary isolated road receiver debug: visualize SnowRT directly through mesh TexCoord.",
            )
            debug_emissive = _new_expr(parent_material, "MaterialExpressionMultiply", 360, 420)
            _connect(debug_base_color, debug_emissive, "A")
            _connect(debug_emissive_multiplier, debug_emissive, "B")

            nanite_usage_result = _enable_nanite_usage(parent_material)
            MATERIAL_LIB.connect_material_property(debug_base_color, "", unreal.MaterialProperty.MP_BASE_COLOR)
            MATERIAL_LIB.connect_material_property(debug_emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

            MATERIAL_LIB.recompile_material(parent_material)
            MATERIAL_LIB.layout_material_expressions(parent_material)

            saved = bool(ASSET_LIB.save_loaded_asset(parent_material, False))
            return {
                "parent_material_path": _object_path(parent_material),
                "road_texture_path": _object_path(road_texture),
                "road_normal_texture_path": _object_path(road_normal_texture),
                "using_flat_road_normal": using_flat_road_normal,
                "snow_rt_path": _object_path(snow_rt),
                "mpc_path": _object_path(mpc),
                "snow_diffuse_path": _object_path(snow_diffuse),
                "snow_normal_path": _object_path(snow_normal),
                "snow_roughness_path": _object_path(snow_roughness),
                "saved": saved,
                "nanite_usage_result": nanite_usage_result,
                "debug_direct_rt_vis": True,
                "debug_force_solid_color": False,
                "debug_direct_texcoord_rt_vis": True,
                "parameters": {
                    "ClearMaskAmplify": CLEAR_MASK_AMPLIFY,
                    "RoadUVScale": ROAD_UV_SCALE,
                    "DebugEmissiveMultiplier": DEBUG_EMISSIVE_MULTIPLIER,
                    "UpFacingNormalThreshold": UP_FACING_NORMAL_THRESHOLD,
                    "UpFacingMaskSharpness": UP_FACING_MASK_SHARPNESS,
                    "RoadDarkMaskThreshold": ROAD_DARK_MASK_THRESHOLD,
                    "RoadDarkMaskSharpness": ROAD_DARK_MASK_SHARPNESS,
                },
            }

        snow_uv_x_for_debug = _new_expr(parent_material, "MaterialExpressionDotProduct", -120, 980)
        _connect(snow_uv_sample, snow_uv_x_for_debug, "A")
        _connect(axis2_x, snow_uv_x_for_debug, "B")

        snow_uv_y_for_debug = _new_expr(parent_material, "MaterialExpressionDotProduct", -120, 1140)
        _connect(snow_uv_sample, snow_uv_y_for_debug, "A")
        _connect(axis2_y, snow_uv_y_for_debug, "B")

        snow_uv_x_non_negative = _new_expr(parent_material, "MaterialExpressionMax", 120, 980)
        _connect(snow_uv_x_for_debug, snow_uv_x_non_negative, "A")
        _connect(zero, snow_uv_x_non_negative, "B")
        snow_uv_y_non_negative = _new_expr(parent_material, "MaterialExpressionMax", 120, 1140)
        _connect(snow_uv_y_for_debug, snow_uv_y_non_negative, "A")
        _connect(zero, snow_uv_y_non_negative, "B")

        snow_uv_x_clamped = _new_expr(parent_material, "MaterialExpressionMin", 360, 980)
        _connect(snow_uv_x_non_negative, snow_uv_x_clamped, "A")
        _connect(one, snow_uv_x_clamped, "B")
        snow_uv_y_clamped = _new_expr(parent_material, "MaterialExpressionMin", 360, 1140)
        _connect(snow_uv_y_non_negative, snow_uv_y_clamped, "A")
        _connect(one, snow_uv_y_clamped, "B")

        snow_uv_x_delta = _new_expr(parent_material, "MaterialExpressionSubtract", 600, 980)
        _connect(snow_uv_x_for_debug, snow_uv_x_delta, "A")
        _connect(snow_uv_x_clamped, snow_uv_x_delta, "B")
        snow_uv_y_delta = _new_expr(parent_material, "MaterialExpressionSubtract", 600, 1140)
        _connect(snow_uv_y_for_debug, snow_uv_y_delta, "A")
        _connect(snow_uv_y_clamped, snow_uv_y_delta, "B")

        snow_uv_x_abs = _new_expr(parent_material, "MaterialExpressionAbs", 840, 980)
        _connect(snow_uv_x_delta, snow_uv_x_abs, "Input")
        snow_uv_y_abs = _new_expr(parent_material, "MaterialExpressionAbs", 840, 1140)
        _connect(snow_uv_y_delta, snow_uv_y_abs, "Input")

        out_of_bounds_amplify = _new_constant(parent_material, 840, 1320, 100000.0)
        snow_uv_x_out_scaled = _new_expr(parent_material, "MaterialExpressionMultiply", 1080, 980)
        _connect(snow_uv_x_abs, snow_uv_x_out_scaled, "A")
        _connect(out_of_bounds_amplify, snow_uv_x_out_scaled, "B")
        snow_uv_y_out_scaled = _new_expr(parent_material, "MaterialExpressionMultiply", 1080, 1140)
        _connect(snow_uv_y_abs, snow_uv_y_out_scaled, "A")
        _connect(out_of_bounds_amplify, snow_uv_y_out_scaled, "B")

        snow_uv_x_out = _new_expr(parent_material, "MaterialExpressionMin", 1320, 980)
        _connect(snow_uv_x_out_scaled, snow_uv_x_out, "A")
        _connect(one, snow_uv_x_out, "B")
        snow_uv_y_out = _new_expr(parent_material, "MaterialExpressionMin", 1320, 1140)
        _connect(snow_uv_y_out_scaled, snow_uv_y_out, "A")
        _connect(one, snow_uv_y_out, "B")

        snow_uv_x_in = _new_expr(parent_material, "MaterialExpressionSubtract", 1560, 980)
        _connect(one, snow_uv_x_in, "A")
        _connect(snow_uv_x_out, snow_uv_x_in, "B")
        snow_uv_y_in = _new_expr(parent_material, "MaterialExpressionSubtract", 1560, 1140)
        _connect(one, snow_uv_y_in, "A")
        _connect(snow_uv_y_out, snow_uv_y_in, "B")

        debug_uv_in_bounds = _new_expr(parent_material, "MaterialExpressionMultiply", 1800, 1060)
        _connect(snow_uv_x_in, debug_uv_in_bounds, "A")
        _connect(snow_uv_y_in, debug_uv_in_bounds, "B")

        debug_rt_board_local = _new_expr(parent_material, "MaterialExpressionMultiply", 2040, 980)
        _connect(rt_r, debug_rt_board_local, "A")
        _connect(debug_uv_in_bounds, debug_rt_board_local, "B")

        debug_tint = _new_color(parent_material, 40, 180, DEBUG_RT_TINT)
        debug_base_color = _new_expr(parent_material, "MaterialExpressionMultiply", 2280, 180)
        _connect(debug_rt_board_local, debug_base_color, "A")
        _connect(debug_tint, debug_base_color, "B")

        debug_emissive_multiplier = _new_scalar_param(
            parent_material,
            40,
            460,
            "DebugEmissiveMultiplier",
            DEBUG_EMISSIVE_MULTIPLIER,
            "Temporary isolated road receiver debug: directly visualize RT writes on the road actor.",
        )
        debug_emissive = _new_expr(parent_material, "MaterialExpressionMultiply", 2280, 420)
        _connect(debug_base_color, debug_emissive, "A")
        _connect(debug_emissive_multiplier, debug_emissive, "B")

        nanite_usage_result = _enable_nanite_usage(parent_material)
        MATERIAL_LIB.connect_material_property(debug_base_color, "", unreal.MaterialProperty.MP_BASE_COLOR)
        MATERIAL_LIB.connect_material_property(debug_emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

        MATERIAL_LIB.recompile_material(parent_material)
        MATERIAL_LIB.layout_material_expressions(parent_material)

        saved = bool(ASSET_LIB.save_loaded_asset(parent_material, False))
        return {
            "parent_material_path": _object_path(parent_material),
            "road_texture_path": _object_path(road_texture),
            "road_normal_texture_path": _object_path(road_normal_texture),
            "using_flat_road_normal": using_flat_road_normal,
            "snow_rt_path": _object_path(snow_rt),
            "mpc_path": _object_path(mpc),
            "snow_diffuse_path": _object_path(snow_diffuse),
            "snow_normal_path": _object_path(snow_normal),
            "snow_roughness_path": _object_path(snow_roughness),
            "saved": saved,
            "nanite_usage_result": nanite_usage_result,
            "debug_direct_rt_vis": True,
            "debug_force_solid_color": False,
            "parameters": {
                "DebugChannel": "R",
                "DebugEmissiveMultiplier": DEBUG_EMISSIVE_MULTIPLIER,
                "UsesBoardLocalBounds": True,
                "UsesInBoundsMask": True,
            },
        }

    base_snow = _new_scalar_param(
        parent_material,
        -1200,
        520,
        "BaseSnowAmount",
        BASE_SNOW_AMOUNT,
        "Debug receiver: makes snow visible on the road section before runtime clearing subtracts it.",
    )
    snow_remaining = _new_expr(parent_material, "MaterialExpressionSubtract", -900, 460)
    _connect(base_snow, snow_remaining, "A")
    _connect(effective_clear_mask_clamped, snow_remaining, "B")

    snow_remaining_non_negative = _new_expr(parent_material, "MaterialExpressionMax", -600, 400)
    _connect(snow_remaining, snow_remaining_non_negative, "A")
    _connect(zero, snow_remaining_non_negative, "B")

    snow_remaining_clamped = _new_expr(parent_material, "MaterialExpressionMin", -300, 400)
    _connect(snow_remaining_non_negative, snow_remaining_clamped, "A")
    _connect(one, snow_remaining_clamped, "B")

    snow_tint_strength = _new_scalar_param(parent_material, -600, 180, "SnowTintStrength", SNOW_TINT_STRENGTH)
    snow_alpha = _new_expr(parent_material, "MaterialExpressionMultiply", -300, 320)
    _connect(snow_remaining_clamped, snow_alpha, "A")
    _connect(snow_tint_strength, snow_alpha, "B")

    snow_alpha_top_only = _new_expr(parent_material, "MaterialExpressionMultiply", -20, 320)
    _connect(snow_alpha, snow_alpha_top_only, "A")
    _connect(up_facing_mask, snow_alpha_top_only, "B")

    snow_alpha_road_only = _new_expr(parent_material, "MaterialExpressionMultiply", 220, 320)
    _connect(snow_alpha_top_only, snow_alpha_road_only, "A")
    _connect(road_surface_mask, snow_alpha_road_only, "B")

    snow_uv_scale = _new_scalar_param(parent_material, -3300, -520, "SnowUVScale", SNOW_UV_SCALE)
    snow_scaled_uv = _new_expr(parent_material, "MaterialExpressionMultiply", -2700, -420)
    _connect(texcoord, snow_scaled_uv, "A")
    _connect(snow_uv_scale, snow_scaled_uv, "B")

    snow_diffuse_sample = _new_texture_param(parent_material, -2400, -320, "Snow_Diffuse", snow_diffuse)
    _connect(snow_scaled_uv, snow_diffuse_sample, "Coordinates")

    snow_color_tint = _new_color(parent_material, -2100, -420, SNOW_COLOR_TINT)
    snow_diffuse_tinted = _new_expr(parent_material, "MaterialExpressionMultiply", -1800, -320)
    _connect(snow_diffuse_sample, snow_diffuse_tinted, "A")
    _connect(snow_color_tint, snow_diffuse_tinted, "B")

    snow_normal_sample = _new_texture_param(parent_material, -2400, -40, "Snow_Normal", snow_normal)
    _set_sampler_type(snow_normal_sample, "SAMPLERTYPE_NORMAL")
    _connect(snow_scaled_uv, snow_normal_sample, "Coordinates")

    snow_roughness_sample = _new_texture_param(parent_material, -2400, 260, "Snow_Roughness", snow_roughness)
    _connect(snow_scaled_uv, snow_roughness_sample, "Coordinates")

    snow_rough_r = _new_expr(parent_material, "MaterialExpressionDotProduct", -2100, 260)
    _connect(snow_roughness_sample, snow_rough_r, "A")
    _connect(axis4_x, snow_rough_r, "B")

    base_color = _new_expr(parent_material, "MaterialExpressionLinearInterpolate", 420, 160)
    _connect(road_tex, base_color, "A")
    _connect(snow_diffuse_tinted, base_color, "B")
    _connect(snow_alpha_road_only, base_color, "Alpha")

    normal = _new_expr(parent_material, "MaterialExpressionLinearInterpolate", 420, 520)
    _connect(road_normal_source, normal, "A")
    _connect(snow_normal_sample, normal, "B")
    _connect(snow_alpha_road_only, normal, "Alpha")

    road_roughness = _new_constant(parent_material, 40, 760, BASE_ROAD_ROUGHNESS)
    roughness = _new_expr(parent_material, "MaterialExpressionLinearInterpolate", 420, 820)
    _connect(road_roughness, roughness, "A")
    _connect(snow_rough_r, roughness, "B")
    _connect(snow_alpha_road_only, roughness, "Alpha")

    trace_tint = _new_color(parent_material, 720, 1080, DEBUG_RT_TINT)
    trace_emissive_strength = _new_scalar_param(
        parent_material,
        420,
        1120,
        "TraceDebugEmissiveMultiplier",
        TRACE_DEBUG_EMISSIVE_MULTIPLIER,
        "Temporary debug overlay to make RT-driven clearing obvious on the road receiver.",
    )
    clear_mask_top_only = _new_expr(parent_material, "MaterialExpressionMultiply", 720, 920)
    _connect(effective_clear_mask_clamped, clear_mask_top_only, "A")
    _connect(up_facing_mask, clear_mask_top_only, "B")
    clear_mask_road_only = _new_expr(parent_material, "MaterialExpressionMultiply", 960, 920)
    _connect(clear_mask_top_only, clear_mask_road_only, "A")
    _connect(road_surface_mask, clear_mask_road_only, "B")
    trace_emissive_tinted = _new_expr(parent_material, "MaterialExpressionMultiply", 1020, 1080)
    _connect(clear_mask_road_only, trace_emissive_tinted, "A")
    _connect(trace_tint, trace_emissive_tinted, "B")
    trace_emissive = _new_expr(parent_material, "MaterialExpressionMultiply", 1320, 1080)
    _connect(trace_emissive_tinted, trace_emissive, "A")
    _connect(trace_emissive_strength, trace_emissive, "B")

    MATERIAL_LIB.connect_material_property(base_color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MATERIAL_LIB.connect_material_property(roughness, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MATERIAL_LIB.connect_material_property(normal, "", unreal.MaterialProperty.MP_NORMAL)
    MATERIAL_LIB.connect_material_property(trace_emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    nanite_usage_result = _enable_nanite_usage(parent_material)
    MATERIAL_LIB.recompile_material(parent_material)
    MATERIAL_LIB.layout_material_expressions(parent_material)

    saved = bool(ASSET_LIB.save_loaded_asset(parent_material, False))
    return {
        "parent_material_path": _object_path(parent_material),
        "road_texture_path": _object_path(road_texture),
        "road_normal_texture_path": _object_path(road_normal_texture),
        "using_flat_road_normal": using_flat_road_normal,
        "snow_rt_path": _object_path(snow_rt),
        "mpc_path": _object_path(mpc),
        "snow_diffuse_path": _object_path(snow_diffuse),
        "snow_normal_path": _object_path(snow_normal),
        "snow_roughness_path": _object_path(snow_roughness),
        "saved": saved,
        "nanite_usage_result": nanite_usage_result,
        "parameters": {
            "BaseSnowAmount": BASE_SNOW_AMOUNT,
            "SnowTintStrength": SNOW_TINT_STRENGTH,
            "SnowColorTint": list(SNOW_COLOR_TINT),
            "ClearMaskAmplify": CLEAR_MASK_AMPLIFY,
            "RoadUVScale": ROAD_UV_SCALE,
            "SnowUVScale": SNOW_UV_SCALE,
            "TraceDebugEmissiveMultiplier": TRACE_DEBUG_EMISSIVE_MULTIPLIER,
            "UpFacingNormalThreshold": UP_FACING_NORMAL_THRESHOLD,
            "UpFacingMaskSharpness": UP_FACING_MASK_SHARPNESS,
            "RoadDarkMaskThreshold": ROAD_DARK_MASK_THRESHOLD,
            "RoadDarkMaskSharpness": ROAD_DARK_MASK_SHARPNESS,
            "DebugDirectRTVis": False,
            "DebugUseTexcoordClearMask": DEBUG_USE_TEXCOORD_CLEAR_MASK,
        },
    }


def _apply_instance_to_test_actor(instance_asset) -> dict:
    try:
        apply_result = prsra.apply_material_to_actor_slot0(TEST_ACTOR_PATH, RECEIVER_INSTANCE_PATH)
    except Exception as exc:
        return {
            "actor_path": TEST_ACTOR_PATH,
            "applied": False,
            "error": str(exc),
        }

    save_result = _save_current_level()
    return {
        "actor_path": TEST_ACTOR_PATH,
        "instance_path": _object_path(instance_asset),
        "applied": bool(apply_result.get("num_components_updated", 0) > 0),
        "apply_result": apply_result,
        "save_result": save_result,
    }


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    result = {
        "success": False,
        "summary": "",
        "notes": [
            "This rebuilds only the isolated road receiver chain under /Game/CityPark/SnowSystem/Receivers.",
            "It does not reparent any road material to a landscape snow material.",
            "It keeps the change scoped to the test road receiver workflow.",
        ],
    }

    try:
        prep_result = _prepare_receiver_assets()
        mpc = _load_asset(MPC_PATH)
        snow_rt = _load_asset(SNOW_RT_PATH)
        snow_diffuse = _load_asset(SNOW_DIFFUSE_PATH)
        snow_normal = _load_asset(SNOW_NORMAL_PATH)
        snow_roughness = _load_asset(SNOW_ROUGHNESS_PATH)

        parent_material = _recreate_material_asset(RECEIVER_PARENT_PATH)
        instance_asset = _load_or_create_material_instance_asset(RECEIVER_INSTANCE_PATH)

        road_texture = _get_instance_texture(instance_asset, "Road")
        road_normal_texture = _get_instance_texture(instance_asset, "Road_N")
        source_instance = None
        if road_texture is None or road_normal_texture is None:
            source_instance = _load_asset(SOURCE_INSTANCE_PATH)
        if road_texture is None and source_instance is not None:
            road_texture = _get_instance_texture(source_instance, "Road")
        if road_normal_texture is None and source_instance is not None:
            road_normal_texture = _get_instance_texture(source_instance, "Road_N")
        if road_texture is None:
            raise RuntimeError("Could not resolve the base road texture parameter 'Road'.")
        if road_normal_texture is None:
            _warn("Could not resolve 'Road_N'; using a flat normal fallback for the isolated road receiver.")

        rebuild_result = _rebuild_parent_material(
            parent_material,
            road_texture,
            road_normal_texture,
            snow_rt,
            mpc,
            snow_diffuse,
            snow_normal,
            snow_roughness,
        )
        try:
            instance_asset.modify()
        except Exception:
            pass
        instance_asset.set_editor_property("parent", parent_material)
        instance_saved = bool(ASSET_LIB.save_loaded_asset(instance_asset, False))
        actor_apply_result = _apply_instance_to_test_actor(instance_asset)

        result.update(
            {
                "prep_result": prep_result,
                "rebuild_result": rebuild_result,
                "instance_path": _object_path(instance_asset),
                "instance_parent_after": _object_path(instance_asset.get_editor_property("parent")),
                "instance_saved": instance_saved,
                "actor_apply_result": actor_apply_result,
            }
        )
        result["success"] = bool(rebuild_result.get("saved"))
        result["summary"] = (
            f"Rebuilt isolated road receiver parent={rebuild_result.get('parent_material_path')} "
            f"instance_saved={instance_saved} actor_applied={actor_apply_result.get('applied')}"
        )
    except Exception as exc:
        result["success"] = False
        result["error"] = str(exc)
        result["summary"] = f"Failed to rebuild visible road snow receiver: {exc}"
        _warn(result["summary"])

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary(output_dir: str | None = None):
    payload = run(output_dir)
    _log(payload["summary"])
    _log(f"summary_path={payload['output_path']}")
    return {
        "success": payload.get("success", False),
        "summary": payload.get("summary", ""),
        "output_path": payload.get("output_path", ""),
    }


if __name__ == "__main__":
    print_summary()
