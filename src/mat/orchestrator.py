"""Top-level orchestrator (spec §6.6).

Event loop: lead turn → inspect task board + inboxes → dispatch ready tasks,
any teammate with unread mail, and any silent-stall nudges → wake the lead
with a status summary → repeat until the lead calls `finalize` (or we hit a
safety cap, an interrupt, or a global timeout).

M3: reply-dispatch for unread-mail teammates; CC-to-lead for teammate-to-
teammate traffic.

M4 hardening:
- Per-dispatch timeout (TeamSettings.stall_timeout_seconds). On timeout the
  task is marked `failed` and the loop continues; the SDK client is left in
  place so the next dispatch can try again.
- Silent-stall auto-nudge: if a task is still `in_progress` for an agent
  with no ready work and no mail, we wake them once with a "complete or
  explain" prompt. Tracked per-task so we don't loop.
- Graceful shutdown: KeyboardInterrupt/CancelledError inside the loop is
  caught, state is flushed, a `run_summary.json` is written. Append-only
  JSONL state (tasks, messages, trace) means partial runs are recoverable.
- run_summary.json: per-agent cost/token totals + final task statuses.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import AsyncExitStack
from pathlib import Path

from mat.config import TeamConfig
from mat.lead import TeamLead
from mat.logging import EventLogger
from mat.state.message_bus import MessageBus
from mat.state.task_store import TaskStore, Task
from mat.teammate import Teammate
from mat.tools import build_coordination_server


_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
_LEAD_NAME = "lead"


def deps_satisfied(task: Task, by_id: dict[str, Task]) -> bool:
    """A task is dispatchable when every declared dependency exists and is completed."""
    for dep_id in task.dependencies:
        dep = by_id.get(dep_id)
        if dep is None or dep.status != "completed":
            return False
    return True


class Orchestrator:
    def __init__(
        self,
        team_config: TeamConfig,
        goal: str,
        run_dir: Path,
    ) -> None:
        self.team_config = team_config
        self.goal = goal
        self.run_dir = Path(run_dir)
        self.finalized_output: str | None = None
        self._interrupted: bool = False
        self._nudged_tasks: set[str] = set()

    async def run(self) -> Path:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        workspace = self.run_dir / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)

        task_store = TaskStore(self.run_dir / "tasks.jsonl")
        cc_agent = _LEAD_NAME if self.team_config.settings.cc_lead_on_messages else None
        message_bus = MessageBus(self.run_dir / "messages", cc_agent=cc_agent)
        event_logger = EventLogger(self.run_dir / "trace.jsonl")

        settings = self.team_config.settings
        event_logger.log(
            "run_start",
            goal=self.goal,
            team=self.team_config.name,
            cc_agent=cc_agent,
            unread_backpressure_threshold=settings.unread_backpressure_threshold,
            stall_timeout_seconds=settings.stall_timeout_seconds,
        )

        teammates: dict[str, Teammate] = {}
        for tc in self.team_config.teammates:
            coord = build_coordination_server(
                task_store=task_store,
                message_bus=message_bus,
                agent_name=tc.name,
                lead_only=False,
            )
            teammates[tc.name] = Teammate(
                tc, coord, workspace_dir=workspace, event_logger=event_logger
            )

        def _team_state() -> list[dict]:
            return [
                {"name": tc.name, "description": tc.description, "status": teammates[tc.name].last_status}
                for tc in self.team_config.teammates
            ]

        def _capture_finalize(text: str) -> None:
            self.finalized_output = text

        lead_coord = build_coordination_server(
            task_store=task_store,
            message_bus=message_bus,
            agent_name=_LEAD_NAME,
            lead_only=True,
            team_state_fn=_team_state,
            finalize_callback=_capture_finalize,
            scratchpad_workspace=workspace,
        )
        lead = TeamLead(
            self.team_config.lead,
            lead_coord,
            self.goal,
            teammates=[(tc.name, tc.description) for tc in self.team_config.teammates],
            workspace_dir=workspace,
            event_logger=event_logger,
        )

        threshold = settings.unread_backpressure_threshold
        timeout = settings.stall_timeout_seconds
        max_iters = settings.max_loop_iterations

        try:
            async with AsyncExitStack() as stack:
                await stack.enter_async_context(lead)
                for tm in teammates.values():
                    await stack.enter_async_context(tm)

                try:
                    await self._main_loop(
                        lead, teammates, task_store, message_bus, event_logger,
                        threshold, timeout, max_iters,
                    )
                except (KeyboardInterrupt, asyncio.CancelledError) as e:
                    self._interrupted = True
                    event_logger.log("run_interrupted", reason=type(e).__name__)

            output_path = workspace / "OUTPUT.md"
            if self.finalized_output is not None:
                output_path.write_text(self.finalized_output, encoding="utf-8")
                event_logger.log("output_written", path=str(output_path))
            elif self._interrupted:
                partial = workspace / "OUTPUT.md.partial"
                partial.write_text(
                    "(run interrupted before finalize — see tasks.jsonl / trace.jsonl)\n",
                    encoding="utf-8",
                )
                event_logger.log("output_partial", path=str(partial))
            else:
                event_logger.log("output_missing", reason="lead never called finalize")

            self._write_summary(event_logger, task_store)
            try:
                from mat.report import generate_reports
                paths = generate_reports(self.run_dir)
                event_logger.log(
                    "reports_written",
                    **{k: str(v) for k, v in paths.items()},
                )
            except Exception as e:
                event_logger.log(
                    "reports_error", error=str(e), error_type=type(e).__name__,
                )
            event_logger.log("run_end", interrupted=self._interrupted)
            return output_path
        finally:
            event_logger.close()

    async def _main_loop(
        self,
        lead: TeamLead,
        teammates: dict[str, Teammate],
        task_store: TaskStore,
        message_bus: MessageBus,
        event_logger: EventLogger,
        threshold: int,
        timeout: float,
        max_iters: int,
    ) -> None:
        event_logger.log("lead_turn_start", turn=0)
        await self._run_with_timeout(lead.start(), timeout, event_logger, who="lead")
        event_logger.log("lead_turn_end", turn=0)

        for turn in range(1, max_iters + 1):
            if self.finalized_output is not None:
                event_logger.log("loop_exit", reason="finalized")
                return

            ready_tasks = self._pending_dispatches(task_store, teammates)
            task_agents = {t.assigned_to for t in ready_tasks}
            pending_replies = [
                name
                for name in teammates
                if name not in task_agents and message_bus.unread_count(name) > 0
            ]

            if not ready_tasks and not pending_replies:
                nudges = self._find_stall_nudges(task_store, teammates)
            else:
                nudges = []

            if ready_tasks or pending_replies or nudges:
                await self._dispatch_round(
                    ready_tasks, pending_replies, nudges,
                    teammates, task_store, message_bus, event_logger, timeout,
                )
                for t in nudges:
                    self._nudged_tasks.add(t.task_id)

                summary = self._status_summary(task_store, message_bus, teammates, threshold)
                event_logger.log("lead_turn_start", turn=turn)
                await self._run_with_timeout(
                    lead.continue_(f"Status update:\n{summary}\n\nWhat next?"),
                    timeout, event_logger, who="lead",
                )
                event_logger.log("lead_turn_end", turn=turn)
                continue

            incomplete = [
                t for t in task_store.list_tasks() if t.status not in _TERMINAL_STATUSES
            ]
            summary = self._status_summary(task_store, message_bus, teammates, threshold)
            if not incomplete:
                event_logger.log("lead_turn_start", turn=turn)
                await self._run_with_timeout(
                    lead.continue_(
                        "All tasks are complete. Synthesize the result and call "
                        f"`finalize(synthesis=...)` now.\n\nBoard:\n{summary}"
                    ),
                    timeout, event_logger, who="lead",
                )
                event_logger.log("lead_turn_end", turn=turn)
                if self.finalized_output is not None:
                    event_logger.log("loop_exit", reason="finalized_after_nudge")
                    return
            else:
                event_logger.log("lead_turn_start", turn=turn)
                await self._run_with_timeout(
                    lead.continue_(
                        "No new dispatches happened this turn but tasks remain "
                        f"open:\n{summary}\n\nReassign or finalize."
                    ),
                    timeout, event_logger, who="lead",
                )
                event_logger.log("lead_turn_end", turn=turn)

        event_logger.log("loop_exit", reason="max_iterations", iterations=max_iters)

    def _find_stall_nudges(
        self,
        task_store: TaskStore,
        teammates: dict[str, Teammate],
    ) -> list[Task]:
        """In_progress tasks whose owner is idle this round and hasn't been
        nudged yet. One nudge per task per run."""
        return [
            t
            for t in task_store.list_tasks()
            if t.status == "in_progress"
            and t.assigned_to in teammates
            and t.task_id not in self._nudged_tasks
        ]

    def _pending_dispatches(
        self,
        task_store: TaskStore,
        teammates: dict[str, Teammate],
    ) -> list[Task]:
        all_tasks = task_store.list_tasks()
        by_id = {t.task_id: t for t in all_tasks}
        return [
            t
            for t in all_tasks
            if t.status == "assigned"
            and t.assigned_to in teammates
            and deps_satisfied(t, by_id)
        ]

    async def _dispatch_round(
        self,
        ready_tasks: list[Task],
        pending_replies: list[str],
        nudges: list[Task],
        teammates: dict[str, Teammate],
        task_store: TaskStore,
        message_bus: MessageBus,
        event_logger: EventLogger,
        timeout: float,
    ) -> None:
        """Tasks + reply wakeups + stall nudges in parallel by agent.

        Each agent appears in at most one branch per round. A task-agent who
        also has mail gets a combined prompt. Reply-agents have mail but no
        task. Nudge-agents have neither — just an in_progress task to chase."""

        by_agent_tasks: dict[str, list[Task]] = {}
        for t in ready_tasks:
            by_agent_tasks.setdefault(t.assigned_to, []).append(t)

        nudge_agents = {t.assigned_to for t in nudges}
        # Don't nudge an agent we're already talking to this round.
        nudges = [t for t in nudges if t.assigned_to not in by_agent_tasks and t.assigned_to not in pending_replies]

        event_logger.log(
            "dispatch_round",
            task_agents=list(by_agent_tasks.keys()),
            task_ids=[t.task_id for t in ready_tasks],
            reply_agents=list(pending_replies),
            nudge_agents=[t.assigned_to for t in nudges],
            nudge_task_ids=[t.task_id for t in nudges],
        )

        async def run_task_agent(agent: str, tasks: list[Task]) -> None:
            has_mail = message_bus.unread_count(agent) > 0
            for i, task in enumerate(tasks):
                await self._dispatch_task(
                    task, teammates, task_store, event_logger,
                    note_inbox=(has_mail and i == 0), timeout=timeout,
                )

        async def run_reply_agent(agent: str) -> None:
            await self._dispatch_reply(agent, teammates, message_bus, event_logger, timeout)

        async def run_nudge(task: Task) -> None:
            await self._dispatch_nudge(task, teammates, event_logger, timeout)

        coros = [run_task_agent(a, ts) for a, ts in by_agent_tasks.items()]
        coros += [run_reply_agent(a) for a in pending_replies]
        coros += [run_nudge(t) for t in nudges]
        await asyncio.gather(*coros)

    async def _dispatch_task(
        self,
        task: Task,
        teammates: dict[str, Teammate],
        task_store: TaskStore,
        event_logger: EventLogger,
        note_inbox: bool,
        timeout: float,
    ) -> None:
        teammate = teammates[task.assigned_to]
        task_store.update_status(task.task_id, "in_progress")
        event_logger.log(
            "dispatch_start",
            agent=task.assigned_to,
            task_id=task.task_id,
            inbox_note=note_inbox,
        )
        inbox_line = (
            "\n\nYou also have unread messages in your inbox. Call "
            "`mcp__coord__read_messages` first; they may affect how you approach "
            "this task."
            if note_inbox
            else ""
        )
        prompt = (
            f"You have been assigned task {task.task_id}.\n\n"
            f"Title: {task.title}\n"
            f"Description: {task.description}\n\n"
            f"Do the work. When finished, call "
            f"`update_task(task_id='{task.task_id}', status='completed', result_ref='<filename>')` "
            f"to mark it done.\n\n"
            f"FILE PATHS: when you write or edit files, use ONLY a bare filename "
            f"like 'analysis.md' — NO leading slashes, NO 'workspace/' prefix, NO "
            f"directory paths. Your current working directory is already the "
            f"workspace; the runtime enforces this and will deny writes outside it."
            f"{inbox_line}"
        )
        try:
            await self._run_with_timeout(
                teammate.dispatch(prompt), timeout, event_logger,
                who=task.assigned_to, task_id=task.task_id,
            )
            event_logger.log("dispatch_end", agent=task.assigned_to, task_id=task.task_id)
        except asyncio.TimeoutError:
            task_store.update_status(
                task.task_id, "failed",
                note=f"dispatch exceeded stall_timeout_seconds={timeout}",
            )
        except Exception as e:
            event_logger.log(
                "dispatch_error",
                agent=task.assigned_to,
                task_id=task.task_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            task_store.update_status(task.task_id, "failed", note=str(e))

    async def _dispatch_reply(
        self,
        agent: str,
        teammates: dict[str, Teammate],
        message_bus: MessageBus,
        event_logger: EventLogger,
        timeout: float,
    ) -> None:
        teammate = teammates[agent]
        unread = message_bus.unread_count(agent)
        event_logger.log("reply_dispatch_start", agent=agent, unread=unread)
        prompt = (
            f"You have {unread} new message(s) waiting. Call "
            f"`mcp__coord__read_messages` to see them.\n\n"
            "Then decide:\n"
            "- If a teammate asked you a question, answer it with "
            "`mcp__coord__send_message(to='<their_name>', content='...')`.\n"
            "- If the message relates to a task you have in progress, continue "
            "that task after responding.\n"
            "- If the message is informational and no reply is needed, just end "
            "your turn.\n\n"
            "Do NOT start new work that wasn't assigned to you via the task board."
        )
        try:
            await self._run_with_timeout(
                teammate.dispatch(prompt), timeout, event_logger, who=agent,
            )
            event_logger.log("reply_dispatch_end", agent=agent)
        except asyncio.TimeoutError:
            pass  # already logged by _run_with_timeout
        except Exception as e:
            event_logger.log(
                "reply_dispatch_error", agent=agent,
                error=str(e), error_type=type(e).__name__,
            )

    async def _dispatch_nudge(
        self,
        task: Task,
        teammates: dict[str, Teammate],
        event_logger: EventLogger,
        timeout: float,
    ) -> None:
        teammate = teammates[task.assigned_to]
        event_logger.log("nudge_start", agent=task.assigned_to, task_id=task.task_id)
        prompt = (
            f"Your task {task.task_id} ({task.title}) is still in progress but "
            f"you appear to have gone idle. Either:\n"
            f"- Complete it now by calling "
            f"`update_task(task_id='{task.task_id}', status='completed', "
            f"result_ref='<filename>')` if the work is done, or\n"
            f"- Send a message to the lead via "
            f"`mcp__coord__send_message(to='lead', content='...')` explaining "
            f"what's blocking you, or\n"
            f"- Mark it failed via "
            f"`update_task(task_id='{task.task_id}', status='failed', "
            f"note='<reason>')` if you can't complete it.\n\n"
            f"You will not be nudged again for this task."
        )
        try:
            await self._run_with_timeout(
                teammate.dispatch(prompt), timeout, event_logger, who=task.assigned_to,
            )
            event_logger.log("nudge_end", agent=task.assigned_to, task_id=task.task_id)
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            event_logger.log(
                "nudge_error", agent=task.assigned_to, task_id=task.task_id,
                error=str(e), error_type=type(e).__name__,
            )

    async def _run_with_timeout(
        self,
        coro,
        timeout: float,
        event_logger: EventLogger,
        who: str,
        task_id: str | None = None,
    ):
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            event_logger.log(
                "dispatch_timeout",
                who=who,
                task_id=task_id,
                timeout_seconds=timeout,
            )
            raise

    def _status_summary(
        self,
        task_store: TaskStore,
        message_bus: MessageBus,
        teammates: dict[str, Teammate],
        threshold: int,
    ) -> str:
        tasks = task_store.list_tasks()
        lines: list[str] = []
        if not tasks:
            lines.append("(no tasks on the board)")
        else:
            for t in tasks:
                line = f"- {t.task_id} [{t.status}] {t.title}"
                if t.assigned_to:
                    line += f" (→ {t.assigned_to})"
                if t.result_ref:
                    line += f" → {t.result_ref}"
                if t.status == "failed" and t.note:
                    line += f" [note: {t.note[:80]}]"
                lines.append(line)

        flags = [
            f"{name}: {message_bus.unread_count(name)} unread"
            for name in teammates
            if message_bus.unread_count(name) > threshold
        ]
        if flags:
            lines.append("")
            lines.append("⚠ Back-pressure (unread > threshold):")
            for f in flags:
                lines.append(f"  - {f}")
        return "\n".join(lines)

    def _write_summary(self, event_logger: EventLogger, task_store: TaskStore) -> None:
        tasks = task_store.list_tasks()
        statuses: dict[str, int] = {}
        for t in tasks:
            statuses[t.status] = statuses.get(t.status, 0) + 1
        summary = {
            "goal": self.goal,
            "team": self.team_config.name,
            "interrupted": self._interrupted,
            "finalized": self.finalized_output is not None,
            "task_counts_by_status": statuses,
            "tasks": [
                {
                    "task_id": t.task_id,
                    "status": t.status,
                    "assigned_to": t.assigned_to,
                    "result_ref": t.result_ref,
                    "note": t.note,
                }
                for t in tasks
            ],
            "cost": event_logger.ledger.as_dict(),
        }
        summary_path = self.run_dir / "run_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        event_logger.log("run_summary_written", path=str(summary_path))
