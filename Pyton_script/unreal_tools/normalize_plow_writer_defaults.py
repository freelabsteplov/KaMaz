import json
import os

import unreal


OUTPUT_BASENAME = "normalize_plow_writer_defaults"

PLOW_BLUEPRINT_PATH = "/Game/CityPark/SnowSystem/BP_PlowBrush_Component"
KAMAZ_BLUEPRINT_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
KAMAZ_PLOW_COMPONENT_NAME = "BP_PlowBrush_Component"

CANONICAL_PLOW_BRUSH_MATERIAL = "/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush.M_Snow_PlowBrush"

CANONICAL_CDO_VALUES = [
    {"property_name": "RenderTargetGlobal", "value_as_string": ""},
    {"property_name": "BrushMaterial", "value_as_string": CANONICAL_PLOW_BRUSH_MATERIAL},
    {"property_name": "BrushDMI", "value_as_string": ""},
    {"property_name": "bEnablePlowClearing", "value_as_string": "true"},
    {"property_name": "MinPlowSpeed", "value_as_string": "2.0"},
    {"property_name": "UpdateRate", "value_as_string": "0.05"},
    {"property_name": "PlowLiftHeight", "value_as_string": "1.0"},
]

CANONICAL_KAMAZ_TEMPLATE_VALUES = [
    {"property_name": "RenderTargetGlobal", "value_as_string": ""},
    {"property_name": "BrushMaterial", "value_as_string": CANONICAL_PLOW_BRUSH_MATERIAL},
    {"property_name": "BrushDMI", "value_as_string": ""},
    {"property_name": "bEnablePlowClearing", "value_as_string": "true"},
    {"property_name": "MinPlowSpeed", "value_as_string": "2.0"},
    {"property_name": "UpdateRate", "value_as_string": "0.05"},
    {"property_name": "PlowLiftHeight", "value_as_string": "1.0"},
]


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return path


def _decode_bridge_result(raw_result):
    payload = {
        "success": False,
        "json": "",
        "summary": "",
        "raw_repr": repr(raw_result),
    }

    if isinstance(raw_result, tuple):
        string_items = []
        for item in raw_result:
            if isinstance(item, bool):
                payload["success"] = item
            elif isinstance(item, str):
                string_items.append(item)
        for item in string_items:
            stripped = item.lstrip()
            if not payload["json"] and stripped.startswith("{"):
                payload["json"] = item
            elif not payload["summary"]:
                payload["summary"] = item
        if payload["json"]:
            try:
                parsed = json.loads(payload["json"])
                if isinstance(parsed, dict) and "success" in parsed:
                    payload["success"] = bool(parsed["success"])
            except Exception:
                pass
        return payload

    if isinstance(raw_result, bool):
        payload["success"] = raw_result
        return payload

    if isinstance(raw_result, str):
        stripped = raw_result.lstrip()
        if stripped.startswith("{"):
            payload["json"] = raw_result
            try:
                parsed = json.loads(raw_result)
                if isinstance(parsed, dict) and "success" in parsed:
                    payload["success"] = bool(parsed["success"])
            except Exception:
                payload["summary"] = raw_result
        else:
            payload["summary"] = raw_result
        return payload

    payload["summary"] = str(raw_result)
    return payload


def _apply_batch(blueprint_path: str, component_name: str, is_component_template: bool, operations: list[dict]) -> dict:
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None or not hasattr(bridge, "set_blueprint_properties_batch_json"):
        raise RuntimeError("BlueprintAutomationPythonBridge.set_blueprint_properties_batch_json is unavailable")

    raw = bridge.set_blueprint_properties_batch_json(
        blueprint_path,
        component_name,
        json.dumps({"operations": operations}, ensure_ascii=False),
        bool(is_component_template),
    )
    decoded = _decode_bridge_result(raw)
    payload = {
        "blueprint_path": blueprint_path,
        "component_name": component_name,
        "is_component_template": bool(is_component_template),
        "success": bool(decoded["success"]),
        "summary": decoded["summary"],
        "result_json": decoded["json"],
        "raw_repr": decoded["raw_repr"],
        "result": {},
    }

    if decoded["json"]:
        try:
            payload["result"] = json.loads(decoded["json"])
        except Exception:
            payload["result"] = {"raw": decoded["json"]}
    return payload


def _apply_single(blueprint_path: str, component_name: str, is_component_template: bool, operation: dict) -> dict:
    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    if bridge is None or not hasattr(bridge, "set_blueprint_property_value"):
        raise RuntimeError("BlueprintAutomationPythonBridge.set_blueprint_property_value is unavailable")

    raw = bridge.set_blueprint_property_value(
        blueprint_path,
        component_name,
        operation["property_name"],
        operation["value_as_string"],
        bool(is_component_template),
    )
    decoded = _decode_bridge_result(raw)
    payload = {
        "blueprint_path": blueprint_path,
        "component_name": component_name,
        "is_component_template": bool(is_component_template),
        "property_name": operation["property_name"],
        "value_as_string": operation["value_as_string"],
        "success": bool(decoded["success"]),
        "summary": decoded["summary"],
        "result_json": decoded["json"],
        "raw_repr": decoded["raw_repr"],
        "result": {},
    }

    if decoded["json"]:
        try:
            payload["result"] = json.loads(decoded["json"])
        except Exception:
            payload["result"] = {"raw": decoded["json"]}
    return payload


def _apply_operations_serial(blueprint_path: str, component_name: str, is_component_template: bool, operations: list[dict]) -> dict:
    payload = {
        "blueprint_path": blueprint_path,
        "component_name": component_name,
        "is_component_template": bool(is_component_template),
        "success": True,
        "operations": [],
    }

    for operation in operations:
        entry = _apply_single(blueprint_path, component_name, is_component_template, operation)
        payload["operations"].append(entry)
        if not entry["success"]:
            payload["success"] = False

    return payload


def run_plow_component_cdo(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    result = {
        "success": False,
        "scope": "plow_component_cdo",
        "canonical_policy": {
            "blueprint_path": PLOW_BLUEPRINT_PATH,
            "canonical_brush_material": CANONICAL_PLOW_BRUSH_MATERIAL,
        },
        "serial_apply": {},
        "error": "",
    }

    try:
        result["serial_apply"] = _apply_operations_serial(PLOW_BLUEPRINT_PATH, "", False, CANONICAL_CDO_VALUES)
        result["success"] = bool(result["serial_apply"].get("success"))
    except Exception as exc:
        result["success"] = False
        result["error"] = str(exc)

    output_path = os.path.join(output_dir, "normalize_plow_component_cdo.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def run_kamaz_template(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    result = {
        "success": False,
        "scope": "kamaz_plow_component_template",
        "canonical_policy": {
            "blueprint_path": KAMAZ_BLUEPRINT_PATH,
            "component_name": KAMAZ_PLOW_COMPONENT_NAME,
            "canonical_brush_material": CANONICAL_PLOW_BRUSH_MATERIAL,
        },
        "serial_apply": {},
        "error": "",
    }

    try:
        result["serial_apply"] = _apply_operations_serial(
            KAMAZ_BLUEPRINT_PATH,
            KAMAZ_PLOW_COMPONENT_NAME,
            True,
            CANONICAL_KAMAZ_TEMPLATE_VALUES,
        )
        result["success"] = bool(result["serial_apply"].get("success"))
    except Exception as exc:
        result["success"] = False
        result["error"] = str(exc)

    output_path = os.path.join(output_dir, "normalize_kamaz_plow_template.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


if __name__ == "__main__":
    print(json.dumps(run_plow_component_cdo(), indent=2, ensure_ascii=False))
