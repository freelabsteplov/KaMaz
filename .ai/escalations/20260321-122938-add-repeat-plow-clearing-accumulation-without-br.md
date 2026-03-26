# Senior Escalation Packet

- Generated: 2026-03-21 12:29:38 +03:00
- Project root: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner
- Branch: snow-source-truth-snapshot

## Goal

Add repeat plow clearing accumulation without breaking active RVT clearing

## Hypothesis

Current active path always writes full-strength RVT clear mask on every stamp, so repeat passes cannot deepen the result. We can preserve the working writer/receiver by introducing 3 stamp-strength tiers selected by local repeat-pass count and feeding ClearStrength through runtime stamp materials.

## Files to touch

- Source/Kamaz_Cleaner/Public/Snow/SnowRuntimeTrailBridgeComponent.h
- Source/Kamaz_Cleaner/Private/Snow/SnowRuntimeTrailBridgeComponent.cpp
- Pyton_script/unreal_tools/apply_repeat_clearing_accumulation.py
- .gitignore
- Config/DefaultEngine.ini
- Config/DefaultGame.ini
- Content/BPs/BP_KamazGameMode.uasset
- Content/CityPark/Kamaz/model/KamazBP.uasset
- Content/CityPark/SnowSystem/BP_PlowBrush_Component.uasset
- Content/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush.uasset
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
- Pyton_script/unreal_tools/fix_vehicle_template_input_nodes.py
- Source/Kamaz_Cleaner/Kamaz_Cleaner.Build.cs
- AGENTS.md
- Content/Automation/BP_BlueprintAutomationSmoke_2604CC05413414FEA1772CA218CB3AAF.uasset
- Content/Automation/BP_BlueprintAutomationSmoke_A124B8A544DDC511CF7D2EBFB09A145A.uasset
- Content/BPs/BP_KamazGameMode_HandlingAudit.uasset
- Content/CityPark/Kamaz/model/Front_wheels_HandlingAudit.uasset
- Content/CityPark/Kamaz/model/KamazBP_HandlingAudit.uasset

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
?? Pyton_script/unreal_tools/inspect_kamaz_runtime_owner_chain.py
?? Pyton_script/unreal_tools/inspect_material_instance_params.py
?? Pyton_script/unreal_tools/inspect_material_python_api.py
?? Pyton_script/unreal_tools/inspect_material_root_connections.py
?? Pyton_script/unreal_tools/inspect_snow_road_materials.py
?? Pyton_script/unreal_tools/phase3_real_height_mvp.py
?? Pyton_script/unreal_tools/phase4_quality_refinement_mvp.py
?? Pyton_script/unreal_tools/phase5_production_bridge_mvp.py
?? Pyton_script/unreal_tools/phase6_runtime_trail_binary_probe.py
?? Pyton_script/unreal_tools/phase6_runtime_trail_mvp.py
?? Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_clean.py
?? Pyton_script/unreal_tools/reparent_landscape_runtimefix_mi_to_clean_parent.py
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
 Source/Kamaz_Cleaner/Kamaz_Cleaner.Build.cs        |   5 +-
 21 files changed, 525 insertions(+), 78 deletions(-)
~~~

## Recent build/log excerpts

### Latest AI build log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\.ai\logs\build_editor_20260320-162944.log
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
---- Starting trace: 260320_162945 ----
UbaSessionServer - Disable remote execution (remote sessions will finish current processes)
[1/4] Compile [x64] SnowWheelTelemetryV1Component.cpp
[2/4] Link [x64] UnrealEditor-Kamaz_Cleaner.lib
[3/4] Link [x64] UnrealEditor-Kamaz_Cleaner.dll
[4/4] WriteMetadata Kamaz_CleanerEditor.target [NoUba]

Trace written to file C:/Users/post/AppData/Local/UnrealBuildTool/Log.uba with size 3.6kb
Total time in Unreal Build Accelerator local executor: 4.83 seconds

Result: Succeeded
Total execution time: 5.75 seconds
~~~

