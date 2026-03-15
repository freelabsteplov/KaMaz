import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import apply_test_zone_snow_bounds as atzsb
import rebuild_visible_road_snow_receiver as rvsr
import capture_road_receiver_after_stamp as crrs


OUTPUT_BASENAME = "run_road_receiver_debug_chain"


def _log(message: str) -> None:
    unreal.log(f"[run_road_receiver_debug_chain] {message}")


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

    global atzsb, rvsr, crrs
    atzsb = importlib.reload(atzsb)
    rvsr = importlib.reload(rvsr)
    crrs = importlib.reload(crrs)

    result = {
        "success": False,
        "steps": {},
    }

    bounds_result = atzsb.run(output_dir)
    rebuild_result = rvsr.run(output_dir)
    capture_result = crrs.run(output_dir)

    result["steps"]["apply_test_zone_snow_bounds"] = bounds_result
    result["steps"]["rebuild_visible_road_snow_receiver"] = rebuild_result
    result["steps"]["capture_road_receiver_after_stamp"] = capture_result
    result["success"] = bool(
        bounds_result.get("success")
        and rebuild_result.get("success")
        and capture_result.get("success")
    )
    result["summary"] = (
        f"road_receiver_debug_chain success={result['success']} "
        f"exports_equal={capture_result.get('capture_exports_equal')} "
        f"center_equal={capture_result.get('capture_center_equal')} "
        f"quarter_equal={capture_result.get('capture_quarter_equal')}"
    )

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(run())
