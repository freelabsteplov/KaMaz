import json
import os

import unreal


PARENT_MATERIAL_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP"
ROAD_MI_PATHS = [
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K",
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_Tile8",
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_V3_Narrow_Tile4",
]

ROAD_EDGE_DEFAULTS = {
    "RoadEdgeBlendEnabled": 1.0,
    "RoadEdgeBlendWidth": 0.12,
    "RoadEdgeBlendPower": 1.15,
    "RoadEdgeDarkenStrength": 0.32,
    "RoadEdgeRoughnessPush": 0.10,
    "RoadEdgeHeightFade": 1.0,
}

OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "apply_road_edge_blend_inplace.json",
)


def create_expression(material, expression_class, x, y):
    expression = unreal.MaterialEditingLibrary.create_material_expression(material, expression_class, x, y)
    expression.set_editor_property("material_expression_editor_x", x)
    expression.set_editor_property("material_expression_editor_y", y)
    return expression


def connect(from_expr, from_output_name, to_expr, to_input_name):
    unreal.MaterialEditingLibrary.connect_material_expressions(
        from_expr,
        from_output_name if from_output_name else "",
        to_expr,
        to_input_name,
    )


def scalar_param(material, parameter_name, default_value, x, y):
    expression = create_expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    expression.set_editor_property("parameter_name", parameter_name)
    expression.set_editor_property("default_value", default_value)
    expression.set_editor_property("group", "RoadEdge")
    expression.set_editor_property("desc", parameter_name)
    return expression


