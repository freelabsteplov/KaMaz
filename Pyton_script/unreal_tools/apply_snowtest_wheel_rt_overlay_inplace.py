import json
import os

import unreal


PARENT_MATERIAL_PATHS = [
    "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP",
    "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP_LandscapeRuntimeFix",
]
ACTIVE_MI_PATHS = [
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K",
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_Tile8",
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_V3_Narrow_Tile4",
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_LandscapeRuntimeFix",
]
WHEEL_RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
MPC_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "apply_snowtest_wheel_rt_overlay_inplace.json",
)

PRESSED_SNOW_COLOR = unreal.LinearColor(0.34, 0.34, 0.36, 1.0)
THIN_SNOW_UNDER_COLOR = unreal.LinearColor(0.42, 0.42, 0.44, 1.0)
WHEEL_TRACK_ASPHALT_COLOR = unreal.LinearColor(0.22, 0.22, 0.24, 1.0)
WHEEL_TRACK_SNOW_COLOR = unreal.LinearColor(0.46, 0.46, 0.48, 1.0)

WHEEL_SCALAR_DEFAULTS = {
    "PressedRoughness": 0.50,
    "WheelTrackMaskAmplify": 24.0,
    "WheelTrackContrast": 1.20,
    "WheelTrackStrength": 0.72,
    "WheelTrackSurfaceSnowLumaLow": 0.34,
    "WheelTrackSurfaceSnowLumaHigh": 0.64,
    "WheelTrackAsphaltRoughness": 0.44,
    "WheelTrackSnowRoughness": 0.68,
}

WHEEL_VECTOR_DEFAULTS = {
    "PressedSnowColor": PRESSED_SNOW_COLOR,
    "ThinSnowUnderColor": THIN_SNOW_UNDER_COLOR,
    "WheelTrackAsphaltColor": WHEEL_TRACK_ASPHALT_COLOR,
    "WheelTrackSnowColor": WHEEL_TRACK_SNOW_COLOR,
}


def create_expression(material, expression_class, x, y):
    expression = unreal.MaterialEditingLibrary.create_material_expression(material, expression_class, x, y)
    if expression is None:
        raise RuntimeError(f"Failed to create expression {expression_class}")
    expression.set_editor_property("material_expression_editor_x", x)
    expression.set_editor_property("material_expression_editor_y", y)
    return expression


def connect(source_expr, source_output, target_expr, target_input):
    unreal.MaterialEditingLibrary.connect_material_expressions(
        source_expr,
        source_output if source_output else "",
        target_expr,
        "" if target_input == "Input" else (target_input or ""),
    )


def connect_any(source_expr, source_outputs, target_expr, target_inputs):
    if isinstance(source_outputs, str):
        source_outputs = [source_outputs]
    if isinstance(target_inputs, str):
        target_inputs = [target_inputs]
    for source_output in source_outputs:
        for target_input in target_inputs:
            try:
                connect(source_expr, source_output, target_expr, target_input)
                return True
            except Exception:
                continue
    return False


def scalar_param(material, parameter_name, default_value, x, y):
    expression = create_expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    expression.set_editor_property("parameter_name", parameter_name)
    expression.set_editor_property("default_value", float(default_value))
    return expression


def vector_param(material, parameter_name, default_value, x, y):
    expression = create_expression(material, unreal.MaterialExpressionVectorParameter, x, y)
    expression.set_editor_property("parameter_name", parameter_name)
    expression.set_editor_property("default_value", default_value)
    return expression


def collection_param(material, parameter_name, collection, x, y):
    expression = create_expression(material, unreal.MaterialExpressionCollectionParameter, x, y)
    expression.set_editor_property("collection", collection)
    expression.set_editor_property("parameter_name", parameter_name)
    return expression


def const(material, value, x, y):
    expression = create_expression(material, unreal.MaterialExpressionConstant, x, y)
    expression.set_editor_property("r", float(value))
    return expression


def const2(material, value_x, value_y, x, y):
    expression = create_expression(material, unreal.MaterialExpressionConstant2Vector, x, y)
    expression.set_editor_property("r", float(value_x))
    expression.set_editor_property("g", float(value_y))
    return expression


def const3(material, value_x, value_y, value_z, x, y):
    expression = create_expression(material, unreal.MaterialExpressionConstant3Vector, x, y)
    expression.set_editor_property(
        "constant",
        unreal.LinearColor(float(value_x), float(value_y), float(value_z), 1.0),
    )
    return expression


def const4(material, value_x, value_y, value_z, value_w, x, y):
    expression = create_expression(material, unreal.MaterialExpressionConstant4Vector, x, y)
    expression.set_editor_property(
        "constant",
        unreal.LinearColor(float(value_x), float(value_y), float(value_z), float(value_w)),
    )
    return expression


