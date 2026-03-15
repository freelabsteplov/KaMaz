import json
import os

import unreal


ASSET_PATH = "/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush"
OUTPUT_BASENAME = "material_parameters_M_Snow_PlowBrush"


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    unreal.log(f"[inspect_material_parameters] Wrote file: {path}")
    return path


def _safe_call(callable_obj, *args):
    try:
        return callable_obj(*args), ""
    except Exception as exc:
        return None, str(exc)


def _serialize_items(items):
    if items is None:
        return None
    result = []
    for item in items:
        try:
            result.append(str(item))
        except Exception:
            result.append("<unserializable>")
    return result


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    material = unreal.EditorAssetLibrary.load_asset(ASSET_PATH)
    if material is None:
        raise RuntimeError(f"Could not load material: {ASSET_PATH}")

    mel = unreal.MaterialEditingLibrary
    payload = {
        "asset_path": ASSET_PATH,
        "asset_class": str(material.get_class().get_path_name()),
    }

    for label, func_name in (
        ("scalar_parameter_names", "get_scalar_parameter_names"),
        ("vector_parameter_names", "get_vector_parameter_names"),
        ("texture_parameter_names", "get_texture_parameter_names"),
        ("static_switch_parameter_names", "get_static_switch_parameter_names"),
    ):
        func = getattr(mel, func_name, None)
        if not callable(func):
            payload[label] = {"error": f"{func_name} is not available"}
            continue
        value, error = _safe_call(func, material)
        payload[label] = {"value": _serialize_items(value), "error": error}

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, payload)
    payload["output_path"] = output_path
    return payload


if __name__ == "__main__":
    print(run())
