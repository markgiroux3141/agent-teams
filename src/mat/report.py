"""Per-run visualizer: generate a self-contained HTML report and a
markdown+mermaid report for any run directory.

Both reports render from the same `ReportData` extracted in a single pass
over `trace.jsonl`, augmented with state from `tasks.jsonl`,
`messages/*.jsonl`, `run_summary.json`, and `workspace/`.

The HTML report uses vanilla SVG emitted server-side — no d3, no vis.js,
no CDN. Hover tooltips use native `<title>` elements. Artifact previews
use native `<details>` disclosure. This keeps reports fully offline and
Windows file://-friendly.

The markdown report uses mermaid `gantt` (for the timeline) and
`graph TD` (for the task DAG), plus plain markdown tables.

CLI:
    python -m mat.report <run_dir>
"""

from __future__ import annotations

import json
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from mat.logging import CostLedger, load_cost_ledger
from mat.replay import replay_trace
from mat.state.message_bus import Message
from mat.state.task_store import Task


# ----------------------------------------------------------------------
# Data extraction
# ----------------------------------------------------------------------


@dataclass
class Span:
    """A period of time where an agent was running. Unified across lead
    turns and teammate dispatches so the timeline renderer can treat them
    uniformly."""

    agent: str
    kind: str  # "turn" | "task" | "reply" | "nudge"
    start_ts: datetime
    end_ts: datetime | None = None
    task_id: str | None = None
    tool_uses: list[dict] = field(default_factory=list)
    error: str | None = None
    timed_out: bool = False


@dataclass
class ReportData:
    run_dir: Path
    run_id: str
    goal: str
    team: str
    run_start: datetime | None
    run_end: datetime | None
    finalized: bool
    interrupted: bool
    agents: list[str]  # [lead, ...teammates] in insertion order
    spans: list[Span]
    round_boundaries: list[datetime]
    tasks: list[Task]
    messages: list[Message]
    cost: CostLedger
    event_counts: dict[str, int]
    artifacts: dict[str, list[tuple[str, int]]]  # folder -> [(name, size)]

    @property
    def duration_seconds(self) -> float:
        if self.run_start and self.run_end:
            return (self.run_end - self.run_start).total_seconds()
        return 0.0


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def extract_report_data(run_dir: Path) -> ReportData:
    run_dir = Path(run_dir).resolve()
    trace_path = run_dir / "trace.jsonl"
    summary_path = run_dir / "run_summary.json"

    summary: dict[str, Any] = {}
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))

    events: list[dict] = []
    if trace_path.exists():
        with trace_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))

    run_start_evt = next((e for e in events if e.get("event") == "run_start"), None)
    run_end_evt = next(
        (e for e in reversed(events) if e.get("event") in ("run_end", "run_interrupted")),
        None,
    )
    run_start = _parse_ts(run_start_evt and run_start_evt.get("ts"))
    run_end = _parse_ts(run_end_evt and run_end_evt.get("ts"))
    if run_end is None and events:
        run_end = _parse_ts(events[-1].get("ts"))

    # --- Build agent list. Lead first, teammates in first-seen order. ---
    agents_seen: list[str] = ["lead"]
    for e in events:
        if e.get("event") in ("dispatch_start", "reply_dispatch_start", "nudge_start"):
            a = e.get("agent")
            if a and a not in agents_seen:
                agents_seen.append(a)

    # --- Build spans from paired start/end events. ---
    spans = _build_spans(events, run_end)

    # --- Round boundaries for timeline vertical markers. ---
    round_boundaries: list[datetime] = []
    for e in events:
        if e.get("event") == "dispatch_round":
            ts = _parse_ts(e.get("ts"))
            if ts is not None:
                round_boundaries.append(ts)

    # --- Event counts. ---
    event_counts = dict(Counter(e.get("event", "?") for e in events))

    # --- Rebuild final task + inbox state via replay. ---
    tasks: list[Task] = []
    if trace_path.exists():
        with tempfile.TemporaryDirectory() as tmp:
            replay = replay_trace(trace_path, Path(tmp))
        tasks = replay.tasks

    # --- Messages: read inbox files directly so we preserve full fields. ---
    messages: list[Message] = []
    messages_dir = run_dir / "messages"
    if messages_dir.exists():
        for inbox in sorted(messages_dir.glob("*.jsonl")):
            with inbox.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    messages.append(Message(**obj))
    messages.sort(key=lambda m: m.ts)

    # --- Cost ledger. ---
    cost = load_cost_ledger(trace_path) if trace_path.exists() else CostLedger()

    # --- Artifact tree under workspace/. ---
    artifacts = _collect_artifacts(run_dir / "workspace")

    return ReportData(
        run_dir=run_dir,
        run_id=run_dir.name,
        goal=summary.get("goal", "(goal unknown)"),
        team=summary.get("team", "(team unknown)"),
        run_start=run_start,
        run_end=run_end,
        finalized=bool(summary.get("finalized", False)),
        interrupted=bool(summary.get("interrupted", False)),
        agents=agents_seen,
        spans=spans,
        round_boundaries=round_boundaries,
        tasks=tasks,
        messages=messages,
        cost=cost,
        event_counts=event_counts,
        artifacts=artifacts,
    )


def _build_spans(events: list[dict], run_end: datetime | None) -> list[Span]:
    """Pair start/end events into spans and attach tool_use ticks by agent.

    Uses an open-per-agent stack so overlapping dispatches within an agent
    (rare, but possible) get paired FIFO. If a start has no matching end,
    it's closed at run_end."""

    spans: list[Span] = []
    # Per-agent open spans so tool_use events can be attached to the most
    # recent open span for that agent.
    open_spans: dict[str, Span] = {}

    # Lead uses a different pairing (turn_start/turn_end), and its "agent"
    # in the span is "lead" but the events have no agent field — they use
    # the `turn` field instead. We key lead spans by their turn number.
    open_lead_turns: dict[int, Span] = {}

    def _close(span: Span, ts: datetime | None) -> None:
        if span.end_ts is None:
            span.end_ts = ts or run_end or span.start_ts
        spans.append(span)

    for e in events:
        kind = e.get("event")
        ts = _parse_ts(e.get("ts"))
        if ts is None:
            continue

        # Lead turn spans.
        if kind == "lead_turn_start":
            turn_no = e.get("turn", -1)
            s = Span(agent="lead", kind="turn", start_ts=ts)
            open_lead_turns[turn_no] = s
            open_spans["lead"] = s
        elif kind == "lead_turn_end":
            turn_no = e.get("turn", -1)
            s = open_lead_turns.pop(turn_no, None)
            if s is not None:
                _close(s, ts)
                if open_spans.get("lead") is s:
                    open_spans.pop("lead", None)

        # Teammate task dispatches.
        elif kind == "dispatch_start":
            agent = e.get("agent", "?")
            s = Span(
                agent=agent, kind="task",
                start_ts=ts, task_id=e.get("task_id"),
            )
            open_spans[agent] = s
        elif kind == "dispatch_end":
            agent = e.get("agent", "?")
            s = open_spans.pop(agent, None)
            if s is not None:
                _close(s, ts)
        elif kind == "dispatch_error":
            agent = e.get("agent", "?")
            s = open_spans.pop(agent, None)
            if s is not None:
                s.error = e.get("error", "error")
                _close(s, ts)
        elif kind == "dispatch_timeout":
            agent = e.get("who", "?")
            s = open_spans.pop(agent, None)
            if s is not None:
                s.timed_out = True
                s.error = f"timeout after {e.get('timeout_seconds')}s"
                _close(s, ts)

        # Reply dispatches.
        elif kind == "reply_dispatch_start":
            agent = e.get("agent", "?")
            s = Span(agent=agent, kind="reply", start_ts=ts)
            open_spans[agent] = s
        elif kind == "reply_dispatch_end":
            agent = e.get("agent", "?")
            s = open_spans.pop(agent, None)
            if s is not None:
                _close(s, ts)
        elif kind == "reply_dispatch_error":
            agent = e.get("agent", "?")
            s = open_spans.pop(agent, None)
            if s is not None:
                s.error = e.get("error", "error")
                _close(s, ts)

        # Nudge dispatches.
        elif kind == "nudge_start":
            agent = e.get("agent", "?")
            s = Span(
                agent=agent, kind="nudge", start_ts=ts,
                task_id=e.get("task_id"),
            )
            open_spans[agent] = s
        elif kind == "nudge_end":
            agent = e.get("agent", "?")
            s = open_spans.pop(agent, None)
            if s is not None:
                _close(s, ts)

        # Attach tool_use ticks to whichever span is open for the agent.
        elif kind == "tool_use":
            agent = e.get("agent", "?")
            open_ = open_spans.get(agent)
            if open_ is not None:
                open_.tool_uses.append({
                    "ts": ts,
                    "name": e.get("name", "?"),
                    "input": e.get("input", {}),
                })

    # Close any lingering open spans at run_end.
    for s in list(open_lead_turns.values()):
        _close(s, run_end)
    for agent, s in list(open_spans.items()):
        if s not in spans:
            _close(s, run_end)

    spans.sort(key=lambda s: s.start_ts)
    return spans


