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

ACTION_TEMPLATE_SOURCE_PATHS = {
    "throttle": "/Game/SnappyRoads/Blueprints/Vehicle/Input/Actions/IA_Throttle",
    "steering": "/Game/SnappyRoads/Blueprints/Vehicle/Input/Actions/IA_Steering",
    "brake": "/Game/SnappyRoads/Blueprints/Vehicle/Input/Actions/IA_Throttle",
    "handbrake": "/Game/SnappyRoads/Blueprints/Vehicle/Input/Actions/IA_Handbrake",
    "reset": "/Game/SnappyRoads/Blueprints/Vehicle/Input/Actions/IA_Handbrake",
    "lookaround": "/Game/SnappyRoads/Blueprints/Vehicle/Input/Actions/IA_LookAround",
    "togglecamera": "/Game/SnappyRoads/Blueprints/Vehicle/Input/Actions/IA_SwitchCamera",
    "headlights": "/Game/SnappyRoads/Blueprints/Vehicle/Input/Actions/IA_Handbrake",
}

ACTION_VALUE_TYPES = {
    "throttle": "AXIS1D",
    "steering": "AXIS1D",
    "brake": "AXIS1D",
    "handbrake": "BOOLEAN",
    "reset": "BOOLEAN",
    "lookaround": "AXIS2D",
    "togglecamera": "BOOLEAN",
    "headlights": "BOOLEAN",
}

OUTPUT_BASENAME = "vehicle_template_input_fix"
PAWN_BASE_NODE_NAME_FALLBACK_ACTIONS = {
    "K2Node_EnhancedInputAction_0": "throttle",
    "K2Node_EnhancedInputAction_1": "brake",
    "K2Node_EnhancedInputAction_2": "handbrake",
    "K2Node_EnhancedInputAction_3": "lookaround",
    "K2Node_EnhancedInputAction_5": "reset",
    "K2Node_EnhancedInputAction_6": "steering",
    "K2Node_EnhancedInputAction_7": "togglecamera",
}

PAWN_BASE_AXIS_VALUE_REWIRES = [
    {
        "source_node_name": "K2Node_EnhancedInputAction_0",
        "source_pin": "ActionValue",
        "disconnect_targets": [
            {
                "node_name": "K2Node_CallFunction_14",
                "pin_name": "InBool",
            }
        ],
        "connect_targets": [
            {
                "node_name": "K2Node_CallFunction_30",
                "pin_name": "Throttle",
            }
        ],
    },
    {
        "source_node_name": "K2Node_EnhancedInputAction_1",
        "source_pin": "ActionValue",
        "disconnect_targets": [
            {
                "node_name": "K2Node_CallFunction_24",
                "pin_name": "InBool",
            },
            {
                "node_name": "K2Node_CallFunction_25",
                "pin_name": "InBool",
            },
        ],
        "connect_targets": [
            {
                "node_name": "K2Node_CallFunction_39",
                "pin_name": "Brake",
            },
            {
                "node_name": "K2Node_CallFunction_31",
                "pin_name": "Brake",
            },
        ],
    },
    {
        "source_node_name": "K2Node_EnhancedInputAction_6",
        "source_pin": "ActionValue",
        "disconnect_targets": [
            {
                "node_name": "K2Node_CallFunction_37",
                "pin_name": "InBool",
            }
        ],
        "connect_targets": [
            {
                "node_name": "K2Node_CallFunction_34",
                "pin_name": "Steering",
            }
        ],
    },
]

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


def _action_key_from_text(text: str) -> str:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return ""

    if "handbrake" in normalized:
        return "handbrake"
    if "headlight" in normalized or "headlights" in normalized:
        return "headlights"
    if "steering" in normalized:
        return "steering"
    if "throttle" in normalized:
        return "throttle"
    if "brake" in normalized:
        return "brake"
    if "reset" in normalized:
        return "reset"
    if "lookaround" in normalized or "look around" in normalized or "yaw" in normalized or "pitch" in normalized:
        return "lookaround"
    if (
        "togglecamera" in normalized
        or "toggle camera" in normalized
        or "switchcamera" in normalized
        or "switch camera" in normalized
        or "camera" in normalized
        or "view" in normalized
    ):
        return "togglecamera"

    return ""


def _ensure_asset_directory(asset_path: str) -> None:
    package_path, _ = asset_path.rsplit("/", 1)
    try:
        unreal.EditorAssetLibrary.make_directory(package_path)
    except Exception:
        pass


def _resolve_input_action_value_type(enum_name: str):
    if not enum_name:
        return None

    enum_obj = getattr(unreal, "InputActionValueType", None)
    if enum_obj is None:
        return None

    return getattr(enum_obj, enum_name, None)


