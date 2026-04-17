"""Architect Agent — produces a SimPlan from a natural-language spec.

Responsibilities:
  - Parse user intent (geometry, loads, BCs, analysis type).
  - Select appropriate solver backend and element strategy.
  - Emit a validated ``SimPlan`` for downstream agents.

This module is a stub (AI-FEA-P0-01).  Logic will be filled in P0-04.
"""

from __future__ import annotations

from typing import Any


def run(state: dict[str, Any]) -> dict[str, Any]:
    """Architect agent entrypoint (LangGraph node signature)."""
    raise NotImplementedError("Architect agent not yet implemented — see AI-FEA-P0-04")
