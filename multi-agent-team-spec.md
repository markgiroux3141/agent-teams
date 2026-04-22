# Multi-Agent Team Orchestrator — Build Spec

A custom team-lead-plus-team agent system built on the **Claude Agent SDK**.
This spec is written to be handed directly to a Claude Code session as the
starting point for implementation.

---

## 1. Context & Why This Exists

Claude Code ships two built-in coordination options:

1. **Subagents** — single-session, fire-and-forget, cannot talk to each other.
2. **Agent Teams** — multi-session, experimental, capped around 3–5 teammates,
   no nested teams, one team per session.

Neither is enough when we need:

- More than ~5 concurrent agents
- Nested teams (team-of-teams)
- Dynamic team composition at runtime
- Headless / service deployment (no interactive terminal)
- Custom coordination protocols (negotiation, voting, peer review, etc.)

This project builds that layer on top of the Claude Agent SDK — the same
harness that powers Claude Code, exposed as a library. We keep all of Claude
Code's built-in goodness (filesystem tools, context compaction, MCP,
permissions, hooks) and layer our own orchestration on top.

---

## 2. Goals & Non-Goals

### Goals

- A **Team Lead** agent that decomposes work, assigns tasks, tracks progress,
  and synthesizes results.
- N **Teammate** agents, each with its own system prompt, tool allowlist,
  model choice, and persistent session.
- **Inter-agent messaging** — teammates can send messages to each other via
  the lead (v1) or directly (v2).
- **Shared task board** — append-only log of tasks with status transitions.
- **Resumable workers** — teammates can be paused and resumed without losing
  their context.
- **Observability** — every tool call, message, and state transition is
  logged to disk for replay/debugging.
- **Headless-friendly** — runs as a Python process; no terminal required.

### Non-Goals (explicitly out of scope for v1)

- A UI. Logs and a simple CLI are fine.
- Distributed deployment across machines. Single-process, single-box.
- Auto-scaling teammate count based on load.
- Fault-tolerant message delivery (at-least-once, etc.). Best-effort is fine.
- Replacing Claude Code for interactive coding — this is for programmatic /
  agentic workflows.

---

## 3. High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                       Orchestrator Process                     │
│                                                                │
│   ┌──────────────┐      ┌─────────────────────────────┐        │
│   │  Team Lead   │◄────►│  Coordination Tools (MCP)   │        │
│   │  query()     │      │  - assign_task              │        │
│   │  session     │      │  - read_task_board          │        │
│   └──────┬───────┘      │  - send_message             │        │
│          │              │  - read_messages            │        │
│          │              │  - get_teammate_status      │        │
│          │              └──────────────┬──────────────┘        │
│          │                             │                       │
│          ▼                             ▼                       │
│   ┌──────────────────────────────────────────────────┐         │
│   │  Shared State (JSON files on disk, v1)           │         │
│   │  - tasks.jsonl   (append-only task board)        │         │
│   │  - messages/     (per-agent inbox files)         │         │
│   │  - workspace/    (shared files teammates edit)   │         │
│   └──────────────────────────────────────────────────┘         │
│                             ▲                                  │
│          ┌──────────────────┼──────────────────┐               │
│          │                  │                  │               │
│   ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐        │
│   │ Teammate A  │    │ Teammate B  │    │ Teammate C  │        │
│   │ query()     │    │ query()     │    │ query()     │        │
│   │ session     │    │ session     │    │ session     │        │
│   └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Flow

1. User gives a goal to the **Orchestrator**.
2. Orchestrator starts a **Team Lead** session with the goal and access to
   coordination tools.
3. Lead decomposes the goal, writes tasks to the task board, and spawns
   teammates (or assigns tasks to already-running teammates).
4. Each teammate runs as its own `query()` session with its own context
   window and its own tool allowlist, plus access to the coordination tools.
5. Teammates claim tasks, do work (editing files in `workspace/`, running
   commands, calling APIs), and post updates back to the task board.
6. Messages between agents are routed through the shared `messages/` dir.
   The lead polls and can re-prompt teammates with new instructions.
7. When all tasks are done, the lead writes a final synthesis and the
   orchestrator returns.

---

## 4. Tech Stack

- **Language**: Python 3.11+
- **SDK**: `claude-agent-sdk` (official Anthropic package)
- **Config**: YAML for team definitions, JSON for runtime state
- **Testing**: `pytest` + replay harness that re-runs from logged traces
- **Async**: `asyncio` — the SDK is async-first

> **TypeScript alternative**: If the team prefers TS, the SDK has a
> first-class TS package (`@anthropic-ai/claude-agent-sdk`) with the same
> concepts. Everything in this spec maps 1:1.

---

