import json
import os
import runpy

import unreal


WRITER_MATERIAL_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_RVT_DebugWriter_MVP"
RECEIVER_PARENT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP"
LANDSCAPE_MI_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_LandscapeRuntimeFix"
REBUILD_RECEIVER_SCRIPT = (
    "C:/Users/post/Documents/Unreal Projects/Kamaz_Cleaner/Pyton_script/unreal_tools/"
    "rebuild_m_snowreceiver_rvt_height_mvp_clean.py"
)
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "apply_repeat_clearing_accumulation.json",
)

ASSET_LIB = unreal.EditorAssetLibrary
MAT_LIB = unreal.MaterialEditingLibrary


def _safe_set(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception:
        return False


def _expr(material, cls_name, x, y):
    cls = getattr(unreal, cls_name, None)
    if cls is None:
        raise RuntimeError(f"Missing class {cls_name}")
    expr = MAT_LIB.create_material_expression(material, cls, x, y)
    if expr is None:
        raise RuntimeError(f"Failed create {cls_name}")
    _safe_set(expr, "material_expression_editor_x", x)
    _safe_set(expr, "material_expression_editor_y", y)
    return expr


def _connect(src, src_outs, dst, dst_ins):
    if isinstance(src_outs, str):
        src_outs = [src_outs]
    if isinstance(dst_ins, str):
        dst_ins = [dst_ins]
    for src_out in src_outs:
        for dst_in in dst_ins:
            try:
                MAT_LIB.connect_material_expressions(src, src_out if src_out else "", dst, dst_in if dst_in else "")
                return {"ok": True, "src": src_out, "dst": dst_in}
            except Exception:
                pass
    return {"ok": False, "src": "", "dst": ""}


def _scalar_param(material, x, y, name, default):
    expr = _expr(material, "MaterialExpressionScalarParameter", x, y)
    _safe_set(expr, "parameter_name", name)
    _safe_set(expr, "default_value", float(default))
    return expr


def _const(material, x, y, value):
    expr = _expr(material, "MaterialExpressionConstant", x, y)
    _safe_set(expr, "r", float(value))
    return expr


def _update_landscape_instance(result):
    parent = ASSET_LIB.load_asset(RECEIVER_PARENT_PATH)
    if not parent:
        raise RuntimeError(f"Missing receiver parent: {RECEIVER_PARENT_PATH}")

    instance = ASSET_LIB.load_asset(LANDSCAPE_MI_PATH)
    if not instance:
        raise RuntimeError(f"Missing landscape MI: {LANDSCAPE_MI_PATH}")

    _safe_set(instance, "parent", parent)
    # Disable additive uplift branches while we validate that clear-only WPO is stable again.
    MAT_LIB.set_material_instance_scalar_parameter_value(instance, "RightBermRaise", 0.0)
    MAT_LIB.set_material_instance_scalar_parameter_value(instance, "RightBermSharpness", 1.0)
    MAT_LIB.set_material_instance_scalar_parameter_value(instance, "RepeatAccumulationDepth", 0.0)
    MAT_LIB.update_material_instance(instance)
    result["landscape_mi_saved"] = bool(ASSET_LIB.save_loaded_asset(instance, False))


def rebuild_writer_with_clear_strength(material, result):
    MAT_LIB.delete_all_material_expressions(material)

    _safe_set(material, "material_domain", unreal.MaterialDomain.MD_SURFACE)
    _safe_set(material, "blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    _safe_set(material, "shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)

    uv = _expr(material, "MaterialExpressionTextureCoordinate", -1400, -40)
    berm_only = _scalar_param(material, -1180, 100, "BermOnly", 0.0)
    berm_only_sat = _expr(material, "MaterialExpressionSaturate", -920, 100)
    _connect(berm_only, "", berm_only_sat, ["Input", ""])

    white = _expr(material, "MaterialExpressionConstant3Vector", 220, -220)
    _safe_set(white, "constant", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    base_rgb = _expr(material, "MaterialExpressionMultiply", 460, -120)
    _connect(berm_only_sat, "", base_rgb, "A")
    _connect(white, "", base_rgb, "B")

    clear_strength = _scalar_param(material, 220, 180, "ClearStrength", 1.0)
    clear_strength_sat = _expr(material, "MaterialExpressionSaturate", 460, 180)
    _connect(clear_strength, "", clear_strength_sat, ["Input", ""])

    repeat_depth_strength = _scalar_param(material, 220, 250, "RepeatDepthStrength", 0.0)
    repeat_depth_strength_sat = _expr(material, "MaterialExpressionSaturate", 460, 250)
    _connect(repeat_depth_strength, "", repeat_depth_strength_sat, ["Input", ""])

    c0 = _const(material, 220, 390, 0.0)
    nrm = _expr(material, "MaterialExpressionConstant3Vector", 460, 320)
    _safe_set(nrm, "constant", unreal.LinearColor(0.5, 0.5, 1.0, 1.0))

    rvt_out = _expr(material, "MaterialExpressionRuntimeVirtualTextureOutput", 920, 20)
    result["connect_basecolor"] = _connect(base_rgb, "", rvt_out, ["Base Color", "BaseColor"])
    result["connect_specular"] = _connect(repeat_depth_strength_sat, "", rvt_out, "Specular")
    result["connect_roughness"] = _connect(c0, "", rvt_out, "Roughness")
    result["connect_normal"] = _connect(nrm, "", rvt_out, "Normal")
    result["connect_mask"] = _connect(clear_strength_sat, "", rvt_out, ["Mask", "mask"])

    MAT_LIB.connect_material_property(base_rgb, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MAT_LIB.connect_material_property(c0, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MAT_LIB.connect_material_property(nrm, "", unreal.MaterialProperty.MP_NORMAL)

    MAT_LIB.recompile_material(material)
    MAT_LIB.layout_material_expressions(material)
    result["saved"] = bool(ASSET_LIB.save_loaded_asset(material, False))
    result["num_expressions"] = int(MAT_LIB.get_num_material_expressions(material))


def main():
    result = {
        "mode": "apply_repeat_clearing_accumulation",
        "writer_material": WRITER_MATERIAL_PATH,
        "receiver_parent": RECEIVER_PARENT_PATH,
        "landscape_mi": LANDSCAPE_MI_PATH,
        "saved": False,
        "receiver_rebuilt": False,
        "landscape_mi_saved": False,
        "num_expressions": 0,
        "connect_basecolor": {},
        "connect_specular": {},
        "connect_roughness": {},
        "connect_normal": {},
        "connect_mask": {},
        "error": "",
    }

    try:
        runpy.run_path(REBUILD_RECEIVER_SCRIPT, run_name="__main__")
        result["receiver_rebuilt"] = True

        writer = ASSET_LIB.load_asset(WRITER_MATERIAL_PATH)
        if not writer:
            raise RuntimeError(f"Missing writer material: {WRITER_MATERIAL_PATH}")
        rebuild_writer_with_clear_strength(writer, result)
        _update_landscape_instance(result)
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
