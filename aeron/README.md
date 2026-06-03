# AERON — status note (ADR-027, 2026-06-03)

**AERON is a live, tested FEABackend seam — NOT orphaned, NOT the active milestone, NOT
signed-validated.** This note exists because an earlier deep-takeover draft mis-stated AERON as
"never imported" (a scoped-grep error caught by Codex ADR-027 R0 P1).

## What AERON is

- `aeron/protocols/` — the `FEABackend` protocol contract (`fea_backend.py`).
- `aeron/drivers/calculix_backend.py` — a *narrow wrapper around the existing CalculiX path*
  (`CalculiXFEABackend`, over the real `tools.calculix_driver`).
- `aeron/drivers/openradioss_backend.py` — the intended ballistic/explicit-dynamics backend
  (`OpenRadiossFEABackend`, FM-04a P4).

## Verified status (import/use audit, 2026-06-03)

- Imported by `agents/solver.py` (`from aeron.protocols import …`; `from aeron.drivers import
  CalculiXFEABackend`; instantiated).
- Exercised by ≥5 test files: `test_aeron_calculix_backend.py`,
  `test_aeron_fea_backend_protocol.py`, `test_openradioss_backend.py`, `test_solver_agent.py`,
  `test_simulation_sample_manifest.py` (all green in the CI pytest job).
- Shipped as a package: `pyproject.toml` `"aeron*"`; egg-info `top_level.txt` lists `aeron`.
- Reachable from the live backend via the `backend/app/workbench` facade — the only sanctioned
  call site that may import `agents.*`.

## What is dead (vs the code)

- The **ROADMAP FM-02 "AERON-Backed Solve Path" milestone framing** — superseded by ADR-026 /
  ADR-027 (`.planning/ROADMAP.md` is marked SUPERSEDED).
- The unmerged remote branches `codex/ENG-35-aeron-calculix-backend`,
  `codex/ENG-36-aeron-solver-backend-wiring`, `codex/ENG-38-aeron-well-harness-graph`.
  (`codex/ENG-37-aeron-graph-provenance` is already merged.)

## Disposition (owner decision, ADR-027, 2026-06-03)

**AERON is NOT pursued further — focus is on the AI-FEA core.** The code stays exactly as-is (a
tested, secondary seam). It is **not** wired into the live workbench solve flow and is **not** a
v2 item.

### TICKET (housekeeping, not yet done — outward git action left to the owner)

Prune the three dead remote branches:

```
git push origin --delete codex/ENG-35-aeron-calculix-backend \
                         codex/ENG-36-aeron-solver-backend-wiring \
                         codex/ENG-38-aeron-well-harness-graph
```

Reversible: the AERON code already lives on the FM-04a branch; these branches carry no unmerged
code worth keeping.
