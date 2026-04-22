# Multi-Agent Team (mat)

Team Lead + N Teammates on the Claude Agent SDK. See [multi-agent-team-spec.md](multi-agent-team-spec.md) for the full design.

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS/Linux

pip install -e ".[dev]"

cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY

python hello_sdk.py              # SDK smoke test
pytest                           # run the test suite
```

## Layout

- `src/mat/` — package (orchestrator, lead, teammate, coordination tools, state)
- `hello_sdk.py` — minimal `query()` + custom MCP tool round-trip to verify SDK wiring
- `teams/` — YAML team definitions and system-prompt files
- `tests/` — pytest suite
- `runs/` — per-run state created at runtime (gitignored)

## Status

Milestone 0: scaffolding only. Module bodies are `NotImplementedError` stubs. Milestone 1 (single lead + one teammate, haiku hello-world) is next.
