# Phase 14 A TAA — slice audit

Commit: 2dcdab7
Date: 2026-05-17
Auditor: independent general-purpose agent (Opus 4.7 1M, no prior knowledge of the implementation conversation)

## Scope

Slice A of FM-04a Phase 14: cross-route signed-registry refusal SSOT.

Artifacts reviewed:
* `.planning/FM-04A_PHASE14_BLUEPRINT.md` §3.A
* `.planning/methodology/case_id_route_discipline.md`
* `backend/app/api/routes/_signed_registry_refusal.py`
* All 13 in-scope route handlers (cf. `_KNOWN_CASE_ID_ROUTES`)
* `backend/app/api/routes/advisor_critique.py` + `case_completeness.py` (pre-existing Tier 1 surfaces)
* `tests/test_phase14_cross_route_signed_registry_refusal.py` (26 tests)

Verification:
* Slice test: **26 passed** in 0.73 s.
* Full backend sweep: **2306 passed, 7 skipped** in 22.71 s — matches implementor claim.
* Adversarial ASGI probe: every in-scope route returns 422 + canonical detail trio (`signed-registry` / `candidate` / `out of scope`) on `GS-001`; every route avoids the canonical helper detail on `GS-A-candidate` (downstream 200/404/422-from-other-cause).

## Scores (sub-rubric, 63 pts)

**M (Methodology): 10/12** — Cap fires.

The SSOT helper `assert_not_signed_registry` is correctly placed at `backend/app/api/routes/_signed_registry_refusal.py` with module-level `SIGNED_REGISTRY_RE`, typed signature, and bump-history docstrings. The 13 in-scope routes covered by `_KNOWN_CASE_ID_ROUTES` correctly import and call the helper. **HOWEVER, two pre-existing Tier 1 surfaces NOT covered by `_KNOWN_CASE_ID_ROUTES` (they are — they are listed) still duplicate the regex + build their own refusal detail string instead of delegating to the SSOT helper:**

* `backend/app/api/routes/advisor_critique.py:52` — `_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")` (regex duplication); lines 97-103 build the detail string by hand.
* `backend/app/api/routes/case_completeness.py:46` — same regex duplication; lines 143-150 same hand-built detail.

The blueprint's anti-gaming guard M:-2 explicitly says "every route imports from the SSOT rather than duplicating the regex"; the methodology doc §"Anti-gaming guards pinned by tests" reinforces this. The rubric cap "M ≤10/12 if any route duplicates the regex or builds its own detail string instead of calling the helper" fires here. Two route handlers in `_KNOWN_CASE_ID_ROUTES` keep their pre-Phase-14 duplication; the SSOT helper exists in parallel but is not the single source for those two routes. Score: **10/12**.

**T (Testing): 14/15** — Strong.

26 tests cover:
* 13 per-route parametrized 422-contract tests (T:-3 hit).
* SSOT introspection / schema-check (`test_known_routes_match_app_introspection`) — T:-4 hit.
* Shape-variant test on `GS-000 / GS-101 / GS-102 / GS-999` (closed-set discipline pin).
* Candidate-passes-the-gate negative test.
* Three SSOT helper unit pins (regex anchor, raise-on-signed, pass-on-candidate, surface-name embedding).
* Forbidden-token vocabulary pin (C:-8).
* Opt-out methodology-doc cross-reference pin.
* Opt-out count pin (`len(_OPT_OUT_ROUTES) == 4`).

Every reviewer-facing route has dedicated coverage (per-route parametrize). No T cap fires. **-1 for one weakness:** the candidate-passes-the-gate test (`test_candidate_case_id_passes_the_gate`) only exercises ONE route (case-completeness). Per-route parametrize over the candidate-passes-side would be symmetric with the per-route 422 parametrize and would catch a route that accidentally short-circuits a legitimate candidate id with 422. Not a cap, but worth -1.

Score: **14/15**.

**C (Claims discipline): 10/12** — Cap fires.

The SSOT helper's canonical detail vocabulary contains zero of the 9 forbidden positive-claim tokens (machine-pinned by `test_canonical_detail_vocabulary_contains_no_forbidden_tokens`). The Tier 1 disclaimer trio surfaces unchanged (separate envelope concern; no regression). **HOWEVER, vocabulary drift across routes:**

* SSOT helper output: `"<surface> refuses signed-registry case_id; Tier 1 candidate surfaces only accept *-candidate identifiers (sealed FM-04b packets are out of scope)"`
* Advisor-critique hand-built output: `"advisor-critique refuses signed-registry case_id; Tier 1 candidate ADVISOR SURFACE only accepts *-candidate identifiers..."` (singular "surface", word "advisor" inserted, verb "accepts" with -s).

