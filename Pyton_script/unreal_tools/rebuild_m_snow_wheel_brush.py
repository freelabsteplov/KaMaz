import json
import os

import unreal


MATERIAL_PATH = "/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_WheelBrush"
MPC_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "rebuild_m_snow_wheel_brush.json",
)

ASSET_LIB = unreal.EditorAssetLibrary
ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MAT_LIB = unreal.MaterialEditingLibrary


def _write_json(payload):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _safe_set(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception:
        return False


def _expr(material, cls, x, y):
    expression_class = getattr(unreal, cls, None)
    if expression_class is None:
        raise RuntimeError(f"Missing Unreal class {cls}")
    expression = MAT_LIB.create_material_expression(material, expression_class, x, y)
    if expression is None:
        raise RuntimeError(f"Could not create {cls}")
    _safe_set(expression, "material_expression_editor_x", x)
    _safe_set(expression, "material_expression_editor_y", y)
    return expression


def _connect(source, output_name, target, input_name):
    MAT_LIB.connect_material_expressions(
        source,
        output_name or "",
        target,
        "" if input_name == "Input" else (input_name or ""),
    )


def _scalar(material, x, y, name, value):
    expression = _expr(material, "MaterialExpressionScalarParameter", x, y)
    _safe_set(expression, "parameter_name", name)
    _safe_set(expression, "default_value", float(value))
    return expression


def _vector(material, x, y, name, color):
    expression = _expr(material, "MaterialExpressionVectorParameter", x, y)
    _safe_set(expression, "parameter_name", name)
    _safe_set(
        expression,
        "default_value",
        unreal.LinearColor(float(color[0]), float(color[1]), float(color[2]), float(color[3])),
    )
    return expression


def _const(material, x, y, value):
    expression = _expr(material, "MaterialExpressionConstant", x, y)
    _safe_set(expression, "r", float(value))
    return expression


def _const2(material, x, y, value_x, value_y):
    expression = _expr(material, "MaterialExpressionConstant2Vector", x, y)
    _safe_set(expression, "r", float(value_x))
    _safe_set(expression, "g", float(value_y))
    return expression


def _const3(material, x, y, value_x, value_y, value_z):
    expression = _expr(material, "MaterialExpressionConstant3Vector", x, y)
    _safe_set(
        expression,
        "constant",
        unreal.LinearColor(float(value_x), float(value_y), float(value_z), 1.0),
    )
    return expression


def _const4(material, x, y, value_x, value_y, value_z, value_w):
    expression = _expr(material, "MaterialExpressionConstant4Vector", x, y)
    _safe_set(
        expression,
        "constant",
        unreal.LinearColor(float(value_x), float(value_y), float(value_z), float(value_w)),
    )
    return expression


def _collection(material, x, y, collection, name):
    expression = _expr(material, "MaterialExpressionCollectionParameter", x, y)
    _safe_set(expression, "collection", collection)
    _safe_set(expression, "parameter_name", name)
    return expression


def _load_or_create_material(asset_path):
    asset = ASSET_LIB.load_asset(asset_path)
    created = False
    if asset is None:
        package_path, asset_name = asset_path.rsplit("/", 1)
        asset = ASSET_TOOLS.create_asset(
            asset_name,
            package_path,
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )
        if asset is None:
            raise RuntimeError(f"Failed to create material {asset_path}")
        created = True
    return asset, created


def _find_collection_color(collection, parameter_name):
    try:
        vector_parameters = list(collection.get_editor_property("vector_parameters") or [])
    except Exception:
        vector_parameters = []
    for parameter in vector_parameters:
        try:
            if str(parameter.get_editor_property("parameter_name")) == parameter_name:
                return parameter.get_editor_property("default_value")
        except Exception:
            continue
    return None


def rebuild():
    result = {
        "material_path": MATERIAL_PATH,
        "created": False,
        "saved": False,
        "num_expressions": 0,
        "material_type": "",
        "defaults": {},
        "error": "",
    }

    try:
        material, created = _load_or_create_material(MATERIAL_PATH)
        collection = ASSET_LIB.load_asset(MPC_PATH)
        if collection is None:
            raise RuntimeError(f"Missing collection {MPC_PATH}")

        if _find_collection_color(collection, "WorldBoundsMin") is None or _find_collection_color(collection, "WorldBoundsMax") is None:
            raise RuntimeError("MPC_SnowSystem is missing WorldBoundsMin/WorldBoundsMax")

        MAT_LIB.delete_all_material_expressions(material)
        _safe_set(material, "material_domain", unreal.MaterialDomain.MD_SURFACE)
        _safe_set(material, "blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
        _safe_set(material, "shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
        _safe_set(material, "two_sided", False)

        texcoord = _expr(material, "MaterialExpressionTextureCoordinate", -2600, 180)
        brush_uv = _collection(material, -2600, -1100, collection, "BrushUV")
        bounds_min_x = _expr(material, "MaterialExpressionDotProduct", -2080, -760)
        bounds_min = _collection(material, -2600, -720, collection, "WorldBoundsMin")
        _connect(bounds_min, "", bounds_min_x, "A")
        axis4_x = _const4(material, -2340, -1260, 1.0, 0.0, 0.0, 0.0)
        axis4_y = _const4(material, -2340, -1060, 0.0, 1.0, 0.0, 0.0)
        _connect(axis4_x, "", bounds_min_x, "B")
        bounds_min_y = _expr(material, "MaterialExpressionDotProduct", -2080, -560)
        _connect(bounds_min, "", bounds_min_y, "A")
        _connect(axis4_y, "", bounds_min_y, "B")
        bounds_min_rg = _expr(material, "MaterialExpressionAppendVector", -1840, -660)
        _connect(bounds_min_x, "", bounds_min_rg, "A")
        _connect(bounds_min_y, "", bounds_min_rg, "B")

        bounds_max = _collection(material, -2600, -360, collection, "WorldBoundsMax")
        bounds_max_x = _expr(material, "MaterialExpressionDotProduct", -2080, -380)
        _connect(bounds_max, "", bounds_max_x, "A")
        _connect(axis4_x, "", bounds_max_x, "B")
        bounds_max_y = _expr(material, "MaterialExpressionDotProduct", -2080, -180)
        _connect(bounds_max, "", bounds_max_y, "A")
        _connect(axis4_y, "", bounds_max_y, "B")
        bounds_max_rg = _expr(material, "MaterialExpressionAppendVector", -1840, -280)
        _connect(bounds_max_x, "", bounds_max_rg, "A")
        _connect(bounds_max_y, "", bounds_max_rg, "B")

        span_rg = _expr(material, "MaterialExpressionSubtract", -1600, -420)
        _connect(bounds_max_rg, "", span_rg, "A")
        _connect(bounds_min_rg, "", span_rg, "B")
        min_span = _const2(material, -1600, -220, 1.0, 1.0)
        safe_span = _expr(material, "MaterialExpressionMax", -1360, -360)
        _connect(span_rg, "", safe_span, "A")
        _connect(min_span, "", safe_span, "B")

        brush_uv_x = _expr(material, "MaterialExpressionDotProduct", -2080, -1160)
        _connect(brush_uv, "", brush_uv_x, "A")
        _connect(axis4_x, "", brush_uv_x, "B")
        brush_uv_y = _expr(material, "MaterialExpressionDotProduct", -2080, -960)
        _connect(brush_uv, "", brush_uv_y, "A")
        _connect(axis4_y, "", brush_uv_y, "B")
        brush_uv_rg = _expr(material, "MaterialExpressionAppendVector", -1840, -1060)
        _connect(brush_uv_x, "", brush_uv_rg, "A")
        _connect(brush_uv_y, "", brush_uv_rg, "B")

        brush_length_cm = _scalar(material, -1600, 120, "BrushLengthCm", 220.0)
        brush_width_cm = _scalar(material, -1600, 300, "BrushWidthCm", 70.0)
        _scalar(material, -1600, 480, "BrushHeightCm", 10.0)
        half = _const(material, -1360, 220, 0.5)
        half_length_cm = _expr(material, "MaterialExpressionMultiply", -1120, 120)
        _connect(brush_length_cm, "", half_length_cm, "A")
        _connect(half, "", half_length_cm, "B")
        half_width_cm = _expr(material, "MaterialExpressionMultiply", -1120, 300)
        _connect(brush_width_cm, "", half_width_cm, "A")
        _connect(half, "", half_width_cm, "B")
        half_size_world = _expr(material, "MaterialExpressionAppendVector", -880, 220)
        _connect(half_length_cm, "", half_size_world, "A")
        _connect(half_width_cm, "", half_size_world, "B")
        half_size_uv = _expr(material, "MaterialExpressionDivide", -640, 220)
        _connect(half_size_world, "", half_size_uv, "A")
        _connect(safe_span, "", half_size_uv, "B")

        delta_uv = _expr(material, "MaterialExpressionSubtract", -1120, -140)
        _connect(texcoord, "", delta_uv, "A")
        _connect(brush_uv_rg, "", delta_uv, "B")
        delta_normalized = _expr(material, "MaterialExpressionDivide", -880, -40)
        _connect(delta_uv, "", delta_normalized, "A")
        _connect(half_size_uv, "", delta_normalized, "B")

        delta_length_sq = _expr(material, "MaterialExpressionDotProduct", -640, -40)
        _connect(delta_normalized, "", delta_length_sq, "A")
        _connect(delta_normalized, "", delta_length_sq, "B")

        one = _const(material, -640, 140, 1.0)
        mask_unclamped = _expr(material, "MaterialExpressionSubtract", -400, -40)
        _connect(one, "", mask_unclamped, "A")
        _connect(delta_length_sq, "", mask_unclamped, "B")

        zero = _const(material, -400, 140, 0.0)
        mask_floor = _expr(material, "MaterialExpressionMax", -160, -100)
        _connect(mask_unclamped, "", mask_floor, "A")
        _connect(zero, "", mask_floor, "B")
        mask_saturate = _expr(material, "MaterialExpressionMin", 80, -100)
        _connect(mask_floor, "", mask_saturate, "A")
        _connect(one, "", mask_saturate, "B")

        falloff = _scalar(material, -160, 140, "WheelTrackFalloff", 1.6)
        mask_pow = _expr(material, "MaterialExpressionPower", 320, -100)
        _connect(mask_saturate, "", mask_pow, "Base")
        _connect(falloff, "", mask_pow, "Exp")

        strength = _scalar(material, 320, 140, "BrushStrength", 1.0)
        brush_alpha = _expr(material, "MaterialExpressionMultiply", 560, -20)
        _connect(mask_pow, "", brush_alpha, "A")
        _connect(strength, "", brush_alpha, "B")

        red = _const3(material, 560, -220, 1.0, 0.0, 0.0)
        brush_rgb = _expr(material, "MaterialExpressionMultiply", 800, -120)
        _connect(red, "", brush_rgb, "A")
        _connect(brush_alpha, "", brush_rgb, "B")

        MAT_LIB.connect_material_property(brush_rgb, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        MAT_LIB.connect_material_property(brush_rgb, "", unreal.MaterialProperty.MP_BASE_COLOR)

        MAT_LIB.layout_material_expressions(material)
        MAT_LIB.recompile_material(material)
        result["saved"] = bool(ASSET_LIB.save_loaded_asset(material, False))
        result["created"] = created
        result["num_expressions"] = int(MAT_LIB.get_num_material_expressions(material))
        result["material_type"] = material.get_class().get_name()
        result["defaults"] = {
            "BrushLengthCm": 220.0,
            "BrushWidthCm": 70.0,
            "BrushHeightCm": 10.0,
            "WheelTrackFalloff": 1.6,
            "BrushStrength": 1.0,
        }
    except Exception as exc:
        result["error"] = str(exc)

    _write_json(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    rebuild()
