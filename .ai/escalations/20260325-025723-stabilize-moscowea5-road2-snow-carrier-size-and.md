# Senior Escalation Packet

- Generated: 2026-03-25 02:57:23 +03:00
- Project root: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner
- Branch: snow-source-truth-snapshot

## Goal

Stabilize MoscowEA5 Road2 snow carrier size and restore runtime reaction through SnowRuntimeTrailBridgeActor

## Hypothesis

Road2 was broken by two separate issues: the saved carrier was still a giant plane because reusing the existing actor did not persist transform reliably, and the map had no SnowRuntimeTrailBridgeActor, so the RoadSnowCarrierHeight receiver had no runtime driver in PIE. Respawning the carrier and placing/configuring a trail bridge actor should make the setup persist and react.

## Files to touch

- Pyton_script/unreal_tools/road_height_carrier_helper.py
- Pyton_script/unreal_tools/apply_road_height_carrier_for_road2.py
- Pyton_script/unreal_tools/inspect_moscowea5_road2_carrier_runtime.py
- Content/Maps/MoscowEA5.umap
- Content/CityPark/SnowSystem/Receivers/MI_SnowRoadCarrier_Road2.uasset
- .gitignore
- Config/DefaultEngine.ini
- Config/DefaultGame.ini
- Content/BPs/BP_KamazGameMode.uasset
- Content/CAA_SnowV2/SnowV2P1/MaterialsP1/M_SnowV2P1_Master.uasset
- Content/CityPark/Kamaz/model/KamazBP.uasset
- Content/CityPark/SnowSystem/BP_PlowBrush_Component.uasset
- Content/CityPark/SnowSystem/BP_WheelSnowTrace_Component.uasset
- Content/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush.uasset
- Content/CityPark/SnowSystem/BrushMaterials/M_Snow_WheelBrush.uasset
- Content/CityPark/SnowSystem/MPC_SnowSystem.uasset
- Content/CityPark/SnowSystem/RT_SnowTest_WheelTracks.uasset
- Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_MVP.uasset
- Content/CityPark/SnowSystem/RVT_MVP/M_RVT_DebugWriter_MVP.uasset
- Content/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_MVP.uasset
- Content/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP.uasset
- Content/CityPark/SnowSystem/SnowTest_Level.umap
- Content/Meshes/Roads/Road.uasset
- Content/VehicleTemplate/Blueprints/BP_VehicleAdvPawnBase.uasset
- Content/VehicleTemplate/Blueprints/SportsCar/BP_VehicleAdvSportsCar.uasset
- Kamaz_Cleaner.uproject
- Plugins/BlueprintAutomationEditor/Source/BlueprintAutomationEditor/Private/BlueprintAutomationPythonBridge.cpp
- Plugins/BlueprintAutomationEditor/Source/BlueprintAutomationEditor/Public/BlueprintAutomationPythonBridge.h
- Pyton_script/unreal_tools/__pycache__/probe_active_pie_snow_rt.cpython-311.pyc
- Pyton_script/unreal_tools/fix_vehicle_template_input_nodes.py

## Ordered steps

1. Reproduce the issue and confirm current behavior.
2. Inspect only the listed files and map the minimum safe change.
3. Apply the smallest patch that validates the hypothesis.
4. Validate with project wrappers (build_editor.ps1, read_last_logs.ps1, optional run_smoke.ps1).
5. If validation fails, revise hypothesis and iterate once with a narrow delta.

## Invariants / Do-not-break rules

- Keep local-first routing as default.
- Do not break existing Unreal build loop or project wrapper workflow.
- Do not treat Live Coding as complete validation for reflection/header/module changes.
- Keep edits small, reviewable, and scoped to the task.

## Validation

- Run Tools/AI/build_editor.ps1 for compile-pass.
- Run Tools/AI/read_last_logs.ps1 to inspect editor/build output.
- Run Tools/AI/run_smoke.ps1 (and -RunHeadless when needed).

## Rollback notes

- Revert only files listed in this packet if regression appears.
- Prefer rolling back the smallest failing patch, not the whole branch.

## Current diff summary

### git status --short