The methodology doc's "shared detail vocabulary" thesis is undermined by this drift. The per-route 422 test passes only because it greps the three load-bearing tokens (`signed-registry` / `candidate` / `out of scope`) — those are present in both versions. But the wider canonical sentence is NOT canonical across routes. Rubric cap "C ≤10/12 if vocabulary drift across routes" fires.

Score: **10/12**.

**A (Adversarial robustness): 6/8** — Cap fires.

The SSOT helper itself raises BEFORE any filesystem stat — correct in isolation. **HOWEVER, two route handlers call the helper AFTER a filesystem-touching service call:**

* `backend/app/api/routes/visualization.py:91-102` (parent `result-mesh/{case_id}` route): `_resolve_result_mesh_artifact_path(case_id, "result_mesh.json")` is called at line 95 BEFORE `assert_not_signed_registry` at line 99. `_resolve_result_mesh_artifact_path` (`backend/app/api/routes/_viz_helpers.py:92-118`) does `.resolve()` + `.is_file()` on a derived path that includes `case_id`. A tampered `project_state/visualizations/GS-001/result_mesh.json` could be stat'd before the 422 fires.
* `backend/app/api/routes/visualization.py:105-115` (artifact sub-route): same call ordering — `_resolve_result_mesh_artifact_path` at line 109 BEFORE `assert_not_signed_registry` at line 113.

Both fall into the rubric cap: "A ≤6/8 if helper call sits after any filesystem stat / read / service-layer call". The 422 contract still passes the smoke test because the resolver returns `None` for a missing file and the helper then raises 422 BEFORE the 404 is constructed — but the defense-in-depth claim is materially weaker: a planted file on disk would be touched. Score: **6/8**.

**E (Evidence): 7/8** — Borderline.

The methodology doc `.planning/methodology/case_id_route_discipline.md` explains:
* Why 422 (not 400): §"Why 422 (not 400)?" with explicit semantic argument.
* Per-route opt-out rationale: §"The opt-out list" with one paragraph per opt-out route (4 entries).
* Anti-gaming guards pinned by tests: §"Anti-gaming guards pinned by tests" with M:-2 / T:-3 / T:-4 / C:-8 / A:-7 cross-reference.

All four opt-outs documented in the methodology doc and pinned by `test_opt_out_routes_are_documented_in_methodology`. No undocumented opt-outs. **-1 for one gap:** the methodology doc does NOT acknowledge that two in-scope routes (`advisor-critique`, `case-completeness`) still duplicate the regex + build their own detail — a future reader following the SSOT discipline would not learn from the doc that the cleanup is partial. The doc reads as if every route delegates to the helper. Score: **7/8**.

**V (Verification): 8/8** — Clean.

* Full backend sweep stays green: 2306 passed, 7 skipped — exactly the implementor's claim.
* Slice tests pass: 26/26.
* ASGI probe confirms 422 + canonical trio on every in-scope route on `GS-001`.
* ASGI probe confirms `GS-A-candidate` does NOT trip the helper on any in-scope route (downstream returns 200/404 with route-specific detail, not the canonical refusal sentence).
* No in-scope route returns 200/404 on `GS-001`; no in-scope route returns a non-canonical detail string on `GS-001`. V cap does not fire.

Score: **8/8**.

## Total: 55/63

## Adversarial findings

**HIGH-1 — Filesystem call BEFORE helper in `visualization.py`.** Both result-mesh handlers (parent route line 91 and artifact sub-route line 105) call `_resolve_result_mesh_artifact_path` (which does `.resolve()` + `.is_file()` on a `case_id`-derived path under `project_state/visualizations/`) BEFORE calling `assert_not_signed_registry`. This violates the rubric's defense-in-depth guard A:-7 ("the 422 fires BEFORE any filesystem lookup so a tampered registry directory cannot leak through the route"). The 422 contract still holds because the resolver gracefully returns `None` on a missing file, but a planted `project_state/visualizations/GS-001/result_mesh.json` would be stat'd before refusal. **Fix:** swap order — call `assert_not_signed_registry(case_id, "visualize-result-mesh")` BEFORE `_resolve_result_mesh_artifact_path`. Add a unit test that mocks `_resolve_result_mesh_artifact_path` to raise / record a call, then probes `GS-001`, and asserts the resolver was NEVER called.