def patch_parent_material(material, wheel_rt, collection, result_row):
    scalar_names = [str(name) for name in unreal.MaterialEditingLibrary.get_scalar_parameter_names(material)]
    if "WheelTrackStrength" in scalar_names:
        result_row["already_patched"] = True
        return

    base_expr = unreal.MaterialEditingLibrary.get_material_property_input_node(material, unreal.MaterialProperty.MP_BASE_COLOR)
    rough_expr = unreal.MaterialEditingLibrary.get_material_property_input_node(material, unreal.MaterialProperty.MP_ROUGHNESS)
    if not base_expr or not rough_expr:
        raise RuntimeError("Missing BaseColor or Roughness input on parent material")

    base_output = unreal.MaterialEditingLibrary.get_material_property_input_node_output_name(
        material,
        unreal.MaterialProperty.MP_BASE_COLOR,
    )
    rough_output = unreal.MaterialEditingLibrary.get_material_property_input_node_output_name(
        material,
        unreal.MaterialProperty.MP_ROUGHNESS,
    )

    world_pos = create_expression(material, unreal.MaterialExpressionWorldPosition, 1800, -1080)
    axis3_x = const3(material, 1.0, 0.0, 0.0, 1580, -1180)
    axis3_y = const3(material, 0.0, 1.0, 0.0, 1580, -980)
    axis4_x = const4(material, 1.0, 0.0, 0.0, 0.0, 1580, -660)
    axis4_y = const4(material, 0.0, 1.0, 0.0, 0.0, 1580, -460)

    world_x = create_expression(material, unreal.MaterialExpressionDotProduct, 2020, -1140)
    connect(world_pos, "", world_x, "A")
    connect(axis3_x, "", world_x, "B")
    world_y = create_expression(material, unreal.MaterialExpressionDotProduct, 2020, -940)
    connect(world_pos, "", world_y, "A")
    connect(axis3_y, "", world_y, "B")
    world_rg = create_expression(material, unreal.MaterialExpressionAppendVector, 2240, -1040)
    connect(world_x, "", world_rg, "A")
    connect(world_y, "", world_rg, "B")

    bounds_min = collection_param(material, "WorldBoundsMin", collection, 1800, -660)
    bounds_max = collection_param(material, "WorldBoundsMax", collection, 1800, -300)
    bounds_min_x = create_expression(material, unreal.MaterialExpressionDotProduct, 2020, -620)
    connect(bounds_min, "", bounds_min_x, "A")
    connect(axis4_x, "", bounds_min_x, "B")
    bounds_min_y = create_expression(material, unreal.MaterialExpressionDotProduct, 2020, -420)
    connect(bounds_min, "", bounds_min_y, "A")
    connect(axis4_y, "", bounds_min_y, "B")
    bounds_min_rg = create_expression(material, unreal.MaterialExpressionAppendVector, 2240, -520)
    connect(bounds_min_x, "", bounds_min_rg, "A")
    connect(bounds_min_y, "", bounds_min_rg, "B")

    bounds_max_x = create_expression(material, unreal.MaterialExpressionDotProduct, 2020, -260)
    connect(bounds_max, "", bounds_max_x, "A")
    connect(axis4_x, "", bounds_max_x, "B")
    bounds_max_y = create_expression(material, unreal.MaterialExpressionDotProduct, 2020, -60)
    connect(bounds_max, "", bounds_max_y, "A")
    connect(axis4_y, "", bounds_max_y, "B")
    bounds_max_rg = create_expression(material, unreal.MaterialExpressionAppendVector, 2240, -160)
    connect(bounds_max_x, "", bounds_max_rg, "A")
    connect(bounds_max_y, "", bounds_max_rg, "B")

    bounds_span = create_expression(material, unreal.MaterialExpressionSubtract, 2480, -300)
    connect(bounds_max_rg, "", bounds_span, "A")
    connect(bounds_min_rg, "", bounds_span, "B")
    min_span = const2(material, 1.0, 1.0, 2480, -120)
    bounds_span_safe = create_expression(material, unreal.MaterialExpressionMax, 2720, -220)
    connect(bounds_span, "", bounds_span_safe, "A")
    connect(min_span, "", bounds_span_safe, "B")

    world_delta = create_expression(material, unreal.MaterialExpressionSubtract, 2480, -880)
    connect(world_rg, "", world_delta, "A")
    connect(bounds_min_rg, "", world_delta, "B")
    wheel_uv = create_expression(material, unreal.MaterialExpressionDivide, 2720, -760)
    connect(world_delta, "", wheel_uv, "A")
    connect(bounds_span_safe, "", wheel_uv, "B")

    wheel_rt_sample = create_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, 2960, -760)
    wheel_rt_sample.set_editor_property("parameter_name", "WheelRT")
    wheel_rt_sample.set_editor_property("texture", wheel_rt)
    if not connect_any(wheel_uv, [""], wheel_rt_sample, ["Coordinates", "UVs"]):
        raise RuntimeError("Could not connect WheelRT UVs")

    red_axis = const4(material, 1.0, 0.0, 0.0, 0.0, 2960, -560)
    wheel_mask_r = create_expression(material, unreal.MaterialExpressionDotProduct, 3200, -700)
    connect_any(wheel_rt_sample, ["RGBA", "RGB", ""], wheel_mask_r, ["A"])
    connect(red_axis, "", wheel_mask_r, "B")

    mask_amplify = scalar_param(material, "WheelTrackMaskAmplify", WHEEL_SCALAR_DEFAULTS["WheelTrackMaskAmplify"], 3200, -500)
    wheel_mask_scaled = create_expression(material, unreal.MaterialExpressionMultiply, 3440, -620)
    connect(wheel_mask_r, "", wheel_mask_scaled, "A")
    connect(mask_amplify, "", wheel_mask_scaled, "B")

    zero = const(material, 0.0, 3440, -420)
    one = const(material, 1.0, 3440, -240)
    wheel_mask_floor = create_expression(material, unreal.MaterialExpressionMax, 3680, -620)
    connect(wheel_mask_scaled, "", wheel_mask_floor, "A")
    connect(zero, "", wheel_mask_floor, "B")
    wheel_mask_sat = create_expression(material, unreal.MaterialExpressionMin, 3920, -620)
    connect(wheel_mask_floor, "", wheel_mask_sat, "A")
    connect(one, "", wheel_mask_sat, "B")

    wheel_contrast = scalar_param(material, "WheelTrackContrast", WHEEL_SCALAR_DEFAULTS["WheelTrackContrast"], 3920, -420)
    wheel_mask_pow = create_expression(material, unreal.MaterialExpressionPower, 4160, -620)
    connect(wheel_mask_sat, "", wheel_mask_pow, "Base")
    connect(wheel_contrast, "", wheel_mask_pow, "Exp")

    wheel_strength = scalar_param(material, "WheelTrackStrength", WHEEL_SCALAR_DEFAULTS["WheelTrackStrength"], 4160, -420)
    wheel_alpha = create_expression(material, unreal.MaterialExpressionMultiply, 4400, -620)
    connect(wheel_mask_pow, "", wheel_alpha, "A")
    connect(wheel_strength, "", wheel_alpha, "B")

    luma_weights = const3(material, 0.333, 0.333, 0.333, 3200, 120)
    base_luma = create_expression(material, unreal.MaterialExpressionDotProduct, 3440, 20)
    connect(base_expr, base_output, base_luma, "A")
    connect(luma_weights, "", base_luma, "B")

    luma_low = scalar_param(material, "WheelTrackSurfaceSnowLumaLow", WHEEL_SCALAR_DEFAULTS["WheelTrackSurfaceSnowLumaLow"], 3200, 260)
    luma_high = scalar_param(material, "WheelTrackSurfaceSnowLumaHigh", WHEEL_SCALAR_DEFAULTS["WheelTrackSurfaceSnowLumaHigh"], 3200, 420)
    luma_range_raw = create_expression(material, unreal.MaterialExpressionSubtract, 3440, 340)
    connect(luma_high, "", luma_range_raw, "A")
    connect(luma_low, "", luma_range_raw, "B")
    luma_eps = const(material, 0.001, 3440, 500)
    luma_range = create_expression(material, unreal.MaterialExpressionMax, 3680, 340)
    connect(luma_range_raw, "", luma_range, "A")
    connect(luma_eps, "", luma_range, "B")

    luma_offset = create_expression(material, unreal.MaterialExpressionSubtract, 3680, 20)
    connect(base_luma, "", luma_offset, "A")
    connect(luma_low, "", luma_offset, "B")
    surface_snow_raw = create_expression(material, unreal.MaterialExpressionDivide, 3920, 120)
    connect(luma_offset, "", surface_snow_raw, "A")
    connect(luma_range, "", surface_snow_raw, "B")
    surface_snow_floor = create_expression(material, unreal.MaterialExpressionMax, 4160, 120)
    connect(surface_snow_raw, "", surface_snow_floor, "A")
    connect(zero, "", surface_snow_floor, "B")
    surface_snow_alpha = create_expression(material, unreal.MaterialExpressionMin, 4400, 120)
    connect(surface_snow_floor, "", surface_snow_alpha, "A")
    connect(one, "", surface_snow_alpha, "B")

    asphalt_color = vector_param(material, "WheelTrackAsphaltColor", WHEEL_TRACK_ASPHALT_COLOR, 4620, -40)
    snow_color = vector_param(material, "WheelTrackSnowColor", WHEEL_TRACK_SNOW_COLOR, 4620, 180)
    target_base = create_expression(material, unreal.MaterialExpressionLinearInterpolate, 4860, 60)
    connect(asphalt_color, "", target_base, "A")
    connect(snow_color, "", target_base, "B")
    connect(surface_snow_alpha, "", target_base, "Alpha")

    asphalt_roughness = scalar_param(material, "WheelTrackAsphaltRoughness", WHEEL_SCALAR_DEFAULTS["WheelTrackAsphaltRoughness"], 4620, 420)
    snow_roughness = scalar_param(material, "WheelTrackSnowRoughness", WHEEL_SCALAR_DEFAULTS["WheelTrackSnowRoughness"], 4860, 420)
    target_roughness = create_expression(material, unreal.MaterialExpressionLinearInterpolate, 5100, 420)
    connect(asphalt_roughness, "", target_roughness, "A")
    connect(snow_roughness, "", target_roughness, "B")
    connect(surface_snow_alpha, "", target_roughness, "Alpha")

    final_base = create_expression(material, unreal.MaterialExpressionLinearInterpolate, 5340, 60)
    connect(base_expr, base_output, final_base, "A")
    connect(target_base, "", final_base, "B")
    connect(wheel_alpha, "", final_base, "Alpha")

    final_roughness = create_expression(material, unreal.MaterialExpressionLinearInterpolate, 5340, 420)
    connect(rough_expr, rough_output, final_roughness, "A")
    connect(target_roughness, "", final_roughness, "B")
    connect(wheel_alpha, "", final_roughness, "Alpha")

    unreal.MaterialEditingLibrary.connect_material_property(final_base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    unreal.MaterialEditingLibrary.connect_material_property(final_roughness, "", unreal.MaterialProperty.MP_ROUGHNESS)
    unreal.MaterialEditingLibrary.layout_material_expressions(material)
    unreal.MaterialEditingLibrary.recompile_material(material)
    result_row["patched"] = True


def update_instances(result):
    updated_instances = []
    for instance_path in ACTIVE_MI_PATHS:
        instance = unreal.EditorAssetLibrary.load_asset(instance_path)
        if not instance:
            continue

        for parameter_name, value in WHEEL_SCALAR_DEFAULTS.items():
            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instance, parameter_name, value)
        for parameter_name, value in WHEEL_VECTOR_DEFAULTS.items():
            unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(instance, parameter_name, value)

        unreal.MaterialEditingLibrary.update_material_instance(instance)
        unreal.EditorAssetLibrary.save_loaded_asset(instance, False)
        updated_instances.append(
            {
                "path": instance_path,
                "scalar_values": {
                    name: float(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(instance, name))
                    for name in WHEEL_SCALAR_DEFAULTS.keys()
                },
                "vector_values": {
                    name: [
                        float(unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(instance, name).r),
                        float(unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(instance, name).g),
                        float(unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(instance, name).b),
                        float(unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(instance, name).a),
                    ]
                    for name in WHEEL_VECTOR_DEFAULTS.keys()
                },
            }
        )
    result["updated_instances"] = updated_instances


def main():
    result = {
        "wheel_rt_path": WHEEL_RT_PATH,
        "mpc_path": MPC_PATH,
        "parents": [],
        "updated_instances": [],
        "error": "",
    }

    try:
        wheel_rt = unreal.EditorAssetLibrary.load_asset(WHEEL_RT_PATH)
        if not wheel_rt:
            raise RuntimeError(f"Missing Wheel RT asset: {WHEEL_RT_PATH}")
        collection = unreal.EditorAssetLibrary.load_asset(MPC_PATH)
        if not collection:
            raise RuntimeError(f"Missing MPC asset: {MPC_PATH}")

        for material_path in PARENT_MATERIAL_PATHS:
            material = unreal.EditorAssetLibrary.load_asset(material_path)
            if not material:
                raise RuntimeError(f"Missing material: {material_path}")

            row = {
                "path": material_path,
                "patched": False,
                "already_patched": False,
                "saved": False,
                "error": "",
            }
            try:
                patch_parent_material(material, wheel_rt, collection, row)
                row["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(material, False))
            except Exception as exc:
                row["error"] = str(exc)
            result["parents"].append(row)

        update_instances(result)
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
