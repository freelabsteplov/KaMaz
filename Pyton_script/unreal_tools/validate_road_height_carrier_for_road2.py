import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import road_height_carrier_helper as helper
import apply_road_height_carrier_for_road2 as road2_setup


OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "validate_road_height_carrier_for_road2.json",
)


EXPECTED_SCALARS = road2_setup.CONFIG["scalar_defaults"]
EXPECTED_VECTORS = road2_setup.CONFIG["vector_defaults"]


def object_path(value):
    return helper.object_path(value)


def asset_path_matches(value, expected_asset_path):
    path = object_path(value)
    return bool(path) and (path == expected_asset_path or path.startswith(expected_asset_path + "."))


def actor_label(actor):
    if actor is None:
        return ""
    try:
        return actor.get_actor_label()
    except Exception:
        return helper.object_name(actor)


def material_scalar(material_instance, param_name):
    try:
        return float(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material_instance, param_name))
    except Exception:
        return None


def material_vector(material_instance, param_name):
    try:
        value = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(material_instance, param_name)
        return [float(value.r), float(value.g), float(value.b), float(value.a)]
    except Exception:
        return None


def material_rvt(material_instance, param_name):
    getter = getattr(unreal.MaterialEditingLibrary, "get_material_instance_runtime_virtual_texture_parameter_value", None)
    if callable(getter):
        try:
            value = getter(material_instance, param_name)
            return object_path(value)
        except Exception:
            return ""
    return ""


def safe_get_editor_property(obj, property_name, default=None):
    if obj is None:
        return default
    try:
        return obj.get_editor_property(property_name)
    except Exception:
        return default


def nearly_equal(actual, expected, tolerance=0.01):
    return abs(float(actual) - float(expected)) <= float(tolerance)


