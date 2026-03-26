# Persistent Snow-State Architecture V1

## Problem Statement

The project no longer needs a local "effect around the truck". It needs a
persistent world snow-state system for a large street scene.

The system must support:

- Kamaz driving over a large street corridor
- wheel tracks that remain after the truck leaves
- plow clearing driven by the actual skeletal plow blade width
- persistent state that survives movement across the map section
- road static meshes as first-class playable surfaces

This is not a landscape-first problem and it should not be solved by one
"magic" road material.

## Core Principle

Render targets and RVT are presentation and working buffers, not the only
source of truth.

The source of truth should be a world-cell snow-state model:

- world is divided into fixed cells
- each cell owns persistent snow-state data
- writers update cells
- receivers visualize cells
- RT/RVT mirrors may exist for fast stamping and material sampling
- CPU-side or serialized tile data remains the authoritative persistent state

## V1 Architecture Overview

### Runtime Layers

1. `SnowStateWorldSubsystem`
- authoritative registry of active and persisted snow cells
- resolves world position to `CellId + LocalUV`
- tracks dirty cells
- loads and saves cell state

2. `SnowWriterLayer`
- wheels and plow produce write events in world space
- writer events are routed into intersected cells

3. `SnowPresentationLayer`
- builds or refreshes GPU mirrors for active cells
- feeds receiver materials on road, curb, sidewalk, shoulder

4. `SnowReceiverLayer`
- road and other surface materials read cell-local masks
- no writer logic inside receiver materials

## 1. World Cell Architecture

### Cell Shape

Use fixed world-aligned square cells.

Recommended V1 size:

- `64m x 64m` per cell

Reason:

- large enough to keep cell count manageable
- small enough for localized updates and partial streaming
- fits urban road segments, sidewalks, curb tops, and shoulders

### Cell Resolution

Recommended V1 mask resolution:

- `512 x 512` per cell

This gives about `12.5 cm` per texel on a `64m` tile, which is good enough for:

- tire tracks
- plow strip edges
- coarse curb and sidewalk transitions

### Cell ID

Use integer world tile coordinates:

- `CellX = floor(WorldX / CellSize)`
- `CellY = floor(WorldY / CellSize)`

Every write and every receiver query first resolves to `CellId`.

### Cell Data Model

Each cell should own a persistent data record like:

- `CellId`
- `WorldMin`
- `WorldMax`
- `SnowStateCPU`
- `ActiveGpuMirror`
- `DirtyRect`
- `LastTouchedTime`
- `ReceiverSet`
- `SurfaceFamilyCoverage`

The important point is:

- the CPU/serialized tile payload is authoritative
- the GPU mirror is a transient working copy

## 2. Snow Receiver Surface Families

Do not treat all surfaces as one generic "snow receiver". Split them into
families with different response rules.

### Road

Examples:

- asphalt driving lanes
- intersections
- large road static meshes

Rules:

- strongest wheel response
- strongest plow clear response
- road should reveal dark asphalt quickly under plow

### Curb Top

Examples:

- top faces of curb meshes
- edge strips between road and sidewalk

Rules:

- weaker wheel response than road
- plow can affect only near blade edge or oversweep
- often keeps more snow than road after a pass

### Sidewalk

Examples:

- pedestrian sidewalk static meshes
- plaza walk surfaces

Rules:

- weak heavy-wheel response
- usually no normal plow clearing unless vehicle or blade really overlaps
- should later support footprint logic more than road logic

### Shoulder

Examples:

- roadside snow edges
- rough verge beside road
- parking edge zones

Rules:

- medium wheel response
- partial plow influence
- can preserve more residual snow than main road

### Family Assignment Rule

Do not infer family only from material names.

Use one of:

- actor/component tags
- data asset mapping by mesh/material slot
- explicit receiver component metadata

V1 recommendation:

- add receiver-family tags per component or per material slot record

## 3. Writer Path: Wheels + Plow

Writers should produce world-space write events, not directly own the final
visual presentation.

### Wheel Writer Path

Input:

- existing `BP_WheelSnowTrace_Component`

Per wheel event:

1. get wheel contact world position
2. resolve world position to `CellId`
3. compute local UV in that cell
4. stamp an elliptical wheel brush into the tile
5. update snow channels according to wheel policy

Recommended wheel effect:

- reduce `R` slightly
- increase `B` for compacted/track influence
- optionally blend wet/compressed response later

### Plow Writer Path

Input:

- existing `BP_PlowBrush_Component`
- attached to the real plow assembly on `SM_FrontHitch`

