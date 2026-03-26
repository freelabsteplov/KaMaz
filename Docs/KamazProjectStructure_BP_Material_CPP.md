# Kamaz_Cleaner Project Structure: BP, Material, C++

## Purpose

This document fixes the current project architecture in one place based on the
verified analysis artifacts from `Saved\BlueprintAutomation`, the existing
`SnowMaterialArchitecture.md`, and the current `BlueprintAutomationEditor`
plugin source.

The goal is to describe:

- where the project logic actually lives
- how `KamazBP`, snow Blueprint components, materials, and editor C++ connect
- which parts are runtime gameplay and which parts are editor automation only
- what is currently verified, and what is still the live blocker

## Top-Level Structure

At the project root:

- `Content`
  - gameplay Blueprints, meshes, maps, and snow assets
- `Plugins\BlueprintAutomationEditor`
  - editor-only C++ automation plugin used for safe Blueprint graph work
- `Pyton_script\unreal_tools`
  - Python orchestration layer on top of the plugin and Unreal Python
- `Saved\BlueprintAutomation`
  - analysis snapshots, graph dumps, diagnostic JSON, and helper outputs
- `Docs`
  - human-readable architecture and workflow notes

Important project fact:

- the project currently has no dedicated gameplay `Source` module
- runtime gameplay logic is content-driven: mostly Blueprint + material logic
- C++ is used mainly as an editor tool layer, not as runtime snow gameplay

## Plugin and Engine State

From `Kamaz_Cleaner.uproject`:

- `ChaosVehiclesPlugin` is enabled
- `RawInput` is enabled
- `BlueprintAutomationEditor` is enabled, editor-only
- `LudusAI` is disabled

Operational constraints for this project:

- do not recreate `BlueprintAutomationEditor`
- do not break `Kamaz` input path
- do not touch or regress `MOZA R16` steering or `MOZA AB` pedals

## Runtime Architecture

### 1. Vehicle Root

Primary gameplay asset:

- `/Game/CityPark/Kamaz/model/KamazBP`

Verified base runtime shape from `kamaz_component_tree.json`:

- root visual/physics body:
  - `VehicleMesh`
  - class: `SkeletalMeshComponent`
  - mesh: `/Game/CityPark/Kamaz/model/kamaz_ue5`
- movement:
  - `VehicleMovementComp`
  - class: `ChaosWheeledVehicleMovementComponent`

This means the truck is a Chaos vehicle driven by Blueprint composition, not by
a custom gameplay C++ vehicle class.

### 2. Snow Writer Components

Verified runtime writer Blueprints:

- `/Game/CityPark/SnowSystem/BP_WheelSnowTrace_Component`
- `/Game/CityPark/SnowSystem/BP_PlowBrush_Component`

Verified shared target:

- `/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks`

From `snow_component_defaults.json`:

- both writer components point to the same render target
- both components also depend on:
  - `/Game/CityPark/SnowSystem/MPC_SnowSystem`

### 3. Plow Attachment Model

The front plow follows:

- `SM_FrontHitch`

Confirmed runtime direction:

- `BP_PlowBrush_Component` must be attached under the front plow assembly
- the brush should follow the actual blade edge, not only the truck root

Current brush shape used for testing:

- box brush instance:
  - `/Game/CityPark/SnowSystem/BrushMaterials/MI_Snow_PlowBrush_BoxSafe_350x50x100`
- intended dimensions:
  - length `50 cm`
  - width `350 cm`
  - height `100 cm`

## Runtime Logic: KamazBP Layer

`KamazBP` is the composition/orchestration layer between the truck and the snow
components.

Verified from `kamazbp_after_plowfix_graph.json` and related summaries:

- fallback resolution exists for:
  - `SnowTraceComponent`
  - `PlowBrushComponent`
- `OwnerVehicle` is explicitly propagated from `KamazBP` into:
  - `BP_WheelSnowTrace_Component`
  - `BP_PlowBrush_Component`
- `PlowLiftHeight` is propagated into `BP_PlowBrush_Component`

This is the main `KamazBP` snow responsibility:

1. resolve the component references
2. cast them to the correct snow BP classes
3. push truck context into them
4. update plow state values used later by the plow writer

