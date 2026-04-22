"""Task-board tools exposed to agents via MCP (spec §6.3).

Each function here is a *factory* that returns a list of `@tool`-decorated
async callables, with the relevant state and agent identity closed over.
"""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from mat.state.task_store import TaskStore


def make_task_board_tools(
    task_store: TaskStore,
    agent_name: str,
    lead_only: bool,
) -> list:
    @tool(
        "create_task",
        (
            "Lead-only. Create a new task. Optionally pass `dependencies` (a list of "
            "existing task_ids) to gate this task — it will not be dispatched until "
            "every dependency reaches status='completed'."
        ),
        {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "dependencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of task_ids that must complete first.",
                },
            },
            "required": ["title", "description"],
            "additionalProperties": False,
        },
    )
    async def create_task(args: dict[str, Any]) -> dict[str, Any]:
        deps = args.get("dependencies") or []
        if deps:
            existing = {t.task_id for t in task_store.list_tasks()}
            unknown = [d for d in deps if d not in existing]
            if unknown:
                return _ok(
                    f"Refused to create task: dependencies {unknown} do not exist. "
                    f"Use only task_ids returned by previous create_task calls. "
                    f"Currently existing task_ids: {sorted(existing) or '(none)'}.",
                    is_error=True,
                )
        task_id = task_store.create_task(args["title"], args["description"], dependencies=deps)
        suffix = f" with deps {deps}" if deps else ""
        return _ok(
            f"Created task with task_id='{task_id}' (title: {args['title']}){suffix}. "
            f"Use the exact string '{task_id}' when referencing this task as a dependency."
        )

    @tool(
        "assign_task",
        "Lead-only. Assign an existing task to a teammate by name.",
        {"task_id": str, "agent": str},
    )
    async def assign_task(args: dict[str, Any]) -> dict[str, Any]:
        task_store.assign_task(args["task_id"], args["agent"])
        return _ok(f"Assigned {args['task_id']} to {args['agent']}.")

    @tool(
        "list_tasks",
        "List all tasks on the board with their status and assignee.",
        {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    )
    async def list_tasks(args: dict[str, Any]) -> dict[str, Any]:
        tasks = task_store.list_tasks()
        if not tasks:
            return _ok("(no tasks yet)")
        rows = []
        for t in tasks:
            row = {
                "task_id": t.task_id,
                "title": t.title,
                "status": t.status,
                "assigned_to": t.assigned_to,
                "dependencies": t.dependencies,
                "result_ref": t.result_ref,
            }
            rows.append(row)
        return _ok(json.dumps(rows, indent=2))

    @tool(
        "claim_task",
        "Teammate. Take ownership of an existing task.",
        {"task_id": str},
    )
    async def claim_task(args: dict[str, Any]) -> dict[str, Any]:
        ok = task_store.claim_task(args["task_id"], agent_name)
        if not ok:
            return _ok(f"Could not claim {args['task_id']} — already owned.", is_error=True)
        return _ok(f"Claimed {args['task_id']}.")

    @tool(
        "update_task",
        "Update the status of a task. Use status='completed' with a result_ref when done.",
        {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "status": {"type": "string", "description": "e.g. in_progress, completed, failed"},
                "note": {"type": "string"},
                "result_ref": {"type": "string", "description": "Path to result, relative to workspace"},
            },
            "required": ["task_id", "status"],
            "additionalProperties": False,
        },
    )
    async def update_task(args: dict[str, Any]) -> dict[str, Any]:
        task_store.update_status(
            args["task_id"],
            args["status"],
            note=args.get("note"),
            result_ref=args.get("result_ref"),
        )
        return _ok(f"Updated {args['task_id']} → {args['status']}.")

    tools = [list_tasks, update_task]
    if lead_only:
        tools.extend([create_task, assign_task])
    else:
        tools.append(claim_task)
    return tools


def _ok(text: str, is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "is_error": is_error}
