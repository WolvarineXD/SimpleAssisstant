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
│   ├── client.py            # CLI client
│   └── notes.json
├── expt2_weather_dashboard/ # Data Dashboard Connector
│   ├── server.py            # MCP tool: get_current_weather (wttr.in)
│   └── client.py            # CLI client
├── web/                     # Browser UI for both experiments
│   ├── app.py
│   ├── bridge.py
│   ├── templates/
│   └── static/
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup

```bash
# Use Windows Python 3.12 (NOT bare `python` — that may be MSYS 3.14 without packages)
py -3.12 -m pip install -r requirements.txt
copy .env.example .env   # add your Groq key from https://console.groq.com/keys
```

Clients use **Groq** (OpenAI-compatible API: `openai/gpt-oss-20b`).
Without a key, a **local router** still demonstrates MCP tool calls.

---

## Web UI (recommended)

```bash
py -3.12 web/app.py
# or double-click run_web.bat
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000)

| Page | URL |
|------|-----|
| Home | `/` |
| Memory assistant | `/memory` |
| Weather dashboard | `/weather` |

Each page shows **thought process → tool result → final answer**.

---

## Expt 1 — Personal Assistant Memory Server

**Objective:** MCP server with CRUD-style note tools backed by `notes.json`.

| Tool | Role |
|------|------|
| `save_note(content, tags)` | Create |
| `search_notes(query)` | Read / search |
| `list_notes()` | Read all |
| `delete_note(note_id)` | Delete |

**CLI:**

```bash
py -3.12 expt1_memory_server/client.py
# or double-click run_expt1.bat
```

**Try:**

```
Remember: the project deadline is Friday
What did I say about the project deadline?
```

---

## Expt 2 — Data Dashboard Connector

**Objective:** Context enhancement — live external data via MCP.

| Tool | Role |
|------|------|
| `get_current_weather(location)` | Fetch structured weather from [wttr.in](https://wttr.in) |

**CLI:**

```bash
py -3.12 expt2_weather_dashboard/client.py
# or double-click run_expt2.bat
```

**Try:**

```
What's the weather in Tokyo?
```

---

## How MCP fits

```
User query -> Client (LLM picks a tool) -> MCP Server (runs tool) -> result -> Client answer
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
- Packages: `mcp`, `openai`, `httpx`, `python-dotenv`, `flask`
