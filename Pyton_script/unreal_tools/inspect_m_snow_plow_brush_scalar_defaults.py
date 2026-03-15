import json
import os

import unreal


ASSET_PATH = "/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush"
PARAMETER_NAMES = ("Param", "Param_1", "Param_2")
OUTPUT_BASENAME = "m_snow_plow_brush_scalar_defaults"


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    unreal.log(f"[inspect_m_snow_plow_brush_scalar_defaults] Wrote file: {path}")
    return path


def _safe_call(callable_obj, *args):
    try:
        return callable_obj(*args), ""
    except Exception as exc:
        return None, str(exc)


def _serialize_source(value):
    if value is None:
        return None
    if isinstance(value, tuple):
        return [str(item) for item in value]
    try:
        return str(value)
    except Exception:
        return "<unserializable>"


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    material = unreal.EditorAssetLibrary.load_asset(ASSET_PATH)
    if material is None:
        raise RuntimeError(f"Could not load material: {ASSET_PATH}")

    mel = unreal.MaterialEditingLibrary
    payload = {
        "asset_path": ASSET_PATH,
        "parameters": {},
    }

    for name in PARAMETER_NAMES:
        default_value, default_error = _safe_call(mel.get_material_default_scalar_parameter_value, material, name)
        source_value, source_error = _safe_call(mel.get_scalar_parameter_source, material, name)
        payload["parameters"][name] = {
            "default_value": default_value,
            "default_error": default_error,
            "source": _serialize_source(source_value),
            "source_error": source_error,
        }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, payload)
    payload["output_path"] = output_path
    return payload


if __name__ == "__main__":
    print(run())
