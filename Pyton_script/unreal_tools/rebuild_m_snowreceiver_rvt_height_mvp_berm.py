import gc
import json
import os

import unreal
from road2_writer_policy import ensure_road2_writer_allowed


ROAD2_WRITER_POLICY = ensure_road2_writer_allowed(__file__)


MATERIAL_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP"
BACKUP_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP_Backup_BaselineRecovery"
RVT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP"
SNOW_DIFFUSE_PATH = "/Game/CAA_SnowV2/SnowV2P1/TexturesP1/T_SnowV2P1_2K_Diffuse"
SNOW_NORMAL_PATH = "/Game/CAA_SnowV2/SnowV2P1/TexturesP1/T_SnowV2P1_2K_Normal"
SNOW_ROUGHNESS_PATH = "/Game/CAA_SnowV2/SnowV2P1/TexturesP1/T_SnowV2P1_2K_Roughness"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "rebuild_m_snowreceiver_rvt_height_mvp_berm.json",
)


ASSET_LIB = unreal.EditorAssetLibrary
MAT_LIB = unreal.MaterialEditingLibrary
ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def _safe_set(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception:
        return False


def _load_asset(path):
    asset = ASSET_LIB.load_asset(path)
    if asset is None:
        raise RuntimeError(f"Missing asset: {path}")
    return asset


def _ensure_dir(package_path):
    if not ASSET_LIB.does_directory_exist(package_path):
        ASSET_LIB.make_directory(package_path)


def _expr(material, cls_name, x, y):
    cls = getattr(unreal, cls_name, None)
    if cls is None:
        raise RuntimeError(f"Missing class {cls_name}")
    expr = MAT_LIB.create_material_expression(material, cls, x, y)
    if expr is None:
        raise RuntimeError(f"Could not create expression {cls_name}")
    _safe_set(expr, "material_expression_editor_x", x)
    _safe_set(expr, "material_expression_editor_y", y)
    return expr


def _connect(src, src_pin, dst, dst_pin):
    resolved_src_pin = src_pin if src_pin else ""
    resolved_dst_pin = dst_pin if dst_pin else ""
    if resolved_dst_pin == "Input" and dst.get_class().get_name() in (
        "MaterialExpressionComponentMask",
        "MaterialExpressionAbs",
        "MaterialExpressionSaturate",
        "MaterialExpressionOneMinus",
    ):
        resolved_dst_pin = ""
    MAT_LIB.connect_material_expressions(src, resolved_src_pin, dst, resolved_dst_pin)


def _try_connect(src, src_names, dst, dst_names):
    if isinstance(src_names, str):
        src_names = [src_names]
    if isinstance(dst_names, str):
        dst_names = [dst_names]
    for src_pin in src_names:
        for dst_pin in dst_names:
            try:
                _connect(src, src_pin, dst, dst_pin)
                return {"ok": True, "src": src_pin, "dst": dst_pin}
            except Exception:
                pass
    return {"ok": False, "src": "", "dst": ""}


def _scalar_param(material, x, y, name, default):
    expr = _expr(material, "MaterialExpressionScalarParameter", x, y)
    _safe_set(expr, "parameter_name", name)
    _safe_set(expr, "default_value", float(default))
    return expr


def _vector_param(material, x, y, name, rgba):
    expr = _expr(material, "MaterialExpressionVectorParameter", x, y)
    _safe_set(expr, "parameter_name", name)
    _safe_set(
        expr,
        "default_value",
        unreal.LinearColor(float(rgba[0]), float(rgba[1]), float(rgba[2]), float(rgba[3])),
    )
    return expr


def _texture_param(material, x, y, name, texture):
    expr = _expr(material, "MaterialExpressionTextureSampleParameter2D", x, y)
    _safe_set(expr, "parameter_name", name)
    _safe_set(expr, "texture", texture)
    return expr


def _const(material, x, y, value):
    expr = _expr(material, "MaterialExpressionConstant", x, y)
    _safe_set(expr, "r", float(value))
    return expr


def _clamp01(material, x, y, input_expr, input_pin=""):
    zero = _const(material, x, y + 120, 0.0)
    one = _const(material, x, y + 240, 1.0)
    max_expr = _expr(material, "MaterialExpressionMax", x + 220, y)
    _connect(input_expr, input_pin, max_expr, "A")
    _connect(zero, "", max_expr, "B")
    min_expr = _expr(material, "MaterialExpressionMin", x + 440, y)
    _connect(max_expr, "", min_expr, "A")
    _connect(one, "", min_expr, "B")
    return min_expr


def _recreate_material_with_backup():
    package_path, asset_name = MATERIAL_PATH.rsplit("/", 1)
    _ensure_dir(package_path)

    existing = ASSET_LIB.load_asset(MATERIAL_PATH)
    backup_created = False
    if existing is not None:
        if not isinstance(existing, unreal.Material):
            raise RuntimeError(f"Existing asset is not a Material: {MATERIAL_PATH}")
        if not ASSET_LIB.does_asset_exist(BACKUP_PATH):
            backup_created = bool(ASSET_LIB.duplicate_asset(MATERIAL_PATH, BACKUP_PATH))
        if not ASSET_LIB.delete_asset(MATERIAL_PATH):
            raise RuntimeError(f"Failed to delete material before rebuild: {MATERIAL_PATH}")

    created = ASSET_TOOLS.create_asset(
        asset_name,
        package_path,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if created is None:
        raise RuntimeError(f"Failed to recreate material: {MATERIAL_PATH}")
    return created, backup_created


def main():
    result = {
        "material_path": MATERIAL_PATH,
        "backup_path": BACKUP_PATH,
        "backup_created": False,
        "saved": False,
        "num_expressions": 0,
        "connections": [],
        "error": "",
    }

    try:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
            json.dump({"started": True, "material_path": MATERIAL_PATH}, handle, indent=2, ensure_ascii=False)

        material, backup_created = _recreate_material_with_backup()
        result["backup_created"] = backup_created

        rvt_asset = _load_asset(RVT_PATH)
        snow_diffuse = _load_asset(SNOW_DIFFUSE_PATH)
        snow_normal = _load_asset(SNOW_NORMAL_PATH)
        snow_roughness = _load_asset(SNOW_ROUGHNESS_PATH)

        _safe_set(material, "material_domain", unreal.MaterialDomain.MD_SURFACE)
        _safe_set(material, "blend_mode", unreal.BlendMode.BLEND_MASKED)
        _safe_set(material, "opacity_mask_clip_value", 0.2)
        _safe_set(material, "shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
        _safe_set(material, "use_material_attributes", False)
        _safe_set(material, "two_sided", True)
        _safe_set(material, "used_with_landscape", True)
        _safe_set(material, "bUsedWithLandscape", True)
        _safe_set(material, "used_with_nanite", True)
        _safe_set(material, "bUsedWithNanite", True)
        _safe_set(material, "used_with_spline_meshes", True)
        _safe_set(material, "bUsedWithSplineMeshes", True)

        texcoord = _expr(material, "MaterialExpressionTextureCoordinate", -2600, -280)
        snow_uv_scale = _scalar_param(material, -2600, -120, "SnowTexUVScale", 10.0)
        scaled_uv = _expr(material, "MaterialExpressionMultiply", -2360, -220)
        _connect(texcoord, "", scaled_uv, "A")
        _connect(snow_uv_scale, "", scaled_uv, "B")

        snow_diffuse_expr = _texture_param(material, -2100, -420, "Snow_Diffuse", snow_diffuse)
        _connect(scaled_uv, "", snow_diffuse_expr, "UVs")

        snow_normal_expr = _texture_param(material, -2100, -40, "Snow_Normal", snow_normal)
        _connect(scaled_uv, "", snow_normal_expr, "UVs")

        snow_roughness_expr = _texture_param(material, -2100, 240, "Snow_Roughness", snow_roughness)
        _connect(scaled_uv, "", snow_roughness_expr, "UVs")

        rvt_sample = _expr(material, "MaterialExpressionRuntimeVirtualTextureSampleParameter", -2600, 720)
        _safe_set(rvt_sample, "parameter_name", "SnowRVT")
        _safe_set(rvt_sample, "virtual_texture", rvt_asset)
        mat_type = getattr(unreal.RuntimeVirtualTextureMaterialType, "BASE_COLOR_NORMAL_SPECULAR_MASK_Y_CO_CG", None)
        if mat_type is not None:
            _safe_set(rvt_sample, "material_type", mat_type)

        mask_sat = _clamp01(material, -2360, 720, rvt_sample, "Mask")
        result["connections"].append({"ok": True, "src": "Mask", "dst": "Clamp01"})

        height_contrast = _scalar_param(material, -2360, 900, "HeightContrast", 1.0)
        mask_pow = _expr(material, "MaterialExpressionPower", -1880, 720)
        result["connections"].append(_try_connect(mask_sat, [""], mask_pow, ["Base", "A"]))
        result["connections"].append(_try_connect(height_contrast, [""], mask_pow, ["Exp", "B"]))

        one_minus_mask = _expr(material, "MaterialExpressionOneMinus", -1640, 860)
        result["connections"].append(_try_connect(mask_pow, [""], one_minus_mask, ["", "Input"]))

        invert_clear_mask = _scalar_param(material, -1880, 900, "InvertClearMask", 0.0)
        clear_mask = _expr(material, "MaterialExpressionLinearInterpolate", -1400, 780)
        result["connections"].append(_try_connect(mask_pow, [""], clear_mask, ["A"]))
        result["connections"].append(_try_connect(one_minus_mask, [""], clear_mask, ["B"]))
        result["connections"].append(_try_connect(invert_clear_mask, [""], clear_mask, ["Alpha"]))

        visual_clear_mask_strength = _scalar_param(material, -1880, 1080, "VisualClearMaskStrength", 1.0)
        visual_mask_scaled = _expr(material, "MaterialExpressionMultiply", -1640, 1040)
        result["connections"].append(_try_connect(clear_mask, [""], visual_mask_scaled, ["A"]))
        result["connections"].append(_try_connect(visual_clear_mask_strength, [""], visual_mask_scaled, ["B"]))
        visual_clear = _clamp01(material, -1400, 1040, visual_mask_scaled, "")
        result["connections"].append({"ok": True, "src": "", "dst": "Clamp01"})

        depth_mask_boost = _scalar_param(material, -1880, 1260, "DepthMaskBoost", 1.0)
        depth_mask_scaled = _expr(material, "MaterialExpressionMultiply", -1640, 1220)
        result["connections"].append(_try_connect(clear_mask, [""], depth_mask_scaled, ["A"]))
        result["connections"].append(_try_connect(depth_mask_boost, [""], depth_mask_scaled, ["B"]))
        depth_clear = _clamp01(material, -1400, 1220, depth_mask_scaled, "")
        result["connections"].append({"ok": True, "src": "", "dst": "Clamp01"})

        baseline_snow_coverage = _scalar_param(material, -1880, 1440, "BaselineSnowCoverage", 0.0)
        baseline_height_cm = _scalar_param(material, -1880, 1620, "BaselineHeightCm", 0.0)
        height_amplitude = _scalar_param(material, -1880, 1800, "HeightAmplitude", 0.0)
        # Keep RVT methodology clean: the plow lowering state may flip HeightAmplitude globally,
        # but only the sampled RVT footprint should reduce visible snow on the carrier.
        local_clear_gate = _clamp01(material, -1400, 1320, visual_clear, "")
        result["connections"].append({"ok": True, "src": "", "dst": "Clamp01"})
        remaining_raw = _expr(material, "MaterialExpressionSubtract", -1400, 1400)
        result["connections"].append(_try_connect(baseline_snow_coverage, [""], remaining_raw, ["A"]))
        result["connections"].append(_try_connect(local_clear_gate, [""], remaining_raw, ["B"]))
        remaining_snow = _clamp01(material, -1160, 1400, remaining_raw, "")
        result["connections"].append({"ok": True, "src": "", "dst": "Clamp01"})

        snow_color = _vector_param(material, -1880, -420, "SnowColor", (0.94, 0.96, 1.0, 1.0))
        road_snow_visual_color = _vector_param(material, -1880, -260, "RoadSnowVisualColor", (0.985, 0.99, 1.0, 1.0))
        road_snow_visual_whiten_strength = _scalar_param(material, -1880, -100, "RoadSnowVisualWhitenStrength", 0.0)
        whitened_snow = _expr(material, "MaterialExpressionLinearInterpolate", -1640, -320)
        result["connections"].append(_try_connect(snow_color, [""], whitened_snow, ["A"]))
        result["connections"].append(_try_connect(road_snow_visual_color, [""], whitened_snow, ["B"]))
        result["connections"].append(_try_connect(road_snow_visual_whiten_strength, [""], whitened_snow, ["Alpha"]))

        snow_detail_influence = _scalar_param(material, -1880, 60, "SnowDetailInfluence", 0.18)
        detailed_snow = _expr(material, "MaterialExpressionLinearInterpolate", -1400, -320)
        result["connections"].append(_try_connect(whitened_snow, [""], detailed_snow, ["A"]))
        result["connections"].append(_try_connect(snow_diffuse_expr, ["RGB", ""], detailed_snow, ["B"]))
        result["connections"].append(_try_connect(snow_detail_influence, [""], detailed_snow, ["Alpha"]))

        pressed_snow_color = _vector_param(material, -1880, 220, "PressedSnowColor", (0.82, 0.85, 0.9, 1.0))
        recovered_pressed_color = _vector_param(
            material,
            -1880,
            380,
            "RoadSnowRecoveredPressedColor",
            (0.48, 0.49, 0.52, 1.0),
        )
        road_snow_recovered_behavior = _scalar_param(material, -1880, 540, "RoadSnowRecoveredBehavior", 0.0)
        pressed_color_final = _expr(material, "MaterialExpressionLinearInterpolate", -1640, 300)
        result["connections"].append(_try_connect(pressed_snow_color, [""], pressed_color_final, ["A"]))
        result["connections"].append(_try_connect(recovered_pressed_color, [""], pressed_color_final, ["B"]))
        result["connections"].append(_try_connect(road_snow_recovered_behavior, [""], pressed_color_final, ["Alpha"]))

        local_height = _expr(material, "MaterialExpressionMultiply", -900, 1520)
        result["connections"].append(_try_connect(depth_clear, [""], local_height, ["A"]))
        result["connections"].append(_try_connect(height_amplitude, [""], local_height, ["B"]))

        spec_sat = _clamp01(material, -1880, 1760, rvt_sample, "Specular")
        result["connections"].append({"ok": True, "src": "Specular", "dst": "Clamp01"})
        repeat_depth_scale = _scalar_param(material, -1640, 1920, "RepeatAccumulationDepth", 0.0)
        repeat_masked = _expr(material, "MaterialExpressionMultiply", -1400, 1760)
        result["connections"].append(_try_connect(spec_sat, [""], repeat_masked, ["A"]))
        result["connections"].append(_try_connect(depth_clear, [""], repeat_masked, ["B"]))
        repeat_depth = _expr(material, "MaterialExpressionMultiply", -1160, 1760)
        result["connections"].append(_try_connect(repeat_masked, [""], repeat_depth, ["A"]))
        result["connections"].append(_try_connect(repeat_depth_scale, [""], repeat_depth, ["B"]))

        berm_sat = _clamp01(material, -1880, 2120, rvt_sample, "Roughness")
        result["connections"].append({"ok": True, "src": "Roughness", "dst": "Clamp01"})
        right_berm_sharpness = _scalar_param(material, -1640, 2280, "RightBermSharpness", 1.0)
        berm_pow = _expr(material, "MaterialExpressionPower", -1400, 2120)
        result["connections"].append(_try_connect(berm_sat, [""], berm_pow, ["Base", "A"]))
        result["connections"].append(_try_connect(right_berm_sharpness, [""], berm_pow, ["Exp", "B"]))
        right_berm_raise = _scalar_param(material, -1640, 2440, "RightBermRaise", 0.0)
        berm_raise = _expr(material, "MaterialExpressionMultiply", -1160, 2120)
        result["connections"].append(_try_connect(berm_pow, [""], berm_raise, ["A"]))
        result["connections"].append(_try_connect(right_berm_raise, [""], berm_raise, ["B"]))

        depth_sum = _expr(material, "MaterialExpressionAdd", -900, 1680)
        result["connections"].append(_try_connect(local_height, [""], depth_sum, ["A"]))
        result["connections"].append(_try_connect(repeat_depth, [""], depth_sum, ["B"]))

        height_total = _expr(material, "MaterialExpressionAdd", -660, 1840)
        result["connections"].append(_try_connect(depth_sum, [""], height_total, ["A"]))
        result["connections"].append(_try_connect(berm_raise, [""], height_total, ["B"]))

        zero_height = _const(material, -660, 2000, 0.0)
        legacy_negative_only_height = _expr(material, "MaterialExpressionMin", -420, 1760)
        result["connections"].append(_try_connect(height_total, [""], legacy_negative_only_height, ["A"]))
        result["connections"].append(_try_connect(zero_height, [""], legacy_negative_only_height, ["B"]))

        baseline_height_sum = _expr(material, "MaterialExpressionAdd", -420, 1960)
        result["connections"].append(_try_connect(height_total, [""], baseline_height_sum, ["A"]))
        result["connections"].append(_try_connect(baseline_height_cm, [""], baseline_height_sum, ["B"]))

        baseline_positive_height = _expr(material, "MaterialExpressionMax", -180, 1960)
        result["connections"].append(_try_connect(baseline_height_sum, [""], baseline_positive_height, ["A"]))
        result["connections"].append(_try_connect(zero_height, [""], baseline_positive_height, ["B"]))

        baseline_gate = _clamp01(material, -180, 2160, baseline_height_cm, "")
        result["connections"].append({"ok": True, "src": "", "dst": "Clamp01"})

        safe_baseline_floor = _const(material, -420, 2320, 1.0)
        safe_baseline_height = _expr(material, "MaterialExpressionMax", -180, 2320)
        result["connections"].append(_try_connect(baseline_height_cm, [""], safe_baseline_height, ["A"]))
        result["connections"].append(_try_connect(safe_baseline_floor, [""], safe_baseline_height, ["B"]))

        baseline_height_ratio_raw = _expr(material, "MaterialExpressionDivide", 60, 1960)
        result["connections"].append(_try_connect(baseline_positive_height, [""], baseline_height_ratio_raw, ["A"]))
        result["connections"].append(_try_connect(safe_baseline_height, [""], baseline_height_ratio_raw, ["B"]))
        baseline_height_ratio = _clamp01(material, 300, 1960, baseline_height_ratio_raw, "")
        result["connections"].append({"ok": True, "src": "", "dst": "Clamp01"})

        baseline_visible_snow = _clamp01(material, 60, 1400, baseline_snow_coverage, "")
        result["connections"].append({"ok": True, "src": "", "dst": "Clamp01"})
        final_visible_snow = _expr(material, "MaterialExpressionMultiply", 300, 1400)
        result["connections"].append(_try_connect(baseline_visible_snow, [""], final_visible_snow, ["A"]))
        result["connections"].append(_try_connect(remaining_snow, [""], final_visible_snow, ["B"]))

        snow_vs_pressed = _expr(material, "MaterialExpressionLinearInterpolate", 540, -40)
        result["connections"].append(_try_connect(pressed_color_final, [""], snow_vs_pressed, ["A"]))
        result["connections"].append(_try_connect(detailed_snow, [""], snow_vs_pressed, ["B"]))
        result["connections"].append(_try_connect(final_visible_snow, [""], snow_vs_pressed, ["Alpha"]))

        thin_under_color = _vector_param(material, -1640, 640, "ThinSnowUnderColor", (0.52, 0.52, 0.54, 1.0))
        thin_snow_min_visual_opacity = _scalar_param(material, -1640, 800, "ThinSnowMinVisualOpacity", 0.88)
        thin_alpha = _expr(material, "MaterialExpressionLinearInterpolate", 540, 680)
        one_for_thin = _const(material, -1640, 960, 1.0)
        result["connections"].append(_try_connect(thin_snow_min_visual_opacity, [""], thin_alpha, ["A"]))
        result["connections"].append(_try_connect(one_for_thin, [""], thin_alpha, ["B"]))
        result["connections"].append(_try_connect(final_visible_snow, [""], thin_alpha, ["Alpha"]))

        final_base = _expr(material, "MaterialExpressionLinearInterpolate", 780, 200)
        result["connections"].append(_try_connect(thin_under_color, [""], final_base, ["A"]))
        result["connections"].append(_try_connect(snow_vs_pressed, [""], final_base, ["B"]))
        result["connections"].append(_try_connect(thin_alpha, [""], final_base, ["Alpha"]))

        baseline_snow_emissive_strength = _scalar_param(
            material,
            540,
            420,
            "BaselineSnowEmissiveStrength",
            0.0,
        )
        emissive_visible = _expr(material, "MaterialExpressionMultiply", 780, 420)
        result["connections"].append(_try_connect(road_snow_visual_color, [""], emissive_visible, ["A"]))
        result["connections"].append(_try_connect(final_visible_snow, [""], emissive_visible, ["B"]))
        emissive_final = _expr(material, "MaterialExpressionMultiply", 1020, 420)
        result["connections"].append(_try_connect(emissive_visible, [""], emissive_final, ["A"]))
        result["connections"].append(_try_connect(baseline_snow_emissive_strength, [""], emissive_final, ["B"]))

        snow_roughness = _scalar_param(material, -1640, 1120, "SnowRoughness", 0.9)
        rough_tex_mul = _expr(material, "MaterialExpressionMultiply", -1400, 1120)
        result["connections"].append(_try_connect(snow_roughness_expr, ["R", "G", "B", ""], rough_tex_mul, ["A"]))
        result["connections"].append(_try_connect(snow_roughness, [""], rough_tex_mul, ["B"]))

        pressed_roughness = _scalar_param(material, -1640, 1280, "PressedRoughness", 0.5)
        final_roughness = _expr(material, "MaterialExpressionLinearInterpolate", 780, 1080)
        result["connections"].append(_try_connect(pressed_roughness, [""], final_roughness, ["A"]))
        result["connections"].append(_try_connect(rough_tex_mul, [""], final_roughness, ["B"]))
        result["connections"].append(_try_connect(final_visible_snow, [""], final_roughness, ["Alpha"]))

        final_height_for_wpo = _expr(material, "MaterialExpressionLinearInterpolate", 60, 1760)
        result["connections"].append(_try_connect(legacy_negative_only_height, [""], final_height_for_wpo, ["A"]))
        result["connections"].append(_try_connect(baseline_positive_height, [""], final_height_for_wpo, ["B"]))
        result["connections"].append(_try_connect(baseline_gate, [""], final_height_for_wpo, ["Alpha"]))

        world_up = _expr(material, "MaterialExpressionConstant3Vector", 300, 2160)
        _safe_set(world_up, "constant", unreal.LinearColor(0.0, 0.0, 1.0, 1.0))
        wpo_mul = _expr(material, "MaterialExpressionMultiply", 540, 1920)
        result["connections"].append(_try_connect(world_up, [""], wpo_mul, ["A"]))
        result["connections"].append(_try_connect(final_height_for_wpo, [""], wpo_mul, ["B"]))

        MAT_LIB.connect_material_property(final_base, "", unreal.MaterialProperty.MP_BASE_COLOR)
        MAT_LIB.connect_material_property(final_roughness, "", unreal.MaterialProperty.MP_ROUGHNESS)
        MAT_LIB.connect_material_property(snow_normal_expr, "RGB", unreal.MaterialProperty.MP_NORMAL)
        MAT_LIB.connect_material_property(emissive_final, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        # Road2 must reveal the real road once the local snow column has been materially cut.
        # Using a soft multiply leaves per-stamp carrier plaques alive, so drive opacity from
        # the minimum surviving snow signal and force a thresholded drop-out.
        reveal_opacity_threshold = _scalar_param(material, 60, 1520, "RevealOpacityThreshold", 0.82)
        reveal_opacity_power = _scalar_param(material, 60, 1680, "RevealOpacityPower", 2.0)
        opacity_presence_min = _expr(material, "MaterialExpressionMin", 300, 1520)
        result["connections"].append(_try_connect(final_visible_snow, [""], opacity_presence_min, ["A"]))
        result["connections"].append(_try_connect(baseline_height_ratio, [""], opacity_presence_min, ["B"]))
        opacity_threshold_sub = _expr(material, "MaterialExpressionSubtract", 540, 1520)
        result["connections"].append(_try_connect(opacity_presence_min, [""], opacity_threshold_sub, ["A"]))
        result["connections"].append(_try_connect(reveal_opacity_threshold, [""], opacity_threshold_sub, ["B"]))
        reveal_one = _const(material, 60, 1840, 1.0)
        reveal_epsilon = _const(material, 60, 1960, 0.001)
        reveal_threshold_range = _expr(material, "MaterialExpressionSubtract", 300, 1840)
        result["connections"].append(_try_connect(reveal_one, [""], reveal_threshold_range, ["A"]))
        result["connections"].append(_try_connect(reveal_opacity_threshold, [""], reveal_threshold_range, ["B"]))
        reveal_threshold_safe = _expr(material, "MaterialExpressionMax", 540, 1840)
        result["connections"].append(_try_connect(reveal_threshold_range, [""], reveal_threshold_safe, ["A"]))
        result["connections"].append(_try_connect(reveal_epsilon, [""], reveal_threshold_safe, ["B"]))
        opacity_normalized_raw = _expr(material, "MaterialExpressionDivide", 780, 1520)
        result["connections"].append(_try_connect(opacity_threshold_sub, [""], opacity_normalized_raw, ["A"]))
        result["connections"].append(_try_connect(reveal_threshold_safe, [""], opacity_normalized_raw, ["B"]))
        opacity_normalized = _clamp01(material, 1020, 1520, opacity_normalized_raw, "")
        result["connections"].append({"ok": True, "src": "", "dst": "Clamp01"})
        opacity_mask_power = _expr(material, "MaterialExpressionPower", 1260, 1520)
        result["connections"].append(_try_connect(opacity_normalized, [""], opacity_mask_power, ["Base", "A"]))
        result["connections"].append(_try_connect(reveal_opacity_power, [""], opacity_mask_power, ["Exp", "B"]))
        MAT_LIB.connect_material_property(opacity_mask_power, "", unreal.MaterialProperty.MP_OPACITY_MASK)
        MAT_LIB.connect_material_property(wpo_mul, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)

        MAT_LIB.layout_material_expressions(material)
        MAT_LIB.recompile_material(material)
        result["num_expressions"] = int(MAT_LIB.get_num_material_expressions(material))
        result["saved"] = bool(ASSET_LIB.save_loaded_asset(material, False))

        material = None
        rvt_asset = None
        snow_diffuse = None
        snow_normal = None
        snow_roughness = None
        gc.collect()
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
