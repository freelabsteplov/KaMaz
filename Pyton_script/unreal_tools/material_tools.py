import unreal

"""Utilities for creating simple Unreal materials from the editor Python console.

Usage from Unreal Output Log -> Python:

    exec(open(r"C:\\Users\\post\\Documents\\Unreal Projects\\Kamaz_Cleaner\\Pyton_script\\unreal_tools\\material_tools.py", encoding="utf-8").read())
    create_rvt_snow_writer_test()

Optional custom destination/name:

    create_rvt_snow_writer_test(
        package_path="/Game/CityPark/SnowSystem/BrushMaterials",
        asset_name="M_RVT_SnowWriter_Test",
        rgb=(1.0, 0.0, 0.0),
        overwrite=False,
    )
"""

ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EDITOR_ASSETS = unreal.EditorAssetLibrary
MATERIAL_LIB = unreal.MaterialEditingLibrary


def _log(msg: str) -> None:
    unreal.log(f"[material_tools] {msg}")


def _warn(msg: str) -> None:
    unreal.log_warning(f"[material_tools] {msg}")


def _ensure_package_path(package_path: str) -> None:
    if not package_path.startswith("/Game/"):
        raise ValueError("package_path must start with /Game/")
    if not EDITOR_ASSETS.does_directory_exist(package_path):
        EDITOR_ASSETS.make_directory(package_path)



def _delete_asset_if_requested(asset_path: str, overwrite: bool) -> None:
    if EDITOR_ASSETS.does_asset_exist(asset_path):
        if not overwrite:
            raise RuntimeError(f"Asset already exists: {asset_path}")
        if not EDITOR_ASSETS.delete_asset(asset_path):
            raise RuntimeError(f"Could not delete existing asset: {asset_path}")



def _create_material_asset(package_path: str, asset_name: str, overwrite: bool = False):
    _ensure_package_path(package_path)
    asset_path = f"{package_path}/{asset_name}"
    _delete_asset_if_requested(asset_path, overwrite)

    material = ASSET_TOOLS.create_asset(
        asset_name,
        package_path,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if not material:
        raise RuntimeError(f"Failed to create material: {asset_path}")

    _log(f"Created material: {asset_path}")
    return material, asset_path



def _set_material_domain(material, enum_names):
    for enum_name in enum_names:
        enum_val = getattr(unreal.MaterialDomain, enum_name, None)
        if enum_val is not None:
            material.set_editor_property("material_domain", enum_val)
            return enum_name
    raise RuntimeError(f"None of the material domain enum names exist: {enum_names}")



def _connect_custom_input(source_expr, custom_expr, input_names):
    for input_name in input_names:
        try:
            MATERIAL_LIB.connect_material_expressions(source_expr, "", custom_expr, input_name)
            _log(f"Connected custom input '{input_name}'")
            return input_name
        except Exception:
            pass
    raise RuntimeError(f"Could not connect custom expression input. Tried: {input_names}")



def create_basic_color_material(
    package_path: str = "/Game/CityPark/SnowSystem/BrushMaterials",
    asset_name: str = "M_TestColor",
    rgb=(1.0, 0.0, 0.0),
    overwrite: bool = False,
):
    material, asset_path = _create_material_asset(package_path, asset_name, overwrite)

    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    _set_material_domain(material, ["MD_SURFACE"])

    vec = MATERIAL_LIB.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, -600, 0)
    vec.set_editor_property("constant", unreal.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))

    MATERIAL_LIB.connect_material_property(vec, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MATERIAL_LIB.recompile_material(material)
    MATERIAL_LIB.layout_material_expressions(material)
    EDITOR_ASSETS.save_loaded_asset(material)

    _log(f"Saved basic color material: {asset_path}")
    return material



def create_rvt_snow_writer_test(
    package_path: str = "/Game/CityPark/SnowSystem/BrushMaterials",
    asset_name: str = "M_RVT_SnowWriter_Test",
    rgb=(1.0, 0.0, 0.0),
    overwrite: bool = False,
):
    """Create a simple surface material that writes a constant color into RVT output.

    R channel can be used as plow mask, G as wheel mask.
    """

    material, asset_path = _create_material_asset(package_path, asset_name, overwrite)

    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    _set_material_domain(material, ["MD_SURFACE"])

    # Make it useful both in main pass and when rendered into RVT.
    vec = MATERIAL_LIB.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, -700, -100)
    vec.set_editor_property("constant", unreal.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))

    roughness = MATERIAL_LIB.create_material_expression(material, unreal.MaterialExpressionConstant, -700, 120)
    roughness.set_editor_property("r", 1.0)

    MATERIAL_LIB.connect_material_property(vec, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MATERIAL_LIB.connect_material_property(roughness, "", unreal.MaterialProperty.MP_ROUGHNESS)

    rvt_output_class = getattr(unreal, "MaterialExpressionRuntimeVirtualTextureOutput", None)
    if rvt_output_class is None:
        raise RuntimeError("MaterialExpressionRuntimeVirtualTextureOutput is not available in this Unreal Python API")

    rvt_output = MATERIAL_LIB.create_material_expression(material, rvt_output_class, -50, 0)

    # Input label differs across UE versions. Try the common variants.
    _connect_custom_input(vec, rvt_output, ["Base Color", "BaseColor"])

    try:
        _connect_custom_input(roughness, rvt_output, ["Roughness"])
    except Exception:
        _warn("Could not connect Roughness to RVT output; continuing with Base Color only")

    MATERIAL_LIB.recompile_material(material)
    MATERIAL_LIB.layout_material_expressions(material)
    EDITOR_ASSETS.save_loaded_asset(material)

    _log(f"Saved RVT writer material: {asset_path}")
    return material



def create_rvt_writer_pair(overwrite: bool = False):
    """Convenience helper for snow system setup.

    Creates:
    - M_RVT_PlowWriter in red (R channel)
    - M_RVT_WheelWriter in green (G channel)
    """

    create_rvt_snow_writer_test(
        asset_name="M_RVT_PlowWriter",
        rgb=(1.0, 0.0, 0.0),
        overwrite=overwrite,
    )
    create_rvt_snow_writer_test(
        asset_name="M_RVT_WheelWriter",
        rgb=(0.0, 1.0, 0.0),
        overwrite=overwrite,
    )
    _log("Created RVT writer pair")


if __name__ == "__main__":
    _log("Loaded material_tools.py")
