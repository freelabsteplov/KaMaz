import json
import os

import unreal


BLUEPRINT_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
TARGET_COMPONENT_NAMES = (
    "SM_FrontHitch",
    "PlowBrush",
    "BP_PlowBrush_Component",
)
OUTPUT_BASENAME = "kamaz_named_components"


def _log(message: str) -> None:
    unreal.log(f"[inspect_kamaz_named_components] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _safe_get(obj, property_name: str, default=None):
    if obj is None:
        return default

    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(property_name)
        except Exception:
            pass

    return getattr(obj, property_name, default)


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


def _serialize_value(value):
    if value is None:
        return None

    if isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, unreal.Name):
        return str(value)

    if isinstance(value, unreal.Vector):
        return _vec_to_dict(value)

    if isinstance(value, unreal.Rotator):
        return _rot_to_dict(value)

    if isinstance(value, unreal.Array):
        return [_serialize_value(item) for item in value]

    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]

    path_name = _object_path(value)
    if path_name:
        return path_name

    try:
        return str(value)
    except Exception:
        return "<unserializable>"


def _component_bounds(component):
    if component is None:
        return None

    for method_name in ("get_local_bounds", "get_bounds"):
        method = getattr(component, method_name, None)
        if not callable(method):
            continue
        try:
            result = method()
        except Exception:
            continue

        if method_name == "get_local_bounds" and isinstance(result, tuple) and len(result) == 2:
            return {
                "local_min": _vec_to_dict(result[0]),
                "local_max": _vec_to_dict(result[1]),
            }

        return _bounds_to_dict(result)

    return None


def _component_entry(component_name: str, component) -> dict:
    parent = None
    get_attach_parent = getattr(component, "get_attach_parent", None)
    if callable(get_attach_parent):
        try:
            parent = get_attach_parent()
        except Exception:
            parent = None

    entry = {
        "requested_name": component_name,
        "found": component is not None,
        "object_name": _object_name(component),
        "object_path": _object_path(component),
        "component_class": _object_path(component.get_class()) if component else "",
        "attach_parent_name": _object_name(parent),
        "attach_parent_path": _object_path(parent),
        "attach_socket_name": _serialize_value(_safe_get(component, "attach_socket_name")),
        "relative_location": _serialize_value(_safe_get(component, "relative_location")),
        "relative_rotation": _serialize_value(_safe_get(component, "relative_rotation")),
        "relative_scale3d": _serialize_value(_safe_get(component, "relative_scale3d")),
        "world_location": None,
        "world_rotation": None,
        "world_scale3d": None,
        "box_extent": _serialize_value(_safe_get(component, "box_extent")),
        "brush_class": _serialize_value(_safe_get(component, "brush_shape")),
        "static_mesh": _serialize_value(_safe_get(component, "static_mesh")),
        "skeletal_mesh": _serialize_value(_safe_get(component, "skeletal_mesh")),
        "child_actor_class": _serialize_value(_safe_get(component, "child_actor_class")),
        "component_bounds": _component_bounds(component),
    }

    if component is not None:
        for method_name, key in (
            ("get_relative_location", "relative_location_runtime"),
            ("get_relative_rotation", "relative_rotation_runtime"),
            ("get_component_location", "world_location"),
            ("get_component_rotation", "world_rotation"),
            ("get_component_scale", "world_scale3d"),
        ):
            method = getattr(component, method_name, None)
            if not callable(method):
                continue
            try:
                entry[key] = _serialize_value(method())
            except Exception:
                entry[key] = None

    interesting_properties = {}
    for property_name in (
        "BoxExtent",
        "box_extent",
        "PlowLiftHeight",
        "bEnablePlowClearing",
        "RenderTargetGlobal",
    ):
        value = _safe_get(component, property_name, None)
        if value is not None:
            interesting_properties[property_name] = _serialize_value(value)
    entry["interesting_properties"] = interesting_properties
    return entry


def inspect_named_components(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    blueprint = unreal.EditorAssetLibrary.load_asset(BLUEPRINT_PATH)
    if blueprint is None:
        raise RuntimeError(f"Could not load blueprint: {BLUEPRINT_PATH}")

    generated_class = _safe_get(blueprint, "generated_class", None)
    if callable(generated_class):
        generated_class = generated_class()
    if generated_class is None:
        raise RuntimeError(f"Could not resolve generated class for: {BLUEPRINT_PATH}")

    cdo = unreal.get_default_object(generated_class)
    components = {}
    for component_name in TARGET_COMPONENT_NAMES:
        component = _safe_get(cdo, component_name, None)
        if component is None:
            component = _safe_get(cdo, component_name.lower(), None)
        components[component_name] = _component_entry(component_name, component)

    result = {
        "blueprint_path": BLUEPRINT_PATH,
        "generated_class": _object_path(generated_class),
        "default_object": _object_path(cdo),
        "components": components,
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(inspect_named_components())
