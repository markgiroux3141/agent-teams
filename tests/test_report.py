"""Report generator tests: data extraction, HTML markers, markdown markers,
end-to-end on real runs, CLI entry, and resilience to report failures."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mat.config import LeadConfig, TeamConfig, TeammateConfig, TeamSettings
from mat.orchestrator import Orchestrator
from mat.report import (
    extract_report_data,
    generate_reports,
    main as report_main,
    render_html,
    render_markdown,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _write_trace(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def _ts(seconds_from_epoch: float) -> str:
    return datetime.fromtimestamp(seconds_from_epoch, tz=timezone.utc).isoformat()


def _build_fixture_run(run_dir: Path) -> None:
    """Minimal but realistic run: lead creates 2 tasks, alice does t_001,
    bob does t_002 (depends on t_001). Both complete. One CC message."""
    run_dir.mkdir(parents=True, exist_ok=True)

    events = [
        {"ts": _ts(1000), "event": "run_start", "goal": "test", "team": "t",
         "cc_agent": "lead", "unread_backpressure_threshold": 5,
         "stall_timeout_seconds": 60},
        {"ts": _ts(1001), "event": "lead_turn_start", "turn": 0},
        {"ts": _ts(1001.1), "event": "tool_use", "agent": "lead",
         "name": "mcp__coord__write_scratchpad",
         "input": {"filename": "DONE_CRITERIA.md", "content": "- bullet"},
         "tool_use_id": "tu_1"},
        {"ts": _ts(1001.2), "event": "tool_use", "agent": "lead",
         "name": "mcp__coord__create_task",
         "input": {"title": "T1", "description": "first", "dependencies": []},
         "tool_use_id": "tu_2"},
        {"ts": _ts(1001.3), "event": "tool_use", "agent": "lead",
         "name": "mcp__coord__create_task",
         "input": {"title": "T2", "description": "second",
                   "dependencies": ["t_001"]},
         "tool_use_id": "tu_3"},
        {"ts": _ts(1001.4), "event": "tool_use", "agent": "lead",
         "name": "mcp__coord__assign_task",
         "input": {"task_id": "t_001", "agent": "alice"}, "tool_use_id": "tu_4"},
        {"ts": _ts(1001.5), "event": "tool_use", "agent": "lead",
         "name": "mcp__coord__assign_task",
         "input": {"task_id": "t_002", "agent": "bob"}, "tool_use_id": "tu_5"},
        {"ts": _ts(1001.6), "event": "lead_result", "cost_usd": 0.01,
         "input_tokens": 10, "output_tokens": 20,
         "cache_read": 100, "cache_write": 50},
        {"ts": _ts(1002), "event": "lead_turn_end", "turn": 0},
        {"ts": _ts(1003), "event": "dispatch_round", "task_agents": ["alice"],
         "task_ids": ["t_001"], "reply_agents": [], "nudge_agents": []},
        {"ts": _ts(1003.1), "event": "dispatch_start", "agent": "alice",
         "task_id": "t_001", "inbox_note": False},
        {"ts": _ts(1003.2), "event": "tool_use", "agent": "alice",
         "name": "Write",
         "input": {"file_path": "alice.md", "content": "hi"},
         "tool_use_id": "tu_6"},
        {"ts": _ts(1003.3), "event": "tool_use", "agent": "alice",
         "name": "mcp__coord__update_task",
         "input": {"task_id": "t_001", "status": "completed",
                   "result_ref": "alice.md"}, "tool_use_id": "tu_7"},
        {"ts": _ts(1003.4), "event": "teammate_result", "agent": "alice",
         "cost_usd": 0.02, "input_tokens": 15, "output_tokens": 25,
         "cache_read": 200, "cache_write": 80},
        {"ts": _ts(1005), "event": "dispatch_end", "agent": "alice",
         "task_id": "t_001"},
        {"ts": _ts(1006), "event": "dispatch_round", "task_agents": ["bob"],
         "task_ids": ["t_002"], "reply_agents": [], "nudge_agents": []},
        {"ts": _ts(1006.1), "event": "dispatch_start", "agent": "bob",
         "task_id": "t_002", "inbox_note": False},
        {"ts": _ts(1006.2), "event": "tool_use", "agent": "bob",
         "name": "mcp__coord__send_message",
         "input": {"to": "alice", "content": "thanks"}, "tool_use_id": "tu_8"},
        {"ts": _ts(1006.3), "event": "tool_use", "agent": "bob",
         "name": "mcp__coord__update_task",
         "input": {"task_id": "t_002", "status": "completed",
                   "result_ref": "bob.md"}, "tool_use_id": "tu_9"},
        {"ts": _ts(1007), "event": "dispatch_end", "agent": "bob",
         "task_id": "t_002"},
        {"ts": _ts(1008), "event": "tool_use", "agent": "lead",
         "name": "mcp__coord__finalize",
         "input": {"synthesis": "done"}, "tool_use_id": "tu_10"},
        {"ts": _ts(1009), "event": "loop_exit", "reason": "finalized"},
        {"ts": _ts(1009.5), "event": "output_written",
         "path": str(run_dir / "workspace" / "OUTPUT.md")},
        {"ts": _ts(1010), "event": "run_summary_written",
         "path": str(run_dir / "run_summary.json")},
        {"ts": _ts(1010.5), "event": "run_end", "interrupted": False},
    ]
    _write_trace(run_dir / "trace.jsonl", events)

    summary = {
        "goal": "test fixture goal",
        "team": "fixture-team",
        "interrupted": False,
        "finalized": True,
        "task_counts_by_status": {"completed": 2},
        "tasks": [
            {"task_id": "t_001", "status": "completed", "assigned_to": "alice",
             "result_ref": "alice.md", "note": None},
            {"task_id": "t_002", "status": "completed", "assigned_to": "bob",
             "result_ref": "bob.md", "note": None},
        ],
        "cost": {
            "per_agent": {
                "lead": {"cost_usd": 0.01, "input_tokens": 10, "output_tokens": 20,
                         "cache_read": 100, "cache_write": 50, "turns": 1},
                "alice": {"cost_usd": 0.02, "input_tokens": 15, "output_tokens": 25,
                          "cache_read": 200, "cache_write": 80, "turns": 1},
            },
            "total": {"cost_usd": 0.03, "input_tokens": 25, "output_tokens": 45,
                      "cache_read": 300, "cache_write": 130, "turns": 2},
        },
    }
    (run_dir / "run_summary.json").write_text(json.dumps(summary), encoding="utf-8")

    workspace = run_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "alice.md").write_text("# Alice\nhello", encoding="utf-8")
    (workspace / "bob.md").write_text("# Bob\nworld", encoding="utf-8")
    (workspace / "OUTPUT.md").write_text("done", encoding="utf-8")
    (workspace / "DONE_CRITERIA.md").write_text("- bullet", encoding="utf-8")

    # One CC message: alice -> bob, lead gets a cc copy.
    messages_dir = run_dir / "messages"
    messages_dir.mkdir(exist_ok=True)
    (messages_dir / "bob.jsonl").write_text(
        json.dumps({"ts": "2026-04-22T10:00:00+00:00",
                    "sender": "alice", "to": "bob", "content": "hey"}) + "\n",
        encoding="utf-8",
    )
    (messages_dir / "lead.jsonl").write_text(
        json.dumps({"ts": "2026-04-22T10:00:00+00:00",
                    "sender": "alice", "to": "lead", "content": "hey",
                    "cc": True, "original_to": "bob"}) + "\n",
        encoding="utf-8",
    )


def test_extract_report_data_on_fixture(tmp_path):
    _build_fixture_run(tmp_path)
    data = extract_report_data(tmp_path)

    assert data.goal == "test fixture goal"
    assert data.team == "fixture-team"
    assert data.finalized is True
    assert data.interrupted is False
    assert "lead" in data.agents
    assert "alice" in data.agents
    assert "bob" in data.agents

    # Spans: 1 lead turn + 1 task per teammate.
    kinds = [s.kind for s in data.spans]
    assert "turn" in kinds
    assert kinds.count("task") == 2
    # Tool uses attached to the right span.
    alice_span = next(s for s in data.spans if s.agent == "alice" and s.kind == "task")
    assert len(alice_span.tool_uses) == 2  # Write + update_task

    # Tasks rebuilt by replay.
    ids = sorted(t.task_id for t in data.tasks)
    assert ids == ["t_001", "t_002"]
    assert all(t.status == "completed" for t in data.tasks)

    # Messages present: the direct one + a CC to lead.
    assert len(data.messages) == 2
    assert any(m.cc for m in data.messages)

    # Cost ledger picked up result events.
    assert data.cost.per_agent["lead"].turns == 1
    assert data.cost.per_agent["alice"].turns == 1

    # Artifacts tree.
    assert "root" in data.artifacts
    assert any(n == "OUTPUT.md" for n, _ in data.artifacts["root"])


def test_render_html_has_expected_markers(tmp_path):
    _build_fixture_run(tmp_path)
    data = extract_report_data(tmp_path)
    html = render_html(data)

    # Header + status pill.
    assert "Run <code>" in html
    assert "finalized" in html
    # Timeline SVG.
    assert "<svg" in html
    assert 'class="timeline"' in html
    # Each agent appears as a lane label.
    for agent in ("lead", "alice", "bob"):
        assert f">{agent}<" in html
    # Task DAG.
    assert "t_001" in html and "t_002" in html
    assert 'class="dag"' in html
    # Agent cards.
    assert 'class="cards"' in html
    # Artifact section with OUTPUT.md listed.
    assert "OUTPUT.md" in html
    # Messages table rendered with CC marker.
    assert "cc (→" in html
    # Link back to sibling markdown report.
    assert 'href="report.md"' in html


def test_render_markdown_has_mermaid_blocks(tmp_path):
    _build_fixture_run(tmp_path)
    data = extract_report_data(tmp_path)
    md = render_markdown(data)

    assert "# Run `" in md
    assert "```mermaid\ngantt" in md
    assert "```mermaid\ngraph TD" in md
    # Cost table.
    assert "| agent | turns | cost" in md
    # Task DAG class definitions.
    assert "classDef completed" in md
    # Sibling link back to HTML.
    assert "[report.html](report.html)" in md


def test_generate_reports_writes_both_files(tmp_path):
    _build_fixture_run(tmp_path)
    paths = generate_reports(tmp_path)
    assert paths["html"].exists() and paths["html"].stat().st_size > 1000
    assert paths["md"].exists() and paths["md"].stat().st_size > 200
    # Both open as utf-8.
    paths["html"].read_text(encoding="utf-8")
    paths["md"].read_text(encoding="utf-8")


def test_empty_run_dir_still_produces_reports(tmp_path):
    """A run dir with no trace / no summary should produce degraded reports
    rather than crashing — graceful-shutdown path may land here."""
    (tmp_path / "workspace").mkdir()
    paths = generate_reports(tmp_path)
    assert paths["html"].exists()
    assert paths["md"].exists()
    html = paths["html"].read_text(encoding="utf-8")
    assert "incomplete" in html


@pytest.mark.parametrize("run_dir", sorted(
    d for d in (PROJECT_ROOT / "runs").glob("*/")
    if (d / "trace.jsonl").exists()
))
def test_generate_reports_on_real_runs(tmp_path, run_dir):
    """Smoke: every real trace under runs/ should produce readable reports
    when copied to a tmp dir. Catches Windows path / encoding regressions."""
    import shutil
    target = tmp_path / run_dir.name
    shutil.copytree(run_dir, target)
    paths = generate_reports(target)
    assert paths["html"].read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    assert paths["md"].read_text(encoding="utf-8").startswith("# Run `")


def test_cli_main(tmp_path, capsys):
    _build_fixture_run(tmp_path)
    rc = report_main([str(tmp_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "html:" in captured.out
    assert "md:" in captured.out
    assert (tmp_path / "report.html").exists()
    assert (tmp_path / "report.md").exists()


def test_cli_main_missing_arg(capsys):
    rc = report_main([])
    assert rc == 2
    assert "usage" in capsys.readouterr().err


def test_cli_main_bad_path(tmp_path, capsys):
    rc = report_main([str(tmp_path / "does_not_exist")])
    assert rc == 1
    assert "does not exist" in capsys.readouterr().err


def test_report_failure_does_not_crash_run(tmp_path, monkeypatch):
    """If generate_reports raises, the orchestrator must log and continue
    rather than letting the error escape out of run()."""

    class FakeLead:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def start(self):
            # Hand finalize to the orchestrator directly; skips all real work.
            return ""
        async def continue_(self, prompt): return ""

    class FakeTM:
        last_status = "ready"
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def dispatch(self, prompt): return ""

    monkeypatch.setattr("mat.orchestrator.TeamLead", FakeLead)
    monkeypatch.setattr("mat.orchestrator.Teammate", FakeTM)

    def boom(run_dir):
        raise RuntimeError("simulated report failure")

    monkeypatch.setattr("mat.report.generate_reports", boom)

    team = TeamConfig(
        name="t", lead=LeadConfig(),
        teammates=[TeammateConfig(name="a", model="m", description="")],
        settings=TeamSettings(),
    )
    orch = Orchestrator(team, goal="g", run_dir=tmp_path)
    # Pretend the run finalized so we reach the reports step.
    orch.finalized_output = "synthesis"
    asyncio.run(orch.run())

    trace = [json.loads(l) for l in (tmp_path / "trace.jsonl").open() if l.strip()]
    assert any(e.get("event") == "reports_error" for e in trace)
    # run_summary.json still written — resilience preserved.
    assert (tmp_path / "run_summary.json").exists()
