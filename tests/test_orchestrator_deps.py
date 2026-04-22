"""Unit tests for the dependency filter that gates dispatch."""

from __future__ import annotations

from mat.orchestrator import deps_satisfied
from mat.state.task_store import Task


def _make(task_id: str, status: str = "assigned", deps: list[str] | None = None) -> Task:
    return Task(
        task_id=task_id,
        title=task_id,
        description="",
        status=status,
        dependencies=deps or [],
    )


def test_no_dependencies_is_ready():
    t = _make("t_001")
    assert deps_satisfied(t, {"t_001": t})


def test_unmet_dependency_blocks():
    a = _make("t_001", status="in_progress")
    b = _make("t_002", deps=["t_001"])
    by_id = {"t_001": a, "t_002": b}
    assert not deps_satisfied(b, by_id)


def test_completed_dependency_unblocks():
    a = _make("t_001", status="completed")
    b = _make("t_002", deps=["t_001"])
    by_id = {"t_001": a, "t_002": b}
    assert deps_satisfied(b, by_id)


def test_chain_of_dependencies():
    a = _make("t_001", status="completed")
    b = _make("t_002", status="completed", deps=["t_001"])
    c = _make("t_003", deps=["t_002"])
    by_id = {"t_001": a, "t_002": b, "t_003": c}
    assert deps_satisfied(c, by_id)


def test_partial_chain_blocks_terminal():
    a = _make("t_001", status="completed")
    b = _make("t_002", status="in_progress", deps=["t_001"])
    c = _make("t_003", deps=["t_002"])
    by_id = {"t_001": a, "t_002": b, "t_003": c}
    assert deps_satisfied(b, by_id) is True   # b's only dep is done
    assert deps_satisfied(c, by_id) is False  # c is blocked behind b


def test_unknown_dependency_blocks():
    t = _make("t_001", deps=["t_does_not_exist"])
    assert not deps_satisfied(t, {"t_001": t})


def test_failed_dependency_blocks():
    a = _make("t_001", status="failed")
    b = _make("t_002", deps=["t_001"])
    by_id = {"t_001": a, "t_002": b}
    assert not deps_satisfied(b, by_id)
