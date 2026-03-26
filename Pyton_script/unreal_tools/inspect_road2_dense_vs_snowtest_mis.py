import json
import os

import unreal


OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_road2_dense_vs_snowtest_mis.json",
)

ASSET_PATHS = [
    "/Game/CityPark/SnowSystem/Receivers/MI_SnowRoadCarrier_Road2_Dense",
    "/Game/CityPark/SnowSystem/Receivers/MI_SnowRoadCarrier_Road2",
    "/Game/CityPark/SnowSystem/Receivers/MI_SnowRoadCarrier_Road2_LocalHeight",
    "/Game/CityPark/SnowSystem/Receivers/M_SnowRoadCarrier_HeightRoadBase",
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP",
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_Tile8",
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K",
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_V3_Narrow_Tile4",
]


def object_path(value):
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def get_parent_chain(material_interface):
    chain = []
    current = material_interface
    while current is not None:
        chain.append(
            {
                "name": current.get_name(),
                "path": current.get_path_name(),
                "class": current.get_class().get_path_name(),
            }
        )
        if isinstance(current, unreal.MaterialInstance):
            current = current.parent
        else:
            break
    return chain


def inspect_material_instance(asset_path):
    result = {
        "asset_path": asset_path,
        "exists": False,
        "class": "",
        "parent_chain": [],
        "scalar_values": {},
        "vector_values": {},
        "texture_values": {},
        "rvt_values": {},
        "error": "",
    }

    try:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if asset is None:
            raise RuntimeError(f"Failed to load asset: {asset_path}")

        result["exists"] = True
        result["class"] = asset.get_class().get_path_name()
        result["parent_chain"] = get_parent_chain(asset)

        for name in unreal.MaterialEditingLibrary.get_scalar_parameter_names(asset):
            key = str(name)
            result["scalar_values"][key] = float(
                unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(asset, name)
            )

        for name in unreal.MaterialEditingLibrary.get_vector_parameter_names(asset):
            key = str(name)
            value = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(asset, name)
            result["vector_values"][key] = [float(value.r), float(value.g), float(value.b), float(value.a)]

        for name in unreal.MaterialEditingLibrary.get_texture_parameter_names(asset):
            key = str(name)
            texture = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(asset, name)
            result["texture_values"][key] = object_path(texture)

        getter = getattr(
            unreal.MaterialEditingLibrary,
            "get_material_instance_runtime_virtual_texture_parameter_value",
            None,
        )
        if callable(getter):
            for key in ("SnowRVT",):
                try:
                    result["rvt_values"][key] = object_path(getter(asset, key))
                except Exception:
                    result["rvt_values"][key] = ""
    except Exception as exc:
        result["error"] = str(exc)

    return result


def main():
    payload = {
        "materials": [inspect_material_instance(asset_path) for asset_path in ASSET_PATHS],
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, ensure_ascii=False)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
