"""Team Lead session wrapper (spec §6.4).

Pure coordinator. Tools: Read/Glob/Grep + the coordination MCP set including
`finalize`. No Write/Edit, no Bash. The lead never modifies the workspace.

Driven by the orchestrator: `start()` sends the initial goal, `continue_()`
sends a follow-up after teammates have run. Between calls, the orchestrator
inspects the task board to decide what to do next.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from mat.config import LeadConfig
from mat.logging import EventLogger
from mat.tools import COORD_SERVER_NAME, coord_tool_names, disallowed_builtins


def _build_lead_system_prompt(
    goal: str,
    teammates: list[tuple[str, str]],
    extra: str,
) -> str:
    roster = "\n".join(f"- {name}: {desc}" for name, desc in teammates) or "(no teammates)"
    return f"""You are the Team Lead.

Your role is pure coordination. You decompose the user's goal into tasks,
assign them to teammates, monitor progress, and synthesize the final result.
You do NOT do the work yourself. You have read-only access to the workspace
(Read, Glob, Grep). You cannot write or edit files.

USER GOAL:
{goal}

YOUR TEAMMATES:
{roster}

HOW TO WORK:
- `create_task(title, description, dependencies=[...])` — add a task to the
  board. The tool returns the new task_id (format like `t_001`, `t_002`).
  When passing `dependencies`, use the EXACT task_id strings returned by
  earlier `create_task` calls — never invent names like "task-1" or
  "research-task". A task with bad dep ids will be silently blocked forever.
  Example: after `create_task → t_001`, the next call might be
  `create_task(title="Analyze", description="...", dependencies=["t_001"])`.
  Tasks with no `dependencies` may run in parallel.
- `assign_task(task_id, agent)` — assign to a teammate by name.
- `list_tasks()` — see the current board (includes dependencies).
- `read_messages()` / `send_message(to, content)` — talk to teammates.
- `update_task(task_id, status, ...)` — rarely used by you.
- `write_scratchpad(filename, content)` — lead-only, for scoping artifacts
  that every teammate should read (currently whitelist: DONE_CRITERIA.md).
  Do NOT use this for code or deliverables — only for pinning down scope.
- `finalize(synthesis)` — call ONLY when every assigned task is `completed`.
  This writes `workspace/OUTPUT.md` and ends the run. Do not call it early.

The orchestrator will run teammates between your turns and report status.
Typical pattern: in your first turn, lay out ALL the tasks at once with
their dependencies and assignments, then let the orchestrator drive
execution. Refine in later turns only if something needs adjusting.

{extra}
""".strip()


class TeamLead:
    def __init__(
        self,
        config: LeadConfig,
        coordination_server: Any,
        goal: str,
        teammates: list[tuple[str, str]],
        workspace_dir: Path,
        event_logger: EventLogger | None = None,
    ) -> None:
        self.config = config
        self.coordination_server = coordination_server
        self.goal = goal
        self.teammates = teammates
        self.workspace_dir = Path(workspace_dir).resolve()
        self.event_logger = event_logger
        self._client: ClaudeSDKClient | None = None

    async def __aenter__(self) -> "TeamLead":
        coord = coord_tool_names(
            lead_only=True, has_status=True, has_finalize=True, has_scratchpad=True,
        )
        lead_builtin = ["Read", "Glob", "Grep"]
        allowed = lead_builtin + coord
        disallowed = disallowed_builtins(lead_builtin)

        options = ClaudeAgentOptions(
            system_prompt=_build_lead_system_prompt(
                self.goal, self.teammates, self.config.extra_instructions
            ),
            mcp_servers={COORD_SERVER_NAME: self.coordination_server},
            allowed_tools=allowed,
            disallowed_tools=disallowed,
            model=self.config.model,
            max_turns=self.config.max_turns,
            cwd=str(self.workspace_dir),
        )
        self._client = ClaudeSDKClient(options=options)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc, tb)
            self._client = None

    async def start(self) -> str:
        return await self._send("Begin. Decompose the goal and assign tasks.")

    async def continue_(self, prompt: str) -> str:
        return await self._send(prompt)

    async def _send(self, prompt: str) -> str:
        assert self._client is not None, "Lead not entered"
        if self.event_logger:
            self.event_logger.log("lead_prompt", prompt=prompt[:500])

        await self._client.query(prompt)
        last_text = ""
        async for msg in self._client.receive_response():
            last_text = self._consume(msg, last_text)
        return last_text

    def _consume(self, msg: Any, last_text: str) -> str:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    last_text = block.text
                if self.event_logger:
                    self.event_logger.log(
                        "lead_block",
                        kind=type(block).__name__,
                        preview=_preview(block),
                    )
                    if isinstance(block, ToolUseBlock):
                        self.event_logger.log(
                            "tool_use",
                            agent="lead",
                            name=block.name,
                            input=block.input,
                            tool_use_id=block.id,
                        )
        elif isinstance(msg, ResultMessage):
            if self.event_logger:
                usage = getattr(msg, "usage", None) or {}
                self.event_logger.log(
                    "lead_result",
                    subtype=getattr(msg, "subtype", None),
                    cost_usd=getattr(msg, "total_cost_usd", None),
                    cache_read=usage.get("cache_read_input_tokens", 0),
                    cache_write=usage.get("cache_creation_input_tokens", 0),
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                )
        return last_text


def _preview(block: Any) -> str:
    if hasattr(block, "text"):
        return block.text[:300]
    if hasattr(block, "name"):
        inp = getattr(block, "input", {})
        return f"{block.name}({inp!r})"[:300]
    return type(block).__name__
