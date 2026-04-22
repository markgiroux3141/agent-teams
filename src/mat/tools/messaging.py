"""Messaging tools exposed to agents via MCP (spec §6.3).

`send_message` sends to a named agent. If the team is configured to CC the
lead on teammate-to-teammate messages, the bus drops an extra copy in the
lead's inbox automatically (see MessageBus.send). `read_messages` renders
CC'd rows distinctly so the lead can tell overheard mail apart.
"""

from __future__ import annotations

from typing import Any

from claude_agent_sdk import tool

from mat.state.message_bus import Message, MessageBus


def make_messaging_tools(message_bus: MessageBus, agent_name: str) -> list:
    @tool(
        "send_message",
        (
            "Send a message to another agent (lead or teammate) by name. "
            "If the team is configured to CC the lead on teammate-to-teammate "
            "traffic, the lead receives a copy automatically."
        ),
        {"to": str, "content": str},
    )
    async def send_message(args: dict[str, Any]) -> dict[str, Any]:
        message_bus.send(to=args["to"], sender=agent_name, content=args["content"])
        return _ok(f"Sent message to {args['to']}.")

    @tool(
        "read_messages",
        "Poll your own inbox. Returns messages received since the last poll.",
        {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    )
    async def read_messages(args: dict[str, Any]) -> dict[str, Any]:
        msgs = message_bus.poll(agent_name)
        if not msgs:
            return _ok("(no new messages)")
        body = "\n\n".join(_format(m) for m in msgs)
        return _ok(body)

    return [send_message, read_messages]


def _format(m: Message) -> str:
    if m.cc:
        return f"[cc: {m.sender} → {m.original_to} @ {m.ts}]\n{m.content}"
    return f"[from {m.sender} @ {m.ts}]\n{m.content}"


def _ok(text: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}]}
