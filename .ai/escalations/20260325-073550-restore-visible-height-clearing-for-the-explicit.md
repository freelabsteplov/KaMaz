# Senior Escalation Packet

- Generated: 2026-03-25 07:35:50 +03:00
- Project root: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner
- Branch: snow-source-truth-snapshot

## Goal

Restore visible height clearing for the explicit RoadSnowCarrierHeight carrier without changing legacy bridge behavior.

## Hypothesis

Road2 height was not visibly clearing because the explicit tagged carrier path was still multiplied by the legacy bridge runtime height scale (0.06), collapsing a -95 runtime amplitude to only -5.7; the fix is to give explicit tagged road carriers full authored amplitude while leaving legacy name-based bridges on the old scale.

## Files to touch

- Source/Kamaz_Cleaner/Private/Snow/SnowRuntimeTrailBridgeComponent.cpp
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
- Content/Maps/MoscowEA5.umap
- Content/Meshes/Roads/Road.uasset
- Content/VehicleTemplate/Blueprints/BP_VehicleAdvPawnBase.uasset
- Content/VehicleTemplate/Blueprints/SportsCar/BP_VehicleAdvSportsCar.uasset
- Kamaz_Cleaner.uproject
- Plugins/BlueprintAutomationEditor/Source/BlueprintAutomationEditor/Private/BlueprintAutomationPythonBridge.cpp
- Plugins/BlueprintAutomationEditor/Source/BlueprintAutomationEditor/Public/BlueprintAutomationPythonBridge.h
- Pyton_script/unreal_tools/__pycache__/probe_active_pie_snow_rt.cpython-311.pyc
- Pyton_script/unreal_tools/fix_vehicle_template_input_nodes.py
- Pyton_script/unreal_tools/probe_active_pie_snow_rt.py
- Pyton_script/unreal_tools/trace_m_snow_plow_brush_graph.py
- Source/Kamaz_Cleaner/Kamaz_Cleaner.Build.cs

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
?? Content/CityPark/SnowSystem/Receivers/M_SnowRoadCarrier_HeightRoadBase.uasset
?? Content/CityPark/SnowSystem/SnowLevel.umap
?? Content/CityPark/SnowSystem/SnowRuntime_V1/
?? Content/Maps/SnowTest_Level.umap
?? Content/Ndi/
?? Content/VehicleTemplate/Input/Actions/
?? Docs/
?? Plugins/LudusAI/
?? Pyton_script/Snow_Mat.py.txt
?? Pyton_script/unreal_tools/_tmp_check_engine_mesh_candidates.py
?? Pyton_script/unreal_tools/_tmp_check_snowtestground_wpo_viability.py
?? Pyton_script/unreal_tools/_tmp_find_high_density_flat_mesh.py
?? Pyton_script/unreal_tools/_tmp_inspect_staticmesh_api.py
?? Pyton_script/unreal_tools/_tmp_list_actor_methods.py
?? Pyton_script/unreal_tools/_tmp_list_level_mesh_density.py
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
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\.ai\logs\build_editor_20260325-073450.log
~~~text
Using bundled DotNet SDK version: 8.0.412 win-x64
Running UnrealBuildTool: dotnet "..\..\Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.dll" Kamaz_CleanerEditor Win64 Development "-Project=C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Kamaz_Cleaner.uproject" -WaitMutex -NoHotReloadFromIDE
Log file: C:\Users\post\AppData\Local\UnrealBuildTool\Log.txt
Using 'git status' to determine working set for adaptive non-unity build (C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner).
Building Kamaz_CleanerEditor...
Using Visual Studio 2022 14.44.35214 toolchain (C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207) and Windows 10.0.22621.0 SDK (C:\Program Files (x86)\Windows Kits\10).
[Adaptive Build] Excluded from Kamaz_Cleaner unity file: SnowRuntimeTrailBridgeActor.cpp, SnowRuntimeTrailBridgeComponent.cpp, SnowSplineRoadActor.cpp, SnowFXManagerV1.cpp, SnowRuntimeBootstrapV1.cpp, SnowStateManagerV1.cpp, SnowWheelTelemetryV1Component.cpp, KamazStartupHoldComponent.cpp
[Adaptive Build] Excluded from BlueprintAutomationEditor unity file: BlueprintAutomationPythonBridge.cpp
Determining max actions to execute in parallel (24 physical cores, 32 logical cores)
  Executing up to 24 processes, one per physical core