def validate():
    payload = {
        "success": False,
        "map_path": road2_setup.CONFIG["target_map_path"],
        "target_actor_path": road2_setup.CONFIG["target_actor_path"],
        "carrier_actor_label": road2_setup.CONFIG["carrier_actor_label"],
        "carrier_actor_path": "",
        "carrier_actor_paths": [],
        "target_actor_mesh_path": "",
        "runtime_trail_actor_path": "",
        "carrier_scale": {},
        "checks": {},
        "material_checks": {},
        "receiver_checks": {},
        "runtime_trail_checks": {},
        "rvt_volume_checks": {},
        "target_render_checks": {},
        "errors": [],
    }

    helper.load_map_if_needed(road2_setup.CONFIG["target_map_path"])

    carrier_actors = helper.find_actors_by_label(road2_setup.CONFIG["carrier_actor_label"])
    payload["carrier_actor_paths"] = [object_path(actor) for actor in carrier_actors]
    payload["checks"]["carrier_label_is_unique"] = len(carrier_actors) == 1
    actor = carrier_actors[0] if carrier_actors else None
    if actor is None:
        payload["errors"].append("Carrier actor not found by label.")
        helper.write_json(OUTPUT_PATH, payload)
        return payload

    target_actor = helper.find_actor_by_path(road2_setup.CONFIG["target_actor_path"]) or helper.find_actor_by_label(
        road2_setup.CONFIG["target_actor_label"]
    )
    target_component = helper.first_static_mesh_component(target_actor)

    payload["carrier_actor_path"] = object_path(actor)
    component = helper.first_static_mesh_component(actor)
    receiver = actor.get_component_by_class(unreal.SnowReceiverSurfaceComponent)
    runtime_trail_actor = helper.find_actor_by_label(road2_setup.CONFIG["runtime_trail_actor_label"])
    runtime_trail_component = None
    if runtime_trail_actor is not None:
        runtime_trail_component = helper.find_component_by_class_path(
            runtime_trail_actor,
            road2_setup.CONFIG.get("runtime_trail_component_class_path", helper.DEFAULT_TRAIL_COMPONENT_CLASS_PATH),
            "SnowRuntimeTrailBridgeComponent",
        )
        payload["runtime_trail_actor_path"] = object_path(runtime_trail_actor)

    target_rvt_asset = helper.load_asset(
        road2_setup.CONFIG.get("runtime_virtual_texture_volume_target_rvt_path", road2_setup.CONFIG["rvt_path"])
    )
    rvt_volume_actor = helper.find_runtime_virtual_texture_volume_by_label(
        road2_setup.CONFIG.get("runtime_virtual_texture_volume_label", helper.DEFAULT_RVT_VOLUME_LABEL)
    )
    if rvt_volume_actor is None:
        rvt_volume_actor = helper.find_runtime_virtual_texture_volume_for_asset(target_rvt_asset)

    payload["checks"]["actor_label"] = actor_label(actor) == road2_setup.CONFIG["carrier_actor_label"]
    payload["checks"]["actor_path_present"] = bool(payload["carrier_actor_path"])
    payload["checks"]["component_present"] = component is not None

    if component is not None:
        static_mesh = safe_get_editor_property(component, "static_mesh")
        assigned_material = component.get_material(0)
        relative_scale = safe_get_editor_property(component, "relative_scale3d")
        actor_scale = actor.get_actor_scale3d()
        expected_carrier_mode = road2_setup.CONFIG.get("carrier_mesh_mode", helper.DEFAULT_CARRIER_MESH_MODE)
        payload["checks"]["carrier_mode_matches_config"] = expected_carrier_mode in (
            helper.TARGET_MESH_CARRIER_MODE,
            helper.DENSE_PLANE_CARRIER_MODE,
        )
        payload["checks"]["collision_is_no_collision"] = (
            component.get_collision_enabled() == unreal.CollisionEnabled.NO_COLLISION
        )
        payload["checks"]["casts_shadow_disabled"] = not bool(safe_get_editor_property(component, "cast_shadow", True))
        payload["checks"]["decals_disabled"] = not bool(safe_get_editor_property(component, "receives_decals", True))
        payload["checks"]["ray_tracing_disabled"] = not bool(safe_get_editor_property(component, "visible_in_ray_tracing", True))
        payload["checks"]["material_assigned"] = asset_path_matches(
            assigned_material,
            road2_setup.CONFIG["target_mi_path"],
        )

        if target_component is not None:
            target_mesh = safe_get_editor_property(target_component, "static_mesh")
            payload["target_actor_mesh_path"] = object_path(target_mesh)
            if expected_carrier_mode == helper.TARGET_MESH_CARRIER_MODE:
                payload["checks"]["mesh_matches_target_actor"] = asset_path_matches(
                    static_mesh,
                    payload["target_actor_mesh_path"],
                )

                target_scale = target_actor.get_actor_scale3d()
                payload["checks"]["actor_scale_matches_target"] = (
                    nearly_equal(actor_scale.x, target_scale.x)
                    and nearly_equal(actor_scale.y, target_scale.y)
                    and nearly_equal(actor_scale.z, target_scale.z)
                )
                payload["carrier_scale"]["target_actor_x"] = float(target_scale.x)
                payload["carrier_scale"]["target_actor_y"] = float(target_scale.y)
                payload["carrier_scale"]["target_actor_z"] = float(target_scale.z)
            else:
                dense_mesh_path = helper.object_path(helper.load_first_existing_asset([
                    helper.DENSE_CARRIER_MESH_PATH,
                    helper.FALLBACK_CARRIER_MESH_PATH,
                ])[0])
                carrier_setup = helper.resolve_carrier_setup(road2_setup.CONFIG, target_actor)
                payload["checks"]["mesh_matches_target_actor"] = asset_path_matches(static_mesh, dense_mesh_path)
                expected_scale = carrier_setup["carrier_actor_scale"]
                payload["checks"]["actor_scale_matches_target"] = (
                    nearly_equal(actor_scale.x, expected_scale.x)
                    and nearly_equal(actor_scale.y, expected_scale.y)
                    and nearly_equal(actor_scale.z, expected_scale.z)
                )

            target_location = target_actor.get_actor_location()
            expected_location = helper.offset_location_along_actor_up(
                target_actor,
                road2_setup.CONFIG.get("carrier_z_offset_cm", helper.DEFAULT_CARRIER_Z_OFFSET_CM),
            )
            actual_location = actor.get_actor_location()
            payload["checks"]["actor_location_matches_target_with_offset"] = (
                nearly_equal(actual_location.x, expected_location.x, 0.1)
                and nearly_equal(actual_location.y, expected_location.y, 0.1)
                and nearly_equal(actual_location.z, expected_location.z, 0.1)
            )
            payload["carrier_scale"]["target_location_z"] = float(target_location.z)
            payload["carrier_scale"]["carrier_location_z"] = float(actual_location.z)

        if actor_scale is not None:
            payload["carrier_scale"] = {
                "actor_x": float(actor_scale.x),
                "actor_y": float(actor_scale.y),
                "actor_z": float(actor_scale.z),
                **payload["carrier_scale"],
            }

        if relative_scale is not None:
            payload["carrier_scale"]["relative_x"] = float(relative_scale.x)
            payload["carrier_scale"]["relative_y"] = float(relative_scale.y)
            payload["carrier_scale"]["relative_z"] = float(relative_scale.z)

        if assigned_material is not None:
            payload["material_checks"]["material_path"] = object_path(assigned_material)
            payload["material_checks"]["rvt_path"] = material_rvt(assigned_material, "SnowRVT")
            payload["material_checks"]["rvt_matches"] = payload["material_checks"]["rvt_path"] in (
                "",
                road2_setup.CONFIG["rvt_path"],
                road2_setup.CONFIG["rvt_path"] + "." + os.path.basename(road2_setup.CONFIG["rvt_path"]),
            )
            for param_name, expected_value in EXPECTED_SCALARS.items():
                actual_value = material_scalar(assigned_material, param_name)
                payload["material_checks"][param_name] = {
                    "expected": expected_value,
                    "actual": actual_value,
                    "matches": actual_value is not None and abs(float(actual_value) - float(expected_value)) <= 0.001,
                }
            for param_name, expected_value in EXPECTED_VECTORS.items():
                actual_value = material_vector(assigned_material, param_name)
                payload["material_checks"][param_name] = {
                    "expected": list(expected_value),
                    "actual": actual_value,
                    "matches": actual_value is not None and all(
                        abs(float(actual_value[index]) - float(expected_value[index])) <= 0.001
                        for index in range(4)
                    ),
                }

    payload["receiver_checks"]["receiver_present"] = receiver is not None
    if receiver is not None:
        payload["receiver_checks"]["surface_family_is_road"] = (
            receiver.get_editor_property("SurfaceFamily") == unreal.SnowReceiverSurfaceFamily.ROAD
        )
        payload["receiver_checks"]["receiver_priority_matches"] = (
            int(receiver.get_editor_property("ReceiverPriority")) == int(road2_setup.CONFIG["receiver_priority"])
        )
        payload["receiver_checks"]["receiver_set_tag_matches"] = (
            str(receiver.get_editor_property("ReceiverSetTag")) == road2_setup.CONFIG["receiver_set_tag"]
        )
        payload["receiver_checks"]["persistent_state_enabled"] = bool(
            receiver.get_editor_property("bParticipatesInPersistentSnowState")
        )

    payload["runtime_trail_checks"]["trail_actor_present"] = runtime_trail_actor is not None
    payload["runtime_trail_checks"]["trail_component_present"] = runtime_trail_component is not None
    if runtime_trail_component is not None:
        payload["runtime_trail_checks"]["runtime_trail_enabled"] = bool(
            safe_get_editor_property(runtime_trail_component, "bEnableRuntimeTrail", False)
        )
        payload["runtime_trail_checks"]["runtime_height_control_matches"] = (
            bool(safe_get_editor_property(runtime_trail_component, "bEnableRuntimeReceiverHeightControl", False))
            == bool(road2_setup.CONFIG.get("runtime_trail_enable_runtime_receiver_height_control", True))
        )
        payload["runtime_trail_checks"]["serialized_source_height_gate_disabled"] = (
            bool(safe_get_editor_property(runtime_trail_component, "bUseSourceHeightGate", True)) is False
        )
        payload["runtime_trail_checks"]["serialized_persistent_plow_length_matches"] = nearly_equal(
            safe_get_editor_property(runtime_trail_component, "PersistentPlowLengthCm", 0.0),
            road2_setup.CONFIG["runtime_trail_persistent_plow_length_cm"],
        )
        payload["runtime_trail_checks"]["serialized_persistent_plow_width_matches"] = nearly_equal(
            safe_get_editor_property(runtime_trail_component, "PersistentPlowWidthCm", 0.0),
            road2_setup.CONFIG["runtime_trail_persistent_plow_width_cm"],
        )
        payload["runtime_trail_checks"]["serialized_runtime_height_active_matches"] = nearly_equal(
            safe_get_editor_property(runtime_trail_component, "RuntimeHeightAmplitudeWhenActive", 0.0),
            road2_setup.CONFIG["runtime_trail_runtime_height_amplitude_when_active"],
        )
        payload["runtime_trail_checks"]["serialized_runtime_height_inactive_matches"] = nearly_equal(
            safe_get_editor_property(runtime_trail_component, "RuntimeHeightAmplitudeWhenInactive", 0.0),
            road2_setup.CONFIG["runtime_trail_runtime_height_amplitude_when_inactive"],
        )

    if target_component is not None:
        payload["target_render_checks"]["hidden_in_game_matches"] = (
            bool(safe_get_editor_property(target_component, "hidden_in_game", False))
            == bool(road2_setup.CONFIG.get("hide_target_road_in_game", False))
        )
        payload["target_render_checks"]["collision_preserved"] = (
            target_component.get_collision_enabled() == unreal.CollisionEnabled.QUERY_AND_PHYSICS
        )

    payload["rvt_volume_checks"]["volume_present"] = rvt_volume_actor is not None
    if rvt_volume_actor is not None:
        rvt_component = helper.runtime_virtual_texture_component(rvt_volume_actor)
        bound_asset = helper.get_runtime_virtual_texture_component_asset(rvt_component)
        payload["rvt_volume_checks"]["volume_path"] = object_path(rvt_volume_actor)
        payload["rvt_volume_checks"]["component_present"] = rvt_component is not None
        payload["rvt_volume_checks"]["bound_asset_path"] = object_path(bound_asset)
        payload["rvt_volume_checks"]["bound_asset_matches"] = asset_path_matches(
            bound_asset,
            road2_setup.CONFIG.get("runtime_virtual_texture_volume_target_rvt_path", road2_setup.CONFIG["rvt_path"]),
        )
        payload["rvt_volume_checks"]["carrier_inside_volume"] = helper.actor_inside_runtime_virtual_texture_volume(
            actor,
            rvt_volume_actor,
        )
        payload["rvt_volume_checks"]["target_actor_inside_volume"] = (
            (
                not bool(road2_setup.CONFIG.get("runtime_virtual_texture_volume_include_target_actor", True))
            )
            or (
                target_actor is not None
                and helper.actor_inside_runtime_virtual_texture_volume(target_actor, rvt_volume_actor)
            )
        )

    all_checks = []
    for value in payload["checks"].values():
        all_checks.append(bool(value))

    for value in payload["receiver_checks"].values():
        all_checks.append(bool(value))

    for key, value in payload["runtime_trail_checks"].items():
        if key.startswith("serialized_"):
            continue
        all_checks.append(bool(value))

    for value in payload["rvt_volume_checks"].values():
        if isinstance(value, str):
            continue
        all_checks.append(bool(value))

    for value in payload["target_render_checks"].values():
        all_checks.append(bool(value))

    for key, value in payload["material_checks"].items():
        if isinstance(value, dict) and "matches" in value:
            all_checks.append(bool(value["matches"]))
        elif key == "rvt_matches":
            all_checks.append(bool(value))

    payload["success"] = all(all_checks) if all_checks else False
    helper.write_json(OUTPUT_PATH, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


if __name__ == "__main__":
    validate()
