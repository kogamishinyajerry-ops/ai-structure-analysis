"""Reviewer / Corrector Agent — validates results and triggers re-runs.

Responsibilities:
  - Compare solver output against reference values or analytical bounds.
  - Flag deviations exceeding thresholds.
  - Decide: Accept / Accept-with-Note / Re-run (with corrective hints).
  - Emit verdict into state for downstream reporting and Notion writeback.

This module is a stub (AI-FEA-P0-01).  Logic will be filled in P0-08.
"""

from __future__ import annotations

from typing import Any


def run(state: dict[str, Any]) -> dict[str, Any]:
    """Reviewer agent entrypoint (LangGraph node signature)."""
    raise NotImplementedError("Reviewer agent not yet implemented — see AI-FEA-P0-08")
