import json
import os

import unreal


DENSE_CARRIER_MESH_PATH = "/Engine/EditorMeshes/PlanarReflectionPlane.PlanarReflectionPlane"
FALLBACK_CARRIER_MESH_PATH = "/Engine/BasicShapes/Plane.Plane"
DEFAULT_SOURCE_MI_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP"
DEFAULT_RVT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP"
DEFAULT_MI_PACKAGE = "/Game/CityPark/SnowSystem/Receivers"
DEFAULT_TRAIL_ACTOR_CLASS_PATH = "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeActor"
DEFAULT_TRAIL_COMPONENT_CLASS_PATH = "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent"
DEFAULT_TRAIL_ACTOR_LABEL = "SnowRuntimeTrailBridgeActor"
DEFAULT_RVT_VOLUME_CLASS_PATH = "/Script/Engine.RuntimeVirtualTextureVolume"
DEFAULT_RVT_VOLUME_LABEL = "SnowRuntimeVirtualTextureVolume"
DEFAULT_CARRIER_MESH_MODE = "dense_plane"
TARGET_MESH_CARRIER_MODE = "target_mesh"
DENSE_PLANE_CARRIER_MODE = "dense_plane"

ROAD_SNOW_CARRIER_HEIGHT_TAG = "RoadSnowCarrierHeight"
ROAD_SNOW_RECEIVER_PRIORITY = 110

DEFAULT_CARRIER_LENGTH_MULTIPLIER = 0.98
DEFAULT_CARRIER_WIDTH_MULTIPLIER = 0.72
DEFAULT_CARRIER_Z_OFFSET_CM = 4.0
DEFAULT_TRAIL_STAMP_SPACING_CM = 15.0
DEFAULT_TRAIL_PLOW_LENGTH_CM = 120.0
DEFAULT_TRAIL_PLOW_WIDTH_CM = 320.0
DEFAULT_TRAIL_SOURCE_ACTIVE_MAX_RELATIVE_Z = -0.5
DEFAULT_TRAIL_RUNTIME_HEIGHT_ACTIVE = -100.0
DEFAULT_TRAIL_RUNTIME_HEIGHT_INACTIVE = 0.0
DEFAULT_HIDE_TARGET_ROAD_IN_GAME = False
DEFAULT_RVT_VOLUME_MARGIN_XY_CM = 300.0
DEFAULT_RVT_VOLUME_MARGIN_Z_CM = 250.0
DEFAULT_RVT_VOLUME_MIN_XY_EXTENT_CM = 512.0
DEFAULT_RVT_VOLUME_MIN_Z_EXTENT_CM = 128.0

DEFAULT_SCALAR_DEFAULTS = {
    "HeightAmplitude": -18.0,
    "HeightContrast": 2.0,
    "HeightBias": 0.0,
    "SnowRoughness": 0.92,
    "PressedRoughness": 0.42,
}

DEFAULT_VECTOR_DEFAULTS = {
    "SnowColor": (0.98, 0.99, 1.0, 1.0),
    "PressedSnowColor": (0.30, 0.31, 0.33, 1.0),
}


def _log(message):
    unreal.log("[road_height_carrier_helper] {0}".format(message))


def saved_output_dir():
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log("Wrote file: {0}".format(path))
    return path


def object_name(value):
    if value is None:
        return ""
    try:
        return value.get_name()
    except Exception:
        return str(value)


def object_path(value):
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def load_asset(asset_path):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        raise RuntimeError("Could not load asset: {0}".format(asset_path))
    return asset


def load_first_existing_asset(asset_paths):
    for asset_path in asset_paths:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if asset is not None:
            return asset, asset_path
    raise RuntimeError("Could not load any candidate asset from: {0}".format(asset_paths))


def ensure_directory(path):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def duplicate_asset_if_missing(source_asset_path, target_asset_path):
    existing = unreal.EditorAssetLibrary.load_asset(target_asset_path)
    if existing is not None:
        return existing, False

    if not unreal.EditorAssetLibrary.duplicate_asset(source_asset_path, target_asset_path):
        raise RuntimeError("Failed to duplicate {0} -> {1}".format(source_asset_path, target_asset_path))

    duplicated = unreal.EditorAssetLibrary.load_asset(target_asset_path)
    if duplicated is None:
        raise RuntimeError("Duplicated asset could not be loaded: {0}".format(target_asset_path))
    return duplicated, True


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


def material_instance_matches_defaults(material_instance, config):
    if material_instance is None:
        return False

    expected_rvt_path = config.get("rvt_path", DEFAULT_RVT_PATH)
    actual_rvt_path = material_rvt(material_instance, "SnowRVT")
    if expected_rvt_path and actual_rvt_path not in (
        "",
        expected_rvt_path,
        expected_rvt_path + "." + os.path.basename(expected_rvt_path),
    ):
        return False

    for name, expected_value in config.get("scalar_defaults", DEFAULT_SCALAR_DEFAULTS).items():
        actual_value = material_scalar(material_instance, name)
        if actual_value is None or abs(float(actual_value) - float(expected_value)) > 0.001:
            return False

    for name, expected_value in config.get("vector_defaults", DEFAULT_VECTOR_DEFAULTS).items():
        actual_value = material_vector(material_instance, name)
        if actual_value is None:
            return False
        for index in range(4):
            if abs(float(actual_value[index]) - float(expected_value[index])) > 0.001:
                return False

    return True


def all_level_actors():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return list(actor_subsystem.get_all_level_actors() or [])


def find_actors_by_label(label):
    if not label:
        return []
    matches = []
    for actor in all_level_actors():
        try:
            if actor.get_actor_label() == label:
                matches.append(actor)
        except Exception:
            continue
    return matches


def find_actor_by_label(label):
    matches = find_actors_by_label(label)
    return matches[0] if matches else None


def find_actor_by_path(actor_path):
    if not actor_path:
        return None
    for actor in all_level_actors():
        try:
            if actor.get_path_name() == actor_path:
                return actor
        except Exception:
            continue
    return None


def selected_mesh_actor():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    selected = list(actor_subsystem.get_selected_level_actors() or [])
    for actor in selected:
        if first_static_mesh_component(actor) is not None:
            return actor
    return None


def first_static_mesh_component(actor):
    if actor is None:
        return None
    return actor.get_component_by_class(unreal.StaticMeshComponent)


def load_map_if_needed(map_path):
    if not map_path:
        return False
    try:
        return bool(unreal.EditorLoadingAndSavingUtils.load_map(map_path))
    except Exception:
        return False


