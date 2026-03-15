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


OUTPUT_BASENAME = "apply_pure_texcoord_rt_debug_to_road2_overlay"
TARGET_ACTOR_LABEL = "SnowOverlay_Road2"
DEBUG_EMISSIVE_MULTIPLIER = 80.0


def _log(message: str) -> None:
    unreal.log(f"[apply_pure_texcoord_rt_debug_to_road2_overlay] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_name(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_name()
    except Exception:
        return str(value)


def _object_path(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _find_actor_by_label(label: str):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        try:
            actor_label = actor.get_actor_label()
        except Exception:
            actor_label = ""
        if actor_label == label:
            return actor
    return None


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()

    target_actor = _find_actor_by_label(TARGET_ACTOR_LABEL)
    if target_actor is None:
        raise RuntimeError(f"Could not find actor with label '{TARGET_ACTOR_LABEL}'.")

    module = importlib.reload(rr)
    module.DEBUG_DIRECT_RT_VIS = True
    module.DEBUG_FORCE_SOLID_COLOR = False
    module.DEBUG_DIRECT_TEXCOORD_RT_VIS = False
    module.DEBUG_PURE_TEXCOORD_RT_VIS = True
    module.DEBUG_USE_TEXCOORD_CLEAR_MASK = False
    module.DEBUG_WORLD_UV_FLIP_Y = False
    module.DEBUG_EMISSIVE_MULTIPLIER = DEBUG_EMISSIVE_MULTIPLIER

    rebuild_result = module.run(output_dir)
    apply_result = prsra.apply_material_to_actor_slot0(_object_path(target_actor), module.RECEIVER_INSTANCE_PATH)

    save_result = {"saved_current_level": False, "error": ""}
    try:
        save_result["saved_current_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    except Exception as exc:
        save_result["error"] = str(exc)

    payload = {
        "success": bool(rebuild_result.get("success", False) and apply_result.get("num_components_updated", 0) > 0),
        "summary": rebuild_result.get("summary", ""),
        "target_actor_label": TARGET_ACTOR_LABEL,
        "target_actor_name": _object_name(target_actor),
        "target_actor_path": _object_path(target_actor),
        "mode": "road2_overlay_pure_texcoord_rt_debug",
        "debug_emissive_multiplier": DEBUG_EMISSIVE_MULTIPLIER,
        "rebuild_output_path": rebuild_result.get("output_path", ""),
        "apply_result": apply_result,
        "save_result": save_result,
        "notes": [
            "Applies a pure TexCoord-based SnowRT debug material to SnowOverlay_Road2.",
            "It does not spawn, move, rotate, or rescale any actor.",
            "It bypasses road/cap/curb masks so only RT visibility is tested.",
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
