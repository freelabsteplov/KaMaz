import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
TARGET_ACTOR_PATHS = [
    "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208",
    "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_188",
    "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_142",
]
OUTPUT_BASENAME = "attach_snow_receiver_surface_to_spawn_zone_roads"
RECEIVER_SET_TAG = "SpawnZoneRoads"
BRIDGE = getattr(unreal, "BlueprintAutomationPythonBridge", None)


def _log(message: str) -> None:
    unreal.log(f"[attach_snow_receiver_surface_to_spawn_zone_roads] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _decode_json(payload: str):
    if not payload:
        return None
    return json.loads(payload)


def _normalize_bridge_result(raw_result, expected_string_count: int):
    if isinstance(raw_result, bool):
        return raw_result, [""] * expected_string_count

    if isinstance(raw_result, tuple):
        success = None
        strings = []
        for item in raw_result:
            if isinstance(item, bool):
                success = item
            elif isinstance(item, str):
                strings.append(item)
        if success is None:
            success = True
        while len(strings) < expected_string_count:
            strings.append("")
        return success, strings[:expected_string_count]

    raise TypeError(f"Unexpected bridge result: {type(raw_result)!r} {raw_result!r}")


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    if BRIDGE is None:
        raise RuntimeError("BlueprintAutomationPythonBridge is unavailable in this editor session.")

    raw_result = BRIDGE.ensure_snow_receiver_surfaces_on_actors(
        MAP_PATH,
        TARGET_ACTOR_PATHS,
        unreal.SnowReceiverSurfaceFamily.ROAD,
        100,
        RECEIVER_SET_TAG,
        True,
        True,
    )
    success, [result_json, summary] = _normalize_bridge_result(raw_result, 2)
    bridge_payload = _decode_json(result_json) if result_json else {}
    result = dict(bridge_payload or {})
    result["success"] = bool(success and result.get("bSuccess", result.get("success", False)))
    result["bridge_summary"] = summary

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary() -> str:
    result = run()
    summary = (
        f"attach_snow_receiver_surface_to_spawn_zone_roads "
        f"created={result.get('CreatedCount', result.get('created_count'))} "
        f"configured={result.get('ConfiguredCount', result.get('configured_count'))} "
        f"success={result.get('success')}"
    )
    _log(summary)
    _log(f"summary_path={result.get('output_path', '')}")
    return summary


if __name__ == "__main__":
    print(run())
