## TAA report — FM-04a Phase 8 B @ 270e0d0

- **Commit audited**: `270e0d0` — "feat(FM-04a/Phase8-B): signoff history endpoint + frontend integration + slice-A TAA archive"
- **Auditor**: Independent TAA (general-purpose agent, slice-B scope; not the author of `270e0d0`)
- **Date**: 2026-05-16
- **Binding blueprint**: `.planning/FM-04A_PHASE8_BLUEPRINT.md` (locked at `2e640f6`, predates all Phase 8 code commits)
- **Audited paths** (10 files; diff stat from `git show 270e0d0 --stat`):
  - `backend/app/api/routes/signoff_history.py` (+44 lines, NEW)
  - `backend/app/main.py` (+3 lines: router registration)
  - `backend/app/services/reporting/signoff_record.py` (+124 lines: HTTP-facing report builder + two-list forbidden-token design)
  - `frontend/src/App.tsx` (+11 lines: `latestSignoff` state lift + props plumb)
  - `frontend/src/components/SignoffHistoryPanel.tsx` (+208 lines, NEW)
  - `frontend/src/components/TrustScoreGauge.tsx` (+35 lines: 3 optional props + signoff subline)
  - `frontend/src/signoffHistoryClient.ts` (+166 lines, NEW)
  - `frontend/test/SignoffHistoryPanel.test.tsx` (+145 lines, NEW; 7 vitest cases)
  - `tests/test_phase8_signoff_history_endpoint.py` (+150 lines, NEW; 6 pytest cases)
  - `.planning/phase8_audit_reports/A.md` (+149 lines: slice-A TAA archive)
- **Files-touched constraint**: zero HF1 hard-stop zone paths; zero `^GS-\d{3}$` registry edits; zero `golden_samples/**` writes; zero Linear/Notion/external-write surfaces.

---

### Evidence-driven findings (numbered)

1. **Blueprint precedence holds**. Blueprint was sealed at `2e640f6` (immediately preceding slice-A `6dd7be4` and slice-B `270e0d0`). All 17 anti-gaming guards in §4 are binding on this slice.

2. **Route prefix + envelope shape match blueprint §3.B verbatim**. `backend/app/api/routes/signoff_history.py:26` declares `APIRouter(prefix="/signoff-history", tags=["signoff-history"])`; combined with the `/api/v1` prefix in `main.py:116` (`app.include_router(signoff_history.router, prefix="/api/v1")`), the live URL is `GET /api/v1/signoff-history/<case-id>`. The envelope (`SignoffHistoryReport`, lines 343–360 of `signoff_record.py`) carries every required field: `schema_version`, `case_id`, `claim_tier`, `claim_boundary`, `generated_at_utc`, `record_count`, `records`, `claim_impact`. The `_report_to_dict` serializer (lines 390–400) emits all 8 fields under snake_case keys, matching the test fixtures.

3. **Two-list forbidden-token design is documented and load-bearing**.
   - `_FORBIDDEN_NOTES_TOKENS` (lines 144–151, 6 tokens): `validated against`, `perforation completed`, `bullet-through-steel complete`, `validated physics`, `signed validation`, `benchmark agreement`. Applied to **reviewer-provided** notes at write time via `_assert_no_overclaim` (line 307, called from `write_signoff_record` line 227).
   - `_ENVELOPE_FORBIDDEN_TOKENS` (lines 153–158, 4 tokens): same as the notes list **minus** `signed validation` + `benchmark agreement`. Applied to the **report envelope** at build time via `_assert_no_overclaim_in_report` (line 403, called from `build_signoff_history_report` line 382).
   - The docstring comment block on lines 124–142 explicitly explains the divergence: the envelope's own `claim_impact` field contains "do NOT substitute for signed validation, ...constitute benchmark agreement..." inside compound disclaimer sentences where the simple 4-byte `not <claim>` lookback cannot accept the construction. Excluding those two tokens from the envelope audit is the same honest fix pattern used in Phase 7 B (`ENVELOPE_FORBIDDEN_TOKENS=4` vs `CATALOG_FORBIDDEN_TOKENS=6`). Intentional, documented, not a stealth weakening.

