# AI Sidecar Workspace

This folder stores generated AI workflow artifacts that should stay local and not pollute gameplay history.

## Structure

- `escalations/`:
  - generated senior escalation packets (`.md`)
- `logs/`:
  - wrapper-generated build/smoke logs

## Notes

- Keep this folder in the repo for predictable tooling paths.
- Generated files are ignored by default through `.ai/.gitignore`.
- Use `Tools/AI/make_escalation_packet.ps1` to create escalation packets.
