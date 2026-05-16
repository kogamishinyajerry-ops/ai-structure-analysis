# FM-04a Phase 13 Slice D — Test Auditor Report

**Commit:** `88b17c8`
**Amendment:** AR-2026-05-16-001 (HF1.7 split into HF1.7a/HF1.7b + `*-candidate` carve-out)
**Auditor stance:** adversarial (slice D touches HF1.7/HF1.8 meta-protection zone)

---

## One-line verdict

**APPROVE — 60/63** (with one MEDIUM doc/code consistency finding to address in slice-D follow-up or next ADR amendment; does not block APPROVE because actual security posture is observable and tests pin reality.)

---

## Per-axis scores

- **M 11/12** — SSOT constants are named + module-scoped: `_GOLDEN_SAMPLES_PREFIX`, `_CANDIDATE_SUFFIX`, `_SIGNED_REGISTRY_RE` (scripts/hf1_path_guard.py:194-196). `_is_candidate_carveout` is the SSOT helper (scripts/hf1_path_guard.py:199-241). Re used `__import__("re")` instead of a top-level `import re` is mildly idiosyncratic (-1).
- **T 14/15** — 16 new tests all pass. Boundary pins on fullmatch anchor (test_zone_table_signed_registry_re_is_anchored_fullmatch), defense-in-depth negative cases (signed-registry, non-golden_samples, missing suffix, empty/root), override compatibility, rejection-message inspection. The MEDIUM finding below is partly self-pinned by `test_candidate_carveout_rejects_signed_registry_candidate_collision`'s honest docstring — but the test name says "rejects" while the assertion is `_is_candidate_carveout(path) is True` (allows). The test pins behavior but the name lies. (-1).
- **C 12/12** ✅ — Slice-D's elevated floor (11/12) MET. AR-2026-05-16-001 appears in: ADR-011 §Status (line 4), §Date (line 6), §Amendment cycles (line 14), §HF1 zone list (lines 95-96); `scripts/hf1_path_guard.py` ZONE entry adr_ref + carve-out docstring + rejection-message; `reports/hf_audit.md` window-001 header + opening notes; `reports/archive/hf_audit_window-000.md` SEALED status note; tests (4 places). Rolling-window protocol followed (window-000 sealed, window-001 head). Tier 1 disclaimer trio preserved in archive + window-001. HF1.7 splits cleanly into HF1.7a/HF1.7b (line 95-96). Prior amendments AR-2026-04-25-001 / AR-2026-05-03-001 / AR-2026-05-06-001 unchanged.
- **A 7/8** — HF1.7a hard-stop preserved (probe 1: `golden_samples/GS-001/file.json` returns rc=1 via HF1.7a ZONE entry). HF1.8 self-protection preserved (probe 4: `scripts/hf1_path_guard.py` still trips without override). Override env-var still works for genuine HF1 paths (test_override_still_works_for_genuine_hf1_path). HF1.8 bootstrap discipline followed: commit message names AR-2026-05-16-001 + the rationale + same-commit ADR amendment. `_SIGNED_REGISTRY_RE` fullmatch anchor pinned. (-1 for the MEDIUM finding: doc claim "REJECTS `GS-NNN-candidate`" is false — code allows it. Defense-in-depth narrative overstates actual guarantee.)
- **E 8/8** ✅ — `pytest tests/ -q` returns **2278 passed, 7 skipped** (slice-C baseline 2262 + 16 slice-D = 2278 exactly as predicted). HF1.7a still trips (probe 1). HF1.8 still trips (probe 4). Bootstrap is self-contained (no follow-up amendment required to ratify this amendment).
- **V 8/8** ✅ — Carve-out observably closes the override path: `check_paths_and_report(["golden_samples/cylinder-pv-collapsed-candidate/data/ballistic_metrics.json"])` returns rc=0 without `HF1_GUARD_OVERRIDE` (test_no_override_needed_for_carveout_paths + probe 2). HF1.7a + HF1.7b together do NOT widen the protective surface: signed-registry paths are still blocked, only `*-candidate` (non-signed-registry-shape) directories are writable.

**Sum: 11+14+12+7+8+8 = 60/63. All floors met: M ≥10 ✓ T ≥10 ✓ C ≥11 ✓ A ≥7 ✓ E ≥7 ✓ V ≥7 ✓.**

---

## Top findings

### MEDIUM-1 — ADR-011 + script docstring overstate defense-in-depth (false claim)

**Location:**
- `docs/adr/ADR-011-pivot-claude-code-takeover.md:14` and `:96`
- `scripts/hf1_path_guard.py:214-216`
- `tests/test_hf1_path_guard_candidate_carveout.py::test_candidate_carveout_rejects_signed_registry_candidate_collision` (the test NAME is the lie; the test assertion is honest)

**Claim:** "the carve-out helper REJECTS `GS-NNN-candidate` first-segments (signed-registry pattern wins over carve-out suffix), so a hypothetical name collision still trips HF1.7a hard-stop."

**Reality:** `_is_candidate_carveout("golden_samples/GS-101-candidate/file.json")` returns **True** (verified probe 3). The helper does `_SIGNED_REGISTRY_RE.fullmatch(case_dir)` where `case_dir = "GS-101-candidate"`. Since `fullmatch` requires the ENTIRE segment to match `^GS-\d{3}$` and `"GS-101-candidate"` has a trailing `-candidate` suffix, the fullmatch returns `None`. The helper then falls through to `return True` (carve-out applies → path is writable).

