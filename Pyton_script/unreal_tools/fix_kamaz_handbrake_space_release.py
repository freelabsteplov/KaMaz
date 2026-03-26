import json
import os

import unreal


BP_PATH = "/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit"
OUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "fix_kamaz_handbrake_space_release.json",
)

NODE_SET_START_BRAKE_FALSE = (
    "/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit."
    "KamazBP_HandlingAudit:EventGraph.K2Node_VariableSet_28"
)
NODE_SET_HANDBRAKE_FALSE = (
    "/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit."
    "KamazBP_HandlingAudit:EventGraph.K2Node_CallFunction_14"
)


def norm_bridge(raw, expected=2):
    success = None
    strings = []
    if isinstance(raw, tuple):
        for item in raw:
            if isinstance(item, bool):
                success = item
            elif isinstance(item, str):
                strings.append(item)
    elif isinstance(raw, bool):
        success = raw
    elif isinstance(raw, str):
        strings.append(raw)

    if success is None:
        success = True if strings else False
    while len(strings) < expected:
        strings.append("")
    return bool(success), strings[:expected]


def decode_json(payload):
    if not payload:
        return None
    try:
        return json.loads(payload)
    except Exception:
        return None


def apply_graph_batch(bp_path, batch):
    raw = unreal.BlueprintAutomationPythonBridge.apply_graph_batch_json(
        bp_path,
        json.dumps(batch, ensure_ascii=False),
    )
    success, strings = norm_bridge(raw, 2)
    payload_json, summary = strings
    return {
        "success": bool(success),
        "summary": summary,
        "payload": decode_json(payload_json),
    }


def compile_blueprint(bp_path):
    raw = unreal.BlueprintAutomationPythonBridge.compile_blueprint(bp_path)
    success, strings = norm_bridge(raw, 2)
    report_json, summary = strings
    report = decode_json(report_json)
    compile_ok = bool(success)
    if isinstance(report, dict) and int(report.get("num_errors", 0) or 0) > 0:
        compile_ok = False
    return compile_ok, summary, report


def save_blueprint(bp_path):
    raw = unreal.BlueprintAutomationPythonBridge.save_blueprint(bp_path)
    success, strings = norm_bridge(raw, 1)
    return bool(success), strings[0]


result = {
    "bp_path": BP_PATH,
    "graph_patch": {},
    "bp_compile": {},
    "bp_save": {},
    "error": "",
}

try:
    # Route the explicit Space/manual release path into SetHandbrakeInput(false).
    # This also replaces the old Completed->false link on that node's exec input.
    batch = {
        "nodes": [],
        "links": [
            {
                "from_node_path": NODE_SET_START_BRAKE_FALSE,
                "from_pin": "then",
                "to_node_path": NODE_SET_HANDBRAKE_FALSE,
                "to_pin": "execute",
            }
        ],
        "execution_chains": [],
    }

    apply_result = apply_graph_batch(BP_PATH, batch)
    result["graph_patch"] = apply_result
    if not apply_result.get("success"):
        raise RuntimeError(f"Graph patch failed: {apply_result.get('summary')}")

    compile_ok, compile_summary, compile_report = compile_blueprint(BP_PATH)
    result["bp_compile"] = {
        "success": compile_ok,
        "summary": compile_summary,
        "report": compile_report,
    }
    if not compile_ok:
        raise RuntimeError(f"Blueprint compile failed: {compile_summary}")

    save_ok, save_summary = save_blueprint(BP_PATH)
    result["bp_save"] = {
        "success": save_ok,
        "summary": save_summary,
    }
    if not save_ok:
        raise RuntimeError(f"Blueprint save failed: {save_summary}")

except Exception as exc:
    result["error"] = str(exc)

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, ensure_ascii=False)

print(OUT_PATH)
