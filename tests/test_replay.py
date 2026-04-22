"""Replay harness tests.

Replay is meaningful only if a trace captures enough detail to reconstruct
observable state — the tests here build a minimal trace by hand (to stay
hermetic) and separately replay any real trace found under runs/ as a
smoke-level regression."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mat.replay import replay_trace

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _write_trace(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def test_empty_trace_yields_empty_state(tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text("", encoding="utf-8")
    result = replay_trace(trace, tmp_path / "replay")
    assert result.tasks == []
    assert result.inbox_counts == {}
    assert result.finalized is None
    assert result.tool_use_count == 0


def test_create_assign_update_task_roundtrip(tmp_path):
    events = [
        {"event": "run_start", "cc_agent": "lead"},
        {"event": "tool_use", "agent": "lead", "name": "mcp__coord__create_task",
         "input": {"title": "T1", "description": "first", "dependencies": []}},
        {"event": "tool_use", "agent": "lead", "name": "mcp__coord__create_task",
         "input": {"title": "T2", "description": "second", "dependencies": ["t_001"]}},
        {"event": "tool_use", "agent": "lead", "name": "mcp__coord__assign_task",
         "input": {"task_id": "t_001", "agent": "alice"}},
        {"event": "tool_use", "agent": "alice", "name": "mcp__coord__update_task",
         "input": {"task_id": "t_001", "status": "completed", "result_ref": "out.md"}},
    ]
    _write_trace(tmp_path / "trace.jsonl", events)
    result = replay_trace(tmp_path / "trace.jsonl", tmp_path / "replay")

    by_id = {t.task_id: t for t in result.tasks}
    assert set(by_id) == {"t_001", "t_002"}
    assert by_id["t_001"].status == "completed"
    assert by_id["t_001"].assigned_to == "alice"
    assert by_id["t_001"].result_ref == "out.md"
    assert by_id["t_002"].dependencies == ["t_001"]
    assert result.cc_agent == "lead"


def test_send_message_replay_with_cc(tmp_path):
    events = [
        {"event": "run_start", "cc_agent": "lead"},
        {"event": "tool_use", "agent": "writer", "name": "mcp__coord__send_message",
         "input": {"to": "researcher", "content": "q?"}},
        {"event": "tool_use", "agent": "researcher", "name": "mcp__coord__send_message",
         "input": {"to": "writer", "content": "a!"}},
    ]
    _write_trace(tmp_path / "trace.jsonl", events)
    result = replay_trace(tmp_path / "trace.jsonl", tmp_path / "replay")

    assert result.inbox_counts.get("researcher") == 1
    assert result.inbox_counts.get("writer") == 1
    # Lead gets two CCs (one per direction).
    assert result.inbox_counts.get("lead") == 2


def test_cc_disabled_when_run_start_lacks_cc_agent(tmp_path):
    events = [
        {"event": "run_start"},  # no cc_agent field
        {"event": "tool_use", "agent": "writer", "name": "mcp__coord__send_message",
         "input": {"to": "researcher", "content": "q?"}},
    ]
    _write_trace(tmp_path / "trace.jsonl", events)
    result = replay_trace(tmp_path / "trace.jsonl", tmp_path / "replay")
    assert result.inbox_counts.get("researcher") == 1
    assert "lead" not in result.inbox_counts
    assert result.cc_agent is None


def test_finalize_captured(tmp_path):
    events = [
        {"event": "run_start"},
        {"event": "tool_use", "agent": "lead", "name": "mcp__coord__finalize",
         "input": {"synthesis": "done and dusted"}},
    ]
    _write_trace(tmp_path / "trace.jsonl", events)
    result = replay_trace(tmp_path / "trace.jsonl", tmp_path / "replay")
    assert result.finalized == "done and dusted"


def test_unknown_tools_ignored_not_crashed(tmp_path):
    events = [
        {"event": "run_start"},
        {"event": "tool_use", "agent": "lead", "name": "mcp__coord__never_heard_of_this",
         "input": {}},
        {"event": "tool_use", "agent": "alice", "name": "Bash",
         "input": {"command": "ls"}},
    ]
    _write_trace(tmp_path / "trace.jsonl", events)
    result = replay_trace(tmp_path / "trace.jsonl", tmp_path / "replay")
    assert "never_heard_of_this" in result.unknown_tools
    # Built-in Bash is not in the coord prefix → doesn't count as coord or unknown.
    assert result.tool_use_count == 2
    assert result.coord_count == 1


def test_write_scratchpad_is_known_noop(tmp_path):
    """write_scratchpad mutates the workspace, not coord state; replay
    should acknowledge it (not flag as unknown) but skip it silently."""
    events = [
        {"event": "run_start"},
        {"event": "tool_use", "agent": "lead", "name": "mcp__coord__write_scratchpad",
         "input": {"filename": "DONE_CRITERIA.md", "content": "- bullet"}},
    ]
    _write_trace(tmp_path / "trace.jsonl", events)
    result = replay_trace(tmp_path / "trace.jsonl", tmp_path / "replay")
    assert result.unknown_tools == []
    assert result.coord_count == 1


def test_non_tool_use_events_ignored(tmp_path):
    events = [
        {"event": "run_start"},
        {"event": "lead_turn_start", "turn": 0},
        {"event": "lead_block", "kind": "TextBlock", "preview": "hi"},
        {"event": "dispatch_round", "task_agents": [], "task_ids": []},
        {"event": "run_end"},
    ]
    _write_trace(tmp_path / "trace.jsonl", events)
    result = replay_trace(tmp_path / "trace.jsonl", tmp_path / "replay")
    assert result.tool_use_count == 0


@pytest.mark.parametrize("run_dir", sorted((PROJECT_ROOT / "runs").glob("*/")))
def test_replay_of_real_runs_is_stable(tmp_path, run_dir):
    """Smoke: every real trace under runs/ replays without error and yields
    some tasks (if the run got past the lead's first turn)."""
    trace = run_dir / "trace.jsonl"
    if not trace.exists():
        pytest.skip(f"no trace in {run_dir}")
    result = replay_trace(trace, tmp_path / "replay")
    # Can't assert exact state because older traces predate tool_use events
    # (only added in M4). What we CAN assert: replay doesn't raise, returns a
    # well-formed result.
    assert isinstance(result.inbox_counts, dict)
    assert result.unknown_tools == []
