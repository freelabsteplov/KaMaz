import json
import os

import unreal


PLOW_BLUEPRINT_PATH = "/Game/CityPark/SnowSystem/BP_PlowBrush_Component"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "set_plow_rt_none_direct.json",
)


def _path(obj):
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _resolve_generated_class(asset):
    candidate = getattr(asset, "generated_class", None)
    if callable(candidate):
        try:
            candidate = candidate()
        except Exception:
            candidate = None
    if candidate is None:
        try:
            candidate = asset.get_editor_property("generated_class")
        except Exception:
            candidate = None
    return candidate


def main():
    result = {
        "asset_path": PLOW_BLUEPRINT_PATH,
        "success": False,
        "before": "",
        "after": "",
        "save_asset": False,
        "save_loaded_asset": False,
        "error": "",
    }
    try:
        asset = unreal.EditorAssetLibrary.load_asset(PLOW_BLUEPRINT_PATH)
        if asset is None:
            raise RuntimeError("Missing plow blueprint")
        generated_class = _resolve_generated_class(asset)
        if generated_class is None:
            raise RuntimeError("Missing generated class")

        cdo = unreal.get_default_object(generated_class)
        result["before"] = _path(cdo.get_editor_property("RenderTargetGlobal"))
        cdo.set_editor_property("RenderTargetGlobal", None)
        result["after"] = _path(cdo.get_editor_property("RenderTargetGlobal"))
        try:
            asset.mark_package_dirty()
        except Exception:
            pass

        result["save_asset"] = bool(unreal.EditorAssetLibrary.save_asset(PLOW_BLUEPRINT_PATH, False))
        result["save_loaded_asset"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(asset, False))
        result["success"] = result["after"] == "" and (result["save_asset"] or result["save_loaded_asset"])
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