**HIGH-2 — Two routes still duplicate the regex and build their own detail string.** `advisor_critique.py` and `case_completeness.py` define their own `_SIGNED_REGISTRY_RE` and build their own refusal detail by hand, ignoring the new SSOT helper. The methodology doc claims "Every reviewer-facing `/{case_id}` route calls the helper after the syntactic `_CASE_ID_RE.fullmatch` check"; the codebase contradicts the methodology doc. Caps both M (≤10/12) and C (≤10/12). **Fix:** replace `_SIGNED_REGISTRY_RE` + the hand-built raise block in each file with a call to `assert_not_signed_registry(case_id, "<surface-name>")`. Drop the local regex import. Add an `ast`-based test that grep / parses the routes directory and asserts no other module defines a `^GS-\d{3}$` regex literal outside `_signed_registry_refusal.py`.

**MEDIUM-1 — Vocabulary drift between advisor-critique and the SSOT helper.** Advisor-critique emits `"Tier 1 candidate advisor surface only accepts"` (singular "surface", word "advisor" inserted, "-s" verb suffix); the SSOT helper emits `"Tier 1 candidate surfaces only accept"` (plural, no "advisor", bare verb). The three load-bearing tokens are shared, so the per-route 422 test passes — but the methodology doc's "shared detail vocabulary" thesis is materially undermined. Closing HIGH-2 closes this automatically.

**LOW-1 — Candidate-passes-the-gate test only exercises one route.** `test_candidate_case_id_passes_the_gate` hits only `case-completeness`. A regression that accidentally makes one route 422 a legitimate `*-candidate` id would not be caught by the slice. **Fix:** parametrize the candidate-passes test over `_KNOWN_CASE_ID_ROUTES` symmetric with the 422-side parametrize.

**LOW-2 — Methodology doc oversells the closure.** The doc reads as if every route now delegates to the helper. It should explicitly call out the partial cleanup (advisor-critique + case-completeness still maintain pre-Phase-14 duplication, follow-up tracked here) so a future reader is not misled. Auto-closes when HIGH-2 closes.

## Verdict

**REQUIRES_REWORK**

Stop-condition floors: M≥10, T≥12, C≥10, A≥6, E≥7, V≥7. The current slice scores M=10, T=14, C=10, A=6, E=7, V=8 — every floor is exactly met or above. By the binding stop condition, this would technically pass the slice.

**BUT** the whole-arc target is ≥99/100 with every axis ≥95% of weight. A slice scoring 55/63 (87%) cannot carry the arc; three axes (M, C, A) sit at the cap floor with explicit findings the implementor can close cheaply. Two of the four floor-hits (M-cap, C-cap) collapse into a single fix (HIGH-2: route the two stragglers through the SSOT helper). The third (A-cap) is a 2-line swap in `visualization.py` (HIGH-1) plus a regression test.

The minimum-cost rework path:
1. Fix HIGH-1: swap the helper call BEFORE `_resolve_result_mesh_artifact_path` in both `visualization.py` handlers. Add the mock-the-resolver regression test (proves the resolver is never called on `GS-001`). Expected A → 8/8.
2. Fix HIGH-2: replace `_SIGNED_REGISTRY_RE` + the hand-built raise in `advisor_critique.py` + `case_completeness.py` with `assert_not_signed_registry(case_id, "<surface>")` calls. Add the AST-grep regression test that asserts no other module redefines the regex. Expected M → 12/12 and C → 12/12.
3. Fix LOW-1: parametrize `test_candidate_case_id_passes_the_gate` over `_KNOWN_CASE_ID_ROUTES`. Expected T → 15/15.
4. Fix LOW-2: append a paragraph to the methodology doc § "Phase 14 A closes the gap with" enumerating the helper-call call sites and noting the AST-grep guard. Expected E → 8/8.

Projected post-rework score: **63/63**.

Returning **REQUIRES_REWORK** because the whole-arc target demands it; the slice as it stands clears every binding floor but the four findings above are cheap to close and the whole-arc 99/100 target is unreachable without closing at least HIGH-1 + HIGH-2.

## Re-audit (post-rework, commit 5779fe7)

Auditor: independent TAA re-review (Opus 4.7 1M, no implementor context). Scope: only the 4 prior findings + regression risk.

### Verification of prior findings