Using Unreal Build Accelerator local executor to run 4 action(s)
  Storage capacity 40Gb
---- Starting trace: 260325_073451 ----
UbaSessionServer - Disable remote execution (remote sessions will finish current processes)
[1/4] Compile [x64] SnowRuntimeTrailBridgeComponent.cpp
[2/4] Link [x64] UnrealEditor-Kamaz_Cleaner.lib
UbaSessionServer - ERROR opening file C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Binaries\Win64\UnrealEditor-Kamaz_Cleaner.dll for write after retrying for 20 seconds (The process cannot access the file because it is being used by another process. - C:\Program Files\Epic Games\UE_5.7\UE_5.7\Engine\Binaries\Win64\UnrealEditor.exe)
Link [x64] UnrealEditor-Kamaz_Cleaner.dll: Exited with error code 9001. This action will retry without UBA
[3/4] Link [x64] UnrealEditor-Kamaz_Cleaner.dll [NoUba]
LINK : fatal error LNK1104: cannot open file 'C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Binaries\Win64\UnrealEditor-Kamaz_Cleaner.dll'
Trace written to file C:/Users/post/AppData/Local/UnrealBuildTool/Log.uba with size 4.9kb
Total time in Unreal Build Accelerator local executor: 23.33 seconds

Result: Failed (OtherCompilationError)
Total execution time: 24.00 seconds
~~~

### Latest Unreal editor log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\Logs\Kamaz_Cleaner.log
~~~text
[2026.03.25-04.31.27:778][565]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:787][566]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:795][567]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:802][568]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:811][569]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:820][570]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:828][571]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:836][572]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:845][573]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:853][574]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:862][575]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:870][576]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:879][577]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:886][578]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:894][579]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:904][580]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:912][581]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:920][582]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:929][583]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:936][584]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:945][585]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:953][586]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:961][587]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:970][588]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:978][589]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:987][590]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.27:994][591]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:003][592]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:012][593]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:020][594]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:028][595]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:037][596]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:045][597]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:053][598]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:062][599]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:070][600]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:078][601]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:087][602]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:095][603]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:102][604]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:111][605]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:119][606]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:127][607]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:136][608]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:144][609]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:153][610]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:162][611]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:170][612]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:179][613]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:187][614]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:195][615]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:203][616]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:212][617]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:220][618]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:228][619]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:237][620]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:245][621]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:254][622]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:262][623]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:270][624]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:279][625]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:286][626]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:295][627]LogBlueprintUserMessages: [BP_PlowBrush_Component] Plow Drawing: {0} Height: {1}
[2026.03.25-04.31.28:326][627]LogSlate: Updating window title bar state: overlay mode, drag disabled, window buttons hidden, title bar hidden
[2026.03.25-04.31.28:326][627]LogWorld: BeginTearingDown for /Game/Maps/UEDPIE_0_MoscowEA5
[2026.03.25-04.31.28:330][627]LogWorld: UWorld::CleanupWorld for MoscowEA5, bSessionEnded=true, bCleanupResources=true
[2026.03.25-04.31.28:377][627]LogSlate: InvalidateAllWidgets triggered.  All widgets were invalidated
[2026.03.25-04.31.28:381][627]LogPlayLevel: Display: Shutting down PIE online subsystems
[2026.03.25-04.31.28:387][627]LogSlate: InvalidateAllWidgets triggered.  All widgets were invalidated
[2026.03.25-04.31.28:437][627]LogAudio: Display: Audio Device unregistered from world 'None'.
[2026.03.25-04.31.28:437][627]LogAudioMixer: Deinitializing Audio Bus Subsystem for audio device with ID 4
[2026.03.25-04.31.28:438][627]LogAudioMixer: Display: FMixerPlatformXAudio2::StopAudioStream() called. InstanceID=4, StreamState=4
[2026.03.25-04.31.28:439][627]LogAudioMixer: Display: FMixerPlatformXAudio2::StopAudioStream() called. InstanceID=4, StreamState=2
[2026.03.25-04.31.28:457][627]LogSlate: Updating window title bar state: overlay mode, drag disabled, window buttons hidden, title bar hidden
[2026.03.25-04.31.28:514][627]LogUObjectHash: Compacting FUObjectHashTables data took   2.74ms
[2026.03.25-04.31.28:622][628]LogPlayLevel: Display: Destroying online subsystem :Context_4
[2026.03.25-04.31.28:644][628]LogUObjectHash: Compacting FUObjectHashTables data took   0.43ms
[2026.03.25-04.34.41:963][692]LogEOSSDK: LogEOS: Updating Product SDK Config, Time: 323.234039
[2026.03.25-04.34.42:963][695]LogEOSSDK: LogEOS: SDK Config Product Update Request Completed - No Change
[2026.03.25-04.34.42:963][695]LogEOSSDK: LogEOS: ScheduleNextSDKConfigDataUpdate - Time: 323.900696, Update Interval: 330.834076
~~~

