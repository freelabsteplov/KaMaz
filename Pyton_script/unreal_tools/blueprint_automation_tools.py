import json
import os

import unreal

"""Thin Python helpers for the BlueprintAutomationEditor bridge.

Usage from Unreal Output Log -> Python:

    import sys
    sys.path.append(r"C:\\Users\\post\\Documents\\Unreal Projects\\Kamaz_Cleaner\\Pyton_script\\unreal_tools")
    import blueprint_automation_tools as bat
    print(bat.run_smoke_test())
    print(bat.inspect_kamazbp_graph())
    print(bat.scan_kamazbp_actions())
    print(bat.compile_kamazbp())
"""

KAMAZ_BP_ASSET_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
BRIDGE = unreal.BlueprintAutomationPythonBridge


def _log(message: str) -> None:
    unreal.log(f"[blueprint_automation_tools] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[blueprint_automation_tools] {message}")


def _normalize_bridge_result(raw_result, expected_string_count: int):
    if isinstance(raw_result, bool):
        return raw_result, [""] * expected_string_count

    if not isinstance(raw_result, tuple):
        raise TypeError(f"Unexpected bridge result type: {type(raw_result)!r}")

    success = None
    strings = []

    for item in raw_result:
        if isinstance(item, bool):
            success = item
        elif isinstance(item, str):
            strings.append(item)

    if success is None:
        raise TypeError(f"Bridge result does not contain a bool status: {raw_result!r}")

    while len(strings) < expected_string_count:
        strings.append("")

    return success, strings[:expected_string_count]


def _call_bridge(method_name: str, *args, expected_string_count: int):
    bridge_method = getattr(BRIDGE, method_name)
    raw_result = bridge_method(*args)
    return _normalize_bridge_result(raw_result, expected_string_count)


def _log_summary(op_name: str, success: bool, summary: str) -> None:
    log_fn = _log if success else _warn
    log_fn(f"{op_name}: {summary}")


def _decode_json(json_payload: str):
    if not json_payload:
        return None
    return json.loads(json_payload)


def _default_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_text_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    _log(f"Wrote file: {path}")


def run_smoke_test():
    success, [summary] = _call_bridge("run_smoke_test", expected_string_count=1)
    _log_summary("run_smoke_test", success, summary)
    return success, summary


def refresh_action_index():
    success, [json_payload, summary] = _call_bridge("refresh_action_index", expected_string_count=2)
    _log_summary("refresh_action_index", success, summary)
    return success, json_payload, summary


def inspect_blueprint_event_graph(
    asset_path: str = KAMAZ_BP_ASSET_PATH,
    include_pins: bool = True,
    include_linked_pins: bool = True,
):
    success, [graph_json, summary] = _call_bridge(
        "inspect_blueprint_event_graph",
        asset_path,
        include_pins,
        include_linked_pins,
        expected_string_count=2,
    )
    _log_summary("inspect_blueprint_event_graph", success, summary)
    return success, graph_json, summary


def inspect_kamazbp_graph(include_pins: bool = True, include_linked_pins: bool = True):
    return inspect_blueprint_event_graph(KAMAZ_BP_ASSET_PATH, include_pins, include_linked_pins)


def scan_blueprint_actions(asset_path: str = KAMAZ_BP_ASSET_PATH, context_sensitive: bool = True):
    success, [index_json, summary] = _call_bridge(
        "scan_blueprint_actions",
        asset_path,
        context_sensitive,
        expected_string_count=2,
    )
    _log_summary("scan_blueprint_actions", success, summary)
    return success, index_json, summary


def scan_kamazbp_actions(context_sensitive: bool = True):
    return scan_blueprint_actions(KAMAZ_BP_ASSET_PATH, context_sensitive)


def compile_blueprint(asset_path: str = KAMAZ_BP_ASSET_PATH):
    success, [report_json, summary] = _call_bridge(
        "compile_blueprint",
        asset_path,
        expected_string_count=2,
    )
    _log_summary("compile_blueprint", success, summary)
    return success, report_json, summary


def compile_kamazbp():
    return compile_blueprint(KAMAZ_BP_ASSET_PATH)


def apply_graph_batch_json(batch_json: str, asset_path: str = KAMAZ_BP_ASSET_PATH):
    success, [result_json, summary] = _call_bridge(
        "apply_graph_batch_json",
        asset_path,
        batch_json,
        expected_string_count=2,
    )
    _log_summary("apply_graph_batch_json", success, summary)
    return success, result_json, summary


def save_blueprint(asset_path: str = KAMAZ_BP_ASSET_PATH):
    success, [summary] = _call_bridge("save_blueprint", asset_path, expected_string_count=1)
    _log_summary("save_blueprint", success, summary)
    return success, summary


def save_kamazbp():
    return save_blueprint(KAMAZ_BP_ASSET_PATH)


def inspect_kamazbp_graph_as_dict(include_pins: bool = True, include_linked_pins: bool = True):
    success, graph_json, summary = inspect_kamazbp_graph(include_pins, include_linked_pins)
    return success, _decode_json(graph_json), summary


def scan_kamazbp_actions_as_dict(context_sensitive: bool = True):
    success, index_json, summary = scan_kamazbp_actions(context_sensitive)
    return success, _decode_json(index_json), summary


def compile_kamazbp_as_dict():
    success, report_json, summary = compile_kamazbp()
    return success, _decode_json(report_json), summary


def export_blueprint_snapshot(asset_path: str = KAMAZ_BP_ASSET_PATH, output_dir: str = None, file_prefix: str = "kamazbp"):
    output_dir = output_dir or _default_output_dir()

    snapshot = {
        "asset_path": asset_path,
        "output_dir": output_dir,
    }

    refresh_success, refresh_json, refresh_summary = refresh_action_index()
    snapshot["refresh_action_index"] = {
        "success": refresh_success,
        "summary": refresh_summary,
    }
    if refresh_json:
        refresh_path = os.path.join(output_dir, f"{file_prefix}_refresh_action_index.json")
        _write_text_file(refresh_path, refresh_json)
        snapshot["refresh_action_index"]["path"] = refresh_path

    graph_success, graph_json, graph_summary = inspect_blueprint_event_graph(asset_path)
    snapshot["graph"] = {
        "success": graph_success,
        "summary": graph_summary,
    }
    if graph_json:
        graph_path = os.path.join(output_dir, f"{file_prefix}_graph.json")
        _write_text_file(graph_path, graph_json)
        snapshot["graph"]["path"] = graph_path

    actions_success, actions_json, actions_summary = scan_blueprint_actions(asset_path)
    snapshot["actions"] = {
        "success": actions_success,
        "summary": actions_summary,
    }
    if actions_json:
        actions_path = os.path.join(output_dir, f"{file_prefix}_actions.json")
        _write_text_file(actions_path, actions_json)
        snapshot["actions"]["path"] = actions_path

    compile_success, compile_json, compile_summary = compile_blueprint(asset_path)
    snapshot["compile"] = {
        "success": compile_success,
        "summary": compile_summary,
    }
    if compile_json:
        compile_path = os.path.join(output_dir, f"{file_prefix}_compile.json")
        _write_text_file(compile_path, compile_json)
        snapshot["compile"]["path"] = compile_path

    return snapshot


def export_kamazbp_snapshot(output_dir: str = None):
    return export_blueprint_snapshot(KAMAZ_BP_ASSET_PATH, output_dir, "kamazbp")


if __name__ == "__main__":
    _log("Loaded blueprint_automation_tools.py")
