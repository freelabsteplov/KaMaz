import json
import os

import unreal


ASSET_PATH = os.environ.get("KAMAZ_MATERIAL_PATH", "")
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_material_python_api.json",
)


def serialize_object_properties(obj):
    names = []
    try:
        names = list(obj.get_editor_property_names())
    except Exception:
        names = []
    return sorted(str(name) for name in names)


def main():
    result = {
        "asset": ASSET_PATH,
        "material_properties": [],
        "editor_only_data_properties": [],
        "error": "",
    }

    try:
        material = unreal.EditorAssetLibrary.load_asset(ASSET_PATH)
        if not material:
            raise RuntimeError(f"Failed to load material: {ASSET_PATH}")

        result["material_properties"] = serialize_object_properties(material)

        try:
            editor_only_data = material.get_editor_property("editor_only_data")
            if editor_only_data:
                result["editor_only_data_properties"] = serialize_object_properties(editor_only_data)
        except Exception as exc:
            result["editor_only_data_error"] = str(exc)
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as output_file:
        json.dump(result, output_file, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
