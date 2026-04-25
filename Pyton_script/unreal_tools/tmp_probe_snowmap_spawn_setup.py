import json
import os

import unreal


MAP_PATH = "/Game/LandscapeDeformation/Maps/SnowMap"
KAMAZ_BP_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "tmp_probe_snowmap_spawn_setup.json",
)


def _vec(value):
    if value is None:
        return None
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def _rot(value):
    if value is None:
        return None
    return {"pitch": float(value.pitch), "yaw": float(value.yaw), "roll": float(value.roll)}


def _safe_path(obj):
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _safe_get(obj, prop, default=None):
    if obj is None:
        return default
    getter = getattr(obj, "get_editor_property", None)
    if callable(getter):
        try:
            return getter(prop)
        except Exception:
            pass
    return getattr(obj, prop, default)


def _find_vehicle_mesh_scale(kamaz_bp):
    blueprint_class = unreal.EditorAssetLibrary.load_blueprint_class(KAMAZ_BP_PATH)
    cdo = blueprint_class.get_default_object() if blueprint_class else None
    if cdo is None:
        return None

    vehicle_mesh = None
    find_component_by_class = getattr(cdo, "find_component_by_class", None)
    if callable(find_component_by_class):
        try:
            vehicle_mesh = find_component_by_class(unreal.SkeletalMeshComponent)
        except Exception:
            vehicle_mesh = None

    if vehicle_mesh is None:
        for comp in list(_safe_get(cdo, "components", []) or []):
            if comp and comp.get_name() == "VehicleMesh":
                vehicle_mesh = comp
                break

    if vehicle_mesh is None:
        return None

    return {
        "component_path": _safe_path(vehicle_mesh),
        "relative_scale": _vec(_safe_get(vehicle_mesh, "relative_scale3d")),
        "relative_location": _vec(_safe_get(vehicle_mesh, "relative_location")),
    }


def main():
    payload = {
        "map_path": MAP_PATH,
        "kamaz_vehicle_mesh": None,
        "world_settings": {},
        "player_starts": [],
        "error": "",
    }

    try:
        kamaz_bp = unreal.EditorAssetLibrary.load_asset(KAMAZ_BP_PATH)
        if kamaz_bp is None:
            raise RuntimeError(f"Could not load {KAMAZ_BP_PATH}")
        payload["kamaz_vehicle_mesh"] = _find_vehicle_mesh_scale(kamaz_bp)

        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        world = unreal.EditorLevelLibrary.get_editor_world()
        if world is None:
            raise RuntimeError("Editor world is unavailable after loading SnowMap")

        world_settings = world.get_world_settings()
        payload["world_settings"] = {
            "default_game_mode": _safe_path(_safe_get(world_settings, "default_game_mode")),
            "global_default_game_mode": _safe_path(_safe_get(world_settings, "global_default_game_mode")),
            "default_pawn_class": _safe_path(_safe_get(world_settings, "default_pawn_class")),
            "player_controller_class": _safe_path(_safe_get(world_settings, "player_controller_class")),
        }

        for actor in unreal.EditorLevelLibrary.get_all_level_actors():
            if actor.get_class().get_name() != "PlayerStart":
                continue
            payload["player_starts"].append(
                {
                    "name": actor.get_name(),
                    "path": _safe_path(actor),
                    "location": _vec(actor.get_actor_location()),
                    "rotation": _rot(actor.get_actor_rotation()),
                    "scale": _vec(actor.get_actor_scale3d()),
                }
            )
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
