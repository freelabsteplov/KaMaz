# Senior Escalation Packet

- Generated: 2026-03-23 08:15:32 +03:00
- Project root: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner
- Branch: snow-source-truth-snapshot

## Goal

Fix SnowTest plow inversion, gray cleared snow, and restore separate wheel RT tracks on asphalt and snow.

## Hypothesis

Plow logic was already correct in C++, but the wheel RT path was broken because writer and probe had drifted away from the project BrushUV+MPC contract and were using mismatched bounds. Restoring canonical BrushUV stamping and road-zone bounds should make RT writes visible again while keeping plow clearing driven by plow lift.

## Files to touch

- Pyton_script/unreal_tools/persist_snowtest_wheel_rt_bounds_to_mpc_asset.py
- Pyton_script/unreal_tools/apply_snowtest_wheel_rt_chain.py
- Pyton_script/unreal_tools/rebuild_m_snow_wheel_brush.py
- Pyton_script/unreal_tools/probe_snowtest_wheel_rt_writer.py
- Pyton_script/unreal_tools/apply_right_plow_berm.py
- Pyton_script/unreal_tools/apply_snowtest_wheel_rt_overlay_inplace.py
- Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_berm.py
- Source/Kamaz_Cleaner/Public/Snow/SnowRuntimeTrailBridgeComponent.h
- Source/Kamaz_Cleaner/Private/Snow/SnowRuntimeTrailBridgeComponent.cpp
- .gitignore
- Config/DefaultEngine.ini
- Config/DefaultGame.ini
- Content/BPs/BP_KamazGameMode.uasset
- Content/CityPark/Kamaz/model/KamazBP.uasset
- Content/CityPark/SnowSystem/BP_PlowBrush_Component.uasset
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
 M Content/CityPark/Kamaz/model/KamazBP.uasset
 M Content/CityPark/SnowSystem/BP_PlowBrush_Component.uasset
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
 M Pyton_script/unreal_tools/fix_vehicle_template_input_nodes.py
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
?? Content/CityPark/SnowSystem/SnowLevel.umap
?? Content/CityPark/SnowSystem/SnowRuntime_V1/
?? Content/Maps/SnowTest_Level.umap
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
?? Pyton_script/unreal_tools/apply_snowtest_landscape_soft_seam.py
?? Pyton_script/unreal_tools/apply_snowtest_wheel_rt_chain.py
?? Pyton_script/unreal_tools/apply_snowtest_wheel_rt_overlay_inplace.py
?? Pyton_script/unreal_tools/apply_soft_rvt_stamp_edges.py
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
?? Pyton_script/unreal_tools/probe_snowtest_wheel_rt_writer.py
?? Pyton_script/unreal_tools/rebuild_m_snow_wheel_brush.py
?? Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_berm.py
?? Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_clean.py
?? Pyton_script/unreal_tools/recreate_rt_snowtest_wheeltracks_4k.py
?? Pyton_script/unreal_tools/reparent_landscape_runtimefix_mi_to_clean_parent.py
?? Pyton_script/unreal_tools/restore_snowtest_road_base_materials.py
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
 Content/CityPark/Kamaz/model/KamazBP.uasset        |   4 +-
 .../SnowSystem/BP_PlowBrush_Component.uasset       |   4 +-
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
 .../fix_vehicle_template_input_nodes.py            | 332 ++++++++++++++++++---
 .../unreal_tools/trace_m_snow_plow_brush_graph.py  |   7 +-
 Source/Kamaz_Cleaner/Kamaz_Cleaner.Build.cs        |   5 +-
 25 files changed, 536 insertions(+), 86 deletions(-)
~~~

## Recent build/log excerpts

