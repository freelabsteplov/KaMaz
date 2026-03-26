# Hybrid Local-First AI Workflow (Unreal + VS Code)

## Purpose

This project uses a hybrid workflow:

- default path: local-first assistant loop (cheap daily work)
- escalation path: senior model (GPT-5.4 / Codex) only for hard cases

The UX stays inside VS Code via tasks and repo-local wrapper scripts.

## Day-to-Day Flow

1. Start in local mode (`/local`) and scope a narrow task.
2. Apply small edits (prefer 1-3 files).
3. Validate with `Build Editor` task.
4. Read logs with `Read Last Logs` task.
5. If still blocked after two compile-pass failures or conflicting local guidance, escalate with `Make Escalation Packet`.
6. Bring senior output back into local loop as small execution batches.

## Routing Policy

### Local default tasks

- autocomplete / next edit
- narrow `.cpp` changes
- explain existing code
- summarize build/log output
- local review of active file
- boilerplate by established pattern
- narrow, low-risk edits in 1-3 files
- simple tooling/config updates

### Senior escalation triggers

- architecture across multiple modules
- C++ <-> Blueprint boundary design
- `.h` edits with reflection macros (`UCLASS/USTRUCT/UENUM/UPROPERTY/UFUNCTION`)
- complex refactor
- crash/root-cause analysis
- perf, replication, networking, async loading, GC, lifetime issues
- plugin/tooling architecture design
- local route failed compile-pass twice or produced contradictory plans

## VS Code Tasks (Wrapper-Only)

Use `Terminal -> Run Task`:

- `Build Editor`
- `Read Last Logs`
- `Make Escalation Packet`
- `Optional Smoke Test`

Tasks call only project wrappers in `Tools/AI/`:

- `build_editor.ps1`
- `read_last_logs.ps1`
- `make_escalation_packet.ps1`
- `run_smoke.ps1`

## Recommended Prompt Tags

These are workflow tags (not a hard command system):

- `/local`: local-first narrow implementation
- `/senior`: escalation request when triggers are met
- `/rootcause`: deep investigation for non-obvious failures
- `/review`: risk-focused review (bugs, regressions, missing tests)
- `/architect`: design options with tradeoffs before coding

## Senior Escalation Packet Loop

Create packet with task `Make Escalation Packet` or:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Tools\AI\make_escalation_packet.ps1
```

Packet is saved in `.ai/escalations/` and must include:

- Goal
- Hypothesis
- Files to touch
- Ordered steps
- Invariants / Do-not-break rules
- Validation
- Rollback notes

The packet also includes diff summary, recent logs, and open questions.

## Local Endpoint Setup (Current Local Default)

Current local-default wiring for this repo:

- `LOCAL_AI_BASE_URL=http://127.0.0.1:11434/v1`
- `LOCAL_AI_MODEL=qwen2.5-coder:32b`
- `LOCAL_AI_AUTOCOMPLETE_MODEL=qwen2.5-coder:32b`

Quick validation commands:

```powershell
ollama ls
ollama run qwen2.5-coder:32b "Reply with exactly: OLLAMA_OK"
```

Stability note for large local models:

- If runner crashes on first token load, set `OLLAMA_CONTEXT_LENGTH=2048` and restart `ollama serve`.

Senior path stays opt-in:

- `SENIOR_AI_BASE_URL`
- `SENIOR_AI_API_KEY`
- `SENIOR_AI_MODEL`

Provider/model IDs are placeholders by design. No cloud model is hardcoded as default baseline.

## Unreal-Specific Safety Rules

1. Narrow `.cpp` edits are good candidates for local-first and quick validate loops.
2. Header/reflection/UObject/module-boundary edits are high-risk and require stricter validation.
3. Live Coding is not sufficient validation for risky structural changes.
4. Always distinguish:
   - local logic iteration
   - structural change
   - multi-system debugging
   - Blueprint/C++ boundary issues

## Cost Discipline

- Keep local path as default for normal development.
- Escalate only on real trigger conditions.
- Send compact escalation packets instead of full noisy context.
- Return from senior path to local loop quickly after direction is clear.

## Current TODO Placeholders

- Set real local endpoint/provider credentials via env vars.
- Set senior endpoint/provider credentials via env vars.
- Optionally wire MCP server command in `.codex/config.toml`.
- If needed, tune `run_smoke.ps1 -RunHeadless` map/command for your machine.