~~~text
 M .gitignore
 M Config/DefaultEngine.ini
 M Config/DefaultGame.ini
 M Content/BPs/BP_KamazGameMode.uasset
 M Content/CAA_SnowV2/SnowV2P1/MaterialsP1/M_SnowV2P1_Master.uasset
 M Content/CityPark/Kamaz/model/KamazBP.uasset
 M Content/CityPark/SnowSystem/BP_PlowBrush_Component.uasset
 M Content/CityPark/SnowSystem/BP_WheelSnowTrace_Component.uasset
 M Content/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush.uasset
 M Content/CityPark/SnowSystem/BrushMaterials/M_Snow_WheelBrush.uasset
 M Content/CityPark/SnowSystem/MPC_SnowSystem.uasset
 M Content/CityPark/SnowSystem/RT_SnowTest_WheelTracks.uasset
 M Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_MVP.uasset
 M Content/CityPark/SnowSystem/RVT_MVP/M_RVT_DebugWriter_MVP.uasset
 M Content/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_MVP.uasset
 M Content/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP.uasset
 M Content/CityPark/SnowSystem/SnowTest_Level.umap
 M Content/Maps/MoscowEA5.umap
 M Content/Meshes/Roads/Road.uasset
 M Content/VehicleTemplate/Blueprints/BP_VehicleAdvPawnBase.uasset
 M Content/VehicleTemplate/Blueprints/SportsCar/BP_VehicleAdvSportsCar.uasset
 M Kamaz_Cleaner.uproject
 M Plugins/BlueprintAutomationEditor/Source/BlueprintAutomationEditor/Private/BlueprintAutomationPythonBridge.cpp
 M Plugins/BlueprintAutomationEditor/Source/BlueprintAutomationEditor/Public/BlueprintAutomationPythonBridge.h
 M Pyton_script/unreal_tools/__pycache__/probe_active_pie_snow_rt.cpython-311.pyc
 M Pyton_script/unreal_tools/fix_vehicle_template_input_nodes.py
 M Pyton_script/unreal_tools/probe_active_pie_snow_rt.py
 M Pyton_script/unreal_tools/trace_m_snow_plow_brush_graph.py
 M Source/Kamaz_Cleaner/Kamaz_Cleaner.Build.cs
