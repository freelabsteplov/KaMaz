import json
import os

import unreal


OUTPUT_BASENAME = "selected_actor_materials"


def _log(message: str) -> None:
    unreal.log(f"[inspect_selected_actor_materials] {message}")


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


def _iter_component_materials(component):
    entries = []
    try:
        materials = component.get_materials() or []
    except Exception:
        materials = []

    for index, material in enumerate(materials):
        entries.append(
            {
                "slot_index": index,
                "material_name": _object_name(material),
                "material_path": _object_path(material),
            }
        )

    return entries


def inspect_selected_actor_materials(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    selected_actors = list(actor_subsystem.get_selected_level_actors() or [])

    result = {
        "num_selected_actors": len(selected_actors),
        "actors": [],
    }

    for actor in selected_actors:
        actor_entry = {
            "actor_name": _object_name(actor),
            "actor_path": _object_path(actor),
            "actor_class": _object_path(actor.get_class()),
            "components": [],
        }

        try:
            components = actor.get_components_by_class(unreal.MeshComponent)
        except Exception:
            components = []

        for component in components or []:
            component_entry = {
                "component_name": _object_name(component),
                "component_path": _object_path(component),
                "component_class": _object_path(component.get_class()),
                "materials": _iter_component_materials(component),
            }
            actor_entry["components"].append(component_entry)

        result["actors"].append(actor_entry)

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(inspect_selected_actor_materials())