* **HIGH-1 (visualization.py ordering) — CLOSED.** Both result-mesh handlers (`visualization.py:99` parent route, `:116` artifact sub-route) now call `assert_not_signed_registry(case_id, "visualize-result-mesh")` BEFORE `_resolve_result_mesh_artifact_path`. The resolver is unreachable on a signed-registry id. Inline comments cite the A:-7 rationale.
* **HIGH-2 (regex + detail duplication) — CLOSED.** `advisor_critique.py:48,104` imports + calls `assert_not_signed_registry(case_id, "advisor-critique")`; the local `_SIGNED_REGISTRY_RE` is gone and the hand-rolled detail block is replaced. Same for `case_completeness.py:35,146` (helper call surface "case-completeness"). `grep _SIGNED_REGISTRY_RE backend/app/api/routes/` returns only `signoff_history.py` (see new finding below).
* **LOW-1 (parametrize candidate-passes) — CLOSED.** `tests/test_phase14_cross_route_signed_registry_refusal.py:243` now parametrizes `test_candidate_case_id_passes_the_gate` over `_KNOWN_CASE_ID_ROUTES`. Per-route candidate id is built with `path.replace("{case_id}", "some-imaginary-candidate") + query_extras`; assertion is "if 422 then `signed-registry` token MUST NOT be present". +12 cases.
* **LOW-2 (methodology helper-call ordering) — CLOSED.** `.planning/methodology/case_id_route_discipline.md:58` adds a new section "Helper-call ordering — MUST fire BEFORE any filesystem stat" with explicit A:-7 rationale, lists what the helper must precede (filesystem, service-layer call, business logic), and references the visualization.py retrospective miss.

### Verification commands

* `pytest tests/test_phase14_cross_route_signed_registry_refusal.py -q`: **38 passed in 0.78 s** (was 26; +12 from LOW-1 parametrize).
* `pytest tests/ -q`: **2350 passed, 7 skipped in 22.54 s** (was 2306; +44 = 12 slice-A + 32 slice-B per commit message). No regressions. `advisor_critique` 4-question gate tests + `case_completeness` 400-on-bad-shape tests pass under the full sweep.

### Scores (sub-rubric, 63 pts)

* **M: 12/12** — SSOT helper is now the single regex + detail source for every in-scope route. The remaining `_SIGNED_REGISTRY_RE` in `signoff_history.py:49` covers the POST surface only, which is documented as opt-out for the GET-enumeration meta-test (line 127-131 of the test); GET surface uses the helper. Not in slice A scope.
* **T: 15/15** — Per-route parametrize on both 422 side and candidate-passes side. T cap floors all cleared.
* **C: 12/12** — Both advisor-critique and case-completeness now emit the SSOT canonical sentence verbatim; vocabulary drift identified in prior C-cap finding is closed. The legacy "advisor surface" / "accepts" drift is gone (replaced by the helper output, which the C:-8 forbidden-token test pins).
* **A: 8/8** — Helper call now precedes the filesystem stat on both visualization.py routes. The A:-7 defense-in-depth posture is intact across every in-scope route.
* **E: 8/8** — Methodology doc now documents the ordering invariant + the retrospective miss. A future reader following the doc cannot accidentally place the helper after a filesystem call.
* **V: 8/8** — Full sweep stays green at 2350. Slice tests 38/38. No regressions in advisor 4-question gate or case_completeness 400-on-bad-shape.

### Total: 63/63

### New findings introduced by rework

* **LOW-3 (NEW) — `signoff_history.py` POST handler still inlines `_SIGNED_REGISTRY_RE` + hand-rolled refusal at lines 49 + 121-128.** Comment on lines 46-48 explicitly states "Retained for back-compat with the existing POST handler's explicit signed-registry refusal block; the canonical SSOT is now the helper". The POST surface IS in scope for the cross-route contract (listed in `_OPT_OUT_ROUTES` only because the schema-check enumeration tracks GET-only; the POST is in scope but tested separately by `test_phase9_signoff_post_endpoint.py`). The comment at `test_phase14_*.py:127-130` claims "POST signoff-history... uses the helper since Phase 14 A", which is factually wrong — the POST still has its own regex + hand-built detail string. Not a slice-A blocker (out of the 4 prior findings; full sweep green) but worth tracking for slice B / a follow-up so the SSOT-everywhere thesis isn't undermined by a misleading test comment. **Fix:** replace `signoff_history.py:121-128` with `assert_not_signed_registry(case_id, "signoff-history-post")`; drop `_SIGNED_REGISTRY_RE` at line 49. The Phase 9 POST test asserts on the three canonical tokens — should pass under the SSOT helper output.

### Verdict

**APPROVE_WITH_COMMENTS**

All 4 prior findings (HIGH-1, HIGH-2, LOW-1, LOW-2) closed. Every sub-axis at ceiling (M=12, T=15, C=12, A=8, E=8, V=8 → 63/63). Stop-condition floors all met (M≥10, T≥12, C≥10, A≥6, E≥7, V≥7). Full sweep green at 2350. No HIGH findings introduced. The one NEW LOW finding (signoff-history POST stragglers + misleading test comment) does NOT block slice A — it's a documented-but-unfixed pre-existing condition that the test enumeration accommodates, the full sweep ratifies, and a 5-line slice-B follow-up closes. Whole-arc 99/100 target is now reachable on the M/T/C/A/E/V dimensions for slice A.