?? AGENTS.md
?? Content/Automation/
?? Content/BPs/BP_KamazGameMode_HandlingAudit.uasset
?? Content/CityPark/Kamaz/model/Front_wheels_HandlingAudit.uasset
?? Content/CityPark/Kamaz/model/KamazBP_HandlingAudit.uasset
?? Content/CityPark/Kamaz/model/Rear_wheels_HandlingAudit.uasset
?? Content/CityPark/SnowSystem/BrushMaterials/MI_Snow_PlowBrush_BoxSafe_350x50x100.uasset
?? Content/CityPark/SnowSystem/BrushMaterials/MI_Snow_PlowBrush_BoxSafe_DebugHuge.uasset
?? Content/CityPark/SnowSystem/BrushMaterials/M_RT_FullscreenGreen_Test.uasset
?? Content/CityPark/SnowSystem/BrushMaterials/M_RVT_SnowWriter_Test.uasset
?? Content/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush_BoxSafe.uasset
?? Content/CityPark/SnowSystem/M_RVT_SnowWriter_Test.uasset
?? Content/CityPark/SnowSystem/M_RVT_SnowWriter_Test1.uasset
?? Content/CityPark/SnowSystem/M_RVT_SnowWriter_Test2.uasset
?? Content/CityPark/SnowSystem/M_SnowTestMVP_Landscape1.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/LI_SnowPaint.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_Landscape.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_LandscapeRuntimeFix.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_Landscape_SoftSeam.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_RoadEdgeBlend.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P2_2K.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P3_2K.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P4_2K.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P5_2K.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_LandscapePaint.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_Tile4.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_Tile8.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_Tile8_RoadEdgeBlend.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_V1_Original.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_V3_Narrow.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_V3_Narrow_Tile4.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_V3_Narrow_Tile4_RoadEdgeBlend.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP_LandscapePaint.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP_LandscapeRuntimeFix.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP_RoadEdgeBlend.uasset
?? Content/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP_WheelRT.uasset
?? Content/CityPark/SnowSystem/Receivers/MI_SnowRoadCarrier_Road2.uasset
?? Content/CityPark/SnowSystem/SnowLevel.umap
?? Content/CityPark/SnowSystem/SnowRuntime_V1/
?? Content/Maps/SnowTest_Level.umap
?? Content/Ndi/
?? Content/VehicleTemplate/Input/Actions/
?? Docs/
?? Plugins/LudusAI/
?? Pyton_script/Snow_Mat.py.txt
?? Pyton_script/unreal_tools/_tmp_actor_external_probe.py
?? Pyton_script/unreal_tools/_tmp_actor_package_probe.py
?? Pyton_script/unreal_tools/_tmp_check_engine_mesh_candidates.py
?? Pyton_script/unreal_tools/_tmp_check_snowtestground_wpo_viability.py
?? Pyton_script/unreal_tools/_tmp_find_high_density_flat_mesh.py
?? Pyton_script/unreal_tools/_tmp_inspect_staticmesh_api.py
?? Pyton_script/unreal_tools/_tmp_list_actor_methods.py
?? Pyton_script/unreal_tools/_tmp_list_level_mesh_density.py
?? Pyton_script/unreal_tools/_tmp_moscow_height_receivers_scan.py
?? Pyton_script/unreal_tools/_tmp_moscow_runtime_graph_probe.py
?? Pyton_script/unreal_tools/_tmp_moscow_runtime_owner_probe.py
?? Pyton_script/unreal_tools/_tmp_phase6_actor_scan.py
?? Pyton_script/unreal_tools/_tmp_phase6_kamaz_components.py
?? Pyton_script/unreal_tools/apply_landscape_runtime_cleanup_pass.py
?? Pyton_script/unreal_tools/apply_repeat_clearing_accumulation.py
?? Pyton_script/unreal_tools/apply_right_plow_berm.py
?? Pyton_script/unreal_tools/apply_road_edge_blend_inplace.py
?? Pyton_script/unreal_tools/apply_road_edge_blend_material.py
?? Pyton_script/unreal_tools/apply_road_height_carrier_for_road2.py
?? Pyton_script/unreal_tools/apply_snowtest_landscape_soft_seam.py
?? Pyton_script/unreal_tools/apply_snowtest_wheel_rt_chain.py
?? Pyton_script/unreal_tools/apply_snowtest_wheel_rt_overlay_inplace.py
?? Pyton_script/unreal_tools/apply_soft_rvt_stamp_edges.py
?? Pyton_script/unreal_tools/apply_visible_snow_to_road_only_carrier.py
?? Pyton_script/unreal_tools/attach_kamaz_startup_hold_component.py
?? Pyton_script/unreal_tools/build_snow_runtime_v1_phase1.py
?? Pyton_script/unreal_tools/build_snow_runtime_v1_phase2_wheel.py
?? Pyton_script/unreal_tools/clone_kamaz_handling_audit.py
?? Pyton_script/unreal_tools/ensure_snowtest_wheel_trace_component.py
?? Pyton_script/unreal_tools/fix_kamaz_beginplay_handbrake_and_nanite.py
?? Pyton_script/unreal_tools/fix_kamaz_handbrake_completed_sink.py
?? Pyton_script/unreal_tools/fix_kamaz_handbrake_space_release.py
?? Pyton_script/unreal_tools/fix_kamaz_respawn_handbrake_flow.py
?? Pyton_script/unreal_tools/fix_kamaz_startbrake_release_path_and_nanite.py
?? Pyton_script/unreal_tools/fix_snowtest_landscape_runtime_receiver.py
?? Pyton_script/unreal_tools/fix_snowtest_use_handlingaudit_gamemode.py
?? Pyton_script/unreal_tools/increase_rt_snowtest_wheeltracks_resolution.py
?? Pyton_script/unreal_tools/increase_rvt_snowmask_mvp_resolution.py
?? Pyton_script/unreal_tools/inspect_current_snowtest_receivers.py
?? Pyton_script/unreal_tools/inspect_kamaz_runtime_owner_chain.py
?? Pyton_script/unreal_tools/inspect_material_instance_params.py
?? Pyton_script/unreal_tools/inspect_material_python_api.py
?? Pyton_script/unreal_tools/inspect_material_root_connections.py
?? Pyton_script/unreal_tools/inspect_moscowea5_road2_carrier_runtime.py
?? Pyton_script/unreal_tools/inspect_mpc_snow_bounds_asset.py
?? Pyton_script/unreal_tools/inspect_rt_factory_api.py
?? Pyton_script/unreal_tools/inspect_rt_python_api.py
?? Pyton_script/unreal_tools/inspect_rvt_snowmask_mvp.py
?? Pyton_script/unreal_tools/inspect_rvt_volume_density.py
?? Pyton_script/unreal_tools/inspect_snow_road_materials.py
?? Pyton_script/unreal_tools/inspect_snowtest_plow_sources.py
?? Pyton_script/unreal_tools/persist_snowtest_rvt_bounds_to_mpc_asset.py
?? Pyton_script/unreal_tools/persist_snowtest_wheel_rt_bounds_to_mpc_asset.py
?? Pyton_script/unreal_tools/phase3_real_height_mvp.py
?? Pyton_script/unreal_tools/phase4_quality_refinement_mvp.py
?? Pyton_script/unreal_tools/phase5_production_bridge_mvp.py
?? Pyton_script/unreal_tools/phase6_runtime_trail_binary_probe.py
?? Pyton_script/unreal_tools/phase6_runtime_trail_mvp.py
?? Pyton_script/unreal_tools/probe_snowtest_plow_height_engagement.py
?? Pyton_script/unreal_tools/probe_snowtest_plow_surface_hits.py
?? Pyton_script/unreal_tools/probe_snowtest_runtime_height_receiver.py
?? Pyton_script/unreal_tools/probe_snowtest_wheel_rt_writer.py
?? Pyton_script/unreal_tools/raise_kamaz_plow_by_50cm.py
?? Pyton_script/unreal_tools/rebuild_m_snow_wheel_brush.py
?? Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_berm.py
?? Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_clean.py
?? Pyton_script/unreal_tools/recreate_rt_snowtest_wheeltracks_4k.py
?? Pyton_script/unreal_tools/reparent_landscape_runtimefix_mi_to_clean_parent.py
?? Pyton_script/unreal_tools/restore_snowtest_road_base_materials.py
?? Pyton_script/unreal_tools/road_height_carrier_helper.py
?? Pyton_script/unreal_tools/spawn_road_only_carrier_for_road2.py
?? Pyton_script/unreal_tools/tmp_apply_landscape_runtime_bridge_fix.py
?? Pyton_script/unreal_tools/tmp_dump_blueprint_editor_library_methods.py
?? Pyton_script/unreal_tools/tmp_dump_vehicleadv_eventgraph.py
?? Pyton_script/unreal_tools/tmp_fix_vehicle_template_value_types.py
?? Pyton_script/unreal_tools/tmp_input_action_types.py
?? Pyton_script/unreal_tools/tmp_inspect_kamaz_respawn_state.py
?? Pyton_script/unreal_tools/tmp_inspect_landscape_paint_variants.py
?? Pyton_script/unreal_tools/tmp_inspect_landscape_runtime_bridge.py
?? Pyton_script/unreal_tools/tmp_inspect_landscape_soft_seam_mi_params.py
?? Pyton_script/unreal_tools/tmp_inspect_snowtest_landscape_mi_params.py
?? Pyton_script/unreal_tools/tmp_inspect_snowtest_landscape_soft_seam_values.py
?? Pyton_script/unreal_tools/tmp_kamaz_beginplay_chain_audit.py
?? Pyton_script/unreal_tools/tmp_kamaz_beginplay_exec_trace.py
?? Pyton_script/unreal_tools/tmp_kamaz_brake_nodes_detail.py
?? Pyton_script/unreal_tools/tmp_kamaz_handbrake_graph_nodes.py
?? Pyton_script/unreal_tools/tmp_kamaz_input_assets_audit.py
?? Pyton_script/unreal_tools/tmp_kamaz_maps_actor_classes.py
?? Pyton_script/unreal_tools/tmp_kamaz_reset_chain_detail.py
?? Pyton_script/unreal_tools/tmp_kamaz_respawn_hold_audit.py
?? Pyton_script/unreal_tools/tmp_kamaz_startbrake_branches.py
?? Pyton_script/unreal_tools/tmp_kamaz_startbrake_var_usage.py
?? Pyton_script/unreal_tools/tmp_probe_enhanced_node_dir.py
?? Pyton_script/unreal_tools/tmp_probe_enhanced_node_methods.py
?? Pyton_script/unreal_tools/tmp_probe_enhanced_node_properties.py
?? Pyton_script/unreal_tools/tmp_probe_node_access.py
?? Pyton_script/unreal_tools/tmp_probe_vehicleadv_graph_api.py
?? Pyton_script/unreal_tools/tmp_snowtest_landscape_road_material_audit.py
?? Pyton_script/unreal_tools/tmp_try_set_protected_inputaction.py
?? Pyton_script/unreal_tools/validate_road_height_carrier_for_road2.py
?? RUN_FIX_CLUMBA_SPRUCE_HEADLESS.cmd
?? RUN_FIX_CLUMBI_TVERSKAY_MEDIA_HEADLESS.cmd
?? RUN_FIX_ENGINE_NANITE_USAGE_FLAGS_HEADLESS.cmd
?? RUN_FIX_KNOWN_INVALID_NANITE_HEADLESS.cmd
?? RUN_SNOW_DEBUG_CHAIN_HEADLESS.cmd
?? ResearchPack.zip
?? ResearchPack/
?? Source/Kamaz_Cleaner/Private/Snow/RuntimeV1/
?? Source/Kamaz_Cleaner/Private/Snow/SnowRuntimeTrailBridgeActor.cpp
?? Source/Kamaz_Cleaner/Private/Snow/SnowRuntimeTrailBridgeComponent.cpp
?? Source/Kamaz_Cleaner/Private/Snow/SnowSplineRoadActor.cpp
?? Source/Kamaz_Cleaner/Private/Vehicle/
?? Source/Kamaz_Cleaner/Public/Snow/RuntimeV1/
?? Source/Kamaz_Cleaner/Public/Snow/SnowReceiverSurfaceTags.h
?? Source/Kamaz_Cleaner/Public/Snow/SnowRuntimeTrailBridgeActor.h
?? Source/Kamaz_Cleaner/Public/Snow/SnowRuntimeTrailBridgeComponent.h
?? Source/Kamaz_Cleaner/Public/Snow/SnowSplineRoadActor.h
?? Source/Kamaz_Cleaner/Public/Vehicle/
?? Tools/
~~~