In other words, `KamazBP` is the owner and state distributor; the actual snow
write work is delegated to the snow components.

## Runtime Logic: BP_PlowBrush_Component

Primary plow writer Blueprint:

- `/Game/CityPark/SnowSystem/BP_PlowBrush_Component`

### Verified Tick Gate

From `plowbrush_event_graph.json`, the normal write path on `Event Tick` is
gated by:

- `bEnablePlowClearing == true`
- `OwnerVehicle` is valid
- `PlowLiftHeight` is in range:
  - min `0.0`
  - max `0.5`
- vehicle movement can be cast to:
  - `ChaosVehicleMovementComponent`
- forward speed is greater than `MinPlowSpeed`
- elapsed time passes `UpdateRate`

Only after those checks does the Blueprint reach:

- `DrawPlowClearance`

### Current Verified Runtime Problem

From `probe_spawned_plow_writer_runtime.json`:

- manual direct call of `DrawPlowClearance` does change the RT
- `rt_changed = true`
- `rt_stats_before.non_black_samples = 0`
- `rt_stats_after.non_black_samples = 3`

So the writer function itself is alive.

But in the same probe:

- `OwnerVehicle = null`

That is important because the normal tick gate requires `OwnerVehicle` to be
valid before it can write.

### Additional Structural Finding

From the same graph dump:

- `Event Begin Play` exists in `BP_PlowBrush_Component`
- but it is disabled and unlinked

This means the component does not currently self-initialize on BeginPlay. It
depends on upstream setup from `KamazBP`.

### Practical Meaning

The project is currently in this state:

- forced write works
- normal live tick write is still likely blocked by initialization/gating
- the cleanest live blocker is `OwnerVehicle` initialization timing or absence

## Runtime Logic: BP_WheelSnowTrace_Component

Primary wheel writer Blueprint:

- `/Game/CityPark/SnowSystem/BP_WheelSnowTrace_Component`

From `snow_component_defaults.json`:

- wheel writer uses the same RT:
  - `RT_SnowTest_WheelTracks`
- wheel names are:
  - `Wheel_FL`
  - `Wheel_FR`
  - `Wheel_RL`
  - `Wheel_RR`

Role in the system:

- samples wheel contact / wheel positions
- writes wheel-track information into the shared snow RT

## Material Architecture

## 1. Shared Runtime Control Assets

Core shared assets:

- `MPC_SnowSystem`
- `RT_SnowTest_WheelTracks`
- `MF_SnowSystem_Core`

Confirmed MPC usage:

- world bounds live in `MPC_SnowSystem`
- the project later added persistent vector params used by snow math:
  - `WorldBoundsMin`
  - `WorldBoundsMax`
  - `BrushUV`

This is the global coordinate bridge between:

- world-space writers
- render-target UVs
- receiver materials

## 2. Writer Materials

Writer-side materials are not final world shading materials. They are RT write
materials.

Known writer assets:

- `/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_WheelBrush`
- `/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush`
- `/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush_BoxSafe`
- `/Game/CityPark/SnowSystem/BrushMaterials/MI_Snow_PlowBrush_BoxSafe_350x50x100`

`M_Snow_PlowBrush_BoxSafe` is the debug-safe box writer used to stamp a
rectangular plow footprint into the RT. Its job is:

1. convert current brush center into RT-relative space
2. build a 2D rectangular mask from length/width parameters
3. output color/intensity into the render target

This material is for writing the mask, not for rendering visible snow on the
world mesh.

## 3. Receiver Materials

Receiver materials read the RT and convert it into visible snow/no-snow on
playable geometry.

### Landscape Receiver Chain

Observed assets:

- `/Game/CityPark/SnowSystem/M_SnowTestMVP_Landscape1`
- `/Game/CityPark/SnowSystem/M_SnowTest_Landscape`
- `/Game/CityPark/SnowSystem/MI_SnowTest_Landscape`

Important distinction:

- `M_SnowTestMVP_Landscape1` is a prototype/debug receiver
- it was useful for proving the world-position-to-UV math
- but it is too simple to act as the final landscape material for the map

Later safe assignment:

