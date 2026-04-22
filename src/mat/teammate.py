"""Teammate session wrapper (spec §6.5).

Each teammate is a long-lived `ClaudeSDKClient` so the SDK auto-tracks the
session_id across multiple `dispatch()` calls — context carries forward
without us threading session ids manually.

Writes are sandboxed to `workspace_dir` via a PreToolUse hook on `Write|Edit`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)

from mat.config import TeammateConfig
from mat.logging import EventLogger
from mat.tools import COORD_SERVER_NAME, coord_tool_names, disallowed_builtins


class Teammate:
    def __init__(
        self,
        config: TeammateConfig,
        coordination_server: Any,
        workspace_dir: Path,
        event_logger: EventLogger | None = None,
    ) -> None:
        self.config = config
        self.coordination_server = coordination_server
        self.workspace_dir = Path(workspace_dir).resolve()
        self.event_logger = event_logger
        self.last_status: str = "idle"
        self._client: ClaudeSDKClient | None = None

    async def __aenter__(self) -> "Teammate":
        coord = coord_tool_names(lead_only=False, has_status=False, has_finalize=False)
        allowed = list(self.config.allowed_tools) + coord
        # `allowed_tools` is a pre-approval list, not a restriction. To actually
        # restrict, explicitly disallow every built-in not in the YAML allow list.
        disallowed = disallowed_builtins(self.config.allowed_tools)

        options = ClaudeAgentOptions(
            system_prompt=self.config.system_prompt or "",
            mcp_servers={COORD_SERVER_NAME: self.coordination_server},
            allowed_tools=allowed,
            disallowed_tools=disallowed,
            model=self.config.model,
            cwd=str(self.workspace_dir),
            hooks={
                "PreToolUse": [
                    HookMatcher(matcher="Write|Edit", hooks=[self._workspace_write_guard]),
                ]
            },
        )
        self._client = ClaudeSDKClient(options=options)
        await self._client.__aenter__()
        self.last_status = "ready"
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc, tb)
            self._client = None

    async def dispatch(self, prompt: str) -> str:
        """Send a prompt; drain the response stream; return last text block."""
        assert self._client is not None, "Teammate not entered"
        self.last_status = "working"
        if self.event_logger:
            self.event_logger.log("teammate_prompt", agent=self.config.name, prompt=prompt[:500])

        await self._client.query(prompt)
        last_text = ""
        async for msg in self._client.receive_response():
            last_text = self._consume(msg, last_text)
        self.last_status = "ready"
        return last_text

    def _consume(self, msg: Any, last_text: str) -> str:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    last_text = block.text
                if self.event_logger:
                    self.event_logger.log(
                        "teammate_block",
                        agent=self.config.name,
                        kind=type(block).__name__,
                        preview=_preview(block),
                    )
                    if isinstance(block, ToolUseBlock):
                        self.event_logger.log(
                            "tool_use",
                            agent=self.config.name,
                            name=block.name,
                            input=block.input,
                            tool_use_id=block.id,
                        )
        elif isinstance(msg, ResultMessage):
            if self.event_logger:
                usage = getattr(msg, "usage", None) or {}
                self.event_logger.log(
                    "teammate_result",
                    agent=self.config.name,
                    subtype=getattr(msg, "subtype", None),
                    cost_usd=getattr(msg, "total_cost_usd", None),
                    cache_read=usage.get("cache_read_input_tokens", 0),
                    cache_write=usage.get("cache_creation_input_tokens", 0),
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                )
        return last_text

    async def _workspace_write_guard(
        self,
        input_data: dict[str, Any],
        tool_use_id: str,
        context: Any,
    ) -> dict[str, Any]:
        tool_input = input_data.get("tool_input", {}) or {}
        path_str = tool_input.get("file_path") or tool_input.get("filePath") or ""
        if not path_str:
            return {}
        try:
            target = Path(path_str)
            if not target.is_absolute():
                target = self.workspace_dir / target
            resolved = target.resolve()
            try:
                resolved.relative_to(self.workspace_dir)
            except ValueError:
                return {
                    "allowed": False,
                    "message": (
                        f"Write/Edit denied: '{path_str}' resolves to '{resolved}', "
                        f"which is outside your workspace. "
                        f"Use a BARE FILENAME like 'analysis.md' (no slashes, no "
                        f"leading paths). Your CWD is already the workspace, so "
                        f"'analysis.md' will land in the right place."
                    ),
                }
        except Exception as e:
            return {"allowed": False, "message": f"Could not validate write path: {e}"}
        return {}


def _preview(block: Any) -> str:
    if hasattr(block, "text"):
        return block.text[:300]
    if hasattr(block, "name"):
        inp = getattr(block, "input", {})
        return f"{block.name}({inp!r})"[:300]
    return type(block).__name__


# Re-export for type hints elsewhere
__all__ = ["Teammate", "AsyncIterator"]
