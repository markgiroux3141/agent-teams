"""Smoke test: prove the Claude Agent SDK + API key + custom MCP tool wiring all work.

Run with: `python hello_sdk.py` (after installing deps and setting ANTHROPIC_API_KEY in .env).

What this exercises:
- Package imports (`query`, `ClaudeAgentOptions`, `tool`, `create_sdk_mcp_server`)
- A trivial in-process MCP server with one custom tool (`echo`)
- Streaming message iteration (`SystemMessage`, `AssistantMessage`, `ResultMessage`)
- Final cost accounting from `ResultMessage.total_cost_usd`

If this prints a result and a non-zero cost, the scaffolding is ready for Milestone 1.
"""

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)


@tool("echo", "Echo the given text back to the caller.", {"text": str})
async def echo(args: dict) -> dict:
    return {"content": [{"type": "text", "text": f"echo: {args['text']}"}]}


async def main() -> int:
    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")
        return 1

    model = os.environ.get("ANTHROPIC_MODEL")
    print(f"[startup] model={model or '<sdk default>'}")

    server = create_sdk_mcp_server(name="demo", version="0.0.1", tools=[echo])
    options = ClaudeAgentOptions(
        mcp_servers={"demo": server},
        allowed_tools=["mcp__demo__echo"],
        max_turns=3,
        model=model,
    )

    prompt = (
        "Call the echo tool with text 'hello from mat'. "
        "Then tell me in one sentence what you did."
    )

    final_cost: float | None = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, SystemMessage):
            print(f"[system] subtype={getattr(message, 'subtype', '?')}")
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"[tool_use] {block.name}({block.input})")
                elif isinstance(block, TextBlock):
                    print(f"[assistant] {block.text}")
        elif isinstance(message, ResultMessage):
            final_cost = getattr(message, "total_cost_usd", None)
            print(f"[result] subtype={getattr(message, 'subtype', '?')} cost=${final_cost}")

    if final_cost is None:
        print("ERROR: no ResultMessage received — something is wrong with SDK wiring.")
        return 2

    print("OK: SDK round-trip succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
