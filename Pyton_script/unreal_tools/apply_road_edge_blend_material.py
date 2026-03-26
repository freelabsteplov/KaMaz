import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
SOURCE_PARENT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP"
TARGET_PARENT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP_RoadEdgeBlend"

ROAD_INSTANCE_MAP = {
    "SnowSplineRoad_MVP": {
        "source": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K",
        "target": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_RoadEdgeBlend",
    },
    "SnowSplineRoad_V1_Original_MVP": {
        "source": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_Tile8",
        "target": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_Tile8_RoadEdgeBlend",
    },
    "SnowSplineRoad_V3_Narrow_MVP": {
        "source": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_V3_Narrow_Tile4",
        "target": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_V3_Narrow_Tile4_RoadEdgeBlend",
    },
}

OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "apply_road_edge_blend_material.json",
)


def asset_name(asset_path):
    return asset_path.rsplit("/", 1)[-1]


def asset_dir(asset_path):
    return asset_path.rsplit("/", 1)[0]


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


def ensure_scalar_param(material, parameter_name, default_value, x, y):
    expression = create_expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    expression.set_editor_property("parameter_name", parameter_name)
    expression.set_editor_property("default_value", default_value)
    expression.set_editor_property("group", "RoadEdge")
    expression.set_editor_property("desc", parameter_name)
    return expression


def try_invoke_actor_function(actor, function_name):
    direct = getattr(actor, function_name, None)
    if callable(direct):
        try:
            direct()
            return {"path": "direct", "called": True, "error": ""}
        except Exception as exc:
            return {"path": "direct", "called": False, "error": str(exc)}

    call_method = getattr(actor, "call_method", None)
    if callable(call_method):
        for args in ((function_name,), (function_name, ())):
            try:
                call_method(*args)
                return {"path": "call_method", "called": True, "error": ""}
            except Exception as exc:
                last_error = str(exc)
        return {"path": "call_method", "called": False, "error": last_error}

    call_by_name = getattr(actor, "call_function_by_name_with_arguments", None)
    if callable(call_by_name):
        try:
            call_by_name(function_name)
            return {"path": "call_function_by_name_with_arguments", "called": True, "error": ""}
        except Exception as exc:
            return {"path": "call_function_by_name_with_arguments", "called": False, "error": str(exc)}

    return {"path": "none", "called": False, "error": "No callable editor invocation path exposed."}


def refresh_road_actor(actor):
    refresh_attempts = []

    rerun = try_invoke_actor_function(actor, "rerun_construction_scripts")
    refresh_attempts.append({"function": "rerun_construction_scripts", **rerun})
    if rerun["called"]:
        return refresh_attempts

    rebuild = try_invoke_actor_function(actor, "RebuildSplineMeshes")
    refresh_attempts.append({"function": "RebuildSplineMeshes", **rebuild})
    if rebuild["called"]:
        return refresh_attempts

    post_edit_change = getattr(actor, "post_edit_change", None)
    if callable(post_edit_change):
        try:
            post_edit_change()
            refresh_attempts.append({"function": "post_edit_change", "path": "direct", "called": True, "error": ""})
            return refresh_attempts
        except Exception as exc:
            refresh_attempts.append(
                {"function": "post_edit_change", "path": "direct", "called": False, "error": str(exc)}
            )

    return refresh_attempts


