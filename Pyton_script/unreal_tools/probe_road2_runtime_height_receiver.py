import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
TRAIL_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.SnowRuntimeTrailBridgeActor_0"
CARRIER_ACTOR_LABEL = "SnowHeightBridgeSurface_Road2"
HEIGHT_PARAM_NAME = "HeightAmplitude"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "probe_road2_runtime_height_receiver.json",
)


def _path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _label(actor):
    if not actor:
        return ""
    try:
        return actor.get_actor_label()
    except Exception:
        return ""


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
    if obj is None:
        return False
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


def _material_scalar(material, param_name):
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


def _scan_carrier_materials(carrier_actor):
    payload = []
    if not carrier_actor:
        return payload
    mesh_component = carrier_actor.get_component_by_class(unreal.StaticMeshComponent)
    if not mesh_component:
        return payload
    material_count = int(mesh_component.get_num_materials())
    for material_index in range(material_count):
        material = mesh_component.get_material(material_index)
        payload.append(
            {
                "slot": material_index,
                "material_class": material.get_class().get_name() if material else "",
                "material_path": _path(material),
                "parent_path": _path(_safe_get(material, "parent", None)),
                "height_amplitude": _material_scalar(material, HEIGHT_PARAM_NAME) if material else None,
            }
        )
    return payload


def main():
    payload = {
        "success": False,
        "map": MAP_PATH,
        "trail_actor_path": TRAIL_ACTOR_PATH,
        "carrier_actor_label": CARRIER_ACTOR_LABEL,
        "trail_component_path": "",
        "carrier_actor_path": "",
        "trail_component_state": {},
        "target_runtime_height_when_active": None,
        "before": [],
        "after": [],
        "stamp_written": False,
        "error": "",
    }

    original_props = {}
    trail_actor = None
    trail_component = None

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        trail_actor = _find_actor_by_path(TRAIL_ACTOR_PATH)
        carrier_actor = _find_actor_by_label(CARRIER_ACTOR_LABEL)
        if not trail_actor or not carrier_actor:
            raise RuntimeError("Trail actor or Road2 carrier missing")

        trail_component = _find_trail_component(trail_actor)
        if not trail_component:
            raise RuntimeError("SnowRuntimeTrailBridgeComponent not found")

        payload["trail_component_path"] = _path(trail_component)
        payload["carrier_actor_path"] = _path(carrier_actor)
        payload["target_runtime_height_when_active"] = _safe_get(
            trail_component,
            "RuntimeHeightAmplitudeWhenActive",
            None,
        )
        payload["trail_component_state"] = {
            "RuntimeHeightAmplitudeWhenInactive": _safe_get(
                trail_component,
                "RuntimeHeightAmplitudeWhenInactive",
                None,
            ),
            "RuntimeHeightAmplitudeWhenActive": _safe_get(
                trail_component,
                "RuntimeHeightAmplitudeWhenActive",
                None,
            ),
            "StampSpacingCm": _safe_get(
                trail_component,
                "StampSpacingCm",
                None,
            ),
            "bEnableRvtVisualStamp": _safe_get(
                trail_component,
                "bEnableRvtVisualStamp",
                None,
            ),
            "bEnableRuntimeTrail": _safe_get(
                trail_component,
                "bEnableRuntimeTrail",
                None,
            ),
            "bUseSourceHeightGate": _safe_get(
                trail_component,
                "bUseSourceHeightGate",
                None,
            ),
        }

        original_props = {
            "bEnableRuntimeTrail": _safe_get(trail_component, "bEnableRuntimeTrail", True),
            "bUseSourceHeightGate": _safe_get(trail_component, "bUseSourceHeightGate", False),
            "SourceComponentOverride": _safe_get(trail_component, "SourceComponentOverride", None),
        }

        trail_root = _safe_get(trail_actor, "root_component", None)

        _safe_set(trail_component, "bEnableRuntimeTrail", True)
        _safe_set(trail_component, "bUseSourceHeightGate", False)
        _safe_set(trail_component, "SourceComponentOverride", trail_root)

        payload["before"] = _scan_carrier_materials(carrier_actor)
        payload["stamp_written"] = bool(trail_component.record_trail_stamp_now())
        payload["after"] = _scan_carrier_materials(carrier_actor)
        payload["success"] = True
    except Exception as exc:
        payload["error"] = str(exc)
    finally:
        if trail_component:
            _safe_set(trail_component, "bEnableRuntimeTrail", original_props.get("bEnableRuntimeTrail", True))
            _safe_set(trail_component, "bUseSourceHeightGate", original_props.get("bUseSourceHeightGate", False))
            _safe_set(trail_component, "SourceComponentOverride", original_props.get("SourceComponentOverride", None))

        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
