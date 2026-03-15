import json
import os

import unreal


OUTPUT_BASENAME = "snow_component_defaults"

TARGETS = [
    {
        "asset_path": "/Game/CityPark/SnowSystem/BP_PlowBrush_Component",
        "properties": [
            "RenderTargetGlobal",
            "BrushMaterial",
            "BrushDMI",
            "MPCSnowSystem",
            "OwnerVehicle",
            "PlowLiftHeight",
            "bEnablePlowClearing",
        ],
    },
    {
        "asset_path": "/Game/CityPark/SnowSystem/BP_WheelSnowTrace_Component",
        "properties": [
            "RenderTargetGlobal",
            "BrushMaterial",
            "BrushDMI",
            "OwnerVehicle",
            "WheelBoneNames",
            "bEnableSnowTraces",
        ],
    },
]


def _log(message: str) -> None:
    unreal.log(f"[inspect_snow_component_defaults] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[inspect_snow_component_defaults] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _load_asset(asset_path: str):
    try:
        return unreal.EditorAssetLibrary.load_asset(asset_path)
    except Exception:
        return None


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


def _safe_property(obj, property_name: str):
    try:
        return obj.get_editor_property(property_name)
    except Exception:
        return None


def _serialize_value(value):
    if value is None:
        return None

    if isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, unreal.Name):
        return str(value)

    if isinstance(value, unreal.Array):
        return [_serialize_value(item) for item in value]

    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]

    if hasattr(value, "get_path_name"):
        try:
            return value.get_path_name()
        except Exception:
            pass

    try:
        return str(value)
    except Exception:
        return "<unserializable>"


def inspect_target(target: dict) -> dict:
    asset_path = target["asset_path"]
    asset = _load_asset(asset_path)
    result = {
        "asset_path": asset_path,
        "exists": asset is not None,
        "blueprint_path": asset.get_path_name() if asset else "",
        "generated_class_path": "",
        "default_object_path": "",
        "properties": {},
    }

    if asset is None:
        return result

    generated_class = _resolve_generated_class(asset)
    if generated_class is None:
        _warn(f"No generated class for {asset_path}")
        return result

    result["generated_class_path"] = generated_class.get_path_name()

    try:
        default_object = unreal.get_default_object(generated_class)
    except Exception:
        default_object = None

    if default_object is None:
        _warn(f"No default object for {asset_path}")
        return result

    result["default_object_path"] = default_object.get_path_name()

    for property_name in target["properties"]:
        value = _safe_property(default_object, property_name)
        result["properties"][property_name] = _serialize_value(value)

    return result


def run_inspection(output_dir: str = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    result = {
        "project_saved_dir": unreal.Paths.project_saved_dir(),
        "targets": [inspect_target(target) for target in TARGETS],
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    return {
        "output_path": output_path,
        "result": result,
    }


def print_inspection_summary(output_dir: str = None):
    payload = run_inspection(output_dir)
    for target in payload["result"]["targets"]:
        if not target["exists"]:
            _warn(f"{target['asset_path']}: missing")
            continue

        _log(
            f"{target['asset_path']}: generated_class={target['generated_class_path']} "
            f"default_object={target['default_object_path']}"
        )
        for key, value in target["properties"].items():
            _log(f"  {key}={value}")

    _log(f"summary_path={payload['output_path']}")
    return payload


if __name__ == "__main__":
    print_inspection_summary()
