import json
import os

import unreal


MASTER_MATERIAL_PATH = "/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush_BoxSafe"
OUTPUT_BASENAME = "apply_plow_master_test_defaults"
TARGET_SCALARS = {
    "BrushLengthCm": 6000.0,
    "BrushWidthCm": 18000.0,
    "BrushHeightCm": 3000.0,
    "BrushStrength": 64.0,
}


def _log(message: str) -> None:
    unreal.log(f"[apply_plow_master_test_defaults] {message}")


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


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    material = unreal.EditorAssetLibrary.load_asset(MASTER_MATERIAL_PATH)
    if material is None:
        raise RuntimeError(f"Could not load master material: {MASTER_MATERIAL_PATH}")

    result = {
        "success": True,
        "master_material_path": _object_path(material),
        "target_scalars": TARGET_SCALARS,
        "updated": [],
        "missing": [],
    }

    expressions = list(material.get_editor_property("expressions") or [])
    material.modify(True)
    for expression in expressions:
        if not isinstance(expression, unreal.MaterialExpressionScalarParameter):
            continue
        parameter_name = str(expression.get_editor_property("parameter_name"))
        if parameter_name not in TARGET_SCALARS:
            continue
        before_value = float(expression.get_editor_property("default_value"))
        after_value = float(TARGET_SCALARS[parameter_name])
        expression.set_editor_property("default_value", after_value)
        result["updated"].append(
            {
                "parameter_name": parameter_name,
                "before": before_value,
                "after": after_value,
            }
        )

    updated_names = {entry["parameter_name"] for entry in result["updated"]}
    for parameter_name in TARGET_SCALARS:
        if parameter_name not in updated_names:
            result["missing"].append(parameter_name)

    unreal.MaterialEditingLibrary.recompile_material(material)
    saved = bool(unreal.EditorAssetLibrary.save_loaded_asset(material, False))
    result["saved"] = saved
    result["success"] = saved and not result["missing"]

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary() -> str:
    result = run()
    summary = (
        f"Updated plow master defaults on {MASTER_MATERIAL_PATH} "
        f"updated={len(result.get('updated', []))}/{len(TARGET_SCALARS)} saved={result.get('saved')}"
    )
    _log(summary)
    return summary


if __name__ == "__main__":
    print(run())
