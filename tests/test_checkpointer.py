from __future__ import annotations

from agents.graph import compile_graph
from persistence.checkpointer import get_checkpointer


def test_get_checkpointer_supports_context_manager(tmp_path):
    db_path = tmp_path / "checkpoints.sqlite"

    with get_checkpointer(db_path) as checkpointer:
        assert checkpointer is not None

    assert db_path.exists()


def test_compile_graph_accepts_sqlite_checkpointer(tmp_path):
    db_path = tmp_path / "checkpoints.sqlite"

    with get_checkpointer(db_path) as checkpointer:
        app = compile_graph(checkpointer=checkpointer)

    assert app is not None
    assert hasattr(app, "invoke")
