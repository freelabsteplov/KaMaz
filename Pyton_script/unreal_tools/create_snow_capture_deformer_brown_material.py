import json
import os

import unreal


MATERIAL_PATH = "/Game/LandscapeDeformation/Materials/M_SnowCaptureDeformer_Brown"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "create_snow_capture_deformer_brown_material.json",
)


def _write(payload):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _safe_path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _connect(material, expression, property_name):
    editing = unreal.MaterialEditingLibrary
    material_property = getattr(unreal.MaterialProperty, property_name)
    editing.connect_material_property(expression, "", material_property)


def _ensure_material():
    result = {
        "material_path": MATERIAL_PATH,
        "created": False,
        "saved": False,
        "asset_class": "",
        "error": "",
    }

    try:
        asset = unreal.EditorAssetLibrary.load_asset(MATERIAL_PATH)
        if asset is None:
            package_path, asset_name = MATERIAL_PATH.rsplit("/", 1)
            asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
            factory = unreal.MaterialFactoryNew()
            asset = asset_tools.create_asset(asset_name, package_path, unreal.Material, factory)
            if asset is None:
                raise RuntimeError(f"Failed to create material: {MATERIAL_PATH}")
            result["created"] = True

        result["asset_class"] = _safe_path(asset.get_class())

        asset.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
        asset.set_editor_property("two_sided", False)
        asset.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)

        editing = unreal.MaterialEditingLibrary
        try:
            editing.delete_all_material_expressions(asset)
        except Exception:
            pass

        brown = editing.create_material_expression(asset, unreal.MaterialExpressionConstant3Vector, -400, 0)
        brown.set_editor_property("constant", unreal.LinearColor(0.24, 0.13, 0.05, 1.0))
        _connect(asset, brown, "MP_EMISSIVE_COLOR")

        opacity = editing.create_material_expression(asset, unreal.MaterialExpressionConstant, -400, 140)
        opacity.set_editor_property("r", 1.0)
        _connect(asset, opacity, "MP_OPACITY_MASK")

        editing.recompile_material(asset)
        result["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(asset, False))
    except Exception as exc:
        result["error"] = str(exc)

    _write(result)
    return result


if __name__ == "__main__":
    _ensure_material()
