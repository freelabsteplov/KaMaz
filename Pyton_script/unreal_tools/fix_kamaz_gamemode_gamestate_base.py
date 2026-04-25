import json
import os

import unreal


BLUEPRINT_PATH = "/Game/BPs/BP_KamazGameMode"
EXPECTED_GAME_STATE_CLASS = "/Script/Engine.GameStateBase"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "fix_kamaz_gamemode_gamestate_base.json",
)


def _object_path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _decode_bridge_result(raw):
    payload = {
        "success": None,
        "json": "",
        "summary": "",
        "raw_repr": repr(raw),
    }

    if isinstance(raw, tuple):
        for item in raw:
            if isinstance(item, bool):
                payload["success"] = item
            elif isinstance(item, str):
                if not payload["json"]:
                    payload["json"] = item
                elif not payload["summary"]:
                    payload["summary"] = item
    elif isinstance(raw, bool):
        payload["success"] = raw
    elif isinstance(raw, str):
        payload["summary"] = raw

    if payload["json"]:
        try:
            payload["result"] = json.loads(payload["json"])
        except Exception:
            payload["result"] = {"raw": payload["json"]}
    else:
        payload["result"] = {}

    return payload


def _compile_with_bridge(asset_path):
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None or not hasattr(bridge, "compile_blueprint"):
        return {"available": False, "success": None, "summary": "compile_blueprint bridge unavailable"}
    return _decode_bridge_result(bridge.compile_blueprint(asset_path))


def _set_property_with_bridge(asset_path, property_name, value_as_string):
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None or not hasattr(bridge, "set_blueprint_property_value"):
        raise RuntimeError("set_blueprint_property_value bridge unavailable")
    return _decode_bridge_result(
        bridge.set_blueprint_property_value(
            asset_path,
            "",
            property_name,
            value_as_string,
            False,
        )
    )


def main():
    result = {
        "blueprint_path": BLUEPRINT_PATH,
        "expected_game_state_class": EXPECTED_GAME_STATE_CLASS,
        "before_game_state_class": "",
        "after_game_state_class": "",
        "set_property": {},
        "compile": {},
        "saved": False,
        "error": "",
    }

    try:
        bp_asset = unreal.EditorAssetLibrary.load_asset(BLUEPRINT_PATH)
        if not bp_asset:
            raise RuntimeError(f"Failed to load blueprint asset: {BLUEPRINT_PATH}")

        bp_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT_PATH)
        if not bp_class:
            raise RuntimeError(f"Failed to load blueprint class: {BLUEPRINT_PATH}")

        cdo = unreal.get_default_object(bp_class)
        if not cdo:
            raise RuntimeError(f"Failed to resolve class default object: {BLUEPRINT_PATH}")

        before_value = cdo.get_editor_property("game_state_class")
        result["before_game_state_class"] = _object_path(before_value)

        result["set_property"] = _set_property_with_bridge(
            BLUEPRINT_PATH,
            "GameStateClass",
            EXPECTED_GAME_STATE_CLASS,
        )

        bp_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT_PATH)
        cdo = unreal.get_default_object(bp_class) if bp_class else None
        after_value = cdo.get_editor_property("game_state_class") if cdo else None
        result["after_game_state_class"] = _object_path(after_value)

        result["compile"] = _compile_with_bridge(BLUEPRINT_PATH)
        result["saved"] = bool(result["set_property"].get("result", {}).get("saved", False))

    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
