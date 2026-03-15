import json
import os

import unreal


BLUEPRINT_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
OUTPUT_BASENAME = "plow_brush_setup"


def _log(message: str) -> None:
    unreal.log(f"[inspect_plow_brush_setup] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _safe_call(callable_obj, *args):
    try:
        return callable_obj(*args), ""
    except Exception as exc:
        return None, str(exc)


def _safe_property(obj, property_name: str, default=None):
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


def _component_summary(component) -> dict:
    if component is None:
        return {}

    return {
        "name": _object_name(component),
        "path": _object_path(component),
        "class": _object_path(component.get_class()),
        "relative_location": _serialize_value(_safe_property(component, "relative_location")),
        "relative_rotation": _serialize_value(_safe_property(component, "relative_rotation")),
        "relative_scale3d": _serialize_value(_safe_property(component, "relative_scale3d")),
        "box_extent": _serialize_value(_safe_property(component, "box_extent")),
        "component_tags": _serialize_value(_safe_property(component, "component_tags")),
        "static_mesh": _serialize_value(_safe_property(component, "static_mesh")),
        "skeletal_mesh": _serialize_value(_safe_property(component, "skeletal_mesh")),
    }


def _actor_summary(actor) -> dict:
    if actor is None:
        return {}

    root_component = _safe_property(actor, "root_component")
    components = []
    get_components = getattr(actor, "get_components_by_class", None)
    if callable(get_components):
        try:
            for component in list(get_components(unreal.ActorComponent) or []):
                components.append(_component_summary(component))
        except Exception:
            components = []

    return {
        "name": _object_name(actor),
        "path": _object_path(actor),
        "class": _object_path(actor.get_class()),
        "root_component": _component_summary(root_component),
        "components": components,
    }


def _subobject_entry(function_library, data, blueprint) -> dict:
    display_name, display_error = _safe_call(function_library.get_display_name, data)
    variable_name, variable_error = _safe_call(function_library.get_variable_name, data)
    parent_handle, parent_error = _safe_call(function_library.get_parent_handle, data)

    parent_display_name = None
    if parent_error == "" and parent_handle is not None:
        parent_data, parent_data_error = _safe_call(function_library.get_data, parent_handle)
        if parent_data_error == "":
            parent_display_name, _ = _safe_call(function_library.get_display_name, parent_data)
    else:
        parent_data_error = ""

    associated_object, associated_error = _safe_call(function_library.get_associated_object, data)
    object_for_blueprint, blueprint_object_error = _safe_call(function_library.get_object_for_blueprint, data, blueprint)
    child_actor_template = _safe_property(associated_object, "child_actor_template")
    child_actor_class = _safe_property(associated_object, "child_actor_class")

    return {
        "display_name": _serialize_value(display_name),
        "display_name_error": display_error,
        "variable_name": _serialize_value(variable_name),
        "variable_name_error": variable_error,
        "parent_display_name": _serialize_value(parent_display_name),
        "parent_error": parent_error,
        "parent_data_error": parent_data_error,
        "associated_object_error": associated_error,
        "blueprint_object_error": blueprint_object_error,
        "associated_object": _component_summary(associated_object),
        "blueprint_object": _component_summary(object_for_blueprint),
        "child_actor_class": _serialize_value(child_actor_class),
        "child_actor_template": _actor_summary(child_actor_template),
    }


def inspect_plow_brush_setup(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    blueprint = unreal.EditorAssetLibrary.load_asset(BLUEPRINT_PATH)
    if blueprint is None:
        raise RuntimeError(f"Could not load blueprint: {BLUEPRINT_PATH}")

    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    function_library = unreal.SubobjectDataBlueprintFunctionLibrary

    handles = list(subsystem.k2_gather_subobject_data_for_blueprint(blueprint) or [])
    entries = []

    for handle in handles:
        data, data_error = _safe_call(function_library.get_data, handle)
        if data_error != "":
            continue

        entry = _subobject_entry(function_library, data, blueprint)
        haystack = " ".join(
            [
                str(entry.get("display_name") or ""),
                str(entry.get("variable_name") or ""),
                str(entry.get("associated_object", {}).get("name") or ""),
                str(entry.get("associated_object", {}).get("path") or ""),
            ]
        ).lower()
        if "plow" in haystack or "hitch" in haystack or "brush" in haystack:
            entries.append(entry)

    result = {
        "blueprint_path": BLUEPRINT_PATH,
        "entries": entries,
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(inspect_plow_brush_setup())
