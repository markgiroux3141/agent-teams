"""Coordination MCP server factory.

Returns a fresh in-process MCP server per agent. Identity (`agent_name`) is
baked in via closure so `send_message` knows who's sending and `read_messages`
knows whose inbox to read.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server

from mat.state.message_bus import MessageBus
from mat.state.task_store import TaskStore
from mat.tools.messaging import make_messaging_tools
from mat.tools.status import make_finalize_tool, make_scratchpad_tool, make_status_tools
from mat.tools.task_board import make_task_board_tools

COORD_SERVER_NAME = "coord"


# Built-in tools the SDK may expose. Used to compute `disallowed_tools` so the
# YAML's per-agent allow-list is actually enforced (the SDK's `allowed_tools`
# is a *pre-approval* list, not a restriction list).
BUILTIN_TOOLS = frozenset({
    "Read", "Write", "Edit",
    "Glob", "Grep",
    "Bash", "BashOutput", "KillBash",
    "WebSearch", "WebFetch",
    "NotebookEdit",
    "Task",
    "TodoWrite",
    "ExitPlanMode",
    "AskUserQuestion",
    "ToolSearch",
    "SlashCommand",
    "ListMcpResources", "ReadMcpResource",
})


def disallowed_builtins(allowed: list[str]) -> list[str]:
    """Return built-in tools that should be blocked, given the explicit allow list."""
    return sorted(BUILTIN_TOOLS - set(allowed))


def build_coordination_server(
    *,
    task_store: TaskStore,
    message_bus: MessageBus,
    agent_name: str,
    lead_only: bool = False,
    team_state_fn: Callable[[], list[dict]] | None = None,
    finalize_callback: Callable[[str], None] | None = None,
    scratchpad_workspace: Path | None = None,
) -> Any:
    tools = []
    tools.extend(make_task_board_tools(task_store, agent_name, lead_only))
    tools.extend(make_messaging_tools(message_bus, agent_name))
    if team_state_fn is not None:
        tools.extend(make_status_tools(team_state_fn))
    if finalize_callback is not None:
        tools.extend(make_finalize_tool(finalize_callback))
    if scratchpad_workspace is not None:
        tools.extend(make_scratchpad_tool(scratchpad_workspace))

    return create_sdk_mcp_server(
        name=COORD_SERVER_NAME,
        version="1.0.0",
        tools=tools,
    )


def coord_tool_names(
    *,
    lead_only: bool,
    has_status: bool,
    has_finalize: bool,
    has_scratchpad: bool = False,
) -> list[str]:
    """Return the `mcp__coord__*` names that should be put in `allowed_tools`."""
    names = [
        "mcp__coord__list_tasks",
        "mcp__coord__update_task",
        "mcp__coord__send_message",
        "mcp__coord__read_messages",
    ]
    if lead_only:
        names.extend(["mcp__coord__create_task", "mcp__coord__assign_task"])
    else:
        names.append("mcp__coord__claim_task")
    if has_status:
        names.append("mcp__coord__get_teammate_info")
    if has_finalize:
        names.append("mcp__coord__finalize")
    if has_scratchpad:
        names.append("mcp__coord__write_scratchpad")
    return names
