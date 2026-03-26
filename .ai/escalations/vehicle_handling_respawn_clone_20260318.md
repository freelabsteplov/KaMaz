## Goal
Fix KamAZ respawn rollback and improve baseline handling stability using clone-only workflow, preserving original BP and input bindings.

## Hypothesis
Rollback after respawn was caused by incomplete reset state (inputs/velocities) and missing forced handbrake lock in the reset path.

## Files To Touch
- `Pyton_script/unreal_tools/clone_kamaz_handling_audit.py`
- `/Game/CityPark/Kamaz/model/KamazBP_HandlingAudit`
- `/Game/CityPark/Kamaz/model/Front_wheels_HandlingAudit`
- `/Game/CityPark/Kamaz/model/Rear_wheels_HandlingAudit`

## Ordered Steps
1. Validate source BP and clone assets.
2. Tune clone wheel/movement defaults.
3. Extend `ResetVehicle` chain on clone:
   - clear throttle/steer/brake
   - set handbrake true
   - zero linear/angular velocity
   - sleep rigid body
4. Compile and save clone assets.
5. Ensure `Kamaz_SnowTest` in `SnowTest_Level` points to clone class.
6. Validate input action assets presence and handbrake key mapping.

## Invariants / Do-Not-Break Rules
- Do not modify original `/Game/CityPark/Kamaz/model/KamazBP`.
- Do not alter input action assets or mapping contexts.
- Do not touch snow/RVT systems.

## Validation
- `Tools/AI/build_editor.ps1` succeeded for `Kamaz_CleanerEditor`.
- Headless run of `clone_kamaz_handling_audit.py` completed with zero errors.
- Output artifact: `Saved/BlueprintAutomation/clone_kamaz_handling_audit.json`.

## Rollback Notes
- Reassign level actor `Kamaz_SnowTest` back to original class `/Game/CityPark/Kamaz/model/KamazBP`.
- Remove clone assets if needed:
  - `KamazBP_HandlingAudit`
  - `Front_wheels_HandlingAudit`
  - `Rear_wheels_HandlingAudit`
- Revert script file `clone_kamaz_handling_audit.py`.

## Diff Summary
- Added robust bridge result handling and strict compile success parsing.
- Added/validated reset chain generation including zero-velocity and handbrake lock.
- Added angular velocity pin fix via zero vector link when chain already exists.

## Relevant Log Excerpts
- Build: `Result: Succeeded` (`.ai/logs/build_editor_20260318-234213.log`).
- Commandlet: `Success - 0 error(s), 3 warning(s)` during final clone run.

## Open Questions
- Final drive feel should be confirmed in PIE with wheel + pedals + shifter hardware in user environment.
