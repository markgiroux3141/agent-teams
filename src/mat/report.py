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
    """Generate both report.html and report.md in the given run directory.
    Returns a mapping of format -> output path."""
    run_dir = Path(run_dir)
    data = extract_report_data(run_dir)
    html = render_html(data)
    md = render_markdown(data)
    html_path = run_dir / "report.html"
    md_path = run_dir / "report.md"
    html_path.write_text(html, encoding="utf-8")
    md_path.write_text(md, encoding="utf-8")
    return {"html": html_path, "md": md_path}


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
