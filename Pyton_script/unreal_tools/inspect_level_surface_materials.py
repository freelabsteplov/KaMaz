import json
import os
from collections import Counter, defaultdict

import unreal


OUTPUT_BASENAME = "level_surface_materials"
SURFACE_HINTS = (
    "road",
    "street",
    "asphalt",
    "pavement",
    "sidewalk",
    "walk",
    "curb",
    "tile",
    "ground",
    "floor",
    "outside",
    "concrete",
)
NOISE_HINTS = (
    "sign",
    "stoika",
    "collar",
    "light",
    "glass",
    "metal",
    "tree",
    "leaf",
    "twig",
    "trunk",
    "banner",
    "table",
    "pole",
    "bench",
    "adverts",
    "advert",
    "navigator",
)


def _log(message: str) -> None:
    unreal.log(f"[inspect_level_surface_materials] {message}")


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


def _safe_get_editor_property(obj, property_name: str, default=None):
    getter = getattr(obj, "get_editor_property", None)
    if getter is None:
        return getattr(obj, property_name, default)

    try:
        return getter(property_name)
    except Exception:
        return getattr(obj, property_name, default)


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


def _surface_score(text: str) -> int:
    lowered = text.lower()
    return sum(1 for hint in SURFACE_HINTS if hint in lowered)


def _noise_score(text: str) -> int:
    lowered = text.lower()
    return sum(1 for hint in NOISE_HINTS if hint in lowered)


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

        materials.extend(_iter_material_paths(component))

    return sorted(set(path for path in materials if path))


def inspect_current_level_surface_materials(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()

    editor_actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.EditorLevelLibrary.get_editor_world()
    actors = editor_actor_subsystem.get_all_level_actors()

    landscape_entries = []
    material_counter = Counter()
    material_to_components = defaultdict(list)
    likely_surface_components = []
    top_surface_materials = []

    for actor in actors:
        actor_name = _object_name(actor)
        actor_path = _object_path(actor)
        actor_class = _object_path(actor.get_class())

        # Landscape actors are the first likely receiver candidates.
        if "Landscape" in actor_class:
            landscape_entries.append(
                {
                    "actor_name": actor_name,
                    "actor_path": actor_path,
                    "actor_class": actor_class,
                    "materials": _iter_landscape_material_paths(actor),
                }
            )

        try:
            mesh_components = actor.get_components_by_class(unreal.MeshComponent)
        except Exception:
            mesh_components = []

        for component in mesh_components or []:
            component_name = _object_name(component)
            component_class = _object_path(component.get_class())
            material_paths = _iter_material_paths(component)
            if not material_paths:
                continue

            joined = " ".join([component_name, component_class, *material_paths])
            score = _surface_score(joined) - _noise_score(joined)

            for material_path in material_paths:
                material_counter[material_path] += 1
                material_to_components[material_path].append(
                    {
                        "actor_name": actor_name,
                        "actor_path": actor_path,
                        "component_name": component_name,
                        "component_class": component_class,
                    }
                )

            if score > 0:
                likely_surface_components.append(
                    {
                        "score": score,
                        "actor_name": actor_name,
                        "actor_path": actor_path,
                        "component_name": component_name,
                        "component_class": component_class,
                        "materials": material_paths,
                    }
                )

    top_materials = []
    for material_path, usage_count in material_counter.most_common(50):
        top_materials.append(
            {
                "material_path": material_path,
                "usage_count": usage_count,
                "example_components": material_to_components[material_path][:5],
            }
        )

    for material_path, usage_count in material_counter.most_common():
        score = _surface_score(material_path) - _noise_score(material_path)
        if score <= 0:
            continue
        top_surface_materials.append(
            {
                "material_path": material_path,
                "usage_count": usage_count,
                "surface_score": score,
                "example_components": material_to_components[material_path][:5],
            }
        )
        if len(top_surface_materials) >= 30:
            break

    likely_surface_components.sort(
        key=lambda entry: (-entry["score"], entry["actor_name"], entry["component_name"])
    )

    result = {
        "level_name": _object_name(world),
        "num_landscape_candidates": len(landscape_entries),
        "landscape_candidates": landscape_entries,
        "top_level_materials": top_materials,
        "top_surface_materials": top_surface_materials,
        "likely_surface_components": likely_surface_components[:100],
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(inspect_current_level_surface_materials())
