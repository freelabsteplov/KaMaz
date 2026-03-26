Goal
- Add a visible snow berm on the right side of the active plow path on `SnowTest_Level` without breaking the restored active snow clearing behavior.

Hypothesis
- The active clearing path is correct when RVT `Mask` remains the authoritative clear signal.
- A separate auxiliary RVT signal in `BaseColor.R` can drive a positive right-side berm raise in the receiver without inverting clearing.

Files to touch
- `Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_clean.py`
- `Pyton_script/unreal_tools/apply_right_plow_berm.py`

Ordered steps
1. Extend the clean receiver rebuild script to read `RVT BaseColor.R` as an optional right-berm signal.
2. Keep default parent safety by setting berm defaults to zero.
3. Create an apply script that:
4. rebuilds the active writer with `Mask = 1` and `BaseColor.R = right-side band only`
5. updates the active landscape runtime MI with `RightBermRaise > 0`
6. Run headless Unreal apply and save.

Invariants / Do-not-break rules
- Do not change clearing polarity.
- Do not change plow/bridge C++ logic.
- Do not touch wheel path, Niagara, or old RT pipeline.
- Keep the active writer path at `/Game/CityPark/SnowSystem/RVT_MVP/M_RVT_DebugWriter_MVP`.

Validation
- JSON apply artifact must show:
- writer saved
- receiver parent rebuilt and saved
- active landscape MI saved
- no error
- manual result target:
- snow still clears
- a raised berm appears only on the right side of the plow trail

Rollback notes
- Re-run the restore mode in `apply_soft_rvt_stamp_edges.py` to restore the known-good writer.
- Rebuild the receiver parent from `rebuild_m_snowreceiver_rvt_height_mvp_clean.py` with `RightBermRaise = 0`.