### git diff --stat

~~~text
 .gitignore                                         |  13 +
 Config/DefaultEngine.ini                           |   2 +
 Config/DefaultGame.ini                             |   2 +
 Content/BPs/BP_KamazGameMode.uasset                |   4 +-
 .../SnowV2P1/MaterialsP1/M_SnowV2P1_Master.uasset  |   4 +-
 Content/CityPark/Kamaz/model/KamazBP.uasset        |   4 +-
 .../SnowSystem/BP_PlowBrush_Component.uasset       |   4 +-
 .../SnowSystem/BP_WheelSnowTrace_Component.uasset  |   4 +-
 .../BrushMaterials/M_Snow_PlowBrush.uasset         |   4 +-
 .../BrushMaterials/M_Snow_WheelBrush.uasset        |   4 +-
 Content/CityPark/SnowSystem/MPC_SnowSystem.uasset  |   4 +-
 .../SnowSystem/RT_SnowTest_WheelTracks.uasset      |   4 +-
 .../RVT_MVP/MI_SnowReceiver_RVT_MVP.uasset         |   4 +-
 .../RVT_MVP/M_RVT_DebugWriter_MVP.uasset           |   4 +-
 .../RVT_MVP/M_SnowReceiver_RVT_MVP.uasset          |   4 +-
 .../SnowSystem/RVT_MVP/RVT_SnowMask_MVP.uasset     |   4 +-
 Content/CityPark/SnowSystem/SnowTest_Level.umap    |   4 +-
 Content/Maps/MoscowEA5.umap                        |   4 +-
 Content/Meshes/Roads/Road.uasset                   |   4 +-
 .../Blueprints/BP_VehicleAdvPawnBase.uasset        |   4 +-
 .../SportsCar/BP_VehicleAdvSportsCar.uasset        |   4 +-
 Kamaz_Cleaner.uproject                             |   6 +-
 .../Private/BlueprintAutomationPythonBridge.cpp    | 184 ++++++++++++
 .../Public/BlueprintAutomationPythonBridge.h       |   7 +
 .../probe_active_pie_snow_rt.cpython-311.pyc       | Bin 14041 -> 15152 bytes
 .../fix_vehicle_template_input_nodes.py            | 332 ++++++++++++++++++---
 .../unreal_tools/probe_active_pie_snow_rt.py       | 126 ++++----
 .../unreal_tools/trace_m_snow_plow_brush_graph.py  |   7 +-
 Source/Kamaz_Cleaner/Kamaz_Cleaner.Build.cs        |   5 +-
 29 files changed, 615 insertions(+), 141 deletions(-)
