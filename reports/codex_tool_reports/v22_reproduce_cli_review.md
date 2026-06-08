# Codex Review — FM-05 V2-2: reproduce-CLI + audit log (close G-2 item 6) — R0→R1→R2 APPROVE

**Scope (risk-tier: golden_samples boundary + solver-truth path + cross-≥3-file):** deliver the
ADR-027 D3 **V2-2** `reproduce <case_id>` CLI (G-2 evidence-packet **item 6**) — re-derive a committed
cross-check case's result + verdict from its **sealed** inputs and write a structured audit-trail log.
LE10 → fresh real-ccx re-solve; any case → ccx-free residual recompute; sealed-hash integrity gate.

**Reviewer:** `codex-relay-with gpt-5.5` (xhigh), static diff review, stdin-closed. Round cap = 3.

## Honesty contract upheld (machine-pinned)

- **Genuine re-derivation, never echo.** `real_solve` runs a FRESH ccx solve of the sealed deck in a
  `TemporaryDirectory` (never touches the sealed dir) and extracts σ_yy@D from the produced `.frd`;
  `recompute` re-derives `residual_pct` from committed observed/analytical via the cohort magnitude
  formula — neither copies the committed `residual_pct`.
- **`reproduced=True` is doubly gated (both paths):** sealed (`all_hashes_match is True`) AND verdict
  matches committed AND the rederived verdict is itself **PASS**. A missing manifest, a tampered
  input, a both-FAIL match, or an out-of-tolerance result all yield `reproduced=False`.
- **No fabricated provenance.** `ccx.version` is recorded ONLY from an actual solve (`None` on the
  recompute path); `real_solve` vs `recompute` is labeled per host/flag and disclosed in `notes`.
- **Item 6 closed honestly.** `artifact_manifest.json` item 6 OPEN→CLOSED names the closing mechanism
  (`scripts/reproduce_case.py`); item 7 (independent signoff) stays OPEN → case remains **Tier-1
  candidate, NOT signed validation**. Seal-test updated to assert the new state.
- **Claim tier:** Tier 1 engineering candidate (reproducibility evidence). Never Tier 2-signed.

## Safety envelope (verified)

- Audit log writes are refused under `golden_samples/**` AND outside the repo tree (R0-2 fix).
- `case_id` must be a bare directory name — `../`, absolute, separators rejected (R0-3 fix).
- The CLI never writes into the sealed case dir; audit logs land in `reports/reproduce_audit/`
  (gitignored generated output; only inputs enter VC).

## Review rounds

- **R0 — CHANGES_REQUIRED (3):** (P1) recompute marked `reproduced=True` with manifest absent
  (`in (True, None)` hole); (P2) `_write_audit` allowed paths outside the repo tree; (P2) `case_id`
  path-traversal. → all fixed.
- **R1 — CHANGES_REQUIRED (1):** (P2) `real_solve` gate lacked the `== "PASS"` check the recompute
  path had → a both-FAIL match would mark reproduced. → fixed (PASS-gated both paths; new ccx-free
  stubbed-solver test).
- **R2 — APPROVE (no findings).** Verbatim: *"APPROVE. No findings. R1-1 is closed … both-FAIL cannot
  reproduce. New test covers that case."*

## Files

- `scripts/reproduce_case.py` (NEW) — `reproduce <case_id>` CLI: real_solve (LE10) / recompute,
  sealed-hash integrity gate, repo-contained audit-log writer, case_id traversal guard.
- `tests/test_reproduce_cli.py` (NEW, 17 tests) — recompute seal/no-seal, integrity gate (match +
  tamper), committed-FAIL not reproduced, real_solve FAIL not reproduced (stubbed), audit-writer
  refusals (golden_samples + outside-repo), case_id traversal param, no-ccx degradation, ccx-guarded
  real LE10 solve.
- `golden_samples/nafems-le10-thick-plate-candidate/artifact_manifest.json` — item 6 OPEN→CLOSED +
  claim_tier prose (not a sealed file; seal hashes unaffected).
- `tests/test_le10_artifact_manifest.py` — seal test asserts item 6 CLOSED + names the mechanism;
  item 7 stays OPEN.
- `.gitignore` — `reports/reproduce_audit/` (generated reproduction-event records).

## Gates

- ruff check + format clean. 36 root-tests pass (reproduce 17 incl. ccx-guarded live solve 14s;
  seal + residual-floor 19). `validate_golden_samples.py` exit 0 (3 signed samples). HF1 path guard
  exit 0. Live: `reproduce nafems-le10-thick-plate-candidate` → real_solve, σ_yy@D −5.4379 MPa,
  drift 1.8e-6 vs committed, REPRODUCED=True, exit 0.

**Closure:** R2 **APPROVE** after 2 fix rounds (within cap). Local commit, `confidence: high`, no push.
