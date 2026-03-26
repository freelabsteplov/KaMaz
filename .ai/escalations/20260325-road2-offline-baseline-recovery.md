# Goal
Recover Road2 offline snow baseline visibility inside the existing MVP receiver path only, without changing parent path or runtime/plow logic.

# Hypothesis
`MI_SnowRoadCarrier_Road2` lost its baseline material-height response because `HeightAmplitude` was left at `0.0`. Raising only the active MI baseline to `+50.0` should restore visible offline snow on the existing Road2 carrier path.

# Files to touch
- `Pyton_script/unreal_tools/apply_road2_offline_baseline_height_plus50.py`
- `Pyton_script/unreal_tools/verify_road2_offline_baseline_before_runtime.py`
- `Content/CityPark/SnowSystem/Receivers/MI_SnowRoadCarrier_Road2.uasset`

# Ordered steps
1. Load `MoscowEA5` and verify the active Road2 carrier/MI path still points to `MI_SnowRoadCarrier_Road2` with parent `M_SnowReceiver_RVT_Height_MVP`.
2. Set only the active MI offline baseline scalars, with `HeightAmplitude = +50.0`.
3. Save only the MI and current map.
4. Run an offline-only proof capture using the existing Road2 proof cameras, without any runtime stamp.
5. Inspect the generated JSON and proof images for visible carrier contribution before runtime.

# Invariants / Do-not-break rules
- Do not change parent material path.
- Do not touch runtime trail settings, plow logic, SnowRuntime_V1, wheel telemetry, Niagara, InteractiveWorld, or RT pipeline.
- Do not create new detour materials.
- Do not add any runtime stamp into the offline proof pass.

# Validation
- `Tools/AI/run_smoke.ps1 -RunHeadless -UProjectPath .\Kamaz_Cleaner.uproject -Map /Game/Maps/MoscowEA5 -PythonScriptPath .\Pyton_script\unreal_tools\apply_road2_offline_baseline_height_plus50.py`
- `Tools/AI/run_smoke.ps1 -RunHeadless -UProjectPath .\Kamaz_Cleaner.uproject -Map /Game/Maps/MoscowEA5 -PythonScriptPath .\Pyton_script\unreal_tools\verify_road2_offline_baseline_before_runtime.py`
- `Tools/AI/run_smoke.ps1 -RunHeadless -UProjectPath .\Kamaz_Cleaner.uproject -Map /Game/Maps/MoscowEA5 -PythonScriptPath .\Pyton_script\unreal_tools\inspect_moscowea5_road2_carrier_runtime.py`
- Result:
- `MI_SnowRoadCarrier_Road2.HeightAmplitude = 50.0`
- Parent stayed on `M_SnowReceiver_RVT_Height_MVP`
- Runtime control stayed at `Inactive=0.0 / Active=-50.0`
- Offline proof images on Road2 perspective/side remained visually identical with and without carrier
- `visible_baseline_response_detected = false`

# Rollback notes
- Restore `MI_SnowRoadCarrier_Road2.HeightAmplitude` to its prior value from the JSON output if the offline baseline pass must be reverted.
- The new Python scripts are isolated tooling and can be removed without touching gameplay/runtime code.

# Current diff summary
- Added one narrow MI setter for Road2 offline baseline.
- Added one offline verifier that reuses existing Road2 proof cameras and avoids runtime stamping.
- Saved `Content/CityPark/SnowSystem/Receivers/MI_SnowRoadCarrier_Road2.uasset` with `HeightAmplitude = +50.0`.

# Relevant log excerpts
- `Saved/BlueprintAutomation/apply_road2_offline_baseline_height_plus50.json`
- `"success": true`
- `"HeightAmplitude": 50.0`
- `Saved/BlueprintAutomation/verify_road2_offline_baseline_before_runtime.json`
- `"topdown_max_sample_delta": 0.0`
- `"perspective_max_sample_delta": 0.0`
- `"side_profile_max_sample_delta": 0.0`
- `"visible_baseline_response_detected": false`
- `Saved/BlueprintAutomation/inspect_moscowea5_road2_carrier_runtime.json`
- `"RuntimeHeightAmplitudeWhenActive": -50.0`
- `"RuntimeHeightAmplitudeWhenInactive": 0.0`

# Open questions
- Whether `M_SnowReceiver_RVT_Height_MVP` can expose any visible offline baseline on the current Road2 carrier at all, since raw Road2 proof captures stay visually flat even with `HeightAmplitude = +50.0`.
