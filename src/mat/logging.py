"""Append-only JSONL event log for a single run, plus a CostLedger that
aggregates per-agent token/cost totals as result events are emitted.

The EventLogger is the single write point; the CostLedger is an optional
sidecar that sees each event after it's written and bumps running totals.
Keeps the log itself dumb (append-only) and the aggregation stateless on
disk (it's reconstituted from the trace on demand too)."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentCost:
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    turns: int = 0


@dataclass
class CostLedger:
    per_agent: dict[str, AgentCost] = field(default_factory=lambda: defaultdict(AgentCost))

    def record(self, agent: str, fields: dict[str, Any]) -> None:
        a = self.per_agent[agent]
        a.cost_usd += float(fields.get("cost_usd") or 0.0)
        a.input_tokens += int(fields.get("input_tokens") or 0)
        a.output_tokens += int(fields.get("output_tokens") or 0)
        a.cache_read += int(fields.get("cache_read") or 0)
        a.cache_write += int(fields.get("cache_write") or 0)
        a.turns += 1

    def totals(self) -> AgentCost:
        out = AgentCost()
        for a in self.per_agent.values():
            out.cost_usd += a.cost_usd
            out.input_tokens += a.input_tokens
            out.output_tokens += a.output_tokens
            out.cache_read += a.cache_read
            out.cache_write += a.cache_write
            out.turns += a.turns
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            "per_agent": {k: vars(v) for k, v in sorted(self.per_agent.items())},
            "total": vars(self.totals()),
        }

    def format_summary(self) -> str:
        rows = []
        for name, a in sorted(self.per_agent.items()):
            rows.append(
                f"  {name:<16} turns={a.turns:<3} "
                f"${a.cost_usd:.4f}  in={a.input_tokens} out={a.output_tokens} "
                f"cache_r={a.cache_read} cache_w={a.cache_write}"
            )
        t = self.totals()
        rows.append(
            f"  {'TOTAL':<16} turns={t.turns:<3} "
            f"${t.cost_usd:.4f}  in={t.input_tokens} out={t.output_tokens} "
            f"cache_r={t.cache_read} cache_w={t.cache_write}"
        )
        return "\n".join(rows)


class EventLogger:
    def __init__(self, trace_path: Path) -> None:
        self.trace_path = Path(trace_path)
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.trace_path.open("a", buffering=1, encoding="utf-8")
        self.ledger = CostLedger()

    def log(self, event_type: str, **fields: Any) -> None:
        entry = {"ts": _now(), "event": event_type, **fields}
        self._fh.write(json.dumps(entry, default=str) + "\n")
        if event_type == "lead_result":
            self.ledger.record("lead", fields)
        elif event_type == "teammate_result":
            self.ledger.record(fields.get("agent", "<unknown>"), fields)

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.close()


def format_cost_summary(run_dir: Path) -> str:
    """Format the cost section of a run_summary.json for terminal display.
    Returns a short placeholder if the summary file is missing."""
    summary = Path(run_dir) / "run_summary.json"
    if not summary.exists():
        return "(no run_summary.json)"
    data = json.loads(summary.read_text(encoding="utf-8"))
    ledger = CostLedger()
    for name, vals in (data.get("cost", {}).get("per_agent") or {}).items():
        ledger.per_agent[name] = AgentCost(**vals)
    return ledger.format_summary()


def load_cost_ledger(trace_path: Path) -> CostLedger:
    """Reconstruct a CostLedger from a trace on disk — used by replay/analysis."""
    ledger = CostLedger()
    path = Path(trace_path)
    if not path.exists():
        return ledger
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            evt = json.loads(line)
            if evt.get("event") == "lead_result":
                ledger.record("lead", evt)
            elif evt.get("event") == "teammate_result":
                ledger.record(evt.get("agent", "<unknown>"), evt)
    return ledger
