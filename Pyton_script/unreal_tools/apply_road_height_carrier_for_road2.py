import os
import sys


TOOLS_DIR = os.path.dirname(__file__)
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)

import road_height_carrier_helper as helper
from road2_writer_policy import ensure_road2_writer_allowed


ROAD2_WRITER_POLICY = ensure_road2_writer_allowed(__file__)


CONFIG = {
    "output_basename": "apply_road_height_carrier_for_road2",
    "target_map_path": "/Game/Maps/MoscowEA5",
    "target_actor_path": "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_208",
    "target_actor_label": "Road2",
    "allow_selection_fallback": True,
    "carrier_actor_label": "SnowHeightBridgeSurface_Road2",
    "carrier_mesh_mode": "target_mesh",
    "recreate_existing_carrier": True,
    "legacy_carrier_labels": [
        "SnowRoadCarrier_Road2",
    ],
    "cleanup_actor_labels": [
        "SnowOverlay_Road2",
    ],
    "target_mi_package": "/Game/CityPark/SnowSystem/Receivers",
    "target_mi_path": "/Game/CityPark/SnowSystem/Receivers/MI_SnowRoadCarrier_Road2",
    "source_mi_path": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_Tile8",
    "rvt_path": "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP",
    "force_rebuild_target_mi_from_source": False,
    "reuse_existing_material_if_matching": False,
    "apply_material_parameter_overrides": True,
    "carrier_length_override_cm": None,
    "carrier_width_override_cm": None,
    "carrier_z_offset_cm": 1.0,
    "hide_target_road_in_game": False,
    "receiver_priority": 110,
    "receiver_set_tag": "RoadSnowCarrierHeight",
    "ensure_runtime_trail_bridge_actor": True,
    "runtime_trail_actor_label": "SnowRuntimeTrailBridgeActor",
    "runtime_trail_target_rvt_path": "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP",
    "ensure_runtime_virtual_texture_volume": True,
    "runtime_virtual_texture_volume_label": "SnowRuntimeVirtualTextureVolume_Road2",
    "runtime_virtual_texture_volume_target_rvt_path": "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP",
    "runtime_virtual_texture_volume_include_target_actor": False,
    "runtime_virtual_texture_volume_margin_xy_cm": 300.0,
    "runtime_virtual_texture_volume_margin_z_cm": 250.0,
    "runtime_virtual_texture_volume_min_xy_extent_cm": 512.0,
    "runtime_virtual_texture_volume_min_z_extent_cm": 128.0,
    "runtime_trail_stamp_spacing_cm": 5.0,
    "runtime_trail_use_source_height_gate": False,
    "runtime_trail_persistent_plow_length_cm": 50.0,
    "runtime_trail_persistent_plow_width_cm": 350.0,
    "runtime_trail_source_active_max_relative_z": -0.5,
    "runtime_trail_runtime_height_amplitude_when_active": -50.0,
    "runtime_trail_runtime_height_amplitude_when_inactive": 0.0,
    "runtime_trail_mark_persistent_snow_state": True,
    "runtime_trail_enable_rvt_visual_stamp": True,
    "runtime_trail_enable_runtime_receiver_height_control": True,
    "runtime_trail_clear_source_component_override": True,
    "scalar_defaults": {
        "BaselineSnowCoverage": 1.0,
        "BaselineHeightCm": 50.0,
        "SnowTexUVScale": 10.0,
        "SnowDetailInfluence": 0.85,
        "HeightAmplitude": 0.0,
        "HeightContrast": 1.0,
        "SnowRoughness": 0.9,
        "PressedRoughness": 0.45,
        "VisualClearMaskStrength": 1.0,
        "DepthMaskBoost": 1.0,
        "RightBermRaise": 0.0,
        "RightBermSharpness": 1.0,
        "RepeatAccumulationDepth": 0.0,
        "ThinSnowMinVisualOpacity": 1.0,
        "RoadSnowVisualWhitenStrength": 0.0,
        "RoadSnowRecoveredBehavior": 1.0,
        "BaselineSnowEmissiveStrength": 0.35,
    },
    "vector_defaults": {
        "SnowColor": (0.98, 0.99, 1.0, 1.0),
        "PressedSnowColor": (0.36, 0.47, 0.62, 1.0),
        "ThinSnowUnderColor": (0.52, 0.52, 0.54, 1.0),
        "RoadSnowVisualColor": (0.985, 0.99, 1.0, 1.0),
        "RoadSnowRecoveredPressedColor": (0.52, 0.52, 0.54, 1.0),
    },
}


def run(output_dir=None):
    return helper.run(CONFIG, output_dir=output_dir)


def print_summary(output_dir=None):
    payload = run(output_dir)
    print(payload["summary"])
    print("summary_path={0}".format(payload["output_path"]))
    return {
        "success": payload.get("success", False),
        "summary": payload.get("summary", ""),
        "output_path": payload.get("output_path", ""),
    }


if __name__ == "__main__":
    print_summary()
