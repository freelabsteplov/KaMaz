import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import prepare_road_snow_receiver_assets as prsra
import rebuild_visible_road_snow_receiver as rr


OUTPUT_BASENAME = "apply_direct_rt_debug_to_selected_overlay"
DEBUG_EMISSIVE_MULTIPLIER = 80.0


def _log(message: str) -> None:
    unreal.log(f"[apply_direct_rt_debug_to_selected_overlay] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _selected_actor_names() -> list[str]:
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    names = []
    for actor in list(actor_subsystem.get_selected_level_actors() or []):
        try:
            names.append(actor.get_actor_label())
        except Exception:
            try:
                names.append(actor.get_name())
            except Exception:
                names.append(str(actor))
    return names


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()

    module = importlib.reload(rr)
    module.DEBUG_DIRECT_RT_VIS = True
    module.DEBUG_FORCE_SOLID_COLOR = False
    module.DEBUG_DIRECT_TEXCOORD_RT_VIS = False
    module.DEBUG_USE_TEXCOORD_CLEAR_MASK = False
    module.DEBUG_WORLD_UV_FLIP_Y = False
    module.DEBUG_EMISSIVE_MULTIPLIER = DEBUG_EMISSIVE_MULTIPLIER

    rebuild_result = module.run(output_dir)
    apply_result = prsra.apply_material_to_selected_slot0(module.RECEIVER_INSTANCE_PATH)

    save_result = {"saved_current_level": False, "error": ""}
    try:
        save_result["saved_current_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    except Exception as exc:
        save_result["error"] = str(exc)

    payload = {
        "success": bool(rebuild_result.get("success", False) and apply_result.get("num_components_updated", 0) > 0),
        "summary": rebuild_result.get("summary", ""),
        "selected_actor_names": _selected_actor_names(),
        "mode": "selected_overlay_direct_world_rt_debug",
        "debug_emissive_multiplier": DEBUG_EMISSIVE_MULTIPLIER,
        "rebuild_output_path": rebuild_result.get("output_path", ""),
        "apply_result": apply_result,
        "save_result": save_result,
        "notes": [
            "Applies direct world-space SnowRT debug to the currently selected overlay actor.",
            "It does not spawn, move, rotate, or rescale any actor.",
            "Use it when SnowOverlay_Road2 is already positioned manually and only the material needs to change.",
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
