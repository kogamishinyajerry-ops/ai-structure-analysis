# AI-FEA Engine

> **Code SSOT** = This repository: [`kogamishinyajerry-ops/ai-structure-analysis`](https://github.com/kogamishinyajerry-ops/ai-structure-analysis)
>
> **Process SSOT** = Notion PRD v0.2: [AI StructureAnalysis 项目中枢](https://www.notion.so/AI-StructureAnalysis-345c68942bed80f6a092c9c2b3d3f5b9)
>
> **Runtime SSOT** = `runs/` directory + CI artifacts

AI-driven Finite Element Analysis engine with multi-agent orchestration.
Solves linear-static, modal, and thermal-structural problems end-to-end:
from natural-language spec → parametric CAD → adaptive mesh → CalculiX solve → validated report.

## Architecture

```
User Spec ─► Architect ─► Geometry ─► Mesh ─► Solver ─► Reviewer ─► Viz
                                                            │
                                                    (re-run if needed)
```

Agents are orchestrated via [LangGraph](https://github.com/langchain-ai/langgraph).
See [`docs/architecture.md`](docs/architecture.md) for the full design.

## Project Structure

```
ai-structure-analysis/
├── agents/            # LangGraph agent nodes (architect → viz)
├── tools/             # External tool drivers (FreeCAD, Gmsh, CalculiX, FRD parser)
├── schemas/           # Pydantic v2 models (SimPlan, SimState, RunResult)
├── templates/         # CalculiX .inp Jinja2 templates
├── checkers/          # Pre-solve quality gates (Jacobian, geometry)
├── reporters/         # Output generators (Markdown, VTP)
├── runs/              # Runtime artifacts (gitignored; CI is canonical archive)
├── tests/             # pytest suite
├── docs/              # Architecture docs (→ Notion PRD)
├── backend/           # Legacy well_harness + API modules
│   └── app/
│       └── well_harness/  # Notion sync, task runner, control plane
├── golden_samples/    # Reference benchmark cases (GS-001 ~ GS-003)
├── config/            # Control plane YAML (Notion data-source bindings)
├── .github/workflows/ # CI: ruff + pytest
├── pyproject.toml     # Python 3.11+, ruff, dev/agents/solvers/viz extras
└── .pre-commit-config.yaml
```

## Quick Start

```bash
# Clone
git clone https://github.com/kogamishinyajerry-ops/ai-structure-analysis
cd ai-structure-analysis

# Install (dev)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Lint
ruff check .
ruff format --check .

# Test
pytest tests/ -v
```

## Well Harness (Legacy Automation)

The `backend/app/well_harness/` module provides the existing golden-sample
automation loop with Notion task/session sync:

```bash
export NOTION_API_KEY="your-integration-token"
python run_well_harness.py GS-001 GS-002 GS-003
```

See [`docs/well_harness_architecture.md`](docs/well_harness_architecture.md).

## Development Rules

> **Canonical ruleset:** [ADR-011 §9 Golden Rules](docs/adr/ADR-011-pivot-claude-code-takeover.md#9-golden-rules) and [§Hard-Floor Rules HF1-HF5](docs/adr/ADR-011-pivot-claude-code-takeover.md#hard-floor-rules-hf1--hf5).
> The bullets below are a quick-reference; when this README and ADR-011 conflict, **ADR-011 wins** and a sync PR is opened.

**Workflow & boundaries**

1. All code lands via **PR** — no direct push to `main`. (Golden Rule #1 + branch protection per ADR-013.)
2. **No local absolute paths** in commits, PRs, or Notion writebacks. Enforced by `scripts/hf1_path_guard.py` pre-commit (FF-06).
3. **HF1 hard-stop zone** (`agents/solver.py`, `agents/router.py`, `agents/geometry.py`, `tools/calculix_driver.py`, `schemas/sim_state.py`, `tests/test_toolchain_probes.py`, `Dockerfile`, `Makefile`, `golden_samples/**`, `scripts/hf1_path_guard.py`, `.github/workflows/**`) — pre-commit blocks staged diffs unless `HF1_GUARD_OVERRIDE='<reason>'` is set. See ADR-011 §Hard-Floor Rules.
4. **PR-protected zone** (`docs/adr/`, `docs/governance/`, `docs/failure_patterns/`) — regular PR + mandatory Codex M1 trigger. Branch protection per ADR-013.

**Process & traceability**

5. Each commit carries `Execution-by:` and (when claims are made) `Codex-verified:` trailers — see ADR-011 §Commit Trailer Convention. Subagent work adds `· Subagent: <id>`.
6. **One Case ID per PR**; completion triggers Notion writeback. Case ID format: `AI-FEA-P{phase}-{nn}` or `AI-FEA-S{sprint}-{nn}` for sub-sprint work.
7. **Architecture decisions** land as `docs/adr/ADR-{nnn}-{slug}.md` AND mirror to Notion 决策库. Golden Rule #3.
8. **Handoffs cannot bypass Notion** — phase-to-phase transitions require a clickable Notion Handoff page. Golden Rule #4.

**Numerical & data integrity**

9. **CalculiX is the only numerical truth source.** Any "equivalent solver" claim requires ADR + Gate. Golden Rule #2.
10. **No golden-standard → no test.** Samples without GS reference get `insufficient_evidence` and don't enter the regression lane. Golden Rule #5; FF-08 will mechanize this.
11. **Schema-first** — Pydantic v2 strict validation per `schemas/`; schema changes go through ADR before code. Golden Rule #7.
12. **Four-layer import boundary** — Control / Execution / Knowledge / Evaluation; imports flow one-way: Control reads all, Execution depends on Knowledge only, Evaluation is independent of Execution. Golden Rule #9.

**Calibration & reversibility**

13. **Self-pass-rate is mechanical, not honor-system.** T1 reads the ceiling from `python3 scripts/compute_calibration_cap.py`; ADR-012 forbids typing a number from intuition. PR template (`.github/PULL_REQUEST_TEMPLATE.md`) prefills the field; CI `calibration-cap-check` validates the claim.
14. **Every decision has a documented rollback path** — see each ADR's §Rollback. Golden Rule #8.

## Naming Conventions

| Entity   | Pattern                                  |
|----------|------------------------------------------|
| Case ID  | `AI-FEA-P{phase}-{nn}`                   |
| Run ID   | `run-{YYYYMMDD}-{case_id}-{shortsha}`    |
| Branch   | `feature/{case_id}-{slug}`               |
| PR title | `[{case_id}] {Summary}`                  |

## License

MIT
