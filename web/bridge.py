"""
Shared MCP + Groq bridge used by the web UI.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

MEMORY_SERVER = ROOT / "expt1_memory_server" / "server.py"
WEATHER_SERVER = ROOT / "expt2_weather_dashboard" / "server.py"


def _has_api_key() -> bool:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return bool(key) and "your" not in key.lower()


def _openai_client():
    from openai import OpenAI

    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )


def _model() -> str:
    return os.getenv("OPENAI_MODEL", "openai/gpt-oss-20b")


def mcp_tools_to_openai(tools) -> list[dict]:
    out = []
    for t in tools:
        schema = getattr(t, "input_schema", None) or getattr(t, "inputSchema", None)
        out.append(
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": schema or {"type": "object", "properties": {}},
                },
            }
        )
    return out


def _tool_text(result) -> str:
    return "\n".join(
        getattr(b, "text", "") for b in result.content if getattr(b, "text", None)
    )


def memory_local_router(user_text: str) -> tuple[str, dict]:
    lower = user_text.lower().strip()
    save_hints = ("remember", "save", "note that", "store", "write down")
    if any(h in lower for h in save_hints):
        content = user_text
        for h in save_hints:
            content = content.replace(h, "").replace(h.title(), "")
        content = content.strip(" :,-")
        return "save_note", {"content": content or user_text, "tags": "personal"}
    return "search_notes", {"query": user_text}


def weather_local_router(user_text: str) -> tuple[str, dict]:
    patterns = [
        r"weather\s+(?:in|for|at)\s+(.+)",
        r"(?:in|for|at)\s+([A-Za-z][A-Za-z\s\-']+)$",
    ]
    for pat in patterns:
        m = re.search(pat, user_text.strip(), re.IGNORECASE)
        if m:
            return "get_current_weather", {"location": m.group(1).strip(" ?.!,")}
    parts = user_text.strip().rstrip("?").split()
    return "get_current_weather", {"location": parts[-1] if parts else "Tokyo"}


def choose_tool(
    user_text: str,
    openai_tools: list[dict],
    *,
    system: str,
    local_router,
) -> tuple[str, str, dict]:
    if not _has_api_key():
        name, args = local_router(user_text)
        thought = (
            f"[Local router] No API key.\n-> Chosen tool: {name}({json.dumps(args)})"
        )
        return thought, name, args

    client = _openai_client()
    response = client.chat.completions.create(
        model=_model(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ],
        tools=openai_tools,
        tool_choice="required",
    )
    msg = response.choices[0].message
    thought = msg.content or "(LLM chose a tool without free-text reasoning.)"
    call = msg.tool_calls[0]
    name = call.function.name
    args = json.loads(call.function.arguments or "{}")
    thought += f"\n-> Chosen tool: {name}({json.dumps(args)})"
    return thought, name, args


def summarize(user_text: str, tool_name: str, tool_text: str, system: str) -> str:
    if not _has_api_key():
        return tool_text
    client = _openai_client()
    final = client.chat.completions.create(
        model=_model(),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
            {
                "role": "assistant",
                "content": f"Tool {tool_name} returned:\n{tool_text}",
            },
        ],
    )
    return final.choices[0].message.content or tool_text


async def run_mcp_query(
    server_script: Path,
    user_text: str,
    *,
    system_choose: str,
    system_summarize: str,
    local_router,
) -> dict:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_script)],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            tools = mcp_tools_to_openai(listed.tools)
            thought, tool_name, arguments = choose_tool(
                user_text,
                tools,
                system=system_choose,
                local_router=local_router,
            )
            result = await session.call_tool(tool_name, arguments)
            tool_text = _tool_text(result)
            answer = summarize(user_text, tool_name, tool_text, system_summarize)
            return {
                "thought": thought,
                "tool": tool_name,
                "arguments": arguments,
                "tool_result": tool_text,
                "answer": answer,
            }


async def ask_memory(user_text: str) -> dict:
    return await run_mcp_query(
        MEMORY_SERVER,
        user_text,
        system_choose=(
            "You are a personal memory assistant. "
            "Use save_note to store info. Use search_notes when asked about past notes. "
            "Use list_notes / delete_note when appropriate. Always call exactly one tool."
        ),
        system_summarize="Summarize the tool result for the user briefly.",
        local_router=memory_local_router,
    )


async def ask_weather(user_text: str) -> dict:
    return await run_mcp_query(
        WEATHER_SERVER,
        user_text,
        system_choose=(
            "You help users with live weather. "
            "Always call get_current_weather with the city name. "
            "Briefly explain your reasoning."
        ),
        system_summarize="Turn the weather data into a short friendly summary.",
        local_router=weather_local_router,
    )
