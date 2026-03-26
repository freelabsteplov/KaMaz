# Senior Escalation Packet

- Generated: 2026-03-22 13:12 +03:00
- Project root: `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner`

## Goal

Restore the missing right-side plow berm / green track behavior after blue clear-box snow removal was already working again in `SnowTest_Level`.

## Hypothesis

The berm path was structurally enabled in C++, but the receiver material graph still failed to read the berm signal from the RVT. The first attempt stored berm data in RVT `BaseColor` and read it through a `ComponentMask`, but that graph compiled invalidly and fell back to `Default Material`, so the green berm box produced no visible snow buildup.

## Files to touch

- `Pyton_script/unreal_tools/apply_right_plow_berm.py`
- `Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_berm.py`
- `Pyton_script/unreal_tools/trace_m_snow_plow_brush_graph.py`

## Ordered steps

1. Reproduce the missing berm path with wrapper-based headless runs.
2. Confirm whether the failure is in gameplay/runtime code or in RVT writer/receiver material compilation.
3. Rebuild the berm-capable receiver parent and writer materials on a safe non-`SnowTest_Level` map to avoid in-use asset deletion failures.
4. Remove the brittle `BaseColor -> ComponentMask` berm read path.
5. Store the berm signal in RVT `Roughness` and read it back as a scalar in the receiver.
6. Re-open `SnowTest_Level` in a fresh headless session and confirm the active writer/receiver chain compiles cleanly.

## Invariants / Do-not-break rules

- Do not change truck gameplay/input logic for this fix.
- Keep `Mask` reserved for clear strength.
- Keep `Specular` reserved for repeat-depth accumulation.
- Use project wrappers for all run/log validation.
- Preserve the already restored blue clearing path while reintroducing berm behavior.

## Validation

- Ran `Tools/AI/run_smoke.ps1` headless on `/Game/Maps/MoscowEA5` with `apply_right_plow_berm.py`.
- Confirmed earlier berm build failures were material-graph failures, not trail-component setup failures.
- Rebuilt the receiver to use RVT `Roughness` for berm signal instead of `BaseColor` plus `ComponentMask`.
- Re-ran `Tools/AI/run_smoke.ps1` headless on `/Game/Maps/MoscowEA5` with the updated berm scripts.
- Re-ran `Tools/AI/run_smoke.ps1` headless on `/Game/CityPark/SnowSystem/SnowTest_Level` with `inspect_current_snowtest_receivers.py`.

Validation outcome:

- In `.ai/logs/run_smoke_engine_20260322-130619.log`, the rebuilt `M_SnowReceiver_RVT_Height_MVP` no longer emits the previous late compile failure after material regeneration.
- In `.ai/logs/run_smoke_engine_20260322-130900.log`, there is no active compile warning for `M_SnowReceiver_RVT_Height_MVP`, `MI_SnowReceiver_RVT_Height_MVP_*`, or `M_RVT_DebugWriter_MVP`.
- `inspect_current_snowtest_receivers.json` shows `SnowTest_Level` still uses the intended receiver chain and the trail bridge still points to `M_RVT_DebugWriter_MVP`.
- `apply_right_plow_berm.json` and `rebuild_m_snowreceiver_rvt_height_mvp_berm.json` show successful rebuild/save with berm parameters present.

## Rollback notes

- Revert only the Python helper changes if berm behavior needs to be backed out.
- If a rollback is required urgently, the clear-only path from the previous recovery can be restored by switching back to the clean receiver rebuild script and removing berm-specific scalar updates.

## Current diff summary

- `Pyton_script/unreal_tools/apply_right_plow_berm.py`
  - writer now stores berm presence in RVT `Roughness`
  - keeps `Mask` for clear and `Specular` for repeat-depth
- `Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_berm.py`
  - receiver now reads berm from RVT `Roughness`
  - removes the invalid `ComponentMask` branch
- `Pyton_script/unreal_tools/trace_m_snow_plow_brush_graph.py`
  - can now trace an arbitrary material via `KAMAZ_MATERIAL_PATH`

## Relevant log excerpts

From `.ai/logs/run_smoke_engine_20260322-130127.log`:

- `M_SnowReceiver_RVT_Height_MVP.uasset: Failed to compile Material...`
- `(Node ComponentMask) Missing ComponentMask input`

From `.ai/logs/run_smoke_engine_20260322-130619.log`:

- receiver and writer packages save successfully after the `Roughness` berm rewrite
- no late post-rebuild `ComponentMask` failure is emitted for the active receiver material

From `.ai/logs/run_smoke_engine_20260322-130900.log`:

- `SnowTest_Level` loads with the berm-capable writer/receiver chain
- no active compile failure is emitted for `M_SnowReceiver_RVT_Height_MVP` or `M_RVT_DebugWriter_MVP`

## Open questions

- The old backup asset `M_SnowReceiver_RVT_Height_MVP_BermBackup` still represents a broken intermediate graph and can still produce warning noise if loaded directly.
- This validation proves the active material chain compiles cleanly again, but the final visual confirmation of berm buildup should still be checked once in Editor with the plow driving over `SnowTest_Level`.
