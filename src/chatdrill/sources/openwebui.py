"""pass01 — load a chat from OpenWebUI's ``webui.db`` (the simplest source).

The ``chat`` table stores each conversation as a JSON blob in the ``chat``
column. ``chat.history.messages`` is the tree (id -> message, parentId /
childrenIds) and ``chat.history.currentId`` is the leaf of the canonical path.

This adapter reads that straight out of SQLite and normalizes it to a
``RawChat``. No OpenWebUI install or UI export needed.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Iterator, Optional

from ..models import RawChat, RawMessage


def _db_path(db: Optional[str] = None) -> Path:
    """Resolve the webui.db path: explicit arg > $OPENWEBUI_DB > default."""
    p = db or os.environ.get("OPENWEBUI_DB") or str(
        Path.home() / "myopenwebui" / "webui.db")
    path = Path(p).expanduser()
    if not path.exists():
        raise FileNotFoundError(
            f"webui.db not found at {path}. Pass --db PATH or set OPENWEBUI_DB "
            f"in .env.")
    return path


def _connect(db: Optional[str] = None) -> sqlite3.Connection:
    # read-only URI so we never risk mutating the user's live db
    path = _db_path(db)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def list_chats(db: Optional[str] = None, limit: int = 50) -> list[dict]:
    """(id, title, message-count) for the most-recently-updated chats."""
    out: list[dict] = []
    with _connect(db) as con:
        rows = con.execute(
            "SELECT id, title, chat FROM chat WHERE chat IS NOT NULL "
            "ORDER BY updated_at DESC LIMIT ?", (limit,))
        for r in rows:
            try:
                d = json.loads(r["chat"])
            except (json.JSONDecodeError, TypeError):
                continue
            n = len(d.get("history", {}).get("messages", {}) or {})
            out.append({"id": r["id"], "title": r["title"] or "", "messages": n})
    return out


def _to_message(mid: str, m: dict) -> RawMessage:
    return RawMessage(
        id=m.get("id", mid),
        parent_id=m.get("parentId"),
        children_ids=list(m.get("childrenIds") or []),
        role=m.get("role", "user"),
        content=m.get("content") or "",
        timestamp=m.get("timestamp"),
        model_name=m.get("modelName") or m.get("model"),
        model_idx=m.get("modelIdx"),
    )


def _raw_chat_from_blob(cid: str, title: str, d: dict) -> RawChat:
    hist = d.get("history", {}) or {}
    msgs = hist.get("messages", {}) or {}
    tree = {mid: _to_message(mid, m) for mid, m in msgs.items()}
    return RawChat(
        id=cid,
        title=title or d.get("title", ""),
        source="openwebui:webui.db",
        models=list(d.get("models") or []),
        created_at=d.get("timestamp"),
        tree=tree,
        current_id=hist.get("currentId"),
    )


def resolve_id(chat_id: str, db: Optional[str] = None) -> str:
    """The canonical full id for an exact id or a unique prefix. Cheap (id only)."""
    with _connect(db) as con:
        row = con.execute("SELECT id FROM chat WHERE id = ?", (chat_id,)).fetchone()
        if row is not None:
            return row["id"]
        cands = con.execute(
            "SELECT id FROM chat WHERE id LIKE ?", (chat_id + "%",)).fetchall()
        if len(cands) == 1:
            return cands[0]["id"]
        if len(cands) > 1:
            raise ValueError(
                f"chat id prefix {chat_id!r} is ambiguous "
                f"({len(cands)} matches) — give more characters.")
        raise KeyError(f"no chat with id (or prefix) {chat_id!r}")


def load_chat(chat_id: str, db: Optional[str] = None) -> RawChat:
    """Load one chat by id (full id or unique prefix) into a RawChat."""
    full = resolve_id(chat_id, db)
    with _connect(db) as con:
        row = con.execute(
            "SELECT id, title, chat FROM chat WHERE id = ?", (full,)).fetchone()
        d = json.loads(row["chat"])
        return _raw_chat_from_blob(row["id"], row["title"], d)


def iter_chats(db: Optional[str] = None) -> Iterator[RawChat]:
    """Stream every chat as a RawChat (for batch/corpus processing)."""
    with _connect(db) as con:
        for r in con.execute(
                "SELECT id, title, chat FROM chat WHERE chat IS NOT NULL"):
            try:
                d = json.loads(r["chat"])
            except (json.JSONDecodeError, TypeError):
                continue
            yield _raw_chat_from_blob(r["id"], r["title"], d)


# -- Source interface --------------------------------------------------------
# Thin wrapper so OpenWebUI plugs into the provider registry. The module-level
# functions above stay the working API; this just adapts them.
from .base import Source                          # noqa: E402  (avoid import cycle)
import re as _re                                  # noqa: E402

_CHATID = _re.compile(r"^[0-9a-fA-F-]{6,}$")       # a chat-id or hex prefix


class OpenWebUISource(Source):
    name = "openwebui"

    def __init__(self, db: Optional[str] = None):
        self.db = db

    def matches(self, ref: str) -> bool:
        # a local webui.db path, or a bare chat-id / hex prefix
        return ref.endswith(".db") or bool(_CHATID.match(ref))

    def load(self, ref: str) -> RawChat:
        return load_chat(ref, db=self.db)

    def list_chats(self, limit: int = 50) -> list[dict]:
        return list_chats(db=self.db, limit=limit)

    def iter_chats(self) -> Iterator[RawChat]:
        return iter_chats(db=self.db)
