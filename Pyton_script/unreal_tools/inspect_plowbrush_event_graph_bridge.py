import json
import os

import unreal


ASSET_PATH = "/Game/CityPark/SnowSystem/BP_PlowBrush_Component"
GRAPH_NAME = "EventGraph"
OUTPUT_BASENAME = "plowbrush_event_graph"


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_text(path: str, text: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    unreal.log(f"[inspect_plowbrush_event_graph_bridge] Wrote file: {path}")
    return path


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    unreal.log(f"[inspect_plowbrush_event_graph_bridge] Wrote file: {path}")
    return path


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None or not hasattr(bridge, "inspect_blueprint_graph"):
        raise RuntimeError("BlueprintAutomationPythonBridge.inspect_blueprint_graph is not available")

    raw_result = bridge.inspect_blueprint_graph(ASSET_PATH, GRAPH_NAME, True, True)
    tuple_items = []
    for item in raw_result if isinstance(raw_result, tuple) else [raw_result]:
        tuple_items.append({"type": str(type(item)), "repr": str(item)[:500]})

    json_text = ""
    for item in raw_result if isinstance(raw_result, tuple) else [raw_result]:
        if isinstance(item, str) and item.strip().startswith("{"):
            json_text = item
            break

    if not json_text:
        raise RuntimeError(f"Could not find JSON payload in bridge result: {tuple_items}")

    json_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    debug_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}_bridge_debug.json")
    _write_text(json_path, json_text)
    _write_json(debug_path, {"tuple_items": tuple_items})
    return {"json_path": json_path, "debug_path": debug_path}


if __name__ == "__main__":
    print(run())
