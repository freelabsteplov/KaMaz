# Road2 Snow Pipeline Search Map

This repository now keeps the Road2 snow pipeline code, automation scripts, and selected text diagnostics in Git so GitHub search can answer the three main investigation questions quickly.

## Code Roots

- `Source/Kamaz_Cleaner/Private/Snow/`
- `Source/Kamaz_Cleaner/Public/Snow/`
- `Pyton_script/unreal_tools/`
- `Config/DefaultEngine.ini`
- `Config/DefaultGame.ini`
- `Plugins/BlueprintAutomationEditor/Source/BlueprintAutomationEditor/`
- `Tools/AI/`

## Search-First Entry Points

Use these searches first in GitHub code search:

- `PlowLiftHeightForNoEffect`
- `bEnableRuntimeReceiverHeightControl`
- `RuntimeHeightAmplitudeWhenActive`
- `RuntimeHeightAmplitudeWhenInactive`
- `VisualClearMaskStrength`
- `InvertClearMask`
- `RevealOpacityThreshold`
- `Road2 writer policy`
- `CANONICAL_ROAD2_WRITERS`
- `BLOCKED_ROAD2_WRITERS`
- `MarkPersistentPlowWriter`
- `SnowRuntimeTrailBridge`
- `receiver`
- `carrier`

## Blueprint And Material Text Exports

The search-friendly exports and probes live in `Saved/BlueprintAutomation/`.

Key files:

- `Saved/BlueprintAutomation/plowbrush_component_graph.json`
- `Saved/BlueprintAutomation/plowbrush_component_road2_snow_slice.json`
- `Saved/BlueprintAutomation/kamazbp_eventgraph_full.json`
- `Saved/BlueprintAutomation/kamazbp_road2_snow_slice.json`
- `Saved/BlueprintAutomation/trace_m_snowreceiver_rvt_height_mvp.json`
- `Saved/BlueprintAutomation/inspect_m_snowreceiver_root_chains.json`
- `Saved/BlueprintAutomation/inspect_m_snowreceiver_lerp_inputs.json`
- `Saved/BlueprintAutomation/road2_snow_pipeline_manifest.json`

## Question Guide

To find where snow opacity is globally suppressed when the plow goes down:

- inspect `Source/Kamaz_Cleaner/Public/Snow/SnowRuntimeTrailBridgeComponent.h`
- inspect `Source/Kamaz_Cleaner/Private/Snow/SnowRuntimeTrailBridgeComponent.cpp`
- search `PlowLiftHeightForNoEffect`, `VisualClearMaskStrength`, `RevealOpacityThreshold`, `Opacity`, `clear mask`
- inspect `Saved/BlueprintAutomation/trace_m_snowreceiver_rvt_height_mvp.json`
- inspect `Saved/BlueprintAutomation/inspect_m_snowreceiver_root_chains.json`
- inspect `Saved/BlueprintAutomation/plowbrush_component_road2_snow_slice.json`
- inspect `Saved/BlueprintAutomation/kamazbp_road2_snow_slice.json`

To find duplicated directives across Blueprint, C++, and Python:

- compare `Saved/BlueprintAutomation/plowbrush_component_graph.json`
- compare `Saved/BlueprintAutomation/kamazbp_eventgraph_full.json`
- compare `Source/Kamaz_Cleaner/Private/Snow/`
- compare `Pyton_script/unreal_tools/`
- search `HeightAmplitude`, `BaselineSnowCoverage`, `InvertClearMask`, `carrier`, `receiver`, `trail`

To find the exact writer that breaks Road2:

- inspect `Pyton_script/unreal_tools/road2_writer_policy.py`
- inspect `Saved/BlueprintAutomation/road2_snow_pipeline_manifest.json`
- inspect `Saved/BlueprintAutomation/apply_road_height_carrier_for_road2.json`
- inspect `Saved/BlueprintAutomation/apply_road2_material_only_pass.json`
- inspect `Saved/BlueprintAutomation/cleanup_legacy_plow_rt_writer.json`
- inspect `Saved/BlueprintAutomation/probe_spawned_plow_writer_runtime.json`
- inspect `.ai/escalations/20260326_road2_rvt_receiver_recovery.md`

## Notes

- `Saved/BlueprintAutomation/` intentionally contains only text diagnostics in Git. PNG captures and binary backups stay out of version control.
- The large raw action indexes are not required for the Road2 search path and are intentionally not part of the curated Git slice.
