import json
import os

import unreal


ROOT = "/Game/CityPark/SnowSystem/SnowRuntime_V1"
MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"

FOLDERS = [
    ROOT,
    f"{ROOT}/Blueprints",
    f"{ROOT}/Materials",
    f"{ROOT}/Materials/Instances",
    f"{ROOT}/RenderTargets",
    f"{ROOT}/Niagara",
    f"{ROOT}/Data",
    f"{ROOT}/Receivers",
    f"{ROOT}/RVT",
]

RT_A_PATH = f"{ROOT}/RenderTargets/RT_SnowState_A_V1"
RT_B_PATH = f"{ROOT}/RenderTargets/RT_SnowState_B_V1"
MAT_WHEEL_PATH = f"{ROOT}/Materials/M_SnowState_Write_Wheel_V1"
MAT_PLOW_PATH = f"{ROOT}/Materials/M_SnowState_Write_Plow_V1"
SANITY_GREEN_MATERIAL_PATH = "/Game/CityPark/SnowSystem/BrushMaterials/M_RT_FullscreenGreen_Test"
BLACK_TEXTURE_PATH = "/Engine/EngineResources/Black.Black"
BP_STATE_MANAGER_PATH = f"{ROOT}/Blueprints/BP_SnowStateManager_V1"
BP_FX_MANAGER_PATH = f"{ROOT}/Blueprints/BP_SnowFXManager_V1"
BP_BOOTSTRAP_PATH = f"{ROOT}/Blueprints/BP_SnowRuntimeBootstrap_V1"

OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "build_snow_runtime_v1_phase1.json",
)

ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
ASSET_LIB = unreal.EditorAssetLibrary
MAT_LIB = unreal.MaterialEditingLibrary
RENDER_LIB = unreal.RenderingLibrary


def _save_output(payload: dict):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _ensure_folders():
    for folder in FOLDERS:
        if not ASSET_LIB.does_directory_exist(folder):
            ASSET_LIB.make_directory(folder)


def _load_asset(asset_path: str):
    return ASSET_LIB.load_asset(asset_path)


