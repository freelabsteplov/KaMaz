import json
import os

import unreal


TARGETS = [
    ("/Game/CityPark/SnowSystem/BP_PlowBrush_Component", "DrawPlowClearance"),
    ("/Game/CityPark/SnowSystem/BP_WheelSnowTrace_Component", "DrawWheelTraces"),
]


def _log(message: str) -> None:
    unreal.log(f"[blueprint_function_origin_tools] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _safe_call(obj, method_name: str, *args, **kwargs):
    method = getattr(obj, method_name, None)
    if method is None:
        return None
    try:
        return method(*args, **kwargs)
    except Exception:
        return None


def _safe_get_editor_property(obj, property_name: str, default=None):
    getter = getattr(obj, "get_editor_property", None)
    if getter is None:
        return getattr(obj, property_name, default)
    try:
        return getter(property_name)
    except Exception:
        return getattr(obj, property_name, default)


def _object_name(obj) -> str:
    if obj is None:
        return ""
    return _safe_call(obj, "get_name") or str(obj)


def _object_path(obj) -> str:
    if obj is None:
        return ""
    return _safe_call(obj, "get_path_name") or str(obj)


def _load_blueprint(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not asset:
        raise RuntimeError(f"Failed to load asset: {asset_path}")

    lib = getattr(unreal, "BlueprintEditorLibrary", None)
    if lib is not None:
        bp = _safe_call(lib, "get_blueprint_asset", asset)
        if bp:
            return bp
    return asset


def inspect_function_origin(asset_path: str, function_name: str) -> dict:
    blueprint = _load_blueprint(asset_path)
    generated_class = _safe_get_editor_property(blueprint, "generated_class")
    parent_class = _safe_get_editor_property(blueprint, "parent_class")

    function_graph = None
    lib = getattr(unreal, "BlueprintEditorLibrary", None)
    if lib is not None:
        function_graph = _safe_call(lib, "find_graph", blueprint, function_name)

    function_graph_nodes = _safe_get_editor_property(function_graph, "nodes", []) or []

    result = {
        "asset_path": asset_path,
        "blueprint_path": _object_path(blueprint),
        "generated_class_path": _object_path(generated_class),
        "generated_class_name": _object_name(generated_class),
        "parent_class_path": _object_path(parent_class),
        "parent_class_name": _object_name(parent_class),
        "function_name": function_name,
        "function_graph_path": _object_path(function_graph),
        "function_graph_node_count": len(function_graph_nodes),
        "has_generated_class_function_attr": hasattr(generated_class, function_name) if generated_class else False,
        "has_parent_class_function_attr": hasattr(parent_class, function_name) if parent_class else False,
    }

    generated_attr = getattr(generated_class, function_name, None) if generated_class else None
    parent_attr = getattr(parent_class, function_name, None) if parent_class else None

    result["generated_attr_repr"] = str(generated_attr)
    result["parent_attr_repr"] = str(parent_attr)

    return result


def inspect_targets(output_dir: str = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    results = [inspect_function_origin(asset_path, function_name) for asset_path, function_name in TARGETS]
    output_path = os.path.join(output_dir, "snow_function_origin.json")
    _write_json(output_path, results)
    return {"results": results, "output_path": output_path}


if __name__ == "__main__":
    _log("Loaded blueprint_function_origin_tools.py")
