import json
import os

import unreal


FRONT_WHEEL_BP = "/Game/CityPark/Kamaz/model/Front_wheels"
REAR_WHEEL_BP = "/Game/CityPark/Kamaz/model/Rear_wheels"
TARGET_WHEEL_RADIUS_CM = 50.0
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "apply_kamaz_wheel_radius_cosmetics.json",
)


def _path(obj):
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _normalize_bridge_result(raw_result, expected_string_count):
    if isinstance(raw_result, bool):
        return raw_result, [""] * expected_string_count

    if isinstance(raw_result, str):
        strings = [raw_result]
        while len(strings) < expected_string_count:
            strings.append("")
        return True, strings[:expected_string_count]

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
        success = True

    while len(strings) < expected_string_count:
        strings.append("")

    return success, strings[:expected_string_count]


def _compile_blueprint(blueprint_path):
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None or not hasattr(bridge, "compile_blueprint"):
        return {
            "success": False,
            "method": "BlueprintAutomationPythonBridge.compile_blueprint",
            "summary": "BlueprintAutomationPythonBridge.compile_blueprint is unavailable",
            "payload": "",
        }

    try:
        success, [payload, summary] = _normalize_bridge_result(
            bridge.compile_blueprint(blueprint_path),
            2,
        )
        return {
            "success": bool(success),
            "method": "BlueprintAutomationPythonBridge.compile_blueprint",
            "summary": summary,
            "payload": payload,
        }
    except Exception as exc:
        return {
            "success": False,
            "method": "BlueprintAutomationPythonBridge.compile_blueprint",
            "summary": f"compile_blueprint raised: {exc}",
            "payload": "",
        }


def _save_blueprint(blueprint_path):
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None or not hasattr(bridge, "save_blueprint"):
        return {
            "success": False,
            "method": "BlueprintAutomationPythonBridge.save_blueprint",
            "summary": "BlueprintAutomationPythonBridge.save_blueprint is unavailable",
        }

    try:
        success, [summary] = _normalize_bridge_result(
            bridge.save_blueprint(blueprint_path),
            1,
        )
        return {
            "success": bool(success),
            "method": "BlueprintAutomationPythonBridge.save_blueprint",
            "summary": summary,
        }
    except Exception as exc:
        return {
            "success": False,
            "method": "BlueprintAutomationPythonBridge.save_blueprint",
            "summary": f"save_blueprint raised: {exc}",
        }


def _wheel_blueprint_entry(blueprint_path):
    blueprint = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if blueprint is None:
        raise RuntimeError(f"Could not load blueprint: {blueprint_path}")

    generated_class = getattr(blueprint, "generated_class", None)
    if callable(generated_class):
        generated_class = generated_class()
    if generated_class is None:
        raise RuntimeError(f"Could not resolve generated class: {blueprint_path}")

    cdo = unreal.get_default_object(generated_class)
    before_radius = float(cdo.get_editor_property("wheel_radius"))
    cdo.set_editor_property("wheel_radius", TARGET_WHEEL_RADIUS_CM)
    compile_result = _compile_blueprint(blueprint_path)
    save_result = _save_blueprint(blueprint_path)

    return {
        "blueprint_path": blueprint_path,
        "generated_class": _path(generated_class),
        "default_object": _path(cdo),
        "wheel_radius_before": before_radius,
        "wheel_radius_after": float(cdo.get_editor_property("wheel_radius")),
        "compile": compile_result,
        "save": save_result,
    }

def main():
    payload = {
        "target_wheel_radius_cm": TARGET_WHEEL_RADIUS_CM,
        "front": {},
        "rear": {},
        "error": "",
    }

    try:
        payload["front"] = _wheel_blueprint_entry(FRONT_WHEEL_BP)
        payload["rear"] = _wheel_blueprint_entry(REAR_WHEEL_BP)
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
