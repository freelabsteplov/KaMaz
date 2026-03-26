import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
CARRIER_LABEL = "SnowHeightBridgeSurface_Road2"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_road2_carrier_flags.json",
)


def _safe_get(obj, name, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(name)
        except Exception:
            pass
    return getattr(obj, name, default)


def _obj_path(obj):
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _find_actor_by_label(label):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        try:
            if actor.get_actor_label() == label:
                return actor
        except Exception:
            continue
    return None


def main():
    result = {
        "success": False,
        "map_path": MAP_PATH,
        "carrier_actor_path": "",
        "actor_flags": {},
        "component_flags": {},
        "error": "",
    }

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        actor = _find_actor_by_label(CARRIER_LABEL)
        if actor is None:
            raise RuntimeError(f"Actor not found: {CARRIER_LABEL}")

        result["carrier_actor_path"] = _obj_path(actor)
        result["actor_flags"] = {
            "is_hidden_ed": bool(_safe_get(actor, "is_hidden_ed", False)),
            "hidden": bool(_safe_get(actor, "hidden", False)),
            "hidden_in_game": bool(_safe_get(actor, "hidden_in_game", False)),
            "is_editor_only_actor": bool(_safe_get(actor, "is_editor_only_actor", False)),
            "is_temporarily_hidden_in_editor": bool(_safe_get(actor, "is_temporarily_hidden_in_editor", False)),
            "bIsEditorOnlyActor": bool(_safe_get(actor, "bIsEditorOnlyActor", False)),
            "enable_auto_lod_generation": bool(_safe_get(actor, "enable_auto_lod_generation", False)),
            "net_load_on_client": bool(_safe_get(actor, "net_load_on_client", True)),
        }

        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if component is not None:
            result["component_flags"] = {
                "component_path": _obj_path(component),
                "visible": bool(_safe_get(component, "visible", True)),
                "hidden_in_game": bool(_safe_get(component, "hidden_in_game", False)),
                "render_in_main_pass": bool(_safe_get(component, "render_in_main_pass", True)),
                "render_in_depth_pass": bool(_safe_get(component, "render_in_depth_pass", True)),
                "visible_in_scene_capture_only": bool(_safe_get(component, "visible_in_scene_capture_only", False)),
                "hidden_in_scene_capture": bool(_safe_get(component, "hidden_in_scene_capture", False)),
                "owner_no_see": bool(_safe_get(component, "owner_no_see", False)),
                "only_owner_see": bool(_safe_get(component, "only_owner_see", False)),
                "render_custom_depth": bool(_safe_get(component, "render_custom_depth", False)),
                "visible_in_ray_tracing": bool(_safe_get(component, "visible_in_ray_tracing", True)),
            }

        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
