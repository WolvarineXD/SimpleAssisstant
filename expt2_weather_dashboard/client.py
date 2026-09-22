"""
Expt 2 — MCP Client for the Data Dashboard (weather).

Shows the LLM's thought process (tool decision), then the final answer.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

SERVER_SCRIPT = Path(__file__).resolve().parent / "server.py"


def mcp_tools_to_openai(tools) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": (
                    getattr(t, "input_schema", None)
                    or getattr(t, "inputSchema", None)
                    or {"type": "object", "properties": {}}
                ),
            },
        }
        for t in tools
    ]


def extract_location(user_text: str) -> str:
    """Simple location extractor for local-router fallback."""
    patterns = [
        r"weather\s+(?:in|for|at)\s+(.+)",
        r"(?:in|for|at)\s+([A-Za-z][A-Za-z\s\-']+)$",
    ]
    for pat in patterns:
        m = re.search(pat, user_text.strip(), re.IGNORECASE)
        if m:
            return m.group(1).strip(" ?.!,")
    # last word fallback
    parts = user_text.strip().rstrip("?").split()
    return parts[-1] if parts else "Tokyo"


def local_router(user_text: str) -> tuple[str, dict]:
    location = extract_location(user_text)
    return "get_current_weather", {"location": location}


async def call_llm(user_text: str, openai_tools: list[dict]) -> tuple[str, str, dict]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or "your" in api_key.lower():
        thought = (
            "[Thought process]\n"
            "1. User is asking about weather / live data.\n"
            "2. I should call get_current_weather.\n"
        )
        name, args = local_router(user_text)
        thought += f"3. Decision -> {name}({json.dumps(args)})"
        return thought, name, args

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-20b")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You help users with live weather. "
                    "Always call get_current_weather with the city name. "
                    "Briefly explain your reasoning in the message content."
                ),
            },
            {"role": "user", "content": user_text},
        ],
        tools=openai_tools,
        tool_choice="required",
    )

    msg = response.choices[0].message
    thought = "[Thought process]\n" + (
        msg.content or "LLM decided a tool is needed."
    )
    call = msg.tool_calls[0]
    name = call.function.name
    args = json.loads(call.function.arguments or "{}")
    thought += f"\n-> Tool call: {name}({json.dumps(args)})"
    return thought, name, args


async def run_once(session: ClientSession, user_text: str) -> None:
    listed = await session.list_tools()
    openai_tools = mcp_tools_to_openai(listed.tools)

    print("\n" + "=" * 50)
    thought, tool_name, arguments = await call_llm(user_text, openai_tools)
    print(thought)
    print("=" * 50)

    print("\n[Calling MCP server...]")
    result = await session.call_tool(tool_name, arguments)
    tool_text = "\n".join(
        getattr(b, "text", "") for b in result.content if getattr(b, "text", None)
    )
    print("\n--- Raw tool result ---")
    print(tool_text)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key and "your" not in api_key.lower():
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        )
        final = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "openai/gpt-oss-20b"),
            messages=[
                {
                    "role": "system",
                    "content": "Turn the weather data into a short friendly summary.",
                },
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": tool_text},
            ],
        )
        print("\n--- Final answer ---")
        print(final.choices[0].message.content)
    else:
        print("\n--- Final answer ---")
        print(tool_text)


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
    )

    print("Data Dashboard — Weather Connector")
    print('Try: What\'s the weather in Tokyo?')
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
