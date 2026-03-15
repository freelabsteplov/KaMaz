import json
import os

import unreal


OUTPUT_BASENAME = "safe_plow_box_brush_apply"
BRUSH_PACKAGE = "/Game/CityPark/SnowSystem/BrushMaterials"
MASTER_ASSET_NAME = "M_Snow_PlowBrush_BoxSafe"
INSTANCE_ASSET_NAME = "MI_Snow_PlowBrush_BoxSafe_350x50x100"
PLOW_BLUEPRINT_PATH = "/Game/CityPark/SnowSystem/BP_PlowBrush_Component"
MPC_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"

BRUSH_LENGTH_CM = 6000.0
BRUSH_WIDTH_CM = 18000.0
BRUSH_HEIGHT_CM = 3000.0
BRUSH_STRENGTH = 64.0

MASTER_ASSET_PATH = f"{BRUSH_PACKAGE}/{MASTER_ASSET_NAME}"
INSTANCE_ASSET_PATH = f"{BRUSH_PACKAGE}/{INSTANCE_ASSET_NAME}"

ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EDITOR_ASSETS = unreal.EditorAssetLibrary
MATERIAL_LIB = unreal.MaterialEditingLibrary


def _log(message: str) -> None:
    unreal.log(f"[build_safe_plow_box_brush] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[build_safe_plow_box_brush] {message}")


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


def _ensure_directory(path: str) -> None:
    if not EDITOR_ASSETS.does_directory_exist(path):
        EDITOR_ASSETS.make_directory(path)


def _delete_asset_if_exists(asset_path: str) -> bool:
    if not EDITOR_ASSETS.does_asset_exist(asset_path):
        return False
    if not EDITOR_ASSETS.delete_asset(asset_path):
        raise RuntimeError(f"Could not delete existing asset: {asset_path}")
    return True


def _create_material_asset(asset_path: str):
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


def _load_or_create_material_asset(asset_path: str):
    existing = EDITOR_ASSETS.load_asset(asset_path)
    if existing is not None:
        return existing
    return _create_material_asset(asset_path)


def _create_material_instance_asset(asset_path: str):
    package_path, asset_name = asset_path.rsplit("/", 1)
    _ensure_directory(package_path)
    _delete_asset_if_exists(asset_path)
    instance = ASSET_TOOLS.create_asset(
        asset_name,
        package_path,
        unreal.MaterialInstanceConstant,
        unreal.MaterialInstanceConstantFactoryNew(),
    )
    if instance is None:
        raise RuntimeError(f"Failed to create material instance: {asset_path}")
    return instance


def _load_or_create_material_instance_asset(asset_path: str):
    existing = EDITOR_ASSETS.load_asset(asset_path)
    if existing is not None:
        return existing
    return _create_material_instance_asset(asset_path)


def _connect(src_expr, dst_expr, input_name: str, src_output_name: str = "") -> None:
    MATERIAL_LIB.connect_material_expressions(src_expr, src_output_name, dst_expr, input_name)


def _new_expr(material, expr_class, x: int, y: int):
    expr = MATERIAL_LIB.create_material_expression(material, expr_class, x, y)
    if expr is None:
        raise RuntimeError(f"Failed to create expression: {expr_class}")
    return expr


def _new_constant(material, x: int, y: int, value: float):
    expr = _new_expr(material, unreal.MaterialExpressionConstant, x, y)
    expr.set_editor_property("r", float(value))
    return expr


def _new_constant2(material, x: int, y: int, value_x: float, value_y: float):
    expr = _new_expr(material, unreal.MaterialExpressionConstant2Vector, x, y)
    expr.set_editor_property("r", float(value_x))
    expr.set_editor_property("g", float(value_y))
    return expr


def _new_constant4(material, x: int, y: int, value_x: float, value_y: float, value_z: float, value_w: float):
    expr = _new_expr(material, unreal.MaterialExpressionConstant4Vector, x, y)
    expr.set_editor_property("constant", unreal.LinearColor(float(value_x), float(value_y), float(value_z), float(value_w)))
    return expr


