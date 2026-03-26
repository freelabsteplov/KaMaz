# Goal

Stop the plow from producing glitchy ripple-like snow growth on `SnowTest_Level`, keep the road clear zone visually dirty/grey instead of warm brown, and preserve stable plow stamping.

# Hypothesis

The active spline-road receivers were too low-poly for aggressive runtime `WPO`, so negative runtime height on `SnowSplineRoad*` was turning the clear mask into triangular ripple artifacts. At the same time, the active receiver instances still used warm under-snow colors and overly strong clear-mask defaults, so the cleared zone looked like exposed brown asphalt instead of compacted dirty snow.

# Files to touch

- `Source/Kamaz_Cleaner/Private/Snow/SnowRuntimeTrailBridgeComponent.cpp`
- `Pyton_script/unreal_tools/apply_right_plow_berm.py`
- `Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_berm.py`
- `Pyton_script/unreal_tools/probe_snowtest_runtime_height_receiver.py`

# Ordered steps

1. Detect spline-road receiver materials by owner/path and disable runtime road `WPO` by scaling road runtime height to `0`.
2. Reset receiver instance base `HeightAmplitude` to `0` for active road/landscape instances.
3. Shift cleared-snow visual defaults toward dirty grey:
   - `PressedSnowColor`
   - `ThinSnowUnderColor`
   - `ThinSnowMinVisualOpacity`
   - softer `VisualClearMaskStrength` / `DepthMaskBoost`
4. Rebuild the editor.
5. Reapply the active material/runtime chain with `apply_right_plow_berm.py`.
6. Re-run the dedicated runtime-height probe to confirm roads no longer receive runtime height deformation after stamping.

# Invariants / Do-not-break rules

- Keep plow stamp writing active on `SnowTest_Level`.
- Do not reintroduce road `WPO` ripple on spline segments.
- Keep non-road test surfaces eligible for runtime height so the runtime path remains validated.
- Use project wrappers only for build/run validation.

# Validation

- Build succeeded: `.ai/logs/build_editor_20260323-143121.log`
- Apply run succeeded: `Saved/BlueprintAutomation/apply_right_plow_berm.json`
- Runtime probe succeeded: `Saved/BlueprintAutomation/probe_snowtest_runtime_height_receiver.json`

Key results:

- Active receiver instances now store:
  - `HeightAmplitude = 0.0`
  - `ThinSnowMinVisualOpacity = 0.72`
  - `VisualClearMaskStrength = 0.75`
  - `DepthMaskBoost = 1.0`
  - grey `PressedSnowColor` / `ThinSnowUnderColor`
- Runtime probe shows `stamp_written = true`
- `SnowSplineRoad*` road materials stay at `height_amplitude = 0.0` both before and after the plow stamp
- Non-road test surfaces still switch to `-95.0` after the stamp, proving the runtime height path itself still works

# Rollback notes

- Revert the spline-road runtime-height suppression in `SnowRuntimeTrailBridgeComponent.cpp`
- Restore the previous visual constants in the two Python material scripts
- Re-run `apply_right_plow_berm.py` after rollback so the old receiver values are written back into the assets

# Diff summary

- Runtime road height deformation is now disabled for `SnowSplineRoad*` receivers.
- Cleared snow visuals are now pushed toward dirty grey instead of warm brown.
- Active receiver instance defaults now avoid baseline road `WPO`.

# Open questions

- This fix intentionally trades road depth for visual stability on spline-road meshes. If deeper geometric clearing is still needed later, the next robust step is a denser dedicated snow surface above the road rather than stronger `WPO` on the spline mesh itself.