### Latest AI build log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\.ai\logs\run_smoke_20260323-081415.log
~~~text
[2026.03.23-05.14.38:863][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:863][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:863][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:863][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:863][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:863][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:863][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:864][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:865][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:865][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:865][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:865][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:865][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:865][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:865][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:865][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:865][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa26038114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:865][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa25fe65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.23-05.14.38:865][  2]LogOutputDevice: Error: 
[2026.03.23-05.14.38:866][  2]LogStats:                SubmitErrorReport -  0.000 s
[2026.03.23-05.14.39:448][  2]LogStats:                    SendNewReport -  0.583 s
[2026.03.23-05.14.39:448][  2]LogStats:             FDebug::EnsureFailed -  1.604 s
[2026.03.23-05.14.39:451][  2]LogEOSSDK: LogEOS: SDK Config Platform Update Request Successful, Time: 17.108196
[2026.03.23-05.14.39:452][  2]LogEOSSDK: LogEOSAnalytics: EOS SDK Analytics disabled for route [1].
[2026.03.23-05.14.39:455][  2]LogEOSSDK: LogEOS: Updating Product SDK Config, Time: 18.971912
[2026.03.23-05.14.39:462][  2]Cmd: QUIT_EDITOR
[2026.03.23-05.14.39:464][  3]LogCore: Engine exit requested (reason: UUnrealEdEngine::CloseEditor())
[2026.03.23-05.14.39:467][  3]LogCore: Engine exit requested (reason: EngineExit() was called; note: exit was already requested)
[2026.03.23-05.14.39:471][  3]LogStaticMesh: Abandoning remaining async distance field tasks for shutdown
[2026.03.23-05.14.39:471][  3]LogStaticMesh: Abandoning remaining async card representation tasks for shutdown
[2026.03.23-05.14.39:493][  3]LogWorld: UWorld::CleanupWorld for SnowLevel, bSessionEnded=true, bCleanupResources=true
[2026.03.23-05.14.39:495][  3]LogOutputDevice: Warning: 

Script Stack (0 frames) :

[2026.03.23-05.14.39:498][  3]LogWindows: Error: appError called: Assertion failed: GetLevel(0) == PersistentLevel [File:D:\build\++UE5\Sync\Engine\Source\Runtime\Engine\Private\World.cpp] [Line: 6315] 


[2026.03.23-05.14.39:498][  3]LogWindows: Windows GetLastError: The operation completed successfully. (0)
[2026.03.23-05.14.43:848][  3]LogWindows: Error: === Critical error: ===
[2026.03.23-05.14.43:848][  3]LogWindows: Error: 
[2026.03.23-05.14.43:848][  3]LogWindows: Error: Assertion failed: GetLevel(0) == PersistentLevel [File:D:\build\++UE5\Sync\Engine\Source\Runtime\Engine\Private\World.cpp] [Line: 6315] 
[2026.03.23-05.14.43:848][  3]LogWindows: Error: 
[2026.03.23-05.14.43:848][  3]LogWindows: Error: 
[2026.03.23-05.14.43:848][  3]LogWindows: Error: 
[2026.03.23-05.14.43:850][  3]LogWindows: Error: [Callstack] 0x00007ffa1aed8448 UnrealEditor-Core.dll!UnknownFunction []
[2026.03.23-05.14.43:850][  3]LogWindows: Error: [Callstack] 0x00007ff9984c1279 UnrealEditor-Engine.dll!UnknownFunction []
[2026.03.23-05.14.43:850][  3]LogWindows: Error: [Callstack] 0x00007ff9984c0b9b UnrealEditor-Engine.dll!UnknownFunction []
[2026.03.23-05.14.43:850][  3]LogWindows: Error: [Callstack] 0x00007ff9b6313d13 UnrealEditor-UnrealEd.dll!UnknownFunction []
[2026.03.23-05.14.43:850][  3]LogWindows: Error: [Callstack] 0x00007ff60d30db05 UnrealEditor-Cmd.exe!UnknownFunction []
[2026.03.23-05.14.43:850][  3]LogWindows: Error: [Callstack] 0x00007ff60d310ca9 UnrealEditor-Cmd.exe!UnknownFunction []
[2026.03.23-05.14.43:850][  3]LogWindows: Error: [Callstack] 0x00007ff60d310d0a UnrealEditor-Cmd.exe!UnknownFunction []
[2026.03.23-05.14.43:850][  3]LogWindows: Error: [Callstack] 0x00007ff60d314590 UnrealEditor-Cmd.exe!UnknownFunction []
[2026.03.23-05.14.43:850][  3]LogWindows: Error: [Callstack] 0x00007ff60d325be4 UnrealEditor-Cmd.exe!UnknownFunction []
[2026.03.23-05.14.43:850][  3]LogWindows: Error: [Callstack] 0x00007ff60d3282f6 UnrealEditor-Cmd.exe!UnknownFunction []
[2026.03.23-05.14.43:850][  3]LogWindows: Error: [Callstack] 0x00007ffa686fe8d7 KERNEL32.DLL!UnknownFunction []
[2026.03.23-05.14.43:850][  3]LogWindows: Error: 
[2026.03.23-05.14.43:855][  3]LogExit: Executing StaticShutdownAfterError
[2026.03.23-05.14.43:858][  3]LogWindows: FPlatformMisc::RequestExit(1, LaunchWindowsStartup.ExceptionHandler)
[2026.03.23-05.14.43:859][  3]LogWindows: FPlatformMisc::RequestExitWithStatus(1, 3, LaunchWindowsStartup.ExceptionHandler)
[2026.03.23-05.14.43:859][  3]LogCore: Engine exit requested (reason: Win RequestExit; note: exit was already requested)
[1948:49204:0323/081422.378:ERROR:google_update_settings.cc(265)] Failed opening key Software\Chromium to set usagestats; result: 5
[1948:54352:0323/081439.453:ERROR:device_event_log_impl.cc(196)] [08:14:37.640] USB: usb_service_win.cc:105 SetupDiGetDeviceProperty({{A45C254E-DF1C-4EFD-8020-67D146A850E0}, 6}) failed: Element not found. (0x490)
~~~