def resolve_target_actor(config):
    target_actor = find_actor_by_path(config.get("target_actor_path", ""))
    if target_actor is not None:
        return target_actor, "path"

    if config.get("allow_selection_fallback", True):
        selected_actor = selected_mesh_actor()
        if selected_actor is not None:
            return selected_actor, "selection"

    target_actor = find_actor_by_label(config.get("target_actor_label", ""))
    if target_actor is not None:
        return target_actor, "label"

    if load_map_if_needed(config.get("target_map_path", "")):
        target_actor = find_actor_by_path(config.get("target_actor_path", ""))
        if target_actor is not None:
            return target_actor, "path_after_load"

        if config.get("allow_selection_fallback", True):
            selected_actor = selected_mesh_actor()
            if selected_actor is not None:
                return selected_actor, "selection_after_load"

        target_actor = find_actor_by_label(config.get("target_actor_label", ""))
        if target_actor is not None:
            return target_actor, "label_after_load"

    raise RuntimeError(
        "Could not resolve target road actor. Tried path='{0}', selection, label='{1}', and loading '{2}'.".format(
            config.get("target_actor_path", ""),
            config.get("target_actor_label", ""),
            config.get("target_map_path", ""),
        )
    )


def destroy_actors_by_label(label, ignored_paths=None):
    ignored_paths = set(ignored_paths or [])
    destroyed_paths = []
    for actor in find_actors_by_label(label):
        actor_path = object_path(actor)
        if actor_path in ignored_paths:
            continue
        try:
            if unreal.EditorLevelLibrary.destroy_actor(actor):
                destroyed_paths.append(actor_path)
        except Exception:
            continue
    return destroyed_paths


def find_or_spawn_carrier_actor(config, location, rotation):
    carrier_label = config["carrier_actor_label"]
    existing_carriers = find_actors_by_label(carrier_label)
    actor = existing_carriers[0] if existing_carriers else None
    creation_mode = "existing"
    removed_paths = []

    if existing_carriers and config.get("recreate_existing_carrier", False):
        removed_paths.extend(destroy_actors_by_label(carrier_label))
        actor = None
        creation_mode = "respawned"

    if actor is None:
        for legacy_label in config.get("legacy_carrier_labels", []):
            actor = find_actor_by_label(legacy_label)
            if actor is not None:
                actor.set_actor_label(config["carrier_actor_label"])
                creation_mode = "reused_{0}".format(legacy_label)
                break

    if actor is None:
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, location, rotation)
        if actor is None:
            raise RuntimeError("Failed to spawn height carrier actor.")
        actor.set_actor_label(config["carrier_actor_label"])
        if creation_mode != "respawned":
            creation_mode = "spawned"

    actor.set_actor_location(location, False, False)
    actor.set_actor_rotation(rotation, False)

    cleanup_labels = list(config.get("legacy_carrier_labels", [])) + list(config.get("cleanup_actor_labels", []))
    removed_labels = []
    ignored_paths = {object_path(actor)}
    duplicate_paths = destroy_actors_by_label(carrier_label, ignored_paths=ignored_paths)
    if duplicate_paths:
        removed_paths.extend(duplicate_paths)
    for label in cleanup_labels:
        if label == carrier_label:
            continue
        destroyed_paths = destroy_actors_by_label(label, ignored_paths=ignored_paths)
        if destroyed_paths:
            removed_labels.append(label)
            removed_paths.extend(destroyed_paths)

    return actor, creation_mode, removed_labels, removed_paths


def get_target_surface_size_cm(actor):
    component = first_static_mesh_component(actor)
    if component is None:
        raise RuntimeError("Target actor has no StaticMeshComponent: {0}".format(object_path(actor)))

    static_mesh = component.get_editor_property("static_mesh")
    if static_mesh is None:
        raise RuntimeError("Target actor has no static mesh assigned: {0}".format(object_path(component)))

    mesh_bounds = static_mesh.get_bounds()
    scale = None
    actor_transform_getter = getattr(actor, "get_actor_transform", None)
    if callable(actor_transform_getter):
        try:
            scale = actor_transform_getter().scale3d
        except Exception:
            scale = None

    if scale is None:
        component_scale_getter = getattr(component, "get_relative_scale3d", None)
        if callable(component_scale_getter):
            try:
                scale = component_scale_getter()
            except Exception:
                scale = None

    if scale is None:
        scale = unreal.Vector(1.0, 1.0, 1.0)

    size_x = abs(float(mesh_bounds.box_extent.x) * 2.0 * float(scale.x))
    size_y = abs(float(mesh_bounds.box_extent.y) * 2.0 * float(scale.y))
    size_z = abs(float(mesh_bounds.box_extent.z) * 2.0 * float(scale.z))

    length_cm = max(size_x, size_y)
    width_cm = min(size_x, size_y)
    return length_cm, width_cm, size_z


def get_mesh_base_size_cm(static_mesh):
    mesh_bounds = static_mesh.get_bounds()
    base_x = max(abs(float(mesh_bounds.box_extent.x) * 2.0), 1.0)
    base_y = max(abs(float(mesh_bounds.box_extent.y) * 2.0), 1.0)
    return base_x, base_y


def resolve_desired_carrier_size_cm(config, target_actor):
    size_source = "scaled_target_bounds"

    override_length_cm = config.get("carrier_length_override_cm")
    override_width_cm = config.get("carrier_width_override_cm")
    if override_length_cm is not None or override_width_cm is not None:
        desired_length_cm = max(float(override_length_cm or 0.0), 100.0)
        desired_width_cm = max(float(override_width_cm or 0.0), 100.0)
        size_source = "explicit_override"
        return desired_length_cm, desired_width_cm, size_source

    length_cm, width_cm, _target_height_cm = get_target_surface_size_cm(target_actor)
    desired_length_cm = max(
        length_cm * float(config.get("carrier_length_multiplier", DEFAULT_CARRIER_LENGTH_MULTIPLIER)),
        100.0,
    )
    desired_width_cm = max(
        width_cm * float(config.get("carrier_width_multiplier", DEFAULT_CARRIER_WIDTH_MULTIPLIER)),
        100.0,
    )
    return desired_length_cm, desired_width_cm, size_source


