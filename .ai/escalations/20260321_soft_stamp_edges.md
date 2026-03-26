Goal
- Add soft snow-clearing edges to the active RVT stamp path on `SnowTest_Level` without changing plow/runtime bridge logic.

Hypothesis
- The current active trail writer uses `M_RVT_DebugWriter_MVP` with a hard rectangular mask.
- Smoothing the writer footprint itself will create visible soft snow boundaries on the existing receiver path.

Files to touch
- `Pyton_script/unreal_tools/apply_soft_rvt_stamp_edges.py`

Ordered steps
1. Rebuild `M_RVT_DebugWriter_MVP` with a soft rectangular RVT mask falloff.
2. Apply a slightly softer `HeightContrast` to the active landscape runtime-fix MI.
3. Save assets and write a JSON validation artifact.
4. Run headless Unreal to apply and compile.

Invariants / Do-not-break rules
- Do not touch old RT pipeline.
- Do not touch plow logic or `SnowRuntimeTrailBridgeComponent`.
- Do not change current isolated `SnowRuntime_V1` work.
- Keep current active writer asset path unchanged: `/Game/CityPark/SnowSystem/RVT_MVP/M_RVT_DebugWriter_MVP`.

Validation
- `apply_soft_rvt_stamp_edges.json` must report:
- writer saved
- runtime-fix MI saved
- no error

Rollback notes
- Rebuild `M_RVT_DebugWriter_MVP` again from prior script if needed.
- Reset `HeightContrast` on `MI_SnowReceiver_RVT_Height_MVP_CAA_P1_2K_LandscapeRuntimeFix` to `1.0`.
