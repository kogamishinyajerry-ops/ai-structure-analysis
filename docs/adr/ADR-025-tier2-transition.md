# ADR-025 — Tier 1 reviewer-harness → Tier 2 production-class transition

**Status:** Accepted (FM-04a Phase 18, 2026-05-17)
**Authors:** Claude Opus 4.7 (1M ctx)
**Authorized by:** User directive 2026-05-17 (scope-tradeoff dialogue:
"拆除 Tier 1 约束 · 真接 solver" + "5-slice 深打磨" +
"按整个工业 FEA 工具栈评" + "绝对诚实客观").
**Supersedes:** Tier 1 hard constraints implicit in Phases 1-17 ADR
chain (ADR-011 §Tier-1 posture, ADR-012 calibration cap, the implicit
"no real solver" discipline running through every phase from Sprint-N
forward).
**Does NOT supersede:** ADR-011 §HF1.7a signed-registry hard-stop,
§HF1.7b candidate carve-out, §HF1.8 path-guard self-protection. Those
remain load-bearing and apply in Tier 2 unchanged.

---

## 1. Context

Phases 1-17 established a **Tier 1 engineering candidate** harness:
synthetic-only solver fixtures, advisor-only AI posture, a hard
4-question gate, a 9-token forbidden-positive-claim audit, and a
`claim_tier` field hard-coded to the string `"Tier 1 engineering
candidate"` on every envelope. The discipline served its purpose —
preventing the system from silently presenting unsigned engineering
candidates as validated production claims — and Phase 16-17 closed
the drift-attribution surface to a defensible maturity.

The Tier 1 posture, however, blocks the next class of value:

* **No real solver runs.** A reviewer can never see the harness
  exercise actual CalculiX `ccx` against a real geometry; the
  cylinder-pv-candidate and rod-wave-impact-candidate cohorts ship
  synthetic .frd fixtures only.
* **No analytical cross-checks.** Without a real solver result, the
  harness cannot compare against an analytical hoop-stress / beam-
  deflection / thin-cylinder solution to substantiate a Tier 2
  validation claim.
* **AI is read-only.** The advisor can critique but cannot trigger
  a re-mesh, swap a material, or re-run the solver — every executable
  action requires the reviewer to leave the harness and use an
  external tool.

The user has authorized lifting the Tier 1 hard constraints to enable
a Tier 2 transition: real solver subprocess (delivered in Phase 18 A),
tier-scoped claim discipline (this ADR), and AI driver mode (Phase 18
D).

## 2. Decision

Introduce a **`ClaimTier` discriminator** on envelopes and scope the
project's Tier 1 disciplines accordingly. Two values are defined:

| Tier value | When it applies | Claim boundary copy |
|---|---|---|
| `tier_1_candidate` | Synthetic fixture data; no real solver invocation; case carries no analytical cross-check | `tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement` (unchanged from Phase 1-17) |
| `tier_2_validated` | Real `ccx` subprocess produced the result; analytical cross-check evidence present in the envelope | `tier2_real_solver_validated; not_signed_validation; cross_check_against_analytical` |

The discriminator is **per-envelope** (each report envelope decides
its own tier from the case provenance), backed by a **single SSOT
registry** (`CLAIM_TIER_REGISTRY` in
`backend/app/services/reporting/_claim_tier.py`) mapping `case_id` →
default tier. Migration path for the 5-case cohort:

* `cylinder-pv-candidate` becomes `tier_2_validated` only after Slice
  A end-to-end ccx run produces a non-empty `.frd` with stress field
  present. Until that's reproducible end-to-end on the dev box, it
  stays `tier_1_candidate`.
* The other 4 candidates stay `tier_1_candidate`.
* New synthetic candidates default to `tier_1_candidate`.
* `^GS-\d{3}$` signed-registry cases are **NOT** allowed to flip to
  `tier_2_validated` via this mechanism — they keep their own
  signed-registry provenance discipline (HF1.7a preserved).

### 2.1 Tier-scoped forbidden-token policy

The Phase 11 `ADVISOR_FORBIDDEN_TOKENS` (9 tokens) becomes a
**tier-scoped** policy in
`backend/app/services/reporting/_forbidden_tokens.py`:

* **`FORBIDDEN_TOKENS_ADVISOR_CLASS`** (5 tokens): `production ready`,
  `certified`, `approved for service`, `asme compliant`, `signed off`.
  These represent **reviewer judgment authority**, not solver output.
  **Refused regardless of tier.** Even a tier_2_validated envelope
  cannot legitimately claim "certified" or "signed off" — that
  authority lives outside this harness entirely.
* **`FORBIDDEN_TOKENS_SOLVER_CLASS`** (4 tokens): `validated against`,
  `perforation completed`, `bullet-through-steel complete`,
  `validated physics`. These represent **solver evidence claims**.
  **Allowed when `tier == "tier_2_validated"` AND the envelope cites
  an analytical cross-check verdict.** Refused on
  `tier_1_candidate` envelopes (unchanged Phase 11 behavior).

This is the minimum policy change needed to let a real-solver result
say "validated against the analytical thin-cylinder solution to within
2% hoop stress" without the audit reflexively refusing — while still
preventing the system from ever claiming reviewer-level certification
authority.

