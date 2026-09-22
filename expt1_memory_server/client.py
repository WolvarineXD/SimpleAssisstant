"""
Expt 1 — MCP Client for the Personal Assistant Memory Server.

Connects to the MCP server over stdio, then uses an LLM (or a simple
local router if no API key is set) to choose save_note / search_notes.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SERVER_SCRIPT = Path(__file__).resolve().parent / "server.py"


def mcp_tools_to_openai(tools) -> list[dict]:
    converted = []
    for t in tools:
        schema = getattr(t, "input_schema", None) or getattr(t, "inputSchema", None)
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": schema or {"type": "object", "properties": {}},
                },
            }
        )
    return converted


def local_router(user_text: str) -> tuple[str, dict]:
    """Fallback when OPENAI_API_KEY is missing — mimics LLM tool choice."""
    lower = user_text.lower().strip()
    save_hints = ("remember", "save", "note that", "store", "write down")
    if any(h in lower for h in save_hints):
        content = user_text
        for h in save_hints:
            content = content.replace(h, "").replace(h.title(), "")
        content = content.strip(" :,-")
        return "save_note", {"content": content or user_text, "tags": "personal"}
    return "search_notes", {"query": user_text}


async def call_llm(user_text: str, openai_tools: list[dict]) -> tuple[str, str, dict]:
    """
    Returns (thought, tool_name, arguments).
    Uses OpenAI tool-calling when a key is present.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-your"):
        thought = (
            "[Local router] No OPENAI_API_KEY — deciding from keywords…"
        )
        name, args = local_router(user_text)
        thought += f"\n→ Chosen tool: {name}({json.dumps(args)})"
        return thought, name, args

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a personal memory assistant. "
                "Use save_note to store information the user wants remembered. "
                "Use search_notes when the user asks about past notes. "
                "Use list_notes / delete_note when appropriate. "
                "Always call exactly one tool."
            ),
        },
        {"role": "user", "content": user_text},
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=openai_tools,
        tool_choice="required",
    )

    msg = response.choices[0].message
    thought = msg.content or "(LLM chose a tool without free-text reasoning.)"
    if not msg.tool_calls:
        raise RuntimeError("LLM did not request a tool.")

    call = msg.tool_calls[0]
    name = call.function.name
    args = json.loads(call.function.arguments or "{}")
    thought += f"\n→ Chosen tool: {name}({json.dumps(args)})"
    return thought, name, args


async def run_once(session: ClientSession, user_text: str) -> None:
    listed = await session.list_tools()
    openai_tools = mcp_tools_to_openai(listed.tools)

    print("\n--- Thought process ---")
    thought, tool_name, arguments = await call_llm(user_text, openai_tools)
    print(thought)

    print("\n--- Tool result ---")
    result = await session.call_tool(tool_name, arguments)
    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            print(text)

    # Optional: ask LLM to phrase a final answer when API key exists
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key and not api_key.startswith("sk-your"):
        from openai import OpenAI

        tool_text = "\n".join(
            getattr(b, "text", "") for b in result.content if getattr(b, "text", None)
        )
        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        )
        final = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the tool result for the user briefly.",
                },
                {"role": "user", "content": user_text},
                {
                    "role": "assistant",
                    "content": f"Tool {tool_name} returned:\n{tool_text}",
                },
            ],
        )
        print("\n--- Final answer ---")
        print(final.choices[0].message.content)


async def main() -> None:
    if not SERVER_SCRIPT.exists():
        print(f"Server not found: {SERVER_SCRIPT}", file=sys.stderr)
        sys.exit(1)

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
    )

    print("Personal Assistant Memory Client")
    print("Examples:")
    print('  Remember: the project deadline is Friday')
    print('  What did I say about the project deadline?')
    print("Type 'quit' to exit.\n")

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Connected. Tools:", ", ".join(t.name for t in tools.tools))

            while True:
                try:
                    user_text = input("\nYou> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nBye.")
                    break
                if not user_text:
                    continue
                if user_text.lower() in {"quit", "exit", "q"}:
                    print("Bye.")
                    break
                await run_once(session, user_text)


if __name__ == "__main__":
    asyncio.run(main())