## 5. Proposed File Layout

```
multi-agent-team/
├── pyproject.toml
├── README.md
├── .env.example                # ANTHROPIC_API_KEY etc.
├── teams/
│   └── example_team.yaml       # Team definition (see §7)
├── src/
│   └── mat/                    # "multi-agent team"
│       ├── __init__.py
│       ├── orchestrator.py     # Top-level entry point
│       ├── lead.py             # Team Lead session wrapper
│       ├── teammate.py         # Teammate session wrapper
│       ├── tools/              # Custom MCP tools for coordination
│       │   ├── __init__.py
│       │   ├── task_board.py
│       │   ├── messaging.py
│       │   └── status.py
│       ├── state/              # Shared state abstractions
│       │   ├── task_store.py
│       │   └── message_bus.py
│       ├── config.py           # YAML loading + validation
│       └── logging.py          # Structured event log
├── runs/                       # Created at runtime
│   └── <run_id>/
│       ├── tasks.jsonl
│       ├── messages/
│       ├── workspace/
│       └── trace.jsonl         # All tool calls + messages
├── tests/
│   ├── test_task_store.py
│   ├── test_messaging.py
│   └── test_end_to_end.py      # Uses a canned cheap team
└── examples/
    └── research_team.py        # Demo: 3-person research squad
```

---

## 6. Core Components

### 6.1 `TaskStore` (`src/mat/state/task_store.py`)

Append-only JSONL task board. Each line is a task event:

```json
{"ts": "...", "event": "created", "task_id": "t_001", "title": "...", "assigned_to": null}
{"ts": "...", "event": "claimed", "task_id": "t_001", "agent": "researcher"}
{"ts": "...", "event": "status", "task_id": "t_001", "status": "in_progress"}
{"ts": "...", "event": "completed", "task_id": "t_001", "result_ref": "workspace/research.md"}
```

Methods:

- `create_task(title, description, dependencies=[]) -> task_id`
- `claim_task(task_id, agent) -> bool`
- `update_status(task_id, status, note=None)`
- `list_tasks(filter=None) -> List[Task]`
- `get_task(task_id) -> Task`

Why append-only: full audit trail, easy replay, no locking surprises in v1.

### 6.2 `MessageBus` (`src/mat/state/message_bus.py`)

One inbox file per agent at `runs/<run_id>/messages/<agent_name>.jsonl`.
Writes are append-only; reads track a per-agent cursor in memory.

```python
bus.send(to="reviewer", sender="writer", content="PR is ready at workspace/draft.md")
bus.poll(agent="reviewer") -> List[Message]   # returns unread since last poll
```

v1: process-local, best-effort. v2: swap in Redis streams.

### 6.3 Coordination Tools (`src/mat/tools/`)

These are **custom MCP tools** exposed to every agent (lead and teammates).
The SDK supports defining tools programmatically with `@tool` decorator or
via an in-process MCP server — both documented in the Agent SDK docs.

Tools to expose:

| Tool                | Available to  | Purpose                                          |
| ------------------- | ------------- | ------------------------------------------------ |
| `create_task`       | Lead only     | Add a task to the board                          |
| `assign_task`       | Lead only     | Assign an existing task to a named teammate      |
| `list_tasks`        | All           | See the current board                            |
| `claim_task`        | Teammates     | A teammate takes ownership of a task             |
| `update_task`       | All           | Set status / add notes / post result_ref         |
| `send_message`      | All           | Send a message to another agent (by name)        |
| `read_messages`     | All           | Poll own inbox (returns unread messages)         |
| `get_teammate_info` | All           | List teammates + their current status            |
| `spawn_teammate`    | Lead only     | (v2) Dynamically add a new teammate to the team  |

Tools are small and composable by design. Rich prompts do the heavy lifting.

### 6.4 `TeamLead` (`src/mat/lead.py`)

Wraps a long-running `query()` call. System prompt emphasizes:

- You are the Team Lead. You do NOT write code or do the work yourself.
- Your job: decompose the goal, assign tasks, poll status, unblock teammates,
  synthesize results.
- Use `create_task` and `assign_task` to distribute work.
- Use `read_messages` regularly to see if anyone is blocked or has a question.
- When all tasks are `completed`, write the final synthesis to
  `workspace/OUTPUT.md` and declare done.

Config:

- Model: `opus` (coordination is worth the compute)
- Tools: all coordination tools + `Read`, `Glob`, `Grep` (read-only on
  workspace; lead should not edit files directly)
- `settingSources=['project']` so it picks up `CLAUDE.md` rules

### 6.5 `Teammate` (`src/mat/teammate.py`)

Also wraps a `query()` call, one per teammate, kept alive for the duration
of the run. Key techniques:

