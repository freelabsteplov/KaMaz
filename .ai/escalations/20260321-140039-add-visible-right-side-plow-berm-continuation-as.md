# Senior Escalation Packet

- Generated: 2026-03-21 14:00:39 +03:00
- Project root: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner
- Branch: snow-source-truth-snapshot

## Goal

Add visible right-side plow berm continuation as 20 percent extension with +100 height

## Hypothesis

The current berm uses only a right-edge mask inside the plow footprint, so it can feel like broad height growth. We can make the berm read as a true continuation by widening the writer plane to 120 percent, shifting it right by 10 percent of plow width, keeping the clear zone aligned to original width, and drawing a dedicated debug berm box.

## Files to touch

- Source/Kamaz_Cleaner/Public/Snow/SnowRuntimeTrailBridgeComponent.h
- Source/Kamaz_Cleaner/Private/Snow/SnowRuntimeTrailBridgeComponent.cpp
- Pyton_script/unreal_tools/apply_repeat_clearing_accumulation.py
- Pyton_script/unreal_tools/apply_right_plow_berm.py
- AGENTS.md
- Content/Automation/BP_BlueprintAutomationSmoke_2604CC05413414FEA1772CA218CB3AAF.uasset
- Content/Automation/BP_BlueprintAutomationSmoke_A124B8A544DDC511CF7D2EBFB09A145A.uasset
- Content/BPs/BP_KamazGameMode_HandlingAudit.uasset
- Content/CityPark/Kamaz/model/Front_wheels_HandlingAudit.uasset
- Content/CityPark/Kamaz/model/KamazBP_HandlingAudit.uasset
- Content/CityPark/Kamaz/model/Rear_wheels_HandlingAudit.uasset
- Content/CityPark/SnowSystem/BrushMaterials/MI_Snow_PlowBrush_BoxSafe_350x50x100.uasset
- Content/CityPark/SnowSystem/BrushMaterials/MI_Snow_PlowBrush_BoxSafe_DebugHuge.uasset
- Content/CityPark/SnowSystem/BrushMaterials/M_RT_FullscreenGreen_Test.uasset
- Content/CityPark/SnowSystem/BrushMaterials/M_RVT_SnowWriter_Test.uasset
- Content/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush_BoxSafe.uasset
- Content/CityPark/SnowSystem/M_RVT_SnowWriter_Test.uasset
- Content/CityPark/SnowSystem/M_RVT_SnowWriter_Test1.uasset
- Content/CityPark/SnowSystem/M_RVT_SnowWriter_Test2.uasset
- Content/CityPark/SnowSystem/M_SnowTestMVP_Landscape1.uasset
- Content/CityPark/SnowSystem/RVT_MVP/LI_SnowPaint.uasset
- Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP.uasset
- Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K.uasset
- Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_Landscape.uasset
- Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_LandscapeRuntimeFix.uasset
- Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_Landscape_SoftSeam.uasset
- Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_RoadEdgeBlend.uasset
- Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P2_2K.uasset
- Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P3_2K.uasset
- Content/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P4_2K.uasset

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
no tracked diff
~~~

## Recent build/log excerpts

### Latest AI build log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\.ai\logs\build_editor_20260321-133330.log
~~~text
Using bundled DotNet SDK version: 8.0.412 win-x64
Running UnrealBuildTool: dotnet "..\..\Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.dll" Kamaz_CleanerEditor Win64 Development "-Project=C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Kamaz_Cleaner.uproject" -WaitMutex -NoHotReloadFromIDE
Log file: C:\Users\post\AppData\Local\UnrealBuildTool\Log.txt
Using 'git status' to determine working set for adaptive non-unity build (C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner).
Parsing headers for Kamaz_CleanerEditor
  Running Internal UnrealHeaderTool "C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Kamaz_Cleaner.uproject" "C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Intermediate\Build\Win64\Kamaz_CleanerEditor\Development\Kamaz_CleanerEditor.uhtmanifest" -WarningsAsErrors -installed