def offset_location_along_actor_up(actor, offset_cm):
    base_location = actor.get_actor_location()
    offset = float(offset_cm)
    if abs(offset) <= 0.0001:
        return unreal.Vector(float(base_location.x), float(base_location.y), float(base_location.z))

    up_vector_getter = getattr(actor, "get_actor_up_vector", None)
    if callable(up_vector_getter):
        try:
            up_vector = up_vector_getter()
            return unreal.Vector(
                float(base_location.x + (float(up_vector.x) * offset)),
                float(base_location.y + (float(up_vector.y) * offset)),
                float(base_location.z + (float(up_vector.z) * offset)),
            )
        except Exception:
            pass

    return unreal.Vector(float(base_location.x), float(base_location.y), float(base_location.z + offset))


def get_relative_vector(component, getter_name, default_value):
    getter = getattr(component, getter_name, None)
    if callable(getter):
        try:
            return getter()
        except Exception:
            pass
    return default_value


def resolve_carrier_setup(config, target_actor):
    carrier_mode = str(config.get("carrier_mesh_mode", DEFAULT_CARRIER_MESH_MODE) or DEFAULT_CARRIER_MESH_MODE)
    target_component = first_static_mesh_component(target_actor)
    if target_component is None:
        raise RuntimeError("Target actor has no StaticMeshComponent: {0}".format(object_path(target_actor)))

    target_mesh = target_component.get_editor_property("static_mesh")
    if target_mesh is None:
        raise RuntimeError("Target actor has no static mesh assigned: {0}".format(object_path(target_component)))

    length_cm, width_cm, target_height_cm = get_target_surface_size_cm(target_actor)

    if carrier_mode == TARGET_MESH_CARRIER_MODE:
        return {
            "carrier_mode": carrier_mode,
            "carrier_mesh": target_mesh,
            "carrier_location": offset_location_along_actor_up(
                target_actor,
                config.get("carrier_z_offset_cm", DEFAULT_CARRIER_Z_OFFSET_CM),
            ),
            "carrier_rotation": target_actor.get_actor_rotation(),
            "carrier_actor_scale": target_actor.get_actor_scale3d(),
            "carrier_component_relative_location": get_relative_vector(
                target_component,
                "get_relative_location",
                unreal.Vector(0.0, 0.0, 0.0),
            ),
            "carrier_component_relative_rotation": get_relative_vector(
                target_component,
                "get_relative_rotation",
                unreal.Rotator(0.0, 0.0, 0.0),
            ),
            "carrier_component_relative_scale": get_relative_vector(
                target_component,
                "get_relative_scale3d",
                unreal.Vector(1.0, 1.0, 1.0),
            ),
            "carrier_size_source": "target_mesh_transform",
            "desired_length_cm": length_cm,
            "desired_width_cm": width_cm,
            "target_length_cm": length_cm,
            "target_width_cm": width_cm,
            "target_height_cm": target_height_cm,
        }

    dense_mesh, _dense_mesh_path = load_first_existing_asset(
        [DENSE_CARRIER_MESH_PATH, FALLBACK_CARRIER_MESH_PATH]
    )
    desired_length_cm, desired_width_cm, size_source = resolve_desired_carrier_size_cm(config, target_actor)
    base_x_cm, base_y_cm = get_mesh_base_size_cm(dense_mesh)
    actor_scale = unreal.Vector(
        float(desired_length_cm / base_x_cm),
        float(desired_width_cm / base_y_cm),
        1.0,
    )

    return {
        "carrier_mode": carrier_mode,
        "carrier_mesh": dense_mesh,
        "carrier_location": offset_location_along_actor_up(
            target_actor,
            config.get("carrier_z_offset_cm", DEFAULT_CARRIER_Z_OFFSET_CM),
        ),
        "carrier_rotation": target_actor.get_actor_rotation(),
        "carrier_actor_scale": actor_scale,
        "carrier_component_relative_location": unreal.Vector(0.0, 0.0, 0.0),
        "carrier_component_relative_rotation": unreal.Rotator(0.0, 0.0, 0.0),
        "carrier_component_relative_scale": unreal.Vector(1.0, 1.0, 1.0),
        "carrier_size_source": size_source,
        "desired_length_cm": desired_length_cm,
        "desired_width_cm": desired_width_cm,
        "target_length_cm": length_cm,
        "target_width_cm": width_cm,
        "target_height_cm": target_height_cm,
    }


def set_editor_bool(component, property_name, value):
    try:
        component.set_editor_property(property_name, value)
        return True
    except Exception:
        return False


def touch_editor_object(obj, include_post_edit_move=False):
    if obj is None:
        return

    modify = getattr(obj, "modify", None)
    if callable(modify):
        try:
            modify()
        except Exception:
            pass

    post_edit_change = getattr(obj, "post_edit_change", None)
    if callable(post_edit_change):
        try:
            post_edit_change()
        except Exception:
            pass

    if include_post_edit_move:
        post_edit_move = getattr(obj, "post_edit_move", None)
        if callable(post_edit_move):
            try:
                post_edit_move(True)
            except Exception:
                pass

    mark_package_dirty = getattr(obj, "mark_package_dirty", None)
    if callable(mark_package_dirty):
        try:
            mark_package_dirty()
        except Exception:
            pass


def configure_mesh_component(
    component,
    static_mesh,
    material_asset,
    relative_location=None,
    relative_rotation=None,
    relative_scale=None,
):
    component.set_static_mesh(static_mesh)
    material_slot_count = 1
    get_num_materials = getattr(component, "get_num_materials", None)
    if callable(get_num_materials):
        try:
            material_slot_count = max(int(get_num_materials()), 1)
        except Exception:
            material_slot_count = 1

    for slot_index in range(material_slot_count):
        try:
            component.set_material(slot_index, material_asset)
        except Exception:
            continue

    if relative_location is not None:
        try:
            component.set_relative_location(relative_location, False, False)
        except Exception:
            pass

    if relative_rotation is not None:
        try:
            component.set_relative_rotation(relative_rotation, False)
        except Exception:
            pass

    try:
        component.set_relative_scale3d(relative_scale or unreal.Vector(1.0, 1.0, 1.0))
    except Exception:
        pass
    try:
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    except Exception:
        pass
    collision_profile_setter = getattr(component, "set_collision_profile_name", None)
    if callable(collision_profile_setter):
        try:
            collision_profile_setter(unreal.Name("NoCollision"))
        except Exception:
            pass
    else:
        try:
            component.set_editor_property("collision_profile_name", unreal.Name("NoCollision"))
        except Exception:
            pass
    try:
        component.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
    except Exception:
        pass
    component.set_editor_property("mobility", unreal.ComponentMobility.STATIC)
    set_editor_bool(component, "generate_overlap_events", False)
    # Road2 uses the shared road mesh, which is Nanite-backed. The snow carrier relies on
    # masked + WPO rendering, so force the carrier component onto the non-Nanite path.
    set_editor_bool(component, "disallow_nanite", True)

    for property_name in (
        "cast_shadow",
        "cast_dynamic_shadow",
        "cast_far_shadow",
        "cast_contact_shadow",
        "cast_hidden_shadow",
        "affect_distance_field_lighting",
        "affect_dynamic_indirect_lighting",
        "receives_decals",
        "visible_in_ray_tracing",
    ):
        set_editor_bool(component, property_name, False)

    for method_name in ("modify", "mark_render_state_dirty", "post_edit_change"):
        method = getattr(component, method_name, None)
        if callable(method):
            try:
                method()
            except Exception:
                continue
    touch_editor_object(component)


