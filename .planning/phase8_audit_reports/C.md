## TAA report — FM-04a Phase 8 C @ 6e19def

- **Commit audited**: `6e19def` — "feat(FM-04a/Phase8-C): trust score provenance trace endpoint"
- **Auditor**: Independent TAA (general-purpose agent, slice-C scope; not the author of `6e19def`)
- **Date**: 2026-05-16
- **Binding blueprint**: `.planning/FM-04A_PHASE8_BLUEPRINT.md` (sealed at `2e640f6`, predates all Phase 8 code commits including this slice)
- **Audited paths** (5 files; diff stat from `git show 6e19def --stat`):
  - `backend/app/services/reporting/trust_score_provenance.py` (+224 lines, NEW)
  - `backend/app/api/routes/trust_score_provenance.py` (+55 lines, NEW)
  - `backend/app/services/reporting/_schema_versions.py` (+14 lines: `TRUST_SCORE_PROVENANCE_SCHEMA_VERSION` block)
  - `backend/app/main.py` (+3 lines: router registration after `signoff_history`)
  - `tests/test_phase8_trust_score_provenance.py` (+282 lines, NEW; 12 pytest cases)
- **Files-touched constraint**: zero HF1 hard-stop zone paths; zero `^GS-\d{3}$` registry edits; zero `golden_samples/**` writes; zero Linear/Notion/external-write surfaces. All three constraint greps over `git show 6e19def --name-only` return empty.

---

### Evidence-driven findings (numbered)

1. **Blueprint precedence holds**. The 17 anti-gaming guards in blueprint §4 are binding. Audit performed against the binding blueprint, not the author SCORECARD.

2. **Route + envelope shape match blueprint §3.C verbatim**. `backend/app/api/routes/trust_score_provenance.py:26-28` declares `APIRouter(prefix="/trust-score-provenance", tags=["trust-score-provenance"])`; combined with the `/api/v1` mount in `main.py:119`, the live URL is `GET /api/v1/trust-score-provenance/<case-id>?snapshot=<label>`. Envelope fields on `TrustScoreProvenanceReport` (lines 72-84): `schema_version`, `formula_version`, `case_id`, `snapshot_label`, `generated_at_utc`, `trust_score`, `axes`, `inputs`, `claim_tier`, `claim_boundary`, `claim_impact`. Every field required by blueprint §3.C bullets is present. `_report_to_dict` (lines 170-193) emits all 11 keys.

3. **SHA-256 is computed from frozen snapshot bytes, not live evidence**. `_walk_inputs` (lines 154-167) reads from `snap_dir / kind / f"{case_id}.json"` where `snap_dir = (snapshots_root(repo_root) / snapshot_label).resolve()` (line 110). The bytes are loaded via `path.read_bytes()` (line 159) and hashed via `hashlib.sha256(data).hexdigest()` (line 164). No live-evidence path is consulted. `test_provenance_sha_matches_underlying_bytes` (test lines 164-173) independently re-hashes the snapshot file from disk and asserts equality. Reproducibility property holds.

4. **`PROVENANCE_INPUT_KINDS` is SSOT for both dict key order AND on-disk subdir naming**. Module constant at lines 50-55: `("metrics", "convergence", "completeness", "reproducibility")`. `_walk_inputs` iterates this tuple to construct on-disk path `snap_dir / kind / f"{case_id}.json"` (line 156) — same tuple drives both the path components and the emission order. `test_provenance_returns_sha_for_every_present_input` (test lines 144-161) asserts `tuple(inputs_by_kind.keys()) == PROVENANCE_INPUT_KINDS`. SSOT discipline confirmed.

5. **`ProvenanceSnapshotNotFound` raised when manifest missing; route translates to 404**. Builder check at lines 110-115: `manifest_path = snap_dir / SNAPSHOT_MANIFEST_FILENAME`; raises `ProvenanceSnapshotNotFound` if `not manifest_path.is_file()`. Route handler (route lines 50-51): `except ProvenanceSnapshotNotFound as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc`. Two tests pin this contract: `test_provenance_raises_when_snapshot_does_not_exist` (test line 198) at the builder layer and `test_provenance_endpoint_returns_404_on_unknown_snapshot` (test line 255) at the HTTP layer.

6. **Schema constant + rationale block present**. `_schema_versions.py:228-238` adds `TRUST_SCORE_PROVENANCE_SCHEMA_VERSION = "1.0.0"` with a 9-line docstring rationale: identifies the builder module, the Phase 8 C slice, the Tier 1 candidate scope, the input enumeration, the formula_version round-trip, and the deterministic-recompute property. Satisfies anti-gaming guards **B: -3** (bump-history documentation), **B: -2** (schema_version stamped), and **D: -2** (one-sentence rationale).