Per plow event:

1. derive blade centerline and width in world space
2. build a swept strip or box over the blade footprint
3. intersect that strip with all overlapped cells
4. stamp a plow brush into each overlapped cell
5. reduce snow amount strongly along the plow strip

Recommended plow effect:

- strongly reduce `R`
- raise `G` as explicit plow-clear influence
- optionally later push residual snow toward edge cells

### Writer Channel Policy

Recommended V1 semantics:

- `R` = remaining snow amount
- `G` = plow clear mask
- `B` = wheel compact / track mask
- `A` = reserved

This gives a real state model instead of "just green trails".

## 4. Storage Strategy for Dirty Tiles

This is the critical persistence layer.

### Authoritative Representation

Per cell, keep an authoritative CPU/serialized payload.

V1 practical format:

- one tile payload per cell under map-specific folder
- compressed binary or PNG-like grayscale/packed channels

Example location:

- `Saved/SnowState/MoscowEA5/Tile_X_Y.bin`

The exact file format is secondary. The important point is:

- active GPU mirrors can be rebuilt from the saved tile payload

### In-Memory Active Tile Cache

Keep only nearby cells active on GPU.

Recommended V1 policy:

- active radius around Kamaz: `1-2` cells
- LRU or time-based eviction for untouched cells

Each active tile keeps:

- `CPU state`
- `working RT mirror`
- `dirty flag`
- `dirty rect`

### Dirty Tile Tracking

After every wheel/plow write:

- mark cell dirty
- expand dirty rect
- record last touched time

Do not flush to disk every frame.

Recommended V1 flush policy:

- autosave dirty tiles every few seconds
- also flush on map unload / checkpoint / editor end PIE

### Readback Strategy

Because existing writers already stamp into RT-like buffers, V1 can use a mixed
approach:

- writer stamps into active GPU mirror
- periodic readback updates the authoritative CPU payload
- CPU payload is saved to disk

That keeps current material writer logic useful without making RT the only
truth.

## 5. Presentation Strategy

Receivers should read per-cell snow state, not invent it.

### Active Presentation

For active nearby tiles:

- each tile has a GPU mirror texture
- receiver materials sample the correct tile using tile bounds and local UV

### Receiver Material Responsibility

Receiver materials should only do:

- choose base surface look
- choose snow look
- blend using `R/G/B` state
- apply family-specific response tuning

They should not:

- decide whether snow exists globally
- create ad hoc local masks unrelated to tile state

## 6. Minimal V1 Rollout

Do not deploy across the whole map first.

Use one limited road corridor near the current Kamaz test zone.

### V1 Test Zone

Recommended rollout area:

- a straight road corridor around the current spawn/test road actors
- approximately `256m x 128m`

Suggested grid:

- `4 x 2` cells
- each cell `64m x 64m`
- total `8` cells

This covers:

- road lanes
- curb tops
- sidewalks
- shoulders near the spawn corridor

### V1 Surface Families in Scope

Implement these first:

- `Road`
- `CurbTop`
- `Sidewalk`
- `Shoulder`

Skip broad landscape integration for V1 unless needed for zone boundaries.

### V1 Writer Scope

Keep current writers and route them into the cell system:

- `BP_WheelSnowTrace_Component`
- `BP_PlowBrush_Component`

For V1, do not redesign the vehicle input or the plow attachment logic beyond
necessary placement correctness.

### V1 Persistence Scope

For V1, persistence means:

- state remains after the vehicle leaves the area
- state survives active-tile unloading and reloading

Optional later:

- save/load between play sessions

### V1 Success Criteria

V1 is successful when:

1. Kamaz drives through the corridor
2. wheels leave tracks on road-family surfaces
3. plow clears a visible strip on road-family surfaces
4. state remains after Kamaz leaves the immediate area
5. re-entering the corridor shows the same state restored from tile storage

## 7. Why This Is Better Than a Material-Only Fix

A material-only fix can show snow, but it cannot define persistent world state.

This architecture separates:

- simulation state
- writing
- storage
- visualization

That is the minimum structure needed for a large street scene.

## 8. Recommended Immediate Next Step

Implement only the V1 corridor architecture:

1. define `64m x 64m` tile grid for the spawn road zone
2. create authoritative tile records and dirty tracking
3. route existing wheel/plow writers into those tiles
4. mirror active tiles to GPU textures
5. make road-family receivers read those tile mirrors

Only after that should the system expand to more road segments or landscape.