def _new_component_mask(material, x: int, y: int, r: bool, g: bool, b: bool, a: bool):
    expr = _new_expr(material, unreal.MaterialExpressionComponentMask, x, y)
    expr.set_editor_property("r", bool(r))
    expr.set_editor_property("g", bool(g))
    expr.set_editor_property("b", bool(b))
    expr.set_editor_property("a", bool(a))
    return expr


def _new_scalar_param(material, x: int, y: int, name: str, value: float, desc: str = ""):
    expr = _new_expr(material, unreal.MaterialExpressionScalarParameter, x, y)
    expr.set_editor_property("parameter_name", name)
    expr.set_editor_property("default_value", float(value))
    if desc:
        expr.set_editor_property("desc", desc)
    return expr


def _new_collection_param(material, x: int, y: int, collection, param_name: str):
    expr = _new_expr(material, unreal.MaterialExpressionCollectionParameter, x, y)
    expr.set_editor_property("collection", collection)
    expr.set_editor_property("parameter_name", param_name)
    return expr


def _new_green_color(material, x: int, y: int):
    expr = _new_expr(material, unreal.MaterialExpressionConstant3Vector, x, y)
    expr.set_editor_property("constant", unreal.LinearColor(0.0, 1.0, 0.0, 1.0))
    return expr


def _resolve_generated_class(blueprint):
    candidate = getattr(blueprint, "generated_class", None)
    if callable(candidate):
        try:
            candidate = candidate()
        except Exception:
            candidate = None

    if candidate is None:
        try:
            candidate = blueprint.get_editor_property("generated_class")
        except Exception:
            candidate = None

    return candidate


def _decode_bridge_compile_result(raw_result):
    payload = {
        "compiled": False,
        "compile_summary": "",
        "compile_json": "",
    }

    if isinstance(raw_result, tuple):
        for item in raw_result:
            if isinstance(item, bool):
                payload["compiled"] = item
            elif isinstance(item, str):
                if not payload["compile_json"]:
                    payload["compile_json"] = item
                else:
                    payload["compile_summary"] = item
        return payload

    if isinstance(raw_result, bool):
        payload["compiled"] = raw_result
        return payload

    payload["compile_summary"] = str(raw_result)
    return payload


