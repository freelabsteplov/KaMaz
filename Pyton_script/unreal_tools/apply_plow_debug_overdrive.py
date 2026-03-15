import json
import os

import unreal


OUTPUT_BASENAME = "apply_plow_debug_overdrive"
MASTER_MATERIAL_PATH = "/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush_BoxSafe"
DEBUG_INSTANCE_PATH = "/Game/CityPark/SnowSystem/BrushMaterials/MI_Snow_PlowBrush_BoxSafe_DebugHuge"
PLOW_BLUEPRINT_PATH = "/Game/CityPark/SnowSystem/BP_PlowBrush_Component"

DEBUG_BRUSH_LENGTH_CM = 6000.0
DEBUG_BRUSH_WIDTH_CM = 18000.0
DEBUG_BRUSH_HEIGHT_CM = 3000.0
DEBUG_BRUSH_STRENGTH = 128.0

DEBUG_MIN_PLOW_SPEED = -1.0
DEBUG_UPDATE_RATE = 0.0
DEBUG_PLOW_LIFT_HEIGHT = 0.0
DEBUG_ENABLE_PLOW_CLEARING = True

ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
ASSET_LIB = unreal.EditorAssetLibrary
MATERIAL_LIB = unreal.MaterialEditingLibrary


def _log(message: str) -> None:
    unreal.log(f"[apply_plow_debug_overdrive] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[apply_plow_debug_overdrive] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_path(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _ensure_directory(package_path: str) -> None:
    if not ASSET_LIB.does_directory_exist(package_path):
        ASSET_LIB.make_directory(package_path)


def _resolve_generated_class(blueprint):
    candidate = getattr(blueprint, "generated_class", None)
    if callable(candidate):
        try:
            candidate = candidate()
        except Exception:
            candidate = None
    if candidate is None:
        try:
            candidate = blueprint.get_editor_property("generated_class")
        except Exception:
            candidate = None
    return candidate


def _decode_bridge_compile_result(raw_result):
    payload = {
        "compiled": False,
        "compile_summary": "",
        "compile_json": "",
    }
    if isinstance(raw_result, tuple):
        for item in raw_result:
            if isinstance(item, bool):
                payload["compiled"] = item
            elif isinstance(item, str):
                if not payload["compile_json"]:
                    payload["compile_json"] = item
                else:
                    payload["compile_summary"] = item
        return payload
    if isinstance(raw_result, bool):
        payload["compiled"] = raw_result
        return payload
    payload["compile_summary"] = str(raw_result)
    return payload


def _load_or_create_material_instance(asset_path: str):
    existing = ASSET_LIB.load_asset(asset_path)
    if existing is not None:
        return existing, False

    package_path, asset_name = asset_path.rsplit("/", 1)
    _ensure_directory(package_path)
    instance = ASSET_TOOLS.create_asset(
        asset_name,
        package_path,
        unreal.MaterialInstanceConstant,
        unreal.MaterialInstanceConstantFactoryNew(),
    )
    if instance is None:
        raise RuntimeError(f"Failed to create material instance: {asset_path}")
    return instance, True


def _safe_set_property(obj, property_name: str, value) -> dict:
    result = {
        "property": property_name,
        "applied": False,
        "before": None,
        "after": None,
        "error": "",
    }
    try:
        before = obj.get_editor_property(property_name)
        result["before"] = _object_path(before) if not isinstance(before, (bool, int, float, str)) else before
    except Exception as exc:
        result["error"] = f"get_before: {exc}"

    try:
        obj.set_editor_property(property_name, value)
        after = obj.get_editor_property(property_name)
        result["after"] = _object_path(after) if not isinstance(after, (bool, int, float, str)) else after
        result["applied"] = True
    except Exception as exc:
        result["error"] = f"{result['error']} | set: {exc}".strip(" |")
    return result


def _prepare_debug_material_instance() -> dict:
    master = ASSET_LIB.load_asset(MASTER_MATERIAL_PATH)
    if master is None:
        raise RuntimeError(f"Missing master material: {MASTER_MATERIAL_PATH}")

    instance, created = _load_or_create_material_instance(DEBUG_INSTANCE_PATH)
    instance.set_editor_property("parent", master)
    MATERIAL_LIB.set_material_instance_scalar_parameter_value(instance, "BrushLengthCm", DEBUG_BRUSH_LENGTH_CM)
    MATERIAL_LIB.set_material_instance_scalar_parameter_value(instance, "BrushWidthCm", DEBUG_BRUSH_WIDTH_CM)
    MATERIAL_LIB.set_material_instance_scalar_parameter_value(instance, "BrushHeightCm", DEBUG_BRUSH_HEIGHT_CM)
    MATERIAL_LIB.set_material_instance_scalar_parameter_value(instance, "BrushStrength", DEBUG_BRUSH_STRENGTH)
    saved = bool(ASSET_LIB.save_loaded_asset(instance, False))
    return {
        "master_material": _object_path(master),
        "instance_path": DEBUG_INSTANCE_PATH,
        "instance_object_path": _object_path(instance),
        "created": created,
        "saved": saved,
        "dimensions_cm": {
            "length": DEBUG_BRUSH_LENGTH_CM,
            "width": DEBUG_BRUSH_WIDTH_CM,
            "height": DEBUG_BRUSH_HEIGHT_CM,
        },
        "brush_strength": DEBUG_BRUSH_STRENGTH,
    }


def _apply_debug_defaults_to_plow_blueprint() -> dict:
    blueprint = ASSET_LIB.load_asset(PLOW_BLUEPRINT_PATH)
    instance = ASSET_LIB.load_asset(DEBUG_INSTANCE_PATH)
    if blueprint is None:
        raise RuntimeError(f"Missing blueprint: {PLOW_BLUEPRINT_PATH}")
    if instance is None:
        raise RuntimeError(f"Missing debug instance: {DEBUG_INSTANCE_PATH}")

    generated_class = _resolve_generated_class(blueprint)
    if generated_class is None:
        raise RuntimeError(f"Could not resolve generated class for {PLOW_BLUEPRINT_PATH}")

    default_object = unreal.get_default_object(generated_class)
    property_results = []
    property_results.append(_safe_set_property(default_object, "BrushMaterial", instance))
    property_results.append(_safe_set_property(default_object, "bEnablePlowClearing", DEBUG_ENABLE_PLOW_CLEARING))
    property_results.append(_safe_set_property(default_object, "MinPlowSpeed", DEBUG_MIN_PLOW_SPEED))
    property_results.append(_safe_set_property(default_object, "UpdateRate", DEBUG_UPDATE_RATE))
    property_results.append(_safe_set_property(default_object, "PlowLiftHeight", DEBUG_PLOW_LIFT_HEIGHT))

    bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
    compile_payload = {
        "compiled": False,
        "compile_summary": "",
        "compile_json": "",
    }
    if bridge is not None:
        try:
            compile_payload = _decode_bridge_compile_result(bridge.compile_blueprint(PLOW_BLUEPRINT_PATH))
        except Exception as exc:
            compile_payload["compile_summary"] = f"compile_blueprint raised: {exc}"
            _warn(compile_payload["compile_summary"])
    else:
        try:
            unreal.KismetEditorUtilities.compile_blueprint(blueprint)
            compile_payload["compiled"] = True
            compile_payload["compile_summary"] = "Compiled via KismetEditorUtilities.compile_blueprint"
        except Exception as exc:
            compile_payload["compile_summary"] = f"Kismet compile failed: {exc}"
            _warn(compile_payload["compile_summary"])

    saved = bool(ASSET_LIB.save_loaded_asset(blueprint, False))
    return {
        "blueprint_path": PLOW_BLUEPRINT_PATH,
        "generated_class": _object_path(generated_class),
        "default_object": _object_path(default_object),
        "property_results": property_results,
        "compiled": compile_payload["compiled"],
        "compile_summary": compile_payload["compile_summary"],
        "compile_json": compile_payload["compile_json"],
        "saved": saved,
    }


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    result = {
        "success": False,
        "summary": "",
        "notes": [
            "This is a temporary debug overdrive for snow/plow validation.",
            "It uses a separate debug material instance instead of overwriting the original box preset.",
            "It does not modify Kamaz input or MOZA input assets.",
        ],
    }
    try:
        material_result = _prepare_debug_material_instance()
        blueprint_result = _apply_debug_defaults_to_plow_blueprint()
        applied_properties = [entry for entry in blueprint_result["property_results"] if entry.get("applied")]
        result.update(
            {
                "material_result": material_result,
                "blueprint_result": blueprint_result,
            }
        )
        result["success"] = bool(material_result.get("saved") and blueprint_result.get("saved"))
        result["summary"] = (
            f"Applied plow debug overdrive using {DEBUG_INSTANCE_PATH}; "
            f"bp_saved={blueprint_result.get('saved')} compiled={blueprint_result.get('compiled')} "
            f"properties_applied={len(applied_properties)}/{len(blueprint_result['property_results'])}"
        )
    except Exception as exc:
        result["success"] = False
        result["error"] = str(exc)
        result["summary"] = f"Failed to apply plow debug overdrive: {exc}"
        _warn(result["summary"])

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary() -> str:
    result = run()
    summary = result.get("summary", "")
    _log(summary)
    _log(f"summary_path={result.get('output_path', '')}")
    return summary


if __name__ == "__main__":
    print(run())
