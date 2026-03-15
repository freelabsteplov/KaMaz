import json
import os

import unreal


BLUEPRINT_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
OUTPUT_BASENAME = "kamaz_subobjects"


def _log(message: str) -> None:
    unreal.log(f"[inspect_kamaz_subobjects] {message}")


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


def _resolve_object(function_library, handle, data, blueprint):
    for args in (
        (handle,),
        (data,),
        (handle, blueprint),
        (data, blueprint),
    ):
        value, error = _safe_call(function_library.get_object, *args)
        if error == "":
            return value, {"get_object_args": [str(type(arg)) for arg in args]}

    for args in (
        (handle, blueprint),
        (data, blueprint),
        (blueprint, handle),
        (blueprint, data),
    ):
        value, error = _safe_call(function_library.get_object_for_blueprint, *args)
        if error == "":
            return value, {"get_object_for_blueprint_args": [str(type(arg)) for arg in args]}

    return None, {}


def inspect_subobjects(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    blueprint = unreal.EditorAssetLibrary.load_asset(BLUEPRINT_PATH)
    if blueprint is None:
        raise RuntimeError(f"Could not load blueprint: {BLUEPRINT_PATH}")

    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    function_library = unreal.SubobjectDataBlueprintFunctionLibrary

    handles = list(subsystem.k2_gather_subobject_data_for_blueprint(blueprint) or [])
    entries = []

    for index, handle in enumerate(handles):
        valid, valid_error = _safe_call(function_library.is_handle_valid, handle)
        data, data_error = _safe_call(function_library.get_data, handle)
        display_name, display_name_error = _safe_call(function_library.get_display_name, handle)
        variable_name, variable_name_error = _safe_call(function_library.get_variable_name, handle)
        parent_handle, parent_error = _safe_call(function_library.get_parent_handle, handle)
        parent_display_name = None
        if parent_error == "" and parent_handle is not None:
            parent_display_name, _ = _safe_call(function_library.get_display_name, parent_handle)

        subobject_object, object_resolution = _resolve_object(function_library, handle, data, blueprint)

        entry = {
            "index": index,
            "is_handle_valid": bool(valid) if valid_error == "" else None,
            "valid_error": valid_error,
            "display_name": _serialize_value(display_name),
            "display_name_error": display_name_error,
            "variable_name": _serialize_value(variable_name),
            "variable_name_error": variable_name_error,
            "parent_display_name": _serialize_value(parent_display_name),
            "parent_error": parent_error,
            "object_resolution": object_resolution,
            "object_name": _object_name(subobject_object),
            "object_path": _object_path(subobject_object),
            "object_class": _object_path(subobject_object.get_class()) if subobject_object else "",
            "relative_location": _serialize_value(_safe_property(subobject_object, "relative_location")),
            "relative_rotation": _serialize_value(_safe_property(subobject_object, "relative_rotation")),
            "relative_scale3d": _serialize_value(_safe_property(subobject_object, "relative_scale3d")),
            "box_extent": _serialize_value(_safe_property(subobject_object, "box_extent")),
            "static_mesh": _serialize_value(_safe_property(subobject_object, "static_mesh")),
            "skeletal_mesh": _serialize_value(_safe_property(subobject_object, "skeletal_mesh")),
            "child_actor_class": _serialize_value(_safe_property(subobject_object, "child_actor_class")),
            "component_tags": _serialize_value(_safe_property(subobject_object, "component_tags")),
            "data_error": data_error,
        }
        entries.append(entry)

    result = {
        "blueprint_path": BLUEPRINT_PATH,
        "num_handles": len(handles),
        "entries": entries,
        "interesting_entries": [
            entry
            for entry in entries
            if str(entry.get("display_name") or "").lower().find("plow") >= 0
            or str(entry.get("variable_name") or "").lower().find("plow") >= 0
            or str(entry.get("display_name") or "").lower().find("hitch") >= 0
            or str(entry.get("variable_name") or "").lower().find("hitch") >= 0
        ],
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(inspect_subobjects())
