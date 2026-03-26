# Goal
Finish the narrow `Road2` recovery pass in `/Game/Maps/MoscowEA5` so the active `Road2` snow receiver follows Unreal Runtime Virtual Texture methodology instead of ad-hoc experiments.

# Hypothesis
The remaining live Road2 regression is a clear-mask polarity mismatch in the receiver, not a new plow logic problem. The active project RVT writer pattern treats `RVT Mask = 1` as the stamped clear footprint, so the Road2 receiver must keep `InvertClearMask = 0.0`. Earlier Road2 material-only apply attempts were also misleading because the script first failed on import and later reached the MI mutation but could not save while the asset file was locked by a live editor/PIE process.

# Files to touch
- `Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_berm.py`
- `Pyton_script/unreal_tools/apply_road2_material_only_pass.py`
- `Pyton_script/unreal_tools/verify_road2_height_only_no_stamp.py`
- `.ai/escalations/20260326_road2_rvt_receiver_recovery.md`

# Ordered steps
1. Compare the active Road2 writer/receiver path with official Unreal RVT methodology and the existing project writer implementation.
2. Restore the active `Road2` MI to the known baseline-style Road2 parameter pattern with non-inverted clear-mask polarity.
3. Keep the runtime path unchanged: `RuntimeHeightAmplitudeWhenInactive = 0`, `RuntimeHeightAmplitudeWhenActive = -50`.
4. Keep the carrier geometry unchanged.
5. Rebuild the current parent receiver material only inside `M_SnowReceiver_RVT_Height_MVP`.
6. Run headless validation through project wrappers, including a no-stamp proof that forces `HeightAmplitude = -50` without writing RVT.
7. Verify that the Road2 material-only apply truly executes and does not silently fail on import or file-save lock.

# Invariants / Do-not-break rules
- Do not touch plow logic.
- Do not touch `SnowRuntime_V1`.
- Do not replace the RVT pipeline.
- Do not change `Road2` carrier geometry.
- Do not move to another parent/material corridor.

# Validation
- `Tools/AI/run_smoke.ps1 -UProjectPath .\Kamaz_Cleaner.uproject -RunHeadless -PythonScriptPath Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_berm.py`
- `Tools/AI/run_smoke.ps1 -UProjectPath .\Kamaz_Cleaner.uproject -RunHeadless -PythonScriptPath Pyton_script/unreal_tools/apply_road2_material_only_pass.py`
- `Tools/AI/run_smoke.ps1 -UProjectPath .\Kamaz_Cleaner.uproject -RunHeadless -PythonScriptPath Pyton_script/unreal_tools/probe_road2_runtime_height_receiver.py`
- `Tools/AI/run_smoke.ps1 -UProjectPath .\Kamaz_Cleaner.uproject -RunHeadless -PythonScriptPath Pyton_script/unreal_tools/verify_road2_height_only_no_stamp.py`

# Rollback notes
- Restore `MI_SnowRoadCarrier_Road2` from pre-pass values if the live viewport regresses.
- Restore `M_SnowReceiver_RVT_Height_MVP` from `/Game/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP_Backup_BaselineRecovery`.

# Current diff summary
- Rebuilt the current parent receiver to remove the last global clear coupling from the Road2 corridor:
- `final_visible_snow` no longer lerps off a global active-plow gate.
- local snow removal now follows only the sampled RVT clear mask.
- baseline snow visibility remains separate from local height cut.
- Rebuilt the current parent receiver to use thresholded opacity drop-out for reveal instead of soft lingering carrier presence.
- Added a material-only Road2 pass script so MI changes do not re-touch carrier geometry.
- Fixed the Road2 material-only pass script so it can import `road2_writer_policy.py` under headless Unreal by appending the tool directory to `sys.path`.
- Current Road2 MI target values keep Road2 on the canonical project RVT writer polarity and reduce dark residual carrier in the rut:
  - `InvertClearMask = 0.0`
  - `BaselineSnowCoverage = 1.0`
  - `BaselineHeightCm = 50.0`
  - `HeightAmplitude = 0.0`
  - `VisualClearMaskStrength = 1.0`
  - `DepthMaskBoost = 1.0`
  - `SnowDetailInfluence = 0.0`
  - `ThinSnowMinVisualOpacity = 0.88`
  - `SnowRoughness = 0.72`
  - `PressedRoughness = 0.46`
  - `PressedSnowColor = (0.52, 0.52, 0.54, 1.0)`
  - `RevealOpacityThreshold = 0.90`

# Relevant log excerpts
- `Pyton_script/unreal_tools/apply_soft_rvt_stamp_edges.py` documents the known-good writer convention: `Mask stays constant 1 for clearing semantics`.
- `Saved/BlueprintAutomation/apply_road2_material_only_pass.json` now shows the intended mutation `InvertClearMask: 1.0 -> 0.0`, but save currently fails with `Error Code 32` because `MI_SnowRoadCarrier_Road2.uasset` is locked by a live editor/PIE process.
- `Saved/BlueprintAutomation/probe_road2_runtime_height_receiver.json -> "stamp_written": true`
- `Saved/BlueprintAutomation/verify_road2_height_only_no_stamp.json -> before/after captures differ only by file hash metadata; sampled mean abs channel diff = 0.0 in shell follow-up`

# Open questions
- The live wireframe view strongly suggests the disappearing object is the masked Road2 carrier itself, which is consistent with the currently saved `InvertClearMask = 1.0` asset state and inconsistent with the project writer convention.
- The next live verification needs the corrected MI (`InvertClearMask = 0.0`) to be saved from an unlocked editor session before further Road2 behavior claims are made.

# Road2 writer-set policy
- Canonical Road2 writer-set is fixed to exactly:
- `Pyton_script/unreal_tools/apply_road_height_carrier_for_road2.py`
- `Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_berm.py`
- `Pyton_script/unreal_tools/apply_road2_material_only_pass.py`
- Ownership split:
- `apply_road_height_carrier_for_road2.py`: carrier actor, receiver tag, trail actor defaults
- `rebuild_m_snowreceiver_rvt_height_mvp_berm.py`: shared parent material graph for the current MVP corridor
- `apply_road2_material_only_pass.py`: active `MI_SnowRoadCarrier_Road2` values only
- Conflicting Road2 writers are deprecated and blocked:
- `apply_road2_height_baseline_recovery.py`
- `apply_road2_offline_baseline_height_plus50.py`
- `fix_road2_active_mi_baseline_scalars.py`
- `fix_road2_receiver_visibility_baseline.py`
- `apply_road2_visible_snow_whiten_inplace.py`
- `apply_visible_snow_to_road_only_carrier.py`
- `set_road2_carrier_to_localheight_baseline.py`
- `rebuild_m_snowreceiver_rvt_height_mvp_clean.py`
- `rebuild_visible_road_snow_receiver.py`
- `offline_recover_road_receiver.py`
- `recover_road_receiver_parent.py`
- Enforcement lives in `Pyton_script/unreal_tools/road2_writer_policy.py`; blocked scripts now fail immediately with a Road2 writer policy error instead of mutating shared Road2 assets.
