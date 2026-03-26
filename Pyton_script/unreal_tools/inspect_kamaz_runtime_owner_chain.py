import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
OUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_kamaz_runtime_owner_chain.json",
)


def object_path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def class_path(obj):
    if not obj:
        return ""
    try:
        return obj.get_class().get_path_name()
    except Exception:
        return ""


def label(obj):
    if not obj:
        return ""
    try:
        return obj.get_actor_label()
    except Exception:
        try:
            return obj.get_name()
        except Exception:
            return ""


result = {
    "map": MAP_PATH,
    "world_settings": {},
    "game_mode_assets": {},
    "actors": [],
    "error": "",
}

try:
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    world = unreal.EditorLevelLibrary.get_editor_world()
    ws = world.get_world_settings() if world else None

    if ws:
        result["world_settings"] = {
            "world_settings_path": object_path(ws),
            "default_game_mode": object_path(getattr(ws, "default_game_mode", None)),
            "game_mode_override": object_path(getattr(ws, "default_game_mode", None)),
        }

    for asset_path in (
        "/Game/BPs/BP_KamazGameMode",
        "/Game/VehicleTemplate/Blueprints/BP_VehicleAdvGameMode",
        "/Game/CityPark/Kamaz/model/KamazBP",
        "/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit",
    ):
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        entry = {
            "asset_found": bool(asset),
            "asset_path": asset_path,
        }
        if asset:
            try:
                generated_class = asset.generated_class()
            except Exception:
                generated_class = getattr(asset, "generated_class", None)

            entry["generated_class"] = object_path(generated_class)
            cdo = None
            if generated_class:
                try:
                    cdo = unreal.get_default_object(generated_class)
                except Exception:
                    cdo = None
            entry["cdo_path"] = object_path(cdo)
            if cdo:
                for prop_name in ("default_pawn_class", "player_controller_class"):
                    try:
                        entry[prop_name] = object_path(cdo.get_editor_property(prop_name))
                    except Exception:
                        pass
        result["game_mode_assets"][asset_path] = entry

    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        actor_label = label(actor)
        actor_path = object_path(actor)
        actor_class = class_path(actor)
        if (
            "Kamaz" in actor_label
            or "Kamaz" in actor_class
            or "SnowRuntimeTrailBridgeActor" in actor_label
            or "SnowRuntimeTrailBridgeActor" in actor_class
        ):
            result["actors"].append(
                {
                    "label": actor_label,
                    "path": actor_path,
                    "class": actor_class,
                }
            )

except Exception as exc:
    result["error"] = str(exc)

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, ensure_ascii=False)

print(OUT_PATH)
