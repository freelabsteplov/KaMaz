import json
import os

import unreal


RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
OUTPUT_BASENAME = "inspect_rt_size"


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    unreal.log(f"[inspect_rt_size] Wrote file: {path}")
    return path


def _load_asset(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Could not load asset: {asset_path}")
    return asset


def _safe_get(obj, property_name: str):
    try:
        return obj.get_editor_property(property_name)
    except Exception:
        return None


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    rt = _load_asset(RT_PATH)

    size_x = _safe_get(rt, "size_x")
    size_y = _safe_get(rt, "size_y")
    clear_color = _safe_get(rt, "clear_color")
    render_target_format = _safe_get(rt, "render_target_format")

    payload = {
        "success": True,
        "rt_path": rt.get_path_name(),
        "class_name": rt.get_class().get_name(),
        "size_x": int(size_x) if size_x is not None else None,
        "size_y": int(size_y) if size_y is not None else None,
        "render_target_format": str(render_target_format) if render_target_format is not None else None,
        "clear_color": {
            "r": float(clear_color.r),
            "g": float(clear_color.g),
            "b": float(clear_color.b),
            "a": float(clear_color.a),
        }
        if clear_color is not None
        else None,
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, payload)
    payload["output_path"] = output_path
    return payload


def print_summary():
    payload = run()
    summary = f"RT size {payload.get('size_x')}x{payload.get('size_y')}"
    unreal.log(f"[inspect_rt_size] {summary}")
    unreal.log(f"[inspect_rt_size] summary_path={payload['output_path']}")
    return {
        "success": payload.get("success", False),
        "summary": summary,
        "output_path": payload.get("output_path", ""),
    }


if __name__ == "__main__":
    print_summary()