- `Landscape_0` was switched from:
  - `M_SnowTestMVP_Landscape1`
- to:
  - `MI_SnowTest_Landscape`

### Road Receiver Chain

Real playable road under the truck is a static mesh road, not landscape.

Verified real road material chain:

- original instance:
  - `/Game/SnappyRoads/Materials/Old/M_SR_RoadSection001_Inst`
- original parent:
  - `/Game/SnappyRoads/Materials/Old/M_SR_RoadSection001`

Safe isolated receiver assets created for road work:

- `/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_SnowReceiver`
- `/Game/CityPark/SnowSystem/Receivers/M_SR_RoadSection001_Inst_SnowReceiver_Test`

Important safety rule from this work:

- do not reparent the road instance to `M_SnowTestMVP_Landscape1`

That experiment previously caused a D3D12 crash and was rolled back.

## 4. Current Visible Test Zone

Road receiver was applied to the spawn-zone road actors:

- `StaticMeshActor_208`
- `StaticMeshActor_188`
- `StaticMeshActor_142`

Confirmed by:

- `apply_receiver_to_spawn_zone_roads.json`

This means the visible snow debug result is currently expected only on that
limited road cluster, not across every road mesh in the map.

## Data Flow: End-to-End

Current intended runtime flow:

1. `KamazBP` drives the vehicle through Chaos Vehicles.
2. `KamazBP` resolves snow helper components and propagates truck state.
3. `BP_WheelSnowTrace_Component` writes wheel marks into the shared RT.
4. `BP_PlowBrush_Component` writes plow-cleared mask into the same RT.
5. `MPC_SnowSystem` provides shared mapping data:
   - world bounds
   - brush UV
6. receiver materials on road/landscape sample the RT and decide how much snow
   is visible
7. the player sees either white snow, cleared asphalt, or wheel response on the
   playable surface

Short version:

- BP writes dynamic state into RT
- materials read RT and turn it into visible snow
- C++ does not drive snow gameplay directly; it supports safe editor-side
  automation around the Blueprint and material assets

## C++ Layer

## 1. There Is No Main Gameplay C++ Module

For current project logic:

- gameplay snow runtime is not implemented in a dedicated game `Source` module
- the meaningful C++ layer for this project is:
  - `Plugins\BlueprintAutomationEditor`

So the architecture is:

- runtime gameplay = BP + materials
- editor automation = C++

## 2. BlueprintAutomationEditor Module

Plugin descriptor:

- `Plugins\BlueprintAutomationEditor\BlueprintAutomationEditor.uplugin`

Module:

- `BlueprintAutomationEditor`
- type: `Editor`
- loading phase: `Default`

Dependencies from `BlueprintAutomationEditor.Build.cs`:

- public:
  - `Core`
  - `CoreUObject`
  - `Engine`
- private:
  - `AssetRegistry`
  - `BlueprintGraph`
  - `Json`
  - `Kismet`
  - `KismetCompiler`
  - `Projects`
  - `UnrealEd`

This confirms the plugin is an editor authoring tool, not a runtime module.

## 3. C++ Service Split

### Asset/SCS Service

Header:

- `Plugins\BlueprintAutomationEditor/Source/BlueprintAutomationEditor/Public/BlueprintAutomationService.h`

Main role:

- create/load Blueprints
- add variables
- add SCS components
- compile/save Blueprints

### Graph Service

Header:

- `Plugins\BlueprintAutomationEditor/Source/BlueprintAutomationEditor/Public/BlueprintGraphAutomationService.h`

Main role:

- open graphs
- spawn function/event/cast/variable nodes
- link pins with schema validation
- inspect graphs to JSON
- apply graph batches

### Action Service

Header:

- `Plugins\BlueprintAutomationEditor/Source/BlueprintAutomationEditor/Public/BlueprintActionAutomationService.h`

Main role:

- scan available Blueprint actions
- resolve action signatures
- spawn nodes through `UBlueprintNodeSpawner`
- compile and return structured diagnostics

### Python Bridge

Header:

- `Plugins\BlueprintAutomationEditor/Source/BlueprintAutomationEditor/Public/BlueprintAutomationPythonBridge.h`