- **Resumable sessions**: capture `session_id` from the first invocation;
  pass `resume=session_id` on subsequent prompts so the teammate keeps its
  full context across multiple dispatches.
- **Prompt loop**: the orchestrator calls `teammate.dispatch(prompt)` when
  the lead assigns new work, and the teammate's internal loop runs until
  it voluntarily reports done (via `update_task`) or hits a max-turns cap.
- **Heartbeats**: teammate periodically writes to its status file so the
  lead can detect stalls.

Config (per teammate, from YAML):

```yaml
name: researcher
model: sonnet
description: "Gathers background info, reads docs, summarizes findings."
system_prompt: |
  You are the Researcher on a multi-agent team. You investigate topics
  thoroughly, write findings to workspace/ as markdown, and post updates
  to the task board. Ask the lead via send_message if you need direction.
allowed_tools:
  - Read
  - Glob
  - Grep
  - WebSearch     # if enabled
  - WebFetch
  - Write         # only into workspace/research/
  # plus coordination tools (auto-injected)
```

### 6.6 `Orchestrator` (`src/mat/orchestrator.py`)

The top-level entry point. Responsibilities:

1. Parse the team YAML.
2. Create `runs/<run_id>/` with empty state.
3. Construct the `MessageBus`, `TaskStore`, and coordination MCP server.
4. Construct each `Teammate` (but don't dispatch yet — they're idle).
5. Launch the `TeamLead` with the user goal.
6. Run the event loop:
   - When lead assigns a task → wake the assigned teammate with a
     dispatch prompt ("You have a new task: see task board for t_XXX").
   - When teammate finishes → notify the lead via a message.
   - When a message is sent to any agent → deliver on next poll.
   - When lead writes `workspace/OUTPUT.md` → return it and shut down.
7. On shutdown: flush logs, close sessions, print summary stats
   (tokens used, tasks completed, wall clock).

### 6.7 Event Logging (`src/mat/logging.py`)

Every event (tool call, message, task transition, session start/end) is
appended to `runs/<run_id>/trace.jsonl`. This enables:

- Replay in tests without burning tokens.
- Debugging ("why did the researcher stall?").
- Post-hoc analysis dashboards (future).

---

## 7. Team Definition Format

Teams are defined in YAML so non-engineers can edit them without touching
Python.

```yaml
# teams/research_team.yaml
name: research-squad
lead:
  model: opus
  max_turns: 200
  extra_instructions: |
    Prioritize breadth over depth in the first pass. Once you have
    3 candidate angles, narrow to the most promising and go deep.

teammates:
  - name: researcher
    model: sonnet
    description: "Finds and summarizes background material."
    allowed_tools: [Read, Glob, Grep, WebSearch, WebFetch, Write]
    system_prompt_file: prompts/researcher.md

  - name: analyst
    model: sonnet
    description: "Critically evaluates evidence and identifies gaps."
    allowed_tools: [Read, Glob, Grep, Write]
    system_prompt_file: prompts/analyst.md

  - name: writer
    model: sonnet
    description: "Turns analysis into a polished brief."
    allowed_tools: [Read, Glob, Grep, Write, Edit]
    system_prompt_file: prompts/writer.md

settings:
  workspace_readonly_for_lead: true
  max_parallel_teammates: 3
  stall_timeout_seconds: 300
```

---

## 8. Key SDK APIs We'll Use

Pulled from the current Agent SDK docs — these are the building blocks:

- `claude_agent_sdk.query(prompt, options)` — the core async iterator.
- `ClaudeAgentOptions(allowed_tools=[...], agents={...}, mcp_servers=[...],
  resume=session_id, system_prompt=..., settingSources=[...])`
- `AgentDefinition(description, prompt, tools, model, skills, mcpServers)`
  — we may or may not use built-in SDK subagents inside each teammate, but
  we won't use them as our primary team mechanism because they can't
  communicate with each other.
- **Custom tools via in-process MCP server** — this is how we expose our
  coordination primitives. Docs:
  `platform.claude.com/docs/en/agent-sdk/custom-tools` and
  `platform.claude.com/docs/en/agent-sdk/mcp`.
- **Session resumption** — `resume=session_id` lets a teammate pick up
  exactly where it left off, with full context preserved.
- **Hooks** — `platform.claude.com/docs/en/agent-sdk/hooks` — for
  intercepting tool calls. Useful for auditing or adding guardrails.
- **Permissions** — fine-grained control so e.g. the researcher can't
  accidentally `rm -rf` the workspace.

Before starting implementation, **fetch these docs** and read them fully:

