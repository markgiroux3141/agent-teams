"""Per-agent inbox files under `runs/<run_id>/messages/<agent>.jsonl` (spec §6.2).

Messaging supports an optional CC agent (typically the lead). When set, any
message whose sender and recipient are both other agents gets an extra copy
dropped into the CC agent's inbox, flagged with `cc: true` so the reader can
tell overheard mail from direct mail.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Message:
    ts: str
    sender: str
    to: str
    content: str
    cc: bool = False
    original_to: str | None = None


class MessageBus:
    def __init__(self, messages_dir: Path, cc_agent: str | None = None) -> None:
        self.messages_dir = Path(messages_dir)
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        self.cc_agent = cc_agent
        self._cursors: dict[str, int] = {}

    def send(self, to: str, sender: str, content: str) -> None:
        ts = _now()
        self._append(to, {"ts": ts, "sender": sender, "to": to, "content": content})
        if (
            self.cc_agent is not None
            and to != self.cc_agent
            and sender != self.cc_agent
        ):
            self._append(
                self.cc_agent,
                {
                    "ts": ts,
                    "sender": sender,
                    "to": self.cc_agent,
                    "content": content,
                    "cc": True,
                    "original_to": to,
                },
            )

    def poll(self, agent: str) -> list[Message]:
        lines = self._read_lines(agent)
        cursor = self._cursors.get(agent, 0)
        new = lines[cursor:]
        self._cursors[agent] = len(lines)
        return [Message(**json.loads(line)) for line in new]

    def unread_count(self, agent: str) -> int:
        lines = self._read_lines(agent)
        return max(0, len(lines) - self._cursors.get(agent, 0))

    def _read_lines(self, agent: str) -> list[str]:
        inbox = self.messages_dir / f"{agent}.jsonl"
        if not inbox.exists():
            return []
        with inbox.open() as f:
            return [line for line in f if line.strip()]

    def _append(self, agent: str, payload: dict) -> None:
        inbox = self.messages_dir / f"{agent}.jsonl"
        with inbox.open("a") as f:
            f.write(json.dumps(payload) + "\n")
