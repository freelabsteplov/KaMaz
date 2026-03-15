import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import rebuild_visible_road_snow_receiver as rr
import apply_receiver_to_spawn_zone_roads as apply_spawn_roads


OUTPUT_BASENAME = "rebuild_road_receiver_direct_rt_debug"


def _log(message: str) -> None:
    unreal.log(f"[rebuild_road_receiver_direct_rt_debug] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    module = importlib.reload(rr)
    module.DEBUG_DIRECT_RT_VIS = True
    module.DEBUG_FORCE_SOLID_COLOR = False

    result = module.run(output_dir)
    spawn_apply_result = apply_spawn_roads.run(output_dir)
    payload = {
        "success": bool(result.get("success", False) and spawn_apply_result.get("success", False)),
        "summary": result.get("summary", ""),
        "mode": "direct_rt_debug",
        "rebuild_output_path": result.get("output_path", ""),
        "spawn_zone_apply_output_path": spawn_apply_result.get("output_path", ""),
        "spawn_zone_total_components_updated": spawn_apply_result.get("total_components_updated", 0),
        "notes": [
            "This is a temporary direct RT visualization mode for the isolated road receiver.",
            "It should show RT writes on the spawn-zone road actors directly as emissive debug color.",
            "Use this only to validate that the plow writer reaches the road receiver visually.",
        ],
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, payload)
    payload["output_path"] = output_path
    return payload


def print_summary(output_dir: str | None = None):
    payload = run(output_dir)
    _log(payload["summary"])
    _log(f"summary_path={payload['output_path']}")
    return {
        "success": payload.get("success", False),
        "summary": payload.get("summary", ""),
        "output_path": payload.get("output_path", ""),
    }


if __name__ == "__main__":
    print_summary()