~~~

## Recent build/log excerpts

### Latest AI build log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\.ai\logs\run_smoke_20260325-025606.log
~~~text
[2026.03.24-23.56.27:769][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:769][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:769][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:769][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:769][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:769][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:769][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:769][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:769][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:769][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:769][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:770][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:770][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:770][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:770][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:770][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:770][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:770][  3]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.24-23.56.27:770][  3]LogEOSSDK: LogEOS: SDK Config Platform Update Request Successful, Time: 13.311977
[2026.03.24-23.56.27:770][  3]LogEOSSDK: LogEOSAnalytics: EOS SDK Analytics disabled for route [1].
[2026.03.24-23.56.27:770][  3]LogEOSSDK: LogEOS: Updating Product SDK Config, Time: 13.740367
[2026.03.24-23.56.27:770][  3]Cmd: QUIT_EDITOR
[2026.03.24-23.56.27:770][  3]LogCore: Engine exit requested (reason: UUnrealEdEngine::CloseEditor())
[2026.03.24-23.56.27:770][  3]LogCore: Engine exit requested (reason: EngineExit() was called; note: exit was already requested)
[2026.03.24-23.56.27:770][  3]LogStaticMesh: Abandoning remaining async distance field tasks for shutdown
[2026.03.24-23.56.27:770][  3]LogStaticMesh: Abandoning remaining async card representation tasks for shutdown
[2026.03.24-23.56.27:771][  3]LogStreaming: Display: FlushAsyncLoading(): 0 QueuedPackages, 1 AsyncPackages
[2026.03.24-23.56.27:844][  3]LogWorld: UWorld::CleanupWorld for MoscowEA5, bSessionEnded=true, bCleanupResources=true
[2026.03.24-23.56.27:844][  3]LogSlate: InvalidateAllWidgets triggered.  All widgets were invalidated
[2026.03.24-23.56.27:847][  3]LogWorld: UWorld::CleanupWorld for Clumbi_Tverskay, bSessionEnded=true, bCleanupResources=true
[2026.03.24-23.56.27:847][  3]LogSlate: InvalidateAllWidgets triggered.  All widgets were invalidated
[2026.03.24-23.56.27:862][  3]LogTedsSettings: UTedsSettingsEditorSubsystem::Deinitialize
[2026.03.24-23.56.27:863][  3]LogLevelSequenceEditor: LevelSequenceEditor subsystem deinitialized.
[2026.03.24-23.56.27:864][  3]LogWorld: UWorld::CleanupWorld for World_0, bSessionEnded=true, bCleanupResources=true
[2026.03.24-23.56.27:864][  3]LogSlate: InvalidateAllWidgets triggered.  All widgets were invalidated
[2026.03.24-23.56.27:865][  3]LogRuntimeTelemetry: Recording EnginePreExit events
[2026.03.24-23.56.27:868][  3]LogAnalytics: Display: [UEEditor.Rocket.Release] AnalyticsET::EndSession
[2026.03.24-23.56.27:881][  3]LogAudio: Display: Beginning Audio Device Manager Shutdown (Module: AudioMixerXAudio2)...
[2026.03.24-23.56.27:881][  3]LogAudio: Display: Destroying 1 Remaining Audio Device(s)...
[2026.03.24-23.56.27:881][  3]LogAudio: Display: Audio Device unregistered from world 'MoscowEA5'.
[2026.03.24-23.56.27:882][  3]LogAudio: Display: Shutting down audio device while 1 references to it are still alive. For more information, compile with INSTRUMENT_AUDIODEVICE_HANDLES.
[2026.03.24-23.56.27:882][  3]LogAudioMixer: Display: FMixerPlatformXAudio2::StopAudioStream() called. InstanceID=1, StreamState=4
[2026.03.24-23.56.27:883][  3]LogAudioMixer: Display: FMixerPlatformXAudio2::StopAudioStream() called. InstanceID=1, StreamState=2
[2026.03.24-23.56.27:887][  3]LogAudioMixer: Deinitializing Audio Bus Subsystem for audio device with ID -1
[2026.03.24-23.56.27:887][  3]LogAudio: Display: Audio Device Manager Shutdown
[2026.03.24-23.56.27:887][  3]LogSlate: Window 'Message Log' being destroyed
[2026.03.24-23.56.27:890][  3]LogSlate: Window 'Content Browser' being destroyed
[2026.03.24-23.56.27:897][  3]LogSlate: Window 'Content Browser 2' being destroyed
[2026.03.24-23.56.27:906][  3]LogSlate: Window 'Kamaz_Cleaner - Unreal Editor' being destroyed
[2026.03.24-23.56.27:931][  3]LogSlate: Slate User Destroyed.  User Index 0, Is Virtual User: 0
[2026.03.24-23.56.27:931][  3]LogExit: Preparing to exit.
[2026.03.24-23.56.27:967][  3]LogUObjectHash: Compacting FUObjectHashTables data took   0.43ms
[2026.03.24-23.56.28:519][  3]LogEditorDataStorage: Deinitializing
[2026.03.24-23.56.28:651][  3]LogDemo: Cleaned up 0 splitscreen connections, owner deletion: enabled
[2026.03.24-23.56.28:660][  3]LogExit: Editor shut down
[2026.03.24-23.56.28:661][  3]LogExit: Transaction tracking system shut down
[2026.03.24-23.56.28:737][  3]LogStall: Shutdown...
[2026.03.24-23.56.28:742][  3]LogStall: Shutdown complete.
[2026.03.24-23.56.28:815][  3]LogExit: Object subsystem successfully closed.
[2026.03.24-23.56.28:924][  3]LogShaderCompilers: Display: Shaders left to compile 0
[2026.03.24-23.56.29:055][  3]LogMemoryProfiler: Shutdown
[2026.03.24-23.56.29:055][  3]LogNetworkingProfiler: Shutdown
[2026.03.24-23.56.29:055][  3]LoadingProfiler: Shutdown
[2026.03.24-23.56.29:055][  3]LogTimingProfiler: Shutdown
[2026.03.24-23.56.29:057][  3]LogChaosVDEditor: [FChaosVDExtensionsManager::UnRegisterExtension] UnRegistering CVD Extension [FChaosVDGenericDebugDrawExtension] ...
[2026.03.24-23.56.29:057][  3]LogChaosVDEditor: [FChaosVDExtensionsManager::UnRegisterExtension] UnRegistering CVD Extension [FChaosVDAccelerationStructuresExtension] ...
[2026.03.24-23.56.29:438][  3]LogWebBrowser: Deleting browser for Url=https://editor.unrealengine.com/en-US/recent-projects.
[2026.03.24-23.56.29:522][  3]LogChaosDD: Chaos Debug Draw Shutdown
[2026.03.24-23.56.29:526][  3]LogNFORDenoise: NFORDenoise function shutting down
[2026.03.24-23.56.29:526][  3]RenderDocPlugin: plugin has been unloaded.
[2026.03.24-23.56.29:927][  3]LogEOSSDK: LogEOS: SDK Config Product Update Request Successful, Time: 16.971951
[2026.03.24-23.56.29:928][  3]LogEOSSDK: LogEOS: SDK Config Data - Watermark: 518340485
[2026.03.24-23.56.29:928][  3]LogEOSSDK: LogEOS: ScheduleNextSDKConfigDataUpdate - Time: 16.971951, Update Interval: 357.515198
[2026.03.24-23.56.30:631][  3]LogEOSShared: FEOSSDKManager::Shutdown EOS_Shutdown Result=[EOS_Success]
[2026.03.24-23.56.30:631][  3]LogXGEController: Cleaning working directory: C:/Users/post/AppData/Local/Temp/UnrealXGEWorkingDir/
[2026.03.24-23.56.30:632][  3]LogPakFile: Destroying PakPlatformFile
[2026.03.24-23.56.30:774][  3]LogD3D12RHI: ~FD3D12DynamicRHI
[2026.03.24-23.56.30:811][  3]LogExit: Exiting.
[41608:5628:0325/025617.733:ERROR:google_update_settings.cc(265)] Failed opening key Software\Chromium to set usagestats; result: 5
[41608:28076:0325/025626.689:ERROR:device_event_log_impl.cc(196)] [02:56:26.323] USB: usb_service_win.cc:105 SetupDiGetDeviceProperty({{A45C254E-DF1C-4EFD-8020-67D146A850E0}, 6}) failed: Element not found. (0x490)
~~~

