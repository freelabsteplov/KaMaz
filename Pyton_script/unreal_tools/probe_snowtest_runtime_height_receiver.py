import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
KAMAZ_ACTOR_LABEL = "Kamaz_SnowTest"
TRAIL_ACTOR_LABEL = "SnowRuntimeTrailBridgeActor"
HEIGHT_RECEIVER_TOKEN = "SnowReceiver_RVT_Height_MVP"
HEIGHT_PARAM_NAME = "HeightAmplitude"
SCALAR_PARAM_NAMES = (
    "VisualClearMaskStrength",
    "DepthMaskBoost",
    "ThinSnowMinVisualOpacity",
)
VECTOR_PARAM_NAMES = (
    "PressedSnowColor",
    "ThinSnowUnderColor",
)
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "probe_snowtest_runtime_height_receiver.json",
)


def _path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _name(obj):
    if not obj:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _label(actor):
    if not actor:
        return ""
    try:
        return actor.get_actor_label()
    except Exception:
        return _name(actor)


def _safe_get(obj, property_name, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(property_name)
        except Exception:
            return default
    return getattr(obj, property_name, default)


def _safe_set(obj, property_name, value):
    setter = getattr(obj, "set_editor_property", None)
    if callable(setter):
        try:
            setter(property_name, value)
            return True
        except Exception:
            return False
    try:
        setattr(obj, property_name, value)
        return True
    except Exception:
        return False


def _find_actor_by_label(label):
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_sub.get_all_level_actors() or []):
        if _label(actor) == label:
            return actor
    return None


def _ensure_map_loaded():
    kamaz_actor = _find_actor_by_label(KAMAZ_ACTOR_LABEL)
    trail_actor = _find_actor_by_label(TRAIL_ACTOR_LABEL)
    if kamaz_actor and trail_actor:
        return kamaz_actor, trail_actor

    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    return _find_actor_by_label(KAMAZ_ACTOR_LABEL), _find_actor_by_label(TRAIL_ACTOR_LABEL)


def _find_trail_component(trail_actor):
    if not trail_actor:
        return None
    component_class = unreal.load_class(None, "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent")
    if component_class:
        component = trail_actor.get_component_by_class(component_class)
        if component:
            return component
    for component in list(trail_actor.get_components_by_class(unreal.ActorComponent) or []):
        try:
            if "SnowRuntimeTrailBridgeComponent" in component.get_class().get_name():
                return component
        except Exception:
            continue
    return None


def _find_plow_component(kamaz_actor):
    preferred = None
    fallback = None
    for component in list(kamaz_actor.get_components_by_class(unreal.ActorComponent) or []):
        try:
            if not isinstance(component, unreal.SceneComponent):
                continue
        except Exception:
            continue
        component_name = _name(component)
        class_name = component.get_class().get_name()
        if "BP_PlowBrush_Component" in component_name or "BP_PlowBrush_Component" in class_name:
            preferred = component
            break
        if ("PlowBrush" in component_name or "BP_PlowBrush" in component_name) and fallback is None:
            fallback = component
    return preferred or fallback


def _resolve_material_parent(material):
    current = material
    visited = set()
    while current:
        current_path = _path(current)
        if current_path in visited:
            break
        visited.add(current_path)
        yield current
        current = _safe_get(current, "parent", None)


def _is_height_receiver_material(material):
    for candidate in _resolve_material_parent(material):
        if HEIGHT_RECEIVER_TOKEN in _path(candidate) or HEIGHT_RECEIVER_TOKEN in _name(candidate):
            return True
    return False


def _material_height_value(material):
    getter = getattr(material, "get_scalar_parameter_value", None)
    if callable(getter):
        try:
            return float(getter(HEIGHT_PARAM_NAME))
        except Exception:
            pass

    try:
        return float(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material, HEIGHT_PARAM_NAME))
    except Exception:
        return None


def _material_scalar_value(material, param_name):
    getter = getattr(material, "get_scalar_parameter_value", None)
    if callable(getter):
        try:
            return float(getter(param_name))
        except Exception:
            pass

    try:
        return float(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material, param_name))
    except Exception:
        return None


def _material_vector_value(material, param_name):
    getter = getattr(material, "get_vector_parameter_value", None)
    if callable(getter):
        try:
            value = getter(param_name)
            return [float(value.r), float(value.g), float(value.b), float(value.a)]
        except Exception:
            pass

    try:
        value = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(material, param_name)
        return [float(value.r), float(value.g), float(value.b), float(value.a)]
    except Exception:
        return None


