# Senior Escalation Packet

- Generated: 2026-03-23 04:43:09 +03:00
- Project root: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner
- Branch: snow-source-truth-snapshot

## Goal

Make SnowTest_Level snow clearing depend on plow lift height instead of a binary gate

## Hypothesis

The torn trail and snow being added on already clean asphalt came from a binary active/inactive trail model. SnowTest_Level exposes PlowLiftHeight=1.0 and bEnablePlowClearing=true on BP_PlowBrush_Component, so the runtime trail should scale both stamp emission and receiver depth from that plow signal: fully lifted means no new stamp, lowered means deeper clearing.

## Files to touch

- Source/Kamaz_Cleaner/Public/Snow/SnowRuntimeTrailBridgeComponent.h
- Source/Kamaz_Cleaner/Private/Snow/SnowRuntimeTrailBridgeComponent.cpp
- Pyton_script/unreal_tools/apply_right_plow_berm.py
- Pyton_script/unreal_tools/inspect_current_snowtest_receivers.py
- Pyton_script/unreal_tools/inspect_snowtest_plow_sources.py
- Saved/BlueprintAutomation/apply_right_plow_berm.json
- Saved/BlueprintAutomation/inspect_current_snowtest_receivers.json
- Saved/BlueprintAutomation/inspect_snowtest_plow_sources.json
- Saved/BlueprintAutomation/rebuild_m_snowreceiver_rvt_height_mvp_berm.json
- .ai/logs/build_editor_20260323-043915.log
- .ai/logs/run_smoke_engine_20260323-043930.log
- .ai/logs/run_smoke_engine_20260323-044145.log
- .gitignore
- Config/DefaultEngine.ini
- Config/DefaultGame.ini
- Content/BPs/BP_KamazGameMode.uasset
- Content/CityPark/Kamaz/model/KamazBP.uasset
- Content/CityPark/SnowSystem/BP_PlowBrush_Component.uasset
- Content/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush.uasset
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
?? Pyton_script/unreal_tools/apply_soft_rvt_stamp_edges.py
?? Pyton_script/unreal_tools/attach_kamaz_startup_hold_component.py
?? Pyton_script/unreal_tools/build_snow_runtime_v1_phase1.py
?? Pyton_script/unreal_tools/build_snow_runtime_v1_phase2_wheel.py
?? Pyton_script/unreal_tools/clone_kamaz_handling_audit.py
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
?? Pyton_script/unreal_tools/phase3_real_height_mvp.py
?? Pyton_script/unreal_tools/phase4_quality_refinement_mvp.py
?? Pyton_script/unreal_tools/phase5_production_bridge_mvp.py
?? Pyton_script/unreal_tools/phase6_runtime_trail_binary_probe.py
?? Pyton_script/unreal_tools/phase6_runtime_trail_mvp.py
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
 23 files changed, 532 insertions(+), 82 deletions(-)
~~~

## Recent build/log excerpts

