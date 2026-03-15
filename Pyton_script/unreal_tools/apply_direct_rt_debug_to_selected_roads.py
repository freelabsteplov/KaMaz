import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import rebuild_visible_road_snow_receiver as rr
import prepare_road_snow_receiver_assets as prsra


OUTPUT_BASENAME = "apply_direct_rt_debug_to_selected_roads"


def _log(message: str) -> None:
    unreal.log(f"[apply_direct_rt_debug_to_selected_roads] {message}")


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

    rebuild_result = module.run(output_dir)
    selected_apply_result = prsra.apply_material_to_selected_slot0(module.RECEIVER_INSTANCE_PATH)

    save_result = {"saved_current_level": False, "error": ""}
    try:
        save_result["saved_current_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    except Exception as exc:
        save_result["error"] = str(exc)

    payload = {
        "success": bool(rebuild_result.get("success", False) and selected_apply_result.get("num_components_updated", 0) > 0),
        "summary": rebuild_result.get("summary", ""),
        "mode": "direct_rt_debug_selected",
        "rebuild_output_path": rebuild_result.get("output_path", ""),
        "selected_apply_result": selected_apply_result,
        "save_result": save_result,
        "notes": [
            "This applies the direct RT debug receiver to the currently selected road actors.",
            "Use it when the fixed test actor path does not match the visible road under Kamaz.",
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
