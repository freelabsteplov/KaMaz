import json
import os

import unreal


MAP_PATH = "/Game/Maps/SnowMap_MoscowEA5"
SUBLEVEL_TOKEN = "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel."
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "apply_snowmap_moscowea5_hide_sublevel_from_capture.json",
)


def _path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _label(actor):
    try:
        return actor.get_actor_label()
    except Exception:
        return actor.get_name()


def _set_bool(component, prop_name, value):
    try:
        component.set_editor_property(prop_name, value)
        return True
    except Exception:
        return False


def _save_current_level():
    try:
        return bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    except Exception:
        return False


def main():
    payload = {
        "map_path": MAP_PATH,
        "sublevel_token": SUBLEVEL_TOKEN,
        "actors_touched": 0,
        "primitive_components_touched": 0,
        "sample_components": [],
        "save_ok": False,
        "error": "",
    }

    try:
        world = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        if not world:
            raise RuntimeError(f"Could not load map: {MAP_PATH}")

        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actors = list(actor_subsystem.get_all_level_actors() or [])

        for actor in actors:
            actor_path = _path(actor)
            if SUBLEVEL_TOKEN not in actor_path:
                continue

            touched_actor = False
            for component in list(actor.get_components_by_class(unreal.PrimitiveComponent) or []):
                changed = False
                changed |= _set_bool(component, "hidden_in_scene_capture", True)
                changed |= _set_bool(component, "visible_in_scene_capture_only", False)
                changed |= _set_bool(component, "hidden_in_game", False)
                if changed:
                    touched_actor = True
                    payload["primitive_components_touched"] += 1
                    if len(payload["sample_components"]) < 40:
                        payload["sample_components"].append(
                            {
                                "actor_label": _label(actor),
                                "actor_path": actor_path,
                                "component_name": component.get_name(),
                                "component_class": _path(component.get_class()),
                            }
                        )

            if touched_actor:
                payload["actors_touched"] += 1

        payload["save_ok"] = _save_current_level()
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
