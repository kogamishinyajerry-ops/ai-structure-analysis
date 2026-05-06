# AI-FEA Engine

> **Code SSOT** = This repository: [`kogamishinyajerry-ops/ai-structure-analysis`](https://github.com/kogamishinyajerry-ops/ai-structure-analysis)
>
> **Work-control SSOT** = Linear `Engineering` issues for scoped work, acceptance, blockers, and proof.
>
> **Architecture mirror** = Notion PRD v0.2: [AI StructureAnalysis 项目中枢](https://www.notion.so/AI-StructureAnalysis-345c68942bed80f6a092c9c2b3d3f5b9)
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

For the current AERON-backed graph adoption smoke, run without external writes:

```bash
python run_well_harness.py GS-001 --executor graph --no-notion-sync
```

This mode exercises the LangGraph path and AERON CalculiX backend boundary, but
it is still replay/dummy execution. Treat its output as an integration smoke and
project_state bundle, not as GS101 or signed validation evidence.

See [`docs/well_harness_architecture.md`](docs/well_harness_architecture.md).

## Development Rules

> **Canonical ruleset:** [ADR-011](docs/adr/ADR-011-pivot-claude-code-takeover.md),
> [ADR-012](docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md), and
> [ADR-013](docs/adr/ADR-013-branch-protection-enforcement.md). This section is
> only a quick-reference; if it drifts from those ADRs, the ADRs win.

**Truth and roles**

1. GitHub/repo is the code truth. All code and governance changes land by PR;
   never direct-push to `main`.
2. Linear `Engineering` issues are the work-control truth: scope, acceptance,
   blockers, evidence, proof comments, and state live there.
3. Codex is the primary implementation agent. Local Claude Opus 4.7 is the
   reviewer/auditor, not the default executor or repo owner.
4. Notion is an architecture/control mirror after repo and Linear truth settle.
   Do not make Notion-first truth changes.

**Gates and traceability**

5. Use the PR template. The `Self-pass-rate` claim must come from
   `python3 scripts/compute_calibration_cap.py --human`, not intuition.
6. Current required checks on `main`: `lint-and-test (3.11)`,
   `calibration-cap-check`, `trailer-check`, and `golden-samples-validation`.
7. Linear-controlled commits carry `Execution-by: codex-primary`,
   `Codex-verified: <claim-id>@<sha>`, `Reviewed-by: claude-opus47 APPROVE ...`
   when review is required, and `Linear-Issue: ENG-<id>`.
8. External writes are gated: show dry-run payloads before Linear comments/state
   transitions, GitHub PR comments/close/merge actions, branch-protection
   mutations, or Notion updates.
9. Do not commit local absolute paths, secrets, raw env dumps, or machine-only
   credentials in commits, PRs, Linear proof comments, or Notion mirrors.

**Safety floors**

10. Treat `golden_samples/**` as read-only unless a signed validation issue
   explicitly authorizes a change. Unsigned smoke/demo fixtures are not signed
   validation samples.
11. No golden-standard reference means `insufficient_evidence`, not regression
    evidence. `scripts/validate_golden_samples.py` enforces signed `GS-###`
    registry shape.
12. CalculiX is the numerical truth source unless a new ADR and gate approve a
    different solver truth source.
13. Keep decisions reversible: architecture changes go through ADRs, schema
    changes are schema-first, and the four-layer import direction in ADR-011
    remains binding.

## Naming Conventions

| Entity   | Pattern                                  |
|----------|------------------------------------------|
| Case ID  | `AI-FEA-P{phase}-{nn}`                   |
| Run ID   | `run-{YYYYMMDD}-{case_id}-{shortsha}`    |
| Branch   | `feature/{case_id}-{slug}`               |
| PR title | `[{case_id}] {Summary}`                  |

## License

MIT
