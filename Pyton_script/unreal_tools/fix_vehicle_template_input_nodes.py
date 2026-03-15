import json
import os

import unreal


PAWN_BASE_ASSET_PATH = "/Game/VehicleTemplate/Blueprints/BP_VehicleAdvPawnBase"
SPORTSCAR_ASSET_PATH = "/Game/VehicleTemplate/Blueprints/SportsCar/BP_VehicleAdvSportsCar"

ACTION_ASSET_PATHS = {
    "throttle": "/Game/VehicleTemplate/Input/Actions/IA_Throttle",
    "steering": "/Game/VehicleTemplate/Input/Actions/IA_Steering",
    "brake": "/Game/VehicleTemplate/Input/Actions/IA_Brake",
    "handbrake": "/Game/VehicleTemplate/Input/Actions/IA_Handbrake",
    "reset": "/Game/VehicleTemplate/Input/Actions/IA_Reset",
    "lookaround": "/Game/VehicleTemplate/Input/Actions/IA_LookAround",
    "togglecamera": "/Game/VehicleTemplate/Input/Actions/IA_ToggleCamera",
    "headlights": "/Game/VehicleTemplate/Input/Actions/IA_Headlights",
}

OUTPUT_BASENAME = "vehicle_template_input_fix"


def _log(message: str) -> None:
    unreal.log(f"[fix_vehicle_template_input_nodes] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[fix_vehicle_template_input_nodes] {message}")


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


def _safe_set_editor_property(obj, property_name: str, value) -> bool:
    setter = getattr(obj, "set_editor_property", None)
    if setter is None:
        return False

    try:
        setter(property_name, value)
        return True
    except Exception:
        return False


def _object_name(obj) -> str:
    if obj is None:
        return ""
    name = _safe_call(obj, "get_name")
    return name or str(obj)


def _class_path(obj) -> str:
    cls = _safe_call(obj, "get_class")
    return _object_path(cls)


def _object_path(obj) -> str:
    if obj is None:
        return ""
    path = _safe_call(obj, "get_path_name")
    return path or str(obj)


