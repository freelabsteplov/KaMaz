import json
import os

import unreal


ASSET = "/Game/VehicleTemplate/Blueprints/BP_VehicleAdvPawnBase"
OUT = os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation", "bp_vehicleadvpawnbase_eventgraph.json")


def _norm(raw, n):
    if raw is None:
        return False, [""] * n
    if isinstance(raw, bool):
        return raw, [""] * n
    if isinstance(raw, str):
        arr = [raw]
        while len(arr) < n:
            arr.append("")
        return True, arr[:n]
    if isinstance(raw, tuple):
        success = None
        arr = []
        for item in raw:
            if isinstance(item, bool):
                success = item
            elif isinstance(item, str):
                arr.append(item)
        if success is None:
            success = True
        while len(arr) < n:
            arr.append("")
        return bool(success), arr[:n]
    return False, [""] * n


bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
if bridge is None:
    raise RuntimeError("BlueprintAutomationPythonBridge is unavailable.")

raw = bridge.inspect_blueprint_event_graph(ASSET, True, True)
ok, parts = _norm(raw, 2)
graph_json, summary = parts

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as handle:
    handle.write(graph_json or "{}")

print(
    json.dumps(
        {
            "asset": ASSET,
            "ok": ok,
            "summary": summary,
            "output": OUT,
            "graph_len": len(graph_json or ""),
        },
        ensure_ascii=False,
    )
)
