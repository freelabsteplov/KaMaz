import json
import os
import sys

import unreal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

BLUEPRINT_PATH = "/Game/CityPark/SnowSystem/BP_PlowBrush_Component"
BATCH_PATH = os.path.join(
    unreal.Paths.project_dir(),
    "Pyton_script",
    "unreal_tools",
    "batches",
    "plowbrush_beginplay_owner_fallback.json",
)
OUTPUT_BASENAME = "apply_plowbrush_beginplay_owner_fallback"
BEGINPLAY_NODE_PATH = (
    "/Game/CityPark/SnowSystem/BP_PlowBrush_Component.BP_PlowBrush_Component:EventGraph.K2Node_Event_0"
)
BRIDGE = unreal.BlueprintAutomationPythonBridge


def _log(message: str) -> None:
    unreal.log(f"[apply_plowbrush_beginplay_owner_fallback] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[apply_plowbrush_beginplay_owner_fallback] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _decode_json(payload: str):
    if not payload:
        return None
    return json.loads(payload)


def _normalize_bridge_result(raw_result, expected_string_count: int):
    if isinstance(raw_result, bool):
        return raw_result, [""] * expected_string_count

    if isinstance(raw_result, str):
        strings = [raw_result]
        while len(strings) < expected_string_count:
            strings.append("")
        return True, strings[:expected_string_count]

    if isinstance(raw_result, tuple):
        success = None
        strings = []
        for item in raw_result:
            if isinstance(item, bool):
                success = item
            elif isinstance(item, str):
                strings.append(item)
        if success is None:
            success = True
        while len(strings) < expected_string_count:
            strings.append("")
        return success, strings[:expected_string_count]

    raise TypeError(f"Unexpected bridge result: {type(raw_result)!r} {raw_result!r}")


def _inspect_graph():
    raw = BRIDGE.inspect_blueprint_event_graph(BLUEPRINT_PATH, True, True)
    return _normalize_bridge_result(raw, 2)


def _apply_batch(batch_json: str):
    raw = BRIDGE.apply_graph_batch_json(BLUEPRINT_PATH, batch_json)
    return _normalize_bridge_result(raw, 2)


def _compile_blueprint():
    raw = BRIDGE.compile_blueprint(BLUEPRINT_PATH)
    return _normalize_bridge_result(raw, 2)


def _save_blueprint():
    raw = BRIDGE.save_blueprint(BLUEPRINT_PATH)
    return _normalize_bridge_result(raw, 1)


def _load_batch_json() -> str:
    with open(BATCH_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def _get_graph_dict() -> dict:
    success, strings = _inspect_graph()
    graph_json, summary = strings
    return {
        "success": bool(success),
        "summary": summary,
        "graph": _decode_json(graph_json) if graph_json else None,
    }


def _find_node(graph: dict, node_path: str) -> dict | None:
    for node in graph.get("nodes", []) or []:
        if node.get("path") == node_path:
            return node
    return None


def _pin_links(node: dict, pin_name: str) -> list[dict]:
    for pin in node.get("pins", []) or []:
        if pin.get("name") == pin_name:
            return list(pin.get("linked_to", []) or [])
    return []


def _has_beginplay_owner_fallback(graph: dict) -> bool:
    event_node = _find_node(graph, BEGINPLAY_NODE_PATH)
    if not event_node:
        return False

    begin_links = _pin_links(event_node, "then")
    if not begin_links:
        return False

    nodes_by_path = {node.get("path"): node for node in graph.get("nodes", []) or []}
    nodes_by_name = {node.get("name"): node for node in graph.get("nodes", []) or []}

    for link in begin_links:
        target = nodes_by_path.get(link.get("node_path")) or nodes_by_name.get(link.get("node_name"))
        if not target or target.get("title") != "Cast To Pawn":
            continue

        object_links = _pin_links(target, "Object")
        then_links = _pin_links(target, "then")
        as_pawn_links = _pin_links(target, "AsPawn")

        has_get_owner = False
        for object_link in object_links:
            source = nodes_by_path.get(object_link.get("node_path")) or nodes_by_name.get(object_link.get("node_name"))
            if source and source.get("title") == "Get Owner":
                has_get_owner = True
                break

        has_owner_vehicle_set = False
        for exec_link in then_links:
            target_set = nodes_by_path.get(exec_link.get("node_path")) or nodes_by_name.get(exec_link.get("node_name"))
            if not target_set or target_set.get("title") != "Set OwnerVehicle":
                continue
            owner_links = _pin_links(target_set, "OwnerVehicle")
            if any(owner_link.get("node_name") == target.get("name") and owner_link.get("pin_name") == "AsPawn" for owner_link in owner_links):
                has_owner_vehicle_set = True
                break

        if has_get_owner and has_owner_vehicle_set and as_pawn_links:
            return True

    return False


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    batch_json = _load_batch_json()

    before_graph = _get_graph_dict()
    if not before_graph["success"] or before_graph["graph"] is None:
        raise RuntimeError(f"Could not inspect {BLUEPRINT_PATH}: {before_graph['summary']}")

    already_present = _has_beginplay_owner_fallback(before_graph["graph"])

    result = {
        "success": True,
        "blueprint_path": BLUEPRINT_PATH,
        "batch_path": BATCH_PATH,
        "already_present": already_present,
        "before_beginplay_then_links": _pin_links(_find_node(before_graph["graph"], BEGINPLAY_NODE_PATH) or {}, "then"),
    }

    if not already_present:
        apply_success, strings = _apply_batch(batch_json)
        apply_json, apply_summary = strings
        result["apply"] = {
            "success": bool(apply_success),
            "summary": apply_summary,
            "payload": _decode_json(apply_json) if apply_json else None,
        }
        if not apply_success:
            raise RuntimeError(f"apply_graph_batch_json failed: {apply_summary}")
    else:
        result["apply"] = {
            "success": True,
            "summary": "BeginPlay owner fallback already present; no new nodes created.",
            "payload": None,
        }

    compile_success, strings = _compile_blueprint()
    compile_json, compile_summary = strings
    result["compile"] = {
        "success": bool(compile_success),
        "summary": compile_summary,
        "payload": _decode_json(compile_json) if compile_json else None,
    }

    save_success, strings = _save_blueprint()
    save_summary = strings[0]
    result["save"] = {
        "success": bool(save_success),
        "summary": save_summary,
    }

    after_graph = _get_graph_dict()
    result["after_beginplay_then_links"] = _pin_links(_find_node(after_graph["graph"], BEGINPLAY_NODE_PATH) or {}, "then")
    result["fallback_present_after"] = bool(after_graph["graph"]) and _has_beginplay_owner_fallback(after_graph["graph"])
    result["graph_inspect_after"] = {
        "success": bool(after_graph["success"]),
        "summary": after_graph["summary"],
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary() -> str:
    result = run()
    summary = (
        f"plowbrush_beginplay_owner_fallback "
        f"already_present={result.get('already_present')} "
        f"fallback_present_after={result.get('fallback_present_after')} "
        f"compiled={result.get('compile', {}).get('success')} "
        f"saved={result.get('save', {}).get('success')}"
    )
    _log(summary)
    _log(f"summary_path={result.get('output_path', '')}")
    return summary


if __name__ == "__main__":
    print(run())
