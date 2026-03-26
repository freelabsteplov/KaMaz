import json
import os

import unreal


MPC_PATH = "/Game/CityPark/SnowSystem/MPC_SnowSystem"
RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_mpc_snow_bounds_asset.json",
)


def _load_asset(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Could not load asset: {asset_path}")
    return asset


def _find_vector_param(collection, parameter_name: str):
    for entry in list(collection.get_editor_property("vector_parameters") or []):
        if str(entry.get_editor_property("parameter_name")) != parameter_name:
            continue
        return entry.get_editor_property("default_value")
    return None


def _vec4_to_dict(value):
    if value is None:
        return None
    return {
        "x": float(value.r),
        "y": float(value.g),
        "z": float(value.b),
        "w": float(value.a),
    }


def main():
    payload = {
        "mpc_path": MPC_PATH,
        "rt_path": RT_PATH,
        "world_bounds_min": None,
        "world_bounds_max": None,
        "rt_size": None,
        "world_span_cm": None,
        "cm_per_texel": None,
        "error": "",
    }

    try:
        mpc = _load_asset(MPC_PATH)
        rt = _load_asset(RT_PATH)

        bounds_min = _find_vector_param(mpc, "WorldBoundsMin")
        bounds_max = _find_vector_param(mpc, "WorldBoundsMax")
        size_x = int(rt.get_editor_property("size_x"))
        size_y = int(rt.get_editor_property("size_y"))

        payload["world_bounds_min"] = _vec4_to_dict(bounds_min)
        payload["world_bounds_max"] = _vec4_to_dict(bounds_max)
        payload["rt_size"] = {
            "x": size_x,
            "y": size_y,
        }

        if bounds_min and bounds_max:
            span_x = float(bounds_max.r) - float(bounds_min.r)
            span_y = float(bounds_max.g) - float(bounds_min.g)
            payload["world_span_cm"] = {
                "x": span_x,
                "y": span_y,
            }
            payload["cm_per_texel"] = {
                "x": span_x / max(1.0, float(size_x)),
                "y": span_y / max(1.0, float(size_y)),
            }
    except Exception as exc:
        payload["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