def ensure_edge_blend_patch(material, result):
    scalar_names = [str(name) for name in unreal.MaterialEditingLibrary.get_scalar_parameter_names(material)]
    if "RoadEdgeBlendWidth" in scalar_names:
        result["parent_already_patched"] = True
        return

    base_expr = unreal.MaterialEditingLibrary.get_material_property_input_node(material, unreal.MaterialProperty.MP_BASE_COLOR)
    rough_expr = unreal.MaterialEditingLibrary.get_material_property_input_node(material, unreal.MaterialProperty.MP_ROUGHNESS)
    wpo_expr = unreal.MaterialEditingLibrary.get_material_property_input_node(material, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)

    if not base_expr or not rough_expr or not wpo_expr:
        raise RuntimeError("Missing one of the required root material inputs (BaseColor/Roughness/WPO)")

    base_output = unreal.MaterialEditingLibrary.get_material_property_input_node_output_name(material, unreal.MaterialProperty.MP_BASE_COLOR)
    rough_output = unreal.MaterialEditingLibrary.get_material_property_input_node_output_name(material, unreal.MaterialProperty.MP_ROUGHNESS)
    wpo_output = unreal.MaterialEditingLibrary.get_material_property_input_node_output_name(material, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)

    texcoord = create_expression(material, unreal.MaterialExpressionTextureCoordinate, -3800, -400)
    texcoord.set_editor_property("coordinate_index", 0)

    vmask = create_expression(material, unreal.MaterialExpressionComponentMask, -3600, -400)
    vmask.set_editor_property("r", False)
    vmask.set_editor_property("g", True)
    vmask.set_editor_property("b", False)
    vmask.set_editor_property("a", False)
    connect(texcoord, "", vmask, "Input")

    one_minus_g = create_expression(material, unreal.MaterialExpressionOneMinus, -3400, -220)
    connect(vmask, "", one_minus_g, "Input")

    edge_distance = create_expression(material, unreal.MaterialExpressionMin, -3200, -320)
    connect(vmask, "", edge_distance, "A")
    connect(one_minus_g, "", edge_distance, "B")

    blend_width = ensure_scalar_param(material, "RoadEdgeBlendWidth", 0.06, -3400, -40)
    divide = create_expression(material, unreal.MaterialExpressionDivide, -3000, -320)
    connect(edge_distance, "", divide, "A")
    connect(blend_width, "", divide, "B")

    saturate = create_expression(material, unreal.MaterialExpressionSaturate, -2800, -320)
    connect(divide, "", saturate, "Input")

    blend_power = ensure_scalar_param(material, "RoadEdgeBlendPower", 1.35, -3000, -120)
    center_mask = create_expression(material, unreal.MaterialExpressionPower, -2600, -320)
    connect(saturate, "", center_mask, "Base")
    connect(blend_power, "", center_mask, "Exp")

    edge_mask = create_expression(material, unreal.MaterialExpressionOneMinus, -2400, -320)
    connect(center_mask, "", edge_mask, "Input")

    darken_strength = ensure_scalar_param(material, "RoadEdgeDarkenStrength", 0.28, -2200, -40)
    darken_mask = create_expression(material, unreal.MaterialExpressionMultiply, -2000, -220)
    connect(edge_mask, "", darken_mask, "A")
    connect(darken_strength, "", darken_mask, "B")

    color_factor = create_expression(material, unreal.MaterialExpressionOneMinus, -1800, -220)
    connect(darken_mask, "", color_factor, "Input")

    base_mul = create_expression(material, unreal.MaterialExpressionMultiply, -1200, 0)
    connect(base_expr, base_output, base_mul, "A")
    connect(color_factor, "", base_mul, "B")
    unreal.MaterialEditingLibrary.connect_material_property(
        base_mul,
        "",
        unreal.MaterialProperty.MP_BASE_COLOR,
    )

    rough_push = ensure_scalar_param(material, "RoadEdgeRoughnessPush", 0.08, -2200, 140)
    rough_mask = create_expression(material, unreal.MaterialExpressionMultiply, -2000, 140)
    connect(edge_mask, "", rough_mask, "A")
    connect(rough_push, "", rough_mask, "B")

    rough_add = create_expression(material, unreal.MaterialExpressionAdd, -1600, 140)
    connect(rough_expr, rough_output, rough_add, "A")
    connect(rough_mask, "", rough_add, "B")

    rough_saturate = create_expression(material, unreal.MaterialExpressionSaturate, -1400, 140)
    connect(rough_add, "", rough_saturate, "Input")
    unreal.MaterialEditingLibrary.connect_material_property(
        rough_saturate,
        "",
        unreal.MaterialProperty.MP_ROUGHNESS,
    )

    height_fade = ensure_scalar_param(material, "RoadEdgeHeightFade", 1.0, -2200, 320)
    height_mask = create_expression(material, unreal.MaterialExpressionMultiply, -2000, 320)
    connect(edge_mask, "", height_mask, "A")
    connect(height_fade, "", height_mask, "B")

    wpo_factor = create_expression(material, unreal.MaterialExpressionOneMinus, -1800, 320)
    connect(height_mask, "", wpo_factor, "Input")

    wpo_mul = create_expression(material, unreal.MaterialExpressionMultiply, -1200, 320)
    connect(wpo_expr, wpo_output, wpo_mul, "A")
    connect(wpo_factor, "", wpo_mul, "B")
    unreal.MaterialEditingLibrary.connect_material_property(
        wpo_mul,
        "",
        unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET,
    )

    unreal.MaterialEditingLibrary.layout_material_expressions(material)
    unreal.MaterialEditingLibrary.recompile_material(material)
    result["parent_patched"] = True