def configure_target_render_proxy(actor, hide_in_game):
    payload = {
        "configured": False,
        "error": "",
        "component_path": "",
        "hidden_in_game": False,
        "collision_enabled": "",
    }

    if actor is None:
        payload["error"] = "Target actor missing."
        return payload

    actor_hidden_setter = getattr(actor, "set_actor_hidden_in_game", None)
    if callable(actor_hidden_setter):
        try:
            actor_hidden_setter(bool(hide_in_game))
        except Exception:
            pass

    component = first_static_mesh_component(actor)
    if component is None:
        payload["error"] = "Target actor has no StaticMeshComponent."
        return payload

    payload["component_path"] = object_path(component)

    try:
        component.set_editor_property("hidden_in_game", bool(hide_in_game))
    except Exception:
        setter = getattr(component, "set_hidden_in_game", None)
        if callable(setter):
            try:
                setter(bool(hide_in_game), True)
            except Exception as exc:
                payload["error"] = str(exc)
                return payload
        else:
            payload["error"] = "Could not set hidden_in_game on target road component."
            return payload

    render_flag_values = {
        "cast_shadow": not bool(hide_in_game),
        "cast_dynamic_shadow": not bool(hide_in_game),
        "cast_far_shadow": not bool(hide_in_game),
        "cast_contact_shadow": not bool(hide_in_game),
        "cast_hidden_shadow": False,
        "receives_decals": not bool(hide_in_game),
        "visible_in_ray_tracing": not bool(hide_in_game),
    }
    for property_name, property_value in render_flag_values.items():
        set_editor_bool(component, property_name, property_value)

    touch_editor_object(component)
    payload["configured"] = True
    try:
        payload["hidden_in_game"] = bool(component.get_editor_property("hidden_in_game"))
    except Exception:
        payload["hidden_in_game"] = bool(hide_in_game)
    try:
        payload["collision_enabled"] = str(component.get_collision_enabled())
    except Exception:
        payload["collision_enabled"] = ""
    payload["render_flags"] = render_flag_values
    return payload


def ensure_receiver_surface(actor, receiver_priority, receiver_set_tag):
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None:
        return False, "BlueprintAutomationPythonBridge missing"

    raw_result = None
    try:
        raw_result = bridge.ensure_snow_receiver_surfaces_on_actors(
            "",
            [actor.get_path_name()],
            unreal.SnowReceiverSurfaceFamily.ROAD,
            int(receiver_priority),
            receiver_set_tag,
            False,
            False,
        )
    except Exception as exc:
        return False, str(exc)

    receiver = actor.get_component_by_class(unreal.SnowReceiverSurfaceComponent)
    if receiver is None:
        return bool(raw_result), "SnowReceiverSurfaceComponent missing after bridge call"

    receiver.set_editor_property("bParticipatesInPersistentSnowState", True)
    receiver.set_editor_property("SurfaceFamily", unreal.SnowReceiverSurfaceFamily.ROAD)
    receiver.set_editor_property("ReceiverPriority", int(receiver_priority))
    receiver.set_editor_property("ReceiverSetTag", receiver_set_tag)
    touch_editor_object(receiver)
    return True, ""


def find_component_by_class_path(actor, class_path, class_name_fragment=""):
    if actor is None:
        return None

    component_class = None
    if class_path:
        try:
            component_class = unreal.load_class(None, class_path)
        except Exception:
            component_class = None

    if component_class is not None:
        try:
            component = actor.get_component_by_class(component_class)
            if component is not None:
                return component
        except Exception:
            pass

    if class_name_fragment:
        try:
            for component in list(actor.get_components_by_class(unreal.ActorComponent) or []):
                try:
                    if class_name_fragment in component.get_class().get_name():
                        return component
                except Exception:
                    continue
        except Exception:
            pass

    return None


def trail_property_value(value):
    if value is None:
        return ""
    if hasattr(value, "get_path_name"):
        try:
            return value.get_path_name()
        except Exception:
            pass
    return str(value)


def runtime_virtual_texture_component(actor):
    if actor is None:
        return None
    try:
        return actor.get_component_by_class(unreal.RuntimeVirtualTextureComponent)
    except Exception:
        return None


def get_runtime_virtual_texture_component_asset(component):
    if component is None:
        return None

    for property_name in ("virtual_texture", "VirtualTexture", "RuntimeVirtualTexture"):
        try:
            value = component.get_editor_property(property_name)
            if value is not None:
                return value
        except Exception:
            continue
    return None


def set_runtime_virtual_texture_component_asset(component, texture_asset):
    if component is None:
        return False, ""

    for property_name in ("virtual_texture", "VirtualTexture", "RuntimeVirtualTexture"):
        try:
            component.set_editor_property(property_name, texture_asset)
            return True, property_name
        except Exception:
            continue
    return False, ""


def actor_bounds(actor):
    if actor is None:
        return None, None
    try:
        return actor.get_actor_bounds(False)
    except Exception:
        return None, None


def actor_inside_runtime_virtual_texture_volume(actor, volume_actor):
    actor_center, _actor_extent = actor_bounds(actor)
    volume_center, volume_extent = actor_bounds(volume_actor)
    if actor_center is None or volume_center is None or volume_extent is None:
        return False

    return (
        abs(float(actor_center.x) - float(volume_center.x)) <= max(float(volume_extent.x), 1.0)
        and abs(float(actor_center.y) - float(volume_center.y)) <= max(float(volume_extent.y), 1.0)
        and abs(float(actor_center.z) - float(volume_center.z)) <= max(float(volume_extent.z), 1.0)
    )


