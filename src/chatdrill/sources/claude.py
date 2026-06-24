"""Claude.ai export encoder — normalize a conversations.json to RawChat.

Claude's data export (Settings → Export data, a .zip) carries a
``conversations.json``: a list of conversations, each with ``uuid``, ``name``,
``created_at`` and ``chat_messages``. Each message has ``sender``
(human/assistant), a flat ``text`` (and a ``content`` block list), ``created_at``
and ``parent_message_uuid``. Messages are linear, so we synthesize a linear chat
tree — the same RawChat the rest of the pipeline consumes.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Iterator, Optional

from ..models import RawChat, RawMessage

_ROLE = {"human": "user", "assistant": "assistant", "user": "user"}


def _load(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, list) else [data]


def is_claude_export(path: str | Path) -> bool:
    try:
        data = _load(path)
    except (json.JSONDecodeError, OSError):
        return False
    return bool(data) and isinstance(data[0], dict) and "chat_messages" in data[0]


def _ts(s: str) -> Optional[int]:
    try:
        return int(datetime.datetime.fromisoformat(
            (s or "").replace("Z", "+00:00")).timestamp())
    except Exception:
        return None


def _text(m: dict) -> str:
    if m.get("text"):
        return m["text"]
    parts = [b.get("text", "") for b in (m.get("content") or [])
             if isinstance(b, dict) and b.get("type") == "text"]
    return "\n".join(p for p in parts if p)


def _raw_chat(conv: dict) -> RawChat:
    msgs = [m for m in (conv.get("chat_messages") or [])
            if _ROLE.get(m.get("sender")) and _text(m).strip()]
    tree: dict[str, RawMessage] = {}
    for i, m in enumerate(msgs):
        mid = m.get("uuid") or f"m{i}"
        tree[mid] = RawMessage(
            id=mid, parent_id=(msgs[i - 1].get("uuid") if i > 0 else None),
            children_ids=([msgs[i + 1].get("uuid")] if i + 1 < len(msgs) else []),
            role=_ROLE[m["sender"]], content=_text(m), timestamp=_ts(m.get("created_at")),
            model_name="claude")
    return RawChat(
        id=conv.get("uuid") or "claude",
        title=conv.get("name") or "",
        source="claude:export",
        models=["claude"] if msgs else [],
        created_at=_ts(conv.get("created_at")),
        tree=tree,
        current_id=(msgs[-1].get("uuid") if msgs else None))


def load_export(path: str | Path, chat_id: Optional[str] = None) -> RawChat:
    convs = _load(path)
    if chat_id:
        exact = [c for c in convs if c.get("uuid") == chat_id]
        if exact:
            return _raw_chat(exact[0])
        pref = [c for c in convs if str(c.get("uuid", "")).startswith(chat_id)]
        if len(pref) == 1:
            return _raw_chat(pref[0])
        if len(pref) > 1:
            raise ValueError(f"uuid prefix {chat_id!r} matches {len(pref)} conversations")
        raise KeyError(f"no Claude conversation with uuid (or prefix) {chat_id!r}")
    if len(convs) == 1:
        return _raw_chat(convs[0])
    raise ValueError(f"{path} holds {len(convs)} conversations — pass --id <uuid|prefix>")


def iter_export(path: str | Path) -> Iterator[RawChat]:
    for conv in _load(path):
        if isinstance(conv, dict) and conv.get("chat_messages"):
            yield _raw_chat(conv)
