import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
ROAD_LABEL = "Road2"
CARRIER_LABEL = "SnowHeightBridgeSurface_Road2"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_road2_receiver_parameter_state.json",
)


def _write_json(payload):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _safe_get(obj, prop_name, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(prop_name)
        except Exception:
            pass
    return getattr(obj, prop_name, default)


def _obj_path(obj):
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _obj_name(obj):
    if obj is None:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _find_actor_by_label(label):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        try:
            if actor.get_actor_label() == label:
                return actor
        except Exception:
            continue
    return None


def _safe_mel_list(material, fn_name):
    fn = getattr(unreal.MaterialEditingLibrary, fn_name, None)
    if not callable(fn):
        return []
    try:
        return list(fn(material) or [])
    except Exception:
        return []


def _safe_scalar(mi, name):
    fn = getattr(unreal.MaterialEditingLibrary, "get_material_instance_scalar_parameter_value", None)
    if not callable(fn):
        return None
    try:
        return float(fn(mi, name))
    except Exception:
        return None


def _safe_vector(mi, name):
    fn = getattr(unreal.MaterialEditingLibrary, "get_material_instance_vector_parameter_value", None)
    if not callable(fn):
        return None
    try:
        c = fn(mi, name)
        return [float(c.r), float(c.g), float(c.b), float(c.a)]
    except Exception:
        return None


def _safe_texture(mi, name):
    fn = getattr(unreal.MaterialEditingLibrary, "get_material_instance_texture_parameter_value", None)
    if not callable(fn):
        return ""
    try:
        return _obj_path(fn(mi, name))
    except Exception:
        return ""


def _safe_static_switch(mi, name):
    fn = getattr(unreal.MaterialEditingLibrary, "get_material_instance_static_switch_parameter_value", None)
    if not callable(fn):
        return None
    try:
        return bool(fn(mi, name))
    except Exception:
        return None


def _safe_rvt(mi, name):
    fn = getattr(unreal.MaterialEditingLibrary, "get_material_instance_runtime_virtual_texture_parameter_value", None)
    if not callable(fn):
        return ""
    try:
        return _obj_path(fn(mi, name))
    except Exception:
        return ""


def _parent_chain(material):
    chain = []
    visited = set()
    current = material
    while current is not None:
        path = _obj_path(current)
        if path in visited:
            break
        visited.add(path)
        chain.append(
            {
                "name": _obj_name(current),
                "path": path,
                "class": _obj_path(current.get_class()) if current else "",
            }
        )
        parent = None
        for prop in ("parent", "Parent", "ParentEditorOnly"):
            parent = _safe_get(current, prop, None)
            if parent is not None:
                break
        current = parent
    return chain


def _component_summary(actor):
    if actor is None:
        return {}
    smc = actor.get_component_by_class(unreal.StaticMeshComponent)
    if smc is None:
        return {}
    material = smc.get_material(0)
    return {
        "component_path": _obj_path(smc),
        "visible": bool(_safe_get(smc, "visible", True)),
        "hidden_in_game": bool(_safe_get(smc, "hidden_in_game", False)),
        "render_in_main_pass": bool(_safe_get(smc, "render_in_main_pass", True)),
        "render_in_depth_pass": bool(_safe_get(smc, "render_in_depth_pass", True)),
        "material_slot0": {
            "name": _obj_name(material),
            "path": _obj_path(material),
            "class": _obj_path(material.get_class()) if material else "",
        },
    }


def _material_params(mi):
    if mi is None:
        return {}

    scalar_names = _safe_mel_list(mi, "get_scalar_parameter_names")
    vector_names = _safe_mel_list(mi, "get_vector_parameter_names")
    texture_names = _safe_mel_list(mi, "get_texture_parameter_names")
    static_switch_names = _safe_mel_list(mi, "get_static_switch_parameter_names")
    rvt_names = _safe_mel_list(mi, "get_runtime_virtual_texture_parameter_names")

    return {
        "scalar_names": [str(n) for n in scalar_names],
        "scalar_values": {str(n): _safe_scalar(mi, n) for n in scalar_names},
        "vector_names": [str(n) for n in vector_names],
        "vector_values": {str(n): _safe_vector(mi, n) for n in vector_names},
        "texture_names": [str(n) for n in texture_names],
        "texture_values": {str(n): _safe_texture(mi, n) for n in texture_names},
        "static_switch_names": [str(n) for n in static_switch_names],
        "static_switch_values": {str(n): _safe_static_switch(mi, n) for n in static_switch_names},
        "rvt_names": [str(n) for n in rvt_names],
        "rvt_values": {str(n): _safe_rvt(mi, n) for n in rvt_names},
    }


def main():
    result = {
        "success": False,
        "map_path": MAP_PATH,
        "road": {},
        "carrier": {},
        "carrier_material_parent_chain": [],
        "carrier_material_parameters": {},
        "error": "",
    }

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        road = _find_actor_by_label(ROAD_LABEL)
        carrier = _find_actor_by_label(CARRIER_LABEL)
        if road is None:
            raise RuntimeError(f"Road actor not found: {ROAD_LABEL}")
        if carrier is None:
            raise RuntimeError(f"Carrier actor not found: {CARRIER_LABEL}")

        result["road"] = {
            "actor_path": _obj_path(road),
            "location": {
                "x": float(road.get_actor_location().x),
                "y": float(road.get_actor_location().y),
                "z": float(road.get_actor_location().z),
            },
            "component": _component_summary(road),
        }
        result["carrier"] = {
            "actor_path": _obj_path(carrier),
            "location": {
                "x": float(carrier.get_actor_location().x),
                "y": float(carrier.get_actor_location().y),
                "z": float(carrier.get_actor_location().z),
            },
            "component": _component_summary(carrier),
        }

        carrier_comp = carrier.get_component_by_class(unreal.StaticMeshComponent)
        carrier_mat = carrier_comp.get_material(0) if carrier_comp else None
        result["carrier_material_parent_chain"] = _parent_chain(carrier_mat)
        result["carrier_material_parameters"] = _material_params(carrier_mat)

        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)

    _write_json(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
