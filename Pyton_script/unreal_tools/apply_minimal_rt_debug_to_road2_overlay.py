import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import prepare_road_snow_receiver_assets as prsra


OUTPUT_BASENAME = "apply_minimal_rt_debug_to_road2_overlay"
TARGET_ACTOR_LABEL = "SnowOverlay_Road2"
TARGET_MATERIAL_PATH = "/Game/CityPark/SnowSystem/Receivers/M_RoadOverlay_PureRTDebug"
SNOW_RT_PATH = "/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks"
CLEAR_MASK_AMPLIFY = 1024.0
DEBUG_EMISSIVE_MULTIPLIER = 120.0
DEBUG_RT_TINT = (0.0, 1.0, 0.0)

ASSET_LIB = unreal.EditorAssetLibrary
MATERIAL_LIB = unreal.MaterialEditingLibrary
ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def _log(message: str) -> None:
    unreal.log(f"[apply_minimal_rt_debug_to_road2_overlay] {message}")


def _saved_output_dir() -> str:
    return os.path.join(unreal.Paths.project_saved_dir(), "BlueprintAutomation")


def _write_json(path: str, payload) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    _log(f"Wrote file: {path}")
    return path


def _object_name(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_name()
    except Exception:
        return str(value)


def _object_path(value) -> str:
    if value is None:
        return ""
    try:
        return value.get_path_name()
    except Exception:
        return str(value)


def _load_asset(asset_path: str):
    asset = ASSET_LIB.load_asset(asset_path)
    if asset is None:
        raise RuntimeError(f"Could not load asset: {asset_path}")
    return asset


def _ensure_directory(path: str) -> None:
    if not ASSET_LIB.does_directory_exist(path):
        ASSET_LIB.make_directory(path)


def _delete_asset_if_exists(asset_path: str) -> bool:
    if not ASSET_LIB.does_asset_exist(asset_path):
        return False
    if not ASSET_LIB.delete_asset(asset_path):
        raise RuntimeError(f"Could not delete existing asset: {asset_path}")
    return True


def _recreate_material_asset(asset_path: str):
    package_path, asset_name = asset_path.rsplit("/", 1)
    _ensure_directory(package_path)
    _delete_asset_if_exists(asset_path)
    material = ASSET_TOOLS.create_asset(
        asset_name,
        package_path,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if material is None:
        raise RuntimeError(f"Failed to create material: {asset_path}")
    return material


def _new_expr(material, class_name: str, x: int, y: int):
    expr_class = getattr(unreal, class_name, None)
    if expr_class is None:
        raise RuntimeError(f"Missing Unreal Python class: {class_name}")
    expr = MATERIAL_LIB.create_material_expression(material, expr_class, x, y)
    if expr is None:
        raise RuntimeError(f"Could not create expression: {class_name}")
    return expr


def _connect(source_expr, target_expr, input_name: str, source_output_name: str = "") -> None:
    MATERIAL_LIB.connect_material_expressions(source_expr, source_output_name, target_expr, input_name)


def _new_scalar_param(material, x: int, y: int, name: str, value: float):
    expr = _new_expr(material, "MaterialExpressionScalarParameter", x, y)
    expr.set_editor_property("parameter_name", name)
    expr.set_editor_property("default_value", float(value))
    return expr


def _new_constant(material, x: int, y: int, value: float):
    expr = _new_expr(material, "MaterialExpressionConstant", x, y)
    expr.set_editor_property("r", float(value))
    return expr


def _new_color(material, x: int, y: int, rgb: tuple[float, float, float]):
    expr = _new_expr(material, "MaterialExpressionConstant3Vector", x, y)
    expr.set_editor_property("constant", unreal.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))
    return expr


def _new_texture_param(material, x: int, y: int, name: str, texture_asset):
    expr = _new_expr(material, "MaterialExpressionTextureSampleParameter2D", x, y)
    expr.set_editor_property("parameter_name", name)
    expr.set_editor_property("texture", texture_asset)
    return expr


def _find_actor_by_label(label: str):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        try:
            if actor.get_actor_label() == label:
                return actor
        except Exception:
            continue
    return None


def _build_minimal_rt_debug_material() -> dict:
    material = _recreate_material_asset(TARGET_MATERIAL_PATH)
    snow_rt = _load_asset(SNOW_RT_PATH)

    try:
        material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    except Exception:
        pass

    texcoord = _new_expr(material, "MaterialExpressionTextureCoordinate", -900, 0)
    rt_sample = _new_texture_param(material, -640, 0, "SnowRT_PureDebugUV", snow_rt)
    _connect(texcoord, rt_sample, "Coordinates")

    axis4_y = _new_expr(material, "MaterialExpressionConstant4Vector", -880, 220)
    axis4_y.set_editor_property("constant", unreal.LinearColor(0.0, 1.0, 0.0, 0.0))

    rt_g = _new_expr(material, "MaterialExpressionDotProduct", -360, 0)
    _connect(rt_sample, rt_g, "A")
    _connect(axis4_y, rt_g, "B")

    amplify = _new_scalar_param(material, -620, 260, "ClearMaskAmplify", CLEAR_MASK_AMPLIFY)
    rt_scaled = _new_expr(material, "MaterialExpressionMultiply", -120, 0)
    _connect(rt_g, rt_scaled, "A")
    _connect(amplify, rt_scaled, "B")

    zero = _new_constant(material, 120, -120, 0.0)
    one = _new_constant(material, 120, 120, 1.0)

    rt_non_negative = _new_expr(material, "MaterialExpressionMax", 120, 0)
    _connect(rt_scaled, rt_non_negative, "A")
    _connect(zero, rt_non_negative, "B")

    rt_clamped = _new_expr(material, "MaterialExpressionMin", 360, 0)
    _connect(rt_non_negative, rt_clamped, "A")
    _connect(one, rt_clamped, "B")

    tint = _new_color(material, 360, 240, DEBUG_RT_TINT)
    base_color = _new_expr(material, "MaterialExpressionMultiply", 600, 120)
    _connect(rt_clamped, base_color, "A")
    _connect(tint, base_color, "B")

    emissive_multiplier = _new_scalar_param(material, 600, 360, "DebugEmissiveMultiplier", DEBUG_EMISSIVE_MULTIPLIER)
    emissive = _new_expr(material, "MaterialExpressionMultiply", 860, 220)
    _connect(base_color, emissive, "A")
    _connect(emissive_multiplier, emissive, "B")

    MATERIAL_LIB.connect_material_property(base_color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MATERIAL_LIB.connect_material_property(emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MATERIAL_LIB.recompile_material(material)
    MATERIAL_LIB.layout_material_expressions(material)

    saved = bool(ASSET_LIB.save_loaded_asset(material, False))
    return {
        "material_path": _object_path(material),
        "snow_rt_path": _object_path(snow_rt),
        "saved": saved,
        "parameters": {
            "ClearMaskAmplify": CLEAR_MASK_AMPLIFY,
            "DebugEmissiveMultiplier": DEBUG_EMISSIVE_MULTIPLIER,
            "DebugTint": list(DEBUG_RT_TINT),
        },
    }


def _apply_to_overlay(material_asset_path: str) -> dict:
    actor = _find_actor_by_label(TARGET_ACTOR_LABEL)
    if actor is None:
        raise RuntimeError(f"Could not find actor with label '{TARGET_ACTOR_LABEL}'.")

    apply_result = prsra.apply_material_to_actor_slot0(_object_path(actor), material_asset_path)
    save_result = {"saved_current_level": False, "error": ""}
    try:
        save_result["saved_current_level"] = bool(unreal.EditorLoadingAndSavingUtils.save_current_level())
    except Exception as exc:
        save_result["error"] = str(exc)

    return {
        "target_actor_name": _object_name(actor),
        "target_actor_path": _object_path(actor),
        "apply_result": apply_result,
        "save_result": save_result,
    }


def run(output_dir: str | None = None) -> dict:
    output_dir = output_dir or _saved_output_dir()
    material_result = _build_minimal_rt_debug_material()
    apply_result = _apply_to_overlay(TARGET_MATERIAL_PATH)

    payload = {
        "success": bool(material_result.get("saved", False) and apply_result["apply_result"].get("num_components_updated", 0) > 0),
        "summary": "Applied minimal pure TexCoord RT debug material to SnowOverlay_Road2.",
        "material_result": material_result,
        "overlay_result": apply_result,
        "notes": [
            "This creates a brand-new minimal material that samples RT_SnowTest_WheelTracks via TexCoord only.",
            "It does not use road texture, snow texture, world mapping, or curb masks.",
            "If this still stays dark in PIE, the problem is no longer the receiver material graph.",
        ],
    }

    output_path = os.path.join(output_dir, f"{OUTPUT_BASENAME}.json")
    _write_json(output_path, payload)
    payload["output_path"] = output_path
    return payload


def print_summary(output_dir: str | None = None):
    payload = run(output_dir)
    _log(payload["summary"])
    _log(f"summary_path={payload['output_path']}")
    return {
        "success": payload.get("success", False),
        "summary": payload.get("summary", ""),
        "output_path": payload.get("output_path", ""),
    }


if __name__ == "__main__":
    print_summary()
