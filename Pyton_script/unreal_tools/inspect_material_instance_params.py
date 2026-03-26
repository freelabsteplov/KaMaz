import json
import os

import unreal


ASSET_PATH = os.environ.get("KAMAZ_MATERIAL_INSTANCE_PATH", "")
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_material_instance_params.json",
)


def main():
    result = {
        "asset": ASSET_PATH,
        "scalar_values": {},
        "vector_values": {},
        "texture_values": {},
        "error": "",
    }

    try:
        if not ASSET_PATH:
            raise RuntimeError("KAMAZ_MATERIAL_INSTANCE_PATH is empty")

        mi = unreal.EditorAssetLibrary.load_asset(ASSET_PATH)
        if not mi:
            raise RuntimeError(f"Failed to load asset: {ASSET_PATH}")

        for name in unreal.MaterialEditingLibrary.get_scalar_parameter_names(mi):
            result["scalar_values"][str(name)] = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(
                mi, name
            )

        for name in unreal.MaterialEditingLibrary.get_vector_parameter_names(mi):
            result["vector_values"][str(name)] = str(
                unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mi, name)
            )

        for name in unreal.MaterialEditingLibrary.get_texture_parameter_names(mi):
            texture = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mi, name)
            result["texture_values"][str(name)] = texture.get_path_name() if texture else None
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as output_file:
        json.dump(result, output_file, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