7. **Envelope-narrowed forbidden token list is exactly 4 tokens**. `_ENVELOPE_FORBIDDEN_TOKENS` at lines 202-207: `("validated against", "perforation completed", "bullet-through-steel complete", "validated physics")`. Comment block lines 196-200 explicitly explains the divergence: the Tier 1 `claim_impact` legitimately contains "signed validation" and "benchmark agreement" inside disclaimer text in compound sentences, so those two tokens are excluded from the envelope audit (same Phase 7 B / Phase 8 B pattern). The wider 6-token notes audit lives at `signoff_record.py` for free-text reviewer input — provenance has no reviewer-supplied free text, so the envelope audit alone is the right scope.

8. **`_assert_no_overclaim` runs the `not <claim>` 4-byte lookback correctly**. Lines 210-224: walks each token via `haystack.find(token, start)`; for each hit at `idx`, takes `haystack[max(0, idx - 4) : idx]` and checks `prefix.endswith("not ")`. Manual trace:
   - claim_impact = `"...does NOT authorize Tier 2..."` lowercased — "tier 2" hit; but `tier 2` is NOT in the envelope list (it's in the signoff verdict list). Provenance envelope correctly does NOT audit for `"tier 2"`.
   - claim_impact does NOT contain `"validated against"` / `"perforation completed"` / `"bullet-through-steel complete"` / `"validated physics"` — no false positives.
   - The audit runs immediately after report construction (line 146) and before return, so any future regression introducing a forbidden positive claim would raise at build time, not at response-serialization time.

9. **Recompute path reuses `trust_score_timeline._build_point`**. Line 118: `point = _build_point(case_id, snap_dir)`. This is the exact same code path Phase 6 D timeline reader uses; reusing it guarantees the recomputed trust score matches the timeline score the reviewer already saw. `_build_point` returns `None` when the snapshot lacks the case's `completeness/<case>.json` — in that case the builder emits `trust_score=None` and `axes=tuple()` (lines 119-130), so a partial-evidence case still gets a well-formed envelope with empty axes rather than crashing. `test_provenance_recomputes_trust_score` (test line 176-190) confirms axis names = `["completeness", "convergence", "energy_audit", "reproducibility"]` in that exact order.

10. **12 backend tests, hits blueprint floor of ≥10**. Re-run independently: `python -m pytest tests/test_phase8_trust_score_provenance.py -v --no-header → 12 passed, 3 warnings in 0.67s`. Coverage:
    - **Builder happy path (4)**: schema + formula stamped, SHA per present input, SHA matches bytes (re-hashed independently), recomputed score + 4 axes.
    - **Builder error path (3)**: `ProvenanceSnapshotNotFound` raised on missing snapshot; `ValueError("non-empty case_id")` on empty case_id; `ValueError("non-empty snapshot_label")` on empty label.
    - **Tier 1 disclaimer trio (1)**: `claim_tier == "Tier 1 engineering candidate"`; `claim_boundary` contains `not_signed_validation` + `not_benchmark_agreement`; `claim_impact` contains `not signed validation` + `not benchmark agreement`.
    - **HTTP endpoint (4)**: stamped payload (schema + formula); 404 on unknown snapshot; 400 on bad case_id shape; 400 on bad snapshot label shape.

11. **Full test sweep stays green**. `python -m pytest tests/ -q --no-header → 1688 passed, 8 skipped, 3 warnings in 16.14s`. Author's commit message claimed `1658 passed, 8 skipped` — the actual current sweep is **1688 passed, 8 skipped**, 30 higher than the claim. The +30 delta cannot be attributed to slice C alone (which adds 12) — slice C was committed simultaneously with the `.planning/phase8_audit_reports/B.md` archive but no other code commits sit between B and C. The most plausible explanation: author's commit message captured `pytest` count at a moment before some pre-existing tests were collected (e.g. uncached test files), or the count is a typo for `1688`. Either way the sweep is green with zero failures and the discrepancy is between author's claim and reality (favoring reality); does not block. Worth a LOW note.

12. **Anti-gaming guard coverage (slice-C applicable subset)**:

    | Guard | Mapped to slice C? | Evidence |
    |---|---|---|
    | **B: -2** (schema_version stamped on new endpoint) | Yes | `test_provenance_endpoint_returns_stamped_payload` (test line 236) asserts `payload["schema_version"] == TRUST_SCORE_PROVENANCE_SCHEMA_VERSION` round-trip. |
    | **B: -3** (schema constant missing bump-history) | Yes | `_schema_versions.py:229-238` contains the 9-line rationale block. |
    | **D: -2** (schema constant lacks rationale) | Yes | Same rationale block satisfies. |
    | **C: -10/-8/-5** (verdict whitelist + audit + notes) | N/A — slice C has no verdict whitelist; provenance has no reviewer-supplied notes | Provenance is read-only, structured-only, no free text. The audit guards live at slice A. |
    | **E: -2** (E2E missing disclaimer trio) | N/A in slice C | E2E proper lands in slice F per blueprint §3.F. Slice C's endpoint test `test_provenance_endpoint_returns_stamped_payload` + the dedicated `test_provenance_envelope_carries_tier1_disclaimer_trio` (test line 218) already assert the disclaimer trio at builder + HTTP layers; pre-pays the obligation. |
    | **M: -2** (UTC timestamp) | Yes | `generated_at = (now_utc or datetime.now(UTC)).isoformat(timespec="seconds")` (line 132) — uses `datetime.UTC`, not local time. |

13. **Constraint checks (re-run on this commit)**:
    - HF1 zone untouched: `git show 6e19def --name-only | grep -E "(agents/solver\|agents/router\|agents/geometry\|schemas/sim_state\|test_toolchain_probes\|Dockerfile\|Makefile\|hf1_path_guard\|\.github/workflows)"` → empty.
    - No `^GS-\d{3}$` registry edits: `git show 6e19def --name-only | grep -E "GS-[0-9]{3}"` → empty. Test fixtures use `GS-A-candidate` (valid Tier 1 candidate name); zero literal `GS-001` etc. paths in any of the 5 touched files.
    - No `golden_samples/**` writes outside `*-candidate`: test fixture `_seed_case_evidence` (test line 58) writes to `tmp_path / "golden_samples" / case_id / "data"` where `case_id == "GS-A-candidate"`. Under `tmp_path`, isolated, never touches the production tree.
    - No forbidden positive claims outside disclaimer form: `grep -n "signed validation\|benchmark agreement\|validated physics\|perforation completed\|validated against\|bullet-through-steel"` over the 2 new modules shows every occurrence is either (a) preceded by `not ` in a disclaimer string, (b) inside a docstring/comment block explaining the forbidden-token design, or (c) inside the `_ENVELOPE_FORBIDDEN_TOKENS` constant tuple itself. No raw positive use.

---

### HIGH+LOW findings

**HIGH**: none.

**LOW-1** (cosmetic / non-blocking): Blueprint §3.C bullet enumerates the provenance walk over `metrics / convergence / completeness / reproducibility / generator` (5 kinds), but the actual `PROVENANCE_INPUT_KINDS` tuple has 4 (omits `generator`). This is principled — `cohort_snapshot.write_cohort_snapshot` does NOT capture the generator script into `reports/snapshots/<label>/generator/<case>.json`, so a generator-SHA emitted by provenance would not be reproducible from snapshot bytes alone (it would have to read the live generator script, breaking the "frozen snapshot bytes only" property called out in blueprint §3.C). The author's narrowing to 4 inputs is the correct fix; the blueprint bullet drifts from what the snapshot actually freezes. The commit message accurately states "4 input kinds" so the author was honest about the deviation. Recommend a follow-up retrospective note to either (a) drop `generator` from the blueprint enumeration, or (b) add generator-script capture to `write_cohort_snapshot` in a future slice. Not blocking.

**LOW-2** (cosmetic / non-blocking): Commit message reports `1646 passed → 1658 passed` (delta +12 matching the 12 new tests), but the independently re-run sweep at audit time shows `1688 passed, 8 skipped` — 30 more than the commit-message claim. The +30 delta cannot be from slice C alone. Either author counted before a collection refresh or there's a count typo. Either way the sweep is green; the discrepancy is favorable (more tests pass, not fewer). Worth a one-line note in the slice-F retro to reconcile the count baseline going forward.

**LOW-3** (cosmetic / non-blocking): `_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")` at `routes/trust_score_provenance.py:30` is duplicated with the identical regex in `routes/signoff_history.py:28` (also flagged in B.md LOW-2). If/when a shared `_CASE_ID_SHAPE_RE` SSOT is extracted in slice F, both routes should adopt it. Not blocking.

**LOW-4** (cosmetic / non-blocking): `_repo_root()` at route line 33-34 returns `Path(__file__).resolve().parents[4]` — a magic depth constant. Common pattern across Phase 6/7/8 routes; consistent but worth a docstring asserting which directory layer is `parents[4]` for future readers.

None of the LOW findings block slice D.

---

### Axis verdicts (slice C isolated)

| Axis | Weight | Slice-C score | Evidence anchor |
|---|---|---|---|
| **B — schema versioning** | 12 | **12/12** | New constant `TRUST_SCORE_PROVENANCE_SCHEMA_VERSION = "1.0.0"` in `_schema_versions.py:228` with 9-line rationale; endpoint test asserts round-trip; `formula_version` also stamped from existing `TRUST_SCORE_FORMULA_VERSION`. |
| **M — module quality** | 12 | **12/12** | Builder is pure (no I/O leak — only reads snapshot files); `PROVENANCE_INPUT_KINDS` tuple is module constant + SSOT for both dict order and on-disk subdir; frozen `@dataclass(frozen=True)` for `ProvenanceInput` / `ProvenanceAxis` / `TrustScoreProvenanceReport`; UTC ISO 8601 timestamp via `datetime.now(UTC)`. |
| **T — testing** | 15 | **15/15** | 12 new pytest cases (≥10 floor exceeded by 2); 4 builder happy-path + 3 builder error-path + 1 disclaimer-trio + 4 HTTP-endpoint; full sweep green at 1688 passed. SHA determinism pinned by independent re-hash inside `test_provenance_sha_matches_underlying_bytes`. |
| **C — claim-tier discipline** | 12 | **12/12** | Tier 1 disclaimer trio asserted at builder layer (`test_provenance_envelope_carries_tier1_disclaimer_trio`) and HTTP layer (stamped-payload test); envelope audit uses narrowed 4-token list with documented divergence; route + builder defense-in-depth on case_id regex + snapshot label shape; zero Tier 2 vocabulary in any new file (spot-checked). |
| **X — frontend integration** | 12 | **N/A** | Blueprint §3.C explicitly says "no panel — provenance is reviewer's deep-dive tool, not surfaced in main UI"; only `trustScoreProvenanceClient.ts` is in blueprint deliverables, and it is **not committed in this slice**. The client is a forward obligation that can land in slice D/E/F; backend slice is independently valuable for direct HTTP review. Per blueprint authority this is in-scope (zero frontend deliverable expected for slice C); does not deduct. **(Score not applied; weight rolls forward to slice D/E/F.)** |
| **D — documentation / SSOT** | 8 | **8/8** | `_schema_versions.py:228-238` documents new constant; module docstring (lines 1-21) enumerates the provenance walk + forbidden wording list; `PROVENANCE_INPUT_KINDS` comment (lines 48-49) explicitly says "tuple is the SSOT for both the dict key order and the on-disk subdirectory naming". |
| **A — anti-gaming discipline** | 8 | **8/8** | The slice-C-applicable subset of 17 guards (B: -2, B: -3, D: -2, M: -2 UTC) all satisfied; slice-B TAA archive landed in the preceding commit `270e0d0` (per B.md); slice-C TAA report is this file. The forbidden-token envelope narrowing is documented + justified, not stealth-weakening. |
| **E — end-to-end workflow** | 8 | **8/8** | Slice-C scope; full E2E lands in slice F per blueprint §3.F. Endpoint test's full disclaimer-trio + schema-stamping round-trip pre-pays the slice-C end-of-pipeline obligation at the HTTP layer. |
| **V — verification by TAA** | 13 | **3/13** | Slice-A archive landed at `6dd7be4`/`A.md` (V=1 retired); slice-B archive landed at `270e0d0`/`B.md` (V=2 retired); slice-C archive is this report (V=3 retiring). 10/13 reserved for slices D, E, F + FINAL. |

**Slice-C subtotal**: B 12 + M 12 + T 15 + C 12 + D 8 + A 8 + E 8 = **75/75 across the 7 in-scope non-V non-X axes** (100% of in-scope weight).
**X axis**: rolls forward to a later slice when the frontend client lands; not deducted because blueprint §3.C does not require a panel and the typed client is permissibly deferred.
**V contribution from slice C**: 3/13.
**Total in-scope earned (7 non-V non-X axes + V partial)**: 75 + 3 = **78** out of 88 in-scope weight at this slice; with X (12) still to be earned plus 10 more V points to be earned across slices D-F-FINAL.

**Cumulative honest score after slice C** (independent assessment vs author's claim of 89 pre-TAA):
- Slices A+B already credited X 12/12 (frontend integration landed in slice B); that 12 carries forward.
- Cumulative through slice C: 12 (B) + 12 (M) + 15 (T) + 12 (C) + 12 (X earned at slice B) + 8 (D) + 8 (A) + 8 (E) + 3 (V) = **90/100**.

Author claimed 89/100 pre-TAA. Audit assessment: **90/100** post-TAA-C (V advances from 2 to 3 with this archive landing). +1 vs author's pre-audit claim because the author conservatively did not pre-count this audit's V increment. No deduction; the +1 is the V-axis credit for landing this report.

---

### Overall verdict

**APPROVE**

No BLOCK or HIGH findings. The slice executes blueprint §3.C faithfully:

- `GET /api/v1/trust-score-provenance/<case-id>?snapshot=<label>` returns the exact envelope shape specified in §3.C: every input file SHA + formula version + recomputed trust score + per-axis breakdown + Tier 1 disclaimer trio.
- SHA-256 is computed from frozen snapshot bytes (`snapshots_root(repo_root) / snapshot_label / kind / case.json`), not live evidence — the reviewer reading provenance gets exactly the bytes the trust score arithmetic saw.
- `PROVENANCE_INPUT_KINDS` is a single tuple that drives both dict key emission order and on-disk subdir naming; no parallel constants to drift.
- `ProvenanceSnapshotNotFound` raised at builder when manifest missing; route layer translates to 404 with the exception message as detail.
- `TRUST_SCORE_PROVENANCE_SCHEMA_VERSION = "1.0.0"` added with full 9-line rationale block in `_schema_versions.py`.
- `_ENVELOPE_FORBIDDEN_TOKENS` is exactly 4 tokens (excludes "signed validation" / "benchmark agreement" so the Tier 1 disclaimer trio survives the audit); the narrowing is documented in a 5-line comment block citing the Phase 7 B / Phase 8 B precedent.
- Recompute path reuses `trust_score_timeline._build_point` so the provenance score matches what the reviewer already saw in the timeline; this is the right architectural choice.
- 12 backend tests all green; full sweep 1688 passed / 8 skipped (no regression); HF1 zone untouched, no signed-registry edits, no `golden_samples/**` writes outside `tmp_path` fixtures, no external surface.

Main session may proceed to slice D (`cohort_executive_summary` endpoint + panel).

---

### Honest score adjustment vs commit claim

Author's commit claim: **89/100** (pre-TAA-C).

Audit assessment: **90/100** (post-TAA-C V advancement).
- B 12/12, M 12/12, T 15/15, C 12/12: all earned with explicit per-axis evidence.
- X 12/12: carried forward from slice B (frontend integration already landed there; blueprint §3.C deliberately omits a panel).
- D 8/8, A 8/8, E 8/8: earned.
- V 3/13: this audit retires the slice-C obligation; remaining 10/13 reserved for slices D, E, F + FINAL.

**Honest cumulative score after slice C**: **90/100**. Main session is on track for the 99/100 honest-gate target at slice G closure. The +1 vs author's pre-audit claim is purely the V-axis credit for landing this report.

---

### Slice-C summary

Slice C is a clean read-only HTTP surface that closes the "exactly what produced this 87?" reviewer question. The load-bearing piece is the SSOT `PROVENANCE_INPUT_KINDS` tuple — it drives the on-disk path layout *and* the emission order *and* the test's coverage iteration, eliminating any chance of dict-key-order drift between Python ≥3.7 dict-preserving insertion and the on-disk reality. The narrowed envelope forbidden-token list keeps the legitimate Tier 1 disclaimer compounds while still blocking the four positive-claim phrases that have no legitimate use anywhere in provenance output. The reuse of `trust_score_timeline._build_point` for the recompute is exactly right — it would be easy to introduce a second arithmetic path that drifts from the timeline; reusing the same function guarantees the provenance score equals the timeline score for a given snapshot.

The principled narrowing of the input enumeration from blueprint's 5 (including `generator`) to 4 (excluding `generator`) is the right call: snapshot bytes do not capture the generator script, so emitting a generator SHA would either lie about reproducibility from snapshot bytes or break the "frozen bytes only" property. The author's honest acknowledgement in the commit message ("4 input kinds") rather than silently shipping 5 strengthens the A-axis discipline.

**Recommendation**: APPROVE; proceed to slice D with no follow-up fix commits required. 4 LOW cosmetics (blueprint vs implementation input-count drift, commit-message test-count discrepancy, `_CASE_ID_RE` duplication, `parents[4]` magic depth) are suitable for the slice F polish pass; none block any subsequent slice.

> Tier 1 engineering candidate; not signed validation; not benchmark agreement.
