# Senior Escalation Packet

- Generated: 2026-03-22 15:41 +03:00
- Project root: `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner`

## Goal

Keep the restored snow-clearing and right-berm behavior as the default active path, and improve snow visuals so thin snow looks cheaper/translucent-like while added berm snow shifts toward a dirty beige tint.

## Hypothesis

True translucent snow on landscape/spline receivers would be too expensive and risky for the current opaque RVT workflow. A cheap approximation can be achieved inside the existing opaque receiver material by:

1. driving a thickness-based underlay blend from the remaining snow mask
2. tinting berm-added snow through the existing berm signal

This preserves the current runtime trail system and avoids a costly blend-mode change.

## Files to touch

- `Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_berm.py`
- `Pyton_script/unreal_tools/apply_right_plow_berm.py`

## Ordered steps

1. Keep the current `Roughness` berm-channel RVT semantics as the default active path.
2. Extend the berm-capable receiver parent with a thin-snow visual-opacity approximation based on remaining snow thickness.
3. Add a dirty-berm tint path driven by the existing berm mask.
4. Rebuild the active receiver/writer materials through the existing wrapper flow.
5. Reload `SnowTest_Level` headlessly and confirm the new scalar parameters are present on the active receiver chain.

## Invariants / Do-not-break rules

- Do not switch the receiver to true translucent blend mode.
- Keep `Mask` as clear strength.
- Keep `Specular` as repeat-depth accumulation.
- Keep `Roughness` as berm signal.
- Preserve current writer/receiver compatibility with `SnowRuntimeTrailBridgeComponent`.

## Validation

- Ran `Tools/AI/run_smoke.ps1` headless on `/Game/Maps/MoscowEA5` with `apply_right_plow_berm.py`.
- Rebuilt `M_SnowReceiver_RVT_Height_MVP` with:
  - `ThinSnowMinVisualOpacity`
  - `ThinSnowUnderColor`
  - `DirtyBermTintStrength`
  - `DirtyBermColor`
- Re-ran `Tools/AI/run_smoke.ps1` headless on `/Game/CityPark/SnowSystem/SnowTest_Level` with `inspect_current_snowtest_receivers.py`.

Validation outcome:

- `rebuild_m_snowreceiver_rvt_height_mvp_berm.json` reports `saved: true`, `num_expressions: 43`.
- `apply_right_plow_berm.json` reports `receiver_rebuilt: true`, `writer_saved: true`, `landscape_mi_saved: true`.
- `inspect_current_snowtest_receivers.json` shows `ThinSnowMinVisualOpacity` and `DirtyBermTintStrength` on all active `M_SnowReceiver_RVT_Height_MVP` chains in `SnowTest_Level`.
- In `.ai/logs/run_smoke_engine_20260322-153931.log`, there is no active compile failure for `M_SnowReceiver_RVT_Height_MVP` or `M_RVT_DebugWriter_MVP`.

## Rollback notes

- Revert the receiver rebuild script and re-run `apply_right_plow_berm.py` to restore the prior visual look while keeping the working berm channel semantics.
- No gameplay or trail-bridge code rollback is required for this visual pass.

## Current diff summary

- `Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_berm.py`
  - added a thin-snow underlay blend that approximates translucency without changing blend mode
  - added dirty-berm tint controls
  - kept the `Roughness`-based berm read path
- `Pyton_script/unreal_tools/apply_right_plow_berm.py`
  - continues to rebuild/apply the now-default berm-capable material chain

## Relevant log excerpts

From `.ai/logs/run_smoke_engine_20260322-153646.log`:

- receiver and writer save successfully after the visual graph expansion
- active receiver/writer assets validate successfully

From `.ai/logs/run_smoke_engine_20260322-153931.log`:

- `SnowTest_Level` loads with the updated receiver chain
- active receiver materials expose `ThinSnowMinVisualOpacity`
- active receiver materials expose `DirtyBermTintStrength`

## Open questions

- This validation confirms the material graph and active parameter chain, but the exact artistic strength of the thin-snow underlay and dirty-berm tint still needs one live eyeball pass in Editor.
- An unrelated compile warning for `BrushMaterials/M_Snow_WheelBrush` still appears in the log, but it is outside the active road/berm receiver path.
