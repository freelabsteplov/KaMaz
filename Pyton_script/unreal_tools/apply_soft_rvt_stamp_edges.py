import json
import os

import unreal


WRITER_MATERIAL_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_RVT_DebugWriter_MVP"
LANDSCAPE_MI_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_LandscapeRuntimeFix"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "apply_soft_rvt_stamp_edges.json",
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


def rebuild_writer_material(material, result):
    MAT_LIB.delete_all_material_expressions(material)

    _safe_set(material, "material_domain", unreal.MaterialDomain.MD_SURFACE)
    _safe_set(material, "blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    _safe_set(material, "shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)

    # Restore the known-good active clearing writer:
    # Mask stays constant 1 for clearing semantics, while BaseColor carries side-rim shaping.
    uv = _expr(material, "MaterialExpressionTextureCoordinate", -1400, -40)
    vmask = _expr(material, "MaterialExpressionComponentMask", -1180, -40)
    _safe_set(vmask, "r", False)
    _safe_set(vmask, "g", True)
    _safe_set(vmask, "b", False)
    _safe_set(vmask, "a", False)
    _connect(uv, "", vmask, ["Input", ""])

    edge_pct = _scalar_param(material, -1400, 160, "EdgeBandPercent", 0.05)
    eps = _const(material, -1400, 320, 0.001)
    one = _const(material, -1160, 320, 1.0)

    edge_safe = _expr(material, "MaterialExpressionMax", -920, 160)
    _connect(edge_pct, "", edge_safe, "A")
    _connect(eps, "", edge_safe, "B")

    left_delta = _expr(material, "MaterialExpressionSubtract", -920, -80)
    _connect(edge_safe, "", left_delta, "A")
    _connect(vmask, "", left_delta, "B")

    left_ratio = _expr(material, "MaterialExpressionDivide", -680, -80)
    _connect(left_delta, "", left_ratio, "A")
    _connect(edge_safe, "", left_ratio, "B")

    left_sat = _expr(material, "MaterialExpressionSaturate", -460, -80)
    _connect(left_ratio, "", left_sat, ["Input", ""])

    one_minus_edge = _expr(material, "MaterialExpressionSubtract", -920, 40)
    _connect(one, "", one_minus_edge, "A")
    _connect(edge_safe, "", one_minus_edge, "B")

    right_delta = _expr(material, "MaterialExpressionSubtract", -680, 40)
    _connect(vmask, "", right_delta, "A")
    _connect(one_minus_edge, "", right_delta, "B")

    right_ratio = _expr(material, "MaterialExpressionDivide", -460, 40)
    _connect(right_delta, "", right_ratio, "A")
    _connect(edge_safe, "", right_ratio, "B")

    right_sat = _expr(material, "MaterialExpressionSaturate", -240, 40)
    _connect(right_ratio, "", right_sat, ["Input", ""])

    rims_sum = _expr(material, "MaterialExpressionAdd", 0, -20)
    _connect(left_sat, "", rims_sum, "A")
    _connect(right_sat, "", rims_sum, "B")

    rims_mask = _expr(material, "MaterialExpressionSaturate", 220, -20)
    _connect(rims_sum, "", rims_mask, ["Input", ""])

    white = _expr(material, "MaterialExpressionConstant3Vector", 220, -220)
    _safe_set(white, "constant", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))

    base_rgb = _expr(material, "MaterialExpressionMultiply", 460, -120)
    _connect(rims_mask, "", base_rgb, "A")
    _connect(white, "", base_rgb, "B")

    c1 = _const(material, 220, 180, 1.0)
    c0 = _const(material, 220, 300, 0.0)

    flat_normal = _expr(material, "MaterialExpressionConstant3Vector", 460, 300)
    _safe_set(flat_normal, "constant", unreal.LinearColor(0.5, 0.5, 1.0, 1.0))

    rvt_out = _expr(material, "MaterialExpressionRuntimeVirtualTextureOutput", 760, 20)
    result["connect_basecolor"] = _connect(base_rgb, "", rvt_out, ["Base Color", "BaseColor"])
    result["connect_specular"] = _connect(c0, "", rvt_out, "Specular")
    result["connect_roughness"] = _connect(c0, "", rvt_out, "Roughness")
    result["connect_normal"] = _connect(flat_normal, "", rvt_out, "Normal")
    result["connect_mask"] = _connect(c1, "", rvt_out, ["Mask", "mask"])

    MAT_LIB.connect_material_property(base_rgb, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MAT_LIB.connect_material_property(c0, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MAT_LIB.connect_material_property(flat_normal, "", unreal.MaterialProperty.MP_NORMAL)

    MAT_LIB.recompile_material(material)
    MAT_LIB.layout_material_expressions(material)
    result["writer_saved"] = bool(ASSET_LIB.save_loaded_asset(material, False))
    result["writer_num_expressions"] = int(MAT_LIB.get_num_material_expressions(material))


def update_active_landscape_instance(result):
    instance = ASSET_LIB.load_asset(LANDSCAPE_MI_PATH)
    if not instance:
        raise RuntimeError(f"Missing landscape MI: {LANDSCAPE_MI_PATH}")

    scalar_updates = {
        "HeightContrast": 1.0,
    }
    for name, value in scalar_updates.items():
        MAT_LIB.set_material_instance_scalar_parameter_value(instance, name, value)

    MAT_LIB.update_material_instance(instance)
    result["landscape_mi_saved"] = bool(ASSET_LIB.save_loaded_asset(instance, False))
    result["landscape_mi_scalar_values"] = {
        name: float(MAT_LIB.get_material_instance_scalar_parameter_value(instance, name))
        for name in scalar_updates.keys()
    }


def main():
    result = {
        "mode": "restore_working_clear_writer",
        "writer_material": WRITER_MATERIAL_PATH,
        "landscape_mi": LANDSCAPE_MI_PATH,
        "writer_saved": False,
        "landscape_mi_saved": False,
        "writer_num_expressions": 0,
        "landscape_mi_scalar_values": {},
        "connect_basecolor": {},
        "connect_specular": {},
        "connect_roughness": {},
        "connect_normal": {},
        "connect_mask": {},
        "error": "",
    }

    try:
        material = ASSET_LIB.load_asset(WRITER_MATERIAL_PATH)
        if not material:
            raise RuntimeError(f"Missing writer material: {WRITER_MATERIAL_PATH}")

        rebuild_writer_material(material, result)
        update_active_landscape_instance(result)
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