### Latest Unreal editor log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\Logs\Kamaz_Cleaner.log
~~~text
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a908114 UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: [Callstack] 0x00007ffa1a8b65af UnrealEditor-SlateCore.dll!UnknownFunction []
[2026.03.21-09.17.46:582][  2]LogOutputDevice: Error: 
[2026.03.21-09.17.46:584][  2]LogStats:                SubmitErrorReport -  0.000 s
[2026.03.21-09.17.47:917][  2]LogStats:                    SendNewReport -  1.333 s
[2026.03.21-09.17.47:917][  2]LogStats:             FDebug::EnsureFailed -  1.396 s
[2026.03.21-09.17.47:923][  2]LogAutomationController: Ignoring very large delta of 17.24 seconds in calls to FAutomationControllerManager::Tick() and not penalizing unresponsive tests
[2026.03.21-09.17.47:924][  2]LogMaterial: Warning: Material 'MI_Strastnaya' expects texture 'Strastnaya' to be Virtual
[2026.03.21-09.17.47:924][  2]LogMaterial: Warning: Material 'MI_Strastnaya' expects texture 'Strastnaya' to be Virtual
[2026.03.21-09.17.47:924][  2]LogMaterial: Warning: Material 'MI_Granite_Tiles_Facade_ukfkbbvfw_1K2' expects texture 'WhiteSquareTexture' to be Virtual
[2026.03.21-09.17.47:925][  2]LogEOSSDK: LogEOS: SDK Config Platform Update Request Successful, Time: 9.435745
[2026.03.21-09.17.47:926][  2]LogEOSSDK: LogEOSAnalytics: EOS SDK Analytics disabled for route [1].
[2026.03.21-09.17.47:927][  2]LogEOSSDK: LogEOS: Updating Product SDK Config, Time: 26.681202
[2026.03.21-09.17.47:987][  3]LogContentValidation: Enabled validators:
[2026.03.21-09.17.47:987][  3]LogContentValidation: 	/Script/DataValidation.DirtyFilesChangelistValidator
[2026.03.21-09.17.47:987][  3]LogContentValidation: 	/Script/DataValidation.EditorValidator_Localization
[2026.03.21-09.17.47:987][  3]LogContentValidation: 	/Script/DataValidation.EditorValidator_Material
[2026.03.21-09.17.47:987][  3]LogContentValidation: 	/Script/DataValidation.PackageFileValidator
[2026.03.21-09.17.47:987][  3]LogContentValidation: 	/Script/DataValidation.WorldPartitionChangelistValidator
[2026.03.21-09.17.47:987][  3]LogContentValidation: 	/Script/InputBlueprintNodes.EnhancedInputUserWidgetValidator
[2026.03.21-09.17.47:987][  3]LogContentValidation: Display: Starting to validate 3 assets (0 associated objects such as actors)
[2026.03.21-09.17.47:987][  3]LogContentValidation: Additional assets added for validation by 0 validators:
[2026.03.21-09.17.47:987][  3]AssetCheck: /Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP Validating asset
[2026.03.21-09.17.47:987][  3]AssetCheck: /Game/CityPark/SnowSystem/RVT_MVP/M_RVT_DebugWriter_MVP Validating asset
[2026.03.21-09.17.47:987][  3]AssetCheck: /Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_LandscapeRuntimeFix Validating asset
[2026.03.21-09.17.47:987][  3]LogContentValidation: Validated asset counts for 1 validators:
[2026.03.21-09.17.47:987][  3]LogContentValidation:   /Script/DataValidation.EditorValidator_Localization : 3
[2026.03.21-09.17.53:742][  3]LogHttp: Warning: HTTP request timed out after 3.00 seconds URL=https://www.google.com/generate_204
[2026.03.21-09.17.53:742][  3]LogWindows: Error: === Critical error: ===
[2026.03.21-09.17.53:742][  3]LogWindows: Error: 
[2026.03.21-09.17.53:742][  3]LogWindows: Error: Unhandled Exception: EXCEPTION_ACCESS_VIOLATION reading address 0x0000000000000000
[2026.03.21-09.17.53:742][  3]LogWindows: Error: 
[2026.03.21-09.17.53:742][  3]LogWindows: Error: [Callstack] 0x00007ff98d0a1eee UnrealEditor-Engine.dll!UnknownFunction []
[2026.03.21-09.17.53:742][  3]LogWindows: Error: [Callstack] 0x00007ff9cd4a6fb0 UnrealEditor-UnrealEd.dll!UnknownFunction []
[2026.03.21-09.17.53:742][  3]LogWindows: Error: [Callstack] 0x00007ff9cdffe396 UnrealEditor-UnrealEd.dll!UnknownFunction []
[2026.03.21-09.17.53:742][  3]LogWindows: Error: [Callstack] 0x00007ff76f4e4da6 UnrealEditor-Cmd.exe!UnknownFunction []
[2026.03.21-09.17.53:742][  3]LogWindows: Error: [Callstack] 0x00007ff76f500bfe UnrealEditor-Cmd.exe!UnknownFunction []
[2026.03.21-09.17.53:742][  3]LogWindows: Error: [Callstack] 0x00007ff76f500d0a UnrealEditor-Cmd.exe!UnknownFunction []
[2026.03.21-09.17.53:742][  3]LogWindows: Error: [Callstack] 0x00007ff76f504590 UnrealEditor-Cmd.exe!UnknownFunction []
[2026.03.21-09.17.53:742][  3]LogWindows: Error: [Callstack] 0x00007ff76f515be4 UnrealEditor-Cmd.exe!UnknownFunction []
[2026.03.21-09.17.53:742][  3]LogWindows: Error: [Callstack] 0x00007ff76f5182f6 UnrealEditor-Cmd.exe!UnknownFunction []
[2026.03.21-09.17.53:742][  3]LogWindows: Error: [Callstack] 0x00007ffa686fe8d7 KERNEL32.DLL!UnknownFunction []
[2026.03.21-09.17.53:742][  3]LogWindows: Error: 
[2026.03.21-09.17.53:751][  3]LogExit: Executing StaticShutdownAfterError
[2026.03.21-09.17.53:752][  3]LogWindows: FPlatformMisc::RequestExit(1, LaunchWindowsStartup.ExceptionHandler)
[2026.03.21-09.17.53:752][  3]LogWindows: FPlatformMisc::RequestExitWithStatus(1, 3, LaunchWindowsStartup.ExceptionHandler)
[2026.03.21-09.17.53:752][  3]LogCore: Engine exit requested (reason: Win RequestExit)
~~~