def _rebuild_master_material_graph(material, mpc) -> None:
    MATERIAL_LIB.delete_all_material_expressions(material)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property("material_domain", unreal.MaterialDomain.MD_SURFACE)

    brush_uv = _new_collection_param(material, -3400, -500, mpc, "BrushUV")
    bounds_min = _new_collection_param(material, -3400, -100, mpc, "WorldBoundsMin")
    bounds_max = _new_collection_param(material, -3400, 300, mpc, "WorldBoundsMax")
    texcoord = _new_expr(material, unreal.MaterialExpressionTextureCoordinate, -3400, 900)

    axis4_x = _new_constant4(material, -3100, -900, 1.0, 0.0, 0.0, 0.0)
    axis4_y = _new_constant4(material, -3100, -700, 0.0, 1.0, 0.0, 0.0)
    axis2_x = _new_constant2(material, -3100, 1200, 1.0, 0.0)
    axis2_y = _new_constant2(material, -3100, 1400, 0.0, 1.0)

    brush_uv_x = _new_expr(material, unreal.MaterialExpressionDotProduct, -2800, -560)
    _connect(brush_uv, brush_uv_x, "A")
    _connect(axis4_x, brush_uv_x, "B")

    brush_uv_y = _new_expr(material, unreal.MaterialExpressionDotProduct, -2800, -360)
    _connect(brush_uv, brush_uv_y, "A")
    _connect(axis4_y, brush_uv_y, "B")

    brush_uv_rg = _new_expr(material, unreal.MaterialExpressionAppendVector, -2500, -460)
    _connect(brush_uv_x, brush_uv_rg, "A")
    _connect(brush_uv_y, brush_uv_rg, "B")

    bounds_min_x = _new_expr(material, unreal.MaterialExpressionDotProduct, -2800, -120)
    _connect(bounds_min, bounds_min_x, "A")
    _connect(axis4_x, bounds_min_x, "B")

    bounds_min_y = _new_expr(material, unreal.MaterialExpressionDotProduct, -2800, 80)
    _connect(bounds_min, bounds_min_y, "A")
    _connect(axis4_y, bounds_min_y, "B")

    bounds_min_rg = _new_expr(material, unreal.MaterialExpressionAppendVector, -2500, -20)
    _connect(bounds_min_x, bounds_min_rg, "A")
    _connect(bounds_min_y, bounds_min_rg, "B")

    bounds_max_x = _new_expr(material, unreal.MaterialExpressionDotProduct, -2800, 280)
    _connect(bounds_max, bounds_max_x, "A")
    _connect(axis4_x, bounds_max_x, "B")

    bounds_max_y = _new_expr(material, unreal.MaterialExpressionDotProduct, -2800, 480)
    _connect(bounds_max, bounds_max_y, "A")
    _connect(axis4_y, bounds_max_y, "B")

    bounds_max_rg = _new_expr(material, unreal.MaterialExpressionAppendVector, -2500, 380)
    _connect(bounds_max_x, bounds_max_rg, "A")
    _connect(bounds_max_y, bounds_max_rg, "B")

    span_rg = _new_expr(material, unreal.MaterialExpressionSubtract, -2200, 180)
    _connect(bounds_max_rg, span_rg, "A")
    _connect(bounds_min_rg, span_rg, "B")

    length_param = _new_scalar_param(material, -2200, 1100, "BrushLengthCm", BRUSH_LENGTH_CM)
    width_param = _new_scalar_param(material, -2200, 1300, "BrushWidthCm", BRUSH_WIDTH_CM)
    _new_scalar_param(
        material,
        -2200,
        1500,
        "BrushHeightCm",
        BRUSH_HEIGHT_CM,
        "Metadata only: current RT writer uses 2D width/length footprint.",
    )
    strength_param = _new_scalar_param(material, -2200, 1700, "BrushStrength", BRUSH_STRENGTH)

    half_constant = _new_constant(material, -1900, 1200, 0.5)

    half_length = _new_expr(material, unreal.MaterialExpressionMultiply, -1900, 1100)
    _connect(length_param, half_length, "A")
    _connect(half_constant, half_length, "B")

    half_width = _new_expr(material, unreal.MaterialExpressionMultiply, -1900, 1300)
    _connect(width_param, half_width, "A")
    _connect(half_constant, half_width, "B")

    half_size_world = _new_expr(material, unreal.MaterialExpressionAppendVector, -1600, 1200)
    _connect(half_length, half_size_world, "A")
    _connect(half_width, half_size_world, "B")

    half_size_uv = _new_expr(material, unreal.MaterialExpressionDivide, -1300, 1200)
    _connect(half_size_world, half_size_uv, "A")
    _connect(span_rg, half_size_uv, "B")

    delta_uv = _new_expr(material, unreal.MaterialExpressionSubtract, -1900, 820)
    _connect(texcoord, delta_uv, "A")
    _connect(brush_uv_rg, delta_uv, "B")

    abs_delta = _new_expr(material, unreal.MaterialExpressionAbs, -1600, 820)
    _connect(delta_uv, abs_delta, "")

    normalized_delta = _new_expr(material, unreal.MaterialExpressionDivide, -1000, 820)
    _connect(abs_delta, normalized_delta, "A")
    _connect(half_size_uv, normalized_delta, "B")

    normalized_x = _new_expr(material, unreal.MaterialExpressionDotProduct, -700, 740)
    _connect(normalized_delta, normalized_x, "A")
    _connect(axis2_x, normalized_x, "B")

    normalized_y = _new_expr(material, unreal.MaterialExpressionDotProduct, -700, 920)
    _connect(normalized_delta, normalized_y, "A")
    _connect(axis2_y, normalized_y, "B")

    normalized_max = _new_expr(material, unreal.MaterialExpressionMax, -400, 820)
    _connect(normalized_x, normalized_max, "A")
    _connect(normalized_y, normalized_max, "B")

    one_const = _new_constant(material, -100, 740, 1.0)
    zero_const = _new_constant(material, -100, 920, 0.0)

    box_mask_unclamped = _new_expr(material, unreal.MaterialExpressionSubtract, 140, 820)
    _connect(one_const, box_mask_unclamped, "A")
    _connect(normalized_max, box_mask_unclamped, "B")

    box_mask_non_negative = _new_expr(material, unreal.MaterialExpressionMax, 420, 740)
    _connect(box_mask_unclamped, box_mask_non_negative, "A")
    _connect(zero_const, box_mask_non_negative, "B")

    box_mask = _new_expr(material, unreal.MaterialExpressionMin, 700, 740)
    _connect(box_mask_non_negative, box_mask, "A")
    _connect(one_const, box_mask, "B")

    box_mask_strength = _new_expr(material, unreal.MaterialExpressionMultiply, 980, 740)
    _connect(box_mask, box_mask_strength, "A")
    _connect(strength_param, box_mask_strength, "B")

    box_mask_strength_non_negative = _new_expr(material, unreal.MaterialExpressionMax, 1260, 660)
    _connect(box_mask_strength, box_mask_strength_non_negative, "A")
    _connect(zero_const, box_mask_strength_non_negative, "B")

    box_mask_strength_clamped = _new_expr(material, unreal.MaterialExpressionMin, 1540, 660)
    _connect(box_mask_strength_non_negative, box_mask_strength_clamped, "A")
    _connect(one_const, box_mask_strength_clamped, "B")

    green_color = _new_green_color(material, 820, 1140)
    output_color = _new_expr(material, unreal.MaterialExpressionMultiply, 1820, 900)
    _connect(green_color, output_color, "A")
    _connect(box_mask_strength_clamped, output_color, "B")

    MATERIAL_LIB.connect_material_property(output_color, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MATERIAL_LIB.recompile_material(material)
    MATERIAL_LIB.layout_material_expressions(material)
    EDITOR_ASSETS.save_loaded_asset(material, False)
 

def build_master_material(material_asset_path: str = MASTER_ASSET_PATH, mpc_path: str = MPC_PATH):
    mpc = EDITOR_ASSETS.load_asset(mpc_path)
    if mpc is None:
        raise RuntimeError(f"Missing material parameter collection: {mpc_path}")

    material = _load_or_create_material_asset(material_asset_path)
    _rebuild_master_material_graph(material, mpc)
    return material


def build_material_instance(instance_asset_path: str = INSTANCE_ASSET_PATH, master_asset_path: str = MASTER_ASSET_PATH):
    master = EDITOR_ASSETS.load_asset(master_asset_path)
    if master is None:
        raise RuntimeError(f"Missing master material: {master_asset_path}")

    instance = _load_or_create_material_instance_asset(instance_asset_path)
    instance.set_editor_property("parent", master)

    MATERIAL_LIB.set_material_instance_scalar_parameter_value(instance, "BrushLengthCm", BRUSH_LENGTH_CM)
    MATERIAL_LIB.set_material_instance_scalar_parameter_value(instance, "BrushWidthCm", BRUSH_WIDTH_CM)
    MATERIAL_LIB.set_material_instance_scalar_parameter_value(instance, "BrushHeightCm", BRUSH_HEIGHT_CM)
    MATERIAL_LIB.set_material_instance_scalar_parameter_value(instance, "BrushStrength", BRUSH_STRENGTH)

    EDITOR_ASSETS.save_loaded_asset(instance, False)
    return instance


def apply_instance_to_plow_blueprint(instance_asset_path: str = INSTANCE_ASSET_PATH, blueprint_path: str = PLOW_BLUEPRINT_PATH) -> dict:
    blueprint = EDITOR_ASSETS.load_asset(blueprint_path)
    instance = EDITOR_ASSETS.load_asset(instance_asset_path)
    if blueprint is None:
        raise RuntimeError(f"Missing blueprint: {blueprint_path}")
    if instance is None:
        raise RuntimeError(f"Missing brush material instance: {instance_asset_path}")

    result = {
        "blueprint_path": blueprint_path,
        "brush_material_instance_path": instance_asset_path,
        "compiled": False,
        "saved": False,
        "before_brush_material": "",
        "after_brush_material": "",
        "compile_summary": "",
        "compile_json": "",
    }

    generated_class = _resolve_generated_class(blueprint)
    if generated_class is None:
        raise RuntimeError(f"Could not resolve generated class for {blueprint_path}")

    default_object = unreal.get_default_object(generated_class)
    before = default_object.get_editor_property("BrushMaterial")
    result["before_brush_material"] = _object_path(before)

    default_object.set_editor_property("BrushMaterial", instance)
    after = default_object.get_editor_property("BrushMaterial")
    result["after_brush_material"] = _object_path(after)

    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is not None:
        try:
            compile_payload = _decode_bridge_compile_result(bridge.compile_blueprint(blueprint_path))
            result["compiled"] = compile_payload["compiled"]
            result["compile_summary"] = compile_payload["compile_summary"]
            result["compile_json"] = compile_payload["compile_json"]
        except Exception as exc:
            result["compile_summary"] = f"compile_blueprint raised: {exc}"
            _warn(result["compile_summary"])
    else:
        try:
            unreal.KismetEditorUtilities.compile_blueprint(blueprint)
            result["compiled"] = True
            result["compile_summary"] = "Compiled via KismetEditorUtilities.compile_blueprint"
        except Exception as exc:
            result["compile_summary"] = f"Kismet compile failed: {exc}"
            _warn(result["compile_summary"])

    try:
        result["saved"] = bool(EDITOR_ASSETS.save_loaded_asset(blueprint, False))
    except Exception as exc:
        result["saved"] = False
        result["save_error"] = str(exc)

    return result


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    build_result = {
        "master_material_path": MASTER_ASSET_PATH,
        "material_instance_path": INSTANCE_ASSET_PATH,
        "blueprint_path": PLOW_BLUEPRINT_PATH,
        "requested_dimensions_cm": {
            "length": BRUSH_LENGTH_CM,
            "width": BRUSH_WIDTH_CM,
            "height": BRUSH_HEIGHT_CM,
        },
        "notes": [
            "BrushHeightCm is stored as metadata/default parameter.",
            "Current draw-to-render-target writer uses 2D footprint from BrushLengthCm and BrushWidthCm.",
            "No changes were made to Kamaz input or MOZA input assets.",
        ],
    }

    master = build_master_material()
    instance = build_material_instance()
    apply_result = apply_instance_to_plow_blueprint()

    build_result["master_material_object_path"] = _object_path(master)
    build_result["material_instance_object_path"] = _object_path(instance)
    build_result["apply_result"] = apply_result
    build_result["success"] = (
        apply_result["after_brush_material"] == _object_path(instance)
        and apply_result["saved"]
    )
    build_result["summary"] = (
        f"Applied safe plow box brush {INSTANCE_ASSET_PATH} to {PLOW_BLUEPRINT_PATH}; "
        f"before={apply_result['before_brush_material']} after={apply_result['after_brush_material']} "
        f"compiled={apply_result['compiled']} saved={apply_result['saved']}"
    )

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, build_result)
    build_result["output_path"] = output_path
    return build_result


def print_summary() -> str:
    result = run()
    summary = result.get("summary", "")
    output_path = result.get("output_path", "")
    _log(summary)
    _log(f"summary_path={output_path}")
    return summary


if __name__ == "__main__":
    print(run())