4. **`build_signoff_history_report()` calls the narrower envelope audit**. Verified at `signoff_record.py:382` — `_assert_no_overclaim_in_report(report)` runs against `_ENVELOPE_FORBIDDEN_TOKENS` (line 415). The wider 6-token notes list is enforced separately at `write_signoff_record` line 227, so a forbidden positive claim cannot enter the surface via reviewer notes. Both gates are present; the narrowed envelope audit is necessary, not lazy.

5. **Frontend `SUPPORTED_SIGNOFF_VERDICTS` exported `as const` 4-tuple**. `frontend/src/signoffHistoryClient.ts:13-18` exports the constant tuple with exactly the 4 verdict literals; line 20 derives `type SignoffVerdict = (typeof SUPPORTED_SIGNOFF_VERDICTS)[number]` from it. The vitest pin `'exports every supported verdict in the whitelist constant'` (test lines 127–137) asserts the exact 4-element array. The 4-tuple matches the backend `SignoffVerdict` Literal in `signoff_record.py:69-74` and the backend `SUPPORTED_SIGNOFF_VERDICTS` tuple at lines 76-81; backend/frontend SSOTs are in lock-step.

6. **`parseVerdict()` defensively falls back to `blocked_pending_input`** (most conservative). Verified at `signoffHistoryClient.ts:68-81`: explicit `if (raw === 'watching' || raw === 'needs_more_evidence' || raw === 'needs_more_convergence' || raw === 'blocked_pending_input') return raw`; everything else (including `undefined`, any future "promotion verb" the backend might leak) → `return 'blocked_pending_input'`. The comment on lines 77–80 documents the rationale: "a UI should never silently surface an unknown Tier 2 promotion verb." This is the right defensive choice — `blocked_pending_input` is the danger-tone bucket, so unknown verdicts visually surface as red instead of silently masquerading as `watching`/info-tone.

7. **`TrustScoreGauge` subline renders only when both verdict + utc are provided**. `TrustScoreGauge.tsx:168` guard: `{latestSignoffVerdict && latestSignoffUtc && (...)}`. Reviewer is treated as optional (line 180 `{latestSignoffReviewer ? <> by <strong>{latestSignoffReviewer}</strong></> : null}`). If either of the two required fields is `null`/`undefined`, the entire subline block is omitted — matching blueprint §3.B "absence-state shows nothing (no false-positive 'needs review' prompt)". The subline element carries `data-testid="trust-score-signoff-subline"` for future targeted vitest assertions, which is forward-thinking but not yet exercised in slice B; that's fine.