def find_runtime_virtual_texture_volume_by_label(label):
    actor = find_actor_by_label(label)
    if actor is None:
        return None
    try:
        if actor.get_class().get_name() == "RuntimeVirtualTextureVolume":
            return actor
    except Exception:
        return None
    return None


def find_runtime_virtual_texture_volume_for_asset(rvt_asset):
    target_path = object_path(rvt_asset)
    if not target_path:
        return None

    for actor in all_level_actors():
        try:
            if actor.get_class().get_name() != "RuntimeVirtualTextureVolume":
                continue
        except Exception:
            continue

        component = runtime_virtual_texture_component(actor)
        if component is None:
            continue

        if object_path(get_runtime_virtual_texture_component_asset(component)) == target_path:
            return actor
    return None


def ensure_runtime_virtual_texture_volume(config, anchor_actors):
    payload = {
        "enabled": bool(config.get("ensure_runtime_virtual_texture_volume", False)),
        "configured": False,
        "error": "",
        "creation_mode": "disabled",
        "actor_label": config.get("runtime_virtual_texture_volume_label", DEFAULT_RVT_VOLUME_LABEL),
        "actor_path": "",
        "component_path": "",
        "target_rvt_path": "",
        "bound_property_name": "",
        "actor_location": {},
        "actor_scale": {},
        "bounds_center": {},
        "bounds_extent": {},
        "anchors_inside_volume": {},
    }

    if not payload["enabled"]:
        return payload

    target_rvt_path = config.get("runtime_virtual_texture_volume_target_rvt_path", config.get("rvt_path", DEFAULT_RVT_PATH))
    target_rvt = load_asset(target_rvt_path)
    payload["target_rvt_path"] = object_path(target_rvt)

    volume_actor = find_runtime_virtual_texture_volume_by_label(payload["actor_label"])
    creation_mode = "existing_label"

    if volume_actor is None:
        volume_actor = find_runtime_virtual_texture_volume_for_asset(target_rvt)
        creation_mode = "existing_target_asset" if volume_actor is not None else "missing"

    if volume_actor is None and bool(config.get("runtime_virtual_texture_volume_reuse_unbound_volume", False)):
        for actor in all_level_actors():
            try:
                if actor.get_class().get_name() != "RuntimeVirtualTextureVolume":
                    continue
            except Exception:
                continue

            component = runtime_virtual_texture_component(actor)
            if component is None:
                continue

            if get_runtime_virtual_texture_component_asset(component) is None:
                volume_actor = actor
                creation_mode = "reused_unbound"
                break

    if volume_actor is None:
        volume_class = unreal.load_class(
            None,
            config.get("runtime_virtual_texture_volume_class_path", DEFAULT_RVT_VOLUME_CLASS_PATH),
        )
        if volume_class is None:
            payload["error"] = "Could not load RuntimeVirtualTextureVolume class."
            return payload

        volume_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            volume_class,
            unreal.Vector(0.0, 0.0, 0.0),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        if volume_actor is None:
            payload["error"] = "Failed to spawn RuntimeVirtualTextureVolume actor."
            return payload
        creation_mode = "spawned"

    payload["creation_mode"] = creation_mode
    volume_actor.set_actor_label(payload["actor_label"])

    volume_component = runtime_virtual_texture_component(volume_actor)
    if volume_component is None:
        payload["actor_path"] = object_path(volume_actor)
        payload["error"] = "RuntimeVirtualTextureComponent missing on volume actor."
        return payload

    anchor_rows = []
    for actor in anchor_actors or []:
        if actor is None:
            continue
        center, extent = actor_bounds(actor)
        if center is None or extent is None:
            continue
        anchor_rows.append(
            {
                "actor": actor,
                "label": getattr(actor, "get_actor_label", lambda: object_name(actor))(),
                "center": center,
                "extent": extent,
            }
        )

    if not anchor_rows:
        payload["actor_path"] = object_path(volume_actor)
        payload["component_path"] = object_path(volume_component)
        payload["error"] = "No valid anchor actors for RVT volume placement."
        return payload

    ok, bound_property_name = set_runtime_virtual_texture_component_asset(volume_component, target_rvt)
    if not ok:
        payload["actor_path"] = object_path(volume_actor)
        payload["component_path"] = object_path(volume_component)
        payload["error"] = "Could not assign target RVT asset to RuntimeVirtualTextureComponent."
        return payload

    min_x = min(float(row["center"].x) - float(row["extent"].x) for row in anchor_rows)
    max_x = max(float(row["center"].x) + float(row["extent"].x) for row in anchor_rows)
    min_y = min(float(row["center"].y) - float(row["extent"].y) for row in anchor_rows)
    max_y = max(float(row["center"].y) + float(row["extent"].y) for row in anchor_rows)
    min_z = min(float(row["center"].z) - float(row["extent"].z) for row in anchor_rows)
    max_z = max(float(row["center"].z) + float(row["extent"].z) for row in anchor_rows)

    margin_xy = float(config.get("runtime_virtual_texture_volume_margin_xy_cm", DEFAULT_RVT_VOLUME_MARGIN_XY_CM))
    margin_z = float(config.get("runtime_virtual_texture_volume_margin_z_cm", DEFAULT_RVT_VOLUME_MARGIN_Z_CM))
    min_xy_extent = float(config.get("runtime_virtual_texture_volume_min_xy_extent_cm", DEFAULT_RVT_VOLUME_MIN_XY_EXTENT_CM))
    min_z_extent = float(config.get("runtime_virtual_texture_volume_min_z_extent_cm", DEFAULT_RVT_VOLUME_MIN_Z_EXTENT_CM))

    min_x -= margin_xy
    max_x += margin_xy
    min_y -= margin_xy
    max_y += margin_xy
    min_z -= margin_z
    max_z += margin_z

    desired_center = unreal.Vector(
        float((min_x + max_x) * 0.5),
        float((min_y + max_y) * 0.5),
        float((min_z + max_z) * 0.5),
    )
    desired_extent = unreal.Vector(
        float(max(min_xy_extent, (max_x - min_x) * 0.5)),
        float(max(min_xy_extent, (max_y - min_y) * 0.5)),
        float(max(min_z_extent, (max_z - min_z) * 0.5)),
    )
    desired_scale = unreal.Vector(
        float(desired_extent.x * 2.0),
        float(desired_extent.y * 2.0),
        float(desired_extent.z * 2.0),
    )
    desired_actor_location = unreal.Vector(
        float(desired_center.x - desired_extent.x),
        float(desired_center.y - desired_extent.y),
        float(desired_center.z - desired_extent.z),
    )

    touch_editor_object(volume_component)
    touch_editor_object(volume_actor, include_post_edit_move=True)
    volume_actor.set_actor_rotation(unreal.Rotator(0.0, 0.0, 0.0), False)
    volume_actor.set_actor_location(desired_actor_location, False, False)
    volume_actor.set_actor_scale3d(desired_scale)
    touch_editor_object(volume_component)
    touch_editor_object(volume_actor, include_post_edit_move=True)

    actual_center, actual_extent = actor_bounds(volume_actor)
    payload["configured"] = True
    payload["actor_path"] = object_path(volume_actor)
    payload["component_path"] = object_path(volume_component)
    payload["bound_property_name"] = bound_property_name
    payload["actor_location"] = {
        "x": float(volume_actor.get_actor_location().x),
        "y": float(volume_actor.get_actor_location().y),
        "z": float(volume_actor.get_actor_location().z),
    }
    payload["actor_scale"] = {
        "x": float(volume_actor.get_actor_scale3d().x),
        "y": float(volume_actor.get_actor_scale3d().y),
        "z": float(volume_actor.get_actor_scale3d().z),
    }
    if actual_center is not None and actual_extent is not None:
        payload["bounds_center"] = {
            "x": float(actual_center.x),
            "y": float(actual_center.y),
            "z": float(actual_center.z),
        }
        payload["bounds_extent"] = {
            "x": float(actual_extent.x),
            "y": float(actual_extent.y),
            "z": float(actual_extent.z),
        }

    for row in anchor_rows:
        payload["anchors_inside_volume"][row["label"]] = actor_inside_runtime_virtual_texture_volume(
            row["actor"],
            volume_actor,
        )

    return payload


