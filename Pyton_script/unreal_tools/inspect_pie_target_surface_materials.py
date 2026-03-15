import json
import os

import unreal


TARGET_EDITOR_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208"
TARGET_ACTOR_NAME = "StaticMeshActor_208"
TARGET_ACTOR_LABEL = "Road2"
TARGET_OVERLAY_LABEL = "SnowOverlay_Road2"
EXPECTED_SLOT0_PATH = "/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_Inst_SnowReceiver_Test.M_SR_RoadSection001_Inst_SnowReceiver_Test"
OUTPUT_BASENAME = "inspect_pie_target_surface_materials"


def _log(message: str) -> None:
    unreal.log(f"[inspect_pie_target_surface_materials] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_name(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _object_path(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _safe_property(obj, property_name: str, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(property_name)
        except Exception:
            pass
    try:
        return getattr(obj, property_name)
    except Exception:
        return default


def _get_pie_worlds() -> list:
    worlds = []
    try:
        worlds = list(unreal.EditorLevelLibrary.get_pie_worlds(False) or [])
    except Exception:
        worlds = []
    if worlds:
        return [world for world in worlds if world is not None]

    try:
        game_world = unreal.EditorLevelLibrary.get_game_world()
    except Exception:
        game_world = None
    if game_world is not None:
        return [game_world]

    try:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        game_world = subsystem.get_game_world()
    except Exception:
        game_world = None
    if game_world is not None:
        return [game_world]
    return []


def _iter_world_actors(world, actor_class):
    gameplay_statics = getattr(unreal, "GameplayStatics", None)
    if gameplay_statics is not None:
        get_all = getattr(gameplay_statics, "get_all_actors_of_class", None)
        if callable(get_all):
            try:
                return list(get_all(world, actor_class) or [])
            except Exception:
                pass

    level = _safe_property(world, "persistent_level")
    if level is not None:
        actors = _safe_property(level, "actors", [])
        return [actor for actor in list(actors or []) if actor is not None and actor.is_a(actor_class)]
    return []


def _actor_label(actor) -> str:
    getter = getattr(actor, "get_actor_label", None)
    if callable(getter):
        try:
            return getter()
        except Exception:
            pass
    return ""


def _component_materials(component) -> list:
    entries = []
    try:
        num_materials = int(component.get_num_materials())
    except Exception:
        num_materials = 0

    for slot_index in range(num_materials):
        try:
            material = component.get_material(slot_index)
        except Exception:
            material = None
        entries.append(
            {
                "slot_index": int(slot_index),
                "material_name": _object_name(material),
                "material_path": _object_path(material),
                "matches_expected_slot0": bool(slot_index == 0 and _object_path(material) == EXPECTED_SLOT0_PATH),
            }
        )
    return entries


def _inspect_actor(actor) -> dict:
    mesh_components = list(actor.get_components_by_class(unreal.MeshComponent) or [])
    inspected_components = []
    for component in mesh_components:
        inspected_components.append(
            {
                "component_name": _object_name(component),
                "component_path": _object_path(component),
                "component_class": _object_path(component.get_class()),
                "materials": _component_materials(component),
            }
        )
    return {
        "actor_name": _object_name(actor),
        "actor_label": _actor_label(actor),
        "actor_path": _object_path(actor),
        "actor_class": _object_path(actor.get_class()),
        "components": inspected_components,
    }


def _match_target_actor(actor) -> bool:
    actor_path = _object_path(actor)
    actor_name = _object_name(actor)
    actor_label = _actor_label(actor)
    return (
        actor_name == TARGET_ACTOR_NAME
        or actor_label == TARGET_ACTOR_LABEL
        or actor_path.endswith(f":PersistentLevel.{TARGET_ACTOR_NAME}")
    )


def _match_overlay_actor(actor) -> bool:
    actor_label = _actor_label(actor)
    actor_name = _object_name(actor)
    return actor_label == TARGET_OVERLAY_LABEL or actor_name == TARGET_OVERLAY_LABEL


def inspect_pie_target_surface_materials(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    pie_worlds = _get_pie_worlds()
    if not pie_worlds:
        raise RuntimeError("No PIE world found. Start PIE first, then rerun this script.")

    result = {
        "success": True,
        "target_editor_actor_path": TARGET_EDITOR_ACTOR_PATH,
        "expected_slot0_material_path": EXPECTED_SLOT0_PATH,
        "num_pie_worlds": len(pie_worlds),
        "pie_worlds": [],
    }

    for world in pie_worlds:
        world_entry = {
            "world_name": _object_name(world),
            "world_path": _object_path(world),
            "world_type": str(_safe_property(world, "world_type")),
            "target_actor": None,
            "overlay_actor": None,
        }
        actors = _iter_world_actors(world, unreal.StaticMeshActor)
        for actor in actors:
            if world_entry["target_actor"] is None and _match_target_actor(actor):
                world_entry["target_actor"] = _inspect_actor(actor)
            if world_entry["overlay_actor"] is None and _match_overlay_actor(actor):
                world_entry["overlay_actor"] = _inspect_actor(actor)
            if world_entry["target_actor"] is not None and world_entry["overlay_actor"] is not None:
                break
        result["pie_worlds"].append(world_entry)

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary() -> str:
    result = inspect_pie_target_surface_materials()
    found = 0
    matching = 0
    for world_entry in result["pie_worlds"]:
        target = world_entry.get("target_actor")
        if not target:
            continue
        found += 1
        for component in target.get("components", []):
            for material in component.get("materials", []):
                if material.get("slot_index") == 0 and material.get("matches_expected_slot0"):
                    matching += 1
    summary = f"pie_worlds={result['num_pie_worlds']} target_found={found} slot0_expected_matches={matching}"
    _log(summary)
    return summary


if __name__ == "__main__":
    print(inspect_pie_target_surface_materials())
