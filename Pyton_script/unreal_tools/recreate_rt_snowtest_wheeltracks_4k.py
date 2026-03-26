import json
import os

import unreal


RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
BACKUP_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks_Backup_2048"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "recreate_rt_snowtest_wheeltracks_4k.json",
)

ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def _safe_get(obj, prop, default=None):
    try:
        return obj.get_editor_property(prop)
    except Exception:
        return default


def _load(asset_path: str):
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Missing asset: {asset_path}")
    return asset


def _asset_exists(asset_path: str) -> bool:
    return bool(unreal.EditorAssetLibrary.does_asset_exist(asset_path))


def _delete_asset(asset_path: str) -> bool:
    return bool(unreal.EditorAssetLibrary.delete_asset(asset_path))


def _save_output(payload):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def main():
    payload = {
        "rt_path": RT_PATH,
        "backup_path": BACKUP_PATH,
        "before": {},
        "after": {},
        "backup_created": False,
        "recreated": False,
        "saved": False,
        "error": "",
    }

    try:
        old_rt = _load(RT_PATH)
        package_path, asset_name = RT_PATH.rsplit("/", 1)

        payload["before"] = {
            "size_x": int(_safe_get(old_rt, "size_x", 0) or 0),
            "size_y": int(_safe_get(old_rt, "size_y", 0) or 0),
            "render_target_format": str(_safe_get(old_rt, "render_target_format")),
            "clear_color": str(_safe_get(old_rt, "clear_color")),
            "target_gamma": _safe_get(old_rt, "target_gamma"),
        }

        if not _asset_exists(BACKUP_PATH):
            payload["backup_created"] = bool(unreal.EditorAssetLibrary.duplicate_asset(RT_PATH, BACKUP_PATH))
            if not payload["backup_created"]:
                raise RuntimeError(f"Failed to create backup asset: {BACKUP_PATH}")

        if not _delete_asset(RT_PATH):
            raise RuntimeError(f"Failed to delete original RT before recreation: {RT_PATH}")

        factory = unreal.TextureRenderTargetFactoryNew()
        try:
            factory.set_editor_property("width", 4096)
            factory.set_editor_property("height", 4096)
        except Exception:
            pass
        try:
            factory.set_editor_property("format", unreal.TextureRenderTargetFormat.RTF_RGBA16F)
        except Exception:
            pass
        new_rt = ASSET_TOOLS.create_asset(asset_name, package_path, unreal.TextureRenderTarget2D, factory)
        if new_rt is None:
            raise RuntimeError(f"Failed to recreate render target at: {RT_PATH}")

        new_rt.set_editor_property("size_x", 4096)
        new_rt.set_editor_property("size_y", 4096)

        clear_color = _safe_get(old_rt, "clear_color")
        if clear_color is not None:
            new_rt.set_editor_property("clear_color", clear_color)

        render_target_format = _safe_get(old_rt, "render_target_format")
        if render_target_format is not None:
            try:
                new_rt.set_editor_property("render_target_format", render_target_format)
            except Exception:
                pass

        target_gamma = _safe_get(old_rt, "target_gamma")
        if target_gamma is not None:
            try:
                new_rt.set_editor_property("target_gamma", float(target_gamma))
            except Exception:
                pass

        post_edit_change = getattr(new_rt, "post_edit_change", None)
        if callable(post_edit_change):
            post_edit_change()

        payload["recreated"] = True
        payload["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(new_rt, False))
        payload["after"] = {
            "size_x": int(_safe_get(new_rt, "size_x", 0) or 0),
            "size_y": int(_safe_get(new_rt, "size_y", 0) or 0),
            "render_target_format": str(_safe_get(new_rt, "render_target_format")),
            "clear_color": str(_safe_get(new_rt, "clear_color")),
            "target_gamma": _safe_get(new_rt, "target_gamma"),
        }

        if payload["after"]["size_x"] != 4096 or payload["after"]["size_y"] != 4096:
            raise RuntimeError("Recreated RT did not persist the expected 4096 size.")
    except Exception as exc:
        payload["error"] = str(exc)

    _save_output(payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
