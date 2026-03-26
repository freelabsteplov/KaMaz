import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
ROAD_INSTANCE_MAP = {
    "SnowSplineRoad_MVP": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K",
    "SnowSplineRoad_V1_Original_MVP": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_Tile8",
    "SnowSplineRoad_V3_Narrow_MVP": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_V3_Narrow_Tile4",
}
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "restore_snowtest_road_base_materials.json",
)


def _try_invoke(actor, function_name):
    direct = getattr(actor, function_name, None)
    if callable(direct):
        try:
            direct()
            return {"function": function_name, "path": "direct", "called": True, "error": ""}
        except Exception as exc:
            return {"function": function_name, "path": "direct", "called": False, "error": str(exc)}

    call_method = getattr(actor, "call_method", None)
    if callable(call_method):
        for args in ((function_name,), (function_name, ())):
            try:
                call_method(*args)
                return {"function": function_name, "path": "call_method", "called": True, "error": ""}
            except Exception as exc:
                last_error = str(exc)
        return {"function": function_name, "path": "call_method", "called": False, "error": last_error}

    return {"function": function_name, "path": "none", "called": False, "error": "No callable path exposed."}


def _refresh_road_actor(actor):
    attempts = []

    rerun = _try_invoke(actor, "rerun_construction_scripts")
    attempts.append(rerun)
    if rerun["called"]:
        return attempts

    rebuild = _try_invoke(actor, "RebuildSplineMeshes")
    attempts.append(rebuild)
    if rebuild["called"]:
        return attempts

    post_edit_change = getattr(actor, "post_edit_change", None)
    if callable(post_edit_change):
        try:
            post_edit_change()
            attempts.append(
                {"function": "post_edit_change", "path": "direct", "called": True, "error": ""}
            )
        except Exception as exc:
            attempts.append(
                {"function": "post_edit_change", "path": "direct", "called": False, "error": str(exc)}
            )

    return attempts


def main():
    result = {
        "map": MAP_PATH,
        "restored_roads": [],
        "saved_map": False,
        "error": "",
    }

    try:
        world = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)

        loaded_materials = {}
        for label, material_path in ROAD_INSTANCE_MAP.items():
            material = unreal.EditorAssetLibrary.load_asset(material_path)
            if not material:
                raise RuntimeError(f"Failed to load road material: {material_path}")
            loaded_materials[label] = material

        for actor in actors:
            label = actor.get_actor_label()
            if label not in loaded_materials:
                continue

            actor.modify()
            actor.set_editor_property("snow_road_material", loaded_materials[label])
            refresh_attempts = _refresh_road_actor(actor)
            result["restored_roads"].append(
                {
                    "actor_label": label,
                    "assigned_material": loaded_materials[label].get_path_name(),
                    "refresh_attempts": refresh_attempts,
                }
            )

        result["saved_map"] = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
