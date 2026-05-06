# FF-08 Symlink Bypass Fix Claude Audit

- **Reviewer:** local Claude Opus 4.7
- **Mode:** reviewer/auditor only, tools disabled
- **Command:** `claude --model opus --tools "" --no-session-persistence`
- **Verdict:** `APPROVE`
- **Scope:** fix for GitHub Codex P1 finding on symlinked `GS-###`
  directories.

## Reviewer Result

Claude Opus returned `APPROVE`.

The reviewer confirmed that:

- `discover_sample_dirs` no longer accepts symlinked `GS-###` directories;
- `validate_registry` explicitly reports `GS-###` symlinks as validation
  errors rather than silently accepting borrowed metadata/artifacts;
- `Path.is_symlink()` is checked before `Path.is_dir()`, avoiding the
  symlink-following behavior that caused the bypass;
- the new test exercises the exact bypass vector and asserts the structured
  validation error;
- targeted and full verification passed.

Non-blocking observations:

- `golden_root.iterdir()` is traversed twice; this is acceptable for the current
  registry size.
- A registry containing only a symlinked `GS-###` reports both the symlink error
  and the absence of valid signed samples; both signals are accurate.
- Bind-mount style escapes are out of scope for this P1 fix.