def duplicate_asset_fresh(source_path, target_path):
    if unreal.EditorAssetLibrary.does_asset_exist(target_path):
        if not unreal.EditorAssetLibrary.delete_asset(target_path):
            raise RuntimeError(f"Failed to refresh existing duplicate at {target_path}")

    duplicated = unreal.EditorAssetLibrary.duplicate_asset(source_path, target_path)
    if not duplicated:
        raise RuntimeError(f"Failed to duplicate {source_path} -> {target_path}")
    return duplicated


def apply():
    result = {
        "map": MAP_PATH,
        "target_parent": TARGET_PARENT_PATH,
        "parent_created": False,
        "parent_already_patched": False,
        "parent_patched": False,
        "instance_updates": [],
        "actor_updates": [],
        "saved_assets": [],
        "saved_map": False,
        "error": "",
    }

    try:
        # Always rebuild the road-edge parent from the current clean source parent.
        # Otherwise the script can keep reusing an older duplicated parent whose
        # WPO semantics no longer match the active writer material.
        target_parent = duplicate_asset_fresh(SOURCE_PARENT_PATH, TARGET_PARENT_PATH)
        result["parent_created"] = True
        ensure_edge_blend_patch(target_parent, result)
        unreal.EditorAssetLibrary.save_loaded_asset(target_parent)
        result["saved_assets"].append(TARGET_PARENT_PATH)

        duplicated_instances = {}
        for actor_label, instance_info in ROAD_INSTANCE_MAP.items():
            target_instance = duplicate_asset_fresh(instance_info["source"], instance_info["target"])
            unreal.MaterialEditingLibrary.set_material_instance_parent(target_instance, target_parent)
            unreal.MaterialEditingLibrary.update_material_instance(target_instance)
            unreal.EditorAssetLibrary.save_loaded_asset(target_instance)
            duplicated_instances[actor_label] = target_instance
            result["instance_updates"].append(
                {
                    "actor_label": actor_label,
                    "source_instance": instance_info["source"],
                    "target_instance": instance_info["target"],
                    "created": True,
                }
            )
            result["saved_assets"].append(instance_info["target"])

        world = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)

        for actor in actors:
            label = actor.get_actor_label()
            if label not in duplicated_instances:
                continue

            actor.modify()
            actor.set_editor_property("snow_road_material", duplicated_instances[label])
            refresh_attempts = refresh_road_actor(actor)
            result["actor_updates"].append(
                {
                    "actor_label": label,
                    "assigned_material": duplicated_instances[label].get_path_name(),
                    "refresh_attempts": refresh_attempts,
                }
            )

        result["saved_map"] = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as output_file:
        json.dump(result, output_file, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    apply()
