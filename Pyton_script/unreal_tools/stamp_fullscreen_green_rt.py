import json
import os

import unreal


MAP_PATH = "/Game/Maps/MoscowEA5"
RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
MATERIAL_PATH = "/Game/CityPark/SnowSystem/BrushMaterials/M_RT_FullscreenGreen_Test"
OUTPUT_BASENAME = "stamp_fullscreen_green_rt"

ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
ASSET_LIB = unreal.EditorAssetLibrary
MAT_LIB = unreal.MaterialEditingLibrary
RENDER_LIB = unreal.RenderingLibrary


def _log(message: str) -> None:
    unreal.log(f"[stamp_fullscreen_green_rt] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _load_asset(asset_path: str):
    asset = ASSET_LIB.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Could not load asset: {asset_path}")
    return asset


def _object_path(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _create_or_rebuild_material():
    package_path, asset_name = MATERIAL_PATH.rsplit("/", 1)
    material = ASSET_LIB.load_asset(MATERIAL_PATH)
    if material is None:
        material = ASSET_TOOLS.create_asset(
            asset_name,
            package_path,
            unreal.Material,
            unreal.MaterialFactoryNew(),
        )
        if material is None:
            raise RuntimeError(f"Failed to create material: {MATERIAL_PATH}")

    MAT_LIB.delete_all_material_expressions(material)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property("material_domain", unreal.MaterialDomain.MD_SURFACE)

    green = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, -400, 0)
    green.set_editor_property("constant", unreal.LinearColor(0.0, 1.0, 0.0, 1.0))

    MAT_LIB.connect_material_property(green, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MAT_LIB.recompile_material(material)
    MAT_LIB.layout_material_expressions(material)
    ASSET_LIB.save_loaded_asset(material, False)
    return material


def _get_editor_world():
    try:
        return unreal.EditorLevelLibrary.get_editor_world()
    except Exception:
        subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        return subsystem.get_editor_world()


def _export_rt(world, render_target, export_dir: str, base_filename: str) -> str:
    os.makedirs(export_dir, exist_ok=True)
    RENDER_LIB.export_render_target(world, render_target, export_dir, base_filename)
    png_path = os.path.join(export_dir, f"{base_filename}.png")
    hdr_path = os.path.join(export_dir, f"{base_filename}.hdr")
    if os.path.exists(png_path):
        return png_path
    if os.path.exists(hdr_path):
        return hdr_path
    return ""


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    world = _get_editor_world()
    render_target = _load_asset(RT_PATH)
    material = _create_or_rebuild_material()

    RENDER_LIB.clear_render_target2d(world, render_target, unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
    RENDER_LIB.draw_material_to_render_target(world, render_target, material)
    sampled_center = RENDER_LIB.read_render_target_raw_uv(world, render_target, 0.5, 0.5)
    exported_image_path = _export_rt(world, render_target, output_dir, OUTPUT_BASENAME)

    result = {
        "success": True,
        "map_path": MAP_PATH,
        "render_target_path": _object_path(render_target),
        "material_path": _object_path(material),
        "sampled_center": {
            "r": float(getattr(sampled_center, "r", 0.0)),
            "g": float(getattr(sampled_center, "g", 0.0)),
            "b": float(getattr(sampled_center, "b", 0.0)),
            "a": float(getattr(sampled_center, "a", 0.0)),
        },
        "exported_image_path": exported_image_path,
    }
    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, result)
    result["output_path"] = output_path
    return result


def print_summary() -> str:
    result = run()
    summary = f"fullscreen_green center={result['sampled_center']} export={result['exported_image_path']}"
    _log(summary)
    return summary


if __name__ == "__main__":
    print(run())
