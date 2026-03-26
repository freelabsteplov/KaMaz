import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
OUTPUT_BASENAME = "inspect_moscowea5_road2_carrier_runtime"
TARGET_LABELS = (
    "Road2",
    "SnowHeightBridgeSurface_Road2",
    "SnowOverlay_Road2",
    "SnowRoadCarrier_Road2",
    "SnowRuntimeTrailBridgeActor",
)
TARGET_PATHS = (
    "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208",
)


def _saved_output_dir():
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    unreal.log(f"[inspect_moscowea5_road2_carrier_runtime] Wrote file: {path}")
    return path


def _object_name(value):
    if value is None:
        return ""
    try:
        return value.get_name()
    except Exception:
        return str(value)


def _object_path(value):
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _safe_property(obj, property_name, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(property_name)
        except Exception:
            return default
    return getattr(obj, property_name, default)


def _vec_to_dict(value):
    if value is None:
        return None
    return {
        "x": float(value.x),
        "y": float(value.y),
        "z": float(value.z),
    }


def _rot_to_dict(value):
    if value is None:
        return None
    return {
        "pitch": float(value.pitch),
        "yaw": float(value.yaw),
        "roll": float(value.roll),
    }


def _color_to_list(value):
    if value is None:
        return None
    return [
        float(value.r),
        float(value.g),
        float(value.b),
        float(value.a),
    ]


def _actor_label(actor):
    if actor is None:
        return ""
    try:
        return actor.get_actor_label()
    except Exception:
        return _object_name(actor)


def _material_scalar(material, param_name):
    try:
        return float(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material, param_name))
    except Exception:
        return None


def _material_vector(material, param_name):
    try:
        value = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(material, param_name)
        return _color_to_list(value)
    except Exception:
        return None


def _receiver_component_summary(actor):
    receiver = actor.get_component_by_class(unreal.SnowReceiverSurfaceComponent)
    if receiver is None:
        return None
    return {
        "component_path": _object_path(receiver),
        "SurfaceFamily": str(_safe_property(receiver, "SurfaceFamily")),
        "ReceiverPriority": int(_safe_property(receiver, "ReceiverPriority", 0)),
        "ReceiverSetTag": str(_safe_property(receiver, "ReceiverSetTag", "")),
        "bParticipatesInPersistentSnowState": bool(
            _safe_property(receiver, "bParticipatesInPersistentSnowState", False)
        ),
    }


def _trail_component_summary(actor):
    if actor is None:
        return None

    trail_component = None
    component_class = unreal.load_class(None, "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent")
    if component_class:
        try:
            trail_component = actor.get_component_by_class(component_class)
        except Exception:
            trail_component = None

    if trail_component is None:
        try:
            for component in list(actor.get_components_by_class(unreal.ActorComponent) or []):
                try:
                    if "SnowRuntimeTrailBridgeComponent" in component.get_class().get_name():
                        trail_component = component
                        break
                except Exception:
                    continue
        except Exception:
            trail_component = None

    if trail_component is None:
        return None

    return {
        "component_path": _object_path(trail_component),
        "bEnableRuntimeTrail": bool(_safe_property(trail_component, "bEnableRuntimeTrail", False)),
        "bUseSourceHeightGate": bool(_safe_property(trail_component, "bUseSourceHeightGate", False)),
        "SourceActiveMaxRelativeZ": float(_safe_property(trail_component, "SourceActiveMaxRelativeZ", 0.0)),
        "MinStampEngagementToWrite": float(_safe_property(trail_component, "MinStampEngagementToWrite", 0.0)),
        "PlowLiftHeightForNoEffect": float(_safe_property(trail_component, "PlowLiftHeightForNoEffect", 0.0)),
        "PersistentPlowLengthCm": float(_safe_property(trail_component, "PersistentPlowLengthCm", 0.0)),
        "PersistentPlowWidthCm": float(_safe_property(trail_component, "PersistentPlowWidthCm", 0.0)),
        "bEnableRuntimeReceiverHeightControl": bool(
            _safe_property(trail_component, "bEnableRuntimeReceiverHeightControl", False)
        ),
        "RuntimeHeightAmplitudeParameterName": str(
            _safe_property(trail_component, "RuntimeHeightAmplitudeParameterName", "")
        ),
        "RuntimeHeightAmplitudeWhenActive": float(
            _safe_property(trail_component, "RuntimeHeightAmplitudeWhenActive", 0.0)
        ),
        "RuntimeHeightAmplitudeWhenInactive": float(
            _safe_property(trail_component, "RuntimeHeightAmplitudeWhenInactive", 0.0)
        ),
        "SourceComponentOverride": _object_path(_safe_property(trail_component, "SourceComponentOverride", None)),
    }


