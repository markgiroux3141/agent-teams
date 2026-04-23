# Multi-Agent Team (mat)

A Python orchestrator for running a **Team Lead** + N **Teammates** on top of the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). Built for headless multi-agent workflows — structured debate, design review, pre/post-mortems, parallel build-outs — that don't fit inside Claude Code's interactive mode or its built-in subagents.

See [multi-agent-team-spec.md](multi-agent-team-spec.md) for the full design doc.

## Why mat exists

Claude Code's two built-in coordination options — subagents (fire-and-forget, can't talk to each other) and Agent Teams (capped ~3–5 teammates, no nesting, experimental) — run out of room when you need:

- More than ~5 concurrent agents
- Nested teams (team-of-teams)
- Dynamic team composition at runtime
- Headless / service deployment (no TTY)
- Custom coordination protocols (debate, voting, negotiation, peer review)

mat keeps everything Claude Code gives you (filesystem tools, context compaction, MCP, permissions, hooks) by building directly on the same SDK, and layers orchestration on top.

## How it works

```
┌──────────────────────────────────────────────────────────┐
│                   Orchestrator (asyncio)                 │
│                                                          │
│   ┌──────────────┐      ┌───────────────────────────┐    │
│   │  Team Lead   │◄────►│ Coordination MCP server   │    │
│   │  (one)       │      │  create_task / assign     │    │
│   └──────┬───────┘      │  update_task / finalize   │    │
│          │              │  send_message / read_msgs │    │
│          ▼              └───────────────────────────┘    │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐   ...      │
│   │ Teammate1 │  │ Teammate2 │  │ Teammate3 │            │
│   └─────┬─────┘  └─────┬─────┘  └─────┬─────┘            │
│         │              │              │                  │
│         ▼              ▼              ▼                  │
│   ┌────────────────────────────────────────────────┐     │
│   │ runs/<ts>/  tasks.jsonl · messages/ ·          │     │
│   │             workspace/ · trace.jsonl           │     │
│   └────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────┘
```

- **Team Lead** — single coordinator. Decomposes the goal, assigns tasks, monitors status, synthesizes results, and calls `finalize(...)` when done. Read-only on the workspace.
- **Teammates** — N specialized agents, each with its own model, tool allowlist, and system prompt. Sessions are long-lived and resumable via `session_id`, so context isn't re-paid each turn.
- **Task board** — append-only JSONL (`tasks.jsonl`) with `created` / `assigned` / `status` / `completed` events. Tasks support dependency chains.
- **Message bus** — per-agent inbox files under `messages/<agent>.jsonl`.
- **Coordination MCP server** — in-process tools: `create_task`, `assign_task`, `update_task`, `list_tasks`, `send_message`, `read_messages`, `finalize`.

## Quickstart

Requires Python ≥ 3.11 (see [pyproject.toml](pyproject.toml)).

```bash
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS/Linux

pip install -e ".[dev]"
cp .env.example .env             # then set ANTHROPIC_API_KEY

python hello_sdk.py              # SDK + custom MCP tool round-trip
python examples/haiku.py         # smallest real run: lead + 1 teammate
```

Every example takes an optional goal or `--scenario` arg; check the top of each file for usage.

## Examples

| Script | Team | What it shows |
|---|---|---|
| [examples/haiku.py](examples/haiku.py) | haiku-team | Minimal lead + 1 teammate, single task end-to-end |
| [examples/steelman.py](examples/steelman.py) | steelman-team | 10-turn structured debate, dependency-chained tasks, early-exit check |
| [examples/steelman_inlined.py](examples/steelman_inlined.py) | steelman-team-inlined | A/B variant that inlines prior turns into each prompt |
| [examples/design_review.py](examples/design_review.py) | design-review-team | Parallel critiques + rebuttal with a multi-dep task |
| [examples/recipes.py](examples/recipes.py) | recipes-team | Two-phase negotiate-then-build across 4 roles |
| [examples/postmortem.py](examples/postmortem.py) | postmortem-team | Four-angle post-incident synthesis |
| [examples/premortem.py](examples/premortem.py) | premortem-team | Risk register for a planned refactor |
| [examples/standup.py](examples/standup.py) | standup-team | Daily standup across 3 roles |
| [examples/refactor.py](examples/refactor.py) | refactor-loop-team | Dev + critic loop over shared code |
| [examples/research.py](examples/research.py) | research squad | Researcher / analyst / writer pipeline |
| [examples/shutdown.py](examples/shutdown.py) | shutdown-team | Service-sunset review across 3 roles |
| [examples/score_debate.py](examples/score_debate.py) | — | Meta-runner that scores debate outputs |

Scenarios (project briefs, role context) live under [examples/scenarios/](examples/scenarios/) — `recipes_site`, `checkout_refactor`, `checkout_outage`, `checkout_refactor_premortem`, `rate_limit_service`.

## Anatomy of a run

Each run writes to `runs/<UTC timestamp>/`:

- `workspace/OUTPUT.md` — final synthesis the lead wrote via `finalize()`. The user-facing deliverable.
- `workspace/` — shared files teammates write (debate turns, critiques, SPEC.md, DONE_CRITERIA.md, etc.).
- `tasks.jsonl` — append-only task board.
- `messages/<agent>.jsonl` — per-agent inbox.
- `trace.jsonl` — every turn, block, tool call, message, and state transition. Full audit trail.
- `run_summary.json` — per-agent and total cost, tokens, turn counts.
- `report.html` / `report.md` / `sequence.md` / `playback.html` — generated analysis views. Produced by [src/mat/report.py](src/mat/report.py) and [src/mat/replay.py](src/mat/replay.py); run `python -m mat.report runs/<ts>` to regenerate.

## Authoring your own team

The smallest possible team is [teams/haiku_team.yaml](teams/haiku_team.yaml) — copy it as a template.

1. Write `teams/my_team.yaml` with `lead:` and `teammates:` sections. Each entry sets `model`, `max_turns`, `allowed_tools`, and `system_prompt_file`.
2. Write the prompt Markdown files under [teams/prompts/](teams/prompts/) (one per role).
3. Copy [examples/haiku.py](examples/haiku.py) as a runner, swap in your team YAML path and goal, and run it.

The full YAML schema and coordination-tool reference are in [multi-agent-team-spec.md](multi-agent-team-spec.md).

## Layout

- [src/mat/](src/mat/) — orchestrator package
  - `orchestrator.py` — event loop
  - `lead.py`, `teammate.py` — agent wrappers around `ClaudeSDKClient`
  - `state/` — `task_store.py`, `message_bus.py`
  - `tools/` — coordination MCP tools (`task_board`, `messaging`, `status`)
  - `config.py`, `logging.py`, `report.py`, `replay.py`
- [teams/](teams/) — YAML team definitions + [teams/prompts/](teams/prompts/) system-prompt Markdown
- [examples/](examples/) — runner scripts + [examples/scenarios/](examples/scenarios/) briefs
- [tests/](tests/) — pytest suite
- [hello_sdk.py](hello_sdk.py) — SDK smoke test
- [multi-agent-team-spec.md](multi-agent-team-spec.md) — full design spec
- `runs/` — runtime output (gitignored)

## Status

Version `0.0.1`. The orchestrator, coordination MCP tools, cost tracking, and replay/reporting are implemented; all 10+ example teams in this repo run end-to-end; the pytest suite passes. Expect rough edges — stall timeouts are conservative, there is no retry-on-API-error logic yet, and coordination v2 items from the spec (direct teammate-to-teammate channels, nested sub-teams) are not yet built.
