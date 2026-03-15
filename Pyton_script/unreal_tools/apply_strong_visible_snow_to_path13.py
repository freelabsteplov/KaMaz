import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import rebuild_visible_road_snow_receiver as rr


OUTPUT_BASENAME = "apply_strong_visible_snow_to_path13"
TARGET_ACTOR_LABEL = "Path13"


def _log(message: str) -> None:
    unreal.log(f"[apply_strong_visible_snow_to_path13] {message}")


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


def _find_actors_by_label(label: str):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    matches = []
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        try:
            actor_label = actor.get_actor_label()
        except Exception:
            actor_label = ""
        if actor_label == label:
            matches.append(actor)
    return matches


def _apply_material_to_actor_slot0(actor, material_asset):
    updated = []
    try:
        components = actor.get_components_by_class(unreal.MeshComponent)
    except Exception:
        components = []

    for component in components or []:
        try:
            component.set_material(0, material_asset)
            updated.append(
                {
                    "actor_name": _object_name(actor),
                    "actor_label": actor.get_actor_label(),
                    "actor_path": _object_path(actor),
                    "component_name": _object_name(component),
                    "component_path": _object_path(component),
                }
            )
        except Exception:
            continue
    return updated


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    module = importlib.reload(rr)
    module.DEBUG_DIRECT_RT_VIS = False
    module.DEBUG_FORCE_SOLID_COLOR = False
    module.DEBUG_DIRECT_TEXCOORD_RT_VIS = False
    module.DEBUG_USE_TEXCOORD_CLEAR_MASK = True

    module.BASE_SNOW_AMOUNT = 0.96
    module.SNOW_TINT_STRENGTH = 1.45
    module.SNOW_COLOR_TINT = (1.6, 1.62, 1.68)
    module.SNOW_UV_SCALE = 3.0
    module.TRACE_DEBUG_EMISSIVE_MULTIPLIER = 8.0

    rebuild_result = module.run(output_dir)
    material_asset = unreal.EditorAssetLibrary.load_asset(module.RECEIVER_INSTANCE_PATH)
    if material_asset is None:
        raise RuntimeError(f"Could not load receiver instance: {module.RECEIVER_INSTANCE_PATH}")

    matched_actors = _find_actors_by_label(TARGET_ACTOR_LABEL)
    updated_components = []
    for actor in matched_actors:
        updated_components.extend(_apply_material_to_actor_slot0(actor, material_asset))

    save_result = {"saved_current_level": False, "error": ""}
    try:
        save_result["saved_current_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    except Exception as exc:
        save_result["error"] = str(exc)

    payload = {
        "success": bool(rebuild_result.get("success", False) and len(updated_components) > 0),
        "summary": rebuild_result.get("summary", ""),
        "mode": "strong_visible_snow_path13",
        "target_actor_label": TARGET_ACTOR_LABEL,
        "matched_actor_count": len(matched_actors),
        "rebuild_output_path": rebuild_result.get("output_path", ""),
        "updated_components": updated_components,
        "save_result": save_result,
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
