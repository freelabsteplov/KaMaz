import json
import math
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
OUTPUT_BASENAME = "inspect_spawn_surface_candidates"
SPAWN_NAME_TOKENS = ("playerstart", "spawn", "start")
ROAD_NAME_TOKENS = ("road", "asphalt", "snappyroad", "street", "lane")
MAX_CANDIDATES_PER_SPAWN = 24


def _log(message: str) -> None:
    unreal.log(f"[inspect_spawn_surface_candidates] {message}")


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


def _vec_to_dict(value) -> dict:
    return {
        "x": float(value.x),
        "y": float(value.y),
        "z": float(value.z),
    }


def _get_actor_bounds(actor):
    try:
        origin, extent = actor.get_actor_bounds(True)
        return origin, extent
    except Exception as exc:
        raise RuntimeError(f"Could not get bounds for {_object_path(actor)}: {exc}")


def _distance_xy(a, b) -> float:
    return math.sqrt(((float(a.x) - float(b.x)) ** 2) + ((float(a.y) - float(b.y)) ** 2))


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


def _mesh_or_material_looks_like_road(component, actor_path: str) -> bool:
    haystacks = [actor_path.lower()]
    static_mesh = _safe_property(component, "static_mesh")
    if static_mesh is not None:
        haystacks.append(_object_path(static_mesh).lower())
    for material_entry in _component_materials(component):
        haystacks.append(str(material_entry.get("material_path", "")).lower())
    text = " ".join(haystacks)
    return any(token in text for token in ROAD_NAME_TOKENS)


def _serialize_surface_candidate(actor, component, spawn_location, origin, extent) -> dict:
    top_z = float(origin.z + extent.z)
    bottom_z = float(origin.z - extent.z)
    location = actor.get_actor_location()
    return {
        "actor_name": actor.get_name(),
        "actor_path": _object_path(actor),
        "actor_class": _object_path(actor.get_class()),
        "component_path": _object_path(component),
        "component_class": _object_path(component.get_class()),
        "actor_location": _vec_to_dict(location),
        "bounds_origin": _vec_to_dict(origin),
        "bounds_extent": _vec_to_dict(extent),
        "top_z": top_z,
        "bottom_z": bottom_z,
        "delta_z_to_spawn": float(spawn_location.z - top_z),
        "distance_xy_to_spawn": _distance_xy(location, spawn_location),
        "is_road_like": _mesh_or_material_looks_like_road(component, _object_path(actor)),
        "static_mesh_path": _object_path(_safe_property(component, "static_mesh")),
        "materials": _component_materials(component),
    }


def _collect_spawn_points(actors) -> list:
    result = []
    for actor in actors:
        actor_path = _object_path(actor)
        actor_name = actor.get_name()
        class_path = _object_path(actor.get_class())
        combined = f"{actor_path} {actor_name} {class_path}".lower()
        if "/script/engine.playerstart" in class_path.lower() or any(token in combined for token in SPAWN_NAME_TOKENS):
            result.append(
                {
                    "actor_name": actor_name,
                    "actor_path": actor_path,
                    "actor_class": class_path,
                    "location": _vec_to_dict(actor.get_actor_location()),
                    "rotation": {
                        "pitch": float(actor.get_actor_rotation().pitch),
                        "yaw": float(actor.get_actor_rotation().yaw),
                        "roll": float(actor.get_actor_rotation().roll),
                    },
                }
            )
    return result


def _find_surfaces_for_spawn(spawn_entry: dict, actors) -> list:
    spawn_location = unreal.Vector(
        float(spawn_entry["location"]["x"]),
        float(spawn_entry["location"]["y"]),
        float(spawn_entry["location"]["z"]),
    )
    candidates = []
    for actor in actors:
        if isinstance(actor, unreal.StaticMeshActor):
            component = actor.get_component_by_class(unreal.StaticMeshComponent)
        else:
            component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if component is None:
            continue
        static_mesh = _safe_property(component, "static_mesh")
        if static_mesh is None:
            continue
        origin, extent = _get_actor_bounds(actor)
        if abs(float(spawn_location.x) - float(origin.x)) > float(extent.x + 2500.0):
            continue
        if abs(float(spawn_location.y) - float(origin.y)) > float(extent.y + 2500.0):
            continue
        top_z = float(origin.z + extent.z)
        if top_z > float(spawn_location.z + 500.0):
            continue
        if top_z < float(spawn_location.z - 5000.0):
            continue
        candidates.append(_serialize_surface_candidate(actor, component, spawn_location, origin, extent))

    candidates.sort(
        key=lambda entry: (
            0 if entry["is_road_like"] else 1,
            abs(entry["delta_z_to_spawn"]),
            entry["distance_xy_to_spawn"],
            entry["actor_name"],
        )
    )
    return candidates[:MAX_CANDIDATES_PER_SPAWN]


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(actor_subsystem.get_all_level_actors() or [])
    spawn_points = _collect_spawn_points(actors)

    result = {
        "success": True,
        "map_path": MAP_PATH,
        "spawn_point_count": int(len(spawn_points)),
        "spawn_points": [],
    }

    for spawn_entry in spawn_points:
        spawn_entry = dict(spawn_entry)
        spawn_entry["surface_candidates"] = _find_surfaces_for_spawn(spawn_entry, actors)
        result["spawn_points"].append(spawn_entry)

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(run())
