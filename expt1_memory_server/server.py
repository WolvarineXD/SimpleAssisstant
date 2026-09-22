"""
Expt 1 — Personal Assistant Memory Server (MCP)

Tools:
  - save_note(content, tags)  → write to notes.json
  - search_notes(query)       → search notes.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

NOTES_FILE = Path(__file__).resolve().parent / "notes.json"

mcp = MCPServer("personal-assistant-memory")


def _load_notes() -> list[dict[str, Any]]:
    if not NOTES_FILE.exists():
        return []
    try:
        data = json.loads(NOTES_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_notes(notes: list[dict[str, Any]]) -> None:
    NOTES_FILE.write_text(
        json.dumps(notes, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


@mcp.tool()
def save_note(content: str, tags: str = "") -> str:
    """Save a personal note with optional comma-separated tags.

    Args:
        content: The note text to remember.
        tags: Optional comma-separated tags, e.g. "work,deadline".
    """
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    note = {
        "id": len(_load_notes()) + 1,
        "content": content.strip(),
        "tags": tag_list,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    notes = _load_notes()
    notes.append(note)
    _save_notes(notes)
    return (
        f"Saved note #{note['id']}: {note['content'][:80]}"
        + ("…" if len(note["content"]) > 80 else "")
        + (f" | tags: {', '.join(tag_list)}" if tag_list else "")
    )


@mcp.tool()
def search_notes(query: str) -> str:
    """Search saved notes by keyword in content or tags.

    Args:
        query: Text to look for in note content or tags.
    """
    q = query.strip().lower()
    if not q:
        return "Please provide a search query."

    matches = []
    for note in _load_notes():
        haystack = " ".join(
            [note.get("content", ""), " ".join(note.get("tags", []))]
        ).lower()
        if q in haystack or any(word in haystack for word in q.split()):
            matches.append(note)

    if not matches:
        return f"No notes found for: {query!r}"

    lines = [f"Found {len(matches)} note(s) for {query!r}:"]
    for n in matches:
        tags = ", ".join(n.get("tags", [])) or "none"
        lines.append(
            f"  #{n['id']} [{n.get('created_at', '?')}] "
            f"(tags: {tags})\n     {n['content']}"
        )
    return "\n".join(lines)


@mcp.tool()
def list_notes() -> str:
    """List all saved notes (CRUD: Read all)."""
    notes = _load_notes()
    if not notes:
        return "No notes saved yet."
    lines = [f"Total notes: {len(notes)}"]
    for n in notes:
        tags = ", ".join(n.get("tags", [])) or "none"
        lines.append(f"  #{n['id']} (tags: {tags}) — {n['content']}")
    return "\n".join(lines)


@mcp.tool()
def delete_note(note_id: int) -> str:
    """Delete a note by its id (CRUD: Delete).

    Args:
        note_id: Numeric id of the note to remove.
    """
    notes = _load_notes()
    remaining = [n for n in notes if n.get("id") != note_id]
    if len(remaining) == len(notes):
        return f"No note found with id={note_id}."
    _save_notes(remaining)
    return f"Deleted note #{note_id}."


if __name__ == "__main__":
    mcp.run(transport="stdio")
