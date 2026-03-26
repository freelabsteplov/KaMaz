# Goal

Restore real snow-height clearing on `SnowTest_Level` when the plow is lowered, instead of writing a stamp that leaves the road height unchanged.

# Hypothesis

The plow stamp was still being written, but runtime height control was skipping the active spline-road materials because many road segments already used `MaterialInstanceDynamic` instances under transient names. The old receiver filter only matched the current material path, so it missed dynamic instances whose parent was the real `SnowReceiver_RVT_Height_MVP` chain.

There was also a secondary signal-risk in plow engagement: `KamazBP` and `BP_PlowBrush_Component` could disagree for a short time on `PlowLiftHeight`. Aggregating the available lift signals reduces false negatives when the blade is lowered.

# Files to touch

- `Source/Kamaz_Cleaner/Private/Snow/SnowRuntimeTrailBridgeComponent.cpp`
- `Pyton_script/unreal_tools/probe_snowtest_runtime_height_receiver.py`

# Ordered steps

1. Update `IsHeightReceiverMaterial()` to recognize height receivers through parent-chain inspection, not only the current material path.
2. Keep runtime plow engagement tolerant to mirror lag by consuming both `PlowLiftHeight` and `TargetPlowHeight` from owner/component signals.
3. Rebuild the editor with the project wrapper.
4. Run a dedicated headless probe on `SnowTest_Level` to compare road-material `HeightAmplitude` before and after `RecordTrailStampNow()`.

# Invariants / Do-not-break rules

- Do not regress plow source selection away from `BP_PlowBrush_Component`.
- Do not reintroduce positive snow raise in the active clear zone.
- Keep validation on wrapper scripts only.
- Avoid destructive map resets; work with existing map state.

# Validation

- Build succeeded: `.ai/logs/build_editor_20260323-134811.log`
- Dedicated runtime-height probe succeeded: `Saved/BlueprintAutomation/probe_snowtest_runtime_height_receiver.json`

Key probe results:

- `stamp_written = true`
- target runtime height = `-95.0`
- `SnowSplineRoad_MVP` road MID height changed from `-72.0` before stamp to `-95.0` after stamp
- the same `-95.0` propagation reached other spline-road variants (`Tile8`, `V3_Narrow`) and flat bridge/test surfaces

Relevant excerpts:

- before: `height_amplitude: -72.0` on `MID_MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_0`
- after: `height_amplitude: -95.0` on the same road MID

# Rollback notes

- Revert the parent-chain receiver detection in `SnowRuntimeTrailBridgeComponent.cpp`
- Remove the probe script if no longer needed
- Rebuild editor again with `Tools/AI/build_editor.ps1 -UProjectPath .\\Kamaz_Cleaner.uproject`

# Diff summary

- Runtime height receiver detection is now parent-aware for dynamic material instances.
- Plow engagement now consumes all visible lift mirrors instead of trusting only one source.
- Added a dedicated probe to prove that runtime `HeightAmplitude` reaches the active road materials.

# Open questions

- `SourceComponentOverride` still reloads as empty on the map in some headless inspections, although runtime source auto-resolution now picks the correct plow component.
- `bEnablePlowClearing = false` still does not suppress `RecordTrailStampNow()` in the existing plow probe; that is a separate runtime issue from the height-control fix above.
