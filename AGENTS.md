# Kamaz_Cleaner — Codex Instructions

## Project context

Unreal Engine 5.7.4 project.

Main active project: `Kamaz_Cleaner`.

Current priority: full-map snow removal pipeline in isolated test map.

Known working test map:
- `/Game/LandscapeDeformation/Maps/SnowMap_FullRemoval_Test`

Known working full-map snow removal pipeline:
- `KamazSnowPlowCaptureDeformer / PlowDeformerMesh`
- `BP_SnowMaskWriter_FullMap`
- `M_SnowMaskStamp_WS`
- `RT_SnowRemoval_A_FullMap`
- `RT_SnowRemoval_B_FullMap`
- `MI_VHM_SnowLand_FullMap`
- `M_VHM_SnowLand_FullMap`
- `VirtualHeightfieldMesh1`

Confirmed fact:
- Snow clears correctly when `BP_SnowMaskWriter_FullMap` sends `RemovalStrength = 1.0` to `M_SnowMaskStamp_WS`.
- Therefore the full-map RT/VHM/material pipeline is alive.
- Current unstable area is only the calculated `RemovalStrength / RS / HeightGate` chain.

## Strong safety rules

Do not modify these unless explicitly instructed:
- original `/Game/LandscapeDeformation/Maps/SnowMap`
- `BP_Capture`
- `RT_Capture`
- `RT_Persistent`
- `M_DepthCheck`
- `M_DrawToPersistent`
- `MPC_Capture`
- old moving-window capture pipeline
- C++
- vehicle physics
- input
- MOZA
- GameMode
- camera
- VHM/RVT bounds
- MinMax texture
- receiver materials

Do not edit Blueprint `.uasset` graph directly unless an Unreal Editor bridge/tool is explicitly active and the user asked for it.

Prefer read-only diagnosis unless the user explicitly asks for a write.

If editing is requested, modify only the named assets.

If Unreal save fails, stop immediately and report the exact error.

## Current recommended fallback

In:
- `/Game/LandscapeDeformation/Generated_FullMap/BP_SnowMaskWriter_FullMap`

Known working fallback:
- `SetScalarParameterValue("RemovalStrength").Value = 1.0`

Do not reconnect the experimental HeightGate/LineTrace/RS chain without explicit instruction.

## Git rules

Before staging:
- run `git status --short`

Never use:
- `git add .`
- broad staging of `Content/`
- broad staging of `Saved/`
- broad staging of `Config/`

Stage only explicitly requested files.

Generated/temporary automation JSON files under `Saved/BlueprintAutomation/` should not be committed unless explicitly requested.

## Environment risks

VPN/proxy can break local Unreal/Aura services.
Important local endpoints:
- `127.0.0.1:41200` = Aura/Autonomix Unreal bridge
- `[::1]:8558` = Unreal Zen/DDC
- `127.0.0.1:11434` = Ollama, if used

If logs show repeated connection refused to `127.0.0.1:41200`, treat Aura/Autonomix bridge as unstable.

If logs show DDC writable node errors, do not edit assets until DDC/Zen is healthy.

## Useful commands

Check repo state:
```powershell
git status --short