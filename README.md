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

1. All code lands via **PR** — no direct push to `main`.
2. **No local absolute paths** in commits, PRs, or Notion writebacks.
3. New agents/solvers require **Notion task review** before merge.
4. One Case ID per PR; completion triggers Notion writeback.
5. Architecture decisions go to the **Notion 决策库** as ADR-{nnn}.

## Naming Conventions

| Entity   | Pattern                                  |
|----------|------------------------------------------|
| Case ID  | `AI-FEA-P{phase}-{nn}`                   |
| Run ID   | `run-{YYYYMMDD}-{case_id}-{shortsha}`    |
| Branch   | `feature/{case_id}-{slug}`               |
| PR title | `[{case_id}] {Summary}`                  |

## License

MIT
