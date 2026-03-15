import json
import os

import unreal


PLOWBRUSH_ASSET_PATH = "/Game/CityPark/SnowSystem/BP_PlowBrush_Component"
WHEELSNOW_ASSET_PATH = "/Game/CityPark/SnowSystem/BP_WheelSnowTrace_Component"


def _log(message: str) -> None:
    unreal.log(f"[blueprint_graph_dump_tools] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[blueprint_graph_dump_tools] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _safe_call(obj, method_name: str, *args, default=None):
    method = getattr(obj, method_name, None)
    if method is None:
        return default

    try:
        return method(*args)
    except Exception:
        return default


def _safe_attr(obj, attr_name: str, default=None):
    try:
        return getattr(obj, attr_name)
    except Exception:
        return default


def _safe_editor_property(obj, property_name: str, default=None):
    getter = getattr(obj, "get_editor_property", None)
    if getter is None:
        return _safe_attr(obj, property_name, default)

    try:
        return getter(property_name)
    except Exception:
        return _safe_attr(obj, property_name, default)


def _enum_to_string(value) -> str:
    if value is None:
        return ""
    return str(value)


def _object_path(obj) -> str:
    if obj is None:
        return ""

    path = _safe_call(obj, "get_path_name")
    if path:
        return path

    return str(obj)


def _object_name(obj) -> str:
    if obj is None:
        return ""

    name = _safe_call(obj, "get_name")
    if name:
        return name

    return str(obj)


def _load_blueprint_asset(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not asset:
        raise RuntimeError(f"Failed to load asset: {asset_path}")

    blueprint = None

    try:
        blueprint = unreal.BlueprintEditorLibrary.get_blueprint_asset(asset)
    except Exception:
        blueprint = None

    if blueprint:
        return blueprint

    return asset


def _get_all_graphs(blueprint) -> list:
    graphs = []
    seen_paths = set()

    event_graph = None
    try:
        event_graph = unreal.BlueprintEditorLibrary.find_event_graph(blueprint)
    except Exception:
        event_graph = None

    if event_graph:
        graphs.append(event_graph)
        seen_paths.add(_object_path(event_graph))

    for property_name in ("ubergraph_pages", "function_graphs", "delegate_signature_graphs", "macro_graphs"):
        for graph in _safe_editor_property(blueprint, property_name, []) or []:
            graph_path = _object_path(graph)
            if graph and graph_path not in seen_paths:
                graphs.append(graph)
                seen_paths.add(graph_path)

    return graphs


def list_graphs(asset_path: str):
    blueprint = _load_blueprint_asset(asset_path)
    result = []

    for graph in _get_all_graphs(blueprint):
        result.append(
            {
                "name": _object_name(graph),
                "path": _object_path(graph),
                "class": _object_path(_safe_call(graph, "get_class")),
            }
        )

    _log(f"Found {len(result)} graphs on {asset_path}")
    return result


def _find_graph(blueprint, graph_name: str):
    try:
        graph = unreal.BlueprintEditorLibrary.find_graph(blueprint, graph_name)
        if graph:
            return graph
    except Exception:
        pass

    for graph in _get_all_graphs(blueprint):
        if _object_name(graph) == graph_name:
            return graph

    return None


def _serialize_pin_link(pin_link) -> dict:
    owning_node = _safe_call(pin_link, "get_owning_node")
    pin_name = _safe_attr(pin_link, "pin_name")
    if pin_name is None:
        pin_name = _safe_call(pin_link, "get_name", default="")

    return {
        "node_name": _object_name(owning_node),
        "node_path": _object_path(owning_node),
        "pin_name": str(pin_name or ""),
    }


def _serialize_pin(pin) -> dict:
    default_object = _safe_attr(pin, "default_object")
    pin_name = _safe_attr(pin, "pin_name")
    if pin_name is None:
        pin_name = _safe_call(pin, "get_name", default="")

    links = []
    for linked_pin in _safe_attr(pin, "linked_to", []) or []:
        links.append(_serialize_pin_link(linked_pin))

    return {
        "name": str(pin_name or ""),
        "direction": _enum_to_string(_safe_attr(pin, "direction")),
        "category": str(_safe_attr(pin, "pin_type", "")),
        "default_value": str(_safe_attr(pin, "default_value", "") or ""),
        "default_object": _object_path(default_object),
        "linked_to": links,
    }


def _node_title(node) -> str:
    node_title_type = getattr(unreal, "NodeTitleType", None)
    if node_title_type is not None:
        full_title = getattr(node_title_type, "FULL_TITLE", None)
        if full_title is not None:
            title = _safe_call(node, "get_node_title", full_title)
            if title:
                return str(title)

    title = _safe_call(node, "get_node_title")
    if title:
        return str(title)

    return _object_name(node)


def _serialize_node(node) -> dict:
    return {
        "name": _object_name(node),
        "path": _object_path(node),
        "class": _object_path(_safe_call(node, "get_class")),
        "title": _node_title(node),
        "comment": str(_safe_editor_property(node, "node_comment", "") or ""),
        "guid": str(_safe_editor_property(node, "node_guid", "") or ""),
        "pos_x": int(_safe_editor_property(node, "node_pos_x", 0) or 0),
        "pos_y": int(_safe_editor_property(node, "node_pos_y", 0) or 0),
        "pins": [_serialize_pin(pin) for pin in _safe_editor_property(node, "pins", []) or []],
    }


def inspect_graph(asset_path: str, graph_name: str) -> dict:
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is not None and hasattr(bridge, "inspect_blueprint_graph"):
        raw_result = bridge.inspect_blueprint_graph(asset_path, graph_name, True, True)
        success = False
        strings = []

        if isinstance(raw_result, tuple):
            for item in raw_result:
                if isinstance(item, bool):
                    success = item
                elif isinstance(item, str):
                    strings.append(item)
        elif isinstance(raw_result, bool):
            success = raw_result

        while len(strings) < 2:
            strings.append("")

        graph_json, summary = strings[:2]
        if not success:
            raise RuntimeError(summary or f"inspect_blueprint_graph failed for {asset_path}:{graph_name}")
        payload = json.loads(graph_json)
        _log(f"Inspected graph '{graph_name}' on {asset_path}: {payload.get('node_count', len(payload.get('nodes', [])))} nodes")
        return payload

    blueprint = _load_blueprint_asset(asset_path)
    graph = _find_graph(blueprint, graph_name)
    if not graph:
        available = [item["name"] for item in list_graphs(asset_path)]
        raise RuntimeError(f"Graph '{graph_name}' was not found on {asset_path}. Available: {available}")

    nodes = _safe_editor_property(graph, "nodes", []) or []
    schema = _safe_editor_property(graph, "schema")

    payload = {
        "asset_path": asset_path,
        "graph_name": _object_name(graph),
        "graph_path": _object_path(graph),
        "graph_class": _object_path(_safe_call(graph, "get_class")),
        "graph_schema": _object_path(schema),
        "node_count": len(nodes),
        "nodes": [_serialize_node(node) for node in nodes],
    }

    _log(f"Inspected graph '{graph_name}' on {asset_path}: {len(nodes)} nodes")
    return payload


def export_graph(asset_path: str, graph_name: str, file_prefix: str, output_dir: str = None) -> str:
    output_dir = output_dir or _saved_output_dir()
    payload = inspect_graph(asset_path, graph_name)
    path = os.path.join(output_dir, f"{file_prefix}.json")
    return _write_json(path, payload)


def export_plowbrush_drawplowclearance(output_dir: str = None) -> str:
    return export_graph(
        PLOWBRUSH_ASSET_PATH,
        "DrawPlowClearance",
        "plowbrush_drawplowclearance_graph",
        output_dir,
    )


def export_wheelsnow_drawwheeltraces(output_dir: str = None) -> str:
    return export_graph(
        WHEELSNOW_ASSET_PATH,
        "DrawWheelTraces",
        "wheelsnow_drawwheeltraces_graph",
        output_dir,
    )


def export_snow_function_graphs(output_dir: str = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    result = {}

    try:
        result["plowbrush_drawplowclearance"] = export_plowbrush_drawplowclearance(output_dir)
    except Exception as exc:
        _warn(str(exc))
        result["plowbrush_drawplowclearance_error"] = str(exc)

    try:
        result["wheelsnow_drawwheeltraces"] = export_wheelsnow_drawwheeltraces(output_dir)
    except Exception as exc:
        _warn(str(exc))
        result["wheelsnow_drawwheeltraces_error"] = str(exc)

    return result


if __name__ == "__main__":
    _log("Loaded blueprint_graph_dump_tools.py")
