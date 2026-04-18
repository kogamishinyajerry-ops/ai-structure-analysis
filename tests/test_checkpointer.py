from __future__ import annotations

from typing import TypedDict
from uuid import uuid4

from langgraph.graph import START, StateGraph
from langgraph.types import Command, interrupt

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


class ReviewState(TypedDict):
    question: str
    decision: str | None


def _review_node(state: ReviewState) -> dict[str, str]:
    decision = interrupt({"question": state["question"]})
    return {"decision": decision}


def test_sqlite_checkpointer_resumes_after_interrupt(tmp_path):
    db_path = tmp_path / "resume.sqlite"
    config = {"configurable": {"thread_id": str(uuid4())}}

    builder = StateGraph(ReviewState)
    builder.add_node("review", _review_node)
    builder.add_edge(START, "review")

    with get_checkpointer(db_path) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        first_pass = list(graph.stream({"question": "Ship this run?"}, config))

    assert "__interrupt__" in first_pass[0]

    with get_checkpointer(db_path) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        resumed = list(graph.stream(Command(resume="approved"), config))

    assert resumed == [{"review": {"decision": "approved"}}]