### Latest Unreal editor log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\Logs\cef3.log
~~~text
[41608:28076:0325/025617.632:WARNING:chrome_main_delegate.cc(745)] This is Chrome version 128.0.6613.138 (not a warning)
[41608:5628:0325/025617.733:ERROR:google_update_settings.cc(265)] Failed opening key Software\Chromium to set usagestats; result: 5
[41608:28076:0325/025617.748:WARNING:account_consistency_mode_manager.cc(77)] Desktop Identity Consistency cannot be enabled as no OAuth client ID and client secret have been configured.
[41608:28076:0325/025626.689:ERROR:device_event_log_impl.cc(196)] [02:56:26.323] USB: usb_service_win.cc:105 SetupDiGetDeviceProperty({{A45C254E-DF1C-4EFD-8020-67D146A850E0}, 6}) failed: Element not found. (0x490)
[41608:28076:0325/025629.026:WARNING:pref_notifier_impl.cc(41)] Pref observer for media_router.cast_allow_all_ips found at shutdown.
~~~

### Latest Blueprint automation log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\inspect_moscowea5_road2_carrier_runtime.json
~~~text
      "location": {
        "x": -67246.10546875,
        "y": -123162.78396576445,
        "z": -207292.87721531276
      },
      "rotation": {
        "pitch": 0.0,
        "yaw": 0.0,
        "roll": 0.0
      },
      "scale3d": {
        "x": 1.0,
        "y": 1.0,
        "z": 1.0
      },
      "root_component": "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.SnowRuntimeTrailBridgeActor_0.Root",
      "receiver_surface": null,
      "trail_component": {
        "component_path": "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.SnowRuntimeTrailBridgeActor_0.TrailComponent",
        "bEnableRuntimeTrail": true,
        "bEnableRuntimeReceiverHeightControl": true,
        "RuntimeHeightAmplitudeParameterName": "HeightAmplitude",
        "RuntimeHeightAmplitudeWhenActive": -100.0,
        "RuntimeHeightAmplitudeWhenInactive": 0.0,
        "SourceComponentOverride": ""
      },
      "mesh_components": []
    }
  ],
  "trail_candidate_count": 1,
  "trail_candidates": [
    {
      "actor_label": "SnowRuntimeTrailBridgeActor",
      "actor_name": "SnowRuntimeTrailBridgeActor_0",
      "actor_path": "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.SnowRuntimeTrailBridgeActor_0",
      "actor_class": "/Script/Kamaz_Cleaner.SnowRuntimeTrailBridgeActor",
      "location": {
        "x": -67246.10546875,
        "y": -123162.78396576445,
        "z": -207292.87721531276
      },
      "rotation": {
        "pitch": 0.0,
        "yaw": 0.0,
        "roll": 0.0
      },
      "scale3d": {
        "x": 1.0,
        "y": 1.0,
        "z": 1.0
      },
      "root_component": "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.SnowRuntimeTrailBridgeActor_0.Root",
      "receiver_surface": null,
      "trail_component": {
        "component_path": "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.SnowRuntimeTrailBridgeActor_0.TrailComponent",
        "bEnableRuntimeTrail": true,
        "bEnableRuntimeReceiverHeightControl": true,
        "RuntimeHeightAmplitudeParameterName": "HeightAmplitude",
        "RuntimeHeightAmplitudeWhenActive": -100.0,
        "RuntimeHeightAmplitudeWhenInactive": 0.0,
        "SourceComponentOverride": ""
      },
      "mesh_components": []
    }
  ],
  "receiver_actor_count": 1,
  "receiver_actors": [
    {
      "actor_label": "SnowHeightBridgeSurface_Road2",
      "actor_path": "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_251",
      "receiver_surface": {
        "component_path": "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.StaticMeshActor_251.SnowReceiverSurfaceComponent_0",
        "SurfaceFamily": "<SnowReceiverSurfaceFamily.ROAD: 1>",
        "ReceiverPriority": 110,
        "ReceiverSetTag": "RoadSnowCarrierHeight",
        "bParticipatesInPersistentSnowState": true
      }
    }
  ]
}
~~~

## Open questions

- Manual PIE verification still needed: does the plow visibly lower snow height on Road2 carrier when driving in MoscowEA5? Is RuntimeHeightAmplitudeWhenActive=-100 visually strong enough for the tagged road carrier or should the tuning be adjusted after gameplay review? Do we want to keep the runtime trail actor colocated near Road2 or reposition it for editor clarity now that it auto-resolves the possessed pawn?

