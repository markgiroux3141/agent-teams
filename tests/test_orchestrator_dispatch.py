"""Tests for _dispatch_round: reply-only dispatch, combined task+mail prompt,
and back-pressure flagging in the status summary. Fake teammates so we don't
touch the SDK."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from mat.config import TeamConfig, LeadConfig, TeamSettings, TeammateConfig
from mat.logging import EventLogger
from mat.orchestrator import Orchestrator
from mat.state.message_bus import MessageBus
from mat.state.task_store import TaskStore


@dataclass
class FakeTeammate:
    name: str
    last_status: str = "ready"
    prompts: list[str] = field(default_factory=list)
    on_dispatch: callable = None  # type: ignore[assignment]

    async def dispatch(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.on_dispatch is not None:
            self.on_dispatch(prompt)
        return "ok"


def _make_orch(tmp_path: Path) -> tuple[Orchestrator, EventLogger]:
    team = TeamConfig(
        name="t",
        lead=LeadConfig(),
        teammates=[
            TeammateConfig(name="writer", model="m", description=""),
            TeammateConfig(name="researcher", model="m", description=""),
        ],
        settings=TeamSettings(unread_backpressure_threshold=2),
    )
    orch = Orchestrator(team, goal="g", run_dir=tmp_path)
    logger = EventLogger(tmp_path / "trace.jsonl")
    return orch, logger


def test_reply_only_dispatch_wakes_agent_with_mail(tmp_path):
    orch, logger = _make_orch(tmp_path)
    store = TaskStore(tmp_path / "tasks.jsonl")
    bus = MessageBus(tmp_path / "messages")
    teammates = {"writer": FakeTeammate("writer"), "researcher": FakeTeammate("researcher")}

    bus.send(to="researcher", sender="writer", content="what stat?")

    asyncio.run(
        orch._dispatch_round(
            ready_tasks=[],
            pending_replies=["researcher"],
            nudges=[],
            teammates=teammates,
            task_store=store,
            message_bus=bus,
            event_logger=logger,
            timeout=60.0,
        )
    )

    assert len(teammates["researcher"].prompts) == 1
    assert "new message" in teammates["researcher"].prompts[0].lower()
    assert "mcp__coord__read_messages" in teammates["researcher"].prompts[0]
    assert teammates["writer"].prompts == []


def test_combined_prompt_when_agent_has_task_and_mail(tmp_path):
    orch, logger = _make_orch(tmp_path)
    store = TaskStore(tmp_path / "tasks.jsonl")
    bus = MessageBus(tmp_path / "messages")
    teammates = {"writer": FakeTeammate("writer"), "researcher": FakeTeammate("researcher")}

    # Writer has mail AND a ready task.
    bus.send(to="writer", sender="researcher", content="here's the stat: 3.2x")
    tid = store.create_task("Write brief", "using researcher's findings")
    store.assign_task(tid, "writer")
    ready = [t for t in store.list_tasks() if t.task_id == tid]

    asyncio.run(
        orch._dispatch_round(
            ready_tasks=ready,
            pending_replies=[],  # already consumed by the task-agent branch
            nudges=[],
            teammates=teammates,
            task_store=store,
            message_bus=bus,
            event_logger=logger,
            timeout=60.0,
        )
    )

    # Exactly one dispatch, containing both the task body and the inbox note.
    assert len(teammates["writer"].prompts) == 1
    prompt = teammates["writer"].prompts[0]
    assert tid in prompt
    assert "unread messages" in prompt.lower()
    assert "mcp__coord__read_messages" in prompt


def test_pause_and_resume_via_message_round_trip(tmp_path):
    """Simulate: writer pauses mid-task by sending a question. Researcher is
    auto-dispatched to reply. Next round, writer is auto-woken and can finish.

    We drive two rounds manually to make the state transitions explicit."""
    orch, logger = _make_orch(tmp_path)
    store = TaskStore(tmp_path / "tasks.jsonl")
    bus = MessageBus(tmp_path / "messages", cc_agent="lead")

    writer = FakeTeammate("writer")
    researcher = FakeTeammate("researcher")
    teammates = {"writer": writer, "researcher": researcher}

    tid = store.create_task("Write brief", "needs a stat you don't have")
    store.assign_task(tid, "writer")

    # Round 1: writer is dispatched with the task. On dispatch, writer "decides"
    # to ask researcher a question instead of completing.
    def writer_asks(_prompt: str) -> None:
        bus.send(to="researcher", sender="writer", content="what stat should I cite?")

    writer.on_dispatch = writer_asks

    ready = [t for t in store.list_tasks() if t.status == "assigned"]
    asyncio.run(
        orch._dispatch_round(
            ready_tasks=ready,
            pending_replies=[],
            nudges=[],
            teammates=teammates,
            task_store=store,
            message_bus=bus,
            event_logger=logger,
            timeout=60.0,
        )
    )

    # Task is now in_progress (writer didn't call update_task), and researcher
    # has one unread message, writer has zero.
    assert store.get_task(tid).status == "in_progress"
    assert bus.unread_count("researcher") == 1
    assert bus.unread_count("writer") == 0
    # Lead got a CC.
    assert bus.unread_count("lead") == 1

    # Round 2: researcher has mail, no task → reply dispatch. On dispatch,
    # researcher polls its inbox (consuming the message) and sends a reply.
    def researcher_replies(_prompt: str) -> None:
        bus.poll("researcher")  # consume
        bus.send(to="writer", sender="researcher", content="cite 3.2x")

    researcher.on_dispatch = researcher_replies

    # Recompute pending dispatches for round 2 — task still in_progress (not
    # "assigned"), so ready_tasks is empty; researcher has mail.
    ready = [t for t in store.list_tasks() if t.status == "assigned"]
    pending_replies = [n for n in teammates if bus.unread_count(n) > 0]
    assert ready == []
    assert pending_replies == ["researcher"]

    asyncio.run(
        orch._dispatch_round(
            ready_tasks=ready,
            pending_replies=pending_replies,
            nudges=[],
            teammates=teammates,
            task_store=store,
            message_bus=bus,
            event_logger=logger,
            timeout=60.0,
        )
    )

    # Writer now has a reply waiting.
    assert bus.unread_count("writer") == 1
    assert len(researcher.prompts) == 1
    # Writer was NOT re-dispatched yet — that would be round 3's pending_replies.


def test_backpressure_flag_in_status_summary(tmp_path):
    orch, _ = _make_orch(tmp_path)  # threshold = 2
    store = TaskStore(tmp_path / "tasks.jsonl")
    bus = MessageBus(tmp_path / "messages")
    teammates = {"writer": FakeTeammate("writer"), "researcher": FakeTeammate("researcher")}

    for _ in range(3):
        bus.send(to="researcher", sender="writer", content="ping")

    summary = orch._status_summary(store, bus, teammates, threshold=2)
    assert "Back-pressure" in summary
    assert "researcher: 3 unread" in summary
    # Writer is under threshold, should NOT be flagged.
    assert "writer:" not in summary


def test_no_backpressure_flag_when_under_threshold(tmp_path):
    orch, _ = _make_orch(tmp_path)
    store = TaskStore(tmp_path / "tasks.jsonl")
    bus = MessageBus(tmp_path / "messages")
    teammates = {"writer": FakeTeammate("writer")}
    bus.send(to="writer", sender="lead", content="hi")
    summary = orch._status_summary(store, bus, teammates, threshold=2)
    assert "Back-pressure" not in summary
