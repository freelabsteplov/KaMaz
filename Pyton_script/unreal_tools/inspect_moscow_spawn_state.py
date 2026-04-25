import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
GAME_MODE_BP_PATH = "/Game/BPs/BP_KamazGameMode"
OUTPUT_NAME = "inspect_moscow_spawn_state.json"


def _safe_path(obj):
    return obj.get_path_name() if obj else ""


def _safe_name(obj):
    return obj.get_name() if obj else ""


def _write_output(payload):
    output_dir = os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, OUTPUT_NAME)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    unreal.log(f"[inspect_moscow_spawn_state] Wrote file: {output_path}")
    return output_path


def _actor_entry(actor):
    return {
        "label": actor.get_actor_label(),
        "path": actor.get_path_name(),
        "class": actor.get_class().get_path_name(),
        "location": {
            "x": actor.get_actor_location().x,
            "y": actor.get_actor_location().y,
            "z": actor.get_actor_location().z,
        },
        "rotation": {
            "pitch": actor.get_actor_rotation().pitch,
            "yaw": actor.get_actor_rotation().yaw,
            "roll": actor.get_actor_rotation().roll,
        },
    }


def main():
    payload = {
        "map_path": MAP_PATH,
        "map_loaded": False,
        "player_starts": [],
        "kamaz_like_actors": [],
        "game_mode": {},
        "error": "",
    }

    try:
        if not unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
            raise RuntimeError(f"Map asset does not exist: {MAP_PATH}")

        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        payload["map_loaded"] = True

        all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
        for actor in all_actors:
            actor_class_path = actor.get_class().get_path_name()
            actor_label = actor.get_actor_label()
            if "PlayerStart" in actor_class_path or "PlayerStart" in actor_label:
                payload["player_starts"].append(_actor_entry(actor))
                continue

            path = actor.get_path_name()
            if "Kamaz" in actor_label or "Kamaz" in path or "Kamaz" in actor_class_path:
                payload["kamaz_like_actors"].append(_actor_entry(actor))

        game_mode_bp = unreal.EditorAssetLibrary.load_asset(GAME_MODE_BP_PATH)
        if not game_mode_bp:
            raise RuntimeError(f"Could not load blueprint: {GAME_MODE_BP_PATH}")

        generated_class = game_mode_bp.generated_class()
        cdo = generated_class.get_default_object() if generated_class else None
        parent_class = None
        try:
            parent_class = game_mode_bp.get_editor_property("parent_class")
        except Exception:
            parent_class = None

        game_state_class = None
        default_pawn_class = None
        player_controller_class = None
        if cdo:
            try:
                game_state_class = cdo.get_editor_property("game_state_class")
            except Exception:
                game_state_class = None
            try:
                default_pawn_class = cdo.get_editor_property("default_pawn_class")
            except Exception:
                default_pawn_class = None
            try:
                player_controller_class = cdo.get_editor_property("player_controller_class")
            except Exception:
                player_controller_class = None

        payload["game_mode"] = {
            "blueprint_path": GAME_MODE_BP_PATH,
            "generated_class": _safe_path(generated_class),
            "parent_class": _safe_path(parent_class),
            "parent_class_name": _safe_name(parent_class),
            "class_default_object": _safe_path(cdo),
            "game_state_class": _safe_path(game_state_class),
            "default_pawn_class": _safe_path(default_pawn_class),
            "player_controller_class": _safe_path(player_controller_class),
        }

    except Exception as exc:
        payload["error"] = str(exc)
        unreal.log_error(f"[inspect_moscow_spawn_state] {exc}")

    output_path = _write_output(payload)
    print(output_path)


if __name__ == "__main__":
    main()
