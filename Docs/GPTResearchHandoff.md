# GPT Research Handoff

## Project

- Project: `Kamaz_Cleaner`
- Project path: `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner`
- Unreal: `5.7.x`
- Main map: `/Game/Maps/MoscowEA5`
- Main vehicle BP: `/Game/CityPark/Kamaz/model/KamazBP`

## Objective

The target result is:

- `Kamaz` drives normally with existing input path intact
- `MOZA` input stays untouched and unbroken
- front plow follows the real blade position on `SM_FrontHitch`
- plow and wheels write into the shared snow render target
- road receiver reads that RT and shows visible snow clearing on the playable
  road mesh

Current status is close but not complete:

- visible white road snow can be shown on the selected road zone
- forced direct plow draw changes the RT
- live plow tick writing is now confirmed under debug conditions
- end-to-end visible clearing in normal PIE is still not confirmed

## Hard Constraints

Do not suggest solutions that violate these:

- do not recreate `BlueprintAutomationEditor`
- use the existing `BlueprintAutomationEditor`
- do not break `Kamaz` input path
- do not touch or regress `MOZA R16` steering
- do not touch or regress `MOZA AB` pedals
- do not reparent road material instance to
  `/Game/CityPark/SnowSystem/M_SnowTestMVP_Landscape1`
- avoid risky live-editor material experiments that swap parents on production
  road assets

## Verified Architecture

Runtime is content-driven, not C++ gameplay-driven.

### Runtime BP layer

- `KamazBP`
  - owns the vehicle
  - resolves snow helper components
  - propagates `OwnerVehicle`
  - propagates `PlowLiftHeight`
- `BP_WheelSnowTrace_Component`
  - wheel writer
- `BP_PlowBrush_Component`
  - plow writer

### Shared snow runtime assets

- RT:
  - `/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks`
- MPC:
  - `/Game/CityPark/SnowSystem/MPC_SnowSystem`

### Material side

- landscape receiver chain exists
- road receiver chain is isolated and safe under:
  - `/Game/CityPark/SnowSystem/Receivers`

### C++ layer

There is no main gameplay `Source` module driving snow.

The meaningful C++ layer is editor-only:

- `Plugins\BlueprintAutomationEditor`

It is used as a safe automation layer for Blueprint graph inspection, graph
batching, compile/save, and action scanning. It is not a runtime snow system.

## Current Verified Facts

### 1. Writer function itself is alive

From `probe_spawned_plow_writer_runtime.json`:

- direct forced `DrawPlowClearance` call succeeds
- `rt_changed = true`
- `rt_stats_before.non_black_samples = 0`
- `rt_stats_after.non_black_samples = 3`

Interpretation:

- the actual plow draw function can modify the RT
- the core writer function is not fundamentally dead

### 2. Road receiver can show visible snow

The road receiver was rebuilt and applied to the spawn-zone road actors:

- `StaticMeshActor_208`
- `StaticMeshActor_188`
- `StaticMeshActor_142`

Interpretation:

- the receiver side is capable of showing white snow on the selected road zone
- this is not a full-map deployment, only a controlled test zone

### 3. Real playable surface under Kamaz is road static mesh, not landscape

This is already established. Work should focus on the road receiver chain, not
on treating `Landscape_0` as the main receiver under the truck.

### 4. `BP_PlowBrush_Component` normal tick path is gated

From `plowbrush_event_graph.json`, normal live writing depends on:

- `bEnablePlowClearing == true`
- `OwnerVehicle` valid
- `PlowLiftHeight` in range `0.0 .. 0.5`
- vehicle movement cast to `ChaosVehicleMovementComponent`
- speed gate using `MinPlowSpeed`
- update gate using `UpdateRate`

Only after those checks does live runtime reach:

- `DrawPlowClearance`

### 5. `OwnerVehicle` self-init has already been repaired

New evidence:

- `apply_plowbrush_beginplay_owner_fallback.json`
- `probe_plow_tick_runtime.json`

Verified result:

- before BeginPlay: `OwnerVehicle = null`
- after BeginPlay: `OwnerVehicle = /Game/Maps/MoscowEA5...KamazBP_C_0`

Interpretation:

- the component now self-resolves `OwnerVehicle` on BeginPlay
- the earlier null-owner hypothesis was real, but it is no longer the main open blocker

### 6. Live tick writing is now confirmed under debug overdrive

From `probe_plow_tick_runtime.json`:

- `ReceiveTick` is callable
- RT stays black on tick 0
- RT changes on tick 1 and remains changed on tick 2
- `tick_rt_changed = true`
- `max_g = 255.0`
- `non_black_samples = 3`

Interpretation:

