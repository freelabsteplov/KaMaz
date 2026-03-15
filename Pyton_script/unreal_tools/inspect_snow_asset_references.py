import json
import os

import unreal


OUTPUT_BASENAME = "snow_asset_references"

TARGETS = [
    "/Game/CityPark/SnowSystem/RT_SnowPersistence_Global",
    "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks",
    "/Game/CityPark/SnowSystem/RVT_SnowMask",
    "/Game/CityPark/SnowSystem/MI_SnowTest_Landscape",
    "/Game/CityPark/SnowSystem/M_SnowTest_Landscape",
    "/Game/CityPark/SnowSystem/M_SnowTestMVP_Landscape1",
    "/Game/CityPark/SnowSystem/BP_PlowBrush_Component",
    "/Game/CityPark/SnowSystem/BP_WheelSnowTrace_Component",
]


def _log(message: str) -> None:
    unreal.log(f"[inspect_snow_asset_references] {message}")


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


def inspect_target(asset_path: str) -> dict:
    asset = _load_asset(asset_path)
    result = {
        "asset_path": asset_path,
        "exists": asset is not None,
        "object_path": asset.get_path_name() if asset else "",
        "class_name": asset.get_class().get_name() if asset else "",
        "referencers": [],
        "dependencies": [],
    }

    if asset is None:
        return result

    try:
        referencers = unreal.EditorAssetLibrary.find_package_referencers_for_asset(asset_path, False)
    except Exception:
        referencers = []

    try:
        dependencies = unreal.EditorAssetLibrary.find_package_references_for_asset(asset_path, False)
    except Exception:
        dependencies = []

    result["referencers"] = sorted(str(item) for item in referencers)
    result["dependencies"] = sorted(str(item) for item in dependencies)
    return result


def run_inspection(output_dir: str = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    result = {
        "project_saved_dir": unreal.Paths.project_saved_dir(),
        "targets": [inspect_target(asset_path) for asset_path in TARGETS],
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    return {"output_path": output_path, "result": result}


def print_inspection_summary(output_dir: str = None):
    payload = run_inspection(output_dir)
    for target in payload["result"]["targets"]:
        _log(
            f"{target['asset_path']}: exists={target['exists']} "
            f"class={target['class_name']} referencers={len(target['referencers'])} "
            f"dependencies={len(target['dependencies'])}"
        )
    _log(f"summary_path={payload['output_path']}")
    return payload


if __name__ == "__main__":
    print_inspection_summary()
