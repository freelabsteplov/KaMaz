import json
import os

import unreal


MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
RVT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP"
PARENT_MATERIAL_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP_LandscapeRuntimeFix"
LANDSCAPE_MI_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_LandscapeRuntimeFix"
SNOW_DIFFUSE_PATH = "/Game/CAA_SnowV2/SnowV2P1/TexturesP1/T_SnowV2P1_2K_Diffuse"
SNOW_NORMAL_PATH = "/Game/CAA_SnowV2/SnowV2P1/TexturesP1/T_SnowV2P1_2K_Normal"
SNOW_ROUGHNESS_PATH = "/Game/CAA_SnowV2/SnowV2P1/TexturesP1/T_SnowV2P1_2K_Roughness"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "fix_snowtest_landscape_runtime_receiver.json",
)
DEFAULT_STAMP_SPACING_CM = 15.0


ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
ASSET_LIB = unreal.EditorAssetLibrary
MAT_LIB = unreal.MaterialEditingLibrary


def _path(obj):
    if not obj:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _safe_set(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception:
        return False


def _load_asset(path):
    return ASSET_LIB.load_asset(path)


def _ensure_dir(package_path: str):
    if not ASSET_LIB.does_directory_exist(package_path):
        ASSET_LIB.make_directory(package_path)


def _ensure_material(asset_path: str):
    existing = _load_asset(asset_path)
    if existing is not None and isinstance(existing, unreal.Material):
        return existing, False

    package_path, asset_name = asset_path.rsplit("/", 1)
    _ensure_dir(package_path)
    if ASSET_LIB.does_asset_exist(asset_path):
        ASSET_LIB.delete_asset(asset_path)

    created = ASSET_TOOLS.create_asset(
        asset_name,
        package_path,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if created is None:
        raise RuntimeError(f"Failed to create material: {asset_path}")
    return created, True


def _ensure_material_instance(asset_path: str):
    existing = _load_asset(asset_path)
    if existing is not None and isinstance(existing, unreal.MaterialInstanceConstant):
        return existing, False

    package_path, asset_name = asset_path.rsplit("/", 1)
    _ensure_dir(package_path)
    if ASSET_LIB.does_asset_exist(asset_path):
        ASSET_LIB.delete_asset(asset_path)

    created = ASSET_TOOLS.create_asset(
        asset_name,
        package_path,
        unreal.MaterialInstanceConstant,
        unreal.MaterialInstanceConstantFactoryNew(),
    )
    if created is None:
        raise RuntimeError(f"Failed to create material instance: {asset_path}")
    return created, True


def _expr(material, cls_name, x, y):
    cls = getattr(unreal, cls_name, None)
    if cls is None:
        raise RuntimeError(f"Missing class {cls_name}")
    expr = MAT_LIB.create_material_expression(material, cls, x, y)
    if expr is None:
        raise RuntimeError(f"Could not create expression {cls_name}")
    _safe_set(expr, "material_expression_editor_x", x)
    _safe_set(expr, "material_expression_editor_y", y)
    return expr


def _connect(src, src_pin, dst, dst_pin):
    MAT_LIB.connect_material_expressions(src, src_pin if src_pin else "", dst, dst_pin)


def _scalar_param(material, x, y, name, default):
    expr = _expr(material, "MaterialExpressionScalarParameter", x, y)
    _safe_set(expr, "parameter_name", name)
    _safe_set(expr, "default_value", float(default))
    return expr


def _vector_param(material, x, y, name, rgb):
    expr = _expr(material, "MaterialExpressionVectorParameter", x, y)
    _safe_set(expr, "parameter_name", name)
    _safe_set(expr, "default_value", unreal.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))
    return expr


def _texture_param(material, x, y, name, texture):
    expr = _expr(material, "MaterialExpressionTextureSampleParameter2D", x, y)
    _safe_set(expr, "parameter_name", name)
    if texture:
        _safe_set(expr, "texture", texture)
    return expr


def _find_actor(world, label: str):
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    for actor in actors:
        if actor.get_actor_label() == label:
            return actor
    return None


def _find_plow_component(actor):
    if not actor:
        return None
    try:
        components = actor.get_components_by_class(unreal.SceneComponent)
    except Exception:
        components = []
    for component in components:
        if "BP_PlowBrush_Component" in component.get_name():
            return component
    for component in components:
        name = component.get_name()
        if "PlowBrush" in name or "BP_PlowBrush" in name:
            return component
    return None


def build_parent_material(result: dict):
    material, created = _ensure_material(PARENT_MATERIAL_PATH)
    rvt_asset = _load_asset(RVT_PATH)
    snow_diffuse = _load_asset(SNOW_DIFFUSE_PATH)
    snow_normal = _load_asset(SNOW_NORMAL_PATH)
    snow_roughness = _load_asset(SNOW_ROUGHNESS_PATH)
    if not rvt_asset:
        raise RuntimeError(f"Missing RVT asset: {RVT_PATH}")
    if not snow_diffuse or not snow_normal or not snow_roughness:
        raise RuntimeError("CAA_SnowV2 texture set could not be loaded")

    MAT_LIB.delete_all_material_expressions(material)
    _safe_set(material, "material_domain", unreal.MaterialDomain.MD_SURFACE)
    _safe_set(material, "blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    _safe_set(material, "shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    _safe_set(material, "use_material_attributes", False)
    _safe_set(material, "two_sided", False)
    _safe_set(material, "used_with_landscape", True)
    _safe_set(material, "bUsedWithLandscape", True)
    _safe_set(material, "used_with_nanite", True)
    _safe_set(material, "bUsedWithNanite", True)

    texcoord = _expr(material, "MaterialExpressionTextureCoordinate", -2200, -200)
    snow_uv_scale = _scalar_param(material, -2200, -60, "SnowTexUVScale", 8.0)
    scaled_uv = _expr(material, "MaterialExpressionMultiply", -1960, -160)
    _connect(texcoord, "", scaled_uv, "A")
    _connect(snow_uv_scale, "", scaled_uv, "B")

    snow_diffuse_expr = _texture_param(material, -1700, -260, "Snow_Diffuse", snow_diffuse)
    _connect(scaled_uv, "", snow_diffuse_expr, "UVs")

    snow_normal_expr = _texture_param(material, -1700, 120, "Snow_Normal", snow_normal)
    _connect(scaled_uv, "", snow_normal_expr, "UVs")

    snow_roughness_expr = _texture_param(material, -1700, 360, "Snow_Roughness", snow_roughness)
    _connect(scaled_uv, "", snow_roughness_expr, "UVs")

    rvt_sample = _expr(material, "MaterialExpressionRuntimeVirtualTextureSampleParameter", -2200, 620)
    _safe_set(rvt_sample, "parameter_name", "SnowRVT")
    _safe_set(rvt_sample, "virtual_texture", rvt_asset)
    mat_type = getattr(unreal.RuntimeVirtualTextureMaterialType, "BASE_COLOR_NORMAL_SPECULAR_MASK_Y_CO_CG", None)
    if mat_type is not None:
        _safe_set(rvt_sample, "material_type", mat_type)

    mask_sat = _expr(material, "MaterialExpressionSaturate", -1940, 620)
    _connect(rvt_sample, "Mask", mask_sat, "Input")

    height_contrast = _scalar_param(material, -1940, 760, "HeightContrast", 1.0)
    mask_pow = _expr(material, "MaterialExpressionPower", -1700, 620)
    _connect(mask_sat, "", mask_pow, "Base")
    _connect(height_contrast, "", mask_pow, "Exp")

    pressed_color = _vector_param(material, -1460, -60, "PressedSnowColor", (0.25, 0.25, 0.25))
    base_lerp = _expr(material, "MaterialExpressionLinearInterpolate", -1180, -120)
    _connect(snow_diffuse_expr, "RGB", base_lerp, "A")
    _connect(pressed_color, "", base_lerp, "B")
    _connect(mask_pow, "", base_lerp, "Alpha")

    snow_roughness_scale = _scalar_param(material, -1460, 280, "SnowRoughness", 0.9)
    rough_tex_mul = _expr(material, "MaterialExpressionMultiply", -1180, 320)
    _connect(snow_roughness_expr, "R", rough_tex_mul, "A")
    _connect(snow_roughness_scale, "", rough_tex_mul, "B")

    pressed_roughness = _scalar_param(material, -1460, 440, "PressedRoughness", 0.45)
    rough_lerp = _expr(material, "MaterialExpressionLinearInterpolate", -920, 360)
    _connect(rough_tex_mul, "", rough_lerp, "A")
    _connect(pressed_roughness, "", rough_lerp, "B")
    _connect(mask_pow, "", rough_lerp, "Alpha")

    height_bias = _scalar_param(material, -1460, 860, "HeightBias", 0.0)
    height_sub = _expr(material, "MaterialExpressionSubtract", -1180, 860)
    _connect(mask_pow, "", height_sub, "A")
    _connect(height_bias, "", height_sub, "B")

    height_amp = _scalar_param(material, -1460, 1000, "HeightAmplitude", -100.0)
    height_scalar = _expr(material, "MaterialExpressionMultiply", -920, 920)
    _connect(height_sub, "", height_scalar, "A")
    _connect(height_amp, "", height_scalar, "B")

    world_up = _expr(material, "MaterialExpressionConstant3Vector", -920, 1080)
    _safe_set(world_up, "constant", unreal.LinearColor(0.0, 0.0, 1.0, 1.0))
    wpo_mul = _expr(material, "MaterialExpressionMultiply", -660, 1000)
    _connect(world_up, "", wpo_mul, "A")
    _connect(height_scalar, "", wpo_mul, "B")

    MAT_LIB.connect_material_property(base_lerp, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MAT_LIB.connect_material_property(rough_lerp, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MAT_LIB.connect_material_property(snow_normal_expr, "RGB", unreal.MaterialProperty.MP_NORMAL)
    MAT_LIB.connect_material_property(wpo_mul, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)

    MAT_LIB.layout_material_expressions(material)
    MAT_LIB.recompile_material(material)
    saved = bool(ASSET_LIB.save_loaded_asset(material, False))

    result["parent_material"] = {
        "path": PARENT_MATERIAL_PATH,
        "created": created,
        "saved": saved,
    }


def build_landscape_instance(result: dict):
    instance, created = _ensure_material_instance(LANDSCAPE_MI_PATH)
    parent = _load_asset(PARENT_MATERIAL_PATH)
    rvt = _load_asset(RVT_PATH)
    diffuse = _load_asset(SNOW_DIFFUSE_PATH)
    normal = _load_asset(SNOW_NORMAL_PATH)
    roughness = _load_asset(SNOW_ROUGHNESS_PATH)

    _safe_set(instance, "parent", parent)
    try:
        MAT_LIB.set_material_instance_runtime_virtual_texture_parameter_value(instance, "SnowRVT", rvt)
    except Exception:
        pass

    scalar_values = {
        "SnowTexUVScale": 8.0,
        "HeightContrast": 1.0,
        "HeightBias": 0.0,
        "HeightAmplitude": -100.0,
        "SnowRoughness": 0.9,
        "PressedRoughness": 0.45,
    }
    for name, value in scalar_values.items():
        MAT_LIB.set_material_instance_scalar_parameter_value(instance, name, value)

    MAT_LIB.set_material_instance_vector_parameter_value(
        instance, "PressedSnowColor", unreal.LinearColor(0.25, 0.25, 0.25, 1.0)
    )
    MAT_LIB.set_material_instance_texture_parameter_value(instance, "Snow_Diffuse", diffuse)
    MAT_LIB.set_material_instance_texture_parameter_value(instance, "Snow_Normal", normal)
    MAT_LIB.set_material_instance_texture_parameter_value(instance, "Snow_Roughness", roughness)
    MAT_LIB.update_material_instance(instance)
    saved = bool(ASSET_LIB.save_loaded_asset(instance, False))

    result["landscape_instance"] = {
        "path": LANDSCAPE_MI_PATH,
        "created": created,
        "saved": saved,
    }


def apply_level_fix(result: dict):
    world = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    if not world:
        raise RuntimeError(f"Could not load map: {MAP_PATH}")

    landscape = _find_actor(world, "Landscape")
    trail_actor = _find_actor(world, "SnowRuntimeTrailBridgeActor")
    kamaz = _find_actor(world, "Kamaz_SnowTest")
    if not landscape:
        raise RuntimeError("Landscape actor not found")
    if not trail_actor:
        raise RuntimeError("SnowRuntimeTrailBridgeActor not found")
    if not kamaz:
        raise RuntimeError("Kamaz_SnowTest not found")

    landscape_mi = _load_asset(LANDSCAPE_MI_PATH)
    if not landscape_mi:
        raise RuntimeError("Landscape runtime fix MI not found")

    landscape.modify()
    landscape.set_editor_property("landscape_material", landscape_mi)
    if callable(getattr(landscape, "post_edit_change", None)):
        landscape.post_edit_change()
    if callable(getattr(landscape, "mark_package_dirty", None)):
        landscape.mark_package_dirty()

    plow_component = _find_plow_component(kamaz)
    if not plow_component:
        raise RuntimeError("Plow component not found on Kamaz_SnowTest")

    component_class = unreal.load_class(None, "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent")
    trail_component = trail_actor.get_component_by_class(component_class) if component_class else None
    if not trail_component:
        raise RuntimeError("SnowRuntimeTrailBridgeComponent not found")

    trail_actor.modify()
    trail_component.modify()
    updates = {
        "bEnableRuntimeTrail": True,
        "StampSpacingCm": DEFAULT_STAMP_SPACING_CM,
        "bMarkPersistentSnowState": True,
        "PersistentPlowLengthCm": 120.0,
        "PersistentPlowWidthCm": 320.0,
        "PersistentSurfaceFamily": unreal.SnowReceiverSurfaceFamily.LANDSCAPE,
        "SourceComponentOverride": plow_component,
        "bEnableRvtVisualStamp": True,
        "RuntimeHeightAmplitudeWhenActive": -100.0,
        "RuntimeHeightAmplitudeWhenInactive": 0.0,
        "bUseSourceHeightGate": True,
        "SourceActiveMaxRelativeZ": -0.5,
    }
    for name, value in updates.items():
        trail_component.set_editor_property(name, value)

    if callable(getattr(trail_component, "post_edit_change", None)):
        trail_component.post_edit_change()
    if callable(getattr(trail_actor, "post_edit_change", None)):
        trail_actor.post_edit_change()
    if callable(getattr(trail_actor, "mark_package_dirty", None)):
        trail_actor.mark_package_dirty()

    settings = unreal.get_default_object(unreal.SnowStateRuntimeSettings)
    if settings:
        settings.set_editor_property("bEnablePersistentSnowStateV1", True)
        if callable(getattr(settings, "save_config", None)):
            settings.save_config()

    result["level_fix"] = {
        "landscape_actor_path": _path(landscape),
        "landscape_material_after": _path(landscape.get_editor_property("landscape_material")),
        "trail_component_path": _path(trail_component),
        "plow_component_path": _path(plow_component),
        "persistent_surface_family": str(trail_component.get_editor_property("PersistentSurfaceFamily")),
        "source_override": _path(trail_component.get_editor_property("SourceComponentOverride")),
        "persistent_snow_enabled": bool(settings.get_editor_property("bEnablePersistentSnowStateV1")) if settings else None,
    }

    result["saved_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    result["saved_packages"] = bool(unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True))


def main():
    result = {
        "map_path": MAP_PATH,
        "parent_material": {},
        "landscape_instance": {},
        "level_fix": {},
        "saved_level": False,
        "saved_packages": False,
        "error": "",
    }

    try:
        build_parent_material(result)
        build_landscape_instance(result)
        apply_level_fix(result)
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
