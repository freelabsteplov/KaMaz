Goal
- Start the new isolated `SnowRuntime_V1` production-like pipeline without breaking the existing RVT MVP.
- Limit this executor pass to `PHASE 0 + PHASE 1`: authoritative RT core, managers/bootstrap, isolated asset root, and one debug write proof.

Hypothesis
- The safest way to move toward the requested production runtime path is to create a fully isolated V1 layer first, instead of extending the current MVP files in place.
- `RT_SnowState_A_V1` + `RT_SnowState_B_V1` plus a new state manager actor can provide a clean authoritative base for future wheel/plow/receiver/FX phases.
- Headless asset generation and validation are the only risky part; source ownership can stay fully isolated under new `RuntimeV1` files.

Files to touch
- `Source/Kamaz_Cleaner/Public/Snow/RuntimeV1/SnowStateManagerV1.h`
- `Source/Kamaz_Cleaner/Private/Snow/RuntimeV1/SnowStateManagerV1.cpp`
- `Source/Kamaz_Cleaner/Public/Snow/RuntimeV1/SnowFXManagerV1.h`
- `Source/Kamaz_Cleaner/Private/Snow/RuntimeV1/SnowFXManagerV1.cpp`
- `Source/Kamaz_Cleaner/Public/Snow/RuntimeV1/SnowRuntimeBootstrapV1.h`
- `Source/Kamaz_Cleaner/Private/Snow/RuntimeV1/SnowRuntimeBootstrapV1.cpp`
- `Pyton_script/unreal_tools/build_snow_runtime_v1_phase1.py`
- new isolated assets only under `/Game/CityPark/SnowSystem/SnowRuntime_V1`

Ordered steps
1. Create new `RuntimeV1` C++ actor classes for state manager, FX manager, and bootstrap ownership.
2. Create a Python asset generator for the isolated `/Game/CityPark/SnowSystem/SnowRuntime_V1` root.
3. Generate `RT_SnowState_A_V1`, `RT_SnowState_B_V1`, `M_SnowState_Write_Wheel_V1`, `M_SnowState_Write_Plow_V1`, and the three manager blueprints.
4. Wire BP default references for the state manager where possible.
5. Run one debug write proof against the new RT state core and capture JSON.

Invariants / Do-not-break rules
- Do not touch old RT-based snow logic.
- Do not change current RVT MVP assets in place.
- Do not modify the original KamAZ blueprint.
- Keep all new content under `SnowRuntime_V1` and all new code under `Snow/RuntimeV1`.

Validation
- Full editor build succeeds after adding the new runtime V1 C++ classes.
- Headless generator creates the isolated V1 asset root and expected new assets.
- Manager debug write path reaches `debug_write_flushed = true`.
- Sample/readback from the authoritative RT should become non-zero; if not, that remains the explicit phase-1 blocker.

Rollback notes
- Delete the isolated `/Game/CityPark/SnowSystem/SnowRuntime_V1` folder.
- Revert only the new `Snow/RuntimeV1` source files and the new generator script.
- Existing MVP runtime path remains untouched.

Current diff summary
- Added new runtime V1 source files for state/FX/bootstrap actors.
- Added a new isolated asset-generation script for `SnowRuntime_V1`.
- No existing snow MVP source files or assets are part of this phase's ownership set.

Relevant log excerpts
- `build_editor_20260320-111814.log`: new runtime V1 classes compile and link successfully.
- `build_snow_runtime_v1_phase1.json`: isolated V1 assets are created and debug flush executes.

Open questions
- Whether the phase-1 write material needs a different render-target output path to make readback visibly non-zero in headless validation.
- Whether future wheel/plow phases should keep RT_B purely semantic or continue using it as scratch during ping-pong writes.
