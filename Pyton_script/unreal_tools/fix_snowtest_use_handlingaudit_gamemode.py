import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
SOURCE_GAMEMODE_PATH = "/Game/BPs/BP_KamazGameMode"
CLONE_GAMEMODE_PATH = "/Game/BPs/BP_KamazGameMode_HandlingAudit"
CLONE_PAWN_PATH = "/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit"
OUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "fix_snowtest_use_handlingaudit_gamemode.json",
)


def object_path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def load_asset(path):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if not asset:
        raise RuntimeError(f"Failed to load asset: {path}")
    return asset


def generated_class_of(asset):
    try:
        generated = asset.generated_class()
        if generated:
            return generated
    except Exception:
        pass
    generated = getattr(asset, "generated_class", None)
    if generated:
        return generated
    raise RuntimeError(f"Failed to resolve generated class for {object_path(asset)}")


result = {
    "map_path": MAP_PATH,
    "source_gamemode": SOURCE_GAMEMODE_PATH,
    "clone_gamemode": CLONE_GAMEMODE_PATH,
    "clone_pawn": CLONE_PAWN_PATH,
    "gamemode_cloned": False,
    "gamemode_saved": False,
    "level_saved": False,
    "clone_gamemode_generated_class": "",
    "clone_pawn_generated_class": "",
    "error": "",
}

try:
    if not unreal.EditorAssetLibrary.does_asset_exist(CLONE_GAMEMODE_PATH):
        if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE_GAMEMODE_PATH, CLONE_GAMEMODE_PATH):
            raise RuntimeError(
                f"Failed to duplicate {SOURCE_GAMEMODE_PATH} -> {CLONE_GAMEMODE_PATH}"
            )
        result["gamemode_cloned"] = True

    clone_gamemode_asset = load_asset(CLONE_GAMEMODE_PATH)
    clone_pawn_asset = load_asset(CLONE_PAWN_PATH)
    clone_gamemode_class = generated_class_of(clone_gamemode_asset)
    clone_pawn_class = generated_class_of(clone_pawn_asset)

    result["clone_gamemode_generated_class"] = object_path(clone_gamemode_class)
    result["clone_pawn_generated_class"] = object_path(clone_pawn_class)

    gamemode_cdo = unreal.get_default_object(clone_gamemode_class)
    gamemode_cdo.set_editor_property("default_pawn_class", clone_pawn_class)
    gamemode_cdo.modify()
    try:
        clone_gamemode_asset.get_outermost().mark_package_dirty()
    except Exception:
        pass
    result["gamemode_saved"] = bool(
        unreal.EditorAssetLibrary.save_loaded_asset(clone_gamemode_asset, False)
    )

    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    world = unreal.EditorLevelLibrary.get_editor_world()
    if not world:
        raise RuntimeError(f"Failed to load world for {MAP_PATH}")

    world_settings = world.get_world_settings()
    if not world_settings:
        raise RuntimeError("WorldSettings not found")

    world_settings.modify()
    world_settings.set_editor_property("default_game_mode", clone_gamemode_class)
    try:
        world.get_outermost().mark_package_dirty()
    except Exception:
        pass
    result["level_saved"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())

except Exception as exc:
    result["error"] = str(exc)

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, ensure_ascii=False)

print(OUT_PATH)
