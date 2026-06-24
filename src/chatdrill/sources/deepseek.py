"""DeepSeek export encoder — handles both DeepSeek shapes.

1. **Bulk export** (`deepseek_conversations.json`, or the `conversations.json`
   inside a `deepseek_data-*.zip`): a list of conversations, each with a
   `mapping` tree (`{id, parent, children, message}`) — like ChatGPT, but the
   message has no `author.role`; role is inferred from its `fragments` types.
2. **Share API** (`api/v0/share/content?share_id=…`, captured from a public
   share link): `{data: {biz_data: {title, messages: [...]}}}` where each message
   has an explicit `role` (USER/ASSISTANT), `parent_id`, and `fragments`.

Both store text in `fragments` with `type` ∈ REQUEST (user) / THINK (reasoning) /
RESPONSE (answer). We keep REQUEST for users and RESPONSE for assistants (THINK,
the chain-of-thought, is dropped by default).
"""
from __future__ import annotations

import datetime
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterator, Optional

from ..models import RawChat, RawMessage

_ROLE = {"USER": "user", "ASSISTANT": "assistant"}


def _ts(v) -> Optional[int]:
    """DeepSeek uses unix floats (share) AND ISO strings (bulk export)."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    try:
        return int(float(v))
    except (TypeError, ValueError):
        pass
    try:
        return int(datetime.datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


def _load(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _is_share(d) -> bool:
    return (isinstance(d, dict) and isinstance(d.get("data"), dict)
            and isinstance(d["data"].get("biz_data"), dict)
            and "messages" in d["data"]["biz_data"])


def _is_bulk(d) -> bool:
    # a list of convs, OR a single conv dict (split writes per-chat dicts)
    if isinstance(d, list):
        convs = d
    elif isinstance(d, dict) and "mapping" in d:
        convs = [d]
    else:
        return False
    if not (convs and isinstance(convs[0], dict) and "mapping" in convs[0]):
        return False
    for n in convs[0]["mapping"].values():
        m = n.get("message")
        if m and "fragments" in m:               # DeepSeek msg (no author.role)
            return True
    return False


def is_deepseek_export(path: str | Path) -> bool:
    try:
        return _is_share(_load(path)) or _is_bulk(_load(path))
    except (json.JSONDecodeError, OSError):
        return False


def _role_of(message: dict) -> Optional[str]:
    if message.get("role"):
        return _ROLE.get(message["role"])
    types = {f.get("type") for f in (message.get("fragments") or [])}
    if "REQUEST" in types:
        return "user"
    if types & {"RESPONSE", "THINK"}:
        return "assistant"
    return None


def _text_of(message: dict, role: str) -> str:
    want = {"user": {"REQUEST"}, "assistant": {"RESPONSE"}}.get(role, set())
    fr = message.get("fragments") or []
    texts = [f.get("content", "") for f in fr if f.get("type") in want and f.get("content")]
    if not texts:                                # fallback: any non-THINK content
        texts = [f.get("content", "") for f in fr
                 if f.get("type") != "THINK" and f.get("content")]
    return "\n".join(t for t in texts if t)


# ---- share-API shape -------------------------------------------------------
def _raw_chat_share(biz: dict, cid: str) -> RawChat:
    msgs = biz.get("messages") or []
    tree: dict[str, RawMessage] = {}
    for m in msgs:
        role = _role_of(m)
        if not role:
            continue
        mid = str(m["message_id"])
        kids = [str(x["message_id"]) for x in msgs if str(x.get("parent_id")) == mid]
        tree[mid] = RawMessage(
            id=mid, parent_id=str(m["parent_id"]) if m.get("parent_id") is not None else None,
            children_ids=kids, role=role, content=_text_of(m, role),
            timestamp=_ts(m.get("inserted_at")),
            model_name=(m.get("model") or biz.get("model_type") or "deepseek"))
    leaf = max(tree, key=lambda k: int(k)) if tree else None
    return RawChat(id=cid, title=biz.get("title") or "", source="deepseek:export",
                   models=sorted({t.model_name for t in tree.values() if t.model_name}),
                   tree=tree, current_id=leaf)


# ---- bulk mapping shape ----------------------------------------------------
def _raw_chat_mapping(conv: dict) -> RawChat:
    mapping = conv.get("mapping", {}) or {}
    included = {nid for nid, n in mapping.items()
                if n.get("message") and _role_of(n["message"]) and
                _text_of(n["message"], _role_of(n["message"])).strip()}

    def nearest(nid):
        p = mapping[nid].get("parent")
        while p is not None and p not in included:
            p = (mapping.get(p) or {}).get("parent")
        return p

    children: dict[str, list[str]] = defaultdict(list)
    parent_of: dict[str, Optional[str]] = {}
    for nid in included:
        par = nearest(nid)
        parent_of[nid] = par
        if par is not None:
            children[par].append(nid)

    tree: dict[str, RawMessage] = {}
    for nid in included:
        m = mapping[nid]["message"]
        role = _role_of(m)
        tree[nid] = RawMessage(
            id=nid, parent_id=parent_of[nid], children_ids=children.get(nid, []),
            role=role, content=_text_of(m, role),
            timestamp=_ts(m.get("inserted_at")),
            model_name=m.get("model") or "deepseek")
    # leaf = deepest node
    leaf = None
    if tree:
        depth = {}
        for nid in tree:
            d, p = 0, parent_of.get(nid)
            while p is not None:
                d += 1; p = parent_of.get(p)
            depth[nid] = d
        leaf = max(depth, key=depth.get)
    return RawChat(id=conv.get("id") or "deepseek", title=conv.get("title") or "",
                   source="deepseek:export",
                   models=sorted({t.model_name for t in tree.values() if t.model_name}),
                   created_at=_ts(conv.get("inserted_at")),
                   tree=tree, current_id=leaf)


def _share_id(biz: dict) -> str:
    seed = (biz.get("title") or "") + str((biz.get("messages") or [{}])[0].get("message_id", ""))
    return "dsk_" + hashlib.sha1(seed.encode()).hexdigest()[:10]


def load_export(path: str | Path, chat_id: Optional[str] = None) -> RawChat:
    d = _load(path)
    if _is_share(d):
        biz = d["data"]["biz_data"]
        return _raw_chat_share(biz, chat_id or _share_id(biz))
    convs = d if isinstance(d, list) else [d]
    if chat_id:
        for c in convs:
            if str(c.get("id", "")).startswith(chat_id):
                return _raw_chat_mapping(c)
        raise KeyError(f"no DeepSeek conversation with id (or prefix) {chat_id!r}")
    if len(convs) == 1:
        return _raw_chat_mapping(convs[0])
    raise ValueError(f"{path} holds {len(convs)} conversations — pass --id <id|prefix>")


def iter_export(path: str | Path) -> Iterator[RawChat]:
    d = _load(path)
    if _is_share(d):
        biz = d["data"]["biz_data"]
        yield _raw_chat_share(biz, _share_id(biz))
        return
    for conv in (d if isinstance(d, list) else [d]):
        if isinstance(conv, dict) and conv.get("mapping"):
            yield _raw_chat_mapping(conv)
