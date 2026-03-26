# Snow Material Architecture

## Current Verified State

- Runtime writers already exist:
  - `/Game/CityPark/SnowSystem/BP_WheelSnowTrace_Component`
  - `/Game/CityPark/SnowSystem/BP_PlowBrush_Component`
- Both writers now target:
  - `/Game/CityPark/SnowSystem/RT_SnowTest_WheelTracks`
- Current map-level snow receiver reference on `MoscowEA5`:
  - `/Game/CityPark/SnowSystem/M_SnowTestMVP_Landscape1`
- Current support assets:
  - `/Game/CityPark/SnowSystem/MF_SnowSystem_Core`
  - `/Game/CityPark/SnowSystem/MPC_SnowSystem`
  - `/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_WheelBrush`
  - `/Game/CityPark/SnowSystem/BrushMaterials/M_Snow_PlowBrush`

This means the write side is already in place. The next scaling step is the
receiver side: how different surfaces read the same snow masks and present
different snow looks.

## Target Surface Types

Use different receiver materials for different surface families:

- `Landscape`
  - broad snow coverage
  - softer wheel response
  - large-scale accumulation and blending
- `Road_SM`
  - sharper wheel tracks
  - faster reveal of asphalt below snow
  - stronger plow clearing response
- `Curb_Sidewalk_SM`
  - thinner snow layer by default
  - stronger pedestrian footprint response
  - weaker heavy-wheel response than roads

The writers can stay shared. The receiver materials should be specialized.

## Channel Layout

Recommended single-mask layout for the first scalable version:

- `R` = wheel tracks
- `G` = plow cleared mask
- `B` = footprints / pedestrian detail
- `A` = reserved for snow coverage, wetness, or blend bias

Notes:

- The current project already writes dynamic snow information into one render
  target. Keep that approach first.
- If later isolation becomes necessary, split into multiple RTs only after the
  first visible result is stable.

## Material Layers

Each receiver material should be built from the same conceptual layers:

1. Base surface
   - asphalt, concrete, curb, landscape ground
2. Base snow look
   - uses your `T_SnowV2P3_*` textures
3. Dynamic snow mask
   - sampled from `RT_SnowTest_WheelTracks`
4. Surface-specific response
   - how wheel, plow, and footprint masks affect the surface

## Recommended Texture Usage

Your `T_SnowV2P3_*` set is suitable for the visible snow layer:

- `Diffuse` -> snow albedo
- `Normal` -> snow surface normal
- `Roughness` -> snow roughness
- `AO` -> optional secondary modulation
- `Displacement` -> optional later, not required for first pass

Footprint-like black and white textures should not replace dynamic runtime
masks. Use them as detail overlays multiplied by the runtime mask when needed.

Example:

- `wheel tracks` = runtime `R` mask
- `footprint detail pattern` = static texture
- final pedestrian impression = `runtime B * footprint detail texture`

## Receiver Material Family

Recommended material structure:

- `M_SnowReceiver_Master`
  - shared logic for reading the RT
  - shared base snow controls
  - shared channel unpacking
- `MI_SnowReceiver_Landscape`
  - tuned for landscape snow depth and softness
- `MI_SnowReceiver_RoadSM`
  - tuned for roads and asphalt reveal
- `MI_SnowReceiver_CurbSM`
  - tuned for curbs and sidewalks

If existing project materials must stay separate, still keep the common math in
`MF_SnowSystem_Core` or a new shared material function.

## Response Rules By Surface

### Landscape

- high base snow coverage
- wheel tracks should be wider and softer
- plow should clear broad strips
- footprints should blend softly

### Road Static Mesh

- medium base snow coverage
- wheel tracks should be darker, sharper, and reveal road quickly
- plow mask should strongly remove snow
- footprints should be weak unless it is a sidewalk road section

### Curbs and Sidewalks

- low to medium base snow coverage
- wheel tracks should have limited effect
- footprints should dominate
- edge accumulation can be stronger than on flat roads

## Plow Brush Attachment

For `KamazBP`, the correct runtime direction is:

- keep `BP_PlowBrush_Component` as the writer
- anchor it to the front plow assembly
- use `SM_FrontHitch` as the attachment source
- preferably attach to a dedicated socket or scene anchor on the plow assembly,
  not just an arbitrary component transform

Reason:

- `BP_PlowBrush_Component` uses its own world position when writing into the
  snow render target
- if its transform does not follow the actual blade position, the visual clear
  strip will drift away from the mesh

## Minimal Implementation Order

1. Confirm which current level components actually use snow receiver materials.
2. Make one visible receiver work on the real playable surface first.
3. Convert that logic into a shared receiver master.
4. Create three tuned instances:
   - landscape
   - road static mesh
   - curb/sidewalk static mesh
5. Add footprint detail only after wheel and plow are visibly correct.

## Recommended Next Step In This Project

Do not expand into many materials yet.

First:

- verify the real receiver under `Kamaz` on `MoscowEA5`
- make one visible snow receiver work there
- confirm that wheel and plow marks are visible in play

Only after that:

- connect `T_SnowV2P3_*`
- split receivers by surface type
- add footprint-specific presentation

