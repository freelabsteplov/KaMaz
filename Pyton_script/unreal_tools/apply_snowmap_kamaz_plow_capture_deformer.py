import json
import os

import unreal


MAP_PATH = "/Game/LandscapeDeformation/Maps/SnowMap"
ACTOR_LABEL = "KamazSnowPlowCaptureDeformer"
ACTOR_CLASS_PATH = "/Script/Kamaz_Cleaner.SnowMapKamazPlowCaptureDeformerActor"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "apply_snowmap_kamaz_plow_capture_deformer.json",
)
TEST_DEFORMER_MESH_PATHS = {
    "/Engine/BasicShapes/Sphere.Sphere",
    "/Engine/BasicShapes/Cube.Cube",
}
HELPER_PREFERRED_COMPONENT = unreal.Name("PlowBrush")
HELPER_SECONDARY_COMPONENT = unreal.Name("SM_FrontHitch")
HELPER_FALLBACK_COMPONENT = unreal.Name("BP_PlowBrush_Component")
HELPER_RELATIVE_LOCATION = unreal.Vector(0.0, 0.0, -30.0)


def _path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _label(actor):
    if not actor:
        return ""
    try:
        return actor.get_actor_label()
    except Exception:
        try:
            return actor.get_name()
        except Exception:
            return ""


def _vec_to_dict(value):
    if value is None:
        return None
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def _rot_to_dict(value):
    if value is None:
        return None
    return {"pitch": float(value.pitch), "yaw": float(value.yaw), "roll": float(value.roll)}


def _all_actors():
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    return list(actor_subsystem.get_all_level_actors() or [])


def _save_current_level():
    try:
        level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if level_editor:
            return bool(level_editor.save_current_level())
    except Exception:
        pass
    try:
        return bool(unreal.EditorLevelLibrary.save_current_level())
    except Exception:
        return False


def main():
    result = {
        "map_path": MAP_PATH,
        "actor_class_path": ACTOR_CLASS_PATH,
        "destroyed": [],
        "destroyed_test_deformers": [],
        "spawned_actor": "",
        "spawned_location": None,
        "spawned_rotation": None,
        "save_ok": False,
        "error": "",
    }

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        actor_class = unreal.load_class(None, ACTOR_CLASS_PATH)
        if actor_class is None:
            raise RuntimeError(f"Could not load actor class: {ACTOR_CLASS_PATH}")

        for actor in _all_actors():
            if _label(actor) != ACTOR_LABEL:
                mesh_component = actor.get_component_by_class(unreal.StaticMeshComponent)
                mesh = mesh_component.get_editor_property("static_mesh") if mesh_component else None
                if _path(mesh) in TEST_DEFORMER_MESH_PATHS and _label(actor) in {"Sphere", "Cube"}:
                    result["destroyed_test_deformers"].append(_path(actor))
                    unreal.EditorLevelLibrary.destroy_actor(actor)
                continue
            result["destroyed"].append(_path(actor))
            unreal.EditorLevelLibrary.destroy_actor(actor)

        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            actor_class,
            unreal.Vector(0.0, 0.0, 0.0),
            unreal.Rotator(0.0, 0.0, 0.0),
        )
        if actor is None:
            raise RuntimeError("Failed to spawn SnowMap Kamaz plow capture deformer actor.")

        actor.set_actor_label(ACTOR_LABEL)
        actor.set_editor_property("bUsePlowLiftVisibilityGate", False)
        actor.set_editor_property("PreferredPlowComponentToken", HELPER_PREFERRED_COMPONENT)
        actor.set_editor_property("SecondaryPlowComponentToken", HELPER_SECONDARY_COMPONENT)
        actor.set_editor_property("FallbackHitchComponentToken", HELPER_FALLBACK_COMPONENT)
        actor.set_editor_property("DeformerRelativeLocation", HELPER_RELATIVE_LOCATION)
        result["spawned_actor"] = _path(actor)
        result["spawned_location"] = _vec_to_dict(actor.get_actor_location())
        result["spawned_rotation"] = _rot_to_dict(actor.get_actor_rotation())
        result["deformer_relative_location"] = _vec_to_dict(HELPER_RELATIVE_LOCATION)

        result["save_ok"] = _save_current_level()
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