- the plow writer does work through the normal tick path
- one tick is not enough because `TimeSinceLastUpdate` must accumulate first
- the live writer is not fundamentally dead
- the remaining issue is translating this confirmed debug/runtime path into visible end-to-end behavior in normal PIE

## Current Working Hypothesis

The current split is now:

- receiver side: sufficiently alive for debug visualization
- direct plow RT writer: alive
- live plow tick path: alive under debug conditions
- remaining open issue: why the user does not yet see stable end-to-end clearing in normal PIE on the test road zone

The most likely remaining causes are now:

- normal non-debug thresholds and gates
- brush placement relative to the blade edge
- receiver coverage and road test-zone visibility
- differences between headless tick proof and actual in-editor PIE behavior

## What We Need From GPT Research

Please answer these specifically:

1. Given that `OwnerVehicle` self-init and tick writing are now confirmed under
   debug conditions, what is the most likely remaining cause for missing visible
   end-to-end plow clearing in normal PIE?

2. What is the minimal safe fix path that:
   - does not touch `MOZA`
   - does not change `Kamaz` input path
   - does not recreate `BlueprintAutomationEditor`
   - does not rely on risky road material parent swaps

3. Please separate:
   - runtime write issue
   - receiver/material visualization issue
   - editor automation/tooling issue

4. If you recommend a fix inside `BP_PlowBrush_Component`, prefer the most
   local safe change possible.

5. Explicitly account for this runtime fact:
   - `ReceiveTick` writes into RT on the second tick under debug overdrive
   - therefore the next diagnosis should focus on non-debug thresholds,
     placement, PIE/runtime conditions, or receiver visibility

## Exact Upload Set

Upload these first.

### Core files

1. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Docs\GPTResearchHandoff.md`
2. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Docs\KamazProjectStructure_BP_Material_CPP.md`
3. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Docs\SnowMaterialArchitecture.md`
4. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\probe_spawned_plow_writer_runtime.json`
5. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\plowbrush_event_graph.json`
6. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\kamazbp_after_plowfix_graph.json`
7. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\snow_component_defaults.json`
8. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\apply_receiver_to_spawn_zone_roads.json`
9. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\rebuild_visible_road_snow_receiver.json`
10. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\apply_plowbrush_beginplay_owner_fallback.json`
11. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\apply_plow_debug_overdrive.json`
12. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\probe_plow_tick_runtime.json`

### Optional if more context is needed

13. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Plugins\BlueprintAutomationEditor\README.md`
14. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Pyton_script\unreal_tools\apply_plowbrush_beginplay_owner_fallback.py`
15. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Pyton_script\unreal_tools\batches\plowbrush_beginplay_owner_fallback.json`
16. `C:\Users\post\Documents\Unreal Projects\Kamaz_Cleaner\Saved\BlueprintAutomation\apply_landscape_receiver_material.json`

## What Not To Upload First

Do not start by uploading:

- the entire `Saved\BlueprintAutomation` directory
- full raw logs
- all screenshots without explanation
- the whole plugin source tree

That will dilute the problem.

## Recommended GPT Research Prompt

Use this as the initial prompt:

```text
I am attaching a focused handoff for an Unreal Engine 5.7.x snow/plow system in the Kamaz_Cleaner project.

Please analyze the attached architecture and evidence and answer these questions:

1. Given the attached evidence, what is the most likely remaining cause for missing visible end-to-end plow clearing in normal PIE, now that:
- BeginPlay self-init for OwnerVehicle has been repaired
- direct DrawPlowClearance changes the RT
- normal ReceiveTick writes into the RT under debug overdrive

2. Propose the minimal safe fix path. Hard constraints:
- do not suggest recreating BlueprintAutomationEditor
- do not touch or break Kamaz input path
- do not touch or regress MOZA R16 steering or MOZA AB pedals
- do not propose risky road material parent swaps to M_SnowTestMVP_Landscape1

3. Separate your analysis into:
- runtime writer problem
- receiver/material visualization problem
- editor automation/tooling problem

4. Prioritize the most local and safest fix inside BP_PlowBrush_Component or its immediate initialization chain if that is the correct direction.

5. Explicitly reason about the difference between:
- confirmed headless runtime writing
- missing visible behavior in normal editor PIE

Please be concrete and reason from the attached files, not from generic Unreal advice.
```

## Recommended Upload Order

If GPT Research has limited space, upload in this order:

1. `GPTResearchHandoff.md`
2. `KamazProjectStructure_BP_Material_CPP.md`
3. `probe_plow_tick_runtime.json`
4. `probe_spawned_plow_writer_runtime.json`
5. `plowbrush_event_graph.json`
6. `kamazbp_after_plowfix_graph.json`
7. `SnowMaterialArchitecture.md`
8. receiver JSONs

That is enough for a strong first-pass analysis.
