import json
import os

import unreal


OUTPUT_BASENAME = "snow_config_alignment"
PLOW_BLUEPRINT_PATH = "/Game/CityPark/SnowSystem/BP_PlowBrush_Component"
ACTIVE_RENDER_TARGET_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"


def _log(message: str) -> None:
    unreal.log(f"[snow_config_tools] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[snow_config_tools] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


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


def _object_path(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


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


def align_plow_render_target(output_dir: str = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    blueprint = unreal.EditorAssetLibrary.load_asset(PLOW_BLUEPRINT_PATH)
    target_rt = unreal.EditorAssetLibrary.load_asset(ACTIVE_RENDER_TARGET_PATH)

    result = {
        "blueprint_path": PLOW_BLUEPRINT_PATH,
        "target_render_target_path": ACTIVE_RENDER_TARGET_PATH,
        "success": False,
        "saved": False,
        "compiled": False,
        "before": "",
        "after": "",
        "summary": "",
    }

    if blueprint is None:
        result["summary"] = f"Missing blueprint: {PLOW_BLUEPRINT_PATH}"
    elif target_rt is None:
        result["summary"] = f"Missing render target: {ACTIVE_RENDER_TARGET_PATH}"
    else:
        target_rt_object_path = _object_path(target_rt)
        result["target_render_target_object_path"] = target_rt_object_path
        generated_class = _resolve_generated_class(blueprint)
        if generated_class is None:
            result["summary"] = f"Could not resolve generated class for {PLOW_BLUEPRINT_PATH}"
        else:
            default_object = unreal.get_default_object(generated_class)
            before = default_object.get_editor_property("RenderTargetGlobal")
            result["before"] = _object_path(before)

            default_object.set_editor_property("RenderTargetGlobal", target_rt)
            after = default_object.get_editor_property("RenderTargetGlobal")
            result["after"] = _object_path(after)

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
                result["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False))
            except Exception as exc:
                result["saved"] = False
                result["save_error"] = str(exc)

            result["success"] = result["after"] == target_rt_object_path and result["saved"]
            result["summary"] = (
                f"RenderTargetGlobal: {result['before']} -> {result['after']} "
                f"compiled={result['compiled']} saved={result['saved']}"
            )

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    return {"output_path": output_path, "result": result}


def print_alignment_summary(output_dir: str = None):
    payload = align_plow_render_target(output_dir)
    _log(payload["result"]["summary"])
    _log(f"summary_path={payload['output_path']}")
    return payload


if __name__ == "__main__":
    print_alignment_summary()
