## Goal
Stop the active cloned KamAZ from rolling backward on level start / restart by enforcing a deterministic startup hold until explicit release.

## Hypothesis
The current Blueprint-only handbrake/start-brake flow is not a hard physics lock. Chaos vehicle simulation starts before that flow reliably holds the pawn, so the truck can roll backward and spin wheels despite the intended parking brake.

## Files To Touch
- `Source/Kamaz_Cleaner/Kamaz_Cleaner.Build.cs`
- `Source/Kamaz_Cleaner/Public/Vehicle/KamazStartupHoldComponent.h`
- `Source/Kamaz_Cleaner/Private/Vehicle/KamazStartupHoldComponent.cpp`
- `Pyton_script/unreal_tools/attach_kamaz_startup_hold_component.py`

## Ordered Steps
1. Add a dedicated runtime startup-hold component for Chaos vehicles.
2. Make it arm on `BeginPlay` and `Pawn Restarted`.
3. While armed:
   - force `Handbrake = true`
   - force `Parked = true`
   - force `Sleeping = true`
   - zero linear/angular velocity
   - sleep rigid bodies
4. Release only on:
   - `Space`
   - real `BrakeInput` over threshold
5. Attach the component only to `KamazBP_HandlingAudit`.
6. Build with the project wrapper and inspect logs/artifacts.

## Invariants / Do-Not-Break Rules
- Do not modify original `/Game/CityPark/Kamaz/model/KamazBP`.
- Do not change input assets or mappings.
- Do not touch snow/RVT logic.
- Keep the fix isolated to the cloned KamAZ setup.

## Validation
- `Tools/AI/build_editor.ps1`
- Headless Unreal Python run of `attach_kamaz_startup_hold_component.py`
- Confirm artifact under `Saved/BlueprintAutomation/attach_kamaz_startup_hold_component.json`

## Rollback Notes
- Remove `KamazStartupHold` component from `KamazBP_HandlingAudit`.
- Revert the new component files and module dependency change.

## Diff Summary
- Added a dedicated startup-hold component for Chaos vehicle pawns.
- Added a headless attachment script for the cloned KamAZ blueprint.

## Relevant Log Excerpts
- Pending build / attach run.

## Open Questions
- If the project uses a custom reset path that does not fire Pawn restart, we may need one follow-up hook into the clone `ResetVehicle` event to re-arm the same component there too.