### Latest AI build log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\.ai\logs\run_smoke_20260323-044145.log
~~~text
  },

  "error": ""

}
[2026.03.23-01.41.58:156][  1]LogMaterial: Warning: Material 'MI_Granite_Tiles_Facade_ukfkbbvfw_1K2' expects texture 'WhiteSquareTexture' to be Virtual
[2026.03.23-01.41.58:447][  1]LogMaterial: Warning: Material 'MI_Granite_Tiles_Facade_ukfkbbvfw_1K2' expects texture 'WhiteSquareTexture' to be Virtual
[2026.03.23-01.41.58:447][  1]LogMaterial: Warning: Material 'MI_Strastnaya' expects texture 'Strastnaya' to be Virtual
[2026.03.23-01.41.58:449][  1]LogMaterial: Warning: Material 'MI_Strastnaya' expects texture 'Strastnaya' to be Virtual
[2026.03.23-01.41.58:449][  1]LogMaterial: Warning: Material 'MI_Strastnoy' expects texture 'strastnoy' to be Virtual
[2026.03.23-01.41.58:449][  1]LogMaterial: Warning: Material 'MI_Strastnoy' expects texture 'strastnoy' to be Virtual
[2026.03.23-01.41.58:557][  2]LogEOSSDK: LogEOS: SDK Config Platform Update Request Successful, Time: 8.342645
[2026.03.23-01.41.58:558][  2]LogMaterial: Warning: Material 'MI_Tverskaya' expects texture 'tverskaya' to be Virtual
[2026.03.23-01.41.58:558][  2]LogMaterial: Warning: Material 'MI_Tverskaya' expects texture 'tverskaya' to be Virtual
[2026.03.23-01.41.58:558][  2]LogMaterial: Warning: Material 'MI_Decal_BUSSTOP' expects texture 'busstop' to be Virtual
[2026.03.23-01.41.58:558][  2]LogMaterial: Warning: Material 'MI_Decal_BUSSTOP' expects texture 'busstop' to be Virtual
[2026.03.23-01.41.58:558][  2]LogMaterial: Warning: Material 'MI_Decal_gerb' expects texture 'gerb' to be Virtual
[2026.03.23-01.41.58:558][  2]LogMaterial: Warning: Material 'MI_Decal_gerb' expects texture 'gerb' to be Virtual
[2026.03.23-01.41.58:558][  2]LogEOSSDK: LogEOSAnalytics: EOS SDK Analytics disabled for route [1].
[2026.03.23-01.41.58:559][  2]LogEOSSDK: LogEOS: Updating Product SDK Config, Time: 8.453489
[2026.03.23-01.41.58:559][  2]LogMaterial: Warning: Material 'MI_Granite_Tiles_Facade_ukfkbbvfw_1K2' expects texture 'WhiteSquareTexture' to be Virtual
[2026.03.23-01.41.58:560][  2]LogMaterial: Warning: Material 'MI_Strastnaya' expects texture 'Strastnaya' to be Virtual
[2026.03.23-01.41.58:560][  2]LogMaterial: Warning: Material 'MI_Strastnaya' expects texture 'Strastnaya' to be Virtual
[2026.03.23-01.41.58:560][  2]LogMaterial: Warning: Material 'MI_Strastnoy' expects texture 'strastnoy' to be Virtual
[2026.03.23-01.41.58:560][  2]LogMaterial: Warning: Material 'MI_Strastnoy' expects texture 'strastnoy' to be Virtual
[2026.03.23-01.41.58:560][  2]LogMaterial: Warning: Material 'MI_Bike_Stand_uhcgehnfa_2K' expects texture 'T_Bike_Stand_uhcgehnfa_2K_D' to be Virtual
[2026.03.23-01.41.58:560][  2]LogMaterial: Warning: Material 'MI_Bike_Stand_uhcgehnfa_2K' expects texture 'T_BikeStand_uhcgehnfa_2K_DpR' to be Virtual
[2026.03.23-01.41.58:568][  2]Cmd: QUIT_EDITOR
[2026.03.23-01.41.58:569][  3]LogCore: Engine exit requested (reason: UUnrealEdEngine::CloseEditor())
[2026.03.23-01.41.58:572][  3]LogCore: Engine exit requested (reason: EngineExit() was called; note: exit was already requested)
[2026.03.23-01.41.58:677][  3]LogStaticMesh: Abandoning remaining async distance field tasks for shutdown
[2026.03.23-01.41.58:677][  3]LogStaticMesh: Abandoning remaining async card representation tasks for shutdown
[2026.03.23-01.41.58:677][  3]LogStreaming: Display: FlushAsyncLoading(): 0 QueuedPackages, 1 AsyncPackages
[2026.03.23-01.41.58:679][  3]LogWorld: UWorld::CleanupWorld for SnowLevel, bSessionEnded=true, bCleanupResources=true
[2026.03.23-01.41.58:679][  3]LogSlate: InvalidateAllWidgets triggered.  All widgets were invalidated
[2026.03.23-01.41.58:694][  3]LogTedsSettings: UTedsSettingsEditorSubsystem::Deinitialize
[2026.03.23-01.41.58:694][  3]LogLevelSequenceEditor: LevelSequenceEditor subsystem deinitialized.
[2026.03.23-01.41.58:695][  3]LogRuntimeTelemetry: Recording EnginePreExit events
[2026.03.23-01.41.58:698][  3]LogAnalytics: Display: [UEEditor.Rocket.Release] AnalyticsET::EndSession
[2026.03.23-01.41.58:699][  3]LogAudio: Display: Beginning Audio Device Manager Shutdown (Module: AudioMixerXAudio2)...
[2026.03.23-01.41.58:699][  3]LogAudio: Display: Destroying 1 Remaining Audio Device(s)...
[2026.03.23-01.41.58:699][  3]LogAudio: Display: Audio Device unregistered from world 'SnowLevel'.
[2026.03.23-01.41.58:699][  3]LogAudio: Display: Shutting down audio device while 1 references to it are still alive. For more information, compile with INSTRUMENT_AUDIODEVICE_HANDLES.
[2026.03.23-01.41.58:726][  3]LogAudioMixer: Display: FMixerPlatformXAudio2::StopAudioStream() called. InstanceID=1, StreamState=4
[2026.03.23-01.41.58:728][  3]LogAudioMixer: Display: FMixerPlatformXAudio2::StopAudioStream() called. InstanceID=1, StreamState=2
[2026.03.23-01.41.58:733][  3]LogAudioMixer: Deinitializing Audio Bus Subsystem for audio device with ID -1
[2026.03.23-01.41.58:734][  3]LogAudio: Display: Audio Device Manager Shutdown
[2026.03.23-01.41.58:734][  3]LogSlate: Window 'Message Log' being destroyed
[2026.03.23-01.41.58:738][  3]LogSlate: Window 'Kamaz_Cleaner - Unreal Editor' being destroyed
[2026.03.23-01.41.58:773][  3]LogSlate: Slate User Destroyed.  User Index 0, Is Virtual User: 0
[2026.03.23-01.41.58:773][  3]LogExit: Preparing to exit.
[2026.03.23-01.41.58:809][  3]LogUObjectHash: Compacting FUObjectHashTables data took   0.43ms
[2026.03.23-01.41.59:618][  3]LogEditorDataStorage: Deinitializing
[2026.03.23-01.41.59:715][  3]LogDemo: Cleaned up 0 splitscreen connections, owner deletion: enabled
[2026.03.23-01.41.59:722][  3]LogExit: Editor shut down
[2026.03.23-01.41.59:724][  3]LogExit: Transaction tracking system shut down
[2026.03.23-01.41.59:773][  3]LogStall: Shutdown...
[2026.03.23-01.41.59:778][  3]LogStall: Shutdown complete.
[2026.03.23-01.41.59:850][  3]LogExit: Object subsystem successfully closed.
[2026.03.23-01.41.59:885][  3]LogShaderCompilers: Display: Shaders left to compile 0
[2026.03.23-01.42.00:012][  3]LogMemoryProfiler: Shutdown
[2026.03.23-01.42.00:013][  3]LogNetworkingProfiler: Shutdown
[2026.03.23-01.42.00:013][  3]LoadingProfiler: Shutdown
[2026.03.23-01.42.00:013][  3]LogTimingProfiler: Shutdown
[2026.03.23-01.42.00:013][  3]LogChaosVDEditor: [FChaosVDExtensionsManager::UnRegisterExtension] UnRegistering CVD Extension [FChaosVDGenericDebugDrawExtension] ...
[2026.03.23-01.42.00:013][  3]LogChaosVDEditor: [FChaosVDExtensionsManager::UnRegisterExtension] UnRegistering CVD Extension [FChaosVDAccelerationStructuresExtension] ...
[2026.03.23-01.42.00:273][  3]LogWebBrowser: Deleting browser for Url=https://editor.unrealengine.com/en-US/recent-projects.
[2026.03.23-01.42.00:318][  3]LogChaosDD: Chaos Debug Draw Shutdown
[2026.03.23-01.42.00:318][  3]RenderDocPlugin: plugin has been unloaded.
[2026.03.23-01.42.00:719][  3]LogEOSSDK: LogEOS: SDK Config Product Update Request Successful, Time: 10.592741
[2026.03.23-01.42.00:720][  3]LogEOSSDK: LogEOS: SDK Config Data - Watermark: 518340485
[2026.03.23-01.42.00:720][  3]LogEOSSDK: LogEOS: ScheduleNextSDKConfigDataUpdate - Time: 10.592741, Update Interval: 347.050385
[2026.03.23-01.42.01:445][  3]LogEOSShared: FEOSSDKManager::Shutdown EOS_Shutdown Result=[EOS_Success]
[2026.03.23-01.42.01:449][  3]LogNFORDenoise: NFORDenoise function shutting down
[2026.03.23-01.42.01:449][  3]LogXGEController: Cleaning working directory: C:/Users/post/AppData/Local/Temp/UnrealXGEWorkingDir/
[2026.03.23-01.42.01:451][  3]LogPakFile: Destroying PakPlatformFile
[2026.03.23-01.42.01:620][  3]LogD3D12RHI: ~FD3D12DynamicRHI
[2026.03.23-01.42.01:668][  3]LogExit: Exiting.
[22812:55664:0323/044152.040:ERROR:google_update_settings.cc(265)] Failed opening key Software\Chromium to set usagestats; result: 5
[22812:10016:0323/044158.560:ERROR:device_event_log_impl.cc(196)] [04:41:58.481] USB: usb_service_win.cc:105 SetupDiGetDeviceProperty({{A45C254E-DF1C-4EFD-8020-67D146A850E0}, 6}) failed: Element not found. (0x490)
~~~

