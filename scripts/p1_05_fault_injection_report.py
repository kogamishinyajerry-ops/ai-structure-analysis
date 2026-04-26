"""P1-05 Reviewer fault-injection report generator.

Runs the injection battery exported by ``tests/test_fault_injection.py`` and
writes a human-readable Markdown + JSON pair under
``runs/run-p1-05-fault-injection/``.

Consumed by the Kogami review flow — so each PR's reviewer can see the
complete injection outcome without re-reading pytest tracebacks.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from schemas.fault_injection import FAULT_RECOVERY_TABLE  # noqa: E402
from tests.test_fault_injection import collect_injection_report  # noqa: E402

OUT_DIR = REPO_ROOT / "runs" / "run-p1-05-fault-injection"


def _render_markdown(report: dict) -> str:
    out: list[str] = []
    out.append("# P1-05 — Reviewer Fault Injection Baseline")
    out.append("")
    out.append(f"> Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    out.append(
        "> Covers every ADR-004 fault_class across three canonical injection "
        "scenarios (fresh, mid-retry, budget-exhausted) — 24 total."
    )
    out.append("")
    out.append("## 1. Headline")
    out.append("")
    out.append(f"- Scenarios executed: **{report['total_scenarios']}**")
    out.append(f"- Passed: **{report['passed']}**")
    out.append(f"- Failed: **{report['failed']}**")
    out.append(f"- Pass rate: **{report['pass_rate_pct']}%**")
    out.append("")

    out.append("## 2. Recovery contract (ADR-004 mirror)")
    out.append("")
    out.append("| FaultClass | Target node | Verdict | Budget key |")
    out.append("|---|---|---|---|")
    for c in FAULT_RECOVERY_TABLE:
        out.append(
            f"| `{c.fault_class.value}` | `{c.target_node}` | "
            f"{c.expected_verdict} | `{c.budget_key}` |"
        )
    out.append("")

    out.append("## 3. Per-scenario verdicts")
    out.append("")
    out.append("| Scenario | FaultClass | Verdict | Route | Pass |")
    out.append("|---|---|---|---|---|")
    for row in report["rows"]:
        mark = "✅" if row["pass"] else "❌"
        out.append(
            f"| `{row['scenario_id']}` | `{row['fault_class']}` | "
            f"{row['verdict']} | `{row['route']}` | {mark} |"
        )
    out.append("")

    out.append("## 4. Architectural findings surfaced by this baseline")
    out.append("")
    out.append(
        "- **REFERENCE_MISMATCH architect-loop is unreachable via the Reviewer path.** "
        "`agents.router.FAULT_TO_NODE` wires it to `architect`, but the Reviewer "
        "emits `verdict=\"Needs Review\"` for REFERENCE_MISMATCH, and the Router "
        "only consults `FAULT_TO_NODE` when `verdict=\"Re-run\"`. Observed "
        "routing lands on `human_fallback`. Flagged for ADR-004 follow-up; the "
        "fault_injection recovery table and router_mapping guards in the test "
        "suite now document this gap explicitly."
    )
    out.append("")

    out.append("## 5. Traceability")
    out.append("")
    out.append(
        "- Source of truth: `schemas/fault_injection.py::FAULT_RECOVERY_TABLE`\n"
        "- Battery generator: `tests/test_fault_injection.py::collect_injection_report`\n"
        "- Drift guards: `TestAdr004Mirror`\n"
        "- Per-scenario assertions: `TestInjectionBattery`\n"
        "- Cross-cutting budget guards: `TestBudgetKeyingIsPerNode`"
    )
    out.append("")
    return "\n".join(out)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = collect_injection_report()

    json_path = OUT_DIR / "injection.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md_path = OUT_DIR / "report.md"
    md_path.write_text(_render_markdown(report), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(
        f"Summary: {report['passed']}/{report['total_scenarios']} passed "
        f"({report['pass_rate_pct']}%)."
    )
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
