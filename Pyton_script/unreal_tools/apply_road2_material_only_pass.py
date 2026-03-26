import json
import os
import sys

import unreal


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

from road2_writer_policy import ensure_road2_writer_allowed


ROAD2_WRITER_POLICY = ensure_road2_writer_allowed(__file__)


MAP_PATH = "/Game/Maps/MoscowEA5"
ROAD_LABEL = "Road2"
CARRIER_LABEL = "SnowHeightBridgeSurface_Road2"
MI_PATH = "/Game/CityPark/SnowSystem/Receivers/MI_SnowRoadCarrier_Road2"
PARENT_PATH = "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP"
OUTPUT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "BlueprintAutomation",
    "apply_road2_material_only_pass.json",
)


MAT_LIB = unreal.MaterialEditingLibrary
ASSET_LIB = unreal.EditorAssetLibrary


SCALAR_VALUES = {
    "BaselineSnowCoverage": 1.0,
    "BaselineHeightCm": 50.0,
    "HeightAmplitude": 0.0,
    "HeightContrast": 1.0,
    "SnowTexUVScale": 10.0,
    "SnowDetailInfluence": 0.0,
    "VisualClearMaskStrength": 1.0,
    "DepthMaskBoost": 1.0,
    "ThinSnowMinVisualOpacity": 0.88,
    "SnowRoughness": 0.72,
    "PressedRoughness": 0.46,
    "RoadSnowVisualWhitenStrength": 1.0,
    "RoadSnowRecoveredBehavior": 1.0,
    "BaselineSnowEmissiveStrength": 0.0,
    "RevealOpacityThreshold": 0.90,
    "RevealOpacityPower": 2.0,
    # Road2 follows the project's RVT writer convention: stamped clear footprints write Mask=1.
    # Keep receiver polarity non-inverted so only stamped areas clear the carrier.
    "InvertClearMask": 0.0,
}

VECTOR_VALUES = {
    "SnowColor": (1.45, 1.5, 1.6, 1.0),
    "RoadSnowVisualColor": (1.75, 1.82, 1.95, 1.0),
    "PressedSnowColor": (0.52, 0.52, 0.54, 1.0),
    "RoadSnowRecoveredPressedColor": (0.52, 0.52, 0.54, 1.0),
    "ThinSnowUnderColor": (0.52, 0.52, 0.54, 1.0),
}


def _obj_path(obj):
    if obj is None:
        return ""
    try:
        return obj.get_path_name()
    except Exception:
        return str(obj)


def _find_actor_by_label(label):
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in list(actor_subsystem.get_all_level_actors() or []):
        try:
            if actor.get_actor_label() == label:
                return actor
        except Exception:
            continue
    return None


def _get_scalar(mi, name):
    try:
        return float(MAT_LIB.get_material_instance_scalar_parameter_value(mi, name))
    except Exception:
        return None


def _set_scalar(mi, name, value):
    MAT_LIB.set_material_instance_scalar_parameter_value(mi, name, float(value))


def _snapshot(mi):
    snap = {name: _get_scalar(mi, name) for name in SCALAR_VALUES.keys()}
    for name in VECTOR_VALUES.keys():
        try:
            color = MAT_LIB.get_material_instance_vector_parameter_value(mi, name)
            snap[name] = [float(color.r), float(color.g), float(color.b), float(color.a)]
        except Exception:
            snap[name] = None
    return snap


def _write_json(payload):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def main():
    result = {
        "success": False,
        "map": MAP_PATH,
        "road_actor_path": "",
        "carrier_actor_path": "",
        "mi_path": MI_PATH,
        "parent_path": PARENT_PATH,
        "before": {},
        "after": {},
        "saved_assets": [],
        "error": "",
    }

    try:
        unreal.EditorLoadingAndSavingUtils.load_map(MAP_PATH)

        road_actor = _find_actor_by_label(ROAD_LABEL)
        carrier_actor = _find_actor_by_label(CARRIER_LABEL)
        mi = ASSET_LIB.load_asset(MI_PATH)
        parent = ASSET_LIB.load_asset(PARENT_PATH)

        if road_actor is None:
            raise RuntimeError(f"Road actor not found: {ROAD_LABEL}")
        if carrier_actor is None:
            raise RuntimeError(f"Carrier actor not found: {CARRIER_LABEL}")
        if mi is None:
            raise RuntimeError(f"MI not found: {MI_PATH}")
        if parent is None:
            raise RuntimeError(f"Parent not found: {PARENT_PATH}")

        result["road_actor_path"] = _obj_path(road_actor)
        result["carrier_actor_path"] = _obj_path(carrier_actor)

        mi.set_editor_property("parent", parent)
        result["before"] = _snapshot(mi)

        for name, value in SCALAR_VALUES.items():
            _set_scalar(mi, name, value)
        for name, rgba in VECTOR_VALUES.items():
            color = unreal.LinearColor(float(rgba[0]), float(rgba[1]), float(rgba[2]), float(rgba[3]))
            MAT_LIB.set_material_instance_vector_parameter_value(mi, name, color)

        MAT_LIB.update_material_instance(mi)
        result["after"] = _snapshot(mi)

        if not ASSET_LIB.save_loaded_asset(mi, False):
            raise RuntimeError("Failed to save MI")
        if not unreal.EditorLoadingAndSavingUtils.save_current_level():
            raise RuntimeError("Failed to save current level")

        result["saved_assets"] = [MI_PATH, MAP_PATH]
        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)

    _write_json(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