- `https://platform.claude.com/docs/en/agent-sdk/overview`
- `https://platform.claude.com/docs/en/agent-sdk/quickstart`
- `https://platform.claude.com/docs/en/agent-sdk/custom-tools`
- `https://platform.claude.com/docs/en/agent-sdk/mcp`
- `https://platform.claude.com/docs/en/agent-sdk/sessions`
- `https://platform.claude.com/docs/en/agent-sdk/permissions`
- `https://platform.claude.com/docs/en/agent-sdk/python`

The docs evolve; when in doubt, trust the docs over this spec.

---

## 9. Implementation Milestones

### Milestone 1 — Single Teammate + Lead (half day)

- Project scaffolding, `pyproject.toml`, `.env.example`.
- `TaskStore` and `MessageBus` as file-backed classes. Unit tests.
- Coordination MCP server exposing `create_task`, `list_tasks`,
  `update_task`, `send_message`, `read_messages`.
- `Orchestrator` that launches a lead + one teammate.
- Hello-world goal: "Write a haiku about observability to
  workspace/haiku.md". Lead creates a task, teammate does it, done.
- **Acceptance**: end-to-end run succeeds, trace log is readable.

### Milestone 2 — Multi-Teammate Coordination (1–2 days)

- Support N teammates from YAML config.
- Dispatch loop: lead assigns → teammate picks up → completes → lead
  notices and moves on.
- Dependency-aware task ordering (task B waits on task A's `completed`).
- Resumable teammate sessions (second dispatch uses `resume=session_id`).
- **Acceptance**: research-squad example (3 teammates) produces a brief
  from a one-line goal, with evidence trail in the task board.

### Milestone 3 — Inter-Teammate Messaging (1 day)

- Teammates can message each other directly (not just the lead).
- Lead receives a carbon copy of every message by default (configurable).
- Back-pressure: a teammate with >N unread messages gets flagged so the
  lead can intervene.
- **Acceptance**: writer asks researcher a follow-up mid-task; researcher
  responds; writer incorporates answer. All visible in trace.

### Milestone 4 — Hardening (1–2 days)

- Stall detection + auto-nudge ("you've been idle 5 min, status?").
- Token + cost tracking per agent via SDK's cost endpoints.
- Graceful shutdown on Ctrl-C; final state is recoverable.
- Replay harness: re-run a trace without hitting the API (for tests).
- **Acceptance**: test suite + one long-running demo that survives a
  simulated teammate crash.

### Milestone 5 — Nice-to-Haves (open-ended)

- Dynamic `spawn_teammate` from the lead.
- Nested teams (a teammate that is itself an orchestrator).
- Redis-backed `MessageBus` and `TaskStore` for cross-process runs.
- Web dashboard that tails the trace log.
- Per-team-member `skills` and `mcpServers` passthrough.

---

## 10. Open Questions / Decisions to Make

The Claude Code session should surface these explicitly before coding:

1. **Python or TypeScript?** Spec defaults to Python. Confirm before
   scaffolding.
2. **Where do teammates run?** Spec assumes single process with asyncio.
   If we expect long-running workers or isolation, we may want
   subprocesses or containers per teammate — more work, more robust.
3. **Does the lead do any work, or is it pure coordination?** Spec says
   pure coordination (analogous to Agent Teams' "delegate mode"). This
   is usually cleaner, but confirm.
4. **How do we sandbox file writes?** Teammates writing outside
   `workspace/` is a footgun. Use SDK permission hooks to enforce.
5. **Budget caps.** Per-run token budget, per-teammate turn cap, global
   wall-clock timeout. Defaults proposed, confirm numbers.
6. **Observability target.** Just JSONL traces for v1, or do we ship
   OpenTelemetry from the start? Spec says JSONL; OTel in M5.

---

## 11. First Prompt for Claude Code

Once this spec is in the repo, kick off the first session with something like:

> Read `multi-agent-team-spec.md` end-to-end. Then fetch the Agent SDK
> docs listed in §8. Before writing any code, summarize your
> understanding, call out any ambiguities or decisions I need to make
> (§10), and propose a concrete plan for Milestone 1 with file-by-file
> changes. Don't start implementing until I approve the plan.

That forces the session to ground itself in the current SDK docs (which
will be newer than this spec) and makes the first back-and-forth cheap
and high-signal.

---

## 12. Success Criteria

We'll know this is working when:

- A non-trivial goal ("produce a competitive analysis of X") runs
  end-to-end with 3+ teammates, coordinated by the lead, and produces a
  coherent output.
- The full trace is replayable from the JSONL log.
- Adding a new teammate role is a YAML edit + a prompt file, no code
  changes.
- We can swap out the underlying model per teammate without touching
  orchestration code.
- A developer new to the project can read this spec + the code and be
  productive in under a day.