def _collect_artifacts(workspace: Path) -> dict[str, list[tuple[str, int]]]:
    out: dict[str, list[tuple[str, int]]] = defaultdict(list)
    if not workspace.exists():
        return dict(out)
    for p in sorted(workspace.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(workspace)
        parts = rel.parts
        folder = parts[0] if len(parts) > 1 else "root"
        out[folder].append((str(rel).replace("\\", "/"), p.stat().st_size))
    return dict(out)


# ----------------------------------------------------------------------
# HTML renderer
# ----------------------------------------------------------------------

_KIND_COLORS = {
    "turn": "#94a3b8",     # slate — lead
    "task": "#2563eb",     # blue
    "reply": "#16a34a",    # green
    "nudge": "#ea580c",    # orange
}
_FAILED_COLOR = "#dc2626"  # red — overrides kind color when span has error

_TIMELINE_WIDTH = 1200
_LANE_LABEL_WIDTH = 140
_LANE_HEIGHT = 44
_LANE_PAD = 6
_MIN_BAR_WIDTH = 4  # px — so zero/near-zero dispatches don't disappear


def render_html(data: ReportData) -> str:
    title = f"MAT run {escape(data.run_id)}"
    css = _html_css()
    header = _html_header(data)
    legend = _html_legend()
    timeline = _html_timeline(data)
    dag = _html_task_dag(data)
    agents = _html_agent_cards(data)
    artifacts = _html_artifacts(data)
    messages = _html_messages(data)
    footer = _html_footer(data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{css}
</style>
</head>
<body>
<div class="wrap">
{header}
<section><h2>Timeline</h2>{legend}{timeline}</section>
<section><h2>Task graph</h2>{dag}</section>
<section><h2>Per-agent breakdown</h2>{agents}</section>
<section><h2>Artifacts</h2>{artifacts}</section>
<section><h2>Messages</h2>{messages}</section>
{footer}
</div>
</body>
</html>"""


def _html_css() -> str:
    return """
body { font: 14px/1.5 -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;
       color: #0f172a; background: #f8fafc; margin: 0; }
.wrap { max-width: 1300px; margin: 24px auto; padding: 0 16px; }
h1 { font-size: 22px; margin: 0 0 8px; }
h2 { font-size: 17px; margin: 28px 0 10px; padding-bottom: 4px;
     border-bottom: 1px solid #e2e8f0; }
section { margin-bottom: 28px; }
.meta { display: grid; grid-template-columns: max-content 1fr; column-gap: 16px;
        row-gap: 4px; font-size: 13px; margin-bottom: 8px; }
.meta dt { color: #64748b; }
.meta dd { margin: 0; }
.pill { display: inline-block; padding: 2px 8px; border-radius: 10px;
        font-size: 12px; font-weight: 600; }
.pill.finalized { background: #dcfce7; color: #166534; }
.pill.interrupted { background: #fef3c7; color: #92400e; }
.pill.incomplete { background: #fee2e2; color: #991b1b; }
.legend { display: flex; gap: 14px; font-size: 12px; margin-bottom: 6px; color: #475569; }
.legend .sw { display: inline-block; width: 14px; height: 10px; border-radius: 2px;
              margin-right: 4px; vertical-align: middle; }
.timeline svg { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; }
.timeline .grid line { stroke: #e2e8f0; }
.timeline .lane-label { font: 12px/1 Consolas, monospace; fill: #334155; }
.timeline .axis text { font: 11px/1 Consolas, monospace; fill: #64748b; }
.timeline .round-boundary { stroke: #cbd5e1; stroke-dasharray: 3 3; }
.dag { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; }
.dag .node rect { stroke: #1e293b; stroke-width: 1; }
.dag .node text { font: 12px/1 Consolas, monospace; }
.dag .edge { stroke: #94a3b8; fill: none; marker-end: url(#arrow); }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
         gap: 12px; }
.card { background: #fff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px; }
.card h3 { margin: 0 0 8px; font-size: 15px; }
.card table { width: 100%; border-collapse: collapse; font-size: 12px; }
.card td { padding: 3px 6px; border-bottom: 1px dashed #f1f5f9; }
.card td:last-child { text-align: right; font-family: Consolas, monospace; }
table.messages, table.events, table.tasks { width: 100%; border-collapse: collapse;
         font-size: 12px; background: #fff; border: 1px solid #e2e8f0; border-radius: 6px; }
table.messages td, table.messages th,
table.events td, table.events th,
table.tasks td, table.tasks th {
    padding: 6px 8px; border-bottom: 1px solid #f1f5f9; text-align: left;
    vertical-align: top;
}
table.messages th, table.events th, table.tasks th { background: #f8fafc; font-weight: 600; }
details.artifact { background: #fff; border: 1px solid #e2e8f0; border-radius: 6px;
                   padding: 8px 12px; margin-bottom: 6px; }
details.artifact summary { cursor: pointer; font-family: Consolas, monospace;
                           font-size: 13px; }
details.artifact pre { background: #f1f5f9; padding: 10px; overflow-x: auto;
                       font-size: 12px; border-radius: 4px; max-height: 420px; }
.folder-header { margin: 14px 0 4px; font-size: 13px; color: #475569;
                 font-family: Consolas, monospace; }
.empty { color: #64748b; font-style: italic; }
.status-completed { background: #dcfce7; }
.status-failed { background: #fee2e2; }
.status-in_progress { background: #fef3c7; }
.status-assigned, .status-created, .status-claimed { background: #e0e7ff; }
"""


def _html_header(data: ReportData) -> str:
    status = "incomplete"
    status_label = "incomplete"
    if data.finalized:
        status, status_label = "finalized", "finalized"
    elif data.interrupted:
        status, status_label = "interrupted", "interrupted"
    total = data.cost.totals()
    dur = data.duration_seconds
    start = data.run_start.isoformat() if data.run_start else "?"
    return f"""<header>
<h1>Run <code>{escape(data.run_id)}</code></h1>
<dl class="meta">
<dt>Goal</dt><dd>{escape(data.goal)}</dd>
<dt>Team</dt><dd><code>{escape(data.team)}</code></dd>
<dt>Started</dt><dd>{escape(start)}</dd>
<dt>Duration</dt><dd>{dur:.1f} s</dd>
<dt>Status</dt><dd><span class="pill {status}">{status_label}</span></dd>
<dt>Total cost</dt><dd>${total.cost_usd:.4f}
  ({total.turns} turns, {total.input_tokens} in / {total.output_tokens} out,
  cache_r={total.cache_read})</dd>
<dt>Sibling</dt><dd><a href="report.md">report.md</a></dd>
</dl>
</header>"""


def _html_legend() -> str:
    items = [
        ("lead turn", _KIND_COLORS["turn"]),
        ("task dispatch", _KIND_COLORS["task"]),
        ("reply dispatch", _KIND_COLORS["reply"]),
        ("nudge", _KIND_COLORS["nudge"]),
        ("failed / timeout", _FAILED_COLOR),
    ]
    return '<div class="legend">' + "".join(
        f'<span><span class="sw" style="background:{c}"></span>{escape(l)}</span>'
        for l, c in items
    ) + "</div>"


def _html_timeline(data: ReportData) -> str:
    if not data.spans or data.run_start is None:
        return '<p class="empty">No dispatch activity recorded.</p>'

    lanes = data.agents
    height_lanes = len(lanes) * _LANE_HEIGHT + 40  # +40 for axis
    total = max(1e-3, data.duration_seconds)
    content_w = _TIMELINE_WIDTH - _LANE_LABEL_WIDTH
    x_scale = content_w / total

    def x_at(ts: datetime) -> float:
        return _LANE_LABEL_WIDTH + (ts - data.run_start).total_seconds() * x_scale

    def lane_y(agent: str) -> int:
        idx = lanes.index(agent) if agent in lanes else len(lanes)
        return 40 + idx * _LANE_HEIGHT

    parts: list[str] = []
    parts.append(
        f'<div class="timeline"><svg viewBox="0 0 {_TIMELINE_WIDTH} {height_lanes}" '
        f'width="100%" preserveAspectRatio="xMinYMin meet">'
    )

    # Axis: 5 ticks evenly spaced.
    axis_y = 24
    parts.append('<g class="axis">')
    for i in range(6):
        frac = i / 5
        x = _LANE_LABEL_WIDTH + content_w * frac
        label = f"{total * frac:.1f}s"
        parts.append(
            f'<line x1="{x:.1f}" y1="{axis_y}" x2="{x:.1f}" '
            f'y2="{height_lanes - 2}" class="grid" stroke="#e2e8f0" />'
        )
        parts.append(f'<text x="{x:.1f}" y="{axis_y - 4}" text-anchor="middle">{label}</text>')
    parts.append("</g>")

    # Lane labels + horizontal separators.
    for i, agent in enumerate(lanes):
        y = 40 + i * _LANE_HEIGHT
        parts.append(
            f'<text class="lane-label" x="{_LANE_LABEL_WIDTH - 8}" '
            f'y="{y + _LANE_HEIGHT / 2 + 4}" text-anchor="end">{escape(agent)}</text>'
        )
        parts.append(
            f'<line x1="{_LANE_LABEL_WIDTH}" y1="{y}" '
            f'x2="{_TIMELINE_WIDTH}" y2="{y}" stroke="#f1f5f9" />'
        )
    # Bottom border.
    y_bot = 40 + len(lanes) * _LANE_HEIGHT
    parts.append(
        f'<line x1="{_LANE_LABEL_WIDTH}" y1="{y_bot}" '
        f'x2="{_TIMELINE_WIDTH}" y2="{y_bot}" stroke="#e2e8f0" />'
    )

    # Round boundaries.
    for b in data.round_boundaries:
        x = x_at(b)
        parts.append(
            f'<line class="round-boundary" x1="{x:.1f}" y1="40" '
            f'x2="{x:.1f}" y2="{y_bot}" />'
        )

    # Spans.
    for span in data.spans:
        end = span.end_ts or data.run_end or span.start_ts
        x1 = x_at(span.start_ts)
        x2 = x_at(end)
        w = max(_MIN_BAR_WIDTH, x2 - x1)
        y = lane_y(span.agent) + _LANE_PAD
        h = _LANE_HEIGHT - 2 * _LANE_PAD
        color = _FAILED_COLOR if span.error or span.timed_out else _KIND_COLORS.get(span.kind, "#64748b")
        label_bits = [span.kind]
        if span.task_id:
            label_bits.append(span.task_id)
        if span.error:
            label_bits.append(f"ERR: {span.error[:60]}")
        dur = (end - span.start_ts).total_seconds()
        tip = f"{span.agent} · {' · '.join(label_bits)} · {dur:.2f}s · {len(span.tool_uses)} tool calls"
        parts.append(
            f'<rect x="{x1:.1f}" y="{y}" width="{w:.1f}" height="{h}" '
            f'fill="{color}" fill-opacity="0.85" rx="2" ry="2">'
            f'<title>{escape(tip)}</title></rect>'
        )
        # Tool-use tick marks.
        for tu in span.tool_uses:
            tx = x_at(tu["ts"])
            if tx < x1 - 1 or tx > x2 + 1:
                continue
            name = tu.get("name", "")
            short_name = name.replace("mcp__coord__", "")
            input_preview = json.dumps(tu.get("input", {}), default=str)[:200]
            tu_tip = f"{tu['ts'].isoformat()}\n{name}\n{input_preview}"
            parts.append(
                f'<line x1="{tx:.1f}" y1="{y}" x2="{tx:.1f}" y2="{y + h}" '
                f'stroke="#ffffff" stroke-opacity="0.85" stroke-width="1.5">'
                f'<title>{escape(tu_tip)}</title></line>'
            )
            _ = short_name  # reserved for future label rendering

    parts.append("</svg></div>")
    return "".join(parts)


def _html_task_dag(data: ReportData) -> str:
    if not data.tasks:
        return '<p class="empty">No tasks on the board.</p>'

    # Layered layout by dependency depth.
    by_id = {t.task_id: t for t in data.tasks}

    def depth(tid: str, seen: set[str] | None = None) -> int:
        if seen is None:
            seen = set()
        if tid in seen:
            return 0
        seen.add(tid)
        t = by_id.get(tid)
        if not t or not t.dependencies:
            return 0
        return 1 + max((depth(d, seen) for d in t.dependencies), default=0)

    depths = {t.task_id: depth(t.task_id) for t in data.tasks}
    by_depth: dict[int, list[Task]] = defaultdict(list)
    for t in data.tasks:
        by_depth[depths[t.task_id]].append(t)

    col_w = 220
    row_h = 64
    pad_x = 20
    pad_y = 20
    max_col = max(by_depth) if by_depth else 0
    max_rows = max((len(v) for v in by_depth.values()), default=1)
    svg_w = pad_x * 2 + (max_col + 1) * col_w
    svg_h = pad_y * 2 + max_rows * row_h

    positions: dict[str, tuple[int, int]] = {}
    for col, tasks in by_depth.items():
        tasks_sorted = sorted(tasks, key=lambda t: t.task_id)
        for row, t in enumerate(tasks_sorted):
            cx = pad_x + col * col_w + 10
            cy = pad_y + row * row_h
            positions[t.task_id] = (cx, cy)

    parts: list[str] = []
    parts.append(
        f'<div class="dag"><svg viewBox="0 0 {svg_w} {svg_h}" '
        f'width="100%" preserveAspectRatio="xMinYMin meet">'
    )
    # Arrow marker.
    parts.append(
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8"/></marker></defs>'
    )
    # Edges.
    for t in data.tasks:
        if t.task_id not in positions:
            continue
        x2, y2 = positions[t.task_id]
        x2 += 5  # left edge of box
        y2 += 20  # middle of box
        for dep in t.dependencies:
            p = positions.get(dep)
            if not p:
                continue
            x1 = p[0] + col_w - 40  # right edge of parent
            y1 = p[1] + 20
            parts.append(
                f'<path class="edge" d="M {x1} {y1} C {x1 + 40} {y1}, '
                f'{x2 - 40} {y2}, {x2} {y2}" />'
            )
    # Nodes.
    status_fill = {
        "completed": "#dcfce7",
        "failed": "#fee2e2",
        "in_progress": "#fef3c7",
        "assigned": "#e0e7ff",
        "created": "#e0e7ff",
        "claimed": "#e0e7ff",
    }
    for t in data.tasks:
        if t.task_id not in positions:
            continue
        x, y = positions[t.task_id]
        fill = status_fill.get(t.status, "#f1f5f9")
        title_text = (
            f"{t.task_id} [{t.status}]\n{t.title}\n"
            f"assigned: {t.assigned_to or '?'}\n"
            f"ref: {t.result_ref or '(none)'}\n"
            f"deps: {', '.join(t.dependencies) or '(none)'}"
        )
        parts.append(f'<g class="node"><title>{escape(title_text)}</title>')
        parts.append(
            f'<rect x="{x}" y="{y}" width="{col_w - 40}" height="40" '
            f'rx="4" fill="{fill}" />'
        )
        title_short = t.title[:26] + ("…" if len(t.title) > 26 else "")
        parts.append(
            f'<text x="{x + 8}" y="{y + 16}">'
            f'<tspan font-weight="700">{escape(t.task_id)}</tspan> '
            f'<tspan fill="#64748b">{escape(t.status)}</tspan></text>'
        )
        parts.append(
            f'<text x="{x + 8}" y="{y + 32}">{escape(title_short)}</text>'
        )
        parts.append("</g>")

    parts.append("</svg></div>")
    return "".join(parts)


def _html_agent_cards(data: ReportData) -> str:
    if not data.cost.per_agent:
        return '<p class="empty">No cost data recorded.</p>'

    # Tool-use tallies per agent.
    tool_counts: dict[str, Counter] = defaultdict(Counter)
    for s in data.spans:
        for tu in s.tool_uses:
            tool_counts[s.agent][tu["name"]] += 1

    cards: list[str] = ['<div class="cards">']
    for agent in data.agents:
        c = data.cost.per_agent.get(agent)
        if c is None:
            continue
        cache_hit = (
            c.cache_read / (c.cache_read + c.input_tokens)
            if (c.cache_read + c.input_tokens) > 0 else 0.0
        )
        tools = tool_counts.get(agent, Counter())
        top = tools.most_common(8)
        rows = "".join(
            f"<tr><td>{escape(n)}</td><td>{v}</td></tr>" for n, v in top
        ) or '<tr><td colspan="2" class="empty">(no tool calls recorded)</td></tr>'
        cards.append(f"""<div class="card">
<h3>{escape(agent)}</h3>
<table>
<tr><td>turns</td><td>{c.turns}</td></tr>
<tr><td>cost</td><td>${c.cost_usd:.4f}</td></tr>
<tr><td>input tok</td><td>{c.input_tokens}</td></tr>
<tr><td>output tok</td><td>{c.output_tokens}</td></tr>
<tr><td>cache read</td><td>{c.cache_read}</td></tr>
<tr><td>cache write</td><td>{c.cache_write}</td></tr>
<tr><td>cache-hit %</td><td>{cache_hit * 100:.1f}%</td></tr>
</table>
<h3 style="margin-top:8px;font-size:13px;">top tools</h3>
<table>{rows}</table>
</div>""")
    cards.append("</div>")
    return "".join(cards)


_TEXT_SUFFIXES = {".md", ".html", ".htm", ".js", ".py", ".json", ".txt",
                  ".yaml", ".yml", ".css"}


def _html_artifacts(data: ReportData) -> str:
    if not data.artifacts:
        return '<p class="empty">No artifacts produced under workspace/.</p>'

    workspace = data.run_dir / "workspace"
    parts: list[str] = []
    for folder in sorted(data.artifacts):
        parts.append(f'<div class="folder-header">{escape(folder)}/</div>')
        for name, size in data.artifacts[folder]:
            path = workspace / name
            suffix = path.suffix.lower()
            safe_name = escape(name)
            size_str = f"{size:,} B"
            if suffix in _TEXT_SUFFIXES and path.exists() and size < 200_000:
                try:
                    body = path.read_text(encoding="utf-8", errors="replace")
                except Exception as e:
                    body = f"(could not read: {e})"
                parts.append(
                    f'<details class="artifact"><summary>{safe_name} '
                    f'<span class="empty">· {size_str}</span></summary>'
                    f'<pre>{escape(body)}</pre></details>'
                )
            else:
                parts.append(
                    f'<div class="artifact" style="font-family:Consolas,monospace;'
                    f'font-size:13px;">{safe_name} '
                    f'<span class="empty">· {size_str} · (binary or large)</span></div>'
                )
    return "".join(parts)


def _html_messages(data: ReportData) -> str:
    if not data.messages:
        return '<p class="empty">No messages exchanged in this run.</p>'
    rows = ""
    for m in data.messages:
        cc_label = f"cc (→ {escape(m.original_to or '?')})" if m.cc else ""
        rows += (
            f"<tr><td>{escape(m.ts)}</td>"
            f"<td>{escape(m.sender)} → {escape(m.to)} {cc_label}</td>"
            f"<td>{escape(m.content[:400])}</td></tr>"
        )
    return f"""<table class="messages">
<thead><tr><th>ts</th><th>from → to</th><th>content</th></tr></thead>
<tbody>{rows}</tbody></table>"""


def _html_footer(data: ReportData) -> str:
    rows = "".join(
        f"<tr><td>{escape(k)}</td><td>{v}</td></tr>"
        for k, v in sorted(data.event_counts.items())
    )
    return f"""<section><details><summary>Raw event counts
({sum(data.event_counts.values())} events total)</summary>
<table class="events"><thead><tr><th>event</th><th>count</th></tr></thead>
<tbody>{rows}</tbody></table></details></section>"""


# ----------------------------------------------------------------------
# Markdown renderer
# ----------------------------------------------------------------------


def render_markdown(data: ReportData) -> str:
    parts: list[str] = []
    parts.append(_md_header(data))
    parts.append(_md_sequence(data))
    parts.append(_md_timeline(data))
    parts.append(_md_task_dag(data))
    parts.append(_md_costs(data))
    parts.append(_md_tool_tally(data))
    parts.append(_md_artifacts(data))
    parts.append(_md_messages(data))
    parts.append(_md_raw_counts(data))
    return "\n\n".join(p for p in parts if p) + "\n"


def _md_header(data: ReportData) -> str:
    status = (
        "finalized" if data.finalized
        else "interrupted" if data.interrupted
        else "incomplete"
    )
    total = data.cost.totals()
    return (
        f"# Run `{data.run_id}`\n\n"
        f"See also: [report.html](report.html)\n\n"
        f"| | |\n|---|---|\n"
        f"| goal | {data.goal} |\n"
        f"| team | `{data.team}` |\n"
        f"| started | {data.run_start.isoformat() if data.run_start else '?'} |\n"
        f"| duration | {data.duration_seconds:.1f} s |\n"
        f"| status | **{status}** |\n"
        f"| total cost | ${total.cost_usd:.4f} ({total.turns} turns) |\n"
        f"| tokens | in {total.input_tokens} / out {total.output_tokens} / cache_r {total.cache_read} |\n"
    )


def _sequence_events(data: ReportData) -> list[dict]:
    """Flatten messages + coordination tool_uses into a time-ordered list of
    sequence-diagram events. Used by both the markdown renderer and the
    standalone sequence.md export."""

    events: list[dict] = []

    for m in data.messages:
        if m.cc:
            continue  # CC duplicates are implicit via the primary message
        ts = _parse_ts(m.ts) or data.run_start
        if ts is None:
            continue
        events.append({
            "ts": ts,
            "kind": "msg",
            "from": m.sender,
            "to": m.to,
            "label": _sequence_label(m.content, 90),
            "full": _sequence_label(m.content, 2000),
            "cc": False,
        })

    for span in data.spans:
        for tu in span.tool_uses:
            name = tu.get("name", "")
            inp = tu.get("input", {}) or {}
            ts = tu.get("ts")
            if not isinstance(ts, datetime):
                continue
            if name == "mcp__coord__create_task":
                events.append({
                    "ts": ts, "kind": "note", "who": span.agent,
                    "label": f'creates task: {_sequence_label(inp.get("title", ""), 60)}',
                })
            elif name == "mcp__coord__assign_task":
                tid = inp.get("task_id", "?")
                target = inp.get("agent", "?")
                events.append({
                    "ts": ts, "kind": "assign",
                    "from": span.agent, "to": target,
                    "label": f"dispatch {tid}",
                })
            elif name == "mcp__coord__update_task":
                status = inp.get("status", "")
                tid = inp.get("task_id", "?")
                if status == "completed":
                    ref = inp.get("result_ref") or ""
                    label = f"{tid} done" + (f" → {ref}" if ref else "")
                    events.append({
                        "ts": ts, "kind": "done",
                        "from": span.agent, "to": "lead",
                        "label": label,
                    })
                elif status == "failed":
                    note = _sequence_label(inp.get("note", ""), 40)
                    events.append({
                        "ts": ts, "kind": "failed",
                        "from": span.agent, "to": "lead",
                        "label": f"{tid} FAILED" + (f": {note}" if note else ""),
                    })
            elif name == "mcp__coord__finalize":
                events.append({
                    "ts": ts, "kind": "note", "who": "lead",
                    "label": "finalize()",
                })
            elif name == "mcp__coord__write_scratchpad":
                fn = inp.get("filename", "?")
                events.append({
                    "ts": ts, "kind": "note", "who": span.agent,
                    "label": f"writes {fn}",
                })

    events.sort(key=lambda e: e["ts"])
    return events


def _sequence_label(text: str, max_chars: int) -> str:
    """Sanitize a label for mermaid: collapse whitespace, strip quotes,
    trim to length, escape backticks. Returns empty string for None/empty."""
    if not text:
        return ""
    s = " ".join(str(text).split())
    s = s.replace('"', "'").replace("`", "'")
    if len(s) > max_chars:
        s = s[:max_chars - 1].rstrip() + "…"
    return s


def _md_sequence(data: ReportData) -> str:
    events = _sequence_events(data)
    if not events:
        return "## Conversation\n\n_No messages or coordination events recorded._"

    # Participants: lead + teammates from roster, plus any stranger recipients
    # (e.g. a message sent to a name that isn't on the team).
    known = list(data.agents)
    seen = set(known)
    for e in events:
        for key in ("from", "to", "who"):
            v = e.get(key)
            if v and v not in seen:
                known.append(v)
                seen.add(v)

    lines = ["## Conversation", "",
             "_Time-ordered exchange between agents: task dispatches,"
             " messages, and completions. CC-to-lead traffic is implicit in"
             " the primary arrow._", "",
             "```mermaid",
             "sequenceDiagram"]
    for agent in known:
        lines.append(f"    participant {_mermaid_ident(agent)}")

    for e in events:
        kind = e["kind"]
        if kind == "note":
            who = _mermaid_ident(e["who"])
            lines.append(f"    Note over {who}: {e['label']}")
        elif kind == "assign":
            src = _mermaid_ident(e["from"])
            dst = _mermaid_ident(e["to"])
            lines.append(f"    {src}->>+{dst}: {e['label']}")
        elif kind == "done":
            src = _mermaid_ident(e["from"])
            dst = _mermaid_ident(e["to"])
            lines.append(f"    {src}-->>-{dst}: {e['label']}")
        elif kind == "failed":
            src = _mermaid_ident(e["from"])
            dst = _mermaid_ident(e["to"])
            lines.append(f"    {src}--x{dst}: {e['label']}")
        elif kind == "msg":
            src = _mermaid_ident(e["from"])
            dst = _mermaid_ident(e["to"])
            lines.append(f"    {src}->>{dst}: {e['label']}")
    lines.append("```")
    return "\n".join(lines)


def _mermaid_ident(name: str) -> str:
    """Mermaid participant identifiers should avoid spaces/punctuation."""
    return "".join(c if (c.isalnum() or c == "_") else "_" for c in name)


# ----------------------------------------------------------------------
# Animated playback (standalone HTML, reveals events one by one)
# ----------------------------------------------------------------------


def _sequence_events_for_json(data: ReportData) -> dict:
    """Serialize the sequence-event stream for the playback UI."""
    events = _sequence_events(data)

    # Unique participants in display order: roster first, then strangers.
    agents: list[str] = list(data.agents)
    seen = set(agents)
    for e in events:
        for key in ("from", "to", "who"):
            v = e.get(key)
            if v and v not in seen:
                agents.append(v)
                seen.add(v)

    json_events: list[dict] = []
    for e in events:
        obj: dict[str, Any] = {
            "ts": e["ts"].isoformat() if isinstance(e["ts"], datetime) else str(e["ts"]),
            "kind": e["kind"],
            "label": e.get("label", ""),
        }
        if "full" in e and e["full"] and e["full"] != e.get("label"):
            obj["full"] = e["full"]
        if "who" in e:
            obj["who"] = e["who"]
        if "from" in e:
            obj["from"] = e["from"]
        if "to" in e:
            obj["to"] = e["to"]
        json_events.append(obj)

    return {
        "run_id": data.run_id,
        "team": data.team,
        "goal": data.goal,
        "agents": agents,
        "events": json_events,
    }


def render_playback_html(data: ReportData) -> str:
    payload = _sequence_events_for_json(data)
    # Inline-encode to avoid any CDN/fetch/`file://` issues.
    # Escape </script and trailing </ sequences defensively.
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_json = payload_json.replace("</", "<\\/")
    title = f"Playback — {payload['run_id']}"
    template = _PLAYBACK_TEMPLATE
    return (
        template
        .replace("{{TITLE}}", escape(title))
        .replace("{{RUN_ID}}", escape(payload["run_id"]))
        .replace("{{TEAM}}", escape(payload["team"]))
        .replace("{{EVENT_COUNT}}", str(len(payload["events"])))
        .replace("{{DATA_JSON}}", payload_json)
    )


def render_stage_html(data: ReportData) -> str:
    """A theatrical playback: emoji avatars on a stage, speech bubbles pop up
    above whoever is talking, a curved arrow connects to the listener, and a
    rolling subtitle log preserves history."""
    payload = _sequence_events_for_json(data)
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_json = payload_json.replace("</", "<\\/")
    title = f"Stage — {payload['run_id']}"
    return (
        _STAGE_TEMPLATE
        .replace("{{TITLE}}", escape(title))
        .replace("{{RUN_ID}}", escape(payload["run_id"]))
        .replace("{{TEAM}}", escape(payload["team"]))
        .replace("{{EVENT_COUNT}}", str(len(payload["events"])))
        .replace("{{DATA_JSON}}", payload_json)
    )


_STAGE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{{TITLE}}</title>
<style>
  :root {
    --bg: #0f172a; --fg: #f1f5f9; --muted: #94a3b8; --line: #334155;
    --panel: #1e293b; --accent: #60a5fa; --ok: #4ade80;
    --warn: #fb923c; --err: #f87171; --msg: #22d3ee;
    --note: #facc15; --bubble: #f8fafc; --bubble-fg: #0f172a;
  }
  * { box-sizing: border-box; }
  body { font: 14px/1.4 -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;
         color: var(--fg); background: var(--bg); margin: 0; }
  .wrap { max-width: 1400px; margin: 16px auto; padding: 0 16px; }
  header { display: flex; justify-content: space-between; align-items: baseline;
           gap: 16px; }
  header h1 { font-size: 20px; margin: 0; }
  header .meta { color: var(--muted); font-size: 13px; }
  header .meta code { background: var(--panel); padding: 1px 6px; border-radius: 3px;
                      color: var(--fg); }
  .controls { display: flex; gap: 8px; align-items: center; padding: 8px 12px;
              background: var(--panel); border: 1px solid var(--line);
              border-radius: 6px; margin: 12px 0; position: sticky; top: 8px;
              z-index: 10; }
  .controls button { font: 14px/1 system-ui; padding: 6px 10px; cursor: pointer;
                     background: var(--panel); color: var(--fg);
                     border: 1px solid var(--line); border-radius: 4px; min-width: 36px; }
  .controls button:hover { background: #334155; }
  .controls button.primary { background: var(--accent); color: #0b1220;
                             border-color: var(--accent); font-weight: 600; }
  .controls button.primary:hover { background: #93c5fd; }
  .controls button:disabled { opacity: 0.4; cursor: not-allowed; }
  .controls .sep { width: 1px; height: 20px; background: var(--line); margin: 0 4px; }
  .controls .group { display: flex; align-items: center; gap: 6px; color: var(--muted);
                     font-size: 12px; }
  .controls select { font: 13px system-ui; padding: 4px 6px; border: 1px solid var(--line);
                     border-radius: 4px; background: var(--panel); color: var(--fg); }
  .controls .toggle { display: flex; align-items: center; gap: 6px; color: var(--muted);
                      font-size: 12px; cursor: pointer; user-select: none; }
  .controls .toggle input { cursor: pointer; accent-color: var(--accent); }
  .controls .toggle.on { color: var(--fg); }
  .controls .scrubber { flex: 1; min-width: 120px; accent-color: var(--accent); }
  .controls .progress { font-family: Consolas, monospace; font-size: 12px;
                        min-width: 62px; text-align: right; }
  #stage { background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
           border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
  #stage svg { display: block; width: 100%; height: auto; }
  .floor { fill: #111827; }
  .floor-line { stroke: #334155; stroke-width: 1; stroke-dasharray: 4 6; }
  .avatar { font-size: 80px; dominant-baseline: central; text-anchor: middle;
            transition: transform 0.3s ease-out;
            animation: idle 4s ease-in-out infinite; }
  .avatar.speaking { animation: speak 0.6s ease-in-out 2; }
  .avatar.listening { animation: listen 0.5s ease-out; }
  .agent-name { fill: var(--muted); font: 600 13px Consolas, monospace;
                text-anchor: middle; }
  .agent-name.active { fill: var(--fg); }
  .agent-role { fill: var(--muted); font: 10px Consolas, monospace;
                text-anchor: middle; opacity: 0.7; }
  @keyframes idle {
    0%, 100% { transform: translateY(0); }
    50%      { transform: translateY(-3px); }
  }
  @keyframes speak {
    0%, 100% { transform: translateY(0) scale(1); }
    50%      { transform: translateY(-10px) scale(1.06); }
  }
  @keyframes listen {
    0%   { transform: translateY(0); }
    50%  { transform: translateY(-4px) scale(1.03); }
    100% { transform: translateY(0); }
  }
  .bubble-layer, .arrow-layer { pointer-events: none; }
  .bubble { opacity: 0; transform-origin: center bottom;
            transition: opacity 0.25s ease-out, transform 0.25s ease-out; }
  .bubble.show { opacity: 1; }
  .bubble-bg { fill: var(--bubble); stroke-width: 2; }
  .bubble-bg.msg     { stroke: var(--msg); }
  .bubble-bg.assign  { stroke: var(--accent); }
  .bubble-bg.done    { stroke: var(--ok); }
  .bubble-bg.failed  { stroke: var(--err); }
  .bubble-bg.note    { fill: #fef9c3; stroke: var(--note); }
  .bubble-tail { fill: var(--bubble); }
  .bubble-tail.note { fill: #fef9c3; }
  .bubble-from { font: 600 11px Consolas, monospace; fill: var(--muted); }
  .bubble-text { font: 14px/1.3 system-ui; color: var(--bubble-fg);
                 padding: 0; margin: 0; word-wrap: break-word;
                 overflow-wrap: break-word; }
  .arrow { fill: none; stroke-width: 2; opacity: 0;
           transition: opacity 0.3s ease-out; }
  .arrow.show { opacity: 0.85; }
  .arrow.msg    { stroke: var(--msg); }
  .arrow.assign { stroke: var(--accent); }
  .arrow.done   { stroke: var(--ok); stroke-dasharray: 6 4; }
  .arrow.failed { stroke: var(--err); stroke-dasharray: 2 3; }
  .log { margin-top: 12px; background: var(--panel); border: 1px solid var(--line);
         border-radius: 6px; padding: 12px 16px; max-height: 240px; overflow-y: auto;
         font-family: Consolas, monospace; font-size: 13px; }
  .log .entry { padding: 4px 0; border-bottom: 1px dashed #273142;
                white-space: pre-wrap; }
  .log .entry:last-child { border-bottom: none; }
  .log .entry .who { color: var(--accent); font-weight: 600; }
  .log .entry .to  { color: var(--msg); }
  .log .entry .tag { display: inline-block; padding: 1px 6px; border-radius: 8px;
                     font-size: 10px; margin-right: 6px; }
  .log .entry .tag.assign { background: #1e3a8a; color: #bfdbfe; }
  .log .entry .tag.done   { background: #14532d; color: #bbf7d0; }
  .log .entry .tag.failed { background: #7f1d1d; color: #fecaca; }
  .log .entry .tag.msg    { background: #164e63; color: #a5f3fc; }
  .log .entry .tag.note   { background: #713f12; color: #fef08a; }
  .log .entry.current { background: #1e293b; margin: 0 -16px;
                        padding: 4px 16px; border-left: 3px solid var(--accent); }
  footer { margin-top: 12px; color: var(--muted); font-size: 12px; text-align: center; }
  footer a { color: var(--muted); }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>Stage — <code>{{RUN_ID}}</code></h1>
      <div class="meta">Team <code>{{TEAM}}</code> · {{EVENT_COUNT}} events</div>
    </div>
  </header>

  <div class="controls" role="toolbar" aria-label="Playback controls">
    <button id="btn-reset" title="Reset to start">⏮</button>
    <button id="btn-back" title="Step back">◂</button>
    <button id="btn-play" class="primary" title="Play / Pause">▶</button>
    <button id="btn-next" title="Step forward">▸</button>
    <button id="btn-end" title="Jump to end">⏭</button>
    <div class="sep"></div>
    <div class="group">
      speed
      <select id="speed">
        <option value="0.5">0.5×</option>
        <option value="1" selected>1×</option>
        <option value="1.5">1.5×</option>
        <option value="2">2×</option>
        <option value="3">3×</option>
      </select>
    </div>
    <div class="sep"></div>
    <label class="toggle" id="human-only-label" title="Show only peer-to-peer messages (hide task dispatches, completions, and lead coordination notes)">
      <input type="checkbox" id="human-only">
      Human only
    </label>
    <label class="toggle" id="paired-label" title="Reorder so each message's reply plays immediately after it (conversational order), instead of strict chronological order across parallel work.">
      <input type="checkbox" id="paired">
      Conversational
    </label>
    <div class="sep"></div>
    <input type="range" id="scrubber" class="scrubber" min="0" max="0" value="0" />
    <span class="progress" id="progress">0 / 0</span>
  </div>

  <div id="stage"></div>

  <div class="log" id="log"></div>

  <footer>Self-contained offline stage playback. Also see
    <a href="playback.html">playback.html</a> ·
    <a href="report.html">report.html</a></footer>
</div>

<script type="application/json" id="data">{{DATA_JSON}}</script>
<script>
(() => {
  'use strict';
  const SVG_NS = 'http://www.w3.org/2000/svg';
  const XHTML_NS = 'http://www.w3.org/1999/xhtml';
  const data = JSON.parse(document.getElementById('data').textContent);
  const agents = data.agents;
  const events = data.events;

  // Per-agent emoji + role hint. Fallback = generic person.
  const AVATAR = {
    lead:     { emoji: '🧑\u200D💼', role: 'manager' },
    backend:  { emoji: '👨\u200D💻', role: 'backend' },
    frontend: { emoji: '👩\u200D💻', role: 'frontend' },
    qa:       { emoji: '🧑\u200D🔬', role: 'qa' },
    design:   { emoji: '🧑\u200D🎨', role: 'design' },
  };
  const FALLBACK_AVATAR = { emoji: '👤', role: '' };
  const meta = (a) => AVATAR[a] || { emoji: FALLBACK_AVATAR.emoji, role: a };

  // ---- Stage layout ----
  const STAGE_W = 1320;
  const STAGE_H = 520;
  const FLOOR_Y = 420;
  const HEAD_Y  = 360;  // rough y where bubble tail should touch
  const LEFT_MARGIN = 80;
  const RIGHT_MARGIN = 80;
  const span = STAGE_W - LEFT_MARGIN - RIGHT_MARGIN;
  const n = Math.max(1, agents.length);
  const positions = {};
  agents.forEach((a, i) => {
    const x = LEFT_MARGIN + (n === 1 ? span/2 : (span * i / (n - 1)));
    positions[a] = { x, headY: HEAD_Y, footY: FLOOR_Y };
  });
  const posOf = (a) => positions[a] || {
    x: STAGE_W - RIGHT_MARGIN / 2, headY: HEAD_Y, footY: FLOOR_Y
  };

  // ---- Build the stage SVG ----
  const stageDiv = document.getElementById('stage');
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${STAGE_W} ${STAGE_H}`);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

  // Arrow markers
  const defs = document.createElementNS(SVG_NS, 'defs');
  const mk = (id, color) => `
    <marker id="${id}" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${color}"/>
    </marker>`;
  defs.innerHTML =
    mk('mkMsg',    '#22d3ee') +
    mk('mkAssign', '#60a5fa') +
    mk('mkDone',   '#4ade80') +
    mk('mkFailed', '#f87171');
  svg.appendChild(defs);

  // Floor
  const floor = document.createElementNS(SVG_NS, 'rect');
  floor.setAttribute('x', 0);
  floor.setAttribute('y', FLOOR_Y + 40);
  floor.setAttribute('width', STAGE_W);
  floor.setAttribute('height', STAGE_H - (FLOOR_Y + 40));
  floor.setAttribute('class', 'floor');
  svg.appendChild(floor);

  const floorLine = document.createElementNS(SVG_NS, 'line');
  floorLine.setAttribute('x1', 20);
  floorLine.setAttribute('x2', STAGE_W - 20);
  floorLine.setAttribute('y1', FLOOR_Y + 40);
  floorLine.setAttribute('y2', FLOOR_Y + 40);
  floorLine.setAttribute('class', 'floor-line');
  svg.appendChild(floorLine);

  // Avatars (the cast)
  const avatarEls = {};
  const nameEls = {};
  agents.forEach((a) => {
    const p = posOf(a);
    const m = meta(a);
    const g = document.createElementNS(SVG_NS, 'g');
    g.setAttribute('transform', `translate(${p.x}, ${p.footY})`);
    g.setAttribute('data-agent', a);

    const avatar = document.createElementNS(SVG_NS, 'text');
    avatar.setAttribute('class', 'avatar');
    avatar.setAttribute('x', 0);
    avatar.setAttribute('y', -10);
    avatar.textContent = m.emoji;
    g.appendChild(avatar);

    const name = document.createElementNS(SVG_NS, 'text');
    name.setAttribute('class', 'agent-name');
    name.setAttribute('x', 0);
    name.setAttribute('y', 64);
    name.textContent = a;
    g.appendChild(name);

    if (m.role) {
      const role = document.createElementNS(SVG_NS, 'text');
      role.setAttribute('class', 'agent-role');
      role.setAttribute('x', 0);
      role.setAttribute('y', 80);
      role.textContent = m.role;
      g.appendChild(role);
    }

    svg.appendChild(g);
    avatarEls[a] = avatar;
    nameEls[a] = name;

    // Stagger idle animations so the cast doesn't bob in unison
    const stagger = (Math.abs(a.charCodeAt(0) + a.length) % 4) * 0.5;
    avatar.style.animationDelay = stagger + 's';
  });

  // Arrow layer (under bubbles) and bubble layer
  const arrowLayer = document.createElementNS(SVG_NS, 'g');
  arrowLayer.setAttribute('class', 'arrow-layer');
  svg.appendChild(arrowLayer);
  const bubbleLayer = document.createElementNS(SVG_NS, 'g');
  bubbleLayer.setAttribute('class', 'bubble-layer');
  svg.appendChild(bubbleLayer);

  stageDiv.appendChild(svg);

  // ---- Bubble + arrow renderers ----
  let currentBubble = null;
  let currentArrow = null;
  let reactionTimer = null;

  function clearStageFX() {
    if (currentBubble) { currentBubble.remove(); currentBubble = null; }
    if (currentArrow)  { currentArrow.remove();  currentArrow = null; }
    if (reactionTimer) { clearTimeout(reactionTimer); reactionTimer = null; }
    // Remove lingering CSS animation classes
    Object.values(avatarEls).forEach(a => {
      a.classList.remove('speaking');
      a.classList.remove('listening');
    });
    Object.entries(nameEls).forEach(([k, el]) => el.classList.remove('active'));
  }

  function drawBubble(who, text, kind) {
    const p = posOf(who);
    // Bubble sizing: width scales with text until 520px, then we wrap.
    // Height is derived from the estimated wrapped row count.
    const len = text.length;
    const W = Math.min(520, Math.max(180, len * 6.8 + 36));
    const approxCharsPerRow = Math.max(18, Math.floor((W - 28) / 7.2));
    const rows = Math.max(1, Math.ceil(len / approxCharsPerRow));
    const H = Math.min(240, 44 + rows * 20);
    const cx = p.x;
    // Anchor the bubble BOTTOM ~30px above the head so the tail tip
    // sits just above it regardless of how tall the bubble grows.
    const baseY = p.headY - 30;
    // Clamp x so bubble doesn't run off either edge
    const minCx = W / 2 + 12;
    const maxCx = STAGE_W - W / 2 - 12;
    const anchorX = Math.max(minCx, Math.min(maxCx, cx));

    const g = document.createElementNS(SVG_NS, 'g');
    g.setAttribute('class', 'bubble');
    g.setAttribute('transform', `translate(${anchorX}, ${baseY})`);

    const rect = document.createElementNS(SVG_NS, 'rect');
    rect.setAttribute('x', -W / 2);
    rect.setAttribute('y', -H);
    rect.setAttribute('width', W);
    rect.setAttribute('height', H);
    rect.setAttribute('rx', 12);
    rect.setAttribute('class', 'bubble-bg ' + kind);
    g.appendChild(rect);

    // Tail points from bubble down to speaker's head
    const tailBaseX = Math.max(-W / 2 + 14,
                               Math.min(W / 2 - 14, cx - anchorX));
    const tailPath = document.createElementNS(SVG_NS, 'polygon');
    tailPath.setAttribute('points',
      `${tailBaseX - 9},0 ${tailBaseX + 9},0 ${tailBaseX},22`);
    tailPath.setAttribute('class', 'bubble-tail ' + (kind === 'note' ? 'note' : ''));
    g.appendChild(tailPath);

    // Tail outline: two short lines to fake a border on just the sides of the tail
    const leftLine = document.createElementNS(SVG_NS, 'line');
    leftLine.setAttribute('x1', tailBaseX - 9);
    leftLine.setAttribute('y1', 0);
    leftLine.setAttribute('x2', tailBaseX);
    leftLine.setAttribute('y2', 22);
    leftLine.setAttribute('stroke', rect.style.stroke || '');
    g.appendChild(leftLine);

    // Sender tag (small "from:" label inside the bubble)
    const from = document.createElementNS(SVG_NS, 'text');
    from.setAttribute('class', 'bubble-from');
    from.setAttribute('x', -W / 2 + 10);
    from.setAttribute('y', -H + 14);
    from.textContent = who;
    g.appendChild(from);

    // Body text via foreignObject so it wraps
    const fo = document.createElementNS(SVG_NS, 'foreignObject');
    fo.setAttribute('x', -W / 2 + 10);
    fo.setAttribute('y', -H + 18);
    fo.setAttribute('width', W - 20);
    fo.setAttribute('height', H - 22);
    const body = document.createElementNS(XHTML_NS, 'div');
    body.setAttribute('class', 'bubble-text');
    body.textContent = text;
    fo.appendChild(body);
    g.appendChild(fo);

    bubbleLayer.appendChild(g);
    // Trigger CSS transition
    requestAnimationFrame(() => g.classList.add('show'));
    return g;
  }

  function drawArrow(from, to, kind) {
    if (!from || !to || from === to) return null;
    const a = posOf(from);
    const b = posOf(to);
    // Curve upward over the heads
    const midX = (a.x + b.x) / 2;
    const midY = Math.min(a.headY, b.headY) - 70;
    const dir = b.x >= a.x ? 1 : -1;
    const startX = a.x + 32 * dir;
    const endX   = b.x - 28 * dir;
    const startY = a.headY - 20;
    const endY   = b.headY - 20;
    const path = document.createElementNS(SVG_NS, 'path');
    path.setAttribute('d',
      `M ${startX} ${startY} Q ${midX} ${midY} ${endX} ${endY}`);
    path.setAttribute('class', 'arrow ' + kind);
    const marker =
      kind === 'done'   ? 'mkDone' :
      kind === 'failed' ? 'mkFailed' :
      kind === 'assign' ? 'mkAssign' : 'mkMsg';
    path.setAttribute('marker-end', `url(#${marker})`);
    arrowLayer.appendChild(path);
    requestAnimationFrame(() => path.classList.add('show'));
    return path;
  }

  function reactSpeaker(who) {
    const a = avatarEls[who];
    if (!a) return;
    a.classList.remove('speaking');
    // force reflow so the animation restarts
    void a.getBoundingClientRect();
    a.classList.add('speaking');
    if (nameEls[who]) nameEls[who].classList.add('active');
  }
  function reactListener(who) {
    const a = avatarEls[who];
    if (!a) return;
    a.classList.remove('listening');
    void a.getBoundingClientRect();
    a.classList.add('listening');
    if (nameEls[who]) nameEls[who].classList.add('active');
  }

  function renderEvent(e) {
    if (!e) return;
    const kind = e.kind;
    const body = (e.full && e.full.length > 0) ? e.full : (e.label || '');
    if (kind === 'note') {
      currentBubble = drawBubble(e.who, body, 'note');
      reactSpeaker(e.who);
    } else {
      currentBubble = drawBubble(e.from, body, kind);
      currentArrow = drawArrow(e.from, e.to, kind);
      reactSpeaker(e.from);
      reactionTimer = setTimeout(() => reactListener(e.to), 350);
    }
  }

  // ---- Filter: "Human only" keeps only peer-to-peer `msg` events. ----
  let visibleEvents = events.slice();
  let logEntries = [];

  function buildLogEntries() {
    logEntries = visibleEvents.map((e, i) => {
      const div = document.createElement('div');
      div.className = 'entry';
      div.dataset.idx = String(i);
      const tag = document.createElement('span');
      tag.className = 'tag ' + e.kind;
      tag.textContent = e.kind;
      div.appendChild(tag);
      const who = document.createElement('span');
      who.className = 'who';
      who.textContent = e.kind === 'note' ? (e.who || '?') : (e.from || '?');
      div.appendChild(who);
      const sep = document.createElement('span');
      if (e.kind === 'note') {
        sep.textContent = ' · ';
        div.appendChild(sep);
      } else {
        sep.textContent = ' → ';
        const to = document.createElement('span');
        to.className = 'to';
        to.textContent = e.to || '?';
        div.appendChild(sep);
        div.appendChild(to);
        const colon = document.createElement('span');
        colon.textContent = ': ';
        div.appendChild(colon);
      }
      const body = document.createElement('span');
      body.textContent = (e.full && e.full.length > 0) ? e.full : (e.label || '');
      div.appendChild(body);
      return div;
    });
  }

  // ---- Subtitle log ----
  const logEl = document.getElementById('log');

  function renderLog(upTo) {
    // upTo = index of last visible entry in `visibleEvents`; -1 = empty
    logEl.innerHTML = '';
    for (let i = 0; i <= upTo; i++) {
      const entry = logEntries[i];
      if (!entry) continue;
      entry.classList.toggle('current', i === upTo);
      logEl.appendChild(entry);
    }
    if (upTo >= 0 && logEntries[upTo]) {
      logEntries[upTo].scrollIntoView({block: 'nearest', behavior: 'smooth'});
    }
  }

  // ---- Playback controls ----
  let idx = -1;
  let playing = false;
  let timer = null;
  const BASE_DELAY = 2000; // ms/event at 1x
  const speedEl = document.getElementById('speed');
  const scrubEl = document.getElementById('scrubber');
  const progEl  = document.getElementById('progress');
  const playBtn = document.getElementById('btn-play');
  const backBtn = document.getElementById('btn-back');
  const nextBtn = document.getElementById('btn-next');
  const humanEl = document.getElementById('human-only');
  const humanLabel = document.getElementById('human-only-label');
  const pairedEl = document.getElementById('paired');
  const pairedLabel = document.getElementById('paired-label');

  const delay = () => BASE_DELAY / parseFloat(speedEl.value || '1');

  function updateProgress() {
    const n = idx + 1;
    progEl.textContent = n + ' / ' + visibleEvents.length;
    scrubEl.value = String(n);
    backBtn.disabled = idx < 0;
    nextBtn.disabled = idx >= visibleEvents.length - 1;
  }
  function setTo(i) {
    idx = Math.max(-1, Math.min(visibleEvents.length - 1, i));
    clearStageFX();
    if (idx >= 0) renderEvent(visibleEvents[idx]);
    renderLog(idx);
    updateProgress();
  }
  function stepNext() {
    if (idx >= visibleEvents.length - 1) { pause(); return; }
    setTo(idx + 1);
  }
  function stepBack() {
    if (idx < 0) return;
    setTo(idx - 1);
  }
  function play() {
    if (idx >= visibleEvents.length - 1) setTo(-1);
    playing = true;
    playBtn.textContent = '⏸';
    const tick = () => {
      stepNext();
      if (playing && idx < visibleEvents.length - 1) {
        timer = setTimeout(tick, delay());
      } else {
        pause();
      }
    };
    stepNext();
    if (playing && idx < visibleEvents.length - 1) {
      timer = setTimeout(tick, delay());
    } else {
      pause();
    }
  }
  function pause() {
    playing = false;
    playBtn.textContent = '▶';
    if (timer) { clearTimeout(timer); timer = null; }
  }

  // Reorder events so each message-question is followed by its reply and each
  // task dispatch is followed by its completion. Unpaired events keep their
  // relative order. Greedy — an A→B message pairs with the NEXT unpaired B→A
  // message; an assign pairs with the next unpaired done mentioning the same
  // task_id. Broadcasts (one-way messages with no reply) stay in place.
  function pairEvents(src) {
    const taken = new Set();
    const out = [];
    const taskIdRe = /\b(t_\d+)\b/;
    const taskIdOf = (e) => {
      const m = taskIdRe.exec(e.label || '');
      return m ? m[1] : null;
    };
    function findReply(i) {
      const e = src[i];
      if (e.kind === 'msg') {
        for (let j = i + 1; j < src.length; j++) {
          if (taken.has(j)) continue;
          const f = src[j];
          if (f.kind === 'msg' && f.from === e.to && f.to === e.from) return j;
        }
      } else if (e.kind === 'assign') {
        const tid = taskIdOf(e);
        if (!tid) return -1;
        for (let j = i + 1; j < src.length; j++) {
          if (taken.has(j)) continue;
          const f = src[j];
          if ((f.kind === 'done' || f.kind === 'failed') && taskIdOf(f) === tid) return j;
        }
      }
      return -1;
    }
    for (let i = 0; i < src.length; i++) {
      if (taken.has(i)) continue;
      out.push(src[i]);
      taken.add(i);
      const r = findReply(i);
      if (r !== -1) {
        out.push(src[r]);
        taken.add(r);
      }
    }
    return out;
  }

  function rebuildVisible() {
    pause();
    const humanOnly = !!(humanEl && humanEl.checked);
    const paired    = !!(pairedEl && pairedEl.checked);
    let pool = humanOnly
      ? events.filter(e => e.kind === 'msg')
      : events.slice();
    if (paired) pool = pairEvents(pool);
    visibleEvents = pool;
    buildLogEntries();
    scrubEl.max = String(visibleEvents.length);
    if (humanLabel) humanLabel.classList.toggle('on', humanOnly);
    if (pairedLabel) pairedLabel.classList.toggle('on', paired);
    setTo(-1);
  }

  playBtn.addEventListener('click',     () => playing ? pause() : play());
  nextBtn.addEventListener('click',     () => { pause(); stepNext(); });
  backBtn.addEventListener('click',     () => { pause(); stepBack(); });
  document.getElementById('btn-reset').addEventListener('click',
    () => { pause(); setTo(-1); });
  document.getElementById('btn-end').addEventListener('click',
    () => { pause(); setTo(visibleEvents.length - 1); });
  scrubEl.addEventListener('input', (ev) => {
    pause();
    setTo(parseInt(ev.target.value, 10) - 1);
  });
  if (humanEl) humanEl.addEventListener('change', rebuildVisible);
  if (pairedEl) pairedEl.addEventListener('change', rebuildVisible);
  document.addEventListener('keydown', (ev) => {
    if (ev.target && /INPUT|SELECT|TEXTAREA/.test(ev.target.tagName)) return;
    if (ev.key === ' ' || ev.key === 'Enter') { ev.preventDefault(); playing ? pause() : play(); }
    else if (ev.key === 'ArrowRight') { ev.preventDefault(); pause(); stepNext(); }
    else if (ev.key === 'ArrowLeft')  { ev.preventDefault(); pause(); stepBack(); }
    else if (ev.key === 'Home')       { ev.preventDefault(); pause(); setTo(-1); }
    else if (ev.key === 'End')        { ev.preventDefault(); pause(); setTo(visibleEvents.length - 1); }
  });

  rebuildVisible();
})();
</script>
</body>
</html>
"""


_PLAYBACK_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{{TITLE}}</title>
<style>
  :root {
    --bg: #f8fafc; --fg: #0f172a; --muted: #64748b; --line: #e2e8f0;
    --accent: #2563eb; --ok: #16a34a; --warn: #f97316; --err: #dc2626;
    --lane: #cbd5e1; --bubble: #ffffff; --note: #fef9c3;
  }
  * { box-sizing: border-box; }
  body { font: 14px/1.4 -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;
         color: var(--fg); background: var(--bg); margin: 0; }
  .wrap { max-width: 1500px; margin: 16px auto; padding: 0 16px; }
  header { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; }
  header h1 { font-size: 20px; margin: 0 0 4px; }
  header .meta { color: var(--muted); font-size: 13px; }
  header .meta code { background: #fff; padding: 1px 6px; border-radius: 3px;
                      border: 1px solid var(--line); }
  .controls { display: flex; gap: 8px; align-items: center; padding: 8px 12px;
              background: #fff; border: 1px solid var(--line); border-radius: 6px;
              margin: 12px 0; position: sticky; top: 8px; z-index: 10;
              box-shadow: 0 1px 2px rgba(15,23,42,0.04); }
  .controls button { font: 14px/1 system-ui; padding: 6px 10px; cursor: pointer;
                     background: #fff; border: 1px solid var(--line); border-radius: 4px;
                     min-width: 36px; }
  .controls button:hover { background: #f1f5f9; }
  .controls button.primary { background: var(--accent); color: white;
                             border-color: var(--accent); }
  .controls button.primary:hover { background: #1d4ed8; }
  .controls button:disabled { opacity: 0.4; cursor: not-allowed; }
  .controls .sep { width: 1px; height: 20px; background: var(--line); margin: 0 4px; }
  .controls .group { display: flex; align-items: center; gap: 6px; color: var(--muted);
                     font-size: 12px; }
  .controls select { font: 13px system-ui; padding: 4px 6px; border: 1px solid var(--line);
                     border-radius: 4px; background: #fff; }
  .controls .scrubber { flex: 1; min-width: 120px; accent-color: var(--accent); }
  .controls .progress { font-family: Consolas, monospace; font-size: 12px; color: var(--fg);
                        min-width: 60px; text-align: right; }
  #stage { background: #fff; border: 1px solid var(--line); border-radius: 6px;
           overflow: hidden; }
  #stage svg { display: block; width: 100%; height: auto; }
  .lane-label { font: 600 13px Consolas, monospace; fill: var(--fg); }
  .lane-sublabel { font: 11px Consolas, monospace; fill: var(--muted); }
  .lane-line { stroke: var(--lane); stroke-width: 1; stroke-dasharray: 2 4; }
  .event { transition: opacity 0.4s ease-out; }
  .event.hidden { opacity: 0; }
  .event.visible { opacity: 1; }
  .event.current .bubble-bg, .event.current .note-bg { stroke-width: 2; }
  .arrow { fill: none; stroke-linecap: round; stroke-width: 2; }
  .arrow.solid { stroke: var(--accent); }
  .arrow.dashed { stroke: var(--ok); stroke-dasharray: 6 4; }
  .arrow.failed { stroke: var(--err); stroke-dasharray: 2 3; }
  .arrow.msg { stroke: #0891b2; }
  .bubble-bg { fill: var(--bubble); stroke: var(--line); }
  .bubble-bg.msg { stroke: #0891b2; }
  .bubble-bg.assign { stroke: var(--accent); }
  .bubble-bg.done { stroke: var(--ok); }
  .bubble-bg.failed { stroke: var(--err); }
  .bubble-text { font: 12px system-ui; fill: var(--fg); }
  .note-bg { fill: var(--note); stroke: #ca8a04; }
  .note-text { font: 12px/1.2 system-ui; fill: #713f12; }
  .sender-tag { font: 10px Consolas, monospace; fill: var(--muted); }
  .now-line { stroke: var(--warn); stroke-width: 2; }
  footer { margin-top: 12px; color: var(--muted); font-size: 12px; text-align: center; }
  footer a { color: var(--muted); }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>Playback — <code>{{RUN_ID}}</code></h1>
      <div class="meta">Team <code>{{TEAM}}</code> · {{EVENT_COUNT}} events</div>
    </div>
  </header>

  <div class="controls" role="toolbar" aria-label="Playback controls">
    <button id="btn-reset" title="Reset to start">⏮</button>
    <button id="btn-back" title="Step back">◂</button>
    <button id="btn-play" class="primary" title="Play / Pause">▶</button>
    <button id="btn-next" title="Step forward">▸</button>
    <button id="btn-end" title="Jump to end">⏭</button>
    <div class="sep"></div>
    <div class="group">
      speed
      <select id="speed">
        <option value="0.25">0.25×</option>
        <option value="0.5">0.5×</option>
        <option value="1" selected>1×</option>
        <option value="2">2×</option>
        <option value="4">4×</option>
      </select>
    </div>
    <div class="sep"></div>
    <input type="range" id="scrubber" class="scrubber" min="0" max="0" value="0" />
    <span class="progress" id="progress">0 / 0</span>
  </div>

  <div id="stage"></div>
  <footer>Self-contained offline playback. Also see
    <a href="report.html">report.html</a> ·
    <a href="sequence.md">sequence.md</a></footer>
</div>

<script type="application/json" id="data">{{DATA_JSON}}</script>
<script>
(() => {
  'use strict';
  const SVG_NS = 'http://www.w3.org/2000/svg';
  const data = JSON.parse(document.getElementById('data').textContent);
  const agents = data.agents;
  const events = data.events;

  // Layout
  const COL_W = 210;
  const LEFT_PAD = 32;
  const RIGHT_PAD = 32;
  const TOP_PAD = 56;
  const BOTTOM_PAD = 32;
  const ROW_H = 58;

  const svgW = LEFT_PAD + RIGHT_PAD + Math.max(1, agents.length) * COL_W;
  const svgH = TOP_PAD + Math.max(1, events.length) * ROW_H + BOTTOM_PAD;

  const xForAgent = (name) => {
    const i = agents.indexOf(name);
    const idx = i < 0 ? agents.length : i;
    return LEFT_PAD + idx * COL_W + COL_W / 2;
  };
  const yForEvent = (i) => TOP_PAD + i * ROW_H + ROW_H / 2;

  const stage = document.getElementById('stage');
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${svgW} ${svgH}`);
  svg.setAttribute('width', svgW);
  svg.setAttribute('preserveAspectRatio', 'xMinYMin meet');

  // Arrow markers
  const defs = document.createElementNS(SVG_NS, 'defs');
  const mk = (id, color) => `
    <marker id="${id}" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="${color}"/>
    </marker>`;
  defs.innerHTML =
    mk('mk-blue',  '#2563eb') +
    mk('mk-green', '#16a34a') +
    mk('mk-red',   '#dc2626') +
    mk('mk-cyan',  '#0891b2');
  svg.appendChild(defs);

  // Lane labels + vertical lifelines
  agents.forEach((a) => {
    const x = xForAgent(a);
    const label = document.createElementNS(SVG_NS, 'text');
    label.setAttribute('x', x);
    label.setAttribute('y', 28);
    label.setAttribute('text-anchor', 'middle');
    label.setAttribute('class', 'lane-label');
    label.textContent = a;
    svg.appendChild(label);

    const line = document.createElementNS(SVG_NS, 'line');
    line.setAttribute('x1', x);
    line.setAttribute('y1', 40);
    line.setAttribute('x2', x);
    line.setAttribute('y2', svgH - BOTTOM_PAD);
    line.setAttribute('class', 'lane-line');
    svg.appendChild(line);
  });

  // Now-line (sweeps down as playback advances)
  const nowLine = document.createElementNS(SVG_NS, 'line');
  nowLine.setAttribute('x1', LEFT_PAD);
  nowLine.setAttribute('x2', svgW - RIGHT_PAD);
  nowLine.setAttribute('y1', TOP_PAD - 8);
  nowLine.setAttribute('y2', TOP_PAD - 8);
  nowLine.setAttribute('class', 'now-line');
  nowLine.setAttribute('opacity', '0');
  svg.appendChild(nowLine);

  // Pre-render every event element (hidden initially)
  const elements = events.map((e, i) => {
    const g = document.createElementNS(SVG_NS, 'g');
    g.setAttribute('class', 'event hidden');
    g.setAttribute('data-idx', String(i));

    const y = yForEvent(i);

    if (e.kind === 'note') {
      const who = e.who || 'lead';
      const x = xForAgent(who);
      const text = e.label || '';
      const width = Math.min(COL_W - 20, Math.max(120, text.length * 6.5 + 20));
      const height = 26;
      const rect = document.createElementNS(SVG_NS, 'rect');
      rect.setAttribute('x', x - width / 2);
      rect.setAttribute('y', y - height / 2);
      rect.setAttribute('width', width);
      rect.setAttribute('height', height);
      rect.setAttribute('rx', 4);
      rect.setAttribute('class', 'note-bg');
      g.appendChild(rect);

      const t = document.createElementNS(SVG_NS, 'text');
      t.setAttribute('x', x);
      t.setAttribute('y', y + 4);
      t.setAttribute('text-anchor', 'middle');
      t.setAttribute('class', 'note-text');
      t.textContent = text;
      g.appendChild(t);

      const full = document.createElementNS(SVG_NS, 'title');
      full.textContent = text;
      g.appendChild(full);
    } else {
      const x1 = xForAgent(e.from);
      const x2 = xForAgent(e.to);
      const arrowCls =
        e.kind === 'done' ? 'arrow dashed' :
        e.kind === 'failed' ? 'arrow failed' :
        e.kind === 'msg' ? 'arrow msg' : 'arrow solid';
      const marker =
        e.kind === 'done' ? 'mk-green' :
        e.kind === 'failed' ? 'mk-red' :
        e.kind === 'msg' ? 'mk-cyan' : 'mk-blue';

      // Arrow path. Slight vertical offset at src/dst so a later bubble
      // below doesn't sit on the line.
      const path = document.createElementNS(SVG_NS, 'path');
      const dir = x2 > x1 ? 1 : -1;
      const pad = 8 * dir;
      path.setAttribute('d', `M ${x1 + pad} ${y} L ${x2 - pad} ${y}`);
      path.setAttribute('class', arrowCls);
      path.setAttribute('marker-end', `url(#${marker})`);
      path.setAttribute('pathLength', '100');
      if (e.kind === 'done') {
        // keep dashed look, but still animate via dashoffset on a wrapper
        path.setAttribute('stroke-dasharray', '6 4');
      } else if (e.kind === 'failed') {
        path.setAttribute('stroke-dasharray', '2 3');
      } else {
        path.setAttribute('stroke-dasharray', '100');
        path.setAttribute('stroke-dashoffset', '100');
        path.style.transition = 'stroke-dashoffset 0.45s ease-out';
      }
      g.appendChild(path);

      // Bubble with truncated label above the arrow
      const label = (e.label || '').slice(0, 110);
      if (label) {
        const midX = (x1 + x2) / 2;
        const bubbleY = y - 18;
        const w = Math.min(Math.abs(x2 - x1) - 30, label.length * 6.2 + 16);
        const bw = Math.max(60, w);
        const h = 18;
        const rect = document.createElementNS(SVG_NS, 'rect');
        rect.setAttribute('x', midX - bw / 2);
        rect.setAttribute('y', bubbleY - h / 2);
        rect.setAttribute('width', bw);
        rect.setAttribute('height', h);
        rect.setAttribute('rx', 3);
        rect.setAttribute('class', 'bubble-bg ' + (e.kind || 'msg'));
        g.appendChild(rect);

        const t = document.createElementNS(SVG_NS, 'text');
        t.setAttribute('x', midX);
        t.setAttribute('y', bubbleY + 4);
        t.setAttribute('text-anchor', 'middle');
        t.setAttribute('class', 'bubble-text');
        t.textContent = label;
        g.appendChild(t);
      }

      const full = document.createElementNS(SVG_NS, 'title');
      full.textContent =
        (e.from || '?') + ' → ' + (e.to || '?') + ' [' + e.kind + ']\n' +
        (e.label || '');
      g.appendChild(full);
    }

    svg.appendChild(g);
    return g;
  });

  stage.appendChild(svg);

  // Playback state
  let idx = -1;                 // index of the last revealed event; -1 = nothing
  let playing = false;
  let timer = null;
  const BASE_DELAY = 850;       // ms/event at 1x
  const speedEl = document.getElementById('speed');
  const scrubEl = document.getElementById('scrubber');
  const progEl  = document.getElementById('progress');
  const playBtn = document.getElementById('btn-play');
  const backBtn = document.getElementById('btn-back');
  const nextBtn = document.getElementById('btn-next');
  const resetBtn = document.getElementById('btn-reset');
  const endBtn = document.getElementById('btn-end');
  scrubEl.max = String(events.length);

  const delay = () => BASE_DELAY / parseFloat(speedEl.value || '1');

  function reveal(i, instant) {
    const g = elements[i];
    if (!g) return;
    g.classList.remove('hidden');
    g.classList.add('visible');
    const path = g.querySelector('path');
    const dashed = path && path.getAttribute('stroke-dasharray') === '100';
    if (dashed) {
      if (instant) {
        path.style.transition = 'none';
        path.setAttribute('stroke-dashoffset', '0');
        // Re-enable transition for next time
        void path.getBoundingClientRect();
        path.style.transition = 'stroke-dashoffset 0.45s ease-out';
      } else {
        requestAnimationFrame(() =>
          path.setAttribute('stroke-dashoffset', '0'));
      }
    }
  }
  function hide(i) {
    const g = elements[i];
    if (!g) return;
    g.classList.remove('visible');
    g.classList.add('hidden');
    const path = g.querySelector('path');
    if (path && path.getAttribute('stroke-dasharray') === '100') {
      path.style.transition = 'none';
      path.setAttribute('stroke-dashoffset', '100');
      void path.getBoundingClientRect();
      path.style.transition = 'stroke-dashoffset 0.45s ease-out';
    }
  }

  function markCurrent() {
    elements.forEach((g, i) => {
      if (i === idx) g.classList.add('current');
      else g.classList.remove('current');
    });
    if (idx >= 0) {
      nowLine.setAttribute('opacity', '0.6');
      const y = yForEvent(idx);
      nowLine.setAttribute('y1', y);
      nowLine.setAttribute('y2', y);
      // Auto-scroll the element into view when we've passed below the fold
      const g = elements[idx];
      if (g && g.scrollIntoView) {
        const r = g.getBoundingClientRect();
        const inView = r.top >= 100 && r.bottom <= window.innerHeight - 20;
        if (!inView) g.scrollIntoView({block: 'center', behavior: 'smooth'});
      }
    } else {
      nowLine.setAttribute('opacity', '0');
    }
  }
  function updateProgress() {
    const n = idx + 1;
    progEl.textContent = n + ' / ' + events.length;
    scrubEl.value = String(n);
    backBtn.disabled = idx < 0;
    nextBtn.disabled = idx >= events.length - 1;
  }
  function setTo(n, instant) {
    // n = number of events revealed (0..events.length)
    const target = n - 1;
    if (target > idx) {
      for (let i = idx + 1; i <= target; i++) reveal(i, instant);
    } else if (target < idx) {
      for (let i = idx; i > target; i--) hide(i);
    }
    idx = target;
    markCurrent();
    updateProgress();
  }
  function stepNext() {
    if (idx >= events.length - 1) { pause(); return; }
    idx++;
    reveal(idx, false);
    markCurrent();
    updateProgress();
  }
  function stepBack() {
    if (idx < 0) return;
    hide(idx);
    idx--;
    markCurrent();
    updateProgress();
  }
  function play() {
    if (idx >= events.length - 1) setTo(0, true);
    playing = true;
    playBtn.textContent = '⏸';
    const tick = () => {
      stepNext();
      if (playing && idx < events.length - 1) {
        timer = setTimeout(tick, delay());
      } else {
        pause();
      }
    };
    timer = setTimeout(tick, delay());
  }
  function pause() {
    playing = false;
    playBtn.textContent = '▶';
    if (timer) { clearTimeout(timer); timer = null; }
  }

  playBtn.addEventListener('click', () => playing ? pause() : play());
  nextBtn.addEventListener('click', () => { pause(); stepNext(); });
  backBtn.addEventListener('click', () => { pause(); stepBack(); });
  resetBtn.addEventListener('click', () => { pause(); setTo(0, true); });
  endBtn.addEventListener('click',   () => { pause(); setTo(events.length, true); });
  scrubEl.addEventListener('input', (ev) => {
    pause(); setTo(parseInt(ev.target.value, 10), true);
  });
  document.addEventListener('keydown', (ev) => {
    if (ev.target && /INPUT|SELECT|TEXTAREA/.test(ev.target.tagName)) return;
    if (ev.key === ' ' || ev.key === 'Enter') { ev.preventDefault(); playing ? pause() : play(); }
    else if (ev.key === 'ArrowRight') { ev.preventDefault(); pause(); stepNext(); }
    else if (ev.key === 'ArrowLeft')  { ev.preventDefault(); pause(); stepBack(); }
    else if (ev.key === 'Home')       { ev.preventDefault(); pause(); setTo(0, true); }
    else if (ev.key === 'End')        { ev.preventDefault(); pause(); setTo(events.length, true); }
  });

  updateProgress();
  markCurrent();
})();
</script>
</body>
</html>
"""


def _md_timeline(data: ReportData) -> str:
    if not data.spans:
        return "## Timeline\n\n_No dispatch activity recorded._"
    # Mermaid gantt groups by section. Group by agent in config order.
    by_agent: dict[str, list[Span]] = defaultdict(list)
    for s in data.spans:
        by_agent[s.agent].append(s)

    lines = ["## Timeline", "",
             "_Tool-use tick marks are omitted in the markdown view — see"
             " [report.html](report.html) for the high-resolution timeline._",
             "",
             "```mermaid",
             "gantt",
             "    title Dispatches by agent",
             "    dateFormat X",  # Unix seconds
             "    axisFormat %S s"]
    for agent in data.agents:
        spans = by_agent.get(agent, [])
        if not spans:
            continue
        lines.append(f"    section {agent}")
        for i, s in enumerate(spans):
            start = int(s.start_ts.timestamp()) if data.run_start else 0
            end = int((s.end_ts or s.start_ts).timestamp())
            duration = max(1, end - start)
            label_bits = [s.kind]
            if s.task_id:
                label_bits.append(s.task_id)
            status_marker = "crit" if (s.error or s.timed_out) else "active" if s.kind == "turn" else "done"
            label = " ".join(label_bits).replace(":", "-")[:48]
            lines.append(f"    {label} :{status_marker}, {agent}_{i}, {start}, {duration}s")
    lines.append("```")
    return "\n".join(lines)


def _md_task_dag(data: ReportData) -> str:
    if not data.tasks:
        return "## Task graph\n\n_No tasks on the board._"
    lines = ["## Task graph", "", "```mermaid", "graph TD"]
    for t in data.tasks:
        short = t.title[:40].replace('"', "'")
        lines.append(f'    {t.task_id}["{t.task_id} ({t.status})<br/>{short}"]')
    for t in data.tasks:
        for dep in t.dependencies:
            lines.append(f"    {dep} --> {t.task_id}")
    # Styling by status.
    lines.append("    classDef completed fill:#dcfce7,stroke:#166534;")
    lines.append("    classDef failed fill:#fee2e2,stroke:#991b1b;")
    lines.append("    classDef in_progress fill:#fef3c7,stroke:#92400e;")
    lines.append("    classDef assigned fill:#e0e7ff,stroke:#3730a3;")
    by_status: dict[str, list[str]] = defaultdict(list)
    for t in data.tasks:
        by_status[t.status].append(t.task_id)
    for status, ids in by_status.items():
        if status in {"completed", "failed", "in_progress", "assigned"}:
            lines.append(f"    class {','.join(ids)} {status};")
    lines.append("```")
    return "\n".join(lines)


def _md_costs(data: ReportData) -> str:
    if not data.cost.per_agent:
        return "## Per-agent costs\n\n_No cost data recorded._"
    lines = ["## Per-agent costs", "",
             "| agent | turns | cost | input | output | cache_r | cache_w |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for agent in sorted(data.cost.per_agent):
        c = data.cost.per_agent[agent]
        lines.append(
            f"| `{agent}` | {c.turns} | ${c.cost_usd:.4f} | "
            f"{c.input_tokens} | {c.output_tokens} | {c.cache_read} | {c.cache_write} |"
        )
    t = data.cost.totals()
    lines.append(
        f"| **TOTAL** | {t.turns} | **${t.cost_usd:.4f}** | "
        f"{t.input_tokens} | {t.output_tokens} | {t.cache_read} | {t.cache_write} |"
    )
    return "\n".join(lines)


def _md_tool_tally(data: ReportData) -> str:
    tool_counts: dict[str, Counter] = defaultdict(Counter)
    for s in data.spans:
        for tu in s.tool_uses:
            tool_counts[s.agent][tu["name"]] += 1
    if not any(tool_counts.values()):
        return ""
    # Pick top 8 tools globally for compact table; aggregate the rest.
    global_counts: Counter = Counter()
    for c in tool_counts.values():
        global_counts.update(c)
    top_tools = [n for n, _ in global_counts.most_common(8)]
    lines = ["## Tool-use tally", "",
             "| agent | " + " | ".join(_short_tool(n) for n in top_tools) + " | other |",
             "|---|" + "|".join(["---:"] * (len(top_tools) + 1)) + "|"]
    for agent in data.agents:
        c = tool_counts.get(agent, Counter())
        cells = [str(c.get(n, 0)) for n in top_tools]
        other = sum(v for n, v in c.items() if n not in top_tools)
        cells.append(str(other))
        lines.append(f"| `{agent}` | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _short_tool(name: str) -> str:
    return name.replace("mcp__coord__", "")


def _md_artifacts(data: ReportData) -> str:
    if not data.artifacts:
        return "## Artifacts\n\n_No artifacts produced._"
    lines = ["## Artifacts", ""]
    for folder in sorted(data.artifacts):
        lines.append(f"**{folder}/**")
        for name, size in data.artifacts[folder]:
            lines.append(f"- `{name}` ({size:,} B)")
    return "\n".join(lines)


def _md_messages(data: ReportData) -> str:
    if not data.messages:
        return "## Messages\n\n_No messages exchanged in this run._"
    lines = ["## Messages", "",
             "| ts | from → to | content |",
             "|---|---|---|"]
    for m in data.messages:
        cc = f" (cc → {m.original_to})" if m.cc else ""
        content = m.content.replace("|", "\\|").replace("\n", " ")[:200]
        lines.append(f"| {m.ts} | `{m.sender}` → `{m.to}`{cc} | {content} |")
    return "\n".join(lines)


def _md_raw_counts(data: ReportData) -> str:
    lines = ["## Event counts", "",
             "| event | count |", "|---|---:|"]
    for k, v in sorted(data.event_counts.items()):
        lines.append(f"| `{k}` | {v} |")
    return "\n".join(lines)


# ----------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------


def generate_reports(run_dir: Path) -> dict[str, Path]:
    """Generate report.html, report.md, sequence.md, playback.html, and
    stage.html in the run directory.
    Returns a mapping of format -> output path."""
    run_dir = Path(run_dir)
    data = extract_report_data(run_dir)
    html = render_html(data)
    md = render_markdown(data)
    sequence = _md_sequence(data) + "\n"
    playback = render_playback_html(data)
    stage = render_stage_html(data)
    html_path = run_dir / "report.html"
    md_path = run_dir / "report.md"
    seq_path = run_dir / "sequence.md"
    playback_path = run_dir / "playback.html"
    stage_path = run_dir / "stage.html"
    html_path.write_text(html, encoding="utf-8")
    md_path.write_text(md, encoding="utf-8")
    seq_path.write_text(sequence, encoding="utf-8")
    playback_path.write_text(playback, encoding="utf-8")
    stage_path.write_text(stage, encoding="utf-8")
    return {
        "html": html_path,
        "md": md_path,
        "sequence": seq_path,
        "playback": playback_path,
        "stage": stage_path,
    }


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("usage: python -m mat.report <run_dir>", file=sys.stderr)
        return 2
    run_dir = Path(args[0])
    if not run_dir.exists():
        print(f"error: {run_dir} does not exist", file=sys.stderr)
        return 1
    paths = generate_reports(run_dir)
    for fmt, p in paths.items():
        print(f"{fmt}: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
