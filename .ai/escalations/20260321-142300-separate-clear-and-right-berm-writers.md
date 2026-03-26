Goal
- Separate plow clearing from right-side berm so clearing continues to work and berm is unambiguously on the vehicle/plow right side by movement direction.

Hypothesis
- The current single widened RVT stamp plane mixes clear mask and berm signal, so UV orientation or overlap causes additive berm to interfere with clearing.
- Splitting into two writer planes will remove overlap and make right-side placement deterministic.

Files to touch
- Source/Kamaz_Cleaner/Public/Snow/SnowRuntimeTrailBridgeComponent.h
- Source/Kamaz_Cleaner/Private/Snow/SnowRuntimeTrailBridgeComponent.cpp
- Pyton_script/unreal_tools/apply_repeat_clearing_accumulation.py

Ordered steps
1. Add separate berm ISM component/material arrays to runtime bridge.
2. In EnsureRvtStampComponent, create clear-tier and berm-tier components with separate MIDs.
3. In AddRvtStampInstance, place clear stamps at source footprint and berm stamps as a separate 20% width strip on world right side.
4. Simplify writer material apply script so clear-only planes write Mask/Specular and berm-only planes write BaseColor only.
5. Build editor.
6. Apply assets through UnrealEditor-Cmd and verify saved JSON/timestamps.

Invariants / Do-not-break rules
- Do not touch old RT pipeline.
- Do not change receiver material semantics beyond existing BaseColor.R berm read path.
- Keep current plow clearing behavior working.
- Keep repeat accumulation path intact.
- Keep debug source/area boxes visible.

Validation
- C++ build succeeds.
- apply_repeat_clearing_accumulation.json updates with no error.
- M_RVT_DebugWriter_MVP.uasset timestamp changes.
- In PIE, clear zone remains separate and berm appears only on right side.

Rollback notes
- Re-run apply script with previous single-plane graph if separate clear/berm split causes regression.
- Remove berm-tier arrays/components from bridge if needed and revert to prior commit state.
