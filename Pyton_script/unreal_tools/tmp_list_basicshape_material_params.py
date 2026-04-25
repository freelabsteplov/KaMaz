import json
import os

import unreal


OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "tmp_list_basicshape_material_params.json",
)

TARGETS = [
    "/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial",
]


def _path(obj):
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _write(payload):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _list_vector_params(asset):
    names = []
    for fn_name in (
        "get_all_vector_parameter_info",
        "get_vector_parameter_names",
    ):
        fn = getattr(asset, fn_name, None)
        if not callable(fn):
            continue
        try:
            raw = fn()
            if isinstance(raw, tuple):
                raw = raw[0]
            for item in list(raw or []):
                if hasattr(item, "name"):
                    names.append(str(item.name))
                else:
                    names.append(str(item))
            if names:
                break
        except Exception:
            continue
    return names


def main():
    payload = {"targets": []}
    for path in TARGETS:
        asset = unreal.EditorAssetLibrary.load_asset(path)
        payload["targets"].append(
            {
                "path": path,
                "loaded": bool(asset),
                "asset_class": _path(asset.get_class()) if asset else "",
                "vector_parameters": _list_vector_params(asset) if asset else [],
            }
        )
    _write(payload)


if __name__ == "__main__":
    main()
