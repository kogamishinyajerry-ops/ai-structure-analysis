# HF1 hard-stop override audit log — window-000 (ARCHIVED)

> **Status:** Archived window-000. Sealed 2026-05-16 by AR-2026-05-16-001 (ADR-011 §HF1 split into HF1.7a + HF1.7b carve-out for `*-candidate`). The override-driven `*-candidate` writes captured below were the load-bearing carry-forward evidence for the amendment. The next rolling window (`reports/hf_audit.md` head) opens at window-001 with the carve-out in force.
> **Format:** chronological newest-on-bottom; one block per override invocation.
> **Tier:** Tier 1 engineering candidate; not signed validation; not benchmark agreement.

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

## 2026-05-16 — FM-04a Phase 12 C `golden_samples/*-candidate/` writes

**Context:** Phase 12 C ships three new Tier 1 candidate cases as
real-runnable evidence the modal axis works end-to-end (FM-04a
binding constraint explicitly authorizes `*-candidate` directory
writes inside `golden_samples/**`):

* `golden_samples/modal-cantilever-candidate/`
* `golden_samples/modal-cantilever-stiff-candidate/`
* `golden_samples/cylinder-pv-extended-candidate/`

HF1.7 (`golden_samples/**` — 全部只读) is whole-directory; it does
not currently carve out `*-candidate` subpaths. Slice C used
`HF1_GUARD_OVERRIDE` with the binding-constraint justification per
override invocation.

**Override invocations:**

* Commit `75a21cd` — `HF1_GUARD_OVERRIDE='Phase 12 C — *-candidate
  fixture writes are explicitly allowed by the FM-04a binding
  constraint; HF1.7 carve-out for *-candidate paths queued as
  ADR-011 HF1.7 amendment for Phase 13.'`

**Audit outcome:** PASS — every override invocation matched the
FM-04a binding-constraint surface (`*-candidate` only; no
signed-registry pattern `^GS-\d{3}$`; no Phase 11-and-earlier seed
case modifications). The per-fixture writes touched only the new
candidate directories.

**Carry-forward action:** Phase 13 carry-forward §3 — file ADR-011
amendment AR-2026-XX-XXX-002 carving out `golden_samples/*-candidate/`
from HF1.7 as a structurally-permitted write zone (analog of the
PR-protected-zone carve-out for `docs/adr/` in AR-2026-04-25-001 §3).
The override-abuse mitigation: the FM-04a binding-constraint surface
is small (`*-candidate` suffix is unambiguous + automatable in
guard.py); a 1-line regex change closes the override path entirely.

---

## Audit trail discipline (post-Phase-12)

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