def _load_asset(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if not asset:
        raise RuntimeError(f"Failed to load asset: {asset_path}")
    return asset


def _load_blueprint_asset(asset_path: str):
    asset = _load_asset(asset_path)
    blueprint_editor_library = getattr(unreal, "BlueprintEditorLibrary", None)
    if blueprint_editor_library is not None:
        blueprint = _safe_call(blueprint_editor_library, "get_blueprint_asset", asset)
        if blueprint:
            return blueprint
    return asset


def _find_event_graph(blueprint):
    blueprint_editor_library = getattr(unreal, "BlueprintEditorLibrary", None)
    if blueprint_editor_library is not None:
        graph = _safe_call(blueprint_editor_library, "find_event_graph", blueprint)
        if graph:
            return graph

    for graph in _safe_get_editor_property(blueprint, "ubergraph_pages", []) or []:
        if _object_name(graph) == "EventGraph":
            return graph

    raise RuntimeError(f"EventGraph not found for {_object_path(blueprint)}")


def _iter_candidate_graphs(blueprint):
    seen = set()

    blueprint_editor_library = getattr(unreal, "BlueprintEditorLibrary", None)
    if blueprint_editor_library is not None:
        graphs = _safe_call(blueprint_editor_library, "get_all_graphs", blueprint) or []
        for graph in graphs:
            graph_path = _object_path(graph)
            if graph and graph_path not in seen:
                seen.add(graph_path)
                yield graph

    for property_name in ("ubergraph_pages", "function_graphs", "delegate_signature_graphs", "macro_graphs"):
        for graph in _safe_get_editor_property(blueprint, property_name, []) or []:
            graph_path = _object_path(graph)
            if graph and graph_path not in seen:
                seen.add(graph_path)
                yield graph


def _is_enhanced_input_node(node) -> bool:
    class_path = _class_path(node)
    if "K2Node_EnhancedInputAction" in class_path:
        return True

    title = str(_safe_call(node, "get_node_title") or "").lower()
    if "enhancedinputaction" in title:
        return True

    for property_name in ("input_action", "InputAction"):
        value = _safe_get_editor_property(node, property_name, default="__missing__")
        if value != "__missing__":
            return True

    return False


def _iter_enhanced_input_nodes(graph):
    for node in _safe_get_editor_property(graph, "nodes", []) or []:
        if _is_enhanced_input_node(node):
            yield node


def _iter_linked_nodes(node):
    seen = set()
    for pin in _safe_get_editor_property(node, "pins", []) or []:
        for linked_pin in getattr(pin, "linked_to", []) or []:
            linked_node = _safe_call(linked_pin, "get_owning_node")
            linked_path = _object_path(linked_node)
            if linked_node and linked_path not in seen:
                seen.add(linked_path)
                yield linked_node


def _collect_node_text(node) -> str:
    parts = []

    title = _safe_call(node, "get_node_title")
    if title:
        parts.append(str(title))

    parts.append(_object_name(node))

    comment = _safe_get_editor_property(node, "node_comment", "")
    if comment:
        parts.append(str(comment))

    for linked_node in _iter_linked_nodes(node):
        linked_title = _safe_call(linked_node, "get_node_title")
        if linked_title:
            parts.append(str(linked_title))
        parts.append(_object_name(linked_node))

    return " | ".join(parts).lower()


def _guess_action_key(blueprint_asset_path: str, node) -> str:
    text = _collect_node_text(node)

    if "handbrake" in text:
        return "handbrake"
    if "brake" in text:
        return "brake"
    if "throttle" in text:
        return "throttle"
    if "steering" in text:
        return "steering"
    if "reset" in text:
        return "reset"
    if "look" in text or "yaw" in text or "pitch" in text:
        return "lookaround"
    if "toggle" in text or "camera" in text or "view" in text:
        return "togglecamera"
    if "headlight" in text or "light" in text:
        return "headlights"

    if blueprint_asset_path == SPORTSCAR_ASSET_PATH:
        return "headlights"

    return ""


def _set_node_input_action(node, action_asset) -> bool:
    if action_asset is None:
        return False

    changed = False

    for property_name in ("input_action", "InputAction"):
        changed = _safe_set_editor_property(node, property_name, action_asset) or changed

    _safe_call(node, "modify")

    for pin in _safe_get_editor_property(node, "pins", []) or []:
        pin_name = str(getattr(pin, "pin_name", "") or _object_name(pin))
        if pin_name == "InputAction":
            try:
                pin.default_object = action_asset
                pin.default_value = _object_name(action_asset)
                changed = True
            except Exception:
                pass

    for method_name in ("reconstruct_node", "post_reconstruct_node", "modify", "post_edit_change"):
        _safe_call(node, method_name)

    return changed


def _compile_and_save_blueprint(blueprint_asset_path: str) -> dict:
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None:
        return {
            "compile_success": False,
            "compile_summary": "BlueprintAutomationPythonBridge is not available.",
            "save_success": False,
            "save_summary": "BlueprintAutomationPythonBridge is not available.",
        }

    compile_success = False
    compile_summary = ""
    compile_report_json = ""
    save_success = False
    save_summary = ""
    save_result_json = ""

    try:
        compile_result = bridge.compile_blueprint(blueprint_asset_path)
        if isinstance(compile_result, tuple):
            for item in compile_result:
                if isinstance(item, bool):
                    compile_success = item
                elif isinstance(item, str):
                    if not compile_report_json:
                        compile_report_json = item
                    else:
                        compile_summary = item
        elif isinstance(compile_result, bool):
            compile_success = compile_result
    except Exception as exc:
        compile_summary = f"compile_blueprint raised: {exc}"

    try:
        save_result = bridge.save_blueprint(blueprint_asset_path)
        if isinstance(save_result, tuple):
            for item in save_result:
                if isinstance(item, bool):
                    save_success = item
                elif isinstance(item, str):
                    if not save_result_json:
                        save_result_json = item
                    else:
                        save_summary = item
        elif isinstance(save_result, bool):
            save_success = save_result
    except Exception as exc:
        save_summary = f"save_blueprint raised: {exc}"

    return {
        "compile_success": compile_success,
        "compile_report_json": compile_report_json,
        "compile_summary": compile_summary,
        "save_success": save_success,
        "save_result_json": save_result_json,
        "save_summary": save_summary,
    }


def fix_blueprint_null_input_actions(blueprint_asset_path: str) -> dict:
    blueprint = _load_blueprint_asset(blueprint_asset_path)

    changes = []
    unresolved = []
    scanned_nodes = []

    for graph in _iter_candidate_graphs(blueprint):
        graph_name = _object_name(graph)
        for node in _iter_enhanced_input_nodes(graph):
            current_action = _safe_get_editor_property(node, "input_action") or _safe_get_editor_property(node, "InputAction")
            scanned_nodes.append(
                {
                    "graph_name": graph_name,
                    "node_name": _object_name(node),
                    "node_path": _object_path(node),
                    "class_path": _class_path(node),
                    "node_title": str(_safe_call(node, "get_node_title") or _object_name(node)),
                    "current_action": _object_path(current_action),
                }
            )

            if current_action:
                continue

            action_key = _guess_action_key(blueprint_asset_path, node)
            action_asset_path = ACTION_ASSET_PATHS.get(action_key, "")
            action_asset = _load_asset(action_asset_path) if action_asset_path else None

            entry = {
                "graph_name": graph_name,
                "node_name": _object_name(node),
                "node_path": _object_path(node),
                "class_path": _class_path(node),
                "node_title": str(_safe_call(node, "get_node_title") or _object_name(node)),
                "guessed_action_key": action_key,
                "action_asset_path": action_asset_path,
                "context": _collect_node_text(node),
            }

            if action_asset and _set_node_input_action(node, action_asset):
                entry["status"] = "fixed"
                changes.append(entry)
            else:
                entry["status"] = "unresolved"
                unresolved.append(entry)

    compile_and_save = _compile_and_save_blueprint(blueprint_asset_path)

    result = {
        "blueprint_asset_path": blueprint_asset_path,
        "scanned_nodes": scanned_nodes,
        "changes": changes,
        "unresolved": unresolved,
        **compile_and_save,
    }

    return result


def fix_vehicle_template_input_nodes(output_dir: str = None) -> dict:
    output_dir = output_dir or _saved_output_dir()

    results = {
        "pawn_base": fix_blueprint_null_input_actions(PAWN_BASE_ASSET_PATH),
        "sportscar": fix_blueprint_null_input_actions(SPORTSCAR_ASSET_PATH),
    }

    results["overall_ok"] = (
        not results["pawn_base"]["unresolved"]
        and not results["sportscar"]["unresolved"]
        and results["pawn_base"]["compile_success"]
        and results["sportscar"]["compile_success"]
        and results["pawn_base"]["save_success"]
        and results["sportscar"]["save_success"]
    )

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, results)
    results["output_path"] = output_path

    if results["overall_ok"]:
        _log(f"VehicleTemplate input nodes fixed successfully. Report: {output_path}")
    else:
        _warn(f"VehicleTemplate input node fix completed with unresolved items. Report: {output_path}")

    return results


if __name__ == "__main__":
    print(fix_vehicle_template_input_nodes())