### Latest Unreal editor log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\Logs\cef3.log
~~~text
[22812:10016:0323/044151.959:WARNING:chrome_main_delegate.cc(745)] This is Chrome version 128.0.6613.138 (not a warning)
[22812:55664:0323/044152.040:ERROR:google_update_settings.cc(265)] Failed opening key Software\Chromium to set usagestats; result: 5
[22812:10016:0323/044152.056:WARNING:account_consistency_mode_manager.cc(77)] Desktop Identity Consistency cannot be enabled as no OAuth client ID and client secret have been configured.
[22812:10016:0323/044158.560:ERROR:device_event_log_impl.cc(196)] [04:41:58.481] USB: usb_service_win.cc:105 SetupDiGetDeviceProperty({{A45C254E-DF1C-4EFD-8020-67D146A850E0}, 6}) failed: Element not found. (0x490)
[22812:10016:0323/044159.985:WARNING:pref_notifier_impl.cc(41)] Pref observer for media_router.cast_allow_all_ips found at shutdown.
~~~

### Latest Blueprint automation log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\inspect_current_snowtest_receivers.json
~~~text
                    "ThinSnowMinVisualOpacity",
                    "EdgeDustingStrength",
                    "SnowRoughness",
                    "PressedRoughness",
                    "HeightBias",
                    "HeightAmplitude",
                    "RepeatAccumulationDepth",
                    "RightBermSharpness",
                    "DirtyBermTintStrength",
                    "RightBermRaise"
                  ]
                }
              ],
              "instance_scalars": {
                "HeightAmplitude": null,
                "EdgeRaiseAmplitude": null,
                "RoadEdgeBlendWidth": null,
                "RoadEdgeHeightFade": null,
                "RightBermRaise": null,
                "RepeatAccumulationDepth": null
              }
            }
          ]
        }
      ]
    }
  ],
  "trail": {
    "label": "SnowRuntimeTrailBridgeActor",
    "path": "/Game/CityPark/SnowSystem/SnowLevel.SnowLevel:PersistentLevel.SnowRuntimeTrailBridgeActor_0",
    "components": [
      {
        "component": "TrailComponent",
        "class": "SnowRuntimeTrailBridgeComponent",
        "stamp_material": "/Game/CityPark/SnowSystem/RVT_MVP/M_RVT_DebugWriter_MVP.M_RVT_DebugWriter_MVP",
        "stamp_material_scalar_names": [
          "ClearStrength",
          "RepeatDepthStrength",
          "StampEdgeFeatherPercent",
          "BermOnly",
          "BermStrength"
        ],
        "stamp_material_chain": [
          {
            "name": "M_RVT_DebugWriter_MVP",
            "path": "/Game/CityPark/SnowSystem/RVT_MVP/M_RVT_DebugWriter_MVP.M_RVT_DebugWriter_MVP",
            "class": "Material",
            "scalar_params": [
              "ClearStrength",
              "RepeatDepthStrength",
              "StampEdgeFeatherPercent",
              "BermOnly",
              "BermStrength"
            ]
          }
        ],
        "props": {
          "StampSpacingCm": 6.0,
          "PersistentPlowLengthCm": 120.0,
          "PersistentPlowWidthCm": 320.0,
          "RightBermContinuationRatio": 0.20000000298023224,
          "bEnableRepeatClearingAccumulation": true,
          "bEnableRuntimeReceiverHeightControl": true,
          "bUseSourceHeightGate": false,
          "RepeatAccumulationMaxPasses": 3,
          "FirstPassClearStrength": 0.75,
          "RepeatPassClearStrengthStep": 0.25,
          "MaxAccumulatedClearStrength": 1.0,
          "SourceActiveMaxRelativeZ": 95.0,
          "MinStampEngagementToWrite": 0.18000000715255737,
          "PlowLiftHeightForNoEffect": 1.0,
          "RuntimeHeightAmplitudeWhenActive": -360.0,
          "RuntimeHeightAmplitudeWhenInactive": 0.0,
          "SourceComponentOverride": ""
        }
      }
    ]
  },
  "error": ""
}
~~~

## Open questions

- A live drive in Unreal Editor is still needed to visually confirm that lowered plow now clears deeper and lifted plow stops writing stamps. Receiver material rebuild script currently reports Failed to create material for M_SnowReceiver_RVT_Height_MVP in unattended mode so this packet treats the runtime plow-height fix as validated and the parent-material rebuild path as a separate follow-up. SourceComponentOverride still reloads as empty but runtime source auto-resolution should still find BP_PlowBrush_Component on Kamaz_SnowTest.