def ensure_runtime_trail_bridge_actor(config, location):
    payload = {
        "enabled": bool(config.get("ensure_runtime_trail_bridge_actor", False)),
        "configured": False,
        "error": "",
        "creation_mode": "disabled",
        "actor_label": config.get("runtime_trail_actor_label", DEFAULT_TRAIL_ACTOR_LABEL),
        "actor_path": "",
        "component_path": "",
        "target_rvt_path": "",
        "values": {},
    }

    if not payload["enabled"]:
        return payload

    actor_label = payload["actor_label"]
    actor = find_actor_by_label(actor_label)
    creation_mode = "existing"

    if actor is None:
        actor_class = unreal.load_class(
            None,
            config.get("runtime_trail_actor_class_path", DEFAULT_TRAIL_ACTOR_CLASS_PATH),
        )
        if actor_class is None:
            payload["error"] = "Could not load runtime trail actor class."
            return payload

        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class, location, unreal.Rotator(0.0, 0.0, 0.0))
        if actor is None:
            payload["error"] = "Failed to spawn runtime trail actor."
            return payload
        actor.set_actor_label(actor_label)
        creation_mode = "spawned"

    actor.set_actor_location(location, False, False)

    trail_component = find_component_by_class_path(
        actor,
        config.get("runtime_trail_component_class_path", DEFAULT_TRAIL_COMPONENT_CLASS_PATH),
        "SnowRuntimeTrailBridgeComponent",
    )
    if trail_component is None:
        payload["creation_mode"] = creation_mode
        payload["actor_path"] = object_path(actor)
        payload["error"] = "SnowRuntimeTrailBridgeComponent missing on runtime trail actor."
        return payload

    target_rvt = None
    target_rvt_path = config.get("runtime_trail_target_rvt_path", DEFAULT_RVT_PATH)
    if target_rvt_path:
        target_rvt = load_asset(target_rvt_path)

    trail_values = {
        "bEnableRuntimeTrail": bool(config.get("runtime_trail_enable_runtime_trail", True)),
        "StampSpacingCm": float(config.get("runtime_trail_stamp_spacing_cm", DEFAULT_TRAIL_STAMP_SPACING_CM)),
        "bUseSourceHeightGate": bool(config.get("runtime_trail_use_source_height_gate", True)),
        "SourceActiveMaxRelativeZ": float(
            config.get("runtime_trail_source_active_max_relative_z", DEFAULT_TRAIL_SOURCE_ACTIVE_MAX_RELATIVE_Z)
        ),
        "bMarkPersistentSnowState": bool(config.get("runtime_trail_mark_persistent_snow_state", True)),
        "PersistentPlowLengthCm": float(config.get("runtime_trail_persistent_plow_length_cm", DEFAULT_TRAIL_PLOW_LENGTH_CM)),
        "PersistentPlowWidthCm": float(config.get("runtime_trail_persistent_plow_width_cm", DEFAULT_TRAIL_PLOW_WIDTH_CM)),
        "PersistentSurfaceFamily": unreal.SnowReceiverSurfaceFamily.ROAD,
        "bEnableRvtVisualStamp": bool(config.get("runtime_trail_enable_rvt_visual_stamp", True)),
        "bEnableRuntimeReceiverHeightControl": bool(
            config.get("runtime_trail_enable_runtime_receiver_height_control", True)
        ),
        "RuntimeHeightAmplitudeWhenActive": float(
            config.get("runtime_trail_runtime_height_amplitude_when_active", DEFAULT_TRAIL_RUNTIME_HEIGHT_ACTIVE)
        ),
        "RuntimeHeightAmplitudeWhenInactive": float(
            config.get("runtime_trail_runtime_height_amplitude_when_inactive", DEFAULT_TRAIL_RUNTIME_HEIGHT_INACTIVE)
        ),
    }

    touch_editor_object(actor, include_post_edit_move=True)
    touch_editor_object(trail_component)

    for property_name, value in trail_values.items():
        trail_component.set_editor_property(property_name, value)

    if target_rvt is not None:
        trail_component.set_editor_property("TargetRvt", target_rvt)

    if config.get("runtime_trail_clear_source_component_override", True):
        try:
            trail_component.set_editor_property("SourceComponentOverride", None)
        except Exception:
            pass

    touch_editor_object(trail_component)
    touch_editor_object(actor, include_post_edit_move=True)

    payload["configured"] = True
    payload["creation_mode"] = creation_mode
    payload["actor_path"] = object_path(actor)
    payload["component_path"] = object_path(trail_component)
    payload["target_rvt_path"] = object_path(target_rvt)
    payload["values"] = {
        "bEnableRuntimeTrail": trail_property_value(trail_component.get_editor_property("bEnableRuntimeTrail")),
        "StampSpacingCm": trail_property_value(trail_component.get_editor_property("StampSpacingCm")),
        "bUseSourceHeightGate": trail_property_value(trail_component.get_editor_property("bUseSourceHeightGate")),
        "SourceActiveMaxRelativeZ": trail_property_value(
            trail_component.get_editor_property("SourceActiveMaxRelativeZ")
        ),
        "bMarkPersistentSnowState": trail_property_value(
            trail_component.get_editor_property("bMarkPersistentSnowState")
        ),
        "PersistentPlowLengthCm": trail_property_value(
            trail_component.get_editor_property("PersistentPlowLengthCm")
        ),
        "PersistentPlowWidthCm": trail_property_value(
            trail_component.get_editor_property("PersistentPlowWidthCm")
        ),
        "PersistentSurfaceFamily": trail_property_value(
            trail_component.get_editor_property("PersistentSurfaceFamily")
        ),
        "bEnableRvtVisualStamp": trail_property_value(
            trail_component.get_editor_property("bEnableRvtVisualStamp")
        ),
        "bEnableRuntimeReceiverHeightControl": trail_property_value(
            trail_component.get_editor_property("bEnableRuntimeReceiverHeightControl")
        ),
        "RuntimeHeightAmplitudeWhenActive": trail_property_value(
            trail_component.get_editor_property("RuntimeHeightAmplitudeWhenActive")
        ),
        "RuntimeHeightAmplitudeWhenInactive": trail_property_value(
            trail_component.get_editor_property("RuntimeHeightAmplitudeWhenInactive")
        ),
        "SourceComponentOverride": trail_property_value(
            trail_component.get_editor_property("SourceComponentOverride")
        ),
    }
    return payload


