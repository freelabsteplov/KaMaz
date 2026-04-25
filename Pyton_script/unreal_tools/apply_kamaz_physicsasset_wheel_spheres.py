import json
import os

import unreal


PHYSICS_ASSET_PATH = "/Game/CityPark/Kamaz/model/kamaz_ue5_PhysicsAsset"
TARGET_BONES = ["WFL", "WFR", "WRL", "WRR"]
TARGET_RADIUS_CM = 30.0
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "apply_kamaz_physicsasset_wheel_spheres.json",
)


def _normalize_bridge_result(raw_result):
    if isinstance(raw_result, bool):
        return raw_result, "", ""

    if not isinstance(raw_result, tuple):
        raise TypeError(f"Unexpected bridge result type: {type(raw_result)!r}")

    success = None
    strings = []
    for item in raw_result:
        if isinstance(item, bool):
            success = item
        elif isinstance(item, str):
            strings.append(item)

    if success is None:
        raise TypeError(f"Bridge result does not contain a bool status: {raw_result!r}")

    while len(strings) < 2:
        strings.append("")

    return success, strings[0], strings[1]


def main():
    payload = {
        "physics_asset_path": PHYSICS_ASSET_PATH,
        "target_bones": TARGET_BONES,
        "target_radius_cm": TARGET_RADIUS_CM,
        "success": False,
        "summary": "",
        "results": None,
        "error": "",
    }

    try:
        bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
        if bridge is None:
            raise RuntimeError("BlueprintAutomationPythonBridge is unavailable")

        raw_result = bridge.set_physics_asset_wheel_sphere_radius(
            PHYSICS_ASSET_PATH,
            TARGET_BONES,
            TARGET_RADIUS_CM,
        )
        success, result_json, summary = _normalize_bridge_result(raw_result)
        payload["success"] = bool(success)
        payload["summary"] = summary
        if result_json:
            payload["results"] = json.loads(result_json)
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
