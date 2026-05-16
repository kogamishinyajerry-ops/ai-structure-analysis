# `/{case_id}` route discipline — SSOT methodology

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**
>
> **Scope:** the cross-route contract for `/api/v1/.*/{case_id}` reviewer-facing surfaces. Every such route MUST consistently refuse `^GS-\d{3}$` signed-registry identifiers with a 422 + canonical detail vocabulary BEFORE any filesystem lookup or service-layer call.
>
> **Status:** Phase 14 A. Closes Phase 13 retrospective slice-B LOW #3 carry-forward.

## Why this discipline exists

Phase 11 introduced the AI advisor surface with a per-route signed-registry refusal at `/api/v1/advisor-critique/{case_id}` (Phase 11 D gate #2). Phase 13 B closed the equivalent gap on `/api/v1/case-completeness/{case_id}` (originally flagged in Phase 12 F slice-F LOW). Both surfaces refused signed-registry case_ids with 422 + a "refuses signed-registry … only accept *-candidate identifiers … out of scope" vocabulary.

Other `/{case_id}` reviewer-facing routes (trust-score / trust-score-timeline / trust-score-alerts / acceptance-packet / convergence-study / reproducibility-manifest / tier1-report / signoff-history / trust-score-provenance / visualize-result-mesh) inherited inconsistent behavior:

* Some silently returned 200 on `GS-001` (cohort-surface inconsistency — the worst case).
* Some returned 404 because the signed-registry directory genuinely lacks the candidate evidence structure (filesystem rejection, not refusal).
* `signoff-history` GET returned 400 via service-layer ValueError pass-through.
* `signoff-history` POST returned 422 with a slightly different vocabulary ("signoff POST refuses signed-registry … Tier 1 candidate signoffs only accept *-candidate identifiers" — different from the 422-canonical "*-candidate identifiers (sealed FM-04b packets are out of scope)").

Phase 13 retrospective §2 named the gap: "a future new route reading case_id might silently accept `GS-NNN` and route around the discipline. Phase 14: consider a route-level meta-test that enumerates all `^/api/v1/.*/{case_id}` routes and asserts each one rejects signed-registry case_ids consistently."

Phase 14 A closes the gap with:
1. A single SSOT helper `assert_not_signed_registry(case_id, surface_name)` at `backend/app/api/routes/_signed_registry_refusal.py`.
2. Every reviewer-facing `/{case_id}` route calls the helper after the syntactic `_CASE_ID_RE.fullmatch` check.
3. A meta-test that enumerates every `/{case_id}` route via FastAPI introspection and asserts each one trips the canonical 422 + vocabulary.

## The canonical refusal contract

Every Tier 1 reviewer-facing route handler MUST:

1. Reject syntactically malformed `case_id` with **400** `"invalid case_id"` (e.g., URL-decoded space characters; this gate is per-route, using the local `_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")` pattern).
2. Call `assert_not_signed_registry(case_id, "<surface-name>")` from `_signed_registry_refusal.py`. The helper raises **422** `<surface-name> refuses signed-registry case_id; Tier 1 candidate surfaces only accept *-candidate identifiers (sealed FM-04b packets are out of scope)`.
3. Proceed with route-specific handler logic.

The 422 raise is BEFORE any filesystem lookup so a tampered or hypothetical seeded signed-registry directory under `golden_samples/` cannot leak data through a Tier 1 candidate route.

## Why 422 (not 400)?

* **400 `Bad Request`** means "the syntax of the request is malformed". A `GS-001` case_id is SYNTACTICALLY VALID (matches `^[A-Za-z0-9_-]{1,64}$`), so 400 mis-classifies the refusal as a malformation error.
* **422 `Unprocessable Entity`** means "the request is well-formed but the server refuses to process it for semantic reasons" — exactly what a signed-registry refusal is.
* Advisor-critique (Phase 11) + case-completeness (Phase 13 B) both use 422; Phase 14 A makes 422 the cross-route canonical.

## The opt-out list

Some `/{case_id}` routes are NOT Tier 1 reviewer-facing surfaces OR are sub-routes whose parent path already participates in the contract. These routes legitimately bypass the per-route SSOT helper call (either because they're not in scope, or because the parent route's gate already protects them via the same handler module). The opt-out list is documented in `tests/test_phase14_cross_route_signed_registry_refusal.py` `_OPT_OUT_ROUTES` SSOT:

* `GET /api/v1/cases/{case_id}` — generic case-fetching workbench API; not Tier 1 reviewer surface. Backed by a database, not the `golden_samples/` reviewer-facing evidence path. Returns DB rows regardless of case_id shape; not part of the Tier 1 disclaimer trio surface.
* `GET /api/v1/api/v1/history/{case_id}` — NL copilot chat history; not Tier 1 candidate surface. Module is `backend.app.api.nl` (preexisting double-prefix routing bug from Phase 1.5 frozen surface).
* `GET /api/v1/visualize/result-mesh/{case_id}/{artifact_path:path}` — artifact sub-path under the result-mesh route. The PARENT route `/api/v1/visualize/result-mesh/{case_id}` IS in scope (listed in `_KNOWN_CASE_ID_ROUTES`) and calls `assert_not_signed_registry(case_id, "visualize-result-mesh")`. The artifact sub-route is served by the same handler module and inherits the parent's gate via the same helper call. Listed here so the meta-test's set-equality enumeration check matches.
* `POST /api/v1/signoff-history/{case_id}` — signoff POST IS in scope and uses the SSOT helper since Phase 14 A (vocabulary harmonized from the legacy "signoff POST refuses signed-registry … only accept *-candidate identifiers" wording to the canonical SSOT vocabulary). The meta-test's per-route parametrize tracks GET-only routes (the enumeration would otherwise produce duplicate (method, path) entries against the same path); POST behavior is pinned by `tests/test_phase9_signoff_post_endpoint.py` separately.

A new route added to the codebase MUST either:
* Call `assert_not_signed_registry` (and pass the meta-test), OR
* Land in `_OPT_OUT_ROUTES` with a docstring rationale explaining why it is NOT a Tier 1 reviewer surface.

The meta-test's `_KNOWN_CASE_ID_ROUTES` SSOT tuple pins the expected enumeration so a NEW route that omits both the helper call AND the opt-out list trips the test with the unfamiliar route path in the failure message.

## Helper-call ordering — MUST fire BEFORE any filesystem stat

The SSOT helper `assert_not_signed_registry(case_id, surface_name)` MUST be the FIRST per-case_id check in every route handler, AFTER the per-route `_CASE_ID_RE.fullmatch` syntactic shape gate but BEFORE:

* any filesystem `.resolve()` / `.is_file()` / `.exists()` on a path derived from `case_id`,
* any service-layer call that reads from `golden_samples/` / `project_state/` / disk,
* any `_resolve_*` helper that maps `case_id` to a path under those roots,
* any database query whose key is derived from `case_id`.

Why: the A:-7 defense-in-depth posture relies on the refusal happening BEFORE the route touches the filesystem. A planted artifact under a signed-registry case_id (`project_state/visualizations/GS-001/result_mesh.json`, hypothetical) MUST be refused without ever being stat'd. A helper call that fires AFTER the filesystem touch still produces a 422 response, but the operating system has already revealed the path's existence (timing side-channel; surfaces inode + permissions to the handler frame; logs may include the path). Phase 14 A retrospective recorded one such ordering miss in `visualization.py` (helper sat after `_resolve_result_mesh_artifact_path`); the fix swaps the call order so the helper fires first and the artifact resolver is never reached on a signed-registry id.

The meta-test enumerates all in-scope routes and ASSERTS the helper trips on `GS-001` before any downstream handler logic; ordering regressions would manifest as a route that returned 404/200/400 instead of 422 on a planted signed-registry artifact. Until a fixture is planted under a signed-registry id (HF1.7a / HF1.7b prevent this on disk; the audit is the static-analysis test by code review), the meta-test exercises the symptom — 422 with the canonical detail — and the ordering invariant is documented here as the LIVE rule.

## Anti-gaming guards pinned by tests

* **M:-2** — `SIGNED_REGISTRY_RE` and `assert_not_signed_registry` are module-level SSOTs in `_signed_registry_refusal.py`; every route imports from the SSOT rather than duplicating the regex.
* **T:-3** — per-route parametrize over `_KNOWN_CASE_ID_ROUTES` so a per-route failure surfaces with the route path in the test name.
* **T:-4** — SSOT enumeration test that asserts the introspected route set matches `_KNOWN_CASE_ID_ROUTES ∪ _OPT_OUT_ROUTES`; a silent route addition trips this test.
* **C:-8** — the canonical detail vocabulary contains no forbidden positive-claim tokens; the vocabulary is the same SSOT across every route.
* **A:-7** — defense in depth: the helper raises BEFORE filesystem lookup so a tampered registry directory cannot leak through the route.

## Reference

The Phase 14 retrospective at `.planning/retrospectives/fm04a_phase14_explicit_dynamics_substantiation.md` will document the closure of Phase 13 retro slice-B LOW #3 by this surface.
