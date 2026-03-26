import json
import os

import unreal


ASSET_PATH = os.environ.get(
    "KAMAZ_MATERIAL_PATH",
    "/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush",
)
OUTPUT_BASENAME = os.environ.get("KAMAZ_TRACE_BASENAME", "trace_m_snow_plow_brush_graph")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    unreal.log(f"[trace_m_snow_plow_brush_graph] Wrote file: {path}")
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


def _serialize_value(value):
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, unreal.Name):
        return str(value)
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    path_name = _object_path(value)
    if path_name:
        return path_name
    try:
        return str(value)
    except Exception:
        return "<unserializable>"


def _get_inputs(mel, expression):
    for args in ((expression,),):
        value, error = _safe_call(mel.get_inputs_for_material_expression, *args)
        if error == "":
            return list(value or []), ""
    return [], "get_inputs_for_material_expression failed"


def _expression_entry(mel, expression):
    position, _ = _safe_call(mel.get_material_expression_node_position, expression)
    input_names, _ = _safe_call(mel.get_material_expression_input_names, expression)
    input_types, _ = _safe_call(mel.get_material_expression_input_types, expression)
    inputs, input_error = _get_inputs(mel, expression)

    return {
        "name": _object_name(expression),
        "path": _object_path(expression),
        "class": _object_path(expression.get_class()),
        "parameter_name": _serialize_value(_safe_property(expression, "parameter_name")),
        "default_value": _serialize_value(_safe_property(expression, "default_value")),
        "desc": _serialize_value(_safe_property(expression, "desc")),
        "position": _serialize_value(position),
        "input_names": _serialize_value(input_names),
        "input_types": _serialize_value(input_types),
        "inputs": [_object_path(item) for item in inputs],
        "input_error": input_error,
    }


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    material = unreal.EditorAssetLibrary.load_asset(ASSET_PATH)
    if material is None:
        raise RuntimeError(f"Could not load material: {ASSET_PATH}")

    mel = unreal.MaterialEditingLibrary
    payload = {
        "asset_path": ASSET_PATH,
        "num_material_expressions": None,
        "property_roots": [],
        "visited_expressions": [],
    }

    num_expressions, num_error = _safe_call(mel.get_num_material_expressions, material)
    payload["num_material_expressions"] = num_expressions
    payload["num_material_expressions_error"] = num_error

    visited = {}
    queue = []

    for prop in unreal.MaterialProperty:
        node, error = _safe_call(mel.get_material_property_input_node, material, prop)
        if node is None:
            continue
        output_name, _ = _safe_call(mel.get_material_property_input_node_output_name, material, prop)
        payload["property_roots"].append(
            {
                "property": str(prop),
                "node_path": _object_path(node),
                "node_name": _object_name(node),
                "output_name": _serialize_value(output_name),
                "error": error,
            }
        )
        queue.append(node)

    while queue:
        expression = queue.pop(0)
        expr_path = _object_path(expression)
        if not expr_path or expr_path in visited:
            continue
        entry = _expression_entry(mel, expression)
        visited[expr_path] = entry
        for input_path in entry["inputs"]:
            if not input_path or input_path in visited:
                continue
            input_obj = unreal.load_object(None, input_path)
            if input_obj is not None:
                queue.append(input_obj)

    payload["visited_expressions"] = list(visited.values())

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, payload)
    payload["output_path"] = output_path
    return payload


if __name__ == "__main__":
    print(run())
