import json
import os
import sys

import unreal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

BRIDGE = unreal.BlueprintAutomationPythonBridge
OUTPUT_BASENAME = "apply_persistent_snow_bridge"
PROJECT_DIR = unreal.Paths.project_dir()

PLOW_BLUEPRINT_PATH = "/Game/CityPark/SnowSystem/BP_PlowBrush_Component"
WHEEL_BLUEPRINT_PATH = "/Game/CityPark/SnowSystem/BP_WheelSnowTrace_Component"

PLOW_DRAW_NODE_PATH = (
    "/Game/CityPark/SnowSystem/BP_PlowBrush_Component.BP_PlowBrush_Component:EventGraph.K2Node_CallFunction_3"
)
WHEEL_DRAW_NODE_PATH = (
    "/Game/CityPark/SnowSystem/BP_WheelSnowTrace_Component.BP_WheelSnowTrace_Component:EventGraph.K2Node_CallFunction_5"
)

PLOW_BATCH_PATH = os.path.join(PROJECT_DIR, "Pyton_script", "unreal_tools", "batches", "plowbrush_persistent_snow_bridge.json")
WHEEL_BATCH_PATH = os.path.join(PROJECT_DIR, "Pyton_script", "unreal_tools", "batches", "wheelsnow_persistent_snow_bridge.json")

PLOW_BRIDGE_TOKENS = ("markpersistentplowwriter", "mark persistent plow writer")
WHEEL_BRIDGE_TOKENS = ("markpersistentwheelwriter", "mark persistent wheel writer")


def _log(message: str) -> None:
    unreal.log(f"[apply_persistent_snow_bridge] {message}")


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


def _inspect_graph(asset_path: str):
    raw = BRIDGE.inspect_blueprint_event_graph(asset_path, True, True)
    return _normalize_bridge_result(raw, 2)


def _apply_batch(asset_path: str, batch_json: str):
    raw = BRIDGE.apply_graph_batch_json(asset_path, batch_json)
    return _normalize_bridge_result(raw, 2)


def _compile_blueprint(asset_path: str):
    raw = BRIDGE.compile_blueprint(asset_path)
    return _normalize_bridge_result(raw, 2)


def _save_blueprint(asset_path: str):
    raw = BRIDGE.save_blueprint(asset_path)
    return _normalize_bridge_result(raw, 1)


def _load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _find_node(graph: dict, node_path: str) -> dict | None:
    for node in graph.get("nodes", []) or []:
        if node.get("path") == node_path:
            return node
    return None


def _node_title_matches(node: dict | None, tokens: tuple[str, ...]) -> bool:
    if not node:
        return False
    title = (node.get("title") or "").lower()
    compact = title.replace(" ", "")
    return any(token in title or token.replace(" ", "") in compact for token in tokens)


def _pin_links(node: dict | None, pin_name: str) -> list[dict]:
    if not node:
        return []
    for pin in node.get("pins", []) or []:
        if pin.get("name") == pin_name:
            return list(pin.get("linked_to", []) or [])
    return []


def _has_bridge(graph: dict, draw_node_path: str, bridge_tokens: tuple[str, ...]) -> bool:
    draw_node = _find_node(graph, draw_node_path)
    if draw_node is None:
        return False

    nodes_by_path = {node.get("path"): node for node in graph.get("nodes", []) or []}
    for link in _pin_links(draw_node, "then"):
        target = nodes_by_path.get(link.get("node_path"))
        if _node_title_matches(target, bridge_tokens):
            return True
    return False


def _apply_bridge_to_blueprint(asset_path: str, batch_path: str, draw_node_path: str, bridge_tokens: tuple[str, ...]) -> dict:
    before_success, before_strings = _inspect_graph(asset_path)
    before_graph_json, before_summary = before_strings
    before_graph = _decode_json(before_graph_json) if before_graph_json else None
    if not before_success or before_graph is None:
        raise RuntimeError(f"Could not inspect {asset_path}: {before_summary}")

    already_present = _has_bridge(before_graph, draw_node_path, bridge_tokens)
    result = {
        "asset_path": asset_path,
        "batch_path": batch_path,
        "already_present": already_present,
        "before_then_links": _pin_links(_find_node(before_graph, draw_node_path), "then"),
    }

    if not already_present:
        apply_success, apply_strings = _apply_batch(asset_path, _load_text(batch_path))
        apply_json, apply_summary = apply_strings
        result["apply"] = {
            "success": bool(apply_success),
            "summary": apply_summary,
            "payload": _decode_json(apply_json) if apply_json else None,
        }
        if not apply_success:
            raise RuntimeError(f"apply_graph_batch_json failed for {asset_path}: {apply_summary}")
    else:
        result["apply"] = {
            "success": True,
            "summary": "Bridge already present; no new nodes created.",
            "payload": None,
        }

    compile_success, compile_strings = _compile_blueprint(asset_path)
    compile_json, compile_summary = compile_strings
    result["compile"] = {
        "success": bool(compile_success),
        "summary": compile_summary,
        "payload": _decode_json(compile_json) if compile_json else None,
    }

    save_success, save_strings = _save_blueprint(asset_path)
    result["save"] = {
        "success": bool(save_success),
        "summary": save_strings[0],
    }

    after_success, after_strings = _inspect_graph(asset_path)
    after_graph_json, after_summary = after_strings
    after_graph = _decode_json(after_graph_json) if after_graph_json else None
    result["after_then_links"] = _pin_links(_find_node(after_graph or {}, draw_node_path), "then")
    result["bridge_present_after"] = bool(after_graph) and _has_bridge(after_graph, draw_node_path, bridge_tokens)
    result["graph_inspect_after"] = {
        "success": bool(after_success),
        "summary": after_summary,
    }

    return result


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()

    plow_result = _apply_bridge_to_blueprint(
        PLOW_BLUEPRINT_PATH,
        PLOW_BATCH_PATH,
        PLOW_DRAW_NODE_PATH,
        PLOW_BRIDGE_TOKENS,
    )
    wheel_result = _apply_bridge_to_blueprint(
        WHEEL_BLUEPRINT_PATH,
        WHEEL_BATCH_PATH,
        WHEEL_DRAW_NODE_PATH,
        WHEEL_BRIDGE_TOKENS,
    )

    result = {
        "success": bool(plow_result.get("bridge_present_after")) and bool(wheel_result.get("bridge_present_after")),
        "plow": plow_result,
        "wheel": wheel_result,
    }
    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary() -> str:
    result = run()
    summary = (
        f"persistent_snow_bridge "
        f"plow={result.get('plow', {}).get('bridge_present_after')} "
        f"wheel={result.get('wheel', {}).get('bridge_present_after')} "
        f"success={result.get('success')}"
    )
    _log(summary)
    _log(f"summary_path={result.get('output_path', '')}")
    return summary


if __name__ == "__main__":
    print(run())
