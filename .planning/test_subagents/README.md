# FM-04a · Test sub-agent infrastructure

> Phase 33 B foundation. 3 specialized testing sub-agents that
> evaluate the product across functional / usability / industrial-UI
> axes. They replace the rubber-stamp tendency of single-purpose
> audit sub-agents with **codebase-grounded, evidence-citing
> evaluation**.

## Why this exists

Phase 22-32 audit sub-agents scored against rubric v1.0 by reading
the rubric and the code, then producing a number. This works for
trajectory continuity but **does not actually test the product
end-to-end**. The user's Phase 33 mandate calls for:

> "一套专门的测试子 agent，真实测评项目的功能、使用手感、可视化追踪"

The 3 sub-agents here are designed to **act like real testers**:

| Sub-agent | What it really tests |
|---|---|
| `functional_tester` | Does the end-to-end workflow actually work? Are there broken handoffs between stages? Are claims in the README borne out in the code? |
| `novice_simulator` | Could a brand-new engineer (with FEA basics but never used this product) complete a task without developer help? Where does the friction live? |
| `industrial_ui_comparator` | Does this UI look + feel + interact like Hyperworks / Abaqus / ANSYS, or does it feel like a research prototype? |

## Directory layout

```
.planning/test_subagents/
├── README.md                          (this file)
├── functional_tester.md               (protocol)
├── novice_simulator.md                (protocol)
├── industrial_ui_comparator.md        (protocol)
├── scenarios/                         (inputs for functional_tester)
│   └── (populated phase 33 C+)
├── personas/                          (inputs for novice_simulator)
│   └── (populated phase 33 C+)
└── references/                        (inputs for industrial_ui_comparator)
    └── (populated phase 33 C+)
```

## Invocation pattern

Each sub-agent is invoked via the Agent tool (in this Claude Code
session) with a prompt that:
1. Specifies the sub-agent role (one of the 3 protocols)
2. Names the codebase root (`/Users/Zhuanz/20260408 AI StructureAnalysis`)
3. Provides a SCENARIO id (functional) / PERSONA + TASK (novice) /
   SURFACE id (industrial UI)
4. Sets evidence requirements (file:line for every claim)
5. Sets output format (JSON or markdown with stated schema)
6. **Explicitly forbids reading prior FINAL / retro / blueprint
   files** (anti-priming guard F:-1)
7. Allots a token budget (≤ 8000 tokens for the report; the
   sub-agent does its own context management)

The main session spawns 3 sub-agents in parallel via a single
message with multiple tool calls, collects their reports, and
synthesizes the composite at the end.

## Anti-gaming guards (also enumerated in RUBRIC_v2.md)

- **B:-1**: scoring done by sub-agents, NOT main session
- **D:-1**: every score requires file:line evidence
- **F:-1**: sub-agents are NEVER given prior audit files
  (the briefing names the codebase + protocol + rubric only)
- **G:-1**: sub-agents must test what the codebase IS, not what
  it CLAIMS to be (no README-trust, no comment-trust)

## Triggers

- **Every phase audit cycle** (e.g., 33 C re-baseline, 33 E
  post-implementation, 34 D, ...)
- **Optional spike tests** (e.g., "run novice_simulator on the
  proposed onboarding redesign before we commit the work")
- **Regression checkpoints** (e.g., every 3 phases re-run
  functional_tester on the full scenario suite to catch
  cross-phase functional drift)

## Output retention

Sub-agent reports are saved to `.planning/audits/phase<N>_<role>_*.md`
and tracked in git. They form the evidence base for the rubric
v2.0 99-anchor claims.

## See also

- `.planning/audits/RUBRIC_v2.md` — the scoring system these
  sub-agents feed
- `.planning/FM-04A_PHASE33_TOP_TIER_FULL_FLOW_AI_FEA_BLUEPRINT.md`
  — the phase 33 mandate that motivated this infrastructure
