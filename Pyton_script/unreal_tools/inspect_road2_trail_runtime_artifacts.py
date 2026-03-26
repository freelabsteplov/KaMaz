import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
TRAIL_ACTOR_PATH = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.SnowRuntimeTrailBridgeActor_0"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_road2_trail_runtime_artifacts.json",
)


def object_path(value):
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def safe_get(obj, property_name, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(property_name)
        except Exception:
            pass
    return getattr(obj, property_name, default)


def find_actor_by_path(actor_path):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        try:
            if actor.get_path_name() == actor_path:
                return actor
        except Exception:
            continue
    return None


def inspect_component(component):
    entry = {
        "name": component.get_name(),
        "class": component.get_class().get_name(),
        "path": component.get_path_name(),
    }

    if isinstance(component, unreal.InstancedStaticMeshComponent):
        entry["instance_count"] = int(component.get_instance_count())
        entry["visible"] = bool(safe_get(component, "visible", True))
        entry["hidden_in_game"] = bool(safe_get(component, "hidden_in_game", False))
        entry["render_in_main_pass"] = bool(safe_get(component, "render_in_main_pass", True))
        entry["render_in_depth_pass"] = bool(safe_get(component, "render_in_depth_pass", True))
        entry["virtual_textures"] = [
            object_path(asset)
            for asset in list(safe_get(component, "runtime_virtual_textures", []) or [])
            if asset is not None
        ]
        entry["materials"] = []
        for index in range(int(component.get_num_materials())):
            try:
                material = component.get_material(index)
            except Exception:
                material = None
            entry["materials"].append(
                {
                    "slot": index,
                    "path": object_path(material),
                }
            )
        if entry["instance_count"] > 0:
            try:
                transforms = list(component.get_instances_transform_array(False) or [])
                if transforms:
                    first = transforms[0]
                    last = transforms[-1]
                    entry["first_instance_location"] = {
                        "x": float(first.translation.x),
                        "y": float(first.translation.y),
                        "z": float(first.translation.z),
                    }
                    entry["last_instance_location"] = {
                        "x": float(last.translation.x),
                        "y": float(last.translation.y),
                        "z": float(last.translation.z),
                    }
            except Exception:
                pass

    return entry


def main():
    result = {
        "success": False,
        "map_path": MAP_PATH,
        "trail_actor_path": TRAIL_ACTOR_PATH,
        "actor_found": False,
        "actor_label": "",
        "components": [],
        "instanced_components": [],
        "error": "",
    }

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        actor = find_actor_by_path(TRAIL_ACTOR_PATH)
        if actor is None:
            raise RuntimeError("SnowRuntimeTrailBridgeActor_0 not found on MoscowEA5")

        result["actor_found"] = True
        result["actor_label"] = actor.get_actor_label()

        for component in list(actor.get_components_by_class(unreal.ActorComponent) or []):
            entry = inspect_component(component)
            result["components"].append(entry)
            if entry["class"] == "InstancedStaticMeshComponent":
                result["instanced_components"].append(entry)

        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
