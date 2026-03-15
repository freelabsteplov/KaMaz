import json
import os

import unreal


BLUEPRINT_PATH = "/Game/CityPark/SnowSystem/BP_PlowBrush_Component"
OUTPUT_BASENAME = "bp_plowbrush_component_inspect"


def _log(message: str) -> None:
    unreal.log(f"[inspect_bp_plowbrush_component] {message}")


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
    }


def inspect_blueprint(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    blueprint = unreal.EditorAssetLibrary.load_asset(BLUEPRINT_PATH)
    if blueprint is None:
        raise RuntimeError(f"Could not load blueprint: {BLUEPRINT_PATH}")

    generated_class = _safe_property(blueprint, "generated_class")
    if callable(generated_class):
        generated_class = generated_class()
    if generated_class is None:
        raise RuntimeError(f"Could not resolve generated class for: {BLUEPRINT_PATH}")

    cdo = unreal.get_default_object(generated_class)
    dir_names = [name for name in dir(cdo) if any(token in name.lower() for token in ("brush", "box", "extent", "size", "scale"))]
    filtered_properties = {}
    for name in sorted(dir_names):
        value = _safe_property(cdo, name, None)
        if value is not None:
            filtered_properties[name] = _serialize_value(value)

    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    function_library = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = list(subsystem.k2_gather_subobject_data_for_blueprint(blueprint) or [])

    subobjects = []
    for handle in handles:
        data, data_error = _safe_call(function_library.get_data, handle)
        if data_error != "":
            continue
        display_name, _ = _safe_call(function_library.get_display_name, data)
        variable_name, _ = _safe_call(function_library.get_variable_name, data)
        parent_handle, _ = _safe_call(function_library.get_parent_handle, data)
        parent_display_name = None
        if parent_handle is not None:
            parent_data, _ = _safe_call(function_library.get_data, parent_handle)
            if parent_data is not None:
                parent_display_name, _ = _safe_call(function_library.get_display_name, parent_data)
        associated_object, _ = _safe_call(function_library.get_associated_object, data)

        haystack = " ".join(
            [
                str(display_name or ""),
                str(variable_name or ""),
                _object_name(associated_object),
                _object_path(associated_object),
                _object_path(associated_object.get_class()) if associated_object else "",
            ]
        ).lower()

        if any(token in haystack for token in ("brush", "box", "extent", "size", "scale")):
            subobjects.append(
                {
                    "display_name": _serialize_value(display_name),
                    "variable_name": _serialize_value(variable_name),
                    "parent_display_name": _serialize_value(parent_display_name),
                    "associated_object": _component_summary(associated_object),
                }
            )

    result = {
        "blueprint_path": BLUEPRINT_PATH,
        "generated_class": _object_path(generated_class),
        "default_object": _object_path(cdo),
        "filtered_cdo_properties": filtered_properties,
        "subobjects": subobjects,
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(inspect_blueprint())
