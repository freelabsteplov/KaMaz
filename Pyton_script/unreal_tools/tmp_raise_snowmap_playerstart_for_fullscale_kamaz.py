import json
import os

import unreal


MAP_PATH = "/Game/LandscapeDeformation/Maps/SnowMap"
TARGET_PLAYERSTART_NAME = "PlayerStart_1"
Z_OFFSET_CM = 300.0
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "tmp_raise_snowmap_playerstart_for_fullscale_kamaz.json",
)


def _vec(value):
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def main():
    payload = {
        "map_path": MAP_PATH,
        "player_start_name": TARGET_PLAYERSTART_NAME,
        "z_offset_cm": Z_OFFSET_CM,
        "before_location": None,
        "after_location": None,
        "saved": False,
        "error": "",
    }

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        actors = list(unreal.EditorLevelLibrary.get_all_level_actors() or [])
        player_start = next(
            (actor for actor in actors if actor.get_name() == TARGET_PLAYERSTART_NAME and actor.get_class().get_name() == "PlayerStart"),
            None,
        )
        if player_start is None:
            raise RuntimeError(f"Could not find {TARGET_PLAYERSTART_NAME} on {MAP_PATH}")

        before_location = player_start.get_actor_location()
        payload["before_location"] = _vec(before_location)

        new_location = unreal.Vector(
            float(before_location.x),
            float(before_location.y),
            float(before_location.z + Z_OFFSET_CM),
        )

        player_start.modify()
        player_start.set_actor_location(new_location, False, False)
        payload["after_location"] = _vec(player_start.get_actor_location())
        payload["saved"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
