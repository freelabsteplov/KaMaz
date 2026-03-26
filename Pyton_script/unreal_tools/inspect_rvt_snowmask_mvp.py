import json
import os

import unreal


RVT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_rvt_snowmask_mvp.json",
)


def _safe_get(obj, prop):
    try:
        return obj.get_editor_property(prop)
    except Exception:
        return None


def _jsonable(value):
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "name"):
        return str(value.name)
    return str(value)


def main():
    result = {
        "asset_path": RVT_PATH,
        "class_name": "",
        "properties": {},
        "property_types": {},
        "methods": {},
        "candidate_names": [],
        "error": "",
    }

    try:
        rvt = unreal.EditorAssetLibrary.load_asset(RVT_PATH)
        if not rvt:
            raise RuntimeError(f"Missing RVT asset: {RVT_PATH}")

        result["class_name"] = rvt.get_class().get_name()

        interesting_props = [
            "tile_size",
            "tile_count",
            "tile_border_size",
            "remove_low_mips",
            "single_physical_space",
            "private_space",
            "adaptive",
            "enable_private_space",
            "enable_compress_crunch",
            "compress_textures",
            "material_type",
            "enable_clear_before_render",
            "size",
            "size_x",
            "size_y",
        ]
        for prop in interesting_props:
            value = _safe_get(rvt, prop)
            result["properties"][prop] = _jsonable(value)
            result["property_types"][prop] = type(value).__name__ if value is not None else "NoneType"

        for method_name in ("get_size", "get_page_table_size"):
            method = getattr(rvt, method_name, None)
            if callable(method):
                try:
                    value = method()
                    result["methods"][method_name] = {
                        "value": _jsonable(value),
                        "type": type(value).__name__,
                        "repr": repr(value),
                    }
                except Exception as exc:
                    result["methods"][method_name] = {
                        "error": str(exc),
                    }

        dir_names = []
        for name in dir(rvt):
            lowered = name.lower()
            if any(token in lowered for token in ("tile", "size", "mip", "virtual", "texture", "adaptive", "space")):
                dir_names.append(name)
        result["candidate_names"] = sorted(dir_names)
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
