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
import apply_receiver_to_spawn_zone_roads as arszr


OUTPUT_BASENAME = "run_spawn_zone_snow_debug_prep"


def _log(message: str) -> None:
    unreal.log(f"[run_spawn_zone_snow_debug_prep] {message}")


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

    global apdo, rvsr, arszr
    apdo = importlib.reload(apdo)
    rvsr = importlib.reload(rvsr)
    arszr = importlib.reload(arszr)

    plow_result = apdo.run(output_dir)
    receiver_result = rvsr.run(output_dir)
    spawn_apply_result = arszr.run(output_dir)

    result = {
        "success": bool(
            plow_result.get("success")
            and receiver_result.get("success")
            and spawn_apply_result.get("success")
        ),
        "steps": {
            "apply_plow_debug_overdrive": plow_result,
            "rebuild_visible_road_snow_receiver": receiver_result,
            "apply_receiver_to_spawn_zone_roads": spawn_apply_result,
        },
    }
    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(run())