def _scan_height_receivers():
    payload = []
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mesh_class = unreal.MeshComponent

    for actor in list(actor_sub.get_all_level_actors() or []):
        for component in list(actor.get_components_by_class(mesh_class) or []):
            material_count = 0
            try:
                material_count = int(component.get_num_materials())
            except Exception:
                continue

            for material_index in range(material_count):
                material = component.get_material(material_index)
                if not material or not _is_height_receiver_material(material):
                    continue

                payload.append(
                    {
                        "actor_label": _label(actor),
                        "actor_path": _path(actor),
                        "component_name": _name(component),
                        "component_path": _path(component),
                        "material_index": int(material_index),
                        "material_class": material.get_class().get_name(),
                        "material_path": _path(material),
                        "material_parent_path": _path(_safe_get(material, "parent", None)),
                        "height_amplitude": _material_height_value(material),
                        "scalar_values": {
                            name: _material_scalar_value(material, name)
                            for name in SCALAR_PARAM_NAMES
                        },
                        "vector_values": {
                            name: _material_vector_value(material, name)
                            for name in VECTOR_PARAM_NAMES
                        },
                    }
                )

    return payload


def _write_output(payload):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main():
    payload = {
        "map": MAP_PATH,
        "trail_component_path": "",
        "plow_source_path": "",
        "height_param_name": HEIGHT_PARAM_NAME,
        "target_runtime_height": None,
        "before": [],
        "after": [],
        "stamp_written": False,
        "error": "",
    }

    trail_component = None
    plow_source = None
    plow_owner = None
    original_props = {}

    try:
        kamaz_actor, trail_actor = _ensure_map_loaded()
        if not kamaz_actor or not trail_actor:
            raise RuntimeError("Missing Kamaz_SnowTest or SnowRuntimeTrailBridgeActor")

        trail_component = _find_trail_component(trail_actor)
        if not trail_component:
            raise RuntimeError("SnowRuntimeTrailBridgeComponent not found")
        payload["trail_component_path"] = _path(trail_component)

        plow_source = _find_plow_component(kamaz_actor)
        if not plow_source:
            raise RuntimeError("BP_PlowBrush_Component not found")
        payload["plow_source_path"] = _path(plow_source)
        plow_owner = plow_source.get_owner()

        original_props = {
            "bEnableRuntimeTrail": _safe_get(trail_component, "bEnableRuntimeTrail", True),
            "bUseSourceHeightGate": _safe_get(trail_component, "bUseSourceHeightGate", False),
            "SourceComponentOverride": _safe_get(trail_component, "SourceComponentOverride", None),
            "OwnerPlowLiftHeight": _safe_get(plow_owner, "PlowLiftHeight", None),
            "SourcePlowLiftHeight": _safe_get(plow_source, "PlowLiftHeight", None),
        }

        payload["target_runtime_height"] = _safe_get(
            trail_component,
            "RuntimeHeightAmplitudeWhenActive",
            None,
        )

        _safe_set(trail_component, "bEnableRuntimeTrail", True)
        _safe_set(trail_component, "bUseSourceHeightGate", False)
        _safe_set(trail_component, "SourceComponentOverride", plow_source)
        _safe_set(plow_owner, "PlowLiftHeight", 0.0)
        _safe_set(plow_source, "PlowLiftHeight", 0.0)

        payload["before"] = _scan_height_receivers()
        payload["stamp_written"] = bool(trail_component.record_trail_stamp_now())
        payload["after"] = _scan_height_receivers()
    except Exception as exc:
        payload["error"] = str(exc)
    finally:
        if trail_component:
            _safe_set(trail_component, "bEnableRuntimeTrail", original_props.get("bEnableRuntimeTrail", True))
            _safe_set(trail_component, "bUseSourceHeightGate", original_props.get("bUseSourceHeightGate", False))
            _safe_set(trail_component, "SourceComponentOverride", original_props.get("SourceComponentOverride", None))
        if plow_owner and original_props.get("OwnerPlowLiftHeight", None) is not None:
            _safe_set(plow_owner, "PlowLiftHeight", original_props.get("OwnerPlowLiftHeight"))
        if plow_source and original_props.get("SourcePlowLiftHeight", None) is not None:
            _safe_set(plow_source, "PlowLiftHeight", original_props.get("SourcePlowLiftHeight"))

        _write_output(payload)


if __name__ == "__main__":
    main()
