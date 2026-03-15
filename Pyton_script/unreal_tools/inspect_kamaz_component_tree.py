import json
import os

import unreal


BLUEPRINT_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
OUTPUT_BASENAME = "kamaz_component_tree"


def _log(message: str) -> None:
    unreal.log(f"[inspect_kamaz_component_tree] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_name(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _object_path(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _vec_to_dict(value):
    if value is None:
        return None
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def _rot_to_dict(value):
    if value is None:
        return None
    return {"pitch": float(value.pitch), "yaw": float(value.yaw), "roll": float(value.roll)}


def _bounds_to_dict(bounds):
    if bounds is None:
        return None
    return {
        "origin": _vec_to_dict(bounds.origin),
        "box_extent": _vec_to_dict(bounds.box_extent),
        "sphere_radius": float(bounds.sphere_radius),
    }


def _safe_get(obj, property_name: str, default=None):
    getter = getattr(obj, "get_editor_property", None)
    if getter is None:
        return getattr(obj, property_name, default)
    try:
        return getter(property_name)
    except Exception:
        return getattr(obj, property_name, default)


def _mesh_info(template) -> dict:
    info = {}
    for property_name in ("static_mesh", "skeletal_mesh"):
        mesh = _safe_get(template, property_name, None)
        if mesh is None:
            continue
        bounds = None
        get_bounds = getattr(mesh, "get_bounds", None)
        if callable(get_bounds):
            try:
                bounds = get_bounds()
            except Exception:
                bounds = None
        info = {
            "mesh_property": property_name,
            "mesh_name": _object_name(mesh),
            "mesh_path": _object_path(mesh),
            "mesh_bounds": _bounds_to_dict(bounds),
        }
        break
    return info


def _node_entry(node):
    template = node.get_editor_property("component_template")
    parent = node.get_parent()
    entry = {
        "node_name": _object_name(node),
        "variable_name": str(node.get_variable_name()),
        "parent_name": _object_name(parent),
        "parent_variable_name": str(parent.get_variable_name()) if parent else "",
        "component_class": _object_path(template.get_class()) if template else "",
        "component_template_path": _object_path(template),
        "attach_socket_name": str(_safe_get(node, "attach_to_name", "")),
        "relative_location": _vec_to_dict(_safe_get(template, "relative_location", None)),
        "relative_rotation": _rot_to_dict(_safe_get(template, "relative_rotation", None)),
        "relative_scale": _vec_to_dict(_safe_get(template, "relative_scale3d", None)),
    }
    entry.update(_mesh_info(template))
    return entry


def _component_entry(component):
    parent = None
    get_attach_parent = getattr(component, "get_attach_parent", None)
    if callable(get_attach_parent):
        try:
            parent = get_attach_parent()
        except Exception:
            parent = None

    entry = {
        "node_name": _object_name(component),
        "variable_name": _object_name(component),
        "parent_name": _object_name(parent),
        "parent_variable_name": _object_name(parent),
        "component_class": _object_path(component.get_class()),
        "component_template_path": _object_path(component),
        "attach_socket_name": str(_safe_get(component, "attach_socket_name", "")),
        "relative_location": _vec_to_dict(_safe_get(component, "relative_location", None)),
        "relative_rotation": _rot_to_dict(_safe_get(component, "relative_rotation", None)),
        "relative_scale": _vec_to_dict(_safe_get(component, "relative_scale3d", None)),
    }
    entry.update(_mesh_info(component))
    return entry


def inspect_kamaz_component_tree(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    blueprint = unreal.EditorAssetLibrary.load_asset(BLUEPRINT_PATH)
    if blueprint is None:
        raise RuntimeError(f"Could not load blueprint: {BLUEPRINT_PATH}")

    scs = _safe_get(blueprint, "simple_construction_script", None)
    node_entries = []

    if scs is not None:
        nodes = list(scs.get_all_nodes() or [])
        node_entries = [_node_entry(node) for node in nodes]
    else:
        generated_class = _safe_get(blueprint, "generated_class", None)
        if callable(generated_class):
            generated_class = generated_class()
        if generated_class is None:
            raise RuntimeError(f"Could not resolve generated class for: {BLUEPRINT_PATH}")
        cdo = unreal.get_default_object(generated_class)
        components = list(cdo.get_components_by_class(unreal.ActorComponent) or [])
        node_entries = [_component_entry(component) for component in components]

    result = {
        "blueprint_path": BLUEPRINT_PATH,
        "num_nodes": len(node_entries),
        "nodes": node_entries,
        "interesting_nodes": [
            entry
            for entry in node_entries
            if entry["variable_name"] in ("SM_FrontHitch", "PlowBrush", "BP_PlowBrush_Component")
        ],
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(inspect_kamaz_component_tree())
