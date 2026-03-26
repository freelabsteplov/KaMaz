import json
import os

import unreal


PARENT_MATERIAL_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP"
ROAD2_MI_PATH = "/Game/CityPark/SnowSystem/Receivers/MI_SnowRoadCarrier_Road2_Dense"
ROAD2_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
CARRIER_LABEL = "SnowHeightBridgeSurface_Road2"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_road2_parent_receiver_state.json",
)


def _safe_output_name(material, material_property):
    try:
        value = unreal.MaterialEditingLibrary.get_material_property_input_node_output_name(material, material_property)
        return str(value or "")
    except Exception:
        return ""


def _safe_node_name(material, material_property):
    try:
        node = unreal.MaterialEditingLibrary.get_material_property_input_node(material, material_property)
        if not node:
            return ""
        return node.get_class().get_name()
    except Exception:
        return ""


def _find_actor_by_path(actor_path):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_subsystem.get_all_level_actors() or []:
        try:
            if actor.get_path_name() == actor_path:
                return actor
        except Exception:
            continue
    return None


def _find_actor_by_label(label):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_subsystem.get_all_level_actors() or []:
        try:
            if actor.get_actor_label() == label:
                return actor
        except Exception:
            continue
    return None


def _component_payload(component):
    if not component:
        return {}
    static_mesh = None
    try:
        static_mesh = component.get_editor_property("static_mesh")
    except Exception:
        static_mesh = None
    payload = {
        "component_path": component.get_path_name(),
        "static_mesh": static_mesh.get_path_name() if static_mesh else "",
    }
    for field in (
        "visible",
        "hidden_in_game",
        "render_in_main_pass",
        "render_in_depth_pass",
        "disallow_nanite",
        "cast_shadow",
        "cast_dynamic_shadow",
        "receives_decals",
        "use_as_occluder",
    ):
        try:
            payload[field] = bool(component.get_editor_property(field))
        except Exception:
            payload[field] = None
    try:
        payload["relative_location"] = dict(component.get_relative_location())
    except Exception:
        pass
    try:
        payload["relative_rotation"] = dict(component.get_relative_rotation())
    except Exception:
        pass
    try:
        payload["relative_scale"] = dict(component.get_relative_scale3d())
    except Exception:
        pass
    return payload


def _vector_to_dict(vector_like):
    try:
        return {
            "x": float(vector_like.x),
            "y": float(vector_like.y),
            "z": float(vector_like.z),
        }
    except Exception:
        return {}


def _rot_to_dict(rot_like):
    try:
        return {
            "pitch": float(rot_like.pitch),
            "yaw": float(rot_like.yaw),
            "roll": float(rot_like.roll),
        }
    except Exception:
        return {}


def main():
    result = {
        "success": False,
        "parent_material": {},
        "road2_mi": {},
        "road2_actor": {},
        "carrier_actor": {},
        "error": "",
    }

    try:
        parent_material = unreal.EditorAssetLibrary.load_asset(PARENT_MATERIAL_PATH)
        if not parent_material:
            raise RuntimeError(f"Failed to load parent material: {PARENT_MATERIAL_PATH}")

        road2_mi = unreal.EditorAssetLibrary.load_asset(ROAD2_MI_PATH)
        if not road2_mi:
            raise RuntimeError(f"Failed to load Road2 MI: {ROAD2_MI_PATH}")

        road2_actor = _find_actor_by_path(ROAD2_ACTOR_PATH)
        carrier_actor = _find_actor_by_label(CARRIER_LABEL)

        result["parent_material"] = {
            "path": parent_material.get_path_name(),
            "blend_mode": str(parent_material.get_editor_property("blend_mode")),
            "two_sided": bool(parent_material.get_editor_property("two_sided")),
            "opacity_mask_clip_value": float(parent_material.get_editor_property("opacity_mask_clip_value")),
            "base_color_node": _safe_node_name(parent_material, unreal.MaterialProperty.MP_BASE_COLOR),
            "roughness_node": _safe_node_name(parent_material, unreal.MaterialProperty.MP_ROUGHNESS),
            "wpo_node": _safe_node_name(parent_material, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET),
            "opacity_mask_node": _safe_node_name(parent_material, unreal.MaterialProperty.MP_OPACITY_MASK),
            "base_color_output": _safe_output_name(parent_material, unreal.MaterialProperty.MP_BASE_COLOR),
            "roughness_output": _safe_output_name(parent_material, unreal.MaterialProperty.MP_ROUGHNESS),
            "wpo_output": _safe_output_name(parent_material, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET),
            "opacity_mask_output": _safe_output_name(parent_material, unreal.MaterialProperty.MP_OPACITY_MASK),
        }

        result["road2_mi"] = {
            "path": road2_mi.get_path_name(),
            "parent": road2_mi.get_editor_property("parent").get_path_name(),
            "scalar_params": {},
            "vector_params": {},
        }
        for name in (
            "HeightAmplitude",
            "RoadSnowVisualWhitenStrength",
            "RoadSnowRecoveredBehavior",
            "ThinSnowMinVisualOpacity",
            "VisualClearMaskStrength",
        ):
            try:
                result["road2_mi"]["scalar_params"][name] = float(
                    unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(road2_mi, name)
                )
            except Exception:
                result["road2_mi"]["scalar_params"][name] = None
        for name in (
            "SnowColor",
            "PressedSnowColor",
            "RoadSnowVisualColor",
            "RoadSnowRecoveredPressedColor",
        ):
            try:
                value = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(road2_mi, name)
                result["road2_mi"]["vector_params"][name] = [float(value.r), float(value.g), float(value.b), float(value.a)]
            except Exception:
                result["road2_mi"]["vector_params"][name] = None

        if road2_actor:
            road2_component = road2_actor.get_component_by_class(unreal.StaticMeshComponent)
            result["road2_actor"] = {
                "path": road2_actor.get_path_name(),
                "label": road2_actor.get_actor_label(),
                "location": _vector_to_dict(road2_actor.get_actor_location()),
                "rotation": _rot_to_dict(road2_actor.get_actor_rotation()),
                "scale": _vector_to_dict(road2_actor.get_actor_scale3d()),
                "component": _component_payload(road2_component),
            }

        if carrier_actor:
            carrier_component = carrier_actor.get_component_by_class(unreal.StaticMeshComponent)
            result["carrier_actor"] = {
                "path": carrier_actor.get_path_name(),
                "label": carrier_actor.get_actor_label(),
                "location": _vector_to_dict(carrier_actor.get_actor_location()),
                "rotation": _rot_to_dict(carrier_actor.get_actor_rotation()),
                "scale": _vector_to_dict(carrier_actor.get_actor_scale3d()),
                "component": _component_payload(carrier_component),
            }

        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
