"""well-harness public exports.

Keep imports lazy so tests can load lightweight modules without pulling in
unrelated optional dependencies from the wider backend package tree.
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "CalculixExecutor",
    "ControlPlaneSyncBuilder",
    "ControlPlaneSyncPlan",
    "GoldenSampleKnowledgeStore",
    "NotionApprovalSyncResult",
    "NotionRunRegistrar",
    "NotionSyncConfig",
    "NotionSyncResult",
    "ProjectStateStore",
    "ReplayExecutor",
    "WellHarnessRunner",
]

_EXPORTS = {
    "CalculixExecutor": (".executors", "CalculixExecutor"),
    "ControlPlaneSyncBuilder": (".control_plane", "ControlPlaneSyncBuilder"),
    "ControlPlaneSyncPlan": (".control_plane", "ControlPlaneSyncPlan"),
    "GoldenSampleKnowledgeStore": (".knowledge_store", "GoldenSampleKnowledgeStore"),
    "NotionApprovalSyncResult": (".notion_sync", "NotionApprovalSyncResult"),
    "NotionRunRegistrar": (".notion_sync", "NotionRunRegistrar"),
    "NotionSyncConfig": (".notion_sync", "NotionSyncConfig"),
    "NotionSyncResult": (".notion_sync", "NotionSyncResult"),
    "ProjectStateStore": (".project_state", "ProjectStateStore"),
    "ReplayExecutor": (".executors", "ReplayExecutor"),
    "WellHarnessRunner": (".task_runner", "WellHarnessRunner"),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name, __name__)
    return getattr(module, attr_name)