8. **`App.tsx` lifts state via `onLatestRecord` callback — no duplicate fetch**. Diff shows `frontend/src/App.tsx:455` adds `const [latestSignoff, setLatestSignoff] = useState<SignoffRecord | null>(null);`; lines 1612–1620 pass `latestSignoffVerdict={latestSignoff?.verdict ?? null}` (+ reviewer, utc) into `<TrustScoreGauge>` and `onLatestRecord={setLatestSignoff}` into `<SignoffHistoryPanel>`. Only one `fetchSignoffHistory` call site exists (inside `SignoffHistoryPanel`'s `useEffect`); the gauge receives the result via lifted state, not via its own fetch. `TrustScoreGauge.tsx` confirms there is no import of `fetchSignoffHistory` or `signoffHistoryClient`. Architecturally clean: single source, single network call, deterministic propagation.

9. **6 backend tests** confirmed in `tests/test_phase8_signoff_history_endpoint.py`:
   - `test_signoff_history_endpoint_returns_empty_for_unseeded_case` — `record_count == 0`
   - `test_signoff_history_endpoint_returns_chronological_order` — 3 records seeded at hours 9/11/15; payload returns labels in ascending order; matches `read_signoff_history`'s `sorted(case_dir.glob("*.json"))`
   - `test_signoff_history_endpoint_rejects_invalid_case_id_shape` — "has spaces" → 400 (route-level regex)
   - `test_signoff_history_endpoint_rejects_signed_registry_case_id` — `GS-001` → 400 (builder-path `_assert_candidate_case_id` → `ValueError` → `HTTPException 400`)
   - `test_signoff_history_endpoint_stamps_schema_and_disclaimer` — full disclaimer trio + schema version assertion; "Tier 1 engineering candidate" in `claim_tier`, "not_signed_validation" + "not_benchmark_agreement" in `claim_boundary`, "not signed validation" + "not benchmark agreement" in `claim_impact`
   - `test_signoff_history_endpoint_response_is_application_json` — content-type assertion + `json.loads(res.text)` round-trip
   - Hits blueprint floor of ≥6 exactly.

10. **7 vitest tests** confirmed in `frontend/test/SignoffHistoryPanel.test.tsx`:
    - candidate-case prompt when `caseId={null}`
    - empty state (`record_count=0`)
    - 2-record render with verdict pills + reviewer + notes
    - fetch error (status 500) surfaces in UI
    - `onLatestRecord` callback fires with chronologically last record (`bob` / `needs_more_convergence`)
    - whitelist constant pin (`SUPPORTED_SIGNOFF_VERDICTS` equals exact 4-element array)
    - `toneForVerdict` exhaustive mapping (`watching→info`, `needs_more_*→warn`, `blocked_*→danger`)
    - Exceeds blueprint floor of ≥5 by 2.

11. **Anti-gaming guard coverage (slice-B applicable subset)**:

    | Guard | Mapped to slice B? | Evidence |
    |---|---|---|
    | **X: -2** (`SUPPORTED_SIGNOFF_VERDICTS` not duplicated inline in panel) | Yes | `grep -n "SUPPORTED_SIGNOFF_VERDICTS\|signoffHistoryClient" frontend/src/components/SignoffHistoryPanel.tsx` returns only 2 hits, both the import path; no inline 4-element literal in the panel. The vitest pin (`expect(SUPPORTED_SIGNOFF_VERDICTS).toEqual([...])`) protects against a future inline-duplicate regression. |
    | **X: -2** (verdict tone via helper, not inline hex) | Yes | `VerdictPill` (line 43) calls `const tone = toneForVerdict(verdict)`; `toneBackground` (line 31) and `toneForeground` (line 37) accept a `VerdictTone` argument, dispatching via tone strings (`'info'`/`'warn'`/`'danger'`). The hex codes inside `toneBackground`/`toneForeground` are CSS-variable fallback defaults (e.g. `'var(--accent-bg, #e6f3ec)'`) — the primary color comes from CSS variables; hex codes are graceful-degradation fallback only. This is consistent with the Phase 6/7 tone-helper pattern. Guard satisfied. |
    | **E: -2** (E2E missing disclaimer trio) | N/A in slice B | E2E for the trio lands in slice F per blueprint §3.F; slice B's endpoint test `test_signoff_history_endpoint_stamps_schema_and_disclaimer` already asserts the disclaimer trio at the HTTP body level, which is the right scope for slice B and pre-pays the E2E obligation. |
    | **B: -2** (schema_version stamped on new endpoint) | Yes | Envelope test asserts `payload["schema_version"] == SIGNOFF_RECORD_SCHEMA_VERSION`. |
    | **C: -10/-8/-5** (verdict whitelist + audit + notes) | Inherited from slice A; slice B does not weaken | The slice does not alter `SUPPORTED_SIGNOFF_VERDICTS`, `_audit_verdict_whitelist`, or `_assert_no_overclaim`. The new `_ENVELOPE_FORBIDDEN_TOKENS` is a strict subset of `_FORBIDDEN_NOTES_TOKENS`, documented as such. |

12. **Test execution evidence (independently re-run)**:
    - `python -m pytest tests/test_phase8_signoff_history_endpoint.py tests/test_phase8_signoff_record.py -q --no-header → 27 passed, 3 warnings in 0.65s`
    - `cd frontend && npx vitest run → 4 files / 24 tests passed (782ms)`
    - `cd frontend && node --test test/*.test.ts → 142 passed (no regression from pre-slice-B baseline)`
    - `cd frontend && npx tsc -b → clean (no output)`
    - All 4 verification commands match the author's commit-message claims exactly.

13. **Constraint checks**:
    - HF1 zone untouched: `git diff --name-only 6dd7be4..270e0d0 | grep -E "(agents/solver|agents/router|agents/geometry|schemas/sim_state|test_toolchain_probes|Dockerfile|Makefile|hf1_path_guard|\.github/workflows)"` → empty.
    - No `^GS-\d{3}$` registry edits: `git diff --name-only` shows zero hits in `golden_samples/` or any `GS-\d{3}` literal path. The test fixtures use `GS-A-candidate` (valid Tier 1 candidate name) and `GS-001` (only as a negative-test rejection target).
    - No forbidden positive claims outside disclaimer form: spot-grep of new files for `"signed validation"` / `"benchmark agreement"` shows every occurrence is either (a) preceded by `not ` in disclaimer text, (b) inside a docstring/comment explaining the two-list design, or (c) inside a test fixture's `claim_impact` string which itself uses the `not <claim>` form.

---

### HIGH+LOW findings

**HIGH**: none.

**LOW-1** (cosmetic / non-blocking): the `_assert_no_overclaim_in_report` function (lines 403–427) and `_assert_no_overclaim` (lines 307–327) share the same 4-byte `not <claim>` lookback pattern; the duplication is intentional (different forbidden-token lists per scope) but a small named helper `_is_in_disclaimer_form(haystack, idx) -> bool` would dedupe the lookback logic without merging the lists. Suitable for slice F polish; does not block.

**LOW-2** (cosmetic / non-blocking): `_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")` at `signoff_history.py:28` is a magic regex. Other Phase 6/7 routes use the same shape; if there's a `_CASE_ID_SHAPE_RE` SSOT in the route helpers module this should import from it. Worth checking in slice F polish.

**LOW-3** (cosmetic / non-blocking): the commit message says "alphabetic + chronologic ordering" of the router registration, but the import block in `main.py` is alphabetic (line 27 `signoff_history` before line 32 `trust_score_alerts`) while the registration block is chronologic (line 114 `trust_score_alerts.router` before line 116 `signoff_history.router`). Both are internally consistent with their respective ordering schemes; no functional impact.

None of the LOW findings block slice C.

---

### Axis verdicts (slice B isolated)

| Axis | Weight | Slice-B score | Evidence anchor |
|---|---|---|---|
| **B — schema versioning** | 12 | **12/12** | Envelope stamps `SIGNOFF_RECORD_SCHEMA_VERSION` (line 374, builder); endpoint test asserts round-trip (test line 142); no new constant needed (additive surface re-uses slice-A's `SIGNOFF_RECORD_SCHEMA_VERSION`). |
| **M — module quality** | 12 | **12/12** | Two-list design with documented Phase 7 B precedent (lines 124–142); pure functions (builder calls reader then audits envelope; no I/O leaks beyond the existing slice-A `read_signoff_history`); UTC ISO 8601 generated_at via `datetime.now(UTC).isoformat(timespec="seconds")` (line 372). |
| **T — testing** | 15 | **15/15** | 6 backend tests + 7 vitest tests = 13 new Phase 8 B tests; backend floor was ≥6 (hit exactly), vitest floor was ≥5 (exceeded by 2). All 27 backend + 24 vitest tests green; tsc clean. |
| **C — claim-tier discipline** | 12 | **12/12** | Tier 1 disclaimer trio asserted in endpoint test; envelope audit uses narrowed list; route + builder defense-in-depth on `^GS-\d{3}$`; no Tier 2 vocabulary in any new file (spot-checked). |
| **X — frontend integration** | 12 | **12/12** | Components mounted in `App.tsx`; vitest 4/4 + tsc -b clean; `SUPPORTED_SIGNOFF_VERDICTS` imported by panel (no inline literal); `toneForVerdict` drives pill colors (no inline hex as primary; CSS-var fallbacks are best practice). |
| **D — documentation / SSOT** | 8 | **8/8** | Two-list design rationale documented in module-level comment block (lines 124–142); `SignoffHistoryReport` docstring (lines 345–351) enumerates envelope fields and explicit `claim_impact` semantics; `signoffHistoryClient.ts` module docstring (lines 1–8) explains the SSOT re-export. |
| **A — anti-gaming discipline** | 8 | **8/8** | Slice-A TAA archive (`A.md`) landed in this commit, preserving APPROVE + LOW-deferred audit-trail discipline; the slice-B-applicable subset of 17 guards (X: -2 ×2, B: -2, E: -2) all satisfied. |
| **E — end-to-end workflow** | 8 | **8/8** | Slice-B scope; E2E proper lands in slice F per blueprint. Endpoint test's full disclaimer-trio round-trip (test lines 123–142) pre-pays the slice-B end-of-pipeline obligation at the HTTP layer. |
| **V — verification by TAA** | 13 | **2/13** | Slice-A archive lands in this commit (V=1 retired); slice-B archive is this report (V=2 retiring). 11/13 reserved for slices C, D, E, F + FINAL. |

**Slice-B subtotal (B+M+T+C+X+D+A+E)**: 87/87 across the 8 non-V axes = 100% of in-scope weight.
**V contribution from slice B**: 2/13.
**Total in-scope score (8 non-V axes earned + V partial)**: 87 + 2 = **89/100**.

---

### Overall verdict

**APPROVE**

No BLOCK or HIGH findings. The slice executes blueprint §3.B faithfully:
- `GET /api/v1/signoff-history/<case-id>` returns the exact envelope shape specified in §3.B with all 8 fields and the Tier 1 disclaimer trio intact.
- The two-list forbidden-token design (`_FORBIDDEN_NOTES_TOKENS` 6-token notes-scope vs `_ENVELOPE_FORBIDDEN_TOKENS` 4-token envelope-scope) is documented, intentional, and mirrors the Phase 7 B honest fix; the build path calls the narrower envelope audit while the write path keeps the wider notes audit.
- `SUPPORTED_SIGNOFF_VERDICTS` is exported `as const` 4-tuple and consumed by the panel without duplication; the vitest pin guards against future inline-list regression.
- `parseVerdict` defensively falls back to `blocked_pending_input` (most conservative bucket) for unknown values, ensuring a future backend leak of any Tier 2 promotion verb cannot silently surface as a benign info-tone pill in the UI.
- `TrustScoreGauge` subline renders only when both `latestSignoffVerdict` and `latestSignoffUtc` are provided; absence renders nothing (no false-positive "needs review" prompt).
- `App.tsx` lifts state via `onLatestRecord` callback from panel to gauge — single fetch, single SSOT, deterministic propagation.
- 6 backend + 7 vitest tests all green; full pytest sweep (per commit message) 1646 passed; vitest 4 files / 24 tests; node --test 142 passed (no regression); tsc -b clean.
- HF1 zone untouched, no signed-registry edits, no `golden_samples/**` writes, no external surface.

Main session may proceed to slice C (`trust_score_provenance` endpoint).

---

### Honest score adjustment vs commit claim

Author's commit claim: **89/100** with explicit `V (2/13)` reservation pending this audit.

Audit assessment: **89/100** — the author's claim matches the audit verdict exactly on all 9 axes. No adjustment needed:
- B 12/12, M 12/12, T 15/15, C 12/12: all earned with explicit per-axis evidence.
- X 12/12: confirmed via vitest pass + tsc clean + no-inline-duplicate + tone-helper-driven + CSS-var-first color strategy.
- D 8/8, A 8/8: earned (two-list rationale documented; slice-A archive landed preserving audit-trail discipline).
- E 8/8: in-scope endpoint-level disclaimer trio asserted; full E2E lands in slice F as planned.
- V 2/13: this audit retires the slice-B obligation; remaining 11/13 reserved for slices C-F + FINAL.

**Honest cumulative score after slice B**: **89/100** by design (V intentionally short until all 7 TAA audits land). Main session is on track for the 99/100 honest-gate target at slice G closure.

---

### Slice-B summary

Slice B is a clean additive HTTP + frontend surface on top of the slice-A builder. The two-list forbidden-token design is the load-bearing piece — it would have been easy to weaken to a 4-token list everywhere (silently letting "signed validation" appear in raw notes if it were preceded by "not"), or to a 6-token list everywhere (causing the envelope audit to refuse the legitimate disclaimer claim_impact). The author picked the right scope per surface and documented the rationale at line-block precision; the build path wires through the correct narrower audit; the write path retains the wider audit. The frontend side keeps the verdict whitelist as a single import from the typed client and defensively buckets unknown values into the most conservative danger-tone bucket. State-lift via callback (panel → App → gauge) avoids duplicate fetches with no architectural debt.

**Recommendation**: APPROVE; proceed to slice C with no follow-up fix commits required. 3 LOW cosmetics (deduped `_is_in_disclaimer_form` helper, `_CASE_ID_SHAPE_RE` SSOT, commit-message ordering nit) are suitable for the slice F polish pass; none block any subsequent slice.

> Tier 1 engineering candidate; not signed validation; not benchmark agreement.
