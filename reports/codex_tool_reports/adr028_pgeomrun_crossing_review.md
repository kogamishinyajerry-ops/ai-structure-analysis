# Codex Review — ADR-028 P-geomrun: real geometry.run dummy-mode tool-wall crossing (R0 → R1 APPROVE)

**Scope (THE highest honesty-risk slice; mandatory-Codex; honesty contract IS the deliverable):**
for a NACA/wing request, CALL the real `agents.geometry.run` node in the live pipeline under
`execution_mode=dummy` — the FIRST time a real tool-bound agent node executes live. CALL-only (no HF1
override; `agents/geometry.py` untouched). Landed on the just-shipped P-fidelity discriminator.

## Provenance: adjudicated REFRAME (not GO-replace, not DEFER-theater)

Pre-flight Workflow `wf_2cd96131-8f8` (2 readers → 3 honesty-stance proposers GO/REFRAME/DEFER → 3
adversarial verifiers → synthesizer) adjudicated the crux: *on dummy data `check_geometry`'s
`valid=True` is a JSON round-trip TAUTOLOGY* (read back from the sidecars the dummy writer hardcoded),
NOT a measurement — so the ONLY net-new honest fact over the planning stand-in is **`toolRan=True`**.
Verdict **REFRAME**: ADD that one bit as a strictly-additive `tier_0_dummy` wiring-proof (never swap
P-geomplan's honest negatives for a positive); DEFER (theater) and GO-replace (drops honesty fields)
both rejected. N/13 stays 6/13 — the crossing UPGRADES geometry's fidelity, it does not add a count.

## Two reasoned deviations from the blueprint (intentional honesty corrections, Codex-confirmed sound)

1. **Gate on `family=='naca_wing' AND not FREECAD_AVAILABLE`** (blueprint said "hardcode
   `data_real=False`"). Verified at source: `generate_geometry` produces REAL geometry when
   `FREECAD_AVAILABLE=True` (ignoring `allow_dummy`), so hardcoding `data_real=False` there would
   MISLABEL a real result `tier_0_dummy`. The dispatcher routes a real-kernel host back to the
   planning stand-in; the dummy projector also asserts `not FREECAD_AVAILABLE` (defense-in-depth). So
   `data_real` is always genuinely False on the crossing path.
2. **Fresh branch-accurate prose** (blueprint said "keep P-geomplan's verbatim '未生成 STEP、未做缺陷校验'
   + append"). In the crossing a placeholder STEP IS written and `check_geometry` DOES run (vacuously),
   so the planning prose would be FALSE. The crossing's disclosure says exactly what happened (a 10-byte
   placeholder STEP, a tautological `valid=True`); only the family/refSource/fromHint metric fields are
   reused.

## Honesty contract upheld (machine-pinned)

- Claim ceiling: "the real geometry agent node executed live under `execution_mode=dummy`
  (`toolRan=True`, `tier_0_dummy`)" — NOT "geometry validated".
- NO measurement key surfaced (watertight/manifold/volume/min_feature/bounding_box/valid) — test-pinned.
- `cadKernelRan=False` + `defectCheckRun=False` pinned; `provenance=deterministic_agent` → N/13 == 6/13.
- Disclosure states (all test-pinned): `FREECAD_AVAILABLE=False`, `10 字节` placeholder STEP, ADR-008
  N-3, `valid=True` is a `tautology`, `defectCheckRun=False`, `未验证` (no geometry validated), and the
  fixed `NACA0012` stand-in profile (`非从请求` — not parsed from the request).
- Temp-dir SimState assembled in the agent layer with `tempfile.TemporaryDirectory` (cleaned on
  with-exit; NO retained path); empty `StageArtifacts`.

## R0 — CHANGES_REQUIRED (1 P1 + 2 P2) → all fixed

- **P1** (`tool_ran` not enforced): a SUCCESS stage could hard-claim `toolRan=True` even if
  `geometry.run` returned no `geometry_path`. **Fix:** `if not tool_ran: raise RuntimeError(...)` after
  the with-block; new test `test_missing_geometry_path_refuses_to_claim_tool_ran` monkeypatches the node
  to return `{}` and asserts the raise.
- **P2b** (hardcoded NACA0012 for every request): the executed node wouldn't match a request naming
  another NACA profile. **Fix (disclose option):** the disclosure now states the geometry is a FIXED
  NACA0012 stand-in, `非从请求逐字解析` (the dummy STEP is a placeholder, so the profile is cosmetic);
  test pins `固定 NACA0012` + `非从请求`.
- **P2a** (test under-pinned): strengthened the crossing test to pin the FULL contract
  (`FREECAD_AVAILABLE=False` / `10 字节` / `tautology` / `defectCheckRun=False` / `未验证` / fixed profile).

## R1 — **APPROVE**

Verbatim (gpt-5.5 xhigh): *"APPROVE. All three R0 issues appear resolved … P1 is fixed by refusing to
emit the stage when geometry_path is absent, with a pinned regression test. P2a/P2b are now materially
pinned in the disclosure assertions … No new honesty-contract issue is apparent: tier_0_dummy,
toolRan=True, no measurement keys, false kernel/check flags, deterministic provenance, and N/13
unchanged are preserved."*

## Files

- `agents/state_projection.py` — `geometry_dummy_exec_to_stage_state` (CALL `agents.geometry.run` in a
  temp-dir dummy SimState; tier_0_dummy via `fidelity_metrics`; enforce `geometry_path`) +
  `geometry_stage_state` (family + `FREECAD_AVAILABLE` dispatcher); imports `tempfile`/`GeometrySpec`;
  `__all__` updated. Agent layer (imports `tools.freecad_driver` + CALLs `agents.geometry`; no backend).
- `backend/app/workbench/agent_facade.py` — GEOMETRY_VALIDATION routes through
  `state_projection.geometry_stage_state` (facade stays the sole `agents.*` importer, no `tools.*` import).
- `backend/tests/test_workflow_fidelity_discriminator.py` — +4 tests (crossing tier_0_dummy + full
  disclosure pins + N/13==6; NACA-only gate; FreeCAD-present fallback; missing-geometry_path raise);
  existing genuine-request test reframed as the non-NACA path.

## Gates

- Fidelity-discriminator suite **15 pass**; full backend **1278 pass / 24 skip / 1 xfail**; root
  facade-discipline + geometry_agent **29 pass**; ruff agents clean; `hf1_path_guard` EXIT=0; ADR-015
  intact (agent layer, no backend import; facade sole `agents.*` importer).

## Open risks (carried)

- The one net-new bit (`toolRan=True`) is of ~zero ENGINEERING value to an end user — its value is
  INTERNAL ADR-028 architecture progress + import-wall de-risking for the later mesh/solver real-tool
  stages. Commit/UI narrative frames it as ARCHITECTURE progress, NOT a user capability, NOT a coverage
  increase.
- Vacuous-green misread: a future audit could misread a green run as "geometry validation works." Mitigated
  by test names/docstrings + the no-measurement-key + disclosure assertions framing it as wiring proof.

**Closure:** R0 CHANGES_REQUIRED (1 P1 + 2 P2) → fixed + test-pinned → **R1 APPROVE**. Local commit,
`confidence: med`, no push. **Deferred next (DEFERRED, NOT cancelled):** a non-tautological check
(real CAD-kernel parse, or a check that can return valid=False on degenerate dummy data) would upgrade
this stage tier_0_dummy → tier_1_real and make surfacing watertight/manifold/volume honest.
