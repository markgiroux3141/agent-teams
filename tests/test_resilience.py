"""M4 acceptance: a mixed dispatch round with a crashing teammate, a
hanging teammate, and a normal teammate should leave the orchestrator in a
coherent state — failed tasks marked failed, the normal task completed, a
run_summary.json correctly reflecting the outcome."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from mat.config import TeamConfig, LeadConfig, TeamSettings, TeammateConfig
from mat.logging import EventLogger
from mat.orchestrator import Orchestrator
from mat.state.message_bus import MessageBus
from mat.state.task_store import TaskStore


class FakeTeammate:
    """Programmable fake. `behavior` controls what dispatch() does."""

    def __init__(self, name: str, behavior: str = "normal",
                 complete_task_id: str | None = None,
                 task_store: TaskStore | None = None,
                 hang_seconds: float = 999.0) -> None:
        self.name = name
        self.behavior = behavior
        self.complete_task_id = complete_task_id
        self.task_store = task_store
        self.hang_seconds = hang_seconds
        self.last_status = "ready"
        self.dispatch_count = 0

    async def dispatch(self, prompt: str) -> str:
        self.dispatch_count += 1
        if self.behavior == "normal":
            if self.complete_task_id and self.task_store:
                self.task_store.update_status(
                    self.complete_task_id, "completed", result_ref=f"{self.name}.md",
                )
            return "ok"
        if self.behavior == "crash":
            raise RuntimeError(f"{self.name} crashed mid-dispatch")
        if self.behavior == "hang":
            await asyncio.sleep(self.hang_seconds)
            return "never"
        raise ValueError(f"unknown behavior: {self.behavior}")


def _make_orch(tmp_path: Path, timeout: float = 60.0) -> tuple[Orchestrator, EventLogger]:
    team = TeamConfig(
        name="resilience",
        lead=LeadConfig(),
        teammates=[
            TeammateConfig(name="alice", model="m", description=""),
            TeammateConfig(name="bob", model="m", description=""),
            TeammateConfig(name="carol", model="m", description=""),
        ],
        settings=TeamSettings(stall_timeout_seconds=timeout),
    )
    orch = Orchestrator(team, goal="mixed", run_dir=tmp_path)
    logger = EventLogger(tmp_path / "trace.jsonl")
    return orch, logger


def _load_trace(tmp_path: Path) -> list[dict]:
    return [json.loads(l) for l in (tmp_path / "trace.jsonl").open() if l.strip()]


def test_crash_marks_task_failed(tmp_path):
    orch, logger = _make_orch(tmp_path)
    store = TaskStore(tmp_path / "tasks.jsonl")
    bus = MessageBus(tmp_path / "messages")

    tid = store.create_task("do X", "")
    store.assign_task(tid, "alice")
    ready = [t for t in store.list_tasks() if t.status == "assigned"]

    teammates = {"alice": FakeTeammate("alice", behavior="crash")}

    asyncio.run(
        orch._dispatch_round(
            ready_tasks=ready, pending_replies=[], nudges=[],
            teammates=teammates, task_store=store, message_bus=bus,
            event_logger=logger, timeout=5.0,
        )
    )

    t = store.get_task(tid)
    assert t.status == "failed"
    assert "crashed" in (t.note or "")

    events = _load_trace(tmp_path)
    assert any(e["event"] == "dispatch_error" and e["agent"] == "alice" for e in events)


def test_timeout_marks_task_failed(tmp_path):
    orch, logger = _make_orch(tmp_path, timeout=0.2)
    store = TaskStore(tmp_path / "tasks.jsonl")
    bus = MessageBus(tmp_path / "messages")

    tid = store.create_task("do Y", "")
    store.assign_task(tid, "bob")
    ready = [t for t in store.list_tasks() if t.status == "assigned"]

    teammates = {"bob": FakeTeammate("bob", behavior="hang", hang_seconds=5.0)}

    asyncio.run(
        orch._dispatch_round(
            ready_tasks=ready, pending_replies=[], nudges=[],
            teammates=teammates, task_store=store, message_bus=bus,
            event_logger=logger, timeout=0.2,
        )
    )

    t = store.get_task(tid)
    assert t.status == "failed"
    assert "stall_timeout" in (t.note or "")

    events = _load_trace(tmp_path)
    assert any(e["event"] == "dispatch_timeout" and e["task_id"] == tid for e in events)


def test_mixed_round_crash_hang_normal(tmp_path):
    """One round, three teammates, three outcomes. Orchestrator survives."""
    orch, logger = _make_orch(tmp_path, timeout=0.2)
    store = TaskStore(tmp_path / "tasks.jsonl")
    bus = MessageBus(tmp_path / "messages")

    t_alice = store.create_task("alice task", "")
    t_bob = store.create_task("bob task", "")
    t_carol = store.create_task("carol task", "")
    store.assign_task(t_alice, "alice")
    store.assign_task(t_bob, "bob")
    store.assign_task(t_carol, "carol")

    teammates = {
        "alice": FakeTeammate("alice", behavior="crash"),
        "bob": FakeTeammate("bob", behavior="hang", hang_seconds=5.0),
        "carol": FakeTeammate(
            "carol", behavior="normal",
            complete_task_id=t_carol, task_store=store,
        ),
    }

    ready = [t for t in store.list_tasks() if t.status == "assigned"]
    asyncio.run(
        orch._dispatch_round(
            ready_tasks=ready, pending_replies=[], nudges=[],
            teammates=teammates, task_store=store, message_bus=bus,
            event_logger=logger, timeout=0.2,
        )
    )

    assert store.get_task(t_alice).status == "failed"
    assert store.get_task(t_bob).status == "failed"
    assert store.get_task(t_carol).status == "completed"

    # Every teammate dispatched exactly once; orchestrator didn't re-run the survivor.
    assert teammates["alice"].dispatch_count == 1
    assert teammates["bob"].dispatch_count == 1
    assert teammates["carol"].dispatch_count == 1


def test_stall_nudge_fires_once_per_task(tmp_path):
    orch, _ = _make_orch(tmp_path)
    store = TaskStore(tmp_path / "tasks.jsonl")

    tid = store.create_task("stuck", "")
    store.assign_task(tid, "alice")
    store.update_status(tid, "in_progress")

    teammates = {"alice": FakeTeammate("alice")}

    first = orch._find_stall_nudges(store, teammates)
    assert [t.task_id for t in first] == [tid]

    # Mark as nudged (what _dispatch_round would do) and verify no re-nudge.
    orch._nudged_tasks.add(tid)
    second = orch._find_stall_nudges(store, teammates)
    assert second == []


def test_stall_nudge_skipped_when_terminal(tmp_path):
    orch, _ = _make_orch(tmp_path)
    store = TaskStore(tmp_path / "tasks.jsonl")

    tid = store.create_task("done", "")
    store.assign_task(tid, "alice")
    store.update_status(tid, "completed", result_ref="x.md")

    teammates = {"alice": FakeTeammate("alice")}
    assert orch._find_stall_nudges(store, teammates) == []


def test_graceful_shutdown_writes_partial_summary(tmp_path, monkeypatch):
    """KeyboardInterrupt / CancelledError inside the main loop must: (a) not
    escape run(), (b) write run_summary.json with interrupted=true, (c) write
    OUTPUT.md.partial since nothing was finalized."""

    class FakeLead:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def start(self):
            raise asyncio.CancelledError()
        async def continue_(self, prompt):
            return ""

    class FakeTM:
        last_status = "ready"
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def dispatch(self, prompt): return ""

    monkeypatch.setattr("mat.orchestrator.TeamLead", FakeLead)
    monkeypatch.setattr("mat.orchestrator.Teammate", FakeTM)

    team = TeamConfig(
        name="t", lead=LeadConfig(),
        teammates=[TeammateConfig(name="alice", model="m", description="")],
        settings=TeamSettings(),
    )
    orch = Orchestrator(team, goal="g", run_dir=tmp_path)
    asyncio.run(orch.run())

    summary_path = tmp_path / "run_summary.json"
    assert summary_path.exists()
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    assert data["interrupted"] is True
    assert data["finalized"] is False
    assert (tmp_path / "workspace" / "OUTPUT.md.partial").exists()


def test_run_summary_after_mixed_round(tmp_path):
    """After a realistic mixed round, _write_summary produces a JSON file
    with the expected task counts and a cost section."""
    orch, logger = _make_orch(tmp_path, timeout=0.2)
    store = TaskStore(tmp_path / "tasks.jsonl")
    bus = MessageBus(tmp_path / "messages")

    t_alice = store.create_task("a", "")
    t_bob = store.create_task("b", "")
    store.assign_task(t_alice, "alice")
    store.assign_task(t_bob, "bob")

    teammates = {
        "alice": FakeTeammate("alice", behavior="crash"),
        "bob": FakeTeammate(
            "bob", behavior="normal",
            complete_task_id=t_bob, task_store=store,
        ),
    }
    ready = [t for t in store.list_tasks() if t.status == "assigned"]
    asyncio.run(
        orch._dispatch_round(
            ready_tasks=ready, pending_replies=[], nudges=[],
            teammates=teammates, task_store=store, message_bus=bus,
            event_logger=logger, timeout=0.2,
        )
    )

    # Simulate end-of-run recording of a fake result event so the ledger has data.
    logger.log("teammate_result", agent="bob", cost_usd=0.01, input_tokens=100,
               output_tokens=50, cache_read=0, cache_write=0)

    orch._write_summary(logger, store)
    summary_path = tmp_path / "run_summary.json"
    assert summary_path.exists()
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    assert data["team"] == "resilience"
    assert data["interrupted"] is False
    assert data["finalized"] is False
    assert data["task_counts_by_status"].get("failed") == 1
    assert data["task_counts_by_status"].get("completed") == 1
    assert data["cost"]["per_agent"]["bob"]["cost_usd"] == pytest.approx(0.01)
    assert data["cost"]["total"]["cost_usd"] == pytest.approx(0.01)