def patch_parent_material(material, result):
    scalar_names = [str(name) for name in unreal.MaterialEditingLibrary.get_scalar_parameter_names(material)]
    if "RoadEdgeBlendEnabled" in scalar_names:
        result["parent_already_patched"] = True
        return

    base_expr = unreal.MaterialEditingLibrary.get_material_property_input_node(material, unreal.MaterialProperty.MP_BASE_COLOR)
    rough_expr = unreal.MaterialEditingLibrary.get_material_property_input_node(material, unreal.MaterialProperty.MP_ROUGHNESS)
    wpo_expr = unreal.MaterialEditingLibrary.get_material_property_input_node(material, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)

    if not base_expr or not rough_expr or not wpo_expr:
        raise RuntimeError("Missing BaseColor/Roughness/WPO root inputs on parent material")

    base_output = unreal.MaterialEditingLibrary.get_material_property_input_node_output_name(
        material, unreal.MaterialProperty.MP_BASE_COLOR
    )
    rough_output = unreal.MaterialEditingLibrary.get_material_property_input_node_output_name(
        material, unreal.MaterialProperty.MP_ROUGHNESS
    )
    wpo_output = unreal.MaterialEditingLibrary.get_material_property_input_node_output_name(
        material, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET
    )

    texcoord = create_expression(material, unreal.MaterialExpressionTextureCoordinate, -4000, -420)
    texcoord.set_editor_property("coordinate_index", 0)

    vmask = create_expression(material, unreal.MaterialExpressionComponentMask, -3800, -420)
    vmask.set_editor_property("r", False)
    vmask.set_editor_property("g", True)
    vmask.set_editor_property("b", False)
    vmask.set_editor_property("a", False)
    connect(texcoord, "", vmask, "Input")

    one_minus_g = create_expression(material, unreal.MaterialExpressionOneMinus, -3600, -260)
    connect(vmask, "", one_minus_g, "Input")

    edge_distance = create_expression(material, unreal.MaterialExpressionMin, -3400, -340)
    connect(vmask, "", edge_distance, "A")
    connect(one_minus_g, "", edge_distance, "B")

    blend_width = scalar_param(material, "RoadEdgeBlendWidth", 0.12, -3600, -80)
    divide = create_expression(material, unreal.MaterialExpressionDivide, -3200, -340)
    connect(edge_distance, "", divide, "A")
    connect(blend_width, "", divide, "B")

    saturate = create_expression(material, unreal.MaterialExpressionSaturate, -3000, -340)
    connect(divide, "", saturate, "Input")

    blend_power = scalar_param(material, "RoadEdgeBlendPower", 1.15, -3200, -160)
    center_mask = create_expression(material, unreal.MaterialExpressionPower, -2800, -340)
    connect(saturate, "", center_mask, "Base")
    connect(blend_power, "", center_mask, "Exp")

    edge_mask = create_expression(material, unreal.MaterialExpressionOneMinus, -2600, -340)
    connect(center_mask, "", edge_mask, "Input")

    blend_enabled = scalar_param(material, "RoadEdgeBlendEnabled", 0.0, -2600, -120)
    edge_influence = create_expression(material, unreal.MaterialExpressionMultiply, -2400, -260)
    connect(edge_mask, "", edge_influence, "A")
    connect(blend_enabled, "", edge_influence, "B")

    darken_strength = scalar_param(material, "RoadEdgeDarkenStrength", 0.32, -2200, -80)
    darken_mask = create_expression(material, unreal.MaterialExpressionMultiply, -2000, -260)
    connect(edge_influence, "", darken_mask, "A")
    connect(darken_strength, "", darken_mask, "B")

    color_factor = create_expression(material, unreal.MaterialExpressionOneMinus, -1800, -260)
    connect(darken_mask, "", color_factor, "Input")

    base_mul = create_expression(material, unreal.MaterialExpressionMultiply, -1300, 0)
    connect(base_expr, base_output, base_mul, "A")
    connect(color_factor, "", base_mul, "B")
    unreal.MaterialEditingLibrary.connect_material_property(base_mul, "", unreal.MaterialProperty.MP_BASE_COLOR)

    rough_push = scalar_param(material, "RoadEdgeRoughnessPush", 0.10, -2200, 120)
    rough_mask = create_expression(material, unreal.MaterialExpressionMultiply, -2000, 120)
    connect(edge_influence, "", rough_mask, "A")
    connect(rough_push, "", rough_mask, "B")

    rough_add = create_expression(material, unreal.MaterialExpressionAdd, -1600, 120)
    connect(rough_expr, rough_output, rough_add, "A")
    connect(rough_mask, "", rough_add, "B")

    rough_saturate = create_expression(material, unreal.MaterialExpressionSaturate, -1400, 120)
    connect(rough_add, "", rough_saturate, "Input")
    unreal.MaterialEditingLibrary.connect_material_property(rough_saturate, "", unreal.MaterialProperty.MP_ROUGHNESS)

    height_fade = scalar_param(material, "RoadEdgeHeightFade", 1.0, -2200, 320)
    height_mask = create_expression(material, unreal.MaterialExpressionMultiply, -2000, 320)
    connect(edge_influence, "", height_mask, "A")
    connect(height_fade, "", height_mask, "B")

    wpo_factor = create_expression(material, unreal.MaterialExpressionOneMinus, -1800, 320)
    connect(height_mask, "", wpo_factor, "Input")

    wpo_mul = create_expression(material, unreal.MaterialExpressionMultiply, -1300, 320)
    connect(wpo_expr, wpo_output, wpo_mul, "A")
    connect(wpo_factor, "", wpo_mul, "B")
    unreal.MaterialEditingLibrary.connect_material_property(
        wpo_mul, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET
    )

    unreal.MaterialEditingLibrary.layout_material_expressions(material)
    unreal.MaterialEditingLibrary.recompile_material(material)
    result["parent_patched"] = True


def main():
    result = {
        "parent_material": PARENT_MATERIAL_PATH,
        "parent_already_patched": False,
        "parent_patched": False,
        "saved_assets": [],
        "updated_instances": [],
        "error": "",
    }

    try:
        parent = unreal.EditorAssetLibrary.load_asset(PARENT_MATERIAL_PATH)
        if not parent:
            raise RuntimeError(f"Failed to load parent material: {PARENT_MATERIAL_PATH}")

        patch_parent_material(parent, result)
        unreal.EditorAssetLibrary.save_loaded_asset(parent)
        result["saved_assets"].append(PARENT_MATERIAL_PATH)

        for mi_path in ROAD_MI_PATHS:
            instance = unreal.EditorAssetLibrary.load_asset(mi_path)
            if not instance:
                raise RuntimeError(f"Failed to load material instance: {mi_path}")

            updated_values = {}
            for name, value in ROAD_EDGE_DEFAULTS.items():
                unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instance, name, value)
                updated_values[name] = float(
                    unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(instance, name)
                )

            unreal.MaterialEditingLibrary.update_material_instance(instance)
            unreal.EditorAssetLibrary.save_loaded_asset(instance)

            result["updated_instances"].append(
                {
                    "material_instance": mi_path,
                    "scalar_values": updated_values,
                }
            )
            result["saved_assets"].append(mi_path)
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as output_file:
        json.dump(result, output_file, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
