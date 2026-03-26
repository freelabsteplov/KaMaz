# Senior Escalation Packet

- Generated: 2026-03-22 12:28 +03:00
- Project root: `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner`
- Branch: `snow-source-truth-snapshot`

## Goal

Understand why the snow plow in the current RVT snow runtime visually adds snow instead of clearing it, and restore a safe working state for `SnowTest_Level`.

## Hypothesis

The visible failure was not a single issue. Two defects stacked together:

1. `M_RVT_DebugWriter_MVP` had been rebuilt into an invalid material graph by the repeat-clearing automation path, so the active RVT writer could fall back to `Default Material`.
2. Road actors in `SnowTest_Level` had been rebound to duplicated `*_RoadEdgeBlend` receivers whose generated parent graph was also invalid.

This combination can easily look like "snow is added instead of removed" because the active writer/receiver pair is no longer speaking a valid, consistent material graph.

## Files to touch

- `Tools/AI/run_smoke.ps1`
- `Pyton_script/unreal_tools/apply_road_edge_blend_material.py`
- `Pyton_script/unreal_tools/apply_road_edge_blend_inplace.py`
- `Pyton_script/unreal_tools/inspect_current_snowtest_receivers.py`
- `Pyton_script/unreal_tools/restore_snowtest_road_base_materials.py`

## Ordered steps

1. Reproduce the failure against `SnowTest_Level` with project wrappers only.
2. Confirm whether the active writer compiles and whether roads are bound to base receivers or `RoadEdgeBlend` duplicates.
3. Restore a known-good clear writer on `M_RVT_DebugWriter_MVP`.
4. Rebind `SnowSplineRoad_*` actors to the original base `MI_SnowReceiver_RVT_Height_MVP_*` instances.
5. Re-run inspection and confirm the active trail bridge and road actors now point to the intended assets.
6. Keep `RoadEdgeBlend` as a secondary follow-up and avoid using it on the active map until its graph is valid again.

## Invariants / Do-not-break rules

- Do not change gameplay code for the truck/input path.
- Use project wrappers for run/log validation.
- Keep changes narrow and reversible.
- Prefer restoring a known-good working asset chain over broad RVT redesign.

## Validation

- Ran `Tools/AI/run_smoke.ps1` headless against `/Game/CityPark/SnowSystem/SnowTest_Level`.
- Ran `apply_soft_rvt_stamp_edges.py` through the wrapper to restore the known-good writer.
- Ran `restore_snowtest_road_base_materials.py` through the wrapper to rebind road actors to base receiver instances.
- Ran `inspect_current_snowtest_receivers.py` through the wrapper to capture current writer/receiver assignments.

Validation outcome:

- The latest inspection shows `SnowRuntimeTrailBridgeComponent` uses `M_RVT_DebugWriter_MVP`.
- `SnowSplineRoad_MVP`, `SnowSplineRoad_V1_Original_MVP`, and `SnowSplineRoad_V3_Narrow_MVP` now point back to:
  - `MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K`
  - `MI_SnowReceiver_RVT_Height_MVP_Tile8`
  - `MI_SnowReceiver_RVT_Height_MVP_V3_Narrow_Tile4`
- In the latest inspect run, there is no compile warning for `M_RVT_DebugWriter_MVP`.
- `MapCheck` finishes cleanly after rebuild with `0 Error(s), 0 Warning(s)`.

## Rollback notes

- To roll back the current recovery state, revert only the helper scripts and asset changes made by the wrapper runs.
- If roads must be returned to the experimental edge blend path later, do it only after revalidating the `RoadEdgeBlend` material graph.

## Current diff summary

Relevant working changes:

- `Tools/AI/run_smoke.ps1`
  - added `-PythonScriptPath` support
  - switched to a safer `Start-Process` wrapper flow
  - writes stdout/stderr/engine logs under `.ai/logs`
  - normalizes Python script paths to forward slashes so `-ExecutePythonScript` works with paths like `\\restore...`
- `Pyton_script/unreal_tools/restore_snowtest_road_base_materials.py`
  - new recovery script that rebinds road actors to base receiver instances
- `Pyton_script/unreal_tools/apply_road_edge_blend_material.py`
  - refreshes duplicates from source and now extracts the V channel via `ComponentMask` instead of invalid `TextureCoordinate.G`
- `Pyton_script/unreal_tools/apply_road_edge_blend_inplace.py`
  - same `ComponentMask` fix for the in-place path

## Relevant log excerpts

From `.ai/logs/run_smoke_engine_20260322-122043.log`:

- `M_RVT_DebugWriter_MVP.uasset: Failed to compile Material...`
- `(Node Saturate) Missing Saturate input`

From `.ai/logs/run_smoke_engine_20260322-122613.log`:

- `restore_snowtest_road_base_materials.py` completed and saved the map
- no active writer compile warning was emitted

From `.ai/logs/run_smoke_engine_20260322-122650.log`:

- roads are bound to base `MI_SnowReceiver_RVT_Height_MVP_*`
- `Map check complete: 0 Error(s), 0 Warning(s)`

## Open questions

- `M_SnowReceiver_RVT_Height_MVP_RoadEdgeBlend` still exists and still compiles invalidly if loaded. It is not active on roads now, but the edge-blend feature itself still needs a dedicated follow-up.
- `SnowRuntimeTrailBridgeComponent` still advertises repeat-clearing-related properties (`bEnableRepeatClearingAccumulation`, `RepeatAccumulationMaxPasses`). If that feature is still desired, it should be rebuilt from the restored working writer, not from the broken `apply_repeat_clearing_accumulation.py` state.
