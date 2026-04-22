"""Roster/status/output tools exposed to agents via MCP (spec §6.3).

`team_state` is a callable returning a list of {name, description, status}
dicts — the orchestrator owns the source of truth and passes a getter in.

`write_scratchpad` is a lead-only file write limited to a whitelist of
scoping filenames (default: DONE_CRITERIA.md). The lead is otherwise a pure
coordinator with no Write/Edit — this tool exists so the lead can set
scope that every teammate reads, without opening up the full workspace.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool


DEFAULT_SCRATCHPAD_FILES = frozenset({"DONE_CRITERIA.md"})


def make_status_tools(team_state_fn: Callable[[], list[dict]]) -> list:
    @tool(
        "get_teammate_info",
        "List teammates with their description and current status.",
        {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    )
    async def get_teammate_info(args: dict[str, Any]) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": json.dumps(team_state_fn(), indent=2)}]}

    return [get_teammate_info]


def make_finalize_tool(set_output: Callable[[str], None]) -> list:
    @tool(
        "finalize",
        (
            "Lead-only. Submit the final synthesis. The orchestrator writes it to "
            "workspace/OUTPUT.md and ends the run. Only call this when all assigned "
            "tasks are completed."
        ),
        {"synthesis": str},
    )
    async def finalize(args: dict[str, Any]) -> dict[str, Any]:
        set_output(args["synthesis"])
        return {
            "content": [
                {"type": "text", "text": "Finalized. Run will end after this turn."}
            ]
        }

    return [finalize]


def make_scratchpad_tool(
    workspace_dir: Path,
    allowed_filenames: frozenset[str] = DEFAULT_SCRATCHPAD_FILES,
) -> list:
    """Lead-only write for scoping files like DONE_CRITERIA.md.

    Refuses anything not in the whitelist and anything that escapes the
    workspace. The default whitelist is tight on purpose — add names here
    only when a new coordination artifact is justified."""

    workspace_dir = Path(workspace_dir).resolve()

    @tool(
        "write_scratchpad",
        (
            "Lead-only. Write content to a whitelisted scoping file in the "
            "workspace (e.g. DONE_CRITERIA.md). Use this to pin down scope "
            "that every teammate needs to read. Allowed filenames: "
            f"{sorted(allowed_filenames)}. Pass a bare filename, no paths."
        ),
        {"filename": str, "content": str},
    )
    async def write_scratchpad(args: dict[str, Any]) -> dict[str, Any]:
        filename = args["filename"]
        content = args["content"]
        if filename not in allowed_filenames:
            return _ok(
                f"Refused: '{filename}' is not in the scratchpad whitelist. "
                f"Allowed: {sorted(allowed_filenames)}.",
                is_error=True,
            )
        # Defense-in-depth: reject anything that isn't a bare filename.
        if "/" in filename or "\\" in filename or filename.startswith("."):
            return _ok(
                f"Refused: '{filename}' must be a bare filename with no path components.",
                is_error=True,
            )
        target = (workspace_dir / filename).resolve()
        try:
            target.relative_to(workspace_dir)
        except ValueError:
            return _ok(
                f"Refused: '{filename}' resolves outside the workspace.",
                is_error=True,
            )
        target.write_text(content, encoding="utf-8")
        return _ok(f"Wrote {filename} ({len(content)} chars) to workspace.")

    return [write_scratchpad]


def _ok(text: str, is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "is_error": is_error}
