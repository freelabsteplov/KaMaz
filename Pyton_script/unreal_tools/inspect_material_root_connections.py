import json
import os

import unreal


ASSET_PATH = os.environ.get("KAMAZ_MATERIAL_PATH", "")
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "inspect_material_root_connections.json",
)


def expression_summary(input_struct):
    expression = None
    output_name = ""
    mask = {}

    if input_struct:
        try:
            expression = input_struct.expression
        except Exception:
            expression = None
        try:
            output_name = str(input_struct.output_name)
        except Exception:
            output_name = ""
        for field in ["mask", "mask_r", "mask_g", "mask_b", "mask_a"]:
            try:
                mask[field] = bool(getattr(input_struct, field))
            except Exception:
                pass

    return {
        "expression_name": expression.get_name() if expression else None,
        "expression_class": expression.get_class().get_name() if expression else None,
        "output_name": output_name,
        "mask": mask,
    }


def main():
    result = {
        "asset": ASSET_PATH,
        "connections": {},
        "blend_mode": "",
        "opacity_mask_clip_value": None,
        "error": "",
    }

    try:
        if not ASSET_PATH:
            raise RuntimeError("KAMAZ_MATERIAL_PATH is empty")

        material = unreal.EditorAssetLibrary.load_asset(ASSET_PATH)
        if not material:
            raise RuntimeError(f"Failed to load material: {ASSET_PATH}")

        try:
            result["blend_mode"] = str(material.get_editor_property("blend_mode"))
        except Exception:
            result["blend_mode"] = ""
        try:
            result["opacity_mask_clip_value"] = float(material.get_editor_property("opacity_mask_clip_value"))
        except Exception:
            result["opacity_mask_clip_value"] = None

        property_map = {
            "base_color": unreal.MaterialProperty.MP_BASE_COLOR,
            "roughness": unreal.MaterialProperty.MP_ROUGHNESS,
            "normal": unreal.MaterialProperty.MP_NORMAL,
            "world_position_offset": unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET,
            "emissive_color": unreal.MaterialProperty.MP_EMISSIVE_COLOR,
            "opacity_mask": unreal.MaterialProperty.MP_OPACITY_MASK,
        }

        for label, material_property in property_map.items():
            expression = unreal.MaterialEditingLibrary.get_material_property_input_node(material, material_property)
            output_name = unreal.MaterialEditingLibrary.get_material_property_input_node_output_name(material, material_property)
            result["connections"][label] = {
                "expression_name": expression.get_name() if expression else None,
                "expression_class": expression.get_class().get_name() if expression else None,
                "output_name": output_name,
            }
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as output_file:
        json.dump(result, output_file, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
