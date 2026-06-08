# HF1 hard-stop override audit log — window-001

> **Status:** Rolling log per ADR-011 §HF1 + AR-2026-04-25-001 §Rollback + AR-2026-05-16-001 §HF1 split.
> **Format:** chronological newest-on-bottom; one block per override invocation.
> **Tier:** Tier 1 engineering candidate; not signed validation; not benchmark agreement.
> **Predecessor:** window-000 archived at `reports/archive/hf_audit_window-000.md`. Window-000 was sealed 2026-05-16 by AR-2026-05-16-001 (the HF1.7 split + `*-candidate` carve-out). Window-001 opens with HF1.7b carve-out IN FORCE, so `golden_samples/*-candidate/` writes no longer trigger the override path.

The HF1 path-guard (`scripts/hf1_path_guard.py`) blocks staged diffs that
touch HF1.1-HF1.9 paths. The `HF1_GUARD_OVERRIDE='<reason>'` env-var
escape hatch is documented in ADR-011 §HF1 as an emergency path; every
invocation MUST be recorded here for post-hoc audit.

This log enables: (a) review-time audit of HF1 override usage, (b)
detection of override-abuse patterns (silent normalization of the
override → motivation for an HF1.x split into a non-protected
carve-out subdirectory), (c) bounded archival via the rolling-window
naming `reports/archive/hf_audit_window-NNN.md`.

---

## Window-001 opening notes (2026-05-16)

AR-2026-05-16-001 (Phase 13 D ratification) split HF1.7:

* **HF1.7a** `golden_samples/<signed-registry>/` — signed-registry whole-directory read-only (hard-stop; the `^GS-\d{3}$` shape is sealed FM-04b P8 packet surface).
* **HF1.7b** `golden_samples/*-candidate/` — WRITABLE per the FM-04a Tier 1 candidate binding constraint.

The path-guard's `_is_candidate_carveout` helper recognizes the
carve-out at staging time so `*-candidate` writes pass without
override. Window-001 therefore captures ONLY:

1. Overrides on HF1.1-HF1.6, HF1.7a (signed-registry), HF1.8, HF1.9 surfaces (true emergency invocations).
2. Any `*-candidate` writes that accidentally tripped the guard (would indicate carve-out helper bug; tracked as a Phase 14 carry-forward if observed).

A clean window-001 (no `*-candidate` overrides) is the operational success criterion for AR-2026-05-16-001.

---

## Audit trail discipline (post-Phase-13)

Future override invocations follow the same template:

```markdown
## YYYY-MM-DD — <slice / PR / commit summary>

**Context:** <why the override was needed; one paragraph>
**Override invocations:**
* Commit `<sha>` — `HF1_GUARD_OVERRIDE='<verbatim justification>'`
**Audit outcome:** <PASS / FLAG / FAIL with explanation>
**Carry-forward action:** <ADR amendment / re-architecture / accept>
```

The log is append-only within a window; window rollover follows the
ADR-011 §Rollback rolling-window protocol (`hf_audit_window-NNN.md`).
