# SimpleAssisstant — WLLM Lab 6

Use **AI Coding Assistants** for code generation, testing, debugging, refactoring,
documentation, and tool comparison — via two Model Context Protocol (MCP) experiments.

Repository: [WolvarineXD/SimpleAssisstant](https://github.com/WolvarineXD/SimpleAssisstant)

---

## Project layout

```
SimpleAssisstant/
├── expt1_memory_server/     # Personal Assistant Memory Server
│   ├── server.py            # MCP tools: save / search / list / delete notes
│   ├── client.py            # LLM decides which tool to call
│   └── notes.json           # Local note store
├── expt2_weather_dashboard/ # Data Dashboard Connector
│   ├── server.py            # MCP tool: get_current_weather (wttr.in)
│   └── client.py            # Shows thought process + final answer
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # optional: add OPENAI_API_KEY for real LLM routing
```

Without an API key, both clients use a **local router** that still demonstrates
MCP tool calls and prints a visible “thought process”.

---

## Expt 1 — Personal Assistant Memory Server

**Objective:** MCP server with CRUD-style note tools backed by `notes.json`.

| Tool | Role |
|------|------|
| `save_note(content, tags)` | Create |
| `search_notes(query)` | Read / search |
| `list_notes()` | Read all |
| `delete_note(note_id)` | Delete |

**Run the client** (it starts the MCP server over stdio):

```bash
python expt1_memory_server/client.py
```

**Try:**

```
Remember: the project deadline is Friday
What did I say about the project deadline?
```

The client shows:

1. Thought process (LLM or local router choosing a tool)
2. Tool result from the MCP server
3. Final answer (when an OpenAI key is set)

---

## Expt 2 — Data Dashboard Connector

**Objective:** Context enhancement — live external data via MCP.

| Tool | Role |
|------|------|
| `get_current_weather(location)` | Fetch structured weather from [wttr.in](https://wttr.in) |

**Run:**

```bash
python expt2_weather_dashboard/client.py
```

**Try:**

```
What's the weather in Tokyo?
```

The client prints the LLM’s tool decision, the raw MCP result, then a short summary.

---

## How MCP fits

```
User query → Client (LLM picks a tool) → MCP Server (runs tool) → result → Client answer
```

- **Server** exposes tools over **stdio**.
- **Client** lists tools, asks an LLM (or local router) which one to call, then `call_tool`.

---

## Tool comparison (lab notes)

| Aspect | Expt 1 Memory | Expt 2 Weather |
|--------|---------------|----------------|
| Data source | Local `notes.json` | Public HTTP API |
| Use case | Persistent personal memory | Real-time context |
| CRUD | Create / Read / Delete | Read-only fetch |
| Offline | Works without network | Needs network |

---

## Requirements

- Python 3.10+
- Packages: `mcp`, `openai`, `httpx`, `python-dotenv`