### Latest Unreal editor log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\Logs\cef3.log
~~~text
[1948:54352:0323/081422.293:WARNING:chrome_main_delegate.cc(745)] This is Chrome version 128.0.6613.138 (not a warning)
[1948:49204:0323/081422.378:ERROR:google_update_settings.cc(265)] Failed opening key Software\Chromium to set usagestats; result: 5
[1948:54352:0323/081422.394:WARNING:account_consistency_mode_manager.cc(77)] Desktop Identity Consistency cannot be enabled as no OAuth client ID and client secret have been configured.
[58372:46092:0323/081437.637:ERROR:frame_impl.cc(537)] frame 5-BE0393916C317D69D79A10EC8F4B3CC6 connection timeout
[1948:54352:0323/081439.453:ERROR:device_event_log_impl.cc(196)] [08:14:37.640] USB: usb_service_win.cc:105 SetupDiGetDeviceProperty({{A45C254E-DF1C-4EFD-8020-67D146A850E0}, 6}) failed: Element not found. (0x490)
~~~

### Latest Blueprint automation log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\probe_snowtest_wheel_rt_writer.json
~~~text
    {
      "wheel": "WRL",
      "location": [
        19498.280720916024,
        -3688.5970062694555,
        63.87832595628811
      ],
      "uv": [
        0.5861886565906085,
        0.7139021217898885
      ]
    },
    {
      "wheel": "WRR",
      "location": [
        19519.39324089063,
        -3876.3048831991896,
        67.30428664573505
      ],
      "uv": [
        0.5865095616022982,
        0.7096964971855934
      ]
    }
  ],
  "manual_targeted_samples": [
    {
      "wheel": "WFL",
      "uv": [
        0.5801171490312673,
        0.7133145152386728
      ],
      "rgba": [
        0.89404296875,
        0.0,
        0.0,
        0.0
      ]
    },
    {
      "wheel": "WFR",
      "uv": [
        0.5804995480016596,
        0.7083030147750832
      ],
      "rgba": [
        0.97509765625,
        0.0,
        0.0,
        0.0
      ]
    },
    {
      "wheel": "WRL",
      "uv": [
        0.5861886565906085,
        0.7139021217898885
      ],
      "rgba": [
        0.88818359375,
        0.0,
        0.0,
        0.0
      ]
    },
    {
      "wheel": "WRR",
      "uv": [
        0.5865095616022982,
        0.7096964971855934
      ],
      "rgba": [
        0.98388671875,
        0.0,
        0.0,
        0.0
      ]
    }
  ]
}
~~~

## Open questions

- Headless run_smoke still ends with the known World cleanup assert GetLevel(0)==PersistentLevel after JSON outputs are written Live visual drive in editor remains the final user-facing check even though plow and wheel probes now validate the logic and RT signal.

