import unreal
import json
import os

ASSET_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_Landscape_SoftSeam"
OUTPUT = os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation", "inspect_landscape_soft_seam_mi_params.json")

result = {
    "asset": ASSET_PATH,
    "scalar_values": {},
    "vector_values": {},
    "texture_values": {},
    "error": ""
}

try:
    mi = unreal.EditorAssetLibrary.load_asset(ASSET_PATH)
    if not mi:
        raise RuntimeError("Failed to load asset")

    scalar_names = [str(n) for n in unreal.MaterialEditingLibrary.get_scalar_parameter_names(mi)]
    vector_names = [str(n) for n in unreal.MaterialEditingLibrary.get_vector_parameter_names(mi)]
    texture_names = [str(n) for n in unreal.MaterialEditingLibrary.get_texture_parameter_names(mi)]

    for name in scalar_names:
        value = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, name)
        result["scalar_values"][name] = value

    for name in vector_names:
        value = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mi, name)
        result["vector_values"][name] = str(value)

    for name in texture_names:
        value = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mi, name)
        result["texture_values"][name] = value.get_path_name() if value else None
except Exception as exc:
    result["error"] = str(exc)

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as fh:
    json.dump(result, fh, indent=2, ensure_ascii=False)
print(json.dumps(result, indent=2, ensure_ascii=False))
