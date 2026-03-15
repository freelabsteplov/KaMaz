import json
import os

import unreal


OUTPUT_BASENAME = "apply_existing_plow_box_brush"
PLOW_BLUEPRINT_PATH = "/Game/CityPark/SnowSystem/BP_PlowBrush_Component"
BOX_BRUSH_INSTANCE_PATH = "/Game/CityPark/SnowSystem/BrushMaterials/MI_Snow_PlowBrush_BoxSafe_350x50x100"

BRUSH_LENGTH_CM = 50.0
BRUSH_WIDTH_CM = 350.0
BRUSH_HEIGHT_CM = 100.0
BRUSH_STRENGTH = 1.0

MATERIAL_LIB = unreal.MaterialEditingLibrary
EDITOR_ASSETS = unreal.EditorAssetLibrary


def _log(message: str) -> None:
    unreal.log(f"[apply_existing_plow_box_brush] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[apply_existing_plow_box_brush] {message}")


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


def _apply_box_dimensions(instance) -> dict:
    MATERIAL_LIB.set_material_instance_scalar_parameter_value(instance, "BrushLengthCm", BRUSH_LENGTH_CM)
    MATERIAL_LIB.set_material_instance_scalar_parameter_value(instance, "BrushWidthCm", BRUSH_WIDTH_CM)
    MATERIAL_LIB.set_material_instance_scalar_parameter_value(instance, "BrushHeightCm", BRUSH_HEIGHT_CM)
    MATERIAL_LIB.set_material_instance_scalar_parameter_value(instance, "BrushStrength", BRUSH_STRENGTH)

    saved = False
    save_error = ""
    try:
        saved = bool(EDITOR_ASSETS.save_loaded_asset(instance, False))
    except Exception as exc:
        save_error = str(exc)

    return {
        "asset_path": BOX_BRUSH_INSTANCE_PATH,
        "saved": saved,
        "save_error": save_error,
        "requested_dimensions_cm": {
            "length": BRUSH_LENGTH_CM,
            "width": BRUSH_WIDTH_CM,
            "height": BRUSH_HEIGHT_CM,
        },
        "brush_strength": BRUSH_STRENGTH,
    }


def apply_existing_box_brush(output_dir: str = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    blueprint = EDITOR_ASSETS.load_asset(PLOW_BLUEPRINT_PATH)
    instance = EDITOR_ASSETS.load_asset(BOX_BRUSH_INSTANCE_PATH)

    result = {
        "blueprint_path": PLOW_BLUEPRINT_PATH,
        "brush_material_instance_path": BOX_BRUSH_INSTANCE_PATH,
        "success": False,
        "compiled": False,
        "saved": False,
        "before_brush_material": "",
        "after_brush_material": "",
        "compile_summary": "",
        "compile_json": "",
        "instance_update": {},
        "summary": "",
        "notes": [
            "This script does not recreate assets.",
            "It only re-applies the existing box brush instance and persists BP_PlowBrush_Component.",
            "BrushHeightCm remains metadata for the current 2D render-target writer.",
        ],
    }

    if blueprint is None:
        result["summary"] = f"Missing blueprint: {PLOW_BLUEPRINT_PATH}"
    elif instance is None:
        result["summary"] = f"Missing material instance: {BOX_BRUSH_INSTANCE_PATH}"
    else:
        result["instance_update"] = _apply_box_dimensions(instance)
        generated_class = _resolve_generated_class(blueprint)
        if generated_class is None:
            result["summary"] = f"Could not resolve generated class for {PLOW_BLUEPRINT_PATH}"
        else:
            default_object = unreal.get_default_object(generated_class)
            before = default_object.get_editor_property("BrushMaterial")
            result["before_brush_material"] = _object_path(before)

            default_object.set_editor_property("BrushMaterial", instance)
            after = default_object.get_editor_property("BrushMaterial")
            result["after_brush_material"] = _object_path(after)

            bridge = getattr(unreal, "BlueprintAutomationPythonBridge", None)
            if bridge is not None:
                try:
                    compile_payload = _decode_bridge_compile_result(bridge.compile_blueprint(PLOW_BLUEPRINT_PATH))
                    result["compiled"] = compile_payload["compiled"]
                    result["compile_summary"] = compile_payload["compile_summary"]
                    result["compile_json"] = compile_payload["compile_json"]
                except Exception as exc:
                    result["compile_summary"] = f"compile_blueprint raised: {exc}"
                    _warn(result["compile_summary"])
            else:
                try:
                    unreal.KismetEditorUtilities.compile_blueprint(blueprint)
                    result["compiled"] = True
                    result["compile_summary"] = "Compiled via KismetEditorUtilities.compile_blueprint"
                except Exception as exc:
                    result["compile_summary"] = f"Kismet compile failed: {exc}"
                    _warn(result["compile_summary"])

            try:
                result["saved"] = bool(EDITOR_ASSETS.save_loaded_asset(blueprint, False))
            except Exception as exc:
                result["saved"] = False
                result["save_error"] = str(exc)

            expected_object_path = _object_path(instance)
            result["success"] = (
                result["instance_update"].get("saved", False)
                and result["after_brush_material"] == expected_object_path
                and result["saved"]
            )
            result["summary"] = (
                f"BrushMaterial: {result['before_brush_material']} -> {result['after_brush_material']} "
                f"compiled={result['compiled']} bp_saved={result['saved']} "
                f"mi_saved={result['instance_update'].get('saved', False)}"
            )

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    return {"output_path": output_path, "result": result}


def print_apply_summary(output_dir: str = None):
    payload = apply_existing_box_brush(output_dir)
    _log(payload["result"]["summary"])
    _log(f"summary_path={payload['output_path']}")
    return {
        "success": payload["result"].get("success", False),
        "summary": payload["result"].get("summary", ""),
        "output_path": payload.get("output_path", ""),
    }


if __name__ == "__main__":
    print_apply_summary()