### Latest Blueprint automation log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\apply_right_plow_berm.json
~~~text
{
  "mode": "apply_right_plow_berm",
  "writer_material": "/Game/CityPark/SnowSystem/RVT_MVP/M_RVT_DebugWriter_MVP",
  "receiver_parent": "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP",
  "landscape_mi": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_LandscapeRuntimeFix",
  "receiver_rebuilt": true,
  "writer_saved": true,
  "landscape_mi_saved": true,
  "writer_num_expressions": 35,
  "landscape_mi_scalar_values": {
    "HeightContrast": 1.0,
    "RightBermRaise": 12.0,
    "RightBermSharpness": 1.149999976158142
  },
  "writer_connect_basecolor": {
    "ok": true,
    "src": "",
    "dst": "Base Color"
  },
  "writer_connect_specular": {
    "ok": true,
    "src": "",
    "dst": "Specular"
  },
  "writer_connect_roughness": {
    "ok": true,
    "src": "",
    "dst": "Roughness"
  },
  "writer_connect_normal": {
    "ok": true,
    "src": "",
    "dst": "Normal"
  },
  "writer_connect_mask": {
    "ok": true,
    "src": "",
    "dst": "Mask"
  },
  "error": ""
}
~~~

## Open questions

- Need to verify that tiered RVT stamp planes with small Z offsets deterministically override lower tiers validate that first-pass clearing remains visible while second/third pass intensify it.