def _set_input_action_value_type(asset, action_key: str) -> bool:
    desired_enum_name = ACTION_VALUE_TYPES.get(action_key, "")
    desired_value = _resolve_input_action_value_type(desired_enum_name)
    if asset is None or desired_value is None:
        return False

    try:
        asset.set_editor_property("value_type", desired_value)
        return True
    except Exception:
        return False


def _ensure_action_asset(action_key: str) -> dict:
    target_asset_path = ACTION_ASSET_PATHS.get(action_key, "")
    source_asset_path = ACTION_TEMPLATE_SOURCE_PATHS.get(action_key, "")
    result = {
        "action_key": action_key,
        "target_asset_path": target_asset_path,
        "source_asset_path": source_asset_path,
        "created": False,
        "loaded": False,
        "saved": False,
        "value_type_set": False,
        "error": "",
    }

    if not target_asset_path:
        result["error"] = "missing_target_asset_path"
        return result

    try:
        asset = unreal.EditorAssetLibrary.load_asset(target_asset_path)
    except Exception:
        asset = None

    if asset is None:
        if not source_asset_path:
            result["error"] = "missing_source_asset_path"
            return result

        if not unreal.EditorAssetLibrary.does_asset_exist(source_asset_path):
            result["error"] = f"missing_source_asset: {source_asset_path}"
            return result

        _ensure_asset_directory(target_asset_path)

        if not unreal.EditorAssetLibrary.duplicate_asset(source_asset_path, target_asset_path):
            result["error"] = f"duplicate_asset_failed: {source_asset_path} -> {target_asset_path}"
            return result

        result["created"] = True
        try:
            asset = _load_asset(target_asset_path)
        except Exception as exc:
            result["error"] = f"load_after_duplicate_failed: {exc}"
            return result

    result["loaded"] = asset is not None
    result["value_type_set"] = _set_input_action_value_type(asset, action_key)

    try:
        result["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(asset, False))
    except Exception:
        try:
            result["saved"] = bool(unreal.EditorAssetLibrary.save_asset(target_asset_path, False))
        except Exception as exc:
            result["error"] = f"save_failed: {exc}"

    if asset is None and not result["error"]:
        result["error"] = "asset_not_loaded"

    return result


def _normalize_bridge_result(raw_result, expected_string_count: int):
    strings = []
    success = None

    if isinstance(raw_result, bool):
        success = raw_result
    elif isinstance(raw_result, str):
        strings.append(raw_result)
        success = True
    elif isinstance(raw_result, tuple):
        for item in raw_result:
            if isinstance(item, bool):
                success = item
            elif isinstance(item, str):
                strings.append(item)

        if success is None:
            success = len(strings) > 0
    else:
        success = False

    while len(strings) < expected_string_count:
        strings.append("")

    return bool(success), strings[:expected_string_count]


def _load_object_by_path(object_path: str):
    if not object_path:
        return None

    loader = getattr(unreal, "load_object", None)
    if loader is not None:
        try:
            return loader(None, object_path)
        except Exception:
            pass

    finder = getattr(unreal, "find_object", None)
    if finder is not None:
        try:
            return finder(None, object_path)
        except Exception:
            try:
                return finder(name=object_path)
            except Exception:
                pass

    return None


def _inspect_event_graph_nodes(blueprint_asset_path: str):
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None:
        return False, [], "BlueprintAutomationPythonBridge is not available."

    try:
        raw_result = bridge.inspect_blueprint_event_graph(blueprint_asset_path, True, True)
    except Exception as exc:
        return False, [], f"inspect_blueprint_event_graph raised: {exc}"

    success, [graph_json, summary] = _normalize_bridge_result(raw_result, 2)
    if not success or not graph_json:
        return False, [], summary

    try:
        graph_payload = json.loads(graph_json)
    except Exception as exc:
        return False, [], f"Failed to parse inspect graph JSON: {exc}"

    return True, graph_payload.get("nodes", []), summary


def _node_snapshot_is_enhanced_input(node_snapshot: dict) -> bool:
    class_path = str(node_snapshot.get("class", ""))
    title = str(node_snapshot.get("title", ""))
    return "K2Node_EnhancedInputAction" in class_path or "EnhancedInputAction" in title


def _snapshot_current_action_object_path(node_snapshot: dict) -> str:
    for pin in node_snapshot.get("pins", []):
        if str(pin.get("name", "")) == "InputAction":
            return str(pin.get("default_object", "") or "")
    return ""


def _collect_snapshot_context(node_snapshot: dict, nodes_by_name: dict) -> str:
    parts = [
        str(node_snapshot.get("title", "")),
        str(node_snapshot.get("name", "")),
        str(node_snapshot.get("comment", "")),
    ]

    for pin in node_snapshot.get("pins", []):
        for linked in pin.get("linked_to", []):
            linked_name = str(linked.get("node_name", ""))
            parts.append(linked_name)
            linked_node = nodes_by_name.get(linked_name) or {}
            parts.append(str(linked_node.get("title", "")))
            parts.append(str(linked_node.get("comment", "")))

    return " | ".join([p for p in parts if p]).lower()


def _guess_action_key_from_snapshot(blueprint_asset_path: str, node_snapshot: dict, nodes_by_name: dict) -> str:
    current_action_path = _snapshot_current_action_object_path(node_snapshot)
    for candidate_text in (
        current_action_path,
        str(node_snapshot.get("title", "")),
        _collect_snapshot_context(node_snapshot, nodes_by_name),
    ):
        action_key = _action_key_from_text(candidate_text)
        if action_key:
            return action_key

    node_name = str(node_snapshot.get("name", ""))
    if blueprint_asset_path == PAWN_BASE_ASSET_PATH:
        return PAWN_BASE_NODE_NAME_FALLBACK_ACTIONS.get(node_name, "")

    if blueprint_asset_path == SPORTSCAR_ASSET_PATH:
        return "headlights"

    return ""


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
        event_graph = _safe_call(blueprint_editor_library, "find_event_graph", blueprint)
        if event_graph:
            graph_path = _object_path(event_graph)
            if graph_path not in seen:
                seen.add(graph_path)
                yield event_graph

        # UE 5.7 Python API may not expose get_all_graphs / graph arrays on Blueprint.
        # Keep best-effort call for engines that still expose it.
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
    for candidate_text in (
        _object_path(_safe_get_editor_property(node, "input_action", None)),
        _object_path(_safe_get_editor_property(node, "InputAction", None)),
        _safe_call(node, "get_node_title"),
        _collect_node_text(node),
    ):
        action_key = _action_key_from_text(candidate_text)
        if action_key:
            return action_key

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
        compile_success, [compile_report_json, compile_summary] = _normalize_bridge_result(compile_result, 2)
        if compile_report_json:
            try:
                report = json.loads(compile_report_json)
                report_status = str(report.get("status", "")).lower()
                if report_status == "error":
                    compile_success = False
                elif report_status in ("success", "up_to_date"):
                    compile_success = True
            except Exception:
                pass
    except Exception as exc:
        compile_summary = f"compile_blueprint raised: {exc}"

    try:
        save_result = bridge.save_blueprint(blueprint_asset_path)
        save_success, save_strings = _normalize_bridge_result(save_result, 2)
        if save_strings:
            save_result_json = save_strings[0]
        if len(save_strings) > 1:
            save_summary = save_strings[1]
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


def _apply_enhanced_input_actions_by_node(blueprint_asset_path: str, node_actions: list):
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None:
        return False, {}, "BlueprintAutomationPythonBridge is not available."

    bridge_method = getattr(bridge, "set_enhanced_input_actions_by_node", None)
    if bridge_method is None:
        return False, {}, "set_enhanced_input_actions_by_node bridge method is not available."

    payload = {"node_actions": node_actions}

    try:
        raw_result = bridge_method(blueprint_asset_path, json.dumps(payload, ensure_ascii=False))
    except Exception as exc:
        return False, {}, f"set_enhanced_input_actions_by_node raised: {exc}"

    success, [result_json, summary] = _normalize_bridge_result(raw_result, 2)

    result_payload = {}
    if result_json:
        try:
            result_payload = json.loads(result_json)
        except Exception:
            result_payload = {}

    return success, result_payload, summary


def _rewire_graph_pin_links_by_node(blueprint_asset_path: str, rewires: list):
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None:
        return False, {}, "BlueprintAutomationPythonBridge is not available."

    bridge_method = getattr(bridge, "rewire_graph_pin_links_by_node", None)
    if bridge_method is None:
        return False, {}, "rewire_graph_pin_links_by_node bridge method is not available."

    payload = {"rewires": rewires}

    try:
        raw_result = bridge_method(blueprint_asset_path, json.dumps(payload, ensure_ascii=False))
    except Exception as exc:
        return False, {}, f"rewire_graph_pin_links_by_node raised: {exc}"

    success, [result_json, summary] = _normalize_bridge_result(raw_result, 2)

    result_payload = {}
    if result_json:
        try:
            result_payload = json.loads(result_json)
        except Exception:
            result_payload = {}

    return success, result_payload, summary


def fix_blueprint_null_input_actions(blueprint_asset_path: str) -> dict:
    _load_blueprint_asset(blueprint_asset_path)

    changes = []
    unresolved = []
    scanned_nodes = []
    ensured_action_assets = []
    ensured_action_assets_by_key = {}
    inspect_success, node_snapshots, inspect_summary = _inspect_event_graph_nodes(blueprint_asset_path)
    nodes_by_name = {str(node.get("name", "")): node for node in node_snapshots}
    pending_entries = []
    pending_node_actions = []
    apply_success = False
    apply_summary = ""
    apply_result_payload = {}
    rewire_success = False
    rewire_summary = ""
    rewire_result_payload = {}

    if inspect_success:
        for node_snapshot in node_snapshots:
            if not _node_snapshot_is_enhanced_input(node_snapshot):
                continue

            node_name = str(node_snapshot.get("name", ""))
            node_path = str(node_snapshot.get("path", ""))
            class_path = str(node_snapshot.get("class", ""))
            node_title = str(node_snapshot.get("title", ""))
            current_action_path = _snapshot_current_action_object_path(node_snapshot)

            scanned_nodes.append(
                {
                    "graph_name": "EventGraph",
                    "node_name": node_name,
                    "node_path": node_path,
                    "class_path": class_path,
                    "node_title": node_title,
                    "current_action": current_action_path,
                }
            )

            action_key = _guess_action_key_from_snapshot(blueprint_asset_path, node_snapshot, nodes_by_name)
            action_asset_path = ACTION_ASSET_PATHS.get(action_key, "")

            entry = {
                "graph_name": "EventGraph",
                "node_name": node_name,
                "node_path": node_path,
                "class_path": class_path,
                "node_title": node_title,
                "guessed_action_key": action_key,
                "action_asset_path": action_asset_path,
                "current_action": current_action_path,
                "context": _collect_snapshot_context(node_snapshot, nodes_by_name),
            }

            if not action_asset_path:
                if current_action_path:
                    continue
                entry["status"] = "unresolved"
                entry["reason"] = "action_key_not_resolved"
                unresolved.append(entry)
                continue

            ensure_result = ensured_action_assets_by_key.get(action_key)
            if ensure_result is None:
                ensure_result = _ensure_action_asset(action_key)
                ensured_action_assets_by_key[action_key] = ensure_result
                ensured_action_assets.append(ensure_result)
            if ensure_result.get("error"):
                entry["status"] = "unresolved"
                entry["reason"] = ensure_result["error"]
                unresolved.append(entry)
                continue

            entry["repair_mode"] = "refresh_existing_action" if current_action_path else "repair_null_action"
            pending_entries.append(entry)
            pending_node_actions.append(
                {
                    "node_name": node_name,
                    "action_asset_path": action_asset_path,
                }
            )

        if pending_node_actions:
            apply_success, apply_result_payload, apply_summary = _apply_enhanced_input_actions_by_node(
                blueprint_asset_path, pending_node_actions
            )
            per_node_results = {
                str(item.get("node_name", "")): item for item in apply_result_payload.get("results", []) if item
            }
            for entry in pending_entries:
                node_name = entry.get("node_name", "")
                node_result = per_node_results.get(node_name, {})
                if bool(node_result.get("applied", False)):
                    entry["status"] = "refreshed" if entry.get("current_action") else "fixed"
                    changes.append(entry)
                else:
                    entry["status"] = "unresolved"
                    entry["reason"] = str(node_result.get("reason", "bridge_apply_failed"))
                    unresolved.append(entry)
    else:
        unresolved.append(
            {
                "graph_name": "EventGraph",
                "node_name": "",
                "node_path": "",
                "class_path": "",
                "node_title": "",
                "guessed_action_key": "",
                "action_asset_path": "",
                "context": "",
                "status": "unresolved",
                "reason": f"inspect_failed: {inspect_summary}",
            }
        )

    if blueprint_asset_path == PAWN_BASE_ASSET_PATH:
        rewire_success, rewire_result_payload, rewire_summary = _rewire_graph_pin_links_by_node(
            blueprint_asset_path, PAWN_BASE_AXIS_VALUE_REWIRES
        )

    compile_and_save = _compile_and_save_blueprint(blueprint_asset_path)

    result = {
        "blueprint_asset_path": blueprint_asset_path,
        "inspect_success": inspect_success,
        "inspect_summary": inspect_summary,
        "apply_success": apply_success,
        "apply_summary": apply_summary,
        "apply_result": apply_result_payload,
        "rewire_success": rewire_success,
        "rewire_summary": rewire_summary,
        "rewire_result": rewire_result_payload,
        "scanned_nodes": scanned_nodes,
        "ensured_action_assets": ensured_action_assets,
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
