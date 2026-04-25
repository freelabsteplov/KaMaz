import json
import os
import re

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "fix_moscowea5_playerstart.json",
)

DEFAULT_TRACE_HEIGHT = 5000.0
DEFAULT_TRACE_DEPTH = 25000.0
PLAYERSTART_Z_PADDING = 5.0
FALLBACK_VIEW_XYZ = (-83566.072225, -151863.753235, -198531.098248)
FALLBACK_VIEW_YAW = 362.600008


def _safe_path(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _safe_name(obj) -> str:
    if obj is None:
        return ""
    try:
        return obj.get_name()
    except Exception:
        return str(obj)


def _vec_dict(vec) -> dict:
    return {
        "x": float(vec.x),
        "y": float(vec.y),
        "z": float(vec.z),
    }


def _rot_dict(rot) -> dict:
    return {
        "pitch": float(rot.pitch),
        "yaw": float(rot.yaw),
        "roll": float(rot.roll),
    }


def _write_json(payload: dict) -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    unreal.log(f"[fix_moscowea5_playerstart] Wrote file: {OUTPUT_PATH}")


def _iter_playerstarts() -> list:
    actors = list(unreal.EditorLevelLibrary.get_all_level_actors() or [])
    result = []
    playerstart_class = unreal.PlayerStart.static_class()
    for actor in actors:
        if actor is None:
            continue
        try:
            actor_class = actor.get_class()
            if actor_class and actor_class.is_child_of(playerstart_class):
                result.append(actor)
        except Exception:
            continue
    return result


def _capsule_half_height(actor) -> float:
    try:
        capsule = actor.get_component_by_class(unreal.CapsuleComponent)
        if capsule:
            return float(capsule.get_editor_property("capsule_half_height"))
    except Exception:
        pass
    return 88.0


def _load_editor_view_xyz() -> tuple[float, float, float, float]:
    ini_path = os.path.join(
        unreal.Paths.project_saved_dir(),
        "Config",
        "WindowsEditor",
        "EditorPerProjectUserSettings.ini",
    )
    try:
        with open(ini_path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except Exception:
        return (
            FALLBACK_VIEW_XYZ[0],
            FALLBACK_VIEW_XYZ[1],
            FALLBACK_VIEW_XYZ[2],
            FALLBACK_VIEW_YAW,
        )

    pattern = (
        r'/Game/Maps/MoscowEA5\.MoscowEA5".*?'
        r'CamPosition=\(X=([-0-9.]+),Y=([-0-9.]+),Z=([-0-9.]+)\),'
        r'CamRotation=\(Pitch=([-0-9.]+),Yaw=([-0-9.]+),Roll=([-0-9.]+)\)'
    )
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return (
            FALLBACK_VIEW_XYZ[0],
            FALLBACK_VIEW_XYZ[1],
            FALLBACK_VIEW_XYZ[2],
            FALLBACK_VIEW_YAW,
        )

    try:
        return (
            float(match.group(1)),
            float(match.group(2)),
            float(match.group(3)),
            float(match.group(5)),
        )
    except Exception:
        return (
            FALLBACK_VIEW_XYZ[0],
            FALLBACK_VIEW_XYZ[1],
            FALLBACK_VIEW_XYZ[2],
            FALLBACK_VIEW_YAW,
        )


def _trace_ground(world, xyz_source: tuple[float, float, float], ignore_actors: list) -> dict:
    start = unreal.Vector(xyz_source[0], xyz_source[1], xyz_source[2] + DEFAULT_TRACE_HEIGHT)
    end = unreal.Vector(xyz_source[0], xyz_source[1], xyz_source[2] - DEFAULT_TRACE_DEPTH)
    trace_result = unreal.SystemLibrary.line_trace_single(
        world,
        start,
        end,
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
        False,
        ignore_actors,
        unreal.DrawDebugTrace.NONE,
        False,
        unreal.LinearColor(1.0, 0.0, 0.0, 1.0),
        unreal.LinearColor(0.0, 1.0, 0.0, 1.0),
        0.0,
    )
    if isinstance(trace_result, tuple):
        hit_result = trace_result[1] if len(trace_result) > 1 else None
    else:
        hit_result = trace_result

    if hit_result is None or not hit_result.is_valid_blocking_hit():
        return {
            "success": False,
            "trace_start": _vec_dict(start),
            "trace_end": _vec_dict(end),
            "hit_actor_path": "",
            "hit_actor_label": "",
            "hit_location": None,
        }

    hit_actor = hit_result.get_actor()
    return {
        "success": True,
        "trace_start": _vec_dict(start),
        "trace_end": _vec_dict(end),
        "hit_actor_path": _safe_path(hit_actor),
        "hit_actor_label": hit_actor.get_actor_label() if hit_actor else "",
        "hit_location": _vec_dict(hit_result.location),
    }


def _best_trace(world, existing_playerstart, ignore_actors: list) -> dict:
    candidates = []
    if existing_playerstart:
        loc = existing_playerstart.get_actor_location()
        candidates.append(
            {
                "source": "existing_playerstart_xyz",
                "xyz": (float(loc.x), float(loc.y), float(loc.z)),
                "yaw": float(existing_playerstart.get_actor_rotation().yaw),
            }
        )

    view_x, view_y, view_z, view_yaw = _load_editor_view_xyz()
    candidates.append(
        {
            "source": "saved_editor_view_xyz",
            "xyz": (float(view_x), float(view_y), float(view_z)),
            "yaw": float(view_yaw),
        }
    )

    for candidate in candidates:
        trace = _trace_ground(world, candidate["xyz"], ignore_actors)
        trace["source"] = candidate["source"]
        trace["yaw"] = float(candidate.get("yaw", FALLBACK_VIEW_YAW))
        if trace["success"]:
            return trace

    return {
        "success": False,
        "source": "",
        "yaw": FALLBACK_VIEW_YAW,
        "trace_start": None,
        "trace_end": None,
        "hit_actor_path": "",
        "hit_actor_label": "",
        "hit_location": None,
    }


def main():
    result = {
        "map_path": MAP_PATH,
        "map_loaded": False,
        "playerstart_found": False,
        "playerstart_created": False,
        "playerstart_path": "",
        "before_location": None,
        "before_rotation": None,
        "trace": {},
        "after_location": None,
        "after_rotation": None,
        "saved": False,
        "error": "",
    }

    try:
        if not unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
            raise RuntimeError(f"Map asset does not exist: {MAP_PATH}")

        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
        result["map_loaded"] = True

        world = unreal.EditorLevelLibrary.get_editor_world()
        if world is None:
            raise RuntimeError("Editor world is unavailable")

        playerstarts = _iter_playerstarts()
        playerstart = playerstarts[0] if playerstarts else None
        result["playerstart_found"] = playerstart is not None

        if playerstart is None:
            playerstart = unreal.EditorLevelLibrary.spawn_actor_from_class(
                unreal.PlayerStart,
                unreal.Vector(FALLBACK_VIEW_XYZ[0], FALLBACK_VIEW_XYZ[1], FALLBACK_VIEW_XYZ[2]),
                unreal.Rotator(0.0, FALLBACK_VIEW_YAW, 0.0),
            )
            if playerstart is None:
                raise RuntimeError("Failed to spawn PlayerStart")
            playerstart.set_actor_label("PlayerStart")
            result["playerstart_created"] = True

        result["playerstart_path"] = _safe_path(playerstart)
        result["before_location"] = _vec_dict(playerstart.get_actor_location())
        result["before_rotation"] = _rot_dict(playerstart.get_actor_rotation())

        trace = _best_trace(world, playerstart, [playerstart])
        result["trace"] = trace
        if not trace.get("success"):
            raise RuntimeError("Could not find valid ground trace for PlayerStart")

        hit_location = trace["hit_location"]
        half_height = _capsule_half_height(playerstart)
        new_location = unreal.Vector(
            float(hit_location["x"]),
            float(hit_location["y"]),
            float(hit_location["z"]) + half_height + PLAYERSTART_Z_PADDING,
        )
        new_rotation = unreal.Rotator(0.0, float(trace.get("yaw", FALLBACK_VIEW_YAW)), 0.0)

        playerstart.set_actor_location(new_location, False, False)
        playerstart.set_actor_rotation(new_rotation, False)

        result["after_location"] = _vec_dict(playerstart.get_actor_location())
        result["after_rotation"] = _rot_dict(playerstart.get_actor_rotation())

        save_ok = unreal.EditorLevelLibrary.save_current_level()
        result["saved"] = bool(save_ok)
        if not save_ok:
            raise RuntimeError("Failed to save MoscowEA5")

    except Exception as exc:
        result["error"] = str(exc)
        unreal.log_error(f"[fix_moscowea5_playerstart] {exc}")

    _write_json(result)
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
