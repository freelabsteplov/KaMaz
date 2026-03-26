Goal
- Implement only `PHASE 2 — WHEEL STAMPING` on top of the already validated V1 authoritative state core.
- Connect real Chaos wheel runtime signals into the existing `SnowStateManagerV1` stamp path without modifying the ping-pong core or touching plow/receiver/FX paths.

Hypothesis
- A new isolated actor component can read `FWheelStatus` from `UChaosWheeledVehicleMovementComponent`, convert contact/load/slip/skid/speed/surface data into `FSnowStateStampRequestV1`, and queue wheel stamps into the already-safe manager path.
- The safest way to validate this is to attach the component only to the cloned KamAZ path and run a dedicated phase-2 headless/debug script that creates/uses a temporary V1 manager and samples the RT around the stamped wheel contact.

Files to touch
- `Source/Kamaz_Cleaner/Public/Snow/RuntimeV1/SnowWheelTelemetryV1Component.h`
- `Source/Kamaz_Cleaner/Private/Snow/RuntimeV1/SnowWheelTelemetryV1Component.cpp`
- `Pyton_script/unreal_tools/build_snow_runtime_v1_phase2_wheel.py`
- new isolated asset only:
  - `/Game/CityPark/SnowSystem/SnowRuntime_V1/Blueprints/BPC_SnowWheelTelemetry_V1`

Ordered steps
1. Add a new `USnowWheelTelemetryV1Component` that resolves the Chaos wheeled vehicle movement component from the owner or owning pawn.
2. Read real wheel runtime state per wheel: contact, contact point, spring force, slip magnitude, skid magnitude, speed, phys material, and resolved surface family.
3. Map those signals into `FSnowStateStampRequestV1` using only `R/G/B` and leave `A` untouched in this phase.
4. Add a callable capture path for validation and an optional tick path for runtime proof.
5. Create `BPC_SnowWheelTelemetry_V1` under the isolated `SnowRuntime_V1` folder and attach it only to `KamazBP_HandlingAudit`.
6. Run one dedicated phase-2 headless/debug validation and capture JSON.

Invariants / Do-not-break rules
- Do not modify `SnowStateManagerV1` ping-pong core or `build_snow_runtime_v1_phase1.py`.
- Do not touch plow logic, receiver logic, Niagara FX, or old RT assets.
- Do not modify the original KamAZ blueprint.
- Keep all new content isolated under `SnowRuntime_V1`.

Validation
- Full editor build succeeds after adding the new wheel telemetry component.
- The isolated `BPC_SnowWheelTelemetry_V1` asset is created and attached to the cloned KamAZ path.
- Dedicated phase-2 JSON confirms:
  - wheel movement component found
  - non-zero in-contact wheels
  - non-zero queued wheel stamps
  - authoritative RT sample at a wheel stamp UV is non-zero

Rollback notes
- Remove `BPC_SnowWheelTelemetry_V1` from the clone and delete the isolated asset.
- Revert only the new `SnowWheelTelemetryV1Component` source files and the phase-2 script.
- Existing phase-1 state core and current MVP remain untouched.

Current diff summary
- No changes yet. This packet owns only the new wheel telemetry component and the new phase-2 asset/validation script.

Relevant log excerpts
- `build_editor_20260320-140833.log`: phase-1 build and ping-pong validation already succeeded.
- `build_snow_runtime_v1_phase1.json`: safe accumulation and two-stamp persistence already validated before this phase.

Open questions
- Whether headless map load exposes valid wheel contact/load data without entering PIE on the chosen map.
- If not, whether a debug capture on the placed clone actor still yields enough real `FWheelStatus` data for a truthful phase-2 proof.