### Latest Blueprint automation log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\validate_road_height_carrier_for_road2.json
~~~text
    },
    "SnowColor": {
      "expected": [
        1.0,
        1.0,
        1.0,
        1.0
      ],
      "actual": [
        1.0,
        1.0,
        1.0,
        1.0
      ],
      "matches": true
    },
    "PressedSnowColor": {
      "expected": [
        0.28,
        0.29,
        0.31,
        1.0
      ],
      "actual": [
        0.2800000011920929,
        0.28999999165534973,
        0.3100000023841858,
        1.0
      ],
      "matches": true
    },
    "ThinSnowUnderColor": {
      "expected": [
        0.38,
        0.39,
        0.41,
        1.0
      ],
      "actual": [
        0.3799999952316284,
        0.38999998569488525,
        0.4099999964237213,
        1.0
      ],
      "matches": true
    }
  },
  "receiver_checks": {
    "receiver_present": true,
    "surface_family_is_road": true,
    "receiver_priority_matches": true,
    "receiver_set_tag_matches": true,
    "persistent_state_enabled": true
  },
  "runtime_trail_checks": {
    "trail_actor_present": true,
    "trail_component_present": true,
    "runtime_trail_enabled": true,
    "runtime_height_control_enabled": true,
    "serialized_source_height_gate_disabled": true,
    "serialized_persistent_plow_length_matches": true,
    "serialized_persistent_plow_width_matches": true,
    "serialized_runtime_height_active_matches": true,
    "serialized_runtime_height_inactive_matches": true
  },
  "rvt_volume_checks": {
    "volume_present": true,
    "volume_path": "/Game/Maps/MoscowEA5.MoscowEA5:PersistentLevel.RuntimeVirtualTextureVolume_1",
    "component_present": true,
    "bound_asset_path": "/Game/CityPark/SnowSystem/RVT_MVP/RVT_SnowMask_MVP.RVT_SnowMask_MVP",
    "bound_asset_matches": true,
    "carrier_inside_volume": true,
    "target_actor_inside_volume": true
  },
  "target_render_checks": {
    "hidden_in_game_matches": true,
    "collision_preserved": true
  },
  "errors": []
}
~~~

## Open questions

- Manual PIE verification is still required after the editor releases the project DLL the currently open UnrealEditor session is locking UnrealEditor-Kamaz_Cleaner.dll and prevented full build validation.

