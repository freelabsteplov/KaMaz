import json
import json
import os
import runpy

import unreal


WRITER_MATERIAL_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_RVT_DebugWriter_MVP"
RECEIVER_PARENT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP"
LANDSCAPE_MI_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_LandscapeRuntimeFix"
MAP_PATH = "/Game/CityPark/SnowSystem/SnowTest_Level"
TRAIL_ACTOR_LABEL = "SnowRuntimeTrailBridgeActor"
KAMAZ_ACTOR_LABEL = "Kamaz_SnowTest"
BRIDGE_ACTOR_LABEL = "SnowHeightBridgeSurface_MVP"
TRAIL_COMPONENT_CLASS = "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeComponent"
DEFAULT_STAMP_SPACING_CM = 5.0
STAMP_EDGE_FEATHER_PERCENT = 0.2
DEFAULT_RECEIVER_HEIGHT_AMPLITUDE = 0.0
DEFAULT_RECEIVER_HEIGHT_CONTRAST = 0.60
DEFAULT_RECEIVER_THIN_SNOW_MIN_VISUAL_OPACITY = 0.38
DEFAULT_RECEIVER_EDGE_DUSTING_STRENGTH = 0.0
DEFAULT_REPEAT_ACCUMULATION_DEPTH = 0.0
DEFAULT_RIGHT_BERM_RAISE = 0.0
DEFAULT_RIGHT_BERM_SHARPNESS = 1.0
DEFAULT_RECEIVER_VISUAL_CLEAR_MASK_STRENGTH = 1.0
DEFAULT_RECEIVER_DEPTH_MASK_BOOST = 1.0
DEFAULT_RECEIVER_PRESSED_SNOW_COLOR = unreal.LinearColor(0.28, 0.29, 0.31, 1.0)
DEFAULT_RECEIVER_THIN_SNOW_UNDER_COLOR = unreal.LinearColor(0.38, 0.39, 0.41, 1.0)
DEFAULT_DIRTY_BERM_TINT_STRENGTH = 1.0
DEFAULT_DIRTY_BERM_COLOR = unreal.LinearColor(0.58, 0.52, 0.43, 1.0)
DEFAULT_WHEEL_TRACK_MASK_AMPLIFY = 0.0
DEFAULT_WHEEL_TRACK_CONTRAST = 1.0
DEFAULT_WHEEL_TRACK_STRENGTH = 0.0
DEFAULT_WHEEL_TRACK_ASPHALT_ROUGHNESS = 0.46
DEFAULT_WHEEL_TRACK_SNOW_ROUGHNESS = 0.68
DEFAULT_WHEEL_TRACK_ASPHALT_COLOR = unreal.LinearColor(0.22, 0.22, 0.24, 1.0)
DEFAULT_WHEEL_TRACK_SNOW_COLOR = unreal.LinearColor(0.46, 0.46, 0.48, 1.0)
DEFAULT_ENABLE_SNOW_WHEEL_TRACES = False
DEFAULT_RUNTIME_HEIGHT_AMPLITUDE_WHEN_ACTIVE = -95.0
DEFAULT_RUNTIME_HEIGHT_AMPLITUDE_WHEN_INACTIVE = 0.0
DEFAULT_ENABLE_REPEAT_CLEARING_ACCUMULATION = False
DEFAULT_FIRST_PASS_CLEAR_STRENGTH = 1.0
DEFAULT_REPEAT_PASS_CLEAR_STRENGTH_STEP = 0.0
DEFAULT_MAX_ACCUMULATED_CLEAR_STRENGTH = 1.0
DEFAULT_RIGHT_BERM_CONTINUATION_RATIO = 0.0
DEFAULT_REPEAT_TIER_Z_OFFSET_CM = 0.0
DEFAULT_USE_SOURCE_HEIGHT_GATE = False
DEFAULT_SOURCE_ACTIVE_MAX_RELATIVE_Z = 95.0
DEFAULT_MIN_STAMP_ENGAGEMENT_TO_WRITE = 0.18
DEFAULT_PLOW_LIFT_HEIGHT_FOR_NO_EFFECT = 1.0
DEFAULT_SNOWTEST_PLOW_SOURCE_RELATIVE_Z = 247.7487413018433
DEFAULT_SNOWTEST_VISIBLE_PLOW_RELATIVE_Z = 242.5751101945879
DEFAULT_SNOWTEST_FRONT_HITCH_RELATIVE_Z = 96.0
BRIDGE_MESH_PATH = "/Engine/EditorMeshes/EditorSphere.EditorSphere"
BRIDGE_RECEIVER_MI_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP"
BRIDGE_TARGET_Z_SCALE = 0.06
BRIDGE_COLLISION_PROFILE_NAME = "BlockAll"
KAMAZ_BLUEPRINT_PATH = "/Game/CityPark/Kamaz/model/KamazBP"
KAMAZ_BLUEPRINT_PLOW_SUBOBJECT_PATH = (
    "/Game/CityPark/Kamaz/model/KamazBP.KamazBP_C:BP_PlowBrush_Component_GEN_VARIABLE"
)
DEFAULT_KAMAZ_BP_PLOW_SOURCE_RELATIVE_Z = 115.53648237506742
KAMAZ_BLUEPRINT_VISIBLE_PLOW_SUBOBJECT_PATH = (
    "/Game/CityPark/Kamaz/model/KamazBP.KamazBP_C:PlowBrush_GEN_VARIABLE"
)
DEFAULT_KAMAZ_BP_VISIBLE_PLOW_RELATIVE_Z = 17.11015685604036
KAMAZ_BLUEPRINT_FRONT_HITCH_SUBOBJECT_PATH = (
    "/Game/CityPark/Kamaz/model/KamazBP.KamazBP_C:SM_FrontHitch_GEN_VARIABLE"
)
DEFAULT_KAMAZ_BP_FRONT_HITCH_RELATIVE_Z = 96.0
ACTIVE_RECEIVER_MI_PATHS = [
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K",
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_Tile8",
    "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_V3_Narrow_Tile4",
    LANDSCAPE_MI_PATH,
]
ROAD_INSTANCE_MAP = {
    "SnowSplineRoad_MVP": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K",
    "SnowSplineRoad_V1_Original_MVP": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_Tile8",
    "SnowSplineRoad_V3_Narrow_MVP": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_V3_Narrow_Tile4",
}
REBUILD_RECEIVER_SCRIPT = (
    "C:/Users/post/Documents/Unreal Projects/Kamaz_Cleaner/Pyton_script/unreal_tools/"
    "rebuild_m_snowreceiver_rvt_height_mvp_berm.py"
)
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "apply_right_plow_berm.json",
)

ASSET_LIB = unreal.EditorAssetLibrary
MAT_LIB = unreal.MaterialEditingLibrary


