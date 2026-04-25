import json
import os

import unreal


MAP_PATH = "/Game/LandscapeDeformation/Maps/SnowMap"
ACTOR_LABEL = "KamazSnowPlowCaptureDeformer"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "tmp_inspect_snowmap_helper_materials.json",
)


def _path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _name(obj):
    if not obj:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _write(payload):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main():
    result = {
        "map_path": MAP_PATH,
        "actor_path": "",
        "components": [],
        "error": "",
    }
    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        helper = None
        for actor in actors:
            try:
                if actor.get_actor_label() == ACTOR_LABEL:
                    helper = actor
                    break
            except Exception:
                continue

        if helper is None:
            raise RuntimeError(f"Could not find actor label: {ACTOR_LABEL}")

        result["actor_path"] = _path(helper)
        for component in list(helper.get_components_by_class(unreal.StaticMeshComponent) or []):
            result["components"].append(
                {
                    "name": _name(component),
                    "path": _path(component),
                    "mesh": _path(component.get_editor_property("static_mesh")),
                    "material_0": _path(component.get_material(0)),
                }
            )
    except Exception as exc:
        result["error"] = str(exc)

    _write(result)


if __name__ == "__main__":
    main()