def _create_or_load_rt(asset_path: str, size: int = 2048):
    asset = _load_asset(asset_path)
    created = False
    if asset is None:
        package_path, asset_name = asset_path.rsplit("/", 1)
        factory = unreal.TextureRenderTargetFactoryNew()
        asset = ASSET_TOOLS.create_asset(asset_name, package_path, unreal.TextureRenderTarget2D, factory)
        if asset is None:
            raise RuntimeError(f"Failed to create render target: {asset_path}")
        created = True

    asset.set_editor_property("size_x", size)
    asset.set_editor_property("size_y", size)
    asset.set_editor_property("clear_color", unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
    try:
        asset.set_editor_property("render_target_format", unreal.TextureRenderTargetFormat.RTF_RGBA16f)
    except Exception:
        pass
    ASSET_LIB.save_loaded_asset(asset, False)
    return asset, created


def _connect(src, src_pin, dst, dst_pin):
    MAT_LIB.connect_material_expressions(src, src_pin, dst, dst_pin)


def _create_or_load_material(asset_path: str):
    material = _load_asset(asset_path)
    created = False
    package_path, asset_name = asset_path.rsplit("/", 1)

    if material is not None:
        if not ASSET_LIB.delete_asset(asset_path):
            raise RuntimeError(f"Failed to recreate material, could not delete existing asset: {asset_path}")
        material = None

    material = ASSET_TOOLS.create_asset(asset_name, package_path, unreal.Material, unreal.MaterialFactoryNew())
    if material is None:
        raise RuntimeError(f"Failed to create material: {asset_path}")
    created = True
    return material, created


def _build_write_material(asset_path: str):
    material, created = _create_or_load_material(asset_path)

    MAT_LIB.delete_all_material_expressions(material)
    material.set_editor_property("material_domain", unreal.MaterialDomain.MD_SURFACE)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)

    texcoord = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionTextureCoordinate, -1800, -100)
    black_texture = _load_asset(BLACK_TEXTURE_PATH)

    previous_state = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -1800, 180)
    previous_state.set_editor_property("parameter_name", "PreviousStateTexture")
    previous_state.set_editor_property("texture", black_texture)
    _connect(texcoord, "", previous_state, "Coordinates")

    stamp_center_u = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -1500, -10)
    stamp_center_u.set_editor_property("parameter_name", "StampCenterU")
    stamp_center_u.set_editor_property("default_value", 0.5)

    stamp_center_v = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -1500, 80)
    stamp_center_v.set_editor_property("parameter_name", "StampCenterV")
    stamp_center_v.set_editor_property("default_value", 0.5)

    stamp_center_uv = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionAppendVector, -1260, 20)
    _connect(stamp_center_u, "", stamp_center_uv, "A")
    _connect(stamp_center_v, "", stamp_center_uv, "B")

    stamp_radius = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -1500, 180)
    stamp_radius.set_editor_property("parameter_name", "StampRadiusUV")
    stamp_radius.set_editor_property("default_value", 0.1)

    falloff_power = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -1500, 320)
    falloff_power.set_editor_property("parameter_name", "StampFalloffPower")
    falloff_power.set_editor_property("default_value", 2.0)

    stamp_delta_r = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -1500, 460)
    stamp_delta_r.set_editor_property("parameter_name", "StampDeltaR")
    stamp_delta_r.set_editor_property("default_value", 1.0)

    stamp_delta_g = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -1500, 560)
    stamp_delta_g.set_editor_property("parameter_name", "StampDeltaG")
    stamp_delta_g.set_editor_property("default_value", 0.0)

    stamp_delta_b = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -1500, 660)
    stamp_delta_b.set_editor_property("parameter_name", "StampDeltaB")
    stamp_delta_b.set_editor_property("default_value", 0.0)

    stamp_delta_a = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -1500, 760)
    stamp_delta_a.set_editor_property("parameter_name", "StampDeltaA")
    stamp_delta_a.set_editor_property("default_value", 0.0)

    distance_node = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionDistance, -1180, -20)
    _connect(texcoord, "", distance_node, "A")
    _connect(stamp_center_uv, "", distance_node, "B")

    divide_node = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionDivide, -900, -20)
    _connect(distance_node, "", divide_node, "A")
    _connect(stamp_radius, "", divide_node, "B")

    one_const = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionConstant, -700, -140)
    one_const.set_editor_property("r", 1.0)

    zero_const = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionConstant, -430, -170)
    zero_const.set_editor_property("r", 0.0)

    one_minus = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionSubtract, -660, -20)
    _connect(one_const, "", one_minus, "A")
    _connect(divide_node, "", one_minus, "B")

    clamp_low = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionMax, -430, -20)
    _connect(one_minus, "", clamp_low, "A")
    _connect(zero_const, "", clamp_low, "B")

    clamp_high = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionMin, -180, -120)
    _connect(clamp_low, "", clamp_high, "A")
    _connect(one_const, "", clamp_high, "B")

    power_node = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionPower, 60, -20)
    _connect(clamp_high, "", power_node, "Base")
    _connect(falloff_power, "", power_node, "Exp")

    red_mul = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionMultiply, 300, -120)
    _connect(power_node, "", red_mul, "A")
    _connect(stamp_delta_r, "", red_mul, "B")

    green_mul = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionMultiply, 300, 0)
    _connect(power_node, "", green_mul, "A")
    _connect(stamp_delta_g, "", green_mul, "B")

    blue_mul = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionMultiply, 300, 120)
    _connect(power_node, "", blue_mul, "A")
    _connect(stamp_delta_b, "", blue_mul, "B")

    axis_r = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionConstant4Vector, -1320, 900)
    axis_r.set_editor_property("constant", unreal.LinearColor(1.0, 0.0, 0.0, 0.0))

    axis_g = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionConstant4Vector, -1320, 1020)
    axis_g.set_editor_property("constant", unreal.LinearColor(0.0, 1.0, 0.0, 0.0))

    axis_b = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionConstant4Vector, -1320, 1140)
    axis_b.set_editor_property("constant", unreal.LinearColor(0.0, 0.0, 1.0, 0.0))

    prev_r = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionDotProduct, -1040, 900)
    _connect(previous_state, "", prev_r, "A")
    _connect(axis_r, "", prev_r, "B")

    prev_g = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionDotProduct, -1040, 1020)
    _connect(previous_state, "", prev_g, "A")
    _connect(axis_g, "", prev_g, "B")

    prev_b = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionDotProduct, -1040, 1140)
    _connect(previous_state, "", prev_b, "A")
    _connect(axis_b, "", prev_b, "B")

    sum_r = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionAdd, 560, -160)
    _connect(prev_r, "", sum_r, "A")
    _connect(red_mul, "", sum_r, "B")

    sum_g = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionAdd, 560, 0)
    _connect(prev_g, "", sum_g, "A")
    _connect(green_mul, "", sum_g, "B")

    sum_b = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionAdd, 560, 160)
    _connect(prev_b, "", sum_b, "A")
    _connect(blue_mul, "", sum_b, "B")

    clamp_r = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionMin, 820, -160)
    _connect(sum_r, "", clamp_r, "A")
    _connect(one_const, "", clamp_r, "B")

    clamp_g = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionMin, 820, 0)
    _connect(sum_g, "", clamp_g, "A")
    _connect(one_const, "", clamp_g, "B")

    clamp_b = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionMin, 820, 160)
    _connect(sum_b, "", clamp_b, "A")
    _connect(one_const, "", clamp_b, "B")

    rg_append = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionAppendVector, 1080, -50)
    _connect(clamp_r, "", rg_append, "A")
    _connect(clamp_g, "", rg_append, "B")

    rgb_append = MAT_LIB.create_material_expression(material, unreal.MaterialExpressionAppendVector, 1340, 10)
    _connect(rg_append, "", rgb_append, "A")
    _connect(clamp_b, "", rgb_append, "B")

    MAT_LIB.connect_material_property(rgb_append, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MAT_LIB.connect_material_property(rgb_append, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MAT_LIB.recompile_material(material)
    MAT_LIB.layout_material_expressions(material)
    ASSET_LIB.save_loaded_asset(material, False)

    return material, created


def _create_or_load_blueprint(asset_path: str, parent_class_path: str):
    blueprint = _load_asset(asset_path)
    created = False
    if blueprint is None:
        package_path, asset_name = asset_path.rsplit("/", 1)
        parent_class = unreal.load_class(None, parent_class_path)
        if parent_class is None:
            raise RuntimeError(f"Could not load parent class: {parent_class_path}")
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", parent_class)
        blueprint = ASSET_TOOLS.create_asset(asset_name, package_path, unreal.Blueprint, factory)
        if blueprint is None:
            raise RuntimeError(f"Failed to create blueprint: {asset_path}")
        created = True

    ASSET_LIB.save_loaded_asset(blueprint, False)
    return blueprint, created


def _try_set_bp_defaults(blueprint, properties: dict):
    try:
        generated_class = blueprint.generated_class()
    except Exception:
        generated_class = None

    if generated_class is None:
        generated_class = getattr(blueprint, "generated_class", None)

    if generated_class is None:
        return False

    cdo = generated_class.get_default_object()
    if cdo is None:
        return False

    for key, value in properties.items():
        try:
            cdo.set_editor_property(key, value)
        except Exception:
            pass
    ASSET_LIB.save_loaded_asset(blueprint, False)
    return True


def _validate_debug_write(rt_a, rt_b, wheel_material):
    unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    world = unreal.EditorLevelLibrary.get_editor_world()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    sanity_green_material = _load_asset(SANITY_GREEN_MATERIAL_PATH)
    state_manager_class = unreal.load_class(None, "/Script/Kamaz_Cleaner.SnowStateManagerV1")
    if state_manager_class is None:
        raise RuntimeError("SnowStateManagerV1 class is not available for validation.")

    def _sample_color(rt_asset):
        sample = RENDER_LIB.read_render_target_raw_uv(world, rt_asset, 0.5, 0.5)
        return {
            "r": float(getattr(sample, "r", 0.0)),
            "g": float(getattr(sample, "g", 0.0)),
            "b": float(getattr(sample, "b", 0.0)),
            "a": float(getattr(sample, "a", 0.0)),
        }

    def _sample_color_at(rt_asset, u: float, v: float):
        sample = RENDER_LIB.read_render_target_raw_uv(world, rt_asset, u, v)
        return {
            "u": float(u),
            "v": float(v),
            "r": float(getattr(sample, "r", 0.0)),
            "g": float(getattr(sample, "g", 0.0)),
            "b": float(getattr(sample, "b", 0.0)),
            "a": float(getattr(sample, "a", 0.0)),
        }

    RENDER_LIB.clear_render_target2d(world, rt_a, unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
    RENDER_LIB.draw_material_to_render_target(world, rt_a, sanity_green_material)
    sanity_sample = _sample_color(rt_a)

    RENDER_LIB.clear_render_target2d(world, rt_a, unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
    RENDER_LIB.draw_material_to_render_target(world, rt_a, wheel_material)
    direct_writer_sample = _sample_color(rt_a)

    manager = actor_subsystem.spawn_actor_from_class(state_manager_class, unreal.Vector(0.0, 0.0, 100.0), unreal.Rotator(0.0, 0.0, 0.0))
    manager.set_editor_property("state_render_target_a", rt_a)
    manager.set_editor_property("state_render_target_b", rt_b)
    manager.set_editor_property("wheel_write_material", wheel_material)
    manager.set_editor_property("plow_write_material", wheel_material)
    manager.set_editor_property("world_mapping_origin", unreal.Vector(0.0, 0.0, 0.0))
    manager.set_editor_property("world_mapping_extent_cm", unreal.Vector2D(1000.0, 1000.0))
    manager.reset_state_render_targets(unreal.LinearColor(0.0, 0.0, 0.0, 0.0))

    initial_read_target = manager.get_current_read_render_target()
    initial_write_target = manager.get_current_write_render_target()

    stamp = unreal.SnowStateStampRequestV1()
    stamp.world_location = unreal.Vector(0.0, 0.0, 0.0)
    stamp.radius_cm = 250.0
    stamp.remaining_snow_depth_delta = 0.75
    stamp.compaction_rut_depth_delta = 0.20
    stamp.cleared_expose_road_delta = 0.40
    stamp.berm_side_pile_delta = 0.15
    stamp.falloff_power = 2.0

    manager.reset_state_render_targets(unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
    manager.queue_wheel_stamp(stamp)
    flushed = bool(manager.flush_queued_state_writes())
    active_rt = manager.get_authoritative_state_render_target()
    sample = _sample_color(active_rt)

    stamp1 = unreal.SnowStateStampRequestV1()
    stamp1.world_location = unreal.Vector(0.0, 0.0, 0.0)
    stamp1.radius_cm = 220.0
    stamp1.remaining_snow_depth_delta = 0.70
    stamp1.compaction_rut_depth_delta = 0.15
    stamp1.cleared_expose_road_delta = 0.10
    stamp1.berm_side_pile_delta = 0.05
    stamp1.falloff_power = 2.0

    stamp2 = unreal.SnowStateStampRequestV1()
    stamp2.world_location = unreal.Vector(400.0, 0.0, 0.0)
    stamp2.radius_cm = 220.0
    stamp2.remaining_snow_depth_delta = 0.25
    stamp2.compaction_rut_depth_delta = 0.55
    stamp2.cleared_expose_road_delta = 0.35
    stamp2.berm_side_pile_delta = 0.10
    stamp2.falloff_power = 2.0

    manager.reset_state_render_targets(unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
    manager.queue_wheel_stamp(stamp1)
    first_flush = bool(manager.flush_queued_state_writes())
    first_authoritative = manager.get_authoritative_state_render_target()
    first_read_target = manager.get_current_read_render_target()
    first_write_target = manager.get_current_write_render_target()
    stamp1_uv = {"u": 0.5, "v": 0.5}
    stamp2_uv = {"u": 0.7, "v": 0.5}
    stamp1_after_first = _sample_color_at(first_authoritative, stamp1_uv["u"], stamp1_uv["v"])
    stamp2_after_first = _sample_color_at(first_authoritative, stamp2_uv["u"], stamp2_uv["v"])

    manager.queue_wheel_stamp(stamp2)
    second_flush = bool(manager.flush_queued_state_writes())
    second_authoritative = manager.get_authoritative_state_render_target()
    second_read_target = manager.get_current_read_render_target()
    second_write_target = manager.get_current_write_render_target()
    stamp1_after_second = _sample_color_at(second_authoritative, stamp1_uv["u"], stamp1_uv["v"])
    stamp2_after_second = _sample_color_at(second_authoritative, stamp2_uv["u"], stamp2_uv["v"])

    two_stamp_ok = (
        first_flush
        and second_flush
        and stamp1_after_first["r"] > 0.01
        and stamp1_after_second["r"] > 0.01
        and (
            stamp2_after_second["r"] > 0.01
            or stamp2_after_second["g"] > 0.01
            or stamp2_after_second["b"] > 0.01
        )
    )
    actor_subsystem.destroy_actor(manager)

    return {
        "sanity_green_sample_center": sanity_sample,
        "direct_writer_sample_center": direct_writer_sample,
        "debug_write_flushed": flushed,
        "authoritative_state_rt": active_rt.get_path_name() if active_rt else "",
        "sample_center": sample,
        "safe_accumulation": bool(two_stamp_ok),
        "read_target_initial": initial_read_target.get_path_name() if initial_read_target else "",
        "write_target_initial": initial_write_target.get_path_name() if initial_write_target else "",
        "read_target_after_stamp1": first_read_target.get_path_name() if first_read_target else "",
        "write_target_after_stamp1": first_write_target.get_path_name() if first_write_target else "",
        "read_target_after_stamp2": second_read_target.get_path_name() if second_read_target else "",
        "write_target_after_stamp2": second_write_target.get_path_name() if second_write_target else "",
        "two_stamp_validation": {
            "stamp1_uv": stamp1_uv,
            "stamp2_uv": stamp2_uv,
            "stamp1_after_first": stamp1_after_first,
            "stamp2_after_first": stamp2_after_first,
            "stamp1_after_second": stamp1_after_second,
            "stamp2_after_second": stamp2_after_second,
            "result": bool(two_stamp_ok),
        },
        "channel_contract": {
            "wheel_proof": {
                "R": "RemainingSnowDepth delta",
                "G": "Compaction_RutDepth delta",
                "B": "Cleared_ExposeRoad delta",
                "A": "Berm_SidePile delta requested by manager but not emitted by current proof material output"
            },
            "plow_proof": {
                "R": "RemainingSnowDepth delta",
                "G": "Compaction_RutDepth delta",
                "B": "Cleared_ExposeRoad delta",
                "A": "Berm_SidePile delta requested by manager but not emitted by current proof material output"
            }
        },
    }


def main():
    result = {
        "root": ROOT,
        "folders": FOLDERS,
        "created_assets": {},
        "validation": {},
        "error": "",
    }

    try:
        _ensure_folders()

        rt_a, rt_a_created = _create_or_load_rt(RT_A_PATH)
        rt_b, rt_b_created = _create_or_load_rt(RT_B_PATH)
        wheel_mat, wheel_created = _build_write_material(MAT_WHEEL_PATH)
        plow_mat, plow_created = _build_write_material(MAT_PLOW_PATH)

        bp_state_manager, bp_state_created = _create_or_load_blueprint(BP_STATE_MANAGER_PATH, "/Script/Kamaz_Cleaner.SnowStateManagerV1")
        bp_fx_manager, bp_fx_created = _create_or_load_blueprint(BP_FX_MANAGER_PATH, "/Script/Kamaz_Cleaner.SnowFXManagerV1")
        bp_bootstrap, bp_bootstrap_created = _create_or_load_blueprint(BP_BOOTSTRAP_PATH, "/Script/Kamaz_Cleaner.SnowRuntimeBootstrapV1")

        _try_set_bp_defaults(
            bp_state_manager,
            {
                "state_render_target_a": rt_a,
                "state_render_target_b": rt_b,
                "wheel_write_material": wheel_mat,
                "plow_write_material": plow_mat,
                "world_mapping_extent_cm": unreal.Vector2D(25000.0, 25000.0),
                "active_area_half_extent_cm": 5000.0,
            },
        )

        result["created_assets"] = {
            "RT_SnowState_A_V1": {"path": rt_a.get_path_name(), "created": rt_a_created},
            "RT_SnowState_B_V1": {"path": rt_b.get_path_name(), "created": rt_b_created},
            "M_SnowState_Write_Wheel_V1": {"path": wheel_mat.get_path_name(), "created": wheel_created},
            "M_SnowState_Write_Plow_V1": {"path": plow_mat.get_path_name(), "created": plow_created},
            "BP_SnowStateManager_V1": {"path": bp_state_manager.get_path_name(), "created": bp_state_created},
            "BP_SnowFXManager_V1": {"path": bp_fx_manager.get_path_name(), "created": bp_fx_created},
            "BP_SnowRuntimeBootstrap_V1": {"path": bp_bootstrap.get_path_name(), "created": bp_bootstrap_created},
        }

        result["validation"] = _validate_debug_write(rt_a, rt_b, wheel_mat)
    except Exception as exc:
        result["error"] = str(exc)

    _save_output(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
