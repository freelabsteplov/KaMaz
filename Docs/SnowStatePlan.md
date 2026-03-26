# Snow State Plan

## Goal

Move the current snow system from a local debug effect into a world-state pipeline:

- one shared world snow mask for the playable area
- plow and wheel systems only write into that mask
- road and landscape materials only read and visualize that mask

The target is not "draw a temporary plow stripe". The target is "maintain
snow state over world space and visualize it consistently on receivers".

## Current Confirmed Facts

- `BP_PlowBrush_Component` can write into the shared RT through
  `DrawPlowClearance`
- `BP_PlowBrush_Component` can also write through normal `ReceiveTick` under
  debug conditions
- `OwnerVehicle` self-init on `BeginPlay` has been repaired
- the selected road receiver can show visible white snow
- the playable surface under Kamaz is a road static mesh, not the main
  landscape

This means the core writer path is alive. The remaining work is now centered on
global state semantics, mapping, and visualization.

## Target Architecture

### 1. Global Snow State

Use one shared render target as the authoritative world snow-state storage for
the current map.

Current candidate:

- `/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks`

This RT should represent snow state in world space, not just a temporary debug
overlay.

### 2. Writer Layer

These systems should only write state:

- `BP_PlowBrush_Component`
- `BP_WheelSnowTrace_Component`

They should not be responsible for final road appearance.

### 3. Receiver Layer

These systems should only read and visualize state:

- road receiver materials
- landscape receiver materials

Receivers should not invent snow logic locally. They should display the world
mask consistently.

## Proposed Channel Semantics

Recommended first-pass channel ownership for the shared RT:

- `R` = snow amount / remaining snow
- `G` = plow clear influence
- `B` = wheel compact / wheel track influence
- `A` = reserved

This can be adjusted later, but the project should explicitly commit to one
meaning instead of treating the RT as an undefined debug texture.

## World Mapping Rule

All writers and receivers must use the same world-to-UV mapping.

Single source of truth:

- `/Game/CityPark/SnowSystem/MPC_SnowSystem`

Required parameters:

- `WorldBoundsMin`
- `WorldBoundsMax`
- `BrushUV`

No receiver should use a separate mapping formula from the writers.

## Three-Phase Plan

### Phase 1. Stabilize Global Snow State

- Treat the shared RT as world storage, not a one-off debug target
- Freeze and document channel semantics
- Freeze and document the world-to-UV conversion
- Verify that plow and wheels both write into the same mapped space

Success condition:

- state written by writers is spatially stable and repeatable across the test
  road zone

### Phase 2. Stabilize Writers

- keep plow and wheel logic isolated as writers only
- verify normal thresholds after debug overdrive is removed
- confirm correct brush placement relative to the real plow blade edge
- confirm write cadence under normal PIE conditions

Success condition:

- in normal PIE, plow and wheels update the shared RT without debug forcing

### Phase 3. Stabilize Receivers

- keep road receiver workflow isolated and safe
- make one road test zone visually correct first
- ensure receiver materials read the same RT and same mapping
- only expand to more road actors after one zone is correct

Success condition:

- visible clearing and wheel effects match the RT on the selected road zone

## Immediate Priorities

1. Confirm why normal visible clearing in editor PIE still lags behind the
   headless debug proof.
2. Compare debug-overdrive behavior against normal thresholds:
   - `MinPlowSpeed`
   - `UpdateRate`
   - brush placement
3. Keep the road receiver workflow focused on the spawn/test road zone before
   scaling to the rest of the map.

## Non-Goals

Do not treat these as the current task:

- large scene refactors
- full-map receiver deployment
- risky road material parent swaps
- input changes
- MOZA changes
- plugin recreation

## Project Constraints

- do not recreate `BlueprintAutomationEditor`
- do not break `Kamaz` input path
- do not touch or regress `MOZA R16` steering
- do not touch or regress `MOZA AB` pedals
- do not reparent road material instances to
  `/Game/CityPark/SnowSystem/M_SnowTestMVP_Landscape1`

## Practical Next Step

Use the current confirmed runtime result as the baseline:

- writer path is alive
- receiver path is partly alive

The next diagnosis should focus on the gap between:

- confirmed headless RT writes
- missing or weak visible end-to-end clearing in normal editor PIE