Exposed bridge methods:

- `RunSmokeTest`
- `RefreshActionIndex`
- `InspectBlueprintEventGraph`
- `InspectBlueprintGraph`
- `ScanBlueprintActions`
- `CompileBlueprint`
- `ApplyGraphBatchJson`
- `ApplyBlueprintGraphBatchJson`
- `SaveBlueprint`

This is the Unreal-facing API used by the local Python tooling.

## 4. Module-Level Commands

From `BlueprintAutomationEditorModule.cpp`, the plugin also exposes console
commands:

- `BlueprintAutomation.RunSmokeTest`
- `BlueprintAutomation.ExportKamazBPSnapshot`
- `BlueprintAutomation.ExportBlueprintSnapshot`
- `BlueprintAutomation.ExportBlueprintGraph`
- `BlueprintAutomation.ApplyBlueprintBatchFile`
- `BlueprintAutomation.ApplyBlueprintBatchFileToGraph`

These write snapshots into:

- `Saved\BlueprintAutomation`

## Python Orchestration Layer

Folder:

- `Pyton_script/unreal_tools`

This is the project-local workflow layer above the plugin.

Important role:

- it does not replace the plugin
- it scripts the plugin and Unreal APIs into safe, narrow helpers
- it stores reproducible diagnostics in JSON

Representative helper groups:

- inspection:
  - `inspect_*`
- graph and bridge helpers:
  - `blueprint_automation_tools.py`
  - `blueprint_graph_dump_tools.py`
- snow/material work:
  - `build_safe_plow_box_brush.py`
  - `rebuild_visible_road_snow_receiver.py`
  - `apply_receiver_to_spawn_zone_roads.py`
  - `apply_landscape_receiver_material.py`
- runtime probes:
  - `probe_spawned_plow_writer_runtime.py`
  - `inspect_runtime_kamaz_plow_actor.py`
- recovery/fixes:
  - road receiver recovery
  - Nanite spam fixes
  - engine material usage-flag fixes

In practice the stack looks like this:

1. C++ plugin offers safe primitive operations
2. Python helpers compose those operations for a concrete task
3. outputs are written to `Saved\BlueprintAutomation`
4. those outputs become the analysis base for further changes

## Diagnostic Source of Truth

For this project, the most reliable source of current architecture state is:

- `Saved\BlueprintAutomation`

Key files:

- `kamazbp_after_plowfix_graph.json`
- `plowbrush_event_graph.json`
- `snow_component_defaults.json`
- `probe_spawned_plow_writer_runtime.json`
- `apply_receiver_to_spawn_zone_roads.json`
- `rebuild_visible_road_snow_receiver.json`
- `apply_landscape_receiver_material.json`

These files are effectively the serialized project analysis.

## Current Verified Snow Status

As of the latest verified analysis:

- road receiver can be made visibly white on the selected road zone
- direct forced `DrawPlowClearance` changes the RT
- the normal live plow trail is still not confirmed as working end-to-end

Current strongest blocker:

- `BP_PlowBrush_Component` depends on `OwnerVehicle`
- in the runtime probe `OwnerVehicle` was still `null`
- its own BeginPlay is disabled, so self-initialization is missing

That makes the current problem a runtime initialization/gating issue more than a
material-read issue.

## Safe Next-Step Logic

For future work, the safe order remains:

1. keep `Kamaz` input and `MOZA` untouched
2. keep `BlueprintAutomationEditor` as the editor C++ tool layer
3. restore or add a safe `OwnerVehicle` self-fallback on
   `BP_PlowBrush_Component`
4. re-run the runtime probe and confirm that normal tick reaches
   `DrawPlowClearance`
5. only after live RT writes are confirmed, continue visual tuning of road
   receiver response

## Short Summary

The project is organized around a content-driven runtime:

- `KamazBP` owns the truck and propagates snow state
- snow writers are Blueprint components
- dynamic snow lives in a shared render target
- materials read that target and show the result on surfaces
- C++ is present mainly as a safe editor automation layer through
  `BlueprintAutomationEditor`
- Python helpers orchestrate inspection, batch graph edits, and diagnostics

That is the real project structure today.
