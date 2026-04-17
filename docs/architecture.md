# AI-FEA Architecture

> **Code SSOT**: This repository — [`ai-structure-analysis`](https://github.com/kogamishinyajerry-ops/ai-structure-analysis)
>
> **Process SSOT**: Notion PRD v0.2 — [AI StructureAnalysis 项目中枢](https://www.notion.so/AI-StructureAnalysis-345c68942bed80f6a092c9c2b3d3f5b9)

## High-Level Pipeline

```
User Spec ──► Architect Agent ──► SimPlan
                                     │
              ┌──────────────────────┘
              ▼
         Geometry Agent ──► STEP
              │
              ▼
          Mesh Agent ──► .inp mesh
              │
              ▼
         Solver Agent ──► CalculiX ──► .frd
              │
              ▼
        Reviewer Agent ──► Accept / Re-run?
              │                    │
              │ (re-run)           │ (accept)
              └────────────────────┤
                                   ▼
                            Viz Agent ──► Report + VTP
                                   │
                                   ▼
                            Notion Writeback (well_harness)
```

## Agent Layer (`agents/`)

| Agent       | File            | Upstream      | Downstream    | Filled in |
|-------------|-----------------|---------------|---------------|-----------|
| Architect   | `architect.py`  | User spec     | SimPlan       | P0-04     |
| Geometry    | `geometry.py`   | SimPlan       | STEP file     | P0-05     |
| Mesh        | `mesh.py`       | STEP          | .inp mesh     | P0-06     |
| Solver      | `solver.py`     | .inp + SimPlan| .frd result   | P0-07     |
| Reviewer    | `reviewer.py`   | .frd + refs   | Verdict       | P0-08     |
| Viz         | `viz.py`        | .frd + verdict| Report + VTP  | P0-09     |
| Graph       | `graph.py`      | —             | LangGraph DAG | P0-02     |

## Tool Drivers (`tools/`)

| Driver            | External Dep    | Filled in |
|-------------------|-----------------|-----------|
| `freecad_driver`  | FreeCAD ≥ 0.21  | P0-05     |
| `gmsh_driver`     | Gmsh ≥ 4.11     | P0-06     |
| `calculix_driver` | CalculiX 2.21   | P0-07     |
| `frd_parser`      | —               | P0-09     |

## Schemas (`schemas/`)

- `SimPlan` — the master contract (Pydantic v2 model).
- Additional types (SimState, RunResult) to be added as agents are filled.

## Quality Gates (`checkers/`)

- `jacobian.py` — mesh quality (scaled Jacobian, aspect ratio).
- `geometry_checker.py` — watertight / manifold validation.

## Output (`reporters/`)

- `markdown.py` — structured Markdown analysis report.
- `vtp.py` — VTK PolyData export for ParaView.

## Runtime Artifacts (`runs/`)

Each run produces a timestamped directory under `runs/`:
```
runs/run-20260417-AI-FEA-P0-10-abc1234/
├── sim_plan.json
├── geometry.step
├── mesh.inp
├── solve.frd
├── report.md
└── result.vtp
```

Large artifacts are gitignored; CI artifacts are the canonical archive.

## Control Plane Integration

The existing `backend/app/well_harness/` module handles:
- Notion task/session/decision database sync.
- `project_state` persistence.
- Approval reconciliation.

See [well_harness_architecture.md](well_harness_architecture.md) for details.