UHT processed Kamaz_CleanerEditor in 2.7883263 seconds (0 files written)
Building Kamaz_CleanerEditor...
Using Visual Studio 2022 14.44.35214 toolchain (C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207) and Windows 10.0.22621.0 SDK (C:\Program Files (x86)\Windows Kits\10).
[Adaptive Build] Excluded from Kamaz_Cleaner unity file: SnowRuntimeTrailBridgeActor.cpp, SnowRuntimeTrailBridgeComponent.cpp, SnowSplineRoadActor.cpp, SnowFXManagerV1.cpp, SnowRuntimeBootstrapV1.cpp, SnowStateManagerV1.cpp, SnowWheelTelemetryV1Component.cpp, KamazStartupHoldComponent.cpp
[Adaptive Build] Excluded from BlueprintAutomationEditor unity file: BlueprintAutomationPythonBridge.cpp
Determining max actions to execute in parallel (24 physical cores, 32 logical cores)
  Executing up to 24 processes, one per physical core
  Requested 1.5 GB memory per action, 26.76 GB available: limiting max parallel actions to 17
Using Unreal Build Accelerator local executor to run 6 action(s)
  Storage capacity 40Gb
---- Starting trace: 260321_133333 ----
UbaSessionServer - Disable remote execution (remote sessions will finish current processes)
[1/6] Compile [x64] SnowRuntimeTrailBridgeActor.cpp
[2/6] Compile [x64] Module.Kamaz_Cleaner.gen.cpp
[3/6] Compile [x64] SnowRuntimeTrailBridgeComponent.cpp
[4/6] Link [x64] UnrealEditor-Kamaz_Cleaner.lib
[5/6] Link [x64] UnrealEditor-Kamaz_Cleaner.dll
[6/6] WriteMetadata Kamaz_CleanerEditor.target [NoUba]

Trace written to file C:/Users/post/AppData/Local/UnrealBuildTool/Log.uba with size 4.0kb
Total time in Unreal Build Accelerator local executor: 3.60 seconds

Result: Succeeded
Total execution time: 7.14 seconds
~~~