def apply_material_parameters(material_instance, rvt_asset, scalar_defaults, vector_defaults):
    results = {
        "rvt_set": False,
        "scalar_set": {},
        "vector_set": {},
    }

    try:
        unreal.MaterialEditingLibrary.set_material_instance_runtime_virtual_texture_parameter_value(
            material_instance,
            "SnowRVT",
            rvt_asset,
        )
        actual_rvt_path = material_rvt(material_instance, "SnowRVT")
        target_rvt_path = object_path(rvt_asset)
        results["rvt_set"] = actual_rvt_path in (
            target_rvt_path,
            target_rvt_path + "." + os.path.basename(target_rvt_path),
        )
    except Exception:
        results["rvt_set"] = False

    for name, value in scalar_defaults.items():
        try:
            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                material_instance,
                name,
                float(value),
            )
            actual_value = material_scalar(material_instance, name)
            results["scalar_set"][name] = actual_value is not None and abs(float(actual_value) - float(value)) <= 0.001
        except Exception:
            results["scalar_set"][name] = False

    for name, rgba in vector_defaults.items():
        try:
            color = unreal.LinearColor(float(rgba[0]), float(rgba[1]), float(rgba[2]), float(rgba[3]))
            unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
                material_instance,
                name,
                color,
            )
            actual_value = material_vector(material_instance, name)
            results["vector_set"][name] = actual_value is not None and all(
                abs(float(actual_value[index]) - float(rgba[index])) <= 0.001
                for index in range(4)
            )
        except Exception:
            results["vector_set"][name] = False

    try:
        unreal.MaterialEditingLibrary.update_material_instance(material_instance)
    except Exception:
        pass

    return results


def configure_material_instance(config):
    target_mi_path = config["target_mi_path"]
    target_package = config.get("target_mi_package", DEFAULT_MI_PACKAGE)
    ensure_directory(target_package)

    source_mi_path = config.get("source_mi_path", DEFAULT_SOURCE_MI_PATH)
    source_mi = load_asset(source_mi_path)
    existing_target_mi = unreal.EditorAssetLibrary.load_asset(target_mi_path)

    if existing_target_mi is not None and config.get("force_rebuild_target_mi_from_source", False):
        unreal.EditorAssetLibrary.delete_asset(target_mi_path)
        existing_target_mi = None

    if existing_target_mi is not None and config.get("reuse_existing_material_if_matching", False):
        if material_instance_matches_defaults(existing_target_mi, config):
            return existing_target_mi, {
                "source_mi_path": source_mi_path,
                "target_mi_path": target_mi_path,
                "target_mi_created": False,
                "target_mi_saved": False,
                "target_mi_reused_without_save": True,
                "rvt_path": config.get("rvt_path", DEFAULT_RVT_PATH),
                "parameter_results": {
                    "rvt_set": True,
                    "scalar_set": {},
                    "vector_set": {},
                },
            }

    rvt_asset = load_asset(config.get("rvt_path", DEFAULT_RVT_PATH))

    target_mi, created = duplicate_asset_if_missing(source_mi_path, target_mi_path)

    parameter_results = {
        "rvt_set": False,
        "scalar_set": {},
        "vector_set": {},
    }
    if config.get("apply_material_parameter_overrides", True):
        parameter_results = apply_material_parameters(
            target_mi,
            rvt_asset,
            config.get("scalar_defaults", DEFAULT_SCALAR_DEFAULTS),
            config.get("vector_defaults", DEFAULT_VECTOR_DEFAULTS),
        )

    asset_saved = bool(unreal.EditorAssetLibrary.save_loaded_asset(target_mi, False))

    return target_mi, {
        "source_mi_path": source_mi_path,
        "target_mi_path": target_mi_path,
        "target_mi_created": created,
        "target_mi_saved": asset_saved,
        "target_mi_reused_without_save": False,
        "rvt_path": config.get("rvt_path", DEFAULT_RVT_PATH),
        "parameter_results": parameter_results,
    }


def select_actor(actor):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    try:
        actor_subsystem.set_selected_level_actors([actor])
    except Exception:
        pass


def save_current_level():
    payload = {
        "saved_current_level": False,
        "saved_dirty_packages": False,
        "error": "",
    }
    try:
        payload["saved_current_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
        payload["saved_dirty_packages"] = bool(unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True))
    except Exception as exc:
        payload["error"] = str(exc)
    return payload


