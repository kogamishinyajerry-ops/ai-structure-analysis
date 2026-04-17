from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

# Setup dynamic path for SQLite db based on the project root structure
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_DIR = PROJECT_ROOT / "runs"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "checkpoints.sqlite"


def get_checkpointer() -> Generator[SqliteSaver, None, None]:
    """Provide a configured SQLite checkpointer for LangGraph persistence.

    Usage:
        with get_checkpointer() as checkpointer:
            app = graph.compile(checkpointer=checkpointer)
    """
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        yield SqliteSaver(conn)