def _safe_set(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception:
        return False


def _expr(material, cls_name, x, y):
    cls = getattr(unreal, cls_name, None)
    if cls is None:
        raise RuntimeError(f"Missing class {cls_name}")
    expr = MAT_LIB.create_material_expression(material, cls, x, y)
    if expr is None:
        raise RuntimeError(f"Failed create {cls_name}")
    _safe_set(expr, "material_expression_editor_x", x)
    _safe_set(expr, "material_expression_editor_y", y)
    return expr


def _connect(src, src_outs, dst, dst_ins):
    if isinstance(src_outs, str):
        src_outs = [src_outs]
    if isinstance(dst_ins, str):
        dst_ins = [dst_ins]
    for src_out in src_outs:
        for dst_in in dst_ins:
            resolved_dst_in = "" if dst_in == "Input" else dst_in
            try:
                MAT_LIB.connect_material_expressions(src, src_out if src_out else "", dst, resolved_dst_in if resolved_dst_in else "")
                return {"ok": True, "src": src_out, "dst": resolved_dst_in}
            except Exception:
                pass
    return {"ok": False, "src": "", "dst": ""}


def _scalar_param(material, x, y, name, default):
    expr = _expr(material, "MaterialExpressionScalarParameter", x, y)
    _safe_set(expr, "parameter_name", name)
    _safe_set(expr, "default_value", float(default))
    return expr


def _const(material, x, y, value):
    expr = _expr(material, "MaterialExpressionConstant", x, y)
    _safe_set(expr, "r", float(value))
    return expr


def _find_actor_by_label(label):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_subsystem.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def _find_scene_plow_component(kamaz_actor):
    fallback = None
    for component in list(kamaz_actor.get_components_by_class(unreal.ActorComponent) or []):
        try:
            is_scene_component = isinstance(component, unreal.SceneComponent)
        except Exception:
            continue
        if not is_scene_component:
            continue

        try:
            name = component.get_name()
        except Exception:
            continue
        if "BP_PlowBrush_Component" in name:
            return component
        if ("PlowBrush" in name or "BP_PlowBrush" in name) and fallback is None:
            fallback = component
    return fallback


def _find_named_scene_component(actor, exact_name):
    for component in list(actor.get_components_by_class(unreal.ActorComponent) or []):
        try:
            is_scene_component = isinstance(component, unreal.SceneComponent)
        except Exception:
            continue
        if not is_scene_component:
            continue
        try:
            component_name = component.get_name()
        except Exception:
            continue
        if component_name == exact_name:
            return component
    return None


def _find_kamaz_actor():
    direct = _find_actor_by_label(KAMAZ_ACTOR_LABEL)
    if direct:
        return direct

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in actor_subsystem.get_all_level_actors():
        try:
            label = actor.get_actor_label()
        except Exception:
            label = ""
        try:
            name = actor.get_name()
        except Exception:
            name = ""
        if "Kamaz" in label or "Kamaz" in name:
            return actor
    return None


def _find_actor_component_by_fragment(actor, name_fragment):
    for component in list(actor.get_components_by_class(unreal.ActorComponent) or []):
        try:
            component_name = component.get_name()
        except Exception:
            component_name = ""
        try:
            class_name = component.get_class().get_name()
        except Exception:
            class_name = ""
        if name_fragment in component_name or name_fragment in class_name:
            return component
    return None


def _try_invoke(actor, function_name):
    direct = getattr(actor, function_name, None)
    if callable(direct):
        try:
            direct()
            return {"function": function_name, "path": "direct", "called": True, "error": ""}
        except Exception as exc:
            return {"function": function_name, "path": "direct", "called": False, "error": str(exc)}

    call_method = getattr(actor, "call_method", None)
    if callable(call_method):
        last_error = "No callable path exposed."
        for args in ((function_name,), (function_name, ())):
            try:
                call_method(*args)
                return {"function": function_name, "path": "call_method", "called": True, "error": ""}
            except Exception as exc:
                last_error = str(exc)
        return {"function": function_name, "path": "call_method", "called": False, "error": last_error}

    return {"function": function_name, "path": "none", "called": False, "error": "No callable path exposed."}


def _refresh_road_actor(actor):
    attempts = []

    rerun = _try_invoke(actor, "rerun_construction_scripts")
    attempts.append(rerun)
    if rerun["called"]:
        return attempts

    rebuild = _try_invoke(actor, "RebuildSplineMeshes")
    attempts.append(rebuild)
    if rebuild["called"]:
        return attempts

    post_edit_change = getattr(actor, "post_edit_change", None)
    if callable(post_edit_change):
        try:
            post_edit_change()
            attempts.append({"function": "post_edit_change", "path": "direct", "called": True, "error": ""})
        except Exception as exc:
            attempts.append(
                {"function": "post_edit_change", "path": "direct", "called": False, "error": str(exc)}
            )

    return attempts


def rebuild_writer_as_right_berm_signal(material, result):
    MAT_LIB.delete_all_material_expressions(material)

    _safe_set(material, "material_domain", unreal.MaterialDomain.MD_SURFACE)
    _safe_set(material, "blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    _safe_set(material, "shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)

    uv = _expr(material, "MaterialExpressionTextureCoordinate", -1560, -380)
    u_mask = _expr(material, "MaterialExpressionComponentMask", -1320, -500)
    _safe_set(u_mask, "r", True)
    _safe_set(u_mask, "g", False)
    _safe_set(u_mask, "b", False)
    _safe_set(u_mask, "a", False)
    _connect(uv, "", u_mask, ["Input", ""])

    v_mask = _expr(material, "MaterialExpressionComponentMask", -1320, -300)
    _safe_set(v_mask, "r", False)
    _safe_set(v_mask, "g", True)
    _safe_set(v_mask, "b", False)
    _safe_set(v_mask, "a", False)
    _connect(uv, "", v_mask, ["Input", ""])

    edge_pct = _scalar_param(material, -1560, -140, "StampEdgeFeatherPercent", STAMP_EDGE_FEATHER_PERCENT)
    eps = _const(material, -1560, 180, 0.001)
    one = _const(material, -1320, 180, 1.0)

    edge_safe = _expr(material, "MaterialExpressionMax", -1080, -140)
    _connect(edge_pct, "", edge_safe, "A")
    _connect(eps, "", edge_safe, "B")
    zero = _const(material, -1080, 20, 0.0)

    one_minus_u = _expr(material, "MaterialExpressionSubtract", -1080, -500)
    _connect(one, "", one_minus_u, "A")
    _connect(u_mask, "", one_minus_u, "B")

    one_minus_v = _expr(material, "MaterialExpressionSubtract", -1080, -300)
    _connect(one, "", one_minus_v, "A")
    _connect(v_mask, "", one_minus_v, "B")

    left_ratio = _expr(material, "MaterialExpressionDivide", -840, -620)
    _connect(u_mask, "", left_ratio, "A")
    _connect(edge_safe, "", left_ratio, "B")
    left_floor = _expr(material, "MaterialExpressionMax", -620, -680)
    _connect(left_ratio, "", left_floor, "A")
    _connect(zero, "", left_floor, "B")
    left_sat = _expr(material, "MaterialExpressionMin", -400, -680)
    _connect(left_floor, "", left_sat, "A")
    _connect(one, "", left_sat, "B")

    right_ratio = _expr(material, "MaterialExpressionDivide", -840, -460)
    _connect(one_minus_u, "", right_ratio, "A")
    _connect(edge_safe, "", right_ratio, "B")
    right_floor = _expr(material, "MaterialExpressionMax", -620, -520)
    _connect(right_ratio, "", right_floor, "A")
    _connect(zero, "", right_floor, "B")
    right_sat = _expr(material, "MaterialExpressionMin", -400, -520)
    _connect(right_floor, "", right_sat, "A")
    _connect(one, "", right_sat, "B")

    bottom_ratio = _expr(material, "MaterialExpressionDivide", -840, -300)
    _connect(v_mask, "", bottom_ratio, "A")
    _connect(edge_safe, "", bottom_ratio, "B")
    bottom_floor = _expr(material, "MaterialExpressionMax", -620, -360)
    _connect(bottom_ratio, "", bottom_floor, "A")
    _connect(zero, "", bottom_floor, "B")
    bottom_sat = _expr(material, "MaterialExpressionMin", -400, -360)
    _connect(bottom_floor, "", bottom_sat, "A")
    _connect(one, "", bottom_sat, "B")

    top_ratio = _expr(material, "MaterialExpressionDivide", -840, -140)
    _connect(one_minus_v, "", top_ratio, "A")
    _connect(edge_safe, "", top_ratio, "B")
    top_floor = _expr(material, "MaterialExpressionMax", -620, -200)
    _connect(top_ratio, "", top_floor, "A")
    _connect(zero, "", top_floor, "B")
    top_sat = _expr(material, "MaterialExpressionMin", -400, -200)
    _connect(top_floor, "", top_sat, "A")
    _connect(one, "", top_sat, "B")

    u_feather = _expr(material, "MaterialExpressionMin", -380, -540)
    _connect(left_sat, "", u_feather, "A")
    _connect(right_sat, "", u_feather, "B")

    v_feather = _expr(material, "MaterialExpressionMin", -380, -220)
    _connect(bottom_sat, "", v_feather, "A")
    _connect(top_sat, "", v_feather, "B")

    rect_feather = _expr(material, "MaterialExpressionMin", -160, -380)
    _connect(u_feather, "", rect_feather, "A")
    _connect(v_feather, "", rect_feather, "B")
    feather_mask = rect_feather

    berm_only = _scalar_param(material, -1180, 20, "BermOnly", 0.0)
    berm_only_sat = _expr(material, "MaterialExpressionSaturate", -920, 20)
    _connect(berm_only, "", berm_only_sat, "")
    berm_strength = _scalar_param(material, -1180, 100, "BermStrength", 1.0)
    berm_strength_sat = _expr(material, "MaterialExpressionSaturate", -920, 100)
    _connect(berm_strength, "", berm_strength_sat, "")

    one = _const(material, -1180, 180, 1.0)
    berm_invert = _expr(material, "MaterialExpressionSubtract", -920, 180)
    _connect(one, "", berm_invert, "A")
    _connect(berm_only_sat, "", berm_invert, "B")

    berm_edge_mask = _expr(material, "MaterialExpressionMultiply", 520, -20)
    _connect(berm_only_sat, "", berm_edge_mask, "A")
    _connect(feather_mask, "", berm_edge_mask, "B")
    berm_edge_mask_scaled = _expr(material, "MaterialExpressionMultiply", 740, -20)
    _connect(berm_edge_mask, "", berm_edge_mask_scaled, "A")
    _connect(berm_strength_sat, "", berm_edge_mask_scaled, "B")

    white = _expr(material, "MaterialExpressionConstant3Vector", 220, -220)
    _safe_set(white, "constant", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    base_rgb = _expr(material, "MaterialExpressionMultiply", 460, -120)
    _connect(berm_edge_mask_scaled, "", base_rgb, "A")
    _connect(white, "", base_rgb, "B")

    clear_strength = _scalar_param(material, 220, 120, "ClearStrength", 1.0)
    clear_strength_sat = _expr(material, "MaterialExpressionSaturate", 460, 120)
    _connect(clear_strength, "", clear_strength_sat, "")
    clear_with_type = _expr(material, "MaterialExpressionMultiply", 680, 120)
    _connect(clear_strength_sat, "", clear_with_type, "A")
    _connect(berm_invert, "", clear_with_type, "B")
    clear_strength_masked = _expr(material, "MaterialExpressionMultiply", 900, 120)
    _connect(clear_with_type, "", clear_strength_masked, "A")
    _connect(feather_mask, "", clear_strength_masked, "B")

    repeat_depth_strength = _scalar_param(material, 220, 220, "RepeatDepthStrength", 0.0)
    repeat_depth_strength_sat = _expr(material, "MaterialExpressionSaturate", 460, 220)
    _connect(repeat_depth_strength, "", repeat_depth_strength_sat, "")
    repeat_with_type = _expr(material, "MaterialExpressionMultiply", 680, 220)
    _connect(repeat_depth_strength_sat, "", repeat_with_type, "A")
    _connect(berm_invert, "", repeat_with_type, "B")
    repeat_depth_masked = _expr(material, "MaterialExpressionMultiply", 900, 220)
    _connect(repeat_with_type, "", repeat_depth_masked, "A")
    _connect(feather_mask, "", repeat_depth_masked, "B")

    c0 = _const(material, 220, 320, 0.0)
    nrm = _expr(material, "MaterialExpressionConstant3Vector", 460, 320)
    _safe_set(nrm, "constant", unreal.LinearColor(0.5, 0.5, 1.0, 1.0))

    rvt_out = _expr(material, "MaterialExpressionRuntimeVirtualTextureOutput", 760, 20)
    result["writer_connect_basecolor"] = _connect(base_rgb, "", rvt_out, ["Base Color", "BaseColor"])
    result["writer_connect_specular"] = _connect(repeat_depth_masked, "", rvt_out, "Specular")
    result["writer_connect_roughness"] = _connect(berm_edge_mask_scaled, "", rvt_out, "Roughness")
    result["writer_connect_normal"] = _connect(nrm, "", rvt_out, "Normal")
    result["writer_connect_mask"] = _connect(clear_strength_masked, "", rvt_out, ["Mask", "mask"])

    MAT_LIB.connect_material_property(base_rgb, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MAT_LIB.connect_material_property(c0, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MAT_LIB.connect_material_property(nrm, "", unreal.MaterialProperty.MP_NORMAL)

    MAT_LIB.recompile_material(material)
    MAT_LIB.layout_material_expressions(material)
    result["writer_saved"] = bool(ASSET_LIB.save_loaded_asset(material, False))
    result["writer_num_expressions"] = int(MAT_LIB.get_num_material_expressions(material))
    result["writer_edge_feather_percent"] = STAMP_EDGE_FEATHER_PERCENT


def update_snowtest_trail_settings(result):
    world = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    if not world:
        raise RuntimeError(f"Could not load map: {MAP_PATH}")

    trail_actor = _find_actor_by_label(TRAIL_ACTOR_LABEL)
    if not trail_actor:
        raise RuntimeError("SnowRuntimeTrailBridgeActor not found")

    kamaz = _find_kamaz_actor()
    if not kamaz:
        raise RuntimeError("Kamaz actor not found on SnowTest_Level")

    plow_component = _find_scene_plow_component(kamaz)
    if not plow_component:
        raise RuntimeError("Plow scene component not found on Kamaz_SnowTest")
    active_source_component = plow_component

    component_class = unreal.load_class(None, TRAIL_COMPONENT_CLASS)
    trail_component = trail_actor.get_component_by_class(component_class) if component_class else None
    if not trail_component:
        raise RuntimeError("SnowRuntimeTrailBridgeComponent not found")

    current_source = trail_component.get_editor_property("SourceComponentOverride")
    needs_save = (
        abs(float(trail_component.get_editor_property("StampSpacingCm")) - DEFAULT_STAMP_SPACING_CM) > 0.001
        or current_source != active_source_component
        or not bool(trail_component.get_editor_property("bEnableRuntimeTrail"))
        or not bool(trail_component.get_editor_property("bEnableRvtVisualStamp"))
        or not bool(trail_component.get_editor_property("bMarkPersistentSnowState"))
        or bool(trail_component.get_editor_property("bEnableRepeatClearingAccumulation"))
        != DEFAULT_ENABLE_REPEAT_CLEARING_ACCUMULATION
        or not bool(trail_component.get_editor_property("bEnableRuntimeReceiverHeightControl"))
        or bool(trail_component.get_editor_property("bUseSourceHeightGate")) != DEFAULT_USE_SOURCE_HEIGHT_GATE
        or abs(
            float(trail_component.get_editor_property("SourceActiveMaxRelativeZ")) - DEFAULT_SOURCE_ACTIVE_MAX_RELATIVE_Z
        ) > 0.001
        or abs(
            float(trail_component.get_editor_property("MinStampEngagementToWrite"))
            - DEFAULT_MIN_STAMP_ENGAGEMENT_TO_WRITE
        ) > 0.001
        or abs(
            float(trail_component.get_editor_property("PlowLiftHeightForNoEffect"))
            - DEFAULT_PLOW_LIFT_HEIGHT_FOR_NO_EFFECT
        ) > 0.001
        or abs(
            float(trail_component.get_editor_property("RuntimeHeightAmplitudeWhenActive"))
            - DEFAULT_RUNTIME_HEIGHT_AMPLITUDE_WHEN_ACTIVE
        ) > 0.001
        or abs(
            float(trail_component.get_editor_property("RuntimeHeightAmplitudeWhenInactive"))
            - DEFAULT_RUNTIME_HEIGHT_AMPLITUDE_WHEN_INACTIVE
        ) > 0.001
        or abs(
            float(trail_component.get_editor_property("FirstPassClearStrength"))
            - DEFAULT_FIRST_PASS_CLEAR_STRENGTH
        ) > 0.001
        or abs(
            float(trail_component.get_editor_property("RepeatPassClearStrengthStep"))
            - DEFAULT_REPEAT_PASS_CLEAR_STRENGTH_STEP
        ) > 0.001
        or abs(
            float(trail_component.get_editor_property("MaxAccumulatedClearStrength"))
            - DEFAULT_MAX_ACCUMULATED_CLEAR_STRENGTH
        ) > 0.001
        or abs(
            float(trail_component.get_editor_property("RightBermContinuationRatio"))
            - DEFAULT_RIGHT_BERM_CONTINUATION_RATIO
        ) > 0.001
        or abs(
            float(trail_component.get_editor_property("RepeatTierZOffsetCm"))
            - DEFAULT_REPEAT_TIER_Z_OFFSET_CM
        ) > 0.001
    )

    if needs_save:
        trail_actor.modify()
        trail_component.modify()
        trail_component.set_editor_property("StampSpacingCm", DEFAULT_STAMP_SPACING_CM)
        trail_component.set_editor_property("SourceComponentOverride", active_source_component)
        trail_component.set_editor_property("bEnableRuntimeTrail", True)
        trail_component.set_editor_property("bEnableRvtVisualStamp", True)
        trail_component.set_editor_property("bMarkPersistentSnowState", True)
        trail_component.set_editor_property(
            "bEnableRepeatClearingAccumulation", DEFAULT_ENABLE_REPEAT_CLEARING_ACCUMULATION
        )
        trail_component.set_editor_property("bEnableRuntimeReceiverHeightControl", True)
        trail_component.set_editor_property("bUseSourceHeightGate", DEFAULT_USE_SOURCE_HEIGHT_GATE)
        trail_component.set_editor_property("SourceActiveMaxRelativeZ", DEFAULT_SOURCE_ACTIVE_MAX_RELATIVE_Z)
        trail_component.set_editor_property("MinStampEngagementToWrite", DEFAULT_MIN_STAMP_ENGAGEMENT_TO_WRITE)
        trail_component.set_editor_property("PlowLiftHeightForNoEffect", DEFAULT_PLOW_LIFT_HEIGHT_FOR_NO_EFFECT)
        trail_component.set_editor_property("RuntimeHeightAmplitudeWhenActive", DEFAULT_RUNTIME_HEIGHT_AMPLITUDE_WHEN_ACTIVE)
        trail_component.set_editor_property("RuntimeHeightAmplitudeWhenInactive", DEFAULT_RUNTIME_HEIGHT_AMPLITUDE_WHEN_INACTIVE)
        trail_component.set_editor_property("FirstPassClearStrength", DEFAULT_FIRST_PASS_CLEAR_STRENGTH)
        trail_component.set_editor_property("RepeatPassClearStrengthStep", DEFAULT_REPEAT_PASS_CLEAR_STRENGTH_STEP)
        trail_component.set_editor_property("MaxAccumulatedClearStrength", DEFAULT_MAX_ACCUMULATED_CLEAR_STRENGTH)
        trail_component.set_editor_property("RightBermContinuationRatio", DEFAULT_RIGHT_BERM_CONTINUATION_RATIO)
        trail_component.set_editor_property("RepeatTierZOffsetCm", DEFAULT_REPEAT_TIER_Z_OFFSET_CM)

        if callable(getattr(trail_component, "post_edit_change", None)):
            trail_component.post_edit_change()
        if callable(getattr(trail_actor, "post_edit_change", None)):
            trail_actor.post_edit_change()
        if callable(getattr(trail_actor, "mark_package_dirty", None)):
            trail_actor.mark_package_dirty()

        trail_component = trail_actor.get_component_by_class(component_class) if component_class else trail_component

    result["trail_component_path"] = trail_component.get_path_name()
    result["trail_map_saved"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level()) if needs_save else False
    result["trail_component_values"] = {
        "StampSpacingCm": float(trail_component.get_editor_property("StampSpacingCm")),
        "bEnableRuntimeTrail": bool(trail_component.get_editor_property("bEnableRuntimeTrail")),
        "bEnableRvtVisualStamp": bool(trail_component.get_editor_property("bEnableRvtVisualStamp")),
        "bEnableRepeatClearingAccumulation": bool(
            trail_component.get_editor_property("bEnableRepeatClearingAccumulation")
        ),
        "bEnableRuntimeReceiverHeightControl": bool(
            trail_component.get_editor_property("bEnableRuntimeReceiverHeightControl")
        ),
        "bUseSourceHeightGate": bool(trail_component.get_editor_property("bUseSourceHeightGate")),
        "SourceActiveMaxRelativeZ": float(trail_component.get_editor_property("SourceActiveMaxRelativeZ")),
        "MinStampEngagementToWrite": float(trail_component.get_editor_property("MinStampEngagementToWrite")),
        "PlowLiftHeightForNoEffect": float(trail_component.get_editor_property("PlowLiftHeightForNoEffect")),
        "RuntimeHeightAmplitudeWhenActive": float(
            trail_component.get_editor_property("RuntimeHeightAmplitudeWhenActive")
        ),
        "RuntimeHeightAmplitudeWhenInactive": float(
            trail_component.get_editor_property("RuntimeHeightAmplitudeWhenInactive")
        ),
        "FirstPassClearStrength": float(
            trail_component.get_editor_property("FirstPassClearStrength")
        ),
        "RepeatPassClearStrengthStep": float(
            trail_component.get_editor_property("RepeatPassClearStrengthStep")
        ),
        "MaxAccumulatedClearStrength": float(
            trail_component.get_editor_property("MaxAccumulatedClearStrength")
        ),
        "RightBermContinuationRatio": float(
            trail_component.get_editor_property("RightBermContinuationRatio")
        ),
        "RepeatTierZOffsetCm": float(
            trail_component.get_editor_property("RepeatTierZOffsetCm")
        ),
        "SourceComponentOverride": (
            trail_component.get_editor_property("SourceComponentOverride").get_path_name()
            if trail_component.get_editor_property("SourceComponentOverride")
            else ""
        ),
    }


def update_plow_source_transform(result):
    world = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    if not world:
        raise RuntimeError(f"Could not load map: {MAP_PATH}")

    kamaz = _find_kamaz_actor()
    if not kamaz:
        raise RuntimeError("Kamaz actor not found on SnowTest_Level")

    plow_component = _find_scene_plow_component(kamaz)
    if not plow_component:
        raise RuntimeError("Plow scene component not found on Kamaz_SnowTest")
    visible_plow_component = _find_named_scene_component(kamaz, "PlowBrush")
    front_hitch_component = _find_named_scene_component(kamaz, "SM_FrontHitch")

    current_location = plow_component.get_editor_property("relative_location")
    target_location = unreal.Vector(
        float(current_location.x),
        float(current_location.y),
        float(DEFAULT_SNOWTEST_PLOW_SOURCE_RELATIVE_Z),
    )
    plow_component_changed = abs(float(current_location.z) - DEFAULT_SNOWTEST_PLOW_SOURCE_RELATIVE_Z) > 0.01

    if plow_component_changed:
        kamaz.modify()
        plow_component.modify()
        plow_component.set_editor_property("relative_location", target_location)
        if callable(getattr(plow_component, "post_edit_change", None)):
            plow_component.post_edit_change()
        if callable(getattr(kamaz, "post_edit_change", None)):
            kamaz.post_edit_change()
        if callable(getattr(kamaz, "mark_package_dirty", None)):
            kamaz.mark_package_dirty()
        unreal.EditorLoadingAndSavingUtils.save_current_level()

    result["snowtest_plow_source_relative_location"] = [
        float(plow_component.get_editor_property("relative_location").x),
        float(plow_component.get_editor_property("relative_location").y),
        float(plow_component.get_editor_property("relative_location").z),
    ]
    result["snowtest_plow_source_map_updated"] = plow_component_changed

    visible_plow_changed = False
    if visible_plow_component:
        try:
            visible_location = visible_plow_component.get_editor_property("relative_location")
            target_visible_location = unreal.Vector(
                float(visible_location.x),
                float(visible_location.y),
                float(DEFAULT_SNOWTEST_VISIBLE_PLOW_RELATIVE_Z),
            )
            visible_plow_changed = abs(float(visible_location.z) - DEFAULT_SNOWTEST_VISIBLE_PLOW_RELATIVE_Z) > 0.01
            if visible_plow_changed:
                kamaz.modify()
                visible_plow_component.modify()
                visible_plow_component.set_editor_property("relative_location", target_visible_location)
                if callable(getattr(visible_plow_component, "post_edit_change", None)):
                    visible_plow_component.post_edit_change()
                if callable(getattr(kamaz, "post_edit_change", None)):
                    kamaz.post_edit_change()
                if callable(getattr(kamaz, "mark_package_dirty", None)):
                    kamaz.mark_package_dirty()
                unreal.EditorLoadingAndSavingUtils.save_current_level()

            result["snowtest_visible_plow_relative_location"] = [
                float(visible_plow_component.get_editor_property("relative_location").x),
                float(visible_plow_component.get_editor_property("relative_location").y),
                float(visible_plow_component.get_editor_property("relative_location").z),
            ]
        except Exception as exc:
            result["snowtest_visible_plow_relative_location"] = []
            result["snowtest_visible_plow_update_error"] = str(exc)
    else:
        result["snowtest_visible_plow_relative_location"] = []
    result["snowtest_visible_plow_map_updated"] = visible_plow_changed

    front_hitch_changed = False
    if front_hitch_component:
        try:
            front_hitch_location = front_hitch_component.get_editor_property("relative_location")
            target_front_hitch_location = unreal.Vector(
                float(front_hitch_location.x),
                float(front_hitch_location.y),
                float(DEFAULT_SNOWTEST_FRONT_HITCH_RELATIVE_Z),
            )
            front_hitch_changed = abs(float(front_hitch_location.z) - DEFAULT_SNOWTEST_FRONT_HITCH_RELATIVE_Z) > 0.01
            if front_hitch_changed:
                kamaz.modify()
                front_hitch_component.modify()
                front_hitch_component.set_editor_property("relative_location", target_front_hitch_location)
                if callable(getattr(front_hitch_component, "post_edit_change", None)):
                    front_hitch_component.post_edit_change()
                if callable(getattr(kamaz, "post_edit_change", None)):
                    kamaz.post_edit_change()
                if callable(getattr(kamaz, "mark_package_dirty", None)):
                    kamaz.mark_package_dirty()
                unreal.EditorLoadingAndSavingUtils.save_current_level()

            result["snowtest_front_hitch_relative_location"] = [
                float(front_hitch_component.get_editor_property("relative_location").x),
                float(front_hitch_component.get_editor_property("relative_location").y),
                float(front_hitch_component.get_editor_property("relative_location").z),
            ]
        except Exception as exc:
            result["snowtest_front_hitch_relative_location"] = []
            result["snowtest_front_hitch_update_error"] = str(exc)
    else:
        result["snowtest_front_hitch_relative_location"] = []
    result["snowtest_front_hitch_map_updated"] = front_hitch_changed


def update_snowtest_bridge_surface(result):
    world = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    if not world:
        raise RuntimeError(f"Could not load map: {MAP_PATH}")

    bridge_actor = _find_actor_by_label(BRIDGE_ACTOR_LABEL)
    if not bridge_actor:
        raise RuntimeError("SnowHeightBridgeSurface_MVP not found on SnowTest_Level")

    bridge_component = bridge_actor.get_component_by_class(unreal.StaticMeshComponent)
    if not bridge_component:
        raise RuntimeError("SnowHeightBridgeSurface_MVP has no StaticMeshComponent")

    bridge_mesh = ASSET_LIB.load_asset(BRIDGE_MESH_PATH)
    if not bridge_mesh:
        raise RuntimeError(f"Missing bridge mesh: {BRIDGE_MESH_PATH}")

    bridge_material = ASSET_LIB.load_asset(BRIDGE_RECEIVER_MI_PATH)
    if not bridge_material:
        raise RuntimeError(f"Missing bridge receiver MI: {BRIDGE_RECEIVER_MI_PATH}")

    bounds_origin, bounds_extent = bridge_actor.get_actor_bounds(False)
    mesh_bounds = bridge_mesh.get_bounds()
    mesh_extent = mesh_bounds.box_extent
    mesh_extent_x = max(float(mesh_extent.x), 1.0)
    mesh_extent_y = max(float(mesh_extent.y), 1.0)
    mesh_extent_z = max(float(mesh_extent.z), 1.0)

    desired_scale = unreal.Vector(
        max(float(bounds_extent.x) / mesh_extent_x, 0.01),
        max(float(bounds_extent.y) / mesh_extent_y, 0.01),
        BRIDGE_TARGET_Z_SCALE,
    )

    current_location = bridge_actor.get_actor_location()
    desired_location = unreal.Vector(
        float(current_location.x),
        float(current_location.y),
        float(bounds_origin.z + bounds_extent.z - (mesh_extent_z * BRIDGE_TARGET_Z_SCALE)),
    )

    current_mesh = bridge_component.get_editor_property("static_mesh")
    current_scale = bridge_actor.get_actor_scale3d()
    current_material = bridge_component.get_material(0) if bridge_component.get_num_materials() > 0 else None
    current_collision_profile = ""
    try:
        get_collision_profile_name = getattr(bridge_component, "get_collision_profile_name", None)
        if callable(get_collision_profile_name):
            current_collision_profile = str(get_collision_profile_name())
    except Exception:
        current_collision_profile = ""

    needs_save = (
        current_mesh != bridge_mesh
        or abs(float(current_scale.x) - float(desired_scale.x)) > 0.01
        or abs(float(current_scale.y) - float(desired_scale.y)) > 0.01
        or abs(float(current_scale.z) - float(desired_scale.z)) > 0.001
        or abs(float(current_location.z) - float(desired_location.z)) > 0.01
        or current_material != bridge_material
        or current_collision_profile != BRIDGE_COLLISION_PROFILE_NAME
    )

    if needs_save:
        bridge_actor.modify()
        bridge_component.modify()
        bridge_component.set_editor_property("static_mesh", bridge_mesh)
        bridge_actor.set_actor_scale3d(desired_scale)
        bridge_actor.set_actor_location(desired_location, False, False)
        if bridge_component.get_num_materials() > 0:
            bridge_component.set_material(0, bridge_material)
        try:
            set_collision_profile_name = getattr(bridge_component, "set_collision_profile_name", None)
            if callable(set_collision_profile_name):
                set_collision_profile_name(unreal.Name(BRIDGE_COLLISION_PROFILE_NAME))
        except Exception:
            pass
        try:
            bridge_component.set_editor_property("collision_enabled", unreal.CollisionEnabled.QUERY_ONLY)
        except Exception:
            pass
        if callable(getattr(bridge_component, "post_edit_change", None)):
            bridge_component.post_edit_change()
        if callable(getattr(bridge_actor, "post_edit_change", None)):
            bridge_actor.post_edit_change()
        if callable(getattr(bridge_actor, "mark_package_dirty", None)):
            bridge_actor.mark_package_dirty()

    result["bridge_surface_path"] = bridge_actor.get_path_name()
    result["bridge_surface_values"] = {
        "mesh": bridge_component.get_editor_property("static_mesh").get_path_name()
        if bridge_component.get_editor_property("static_mesh")
        else "",
        "material_slot0": bridge_component.get_material(0).get_path_name()
        if bridge_component.get_num_materials() > 0 and bridge_component.get_material(0)
        else "",
        "actor_scale": [
            float(bridge_actor.get_actor_scale3d().x),
            float(bridge_actor.get_actor_scale3d().y),
            float(bridge_actor.get_actor_scale3d().z),
        ],
        "actor_location": [
            float(bridge_actor.get_actor_location().x),
            float(bridge_actor.get_actor_location().y),
            float(bridge_actor.get_actor_location().z),
        ],
        "collision_profile_name": (
            str(bridge_component.get_collision_profile_name())
            if callable(getattr(bridge_component, "get_collision_profile_name", None))
            else ""
        ),
    }
    result["bridge_surface_saved"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level()) if needs_save else False

    kamaz_blueprint = ASSET_LIB.load_asset(KAMAZ_BLUEPRINT_PATH)
    blueprint_plow_source = unreal.load_object(None, KAMAZ_BLUEPRINT_PLOW_SUBOBJECT_PATH)
    blueprint_visible_plow = unreal.load_object(None, KAMAZ_BLUEPRINT_VISIBLE_PLOW_SUBOBJECT_PATH)
    blueprint_front_hitch = unreal.load_object(None, KAMAZ_BLUEPRINT_FRONT_HITCH_SUBOBJECT_PATH)
    blueprint_changed = False
    if kamaz_blueprint and blueprint_plow_source:
        try:
            blueprint_location = blueprint_plow_source.get_editor_property("relative_location")
            target_blueprint_location = unreal.Vector(
                float(blueprint_location.x),
                float(blueprint_location.y),
                float(DEFAULT_KAMAZ_BP_PLOW_SOURCE_RELATIVE_Z),
            )
            blueprint_changed = abs(float(blueprint_location.z) - DEFAULT_KAMAZ_BP_PLOW_SOURCE_RELATIVE_Z) > 0.01
            if blueprint_changed:
                blueprint_plow_source.modify()
                blueprint_plow_source.set_editor_property("relative_location", target_blueprint_location)
                if callable(getattr(blueprint_plow_source, "post_edit_change", None)):
                    blueprint_plow_source.post_edit_change()
                if callable(getattr(kamaz_blueprint, "mark_package_dirty", None)):
                    kamaz_blueprint.mark_package_dirty()
                ASSET_LIB.save_loaded_asset(kamaz_blueprint, False)

            result["kamaz_bp_plow_source_relative_location"] = [
                float(blueprint_plow_source.get_editor_property("relative_location").x),
                float(blueprint_plow_source.get_editor_property("relative_location").y),
                float(blueprint_plow_source.get_editor_property("relative_location").z),
            ]
        except Exception as exc:
            result["kamaz_bp_plow_source_relative_location"] = []
            result["kamaz_bp_plow_source_update_error"] = str(exc)
    else:
        result["kamaz_bp_plow_source_relative_location"] = []

    result["kamaz_bp_plow_source_updated"] = blueprint_changed

    blueprint_visible_changed = False
    if kamaz_blueprint and blueprint_visible_plow:
        try:
            blueprint_visible_location = blueprint_visible_plow.get_editor_property("relative_location")
            target_blueprint_visible_location = unreal.Vector(
                float(blueprint_visible_location.x),
                float(blueprint_visible_location.y),
                float(DEFAULT_KAMAZ_BP_VISIBLE_PLOW_RELATIVE_Z),
            )
            blueprint_visible_changed = (
                abs(float(blueprint_visible_location.z) - DEFAULT_KAMAZ_BP_VISIBLE_PLOW_RELATIVE_Z) > 0.01
            )
            if blueprint_visible_changed:
                blueprint_visible_plow.modify()
                blueprint_visible_plow.set_editor_property("relative_location", target_blueprint_visible_location)
                if callable(getattr(blueprint_visible_plow, "post_edit_change", None)):
                    blueprint_visible_plow.post_edit_change()
                if callable(getattr(kamaz_blueprint, "mark_package_dirty", None)):
                    kamaz_blueprint.mark_package_dirty()
                ASSET_LIB.save_loaded_asset(kamaz_blueprint, False)

            result["kamaz_bp_visible_plow_relative_location"] = [
                float(blueprint_visible_plow.get_editor_property("relative_location").x),
                float(blueprint_visible_plow.get_editor_property("relative_location").y),
                float(blueprint_visible_plow.get_editor_property("relative_location").z),
            ]
        except Exception as exc:
            result["kamaz_bp_visible_plow_relative_location"] = []
            result["kamaz_bp_visible_plow_update_error"] = str(exc)
    else:
        result["kamaz_bp_visible_plow_relative_location"] = []
    result["kamaz_bp_visible_plow_updated"] = blueprint_visible_changed

    blueprint_front_hitch_changed = False
    if kamaz_blueprint and blueprint_front_hitch:
        try:
            blueprint_front_hitch_location = blueprint_front_hitch.get_editor_property("relative_location")
            target_blueprint_front_hitch_location = unreal.Vector(
                float(blueprint_front_hitch_location.x),
                float(blueprint_front_hitch_location.y),
                float(DEFAULT_KAMAZ_BP_FRONT_HITCH_RELATIVE_Z),
            )
            blueprint_front_hitch_changed = (
                abs(float(blueprint_front_hitch_location.z) - DEFAULT_KAMAZ_BP_FRONT_HITCH_RELATIVE_Z) > 0.01
            )
            if blueprint_front_hitch_changed:
                blueprint_front_hitch.modify()
                blueprint_front_hitch.set_editor_property("relative_location", target_blueprint_front_hitch_location)
                if callable(getattr(blueprint_front_hitch, "post_edit_change", None)):
                    blueprint_front_hitch.post_edit_change()
                if callable(getattr(kamaz_blueprint, "mark_package_dirty", None)):
                    kamaz_blueprint.mark_package_dirty()
                ASSET_LIB.save_loaded_asset(kamaz_blueprint, False)

            result["kamaz_bp_front_hitch_relative_location"] = [
                float(blueprint_front_hitch.get_editor_property("relative_location").x),
                float(blueprint_front_hitch.get_editor_property("relative_location").y),
                float(blueprint_front_hitch.get_editor_property("relative_location").z),
            ]
        except Exception as exc:
            result["kamaz_bp_front_hitch_relative_location"] = []
            result["kamaz_bp_front_hitch_update_error"] = str(exc)
    else:
        result["kamaz_bp_front_hitch_relative_location"] = []
    result["kamaz_bp_front_hitch_updated"] = blueprint_front_hitch_changed


def update_snowtest_road_materials(result):
    world = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    if not world:
        raise RuntimeError(f"Could not load map: {MAP_PATH}")

    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    loaded_materials = {}
    for label, material_path in ROAD_INSTANCE_MAP.items():
        material = ASSET_LIB.load_asset(material_path)
        if not material:
            raise RuntimeError(f"Failed to load road material: {material_path}")
        loaded_materials[label] = material

    updated_roads = []
    for actor in actors:
        label = actor.get_actor_label()
        if label not in loaded_materials:
            continue

        material = loaded_materials[label]
        actor.modify()
        actor.set_editor_property("snow_road_material", material)

        for component in list(actor.get_components_by_class(unreal.SplineMeshComponent) or []):
            try:
                component.modify()
                component.set_material(0, material)
            except Exception:
                pass

        refresh_attempts = _refresh_road_actor(actor)
        updated_roads.append(
            {
                "actor_label": label,
                "assigned_material": material.get_path_name(),
                "refresh_attempts": refresh_attempts,
            }
        )

    result["road_material_updates"] = updated_roads
    result["road_materials_saved"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level()) if updated_roads else False


def disable_snowtest_wheel_trace(result):
    world = unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)
    if not world:
        raise RuntimeError(f"Could not load map: {MAP_PATH}")

    kamaz = _find_kamaz_actor()
    if not kamaz:
        raise RuntimeError("Kamaz actor not found on SnowTest_Level")

    wheel_component = _find_actor_component_by_fragment(kamaz, "WheelSnowTrace")
    if not wheel_component:
        wheel_component = _find_actor_component_by_fragment(kamaz, "BP_WheelSnowTrace_Component")
    if not wheel_component:
        result["wheel_trace_component_path"] = ""
        result["wheel_trace_component_values"] = {}
        result["wheel_trace_component_saved"] = False
        return

    current_enabled = True
    current_rt = None
    try:
        current_enabled = bool(wheel_component.get_editor_property("bEnableSnowTraces"))
    except Exception:
        pass
    try:
        current_rt = wheel_component.get_editor_property("RenderTargetGlobal")
    except Exception:
        pass

    needs_save = current_enabled != DEFAULT_ENABLE_SNOW_WHEEL_TRACES or current_rt is not None
    if needs_save:
        kamaz.modify()
        wheel_component.modify()
        try:
            wheel_component.set_editor_property("bEnableSnowTraces", DEFAULT_ENABLE_SNOW_WHEEL_TRACES)
        except Exception:
            pass
        try:
            wheel_component.set_editor_property("RenderTargetGlobal", None)
        except Exception:
            pass
        if callable(getattr(wheel_component, "post_edit_change", None)):
            wheel_component.post_edit_change()
        if callable(getattr(kamaz, "post_edit_change", None)):
            kamaz.post_edit_change()
        if callable(getattr(kamaz, "mark_package_dirty", None)):
            kamaz.mark_package_dirty()

    result["wheel_trace_component_path"] = wheel_component.get_path_name()
    try:
        current_rt = wheel_component.get_editor_property("RenderTargetGlobal")
    except Exception:
        current_rt = None
    result["wheel_trace_component_values"] = {
        "bEnableSnowTraces": bool(wheel_component.get_editor_property("bEnableSnowTraces")),
        "RenderTargetGlobal": current_rt.get_path_name() if current_rt else "",
    }
    result["wheel_trace_component_saved"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level()) if needs_save else False


def update_landscape_instance(result):
    parent = ASSET_LIB.load_asset(RECEIVER_PARENT_PATH)
    if not parent:
        raise RuntimeError(f"Missing receiver parent: {RECEIVER_PARENT_PATH}")

    scalar_updates = {
        "HeightAmplitude": DEFAULT_RECEIVER_HEIGHT_AMPLITUDE,
        "HeightContrast": DEFAULT_RECEIVER_HEIGHT_CONTRAST,
        "ThinSnowMinVisualOpacity": DEFAULT_RECEIVER_THIN_SNOW_MIN_VISUAL_OPACITY,
        "EdgeDustingStrength": DEFAULT_RECEIVER_EDGE_DUSTING_STRENGTH,
        "RightBermRaise": DEFAULT_RIGHT_BERM_RAISE,
        "RightBermSharpness": DEFAULT_RIGHT_BERM_SHARPNESS,
        "RepeatAccumulationDepth": DEFAULT_REPEAT_ACCUMULATION_DEPTH,
        "VisualClearMaskStrength": DEFAULT_RECEIVER_VISUAL_CLEAR_MASK_STRENGTH,
        "DepthMaskBoost": DEFAULT_RECEIVER_DEPTH_MASK_BOOST,
        "DirtyBermTintStrength": DEFAULT_DIRTY_BERM_TINT_STRENGTH,
    }
    vector_updates = {
        "PressedSnowColor": DEFAULT_RECEIVER_PRESSED_SNOW_COLOR,
        "ThinSnowUnderColor": DEFAULT_RECEIVER_THIN_SNOW_UNDER_COLOR,
        "DirtyBermColor": DEFAULT_DIRTY_BERM_COLOR,
    }
    result["receiver_instance_scalar_values"] = {}
    result["receiver_instance_vector_values"] = {}
    saved_any = False

    for instance_path in ACTIVE_RECEIVER_MI_PATHS:
        instance = ASSET_LIB.load_asset(instance_path)
        if not instance:
            raise RuntimeError(f"Missing receiver MI: {instance_path}")

        _safe_set(instance, "parent", parent)
        for name, value in scalar_updates.items():
            MAT_LIB.set_material_instance_scalar_parameter_value(instance, name, value)
        for name, value in vector_updates.items():
            MAT_LIB.set_material_instance_vector_parameter_value(instance, name, value)

        MAT_LIB.update_material_instance(instance)
        saved = bool(ASSET_LIB.save_loaded_asset(instance, False))
        saved_any = saved_any or saved
        result["receiver_instance_scalar_values"][instance_path] = {
            name: float(MAT_LIB.get_material_instance_scalar_parameter_value(instance, name))
            for name in scalar_updates.keys()
        }
        result["receiver_instance_vector_values"][instance_path] = {
            name: [
                float(MAT_LIB.get_material_instance_vector_parameter_value(instance, name).r),
                float(MAT_LIB.get_material_instance_vector_parameter_value(instance, name).g),
                float(MAT_LIB.get_material_instance_vector_parameter_value(instance, name).b),
                float(MAT_LIB.get_material_instance_vector_parameter_value(instance, name).a),
            ]
            for name in vector_updates.keys()
        }

    result["landscape_mi_saved"] = saved_any
    result["landscape_mi_scalar_values"] = result["receiver_instance_scalar_values"].get(LANDSCAPE_MI_PATH, {})
    result["landscape_mi_vector_values"] = result["receiver_instance_vector_values"].get(LANDSCAPE_MI_PATH, {})


def main():
    result = {
        "mode": "apply_right_plow_berm",
        "writer_material": WRITER_MATERIAL_PATH,
        "receiver_parent": RECEIVER_PARENT_PATH,
        "landscape_mi": LANDSCAPE_MI_PATH,
        "receiver_rebuilt": False,
        "writer_saved": False,
        "landscape_mi_saved": False,
        "road_materials_saved": False,
        "bridge_surface_saved": False,
        "wheel_trace_component_saved": False,
        "trail_map_saved": False,
        "writer_num_expressions": 0,
        "writer_edge_feather_percent": 0.0,
        "landscape_mi_scalar_values": {},
        "road_material_updates": [],
        "bridge_surface_path": "",
        "bridge_surface_values": {},
        "wheel_trace_component_path": "",
        "wheel_trace_component_values": {},
        "trail_component_path": "",
        "trail_component_values": {},
        "writer_connect_basecolor": {},
        "writer_connect_specular": {},
        "writer_connect_roughness": {},
        "writer_connect_normal": {},
        "writer_connect_mask": {},
        "error": "",
    }

    try:
        runpy.run_path(REBUILD_RECEIVER_SCRIPT, run_name="__main__")
        result["receiver_rebuilt"] = True

        writer = ASSET_LIB.load_asset(WRITER_MATERIAL_PATH)
        if not writer:
            raise RuntimeError(f"Missing writer material: {WRITER_MATERIAL_PATH}")

        rebuild_writer_as_right_berm_signal(writer, result)
        update_landscape_instance(result)
        update_snowtest_bridge_surface(result)
        update_snowtest_road_materials(result)
        disable_snowtest_wheel_trace(result)
        update_snowtest_trail_settings(result)
        update_plow_source_transform(result)
    except Exception as exc:
        result["error"] = str(exc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
