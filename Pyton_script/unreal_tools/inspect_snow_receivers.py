import json
import os

import unreal


SNOW_MATERIAL_PATH_HINTS = (
    "/Game/CityPark/SnowSystem/",
    "/Game/CityPark/SnowSystem/M_SnowTestMVP_Landscape1",
    "/Game/CityPark/SnowSystem/MI_SnowTest_Landscape",
    "/Game/CityPark/SnowSystem/M_SnowTest_Landscape",
)

OUTPUT_BASENAME = "snow_receivers_current_level"


def _log(message: str) -> None:
    unreal.log(f"[inspect_snow_receivers] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_path(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _object_name(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _iter_material_paths(component) -> list[str]:
    paths = []
    try:
        for material in component.get_materials() or []:
            material_path = _object_path(material)
            if material_path:
                paths.append(material_path)
    except Exception:
        pass
    return paths


def _is_snow_receiver(material_paths: list[str]) -> bool:
    for material_path in material_paths:
        for hint in SNOW_MATERIAL_PATH_HINTS:
            if hint in material_path:
                return True
    return False


def inspect_current_level_snow_receivers(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()

    editor_actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.EditorLevelLibrary.get_editor_world()
    level_name = _object_name(world)

    actors = editor_actor_subsystem.get_all_level_actors()
    all_components = []
    snow_receivers = []

    for actor in actors:
        actor_name = _object_name(actor)
        actor_path = _object_path(actor)

        try:
            components = actor.get_components_by_class(unreal.MeshComponent)
        except Exception:
            components = []

        for component in components or []:
            material_paths = _iter_material_paths(component)
            if not material_paths:
                continue

            entry = {
                "actor_name": actor_name,
                "actor_path": actor_path,
                "component_name": _object_name(component),
                "component_class": _object_path(component.get_class()),
                "materials": material_paths,
            }
            all_components.append(entry)

            if _is_snow_receiver(material_paths):
                snow_receivers.append(entry)

    result = {
        "level_name": level_name,
        "num_mesh_components_with_materials": len(all_components),
        "num_snow_receivers": len(snow_receivers),
        "snow_receivers": snow_receivers,
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(inspect_current_level_snow_receivers())
