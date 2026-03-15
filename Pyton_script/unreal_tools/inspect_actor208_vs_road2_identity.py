import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
ACTOR_208_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
TARGET_LABELS = ("Road2", "StaticMeshActor_208", "SnowOverlay_Road2")
OUTPUT_BASENAME = "inspect_actor208_vs_road2_identity"


def _log(message: str) -> None:
    unreal.log(f"[inspect_actor208_vs_road2_identity] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_path(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _object_name(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_name()
    except Exception:
        return str(value)


def _safe_property(obj, property_name: str, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(property_name)
        except Exception:
            pass
    return getattr(obj, property_name, default)


def _all_level_actors():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return list(actor_subsystem.get_all_level_actors() or [])


def _actor_label(actor) -> str:
    try:
        return actor.get_actor_label()
    except Exception:
        return ""


def _actor_bounds(actor) -> dict:
    get_bounds = getattr(actor, "get_actor_bounds", None)
    if callable(get_bounds):
        try:
            origin, extent = get_bounds(True)
            return {
                "origin": {
                    "x": float(origin.x),
                    "y": float(origin.y),
                    "z": float(origin.z),
                },
                "extent": {
                    "x": float(extent.x),
                    "y": float(extent.y),
                    "z": float(extent.z),
                },
            }
        except Exception:
            pass
    return {"origin": None, "extent": None}


def _component_materials(component):
    materials = []
    try:
        num_materials = int(component.get_num_materials())
    except Exception:
        num_materials = 0
    for slot_index in range(num_materials):
        try:
            material = component.get_material(slot_index)
        except Exception:
            material = None
        materials.append(
            {
                "slot_index": int(slot_index),
                "material_path": _object_path(material),
            }
        )
    return materials


def _describe_actor(actor) -> dict:
    static_mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
    static_mesh = _safe_property(static_mesh_component, "static_mesh") if static_mesh_component else None
    return {
        "actor_label": _actor_label(actor),
        "actor_name": _object_name(actor),
        "actor_path": _object_path(actor),
        "actor_class": _object_name(actor.get_class()) if actor is not None else "",
        "bounds": _actor_bounds(actor),
        "static_mesh_component_path": _object_path(static_mesh_component),
        "static_mesh_path": _object_path(static_mesh),
        "component_materials": _component_materials(static_mesh_component) if static_mesh_component else [],
    }


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    actor_208 = None
    by_label = {label: [] for label in TARGET_LABELS}
    for actor in _all_level_actors():
        actor_path = _object_path(actor)
        actor_label = _actor_label(actor)
        if actor_path == ACTOR_208_PATH:
            actor_208 = actor
        if actor_label in by_label:
            by_label[actor_label].append(_describe_actor(actor))

    result = {
        "success": True,
        "map_path": MAP_PATH,
        "actor_208": _describe_actor(actor_208) if actor_208 is not None else None,
        "matches_by_label": by_label,
    }
    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary() -> str:
    result = run()
    actor_208_label = ""
    if result.get("actor_208"):
        actor_208_label = result["actor_208"].get("actor_label", "")
    summary = (
        f"actor208_label={actor_208_label} "
        f"road2_matches={len(result['matches_by_label'].get('Road2', []))} "
        f"overlay_matches={len(result['matches_by_label'].get('SnowOverlay_Road2', []))}"
    )
    _log(summary)
    return summary


if __name__ == "__main__":
    print(run())
