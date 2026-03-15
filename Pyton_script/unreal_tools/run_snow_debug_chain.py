import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import apply_plow_debug_overdrive as apdo
import rebuild_visible_road_snow_receiver as rvsr
import inspect_snow_component_defaults as iscd
import inspect_kamaz_named_components as iknc


OUTPUT_BASENAME = "run_snow_debug_chain"


def _log(message: str) -> None:
    unreal.log(f"[run_snow_debug_chain] {message}")


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

    global apdo, rvsr, iscd, iknc
    apdo = importlib.reload(apdo)
    rvsr = importlib.reload(rvsr)
    iscd = importlib.reload(iscd)
    iknc = importlib.reload(iknc)

    result = {
        "success": False,
        "steps": {},
    }

    plow_result = apdo.run(output_dir)
    road_result = rvsr.run(output_dir)

    inspect_defaults_result = None
    inspect_kamaz_result = None
    try:
        inspect_defaults_result = iscd.run_inspection(output_dir)
    except Exception as exc:
        inspect_defaults_result = {"error": str(exc)}

    try:
        inspect_kamaz_result = iknc.inspect_named_components(output_dir)
    except Exception as exc:
        inspect_kamaz_result = {"error": str(exc)}

    result["steps"]["plow_debug_overdrive"] = plow_result
    result["steps"]["road_receiver_rebuild"] = road_result
    result["steps"]["inspect_snow_component_defaults"] = inspect_defaults_result
    result["steps"]["inspect_kamaz_named_components"] = inspect_kamaz_result
    result["success"] = bool(plow_result.get("success") and road_result.get("success"))
    result["summary"] = (
        f"snow_debug_chain success={result['success']} "
        f"plow={plow_result.get('success')} road={road_result.get('success')}"
    )

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(run())
