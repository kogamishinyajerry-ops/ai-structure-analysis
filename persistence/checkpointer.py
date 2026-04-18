from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

# Setup dynamic path for SQLite db based on the project root structure
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_DIR = PROJECT_ROOT / "runs"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "checkpoints.sqlite"


@contextmanager
def get_checkpointer(db_path: Path | None = None) -> Iterator[SqliteSaver]:
    """Provide a configured SQLite checkpointer for LangGraph persistence.

    Usage:
        with get_checkpointer() as checkpointer:
            app = graph.compile(checkpointer=checkpointer)
    """
    target_path = db_path or DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target_path, check_same_thread=False) as conn:
        yield SqliteSaver(conn)