**Risk profile:** LOW in practice (no actual signed-registry file is at `GS-NNN-candidate/...`; FM-04b P8 packet authors would have to deliberately name a packet `GS-101-candidate` to exploit, and the signed-registry SHA-256 manifest catches semantic collisions). But the documented defense-in-depth narrative is wrong, and slice D's C-floor is elevated specifically because narrative integrity is load-bearing for the meta-protection zone.

**Fix proposal (pick one):**
1. **Code fix (preferred · 5 LOC):** Tighten `_is_candidate_carveout` to ALSO reject a case_dir that *starts* with `^GS-\d{3}-` (i.e., signed-registry-shape prefix followed by `-`). Pseudo-code:
   ```python
   _SIGNED_REGISTRY_PREFIX_RE = re.compile(r"^GS-\d{3}-")
   ...
   if _SIGNED_REGISTRY_RE.fullmatch(case_dir) or _SIGNED_REGISTRY_PREFIX_RE.match(case_dir):
       return False
   ```
   Add 1 test pinning `_is_candidate_carveout("golden_samples/GS-101-candidate/file.json")` is **False**. Rename the existing test to `..._is_blocked` and flip the assertion.
2. **Doc fix (cheaper · 3 lines):** Reword ADR-011 lines 14 + 96 + the helper docstring to say "the signed-registry pattern is preserved as a separate hard-stop ZONE entry; `GS-NNN-candidate` directory NAMES would be allowed by the carve-out but the FM-04b signed-registry manifest enforcement catches collisions at packet-sign time." This is honest but admits the carve-out doesn't itself do the rejection.

**Recommendation:** Code fix in a follow-up commit during slice-D ratification or as Phase 14 carry-forward. The defense-in-depth narrative SHOULD be true; closing the gap is 5 LOC + 1 test + a 1-line ADR-011 reword.

### LOW-1 — `__import__("re")` instead of `import re`

**Location:** `scripts/hf1_path_guard.py:196`

`_SIGNED_REGISTRY_RE = __import__("re").compile(r"^GS-\d{3}$")` — works but is idiosyncratic. The module doesn't import `re` at the top because the original module had no regex usage. Top-level `import re` would be cleaner.

**Fix proposal:** Add `import re` to the module's top imports; change line 196 to `_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")`. Trivial; can be bundled with MEDIUM-1 code fix.

### LOW-2 — Test name vs assertion mismatch

**Location:** `tests/test_hf1_path_guard_candidate_carveout.py:128` (`test_candidate_carveout_rejects_signed_registry_candidate_collision`)

The test name says "rejects" but `assert _is_candidate_carveout(path) is True` confirms the helper ALLOWS the path. The docstring is candid about this. A reader scanning test names would conclude defense-in-depth is enforced when it isn't.

**Fix proposal:** Rename to `test_candidate_carveout_currently_allows_GS_NNN_candidate_name_collision_DOCUMENT_GAP` until the MEDIUM-1 code fix lands, then flip to `_blocks_` after the fix.

---

## Engineering-coherence summary

The amendment correctly splits HF1.7, lands the carve-out at the right plumbing layer (find_violations short-circuit before ZONE walk), preserves HF1.7a hard-stop + HF1.8 self-protection, follows HF1.8 bootstrap discipline verbatim, and rolls the audit log correctly to window-001 with window-000 SEALED. The 16 new tests pin the right behaviors and the full sweep stays green at 2278/7. The one MEDIUM gap is a narrative overstatement of defense-in-depth that costs 5 LOC + 1 test to close cleanly.

---

## Special note: bootstrap discipline survival + carve-out scope

**Bootstrap discipline: SURVIVED.** The HF1.8 self-protection clause exists so the guard cannot silently self-modify. This commit modifies the guard, but: (a) the commit message explicitly names AR-2026-05-16-001 as the amendment cycle and explains the bootstrap rationale verbatim ("the HF1.8 clause exists so the guard cannot SILENTLY self-modify; the required ADR cover is in the same commit"); (b) the ADR-011 amendment lands in the SAME commit as the guard change, satisfying "every change to it must come through a PR with explicit AR/ADR cover" (ADR-011 §HF1 #8); (c) the override env-var carries the bootstrap reason. Future modifications to the guard remain protected because HF1.8 itself is unchanged.

**Carve-out scope: CORRECTLY NARROW** (with the MEDIUM caveat above). HF1.7a still seals `^GS-\d{3}$` signed-registry directories. The carve-out applies ONLY when path starts with `golden_samples/` AND first segment ends in `-candidate` AND first segment does not fullmatch `^GS-\d{3}$`. HF1.1-HF1.6, HF1.8, HF1.9 are untouched (test_non_golden_samples_zone_entries_still_hard_stop pins this). The carve-out scope does NOT widen the protective surface — it only narrows HF1.7. The MEDIUM finding is about defense-in-depth narrative truth, not actual surface widening.

**Rejection-message hygiene: CONFIRMED.** Probe 4 verified the stderr rejection block does NOT leak `HF1_GUARD_OVERRIDE` env-var contents even when set. The block lists the new AR-2026-05-16-001 carve-out resolution path FIRST so a reviewer reading the rejection sees the legitimate (non-override) path before falling to override/ADR cycles.

**Forbidden-token grep:** ZERO hits across all slice-D artifacts (ADR-011, hf1_path_guard.py, hf_audit.md, hf_audit_window-000.md, both test files). Verbatim grep command in audit log; no `validated against|perforation completed|bullet-through-steel complete|validated physics|production ready|certified|approved for service|asme compliant|signed off` outside fixture/test inputs (none present).

**Audit-log rollover: CORRECT.** `reports/archive/hf_audit_window-000.md` is a complete pre-amendment snapshot with SEALED status note added at top; `reports/hf_audit.md` is a clean window-001 head with carve-out IN FORCE.
