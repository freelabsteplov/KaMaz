# Goal

Publish a search-friendly Road2 snow pipeline snapshot to the `KaMaz` GitHub repository so the full code, scripts, and critical Blueprint/material diagnostics are available for repository-wide analysis.

# Hypothesis

The project already contains enough C++, Python, config, and BlueprintAutomation evidence to answer the Road2 investigation questions. The missing step is selective Git exposure: include the Snow source tree, Unreal automation scripts, config files, relevant markdown, and compact text diagnostics from `Saved/BlueprintAutomation` without pushing transient binaries, PNG captures, or cache noise.

# Files to touch

- `.gitignore`
- `Docs/Road2SnowPipeline_SearchMap.md`
- `.ai/escalations/20260326-road2-snow-pipeline-github-access.md`
- `Saved/BlueprintAutomation/road2_snow_pipeline_manifest.json`
- `Saved/BlueprintAutomation/plowbrush_component_road2_snow_slice.json`
- `Saved/BlueprintAutomation/kamazbp_road2_snow_slice.json`

# Ordered steps

1. Verify which Road2 snow pipeline code and diagnostics already exist locally.
2. Open Git exposure for `.ai/escalations/*.md` and selected text files in `Saved/BlueprintAutomation/`.
3. Add a human-readable search map that points GitHub search to the correct Snow, Road2, carrier, receiver, writer, and trail entry points.
4. Generate compact JSON slices from the existing Blueprint graph dumps so `BP_PlowBrush_Component` and `KamazBP` are searchable without relying on oversized raw dumps.
5. Add a manifest that maps investigation questions to exact files.
6. Stage the Snow source tree, automation scripts, config files, relevant docs, wrappers, and selected diagnostics for GitHub publication.
7. Validate the staged file set and push if the remote accepts it.

# Invariants / Do-not-break rules

- Do not revert unrelated user changes.
- Do not publish `Saved/` cache noise, PNG captures, or binary backups.
- Do not require `.uasset` parsing to understand the Road2 investigation path.
- Keep the repo searchable by prioritizing text diagnostics and compact summaries over giant generated dumps.

# Validation

- `git diff -- .gitignore`
- `git status --short`
- `git diff --cached --stat`
- `git ls-files Source/Kamaz_Cleaner/Private/Snow Source/Kamaz_Cleaner/Public/Snow Pyton_script/unreal_tools Config Docs .ai/escalations Saved/BlueprintAutomation`
- `rg -n -i "road2|snow|plow|rvt|carrier|receiver|trail" Docs/Road2SnowPipeline_SearchMap.md Saved/BlueprintAutomation/road2_snow_pipeline_manifest.json`

# Rollback notes

- Remove the selective unignore rules from `.gitignore`.
- Drop the curated `Saved/BlueprintAutomation/*.json` files from the index if the repo becomes too noisy.
- Keep all existing local diagnostics on disk even if the Git slice is reduced later.

# Current diff summary

- The Snow C++ source tree exists locally under `Source/Kamaz_Cleaner/Private/Snow/` and `Source/Kamaz_Cleaner/Public/Snow/`.
- The Unreal automation script corpus exists locally under `Pyton_script/unreal_tools/`.
- Config diffs relevant to the current Road2 investigation exist in `Config/DefaultEngine.ini` and `Config/DefaultGame.ini`.
- `Saved/BlueprintAutomation/` already contains the needed Road2, plow, carrier, receiver, RVT, and runtime trail diagnostics, but Git currently hides them.

# Relevant log excerpts

- `Saved/BlueprintAutomation/probe_road2_runtime_height_receiver.json` confirms the runtime receiver path is probeable as text.
- `Saved/BlueprintAutomation/verify_road2_offline_baseline_before_runtime.json` and `Saved/BlueprintAutomation/verify_road2_height_only_no_stamp.json` already preserve the Road2 baseline and no-stamp comparisons.
- `Saved/BlueprintAutomation/trace_m_snowreceiver_rvt_height_mvp.json` provides a text trace for the active Road2 receiver parent material.

# Open questions

- Whether the current Git remote accepts a direct push from this workspace still needs to be verified live.
- If GitHub indexing proves too strict for one of the larger graph dumps, the compact slices should remain the canonical search entry point.