def _mesh_component_summary(component):
    static_mesh = _safe_property(component, "static_mesh", None)
    nanite_settings = _safe_property(static_mesh, "nanite_settings", None)
    materials = []
    try:
        material_count = int(component.get_num_materials())
    except Exception:
        material_count = 0

    for material_index in range(material_count):
        try:
            material = component.get_material(material_index)
        except Exception:
            material = None

        entry = {
            "slot_index": int(material_index),
            "material_name": _object_name(material),
            "material_path": _object_path(material),
        }

        if material_index == 0 and material is not None:
            entry["HeightAmplitude"] = _material_scalar(material, "HeightAmplitude")
            entry["HeightContrast"] = _material_scalar(material, "HeightContrast")
            entry["HeightBias"] = _material_scalar(material, "HeightBias")
            entry["PressedSnowColor"] = _material_vector(material, "PressedSnowColor")
        materials.append(entry)

    return {
        "component_path": _object_path(component),
        "static_mesh_path": _object_path(static_mesh),
        "visible": bool(_safe_property(component, "visible", True)),
        "hidden_in_game": bool(_safe_property(component, "hidden_in_game", False)),
        "render_in_main_pass": bool(_safe_property(component, "render_in_main_pass", True)),
        "render_in_depth_pass": bool(_safe_property(component, "render_in_depth_pass", True)),
        "disallow_nanite": bool(_safe_property(component, "disallow_nanite", False)),
        "mesh_nanite_enabled": bool(_safe_property(nanite_settings, "enabled", False)) if nanite_settings is not None else None,
        "relative_location": _vec_to_dict(_safe_property(component, "relative_location")),
        "relative_rotation": _rot_to_dict(_safe_property(component, "relative_rotation")),
        "relative_scale3d": _vec_to_dict(_safe_property(component, "relative_scale3d")),
        "collision_enabled": str(component.get_collision_enabled()),
        "cast_shadow": bool(_safe_property(component, "cast_shadow", True)),
        "receives_decals": bool(_safe_property(component, "receives_decals", True)),
        "visible_in_ray_tracing": bool(_safe_property(component, "visible_in_ray_tracing", True)),
        "materials": materials,
    }


def _actor_summary(actor):
    if actor is None:
        return None

    root_component = _safe_property(actor, "root_component", None)
    mesh_components = []
    try:
        components = list(actor.get_components_by_class(unreal.MeshComponent) or [])
    except Exception:
        components = []
    for component in components:
        mesh_components.append(_mesh_component_summary(component))

    return {
        "actor_label": _actor_label(actor),
        "actor_name": _object_name(actor),
        "actor_path": _object_path(actor),
        "actor_class": _object_path(actor.get_class()),
        "location": _vec_to_dict(actor.get_actor_location()),
        "rotation": _rot_to_dict(actor.get_actor_rotation()),
        "scale3d": _vec_to_dict(actor.get_actor_scale3d()),
        "root_component": _object_path(root_component),
        "receiver_surface": _receiver_component_summary(actor),
        "trail_component": _trail_component_summary(actor),
        "mesh_components": mesh_components,
    }


def run(output_dir=None):
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(actor_subsystem.get_all_level_actors() or [])

    matches_by_label = {label: [] for label in TARGET_LABELS}
    matches_by_path = {path: [] for path in TARGET_PATHS}
    kamaz_candidates = []
    trail_candidates = []
    road_receiver_actors = []

    for actor in actors:
        actor_label = _actor_label(actor)
        actor_path = _object_path(actor)
        actor_class = _object_path(actor.get_class())

        if actor_label in matches_by_label:
            matches_by_label[actor_label].append(_actor_summary(actor))

        if actor_path in matches_by_path:
            matches_by_path[actor_path].append(_actor_summary(actor))

        if "Kamaz" in actor_label or "Kamaz" in actor_class or "Kamaz" in actor_path:
            kamaz_candidates.append(_actor_summary(actor))

        if "SnowRuntimeTrailBridgeActor" in actor_label or "SnowRuntimeTrailBridgeActor" in actor_class:
            trail_candidates.append(_actor_summary(actor))

        receiver_summary = _receiver_component_summary(actor)
        if receiver_summary is not None:
            road_receiver_actors.append(
                {
                    "actor_label": actor_label,
                    "actor_path": actor_path,
                    "receiver_surface": receiver_summary,
                }
            )

    result = {
        "success": True,
        "map_path": MAP_PATH,
        "actor_count": len(actors),
        "matches_by_label": matches_by_label,
        "matches_by_path": matches_by_path,
        "kamaz_candidate_count": len(kamaz_candidates),
        "kamaz_candidates": kamaz_candidates[:12],
        "trail_candidate_count": len(trail_candidates),
        "trail_candidates": trail_candidates[:12],
        "receiver_actor_count": len(road_receiver_actors),
        "receiver_actors": road_receiver_actors[:80],
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
