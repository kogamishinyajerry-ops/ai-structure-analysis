<!--
ADR-013 PR template. Sections marked REQUIRED are validated by CI.
The "Self-pass-rate" section is mechanically checked against the formula
in scripts/compute_calibration_cap.py — claims above the current ceiling
fail CI. Fill it by running:

    python3 scripts/compute_calibration_cap.py --human

and copying the ceiling integer (no `%`) into the section below.
-->

## Summary

<!-- 1-3 bullets: what changes, why now. -->

-
-

## Self-pass-rate (mechanically derived) <!-- REQUIRED — ADR-013 -->

<!--
Replace `<N>` with the integer printed by:
    python3 scripts/compute_calibration_cap.py
The CI calibration-cap-check job will fail if your claim exceeds the
current ceiling. Do not type a number from intuition; ADR-012 forbids it.
-->

**<N>%** · derived from `reports/calibration_state.json` last-5 R1 outcomes.

Codex pre-merge gate (per ADR-012):

- [ ] BLOCKING (ceiling 30) — must reach Codex R1=APPROVE before merge
- [ ] MANDATORY non-blocking (ceiling 50) — Codex R1 required, can iterate
- [ ] RECOMMENDED (ceiling 80) — Codex review strongly suggested
- [ ] OPTIONAL (ceiling 95) — honor system, Codex at author discretion

ADR-011 §T2 mandatory triggers (M1-M5) override the ceiling-derived gate
when applicable. Tick any that fire:

- [ ] M1: governance text added/changed (ADRs, FailurePatterns, RETROs)
- [ ] M2: sign-or-direction math (revert direction, BC orientation, etc.)
- [ ] M3: HF compliance claim (HF1-HF6 path/zone/process assertions)
- [ ] M4: governance→enforcement translation (script/CI/hook implementing a rule)
- [ ] M5: PR opened while ceiling ≤ 50%

## Test plan <!-- REQUIRED -->

- [ ] `pytest tests/`
- [ ] `ruff check .` and `ruff format --check .`
- [ ] *(if applicable)* hot-smoke / hand-tested in a real workflow
- [ ] Codex pre-merge review *(if BLOCKING/MANDATORY or any M1-M5 triggered)*

## Out of scope

<!-- What this PR explicitly does NOT do, to prevent scope creep reviews. -->

-

## Related

- ADR-XXX, FP-XXX, DEC-XXX, AR-XXX as relevant
