"""ChatGPT export encoder — normalize a `conversations.json` export to RawChat.

ChatGPT's export is a JSON array of conversations, each with a `mapping`
(node_id → {id, message, parent, children}) and a `current_node` leaf. We lift
the message-bearing nodes into a clean RawChat tree, re-parenting each to its
nearest message-bearing ancestor (so null tool/system nodes don't break the
parent chain). Matches the same RawChat the rest of the pipeline consumes.

The auth-gated chat URL can't be fetched server-side; this reads the JSON the
user exports (Settings → Data Controls → Export) — possibly the bulk file with
all chats, from which we pick one by id/prefix.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Iterator, Optional

from ..models import RawChat, RawMessage

_ROLES = {"user", "assistant", "system", "tool"}


def _load(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, list) else [data]


def is_chatgpt_export(path: str | Path) -> bool:
    try:
        data = _load(path)
    except (json.JSONDecodeError, OSError):
        return False
    return bool(data) and isinstance(data[0], dict) and "mapping" in data[0]


def _text(message: dict) -> str:
    parts = (message.get("content") or {}).get("parts") or []
    return "\n".join(p for p in parts if isinstance(p, str))


def _node_ok(node: dict) -> bool:
    m = node.get("message")
    if not m or m.get("author", {}).get("role") not in _ROLES:
        return False
    return bool(_text(m).strip())


def _raw_chat(conv: dict) -> RawChat:
    mapping = conv.get("mapping", {}) or {}
    included = {nid for nid, node in mapping.items() if _node_ok(node)}

    def nearest_parent(nid: str) -> Optional[str]:
        p = mapping[nid].get("parent")
        while p is not None and p not in included:
            p = (mapping.get(p) or {}).get("parent")
        return p

    children: dict[str, list[str]] = defaultdict(list)
    parent_of: dict[str, Optional[str]] = {}
    for nid in included:
        par = nearest_parent(nid)
        parent_of[nid] = par
        if par is not None:
            children[par].append(nid)

    tree: dict[str, RawMessage] = {}
    for nid in included:
        m = mapping[nid]["message"]
        ts = m.get("create_time")
        tree[nid] = RawMessage(
            id=nid, parent_id=parent_of[nid], children_ids=children.get(nid, []),
            role=m["author"]["role"], content=_text(m),
            timestamp=int(ts) if ts else None,
            model_name=(m.get("metadata") or {}).get("model_slug"))

    current = conv.get("current_node")
    if current not in included:
        current = None                       # linearize falls back to deepest leaf
    created = conv.get("create_time")
    return RawChat(
        id=conv.get("id") or conv.get("conversation_id") or "chatgpt",
        title=conv.get("title") or "",
        source="chatgpt:export",
        models=sorted({t.model_name for t in tree.values() if t.model_name}),
        created_at=int(created) if created else None,
        tree=tree, current_id=current)


def load_export(path: str | Path, chat_id: Optional[str] = None) -> RawChat:
    """One conversation from an export: by exact id, unique id-prefix, or (if the
    file holds exactly one) that one."""
    convs = _load(path)
    if chat_id:
        exact = [c for c in convs if c.get("id") == chat_id]
        if exact:
            return _raw_chat(exact[0])
        pref = [c for c in convs if str(c.get("id", "")).startswith(chat_id)]
        if len(pref) == 1:
            return _raw_chat(pref[0])
        if len(pref) > 1:
            raise ValueError(f"id prefix {chat_id!r} matches {len(pref)} conversations")
        raise KeyError(f"no conversation with id (or prefix) {chat_id!r} in {path}")
    if len(convs) == 1:
        return _raw_chat(convs[0])
    raise ValueError(f"{path} holds {len(convs)} conversations — pass --id <id|prefix>")


def iter_export(path: str | Path) -> Iterator[RawChat]:
    for conv in _load(path):
        if isinstance(conv, dict) and conv.get("mapping"):
            yield _raw_chat(conv)