### Latest Unreal editor log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\Logs\Kamaz_Cleaner.log
~~~text
[2026.03.21-10.46.52:551][437]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:551][437]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:551][437]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:551][437]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:551][437]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:551][437]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:551][437]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:551][437]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:551][437]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:551][437]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:551][437]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:559][438]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:559][438]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:559][438]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:559][438]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:559][438]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:559][438]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:559][438]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:559][438]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.46.52:559][438]LogStaticMesh: Warning: Invalid material [Spruce_] used on Nanite static mesh [1_Cube_007]. Only opaque or masked blend modes are currently supported, [BLEND_TranslucentGreyTransmittance] blend mode was specified. (NOTE: "Disallow Nanite" on static mesh components can be used to suppress this warning and forcibly render the object as non-Nanite.)
[2026.03.21-10.47.17:002][764]LogEOSSDK: LogEOS: Updating Product SDK Config, Time: 358.087280
[2026.03.21-10.47.17:227][791]LogEOSSDK: LogEOS: SDK Config Product Update Request Completed - No Change
[2026.03.21-10.47.17:227][791]LogEOSSDK: LogEOS: ScheduleNextSDKConfigDataUpdate - Time: 358.304718, Update Interval: 354.567108
[2026.03.21-10.53.14:803][923]LogEOSSDK: LogEOS: Updating Product SDK Config, Time: 715.888245
[2026.03.21-10.53.15:803][926]LogEOSSDK: LogEOS: SDK Config Product Update Request Completed - No Change
[2026.03.21-10.53.15:803][926]LogEOSSDK: LogEOS: ScheduleNextSDKConfigDataUpdate - Time: 716.554932, Update Interval: 322.628876
[2026.03.21-10.56.33:929][902]LogUObjectHash: Compacting FUObjectHashTables data took   0.47ms
[2026.03.21-10.56.33:980][902]LogStall: Shutdown...
[2026.03.21-10.56.33:985][902]LogStall: Shutdown complete.
[2026.03.21-10.56.34:026][902]LogSlate: Window 'Message Log' being destroyed
[2026.03.21-10.56.34:028][902]LogSlate: Window 'Kamaz_Cleaner - Unreal Editor' being destroyed
[2026.03.21-10.56.34:079][902]Cmd: QUIT_EDITOR
[2026.03.21-10.56.34:079][903]LogCore: Engine exit requested (reason: UUnrealEdEngine::CloseEditor())
[2026.03.21-10.56.34:084][903]LogCore: Engine exit requested (reason: EngineExit() was called; note: exit was already requested)
[2026.03.21-10.56.34:084][903]LogStaticMesh: Abandoning remaining async distance field tasks for shutdown
[2026.03.21-10.56.34:084][903]LogStaticMesh: Abandoning remaining async card representation tasks for shutdown
[2026.03.21-10.56.34:159][903]LogWorld: UWorld::CleanupWorld for SnowTest_Level, bSessionEnded=true, bCleanupResources=true
[2026.03.21-10.56.34:160][903]LogSlate: InvalidateAllWidgets triggered.  All widgets were invalidated
[2026.03.21-10.56.34:172][903]LogWorld: UWorld::CleanupWorld for MoscowEA5, bSessionEnded=true, bCleanupResources=true
[2026.03.21-10.56.34:172][903]LogSlate: InvalidateAllWidgets triggered.  All widgets were invalidated
[2026.03.21-10.56.34:183][903]LogWorld: UWorld::CleanupWorld for Clumbi_Tverskay, bSessionEnded=true, bCleanupResources=true
[2026.03.21-10.56.34:183][903]LogSlate: InvalidateAllWidgets triggered.  All widgets were invalidated
[2026.03.21-10.56.34:193][903]LogTedsSettings: UTedsSettingsEditorSubsystem::Deinitialize
[2026.03.21-10.56.34:193][903]LogLevelSequenceEditor: LevelSequenceEditor subsystem deinitialized.
[2026.03.21-10.56.34:195][903]LogRuntimeTelemetry: Recording EnginePreExit events
[2026.03.21-10.56.34:198][903]LogAnalytics: Display: [UEEditor.Rocket.Release] AnalyticsET::EndSession
[2026.03.21-10.56.35:145][903]LogAudio: Display: Beginning Audio Device Manager Shutdown (Module: AudioMixerXAudio2)...
[2026.03.21-10.56.35:145][903]LogAudio: Display: Destroying 1 Remaining Audio Device(s)...
[2026.03.21-10.56.35:145][903]LogAudio: Display: Audio Device unregistered from world 'SnowTest_Level'.
[2026.03.21-10.56.35:145][903]LogAudio: Display: Shutting down audio device while 1 references to it are still alive. For more information, compile with INSTRUMENT_AUDIODEVICE_HANDLES.
[2026.03.21-10.56.35:170][903]LogAudioMixer: Display: FMixerPlatformXAudio2::StopAudioStream() called. InstanceID=1, StreamState=4
[2026.03.21-10.56.35:172][903]LogAudioMixer: Display: FMixerPlatformXAudio2::StopAudioStream() called. InstanceID=1, StreamState=2
[2026.03.21-10.56.35:176][903]LogAudioMixer: Deinitializing Audio Bus Subsystem for audio device with ID -1
[2026.03.21-10.56.35:176][903]LogAudio: Display: Audio Device Manager Shutdown
[2026.03.21-10.56.35:180][903]LogSlate: Slate User Destroyed.  User Index 0, Is Virtual User: 0
[2026.03.21-10.56.35:180][903]LogExit: Preparing to exit.
[2026.03.21-10.56.35:212][903]LogUObjectHash: Compacting FUObjectHashTables data took   0.46ms
[2026.03.21-10.56.36:137][903]LogEditorDataStorage: Deinitializing
[2026.03.21-10.56.36:239][903]LogDemo: Cleaned up 0 splitscreen connections, owner deletion: enabled
[2026.03.21-10.56.36:252][903]LogExit: Editor shut down
[2026.03.21-10.56.36:254][903]LogExit: Transaction tracking system shut down
[2026.03.21-10.56.36:466][903]LogExit: Object subsystem successfully closed.
[2026.03.21-10.56.36:551][903]LogShaderCompilers: Display: Shaders left to compile 0
[2026.03.21-10.56.36:741][903]LogMemoryProfiler: Shutdown
[2026.03.21-10.56.36:741][903]LogNetworkingProfiler: Shutdown
[2026.03.21-10.56.36:741][903]LoadingProfiler: Shutdown
[2026.03.21-10.56.36:741][903]LogTimingProfiler: Shutdown
[2026.03.21-10.56.36:742][903]LogChaosVDEditor: [FChaosVDExtensionsManager::UnRegisterExtension] UnRegistering CVD Extension [FChaosVDGenericDebugDrawExtension] ...
[2026.03.21-10.56.36:742][903]LogChaosVDEditor: [FChaosVDExtensionsManager::UnRegisterExtension] UnRegistering CVD Extension [FChaosVDAccelerationStructuresExtension] ...
[2026.03.21-10.56.36:982][903]LogWebBrowser: Deleting browser for Url=https://editor.unrealengine.com/en-US/get-started-with-unreal-engine.
[2026.03.21-10.56.37:038][903]LogChaosDD: Chaos Debug Draw Shutdown
[2026.03.21-10.56.37:039][903]RenderDocPlugin: plugin has been unloaded.
[2026.03.21-10.56.37:042][903]LogHttp: Warning: [FHttpManager::Shutdown] Unbinding delegates for 1 outstanding Http Requests:
[2026.03.21-10.56.37:042][903]LogHttp: Warning: 	verb=[POST] url=[https://datarouter.ol.epicgames.com/datarouter/api/v1/public/data?SessionID=%7BD7AC4C40-4FF2-3B67-7ED2-AF81DA29CD58%7D&AppID=UEEditor.Rocket.Release&AppVersion=5.7.4-51494982%2B%2B%2BUE5%2BRelease-5.7&UserID=cf16a88d450dfab35e2a9f80ed544f22%7C1538f1a5dc2d49859adeab46ba6210a3%7Ce53cff49-76a5-434a-99a0-c32d54467603&AppEnvironment=datacollector-binary&UploadType=eteventstream] refs=[2] status=Processing
[2026.03.21-10.56.38:113][903]LogEOSShared: FEOSSDKManager::Shutdown EOS_Shutdown Result=[EOS_Success]
[2026.03.21-10.56.38:118][903]LogNFORDenoise: NFORDenoise function shutting down
[2026.03.21-10.56.38:119][903]LogPakFile: Destroying PakPlatformFile
[2026.03.21-10.56.38:371][903]LogD3D12RHI: ~FD3D12DynamicRHI
[2026.03.21-10.56.38:416][903]LogExit: Exiting.
[2026.03.21-10.56.38:442][903]Log file closed, 03/21/26 13:56:38
~~~

### Latest Blueprint automation log
- File: C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\apply_repeat_clearing_accumulation.json
~~~text
{
  "mode": "apply_repeat_clearing_accumulation",
  "writer_material": "/Game/CityPark/SnowSystem/RVT_MVP/M_RVT_DebugWriter_MVP",
  "receiver_parent": "/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP",
  "landscape_mi": "/Game/CityPark/SnowSystem/RVT_MVP/MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_LandscapeRuntimeFix",
  "saved": true,
  "receiver_rebuilt": true,
  "landscape_mi_saved": true,
  "num_expressions": 35,
  "connect_basecolor": {
    "ok": true,
    "src": "",
    "dst": "Base Color"
  },
  "connect_specular": {
    "ok": true,
    "src": "",
    "dst": "Specular"
  },
  "connect_roughness": {
    "ok": true,
    "src": "",
    "dst": "Roughness"
  },
  "connect_normal": {
    "ok": true,
    "src": "",
    "dst": "Normal"
  },
  "connect_mask": {
    "ok": true,
    "src": "",
    "dst": "Mask"
  },
  "error": ""
}
~~~

## Open questions

- Need to confirm visual side orientation in-game if UV/right-vector orientation is flipped we will invert the continuation side in one follow-up pass.

