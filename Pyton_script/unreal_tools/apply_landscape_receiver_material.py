import importlib
import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import inspect_level_surface_materials as ilsm


OUTPUT_BASENAME = "apply_landscape_receiver_material"
LANDSCAPE_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.Landscape_0"
TARGET_MATERIAL_PATH = "/Game/CityPark/SnowSystem/MI_SnowTest_Landscape"

ASSET_LIB = unreal.EditorAssetLibrary


def _log(message: str) -> None:
    unreal.log(f"[apply_landscape_receiver_material] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[apply_landscape_receiver_material] {message}")


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


def _safe_get_editor_property(obj, property_name: str, default=None):
    getter = getattr(obj, "get_editor_property", None)
    if getter is None:
        return getattr(obj, property_name, default)
    try:
        return getter(property_name)
    except Exception:
        return getattr(obj, property_name, default)


def _iter_landscape_material_paths(actor) -> list[str]:
    materials = []

    actor_material = _safe_get_editor_property(actor, "landscape_material")
    actor_material_path = _object_path(actor_material)
    if actor_material_path:
        materials.append(actor_material_path)

    try:
        all_components = actor.get_components_by_class(unreal.ActorComponent)
    except Exception:
        all_components = []

    for component in all_components or []:
        class_path = _object_path(component.get_class())
        if "LandscapeComponent" not in class_path:
            continue

        override_material = _safe_get_editor_property(component, "override_material")
        override_material_path = _object_path(override_material)
        if override_material_path:
            materials.append(override_material_path)

        try:
            for material in component.get_materials() or []:
                material_path = _object_path(material)
                if material_path:
                    materials.append(material_path)
        except Exception:
            pass

    return sorted(set(path for path in materials if path))


def _find_actor_by_path(actor_path: str):
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in subsystem.get_all_level_actors():
        if _object_path(actor) == actor_path:
            return actor
    return None


def _save_current_level() -> dict:
    result = {"saved_current_level": False, "error": ""}
    try:
        result["saved_current_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    except Exception as exc:
        result["error"] = str(exc)
    return result


def apply_landscape_receiver_material(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    target_material = ASSET_LIB.load_asset(TARGET_MATERIAL_PATH)
    landscape_actor = _find_actor_by_path(LANDSCAPE_ACTOR_PATH)

    result = {
        "landscape_actor_path": LANDSCAPE_ACTOR_PATH,
        "target_material_path": TARGET_MATERIAL_PATH,
        "success": False,
        "before_actor_material": "",
        "after_actor_material": "",
        "before_materials": [],
        "after_materials": [],
        "saved_level": False,
        "save_error": "",
        "surface_report_path": "",
        "summary": "",
        "notes": [
            "This changes only Landscape_0 material assignment.",
            "It does not edit Kamaz, MOZA input, road receiver assets, or any snow material graphs.",
            "The previous landscape assignment is recorded in this JSON for rollback.",
        ],
    }

    if target_material is None:
        result["summary"] = f"Missing target material: {TARGET_MATERIAL_PATH}"
    elif landscape_actor is None:
        result["summary"] = f"Missing landscape actor: {LANDSCAPE_ACTOR_PATH}"
    else:
        before_actor_material = _safe_get_editor_property(landscape_actor, "landscape_material")
        result["before_actor_material"] = _object_path(before_actor_material)
        result["before_materials"] = _iter_landscape_material_paths(landscape_actor)

        try:
            landscape_actor.modify()
        except Exception:
            pass

        landscape_actor.set_editor_property("landscape_material", target_material)

        try:
            landscape_actor.post_edit_change()
        except Exception as exc:
            _warn(f"post_edit_change failed: {exc}")

        try:
            unreal.EditorLevelLibrary.editor_invalidate_viewports()
        except Exception:
            pass

        after_actor_material = _safe_get_editor_property(landscape_actor, "landscape_material")
        result["after_actor_material"] = _object_path(after_actor_material)
        result["after_materials"] = _iter_landscape_material_paths(landscape_actor)

        save_result = _save_current_level()
        result["saved_level"] = bool(save_result.get("saved_current_level", False))
        result["save_error"] = save_result.get("error", "")

        try:
            ilsm_module = importlib.reload(ilsm)
            surface_report = ilsm_module.inspect_current_level_surface_materials(output_dir)
            result["surface_report_path"] = surface_report.get("output_path", "")
        except Exception as exc:
            _warn(f"surface report failed: {exc}")

        result["success"] = (
            result["after_actor_material"] == f"{TARGET_MATERIAL_PATH}.{_object_name(target_material)}"
            and result["saved_level"]
        )
        result["summary"] = (
            f"Landscape_0 material: {result['before_actor_material']} -> {result['after_actor_material']} "
            f"saved_level={result['saved_level']}"
        )

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    return {"output_path": output_path, "result": result}


def print_summary(output_dir: str | None = None):
    payload = apply_landscape_receiver_material(output_dir)
    _log(payload["result"]["summary"])
    _log(f"summary_path={payload['output_path']}")
    return {
        "success": payload["result"].get("success", False),
        "summary": payload["result"].get("summary", ""),
        "output_path": payload.get("output_path", ""),
    }


if __name__ == "__main__":
    print_summary()
