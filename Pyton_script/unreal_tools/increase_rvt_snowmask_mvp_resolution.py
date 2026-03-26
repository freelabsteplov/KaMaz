import json
import os

import unreal


RVT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "increase_rvt_snowmask_mvp_resolution.json",
)


def _safe_get(obj, prop):
    try:
        return obj.get_editor_property(prop)
    except Exception:
        return None


def _safe_set(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception:
        return False


def _size_snapshot(rvt):
    get_size = getattr(rvt, "get_size", None)
    get_page_table_size = getattr(rvt, "get_page_table_size", None)
    return {
        "tile_size": _safe_get(rvt, "tile_size"),
        "tile_count": _safe_get(rvt, "tile_count"),
        "tile_border_size": _safe_get(rvt, "tile_border_size"),
        "remove_low_mips": _safe_get(rvt, "remove_low_mips"),
        "virtual_size": get_size() if callable(get_size) else None,
        "page_table_size": get_page_table_size() if callable(get_page_table_size) else None,
    }


def _try_raise(rvt, prop_name, result):
    before_value = _safe_get(rvt, prop_name)
    if before_value is None:
        return False

    target_value = int(before_value) + 1
    if not _safe_set(rvt, prop_name, target_value):
        return False

    if callable(getattr(rvt, "post_edit_change", None)):
        rvt.post_edit_change()

    after = _size_snapshot(rvt)
    result["attempts"].append(
        {
            "property": prop_name,
            "before_value": int(before_value),
            "after_value": int(after[prop_name]) if after[prop_name] is not None else None,
            "after_virtual_size": int(after["virtual_size"]) if after["virtual_size"] is not None else None,
            "after_page_table_size": int(after["page_table_size"]) if after["page_table_size"] is not None else None,
        }
    )

    before_virtual_size = int(result["before"]["virtual_size"]) if result["before"]["virtual_size"] is not None else 0
    after_virtual_size = int(after["virtual_size"]) if after["virtual_size"] is not None else 0
    if after_virtual_size > before_virtual_size:
        result["changed_property"] = prop_name
        result["after"] = after
        return True

    _safe_set(rvt, prop_name, before_value)
    if callable(getattr(rvt, "post_edit_change", None)):
        rvt.post_edit_change()
    return False


def main():
    result = {
        "asset_path": RVT_PATH,
        "before": {},
        "after": {},
        "attempts": [],
        "changed_property": "",
        "saved": False,
        "error": "",
    }

    try:
        rvt = unreal.EditorAssetLibrary.load_asset(RVT_PATH)
        if not rvt:
            raise RuntimeError(f"Missing RVT asset: {RVT_PATH}")

        result["before"] = _size_snapshot(rvt)

        changed = _try_raise(rvt, "tile_count", result)
        if not changed:
            changed = _try_raise(rvt, "tile_size", result)
        if not changed:
            raise RuntimeError("Could not increase RVT virtual size using tile_count or tile_size")

        result["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(rvt, False))
        if not result["saved"]:
            raise RuntimeError("RVT asset change was applied in memory but failed to save")
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
