"""Append-only JSONL task board (spec §6.1).

Each line in `tasks.jsonl` is one event: `created`, `assigned`, `claimed`,
`status`. The in-memory view is derived by replaying the file on demand —
no caching for v1. Cheap because boards are small.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    status: str
    assigned_to: str | None = None
    dependencies: list[str] = field(default_factory=list)
    result_ref: str | None = None
    note: str | None = None


class TaskStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self._counter = len(self._replay())

    def create_task(
        self,
        title: str,
        description: str,
        dependencies: list[str] | None = None,
    ) -> str:
        self._counter += 1
        task_id = f"t_{self._counter:03d}"
        self._append({
            "ts": _now(),
            "event": "created",
            "task_id": task_id,
            "title": title,
            "description": description,
            "dependencies": dependencies or [],
        })
        return task_id

    def assign_task(self, task_id: str, agent: str) -> None:
        self._append({
            "ts": _now(),
            "event": "assigned",
            "task_id": task_id,
            "agent": agent,
        })

    def claim_task(self, task_id: str, agent: str) -> bool:
        task = self.get_task(task_id)
        if task.assigned_to and task.assigned_to != agent:
            return False
        self._append({
            "ts": _now(),
            "event": "claimed",
            "task_id": task_id,
            "agent": agent,
        })
        return True

    def update_status(
        self,
        task_id: str,
        status: str,
        note: str | None = None,
        result_ref: str | None = None,
    ) -> None:
        event = {
            "ts": _now(),
            "event": "status",
            "task_id": task_id,
            "status": status,
        }
        if note:
            event["note"] = note
        if result_ref:
            event["result_ref"] = result_ref
        self._append(event)

    def list_tasks(self, status: str | None = None) -> list[Task]:
        tasks = list(self._replay().values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def get_task(self, task_id: str) -> Task:
        tasks = self._replay()
        if task_id not in tasks:
            raise KeyError(f"unknown task_id: {task_id}")
        return tasks[task_id]

    def _replay(self) -> dict[str, Task]:
        tasks: dict[str, Task] = {}
        if not self.path.exists():
            return tasks
        with self.path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                self._apply_event(tasks, json.loads(line))
        return tasks

    @staticmethod
    def _apply_event(tasks: dict[str, Task], event: dict) -> None:
        task_id = event["task_id"]
        kind = event["event"]
        if kind == "created":
            tasks[task_id] = Task(
                task_id=task_id,
                title=event["title"],
                description=event["description"],
                status="created",
                dependencies=event.get("dependencies", []),
            )
        elif kind == "assigned" and task_id in tasks:
            tasks[task_id].assigned_to = event["agent"]
            tasks[task_id].status = "assigned"
        elif kind == "claimed" and task_id in tasks:
            tasks[task_id].assigned_to = event["agent"]
            tasks[task_id].status = "claimed"
        elif kind == "status" and task_id in tasks:
            tasks[task_id].status = event["status"]
            if "result_ref" in event:
                tasks[task_id].result_ref = event["result_ref"]
            if "note" in event:
                tasks[task_id].note = event["note"]

    def _append(self, event: dict) -> None:
        with self.path.open("a") as f:
            f.write(json.dumps(event) + "\n")
