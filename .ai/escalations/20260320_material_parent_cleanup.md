Goal
- Repair the broken legacy parent material `M_SnowReceiver_RVT_Height_MVP` so it compiles cleanly again and no longer forces default checkerboard rendering on dependent material instances.

Hypothesis
- The visible checkerboard on `SnowTest_Level` is caused by compile-failing orphan nodes left inside `M_SnowReceiver_RVT_Height_MVP`.
- Rebuilding this parent from a small, explicit graph is safer than trying to reconnect the duplicated orphan nodes in place.

Files to touch
- `Pyton_script/unreal_tools/rebuild_m_snowreceiver_rvt_height_mvp_clean.py`
- `Content/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP.uasset`

Ordered steps
1. Inspect the current rebuild script and confirm the existing compile error signatures.
2. Adjust the rebuild script so it creates a minimal valid parent graph from scratch.
3. Run the script headlessly against `SnowTest_Level`.
4. Verify that `M_SnowReceiver_RVT_Height_MVP` saves successfully and compile errors disappear from the fresh validation pass.

Invariants / Do-not-break rules
- Do not touch `SnowStateManagerV1` or any `SnowRuntime_V1` files.
- Do not touch plow logic, wheel telemetry, Niagara, or old RT pipeline assets.
- Do not change level assignments in this pass.
- Keep parameter names stable where practical so existing instances remain usable.

Validation
- Headless run writes a fresh JSON artifact for the rebuild pass.
- `M_SnowReceiver_RVT_Height_MVP` saves successfully.
- Fresh log/validation no longer reports `Missing 1-x input` or `Missing Saturate input` for this material.

Rollback notes
- Restore `Content/CityPark/SnowSystem/RVT_MVP/M_SnowReceiver_RVT_Height_MVP.uasset` from source control or prior asset backup if the clean rebuild regresses expected behavior.
- Revert only the rebuild script if the asset itself should stay untouched.

Current diff summary
- Narrow pass limited to one Python rebuild script and one material asset.

Relevant log excerpts
- `Kamaz_Cleaner.log` currently reports:
- `M_SnowReceiver_RVT_Height_MVP.uasset: Failed to compile Material for platform PCD3D_SM6, Default Material will be used in game.`
- `(Node OneMinus) Missing 1-x input`
- `(Node Saturate) Missing Saturate input`

Open questions
- Whether any legacy material instances still depend on road-edge parameters that will no longer exist after the clean rebuild.