The existing inline `ADVISOR_FORBIDDEN_TOKENS` tuple in
`backend/app/services/reporting/advisor_critique.py` is **NOT removed**
in Phase 18 B. The tier-aware policy is a **NEW consumer-facing SSOT**;
the advisor critique path keeps its hard refusal as defense-in-depth
since advisor critiques never carry a real-solver result. A future
phase may unify the two if/when the advisor critique path needs to
emit tier_2_validated envelopes (currently it doesn't).

### 2.2 4-question gate flips to reporting-only on tier_2_validated

The Phase 11 `_audit_four_question_gate` function raises `ValueError`
on a False answer to any of the four gate questions
(`llm_offline_ok`, `artifacts_user_owned`, `trustgate_explains`,
`advisor_only`). This was correct for Tier 1: a False on
`advisor_only` meant the system had drifted out of advisor posture
entirely, and we wanted loud failure.

Phase 18 introduces a **reporting-only sibling**
(`build_gate_audit_record` in
`backend/app/services/reporting/gate_audit.py`) that **never raises**
and instead returns a structured `GateAuditRecord` carrying the
boolean answers + a list of False keys + a list of missing keys.
Consumers that want the loud-failure behavior keep calling the
existing `_audit_four_question_gate`; the new sibling is for surfaces
that want to **report** the gate state as audit metadata rather than
gate on it.

Rationale for the sibling rather than flipping the existing function:
the Tier 1 hard-raise discipline is still correct for advisor critique
construction; a tier_2_validated envelope produced by a real solver
run is a different path with different posture semantics. Adding the
sibling lets each consumer pick the right behavior without breaking
the 17-phase advisor envelope chain.

### 2.3 Schema-bump policy stays MINOR-additive for now

The new `tier` field on envelopes is **additive optional** with a
`tier_1_candidate` default for back-compat (envelopes without a `tier`
field are read as `tier_1_candidate`). This is a **MINOR** bump under
RFC-001 §6.3 schema discipline, not a MAJOR one. A future phase may
promote it to required (MAJOR bump) once every producer pathway has
been audited; Phase 18 keeps the change conservative.

## 3. Consequences

**Enabling:**
* Phase 18 A `CalculiXRunner` can emit envelopes that legitimately
  claim "validated against analytical" without tripping the forbidden-
  token audit, provided the case is registered as `tier_2_validated`
  AND the envelope cites an analytical cross-check.
* Phase 18 C mesh + materials pipeline can register new cases at
  whichever tier their provenance supports.
* Phase 18 D frontend can render tier-aware claim banners (the
  reviewer sees a different boundary copy on Tier 2 envelopes).
* AI advisor can stop refusing solver-class language on Tier 2 cases
  while still refusing advisor-class language regardless of tier.

**Preserving:**
* HF1.7a signed-registry hard-stop intact.
* HF1.7b candidate carve-out intact.
* Existing 4-question gate hard-raise path in `advisor_critique.py`
  intact (advisor critique envelopes still must answer True on all
  four).
* All Phase 1-17 envelope shapes back-compat (no `tier` field reads
  as `tier_1_candidate`).
* All 9 forbidden tokens still refused on `tier_1_candidate` envelopes.
* Advisor-class 5 tokens refused regardless of tier (reviewer
  authority is not delegated to the harness in any tier).

**New surface area** (audit / test coverage):
* `_claim_tier.py` SSOT must stay the only place that says
  "cylinder-pv-candidate is tier_2_validated" — duplicating that
  string anywhere else is a smell.
* `_forbidden_tokens.py` `is_token_allowed(token, *, tier)` must be
  the only place that decides token-vs-tier policy. Inline `if token
  in FORBIDDEN_TOKENS` checks elsewhere indicate stale code.
* `gate_audit.py` `build_gate_audit_record` must never raise on
  invalid gate input — it returns structured audit, not a refusal.

**Migration risk** (called out for retro):
* A case incorrectly registered as `tier_2_validated` would let the
  system pass solver-class claims through the audit. Mitigated by:
  registry change requires a code edit + tests + commit (no runtime
  override), and the registry itself is the SSOT (no duplication
  surface).
* Two consumers reading the same envelope could draw different
  conclusions if one uses `_claim_tier.get_claim_tier(case_id)` and
  the other reads a stale string field. Mitigated by: new consumers
  are pointed at the SSOT helper; existing Phase 1-17 consumers
  continue to read their inline strings (which still correctly say
  "Tier 1 engineering candidate" because no case has been re-
  registered in those code paths yet).

## 4. Rollback plan

If the Tier 2 transition surfaces an integrity failure (e.g., a
tier_2_validated envelope ships without the analytical cross-check
the registry promises), the rollback path is:

1. `CLAIM_TIER_REGISTRY` entries flip back to `tier_1_candidate` —
   single-file edit, takes effect on next request.
2. The two new modules (`_claim_tier.py`, `_forbidden_tokens.py`,
   `gate_audit.py`) can be left in place — they are additive and
   inert when no envelope claims tier_2_validated.
3. ADR-025 status changes to `Superseded by ADR-NNN` documenting
   the integrity failure observed.

No 17-phase envelope shape changes. No Phase 1-17 test regressions
expected (every existing test reads `tier_1_candidate` as default).

## 5. Cross-references

* FM-04a Phase 18 blueprint (`.planning/FM-04A_PHASE18_BLUEPRINT.md`)
* Phase 18 A real CalculiX runner (commit 94fcffa)
* ADR-011 (the unchanged HF1.7a/b/8 disciplines this ADR explicitly
  preserves)
* Phase 11 advisor critique chain (`advisor_critique.py`
  ADVISOR_FORBIDDEN_TOKENS + FOUR_QUESTION_GATE_KEYS) — referenced as
  the inline policy this ADR offers a tier-scoped sibling to, not as
  a path being removed.