def mark_level_dirty():
    try:
        world = unreal.EditorLevelLibrary.get_editor_world()
    except Exception:
        world = None

    if world is not None:
        current_level = getattr(world, "get_current_level", None)
        if callable(current_level):
            try:
                touch_editor_object(current_level())
            except Exception:
                pass
        outermost = getattr(world, "get_outermost", None)
        if callable(outermost):
            try:
                touch_editor_object(outermost())
            except Exception:
                pass


def run(config, output_dir=None):
    output_dir = output_dir or saved_output_dir()

    target_actor, target_resolution = resolve_target_actor(config)
    carrier_material, material_payload = configure_material_instance(config)
    carrier_setup = resolve_carrier_setup(config, target_actor)

    carrier_actor, creation_mode, removed_labels, removed_paths = find_or_spawn_carrier_actor(
        config,
        carrier_setup["carrier_location"],
        carrier_setup["carrier_rotation"],
    )
    component = first_static_mesh_component(carrier_actor)
    if component is None:
        raise RuntimeError("Carrier actor has no StaticMeshComponent: {0}".format(object_path(carrier_actor)))

    touch_editor_object(carrier_actor, include_post_edit_move=True)
    touch_editor_object(component)

    carrier_actor.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
    configure_mesh_component(
        component,
        carrier_setup["carrier_mesh"],
        carrier_material,
        relative_location=carrier_setup["carrier_component_relative_location"],
        relative_rotation=carrier_setup["carrier_component_relative_rotation"],
        relative_scale=carrier_setup["carrier_component_relative_scale"],
    )
    carrier_actor.set_actor_location(carrier_setup["carrier_location"], False, False)
    carrier_actor.set_actor_rotation(carrier_setup["carrier_rotation"], False)
    carrier_actor.set_actor_scale3d(carrier_setup["carrier_actor_scale"])
    target_render_proxy_payload = configure_target_render_proxy(
        target_actor,
        bool(config.get("hide_target_road_in_game", DEFAULT_HIDE_TARGET_ROAD_IN_GAME)),
    )
    receiver_ok, receiver_error = ensure_receiver_surface(
        carrier_actor,
        int(config.get("receiver_priority", ROAD_SNOW_RECEIVER_PRIORITY)),
        config.get("receiver_set_tag", ROAD_SNOW_CARRIER_HEIGHT_TAG),
    )
    runtime_trail_payload = ensure_runtime_trail_bridge_actor(config, carrier_setup["carrier_location"])
    runtime_trail_actor = find_actor_by_label(runtime_trail_payload.get("actor_label", ""))
    rvt_anchor_actors = [carrier_actor, runtime_trail_actor]
    if bool(config.get("runtime_virtual_texture_volume_include_target_actor", True)):
        rvt_anchor_actors.insert(0, target_actor)
    rvt_volume_payload = ensure_runtime_virtual_texture_volume(config, rvt_anchor_actors)
    touch_editor_object(component)
    touch_editor_object(carrier_actor, include_post_edit_move=True)
    mark_level_dirty()

    select_actor(carrier_actor)
    level_save = save_current_level()
    map_saved_ok = bool(level_save.get("saved_current_level")) or bool(level_save.get("saved_dirty_packages"))
    material_saved_ok = bool(material_payload.get("target_mi_saved")) or bool(
        material_payload.get("target_mi_reused_without_save")
    )

    runtime_trail_ok = bool(
        (not runtime_trail_payload.get("enabled"))
        or runtime_trail_payload.get("configured")
    )
    runtime_virtual_texture_volume_ok = bool(
        (not rvt_volume_payload.get("enabled"))
        or rvt_volume_payload.get("configured")
    )

    payload = {
        "success": bool(
            receiver_ok
            and runtime_trail_ok
            and runtime_virtual_texture_volume_ok
            and map_saved_ok
            and material_saved_ok
        ),
        "summary": "Configured road height carrier for {0}: carrier={1} material={2}".format(
            object_name(target_actor),
            object_path(carrier_actor),
            material_payload["target_mi_path"],
        ),
        "target_actor_label": getattr(target_actor, "get_actor_label", lambda: "")(),
        "target_actor_name": object_name(target_actor),
        "target_actor_path": object_path(target_actor),
        "target_resolution": target_resolution,
        "target_height_cm": carrier_setup["target_height_cm"],
        "carrier_actor_label": config["carrier_actor_label"],
        "carrier_actor_name": object_name(carrier_actor),
        "carrier_actor_path": object_path(carrier_actor),
        "carrier_creation_mode": creation_mode,
        "carrier_mode": carrier_setup["carrier_mode"],
        "removed_stale_actor_labels": removed_labels,
        "removed_stale_actor_paths": removed_paths,
        "carrier_component_path": object_path(component),
        "carrier_mesh_path": object_path(carrier_setup["carrier_mesh"]),
        "carrier_location": {
            "x": carrier_setup["carrier_location"].x,
            "y": carrier_setup["carrier_location"].y,
            "z": carrier_setup["carrier_location"].z,
        },
        "carrier_scale": {
            "x": carrier_setup["carrier_actor_scale"].x,
            "y": carrier_setup["carrier_actor_scale"].y,
            "z": carrier_setup["carrier_actor_scale"].z,
        },
        "carrier_actor_scale": {
            "x": carrier_actor.get_actor_scale3d().x,
            "y": carrier_actor.get_actor_scale3d().y,
            "z": carrier_actor.get_actor_scale3d().z,
        },
        "target_length_cm": carrier_setup["target_length_cm"],
        "target_width_cm": carrier_setup["target_width_cm"],
        "carrier_size_source": carrier_setup["carrier_size_source"],
        "desired_length_cm": carrier_setup["desired_length_cm"],
        "desired_width_cm": carrier_setup["desired_width_cm"],
        "receiver_configured": receiver_ok,
        "receiver_error": receiver_error,
        "receiver_priority": int(config.get("receiver_priority", ROAD_SNOW_RECEIVER_PRIORITY)),
        "receiver_set_tag": config.get("receiver_set_tag", ROAD_SNOW_CARRIER_HEIGHT_TAG),
        "target_render_proxy": target_render_proxy_payload,
        "material": material_payload,
        "runtime_trail": runtime_trail_payload,
        "runtime_virtual_texture_volume": rvt_volume_payload,
        "material_saved_ok": material_saved_ok,
        "map_saved_ok": map_saved_ok,
        "save_result": level_save,
    }

    output_path = os.path.join(output_dir, "{0}.json".format(config["output_basename"]))
    write_json(output_path, payload)
    payload["output_path"] = output_path
    return payload
