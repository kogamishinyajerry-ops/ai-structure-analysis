"""Workbench facade layer (ADR-015).

This package is the only call site that may import from `agents.*` outside
the agent layer itself. See `docs/adr/ADR-015-workbench-agent-rpc-boundary.md`.
"""
