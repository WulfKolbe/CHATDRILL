"""Perplexity export encoder — normalize a bodies dump to RawChat.

A Perplexity bodies dump is ``{ "<slug>": <thread-body>, ... }`` (the shape the
user's pplx fetcher / pplx2tw.py produce). Each thread-body has
``thread_metadata`` (title, created_at) and ``entries[]``; each entry's ``text``
is a JSON-encoded ``steps[]`` with an INITIAL_QUERY step (the question) and a
FINAL step (the answer, itself JSON with ``structured_answer`` markdown blocks +
``web_results`` sources). One entry = one Q&A pair = one Exchange.

A Perplexity thread is a FLAT Q&A list, so we synthesize a linear chat tree
(q0→a0→q1→a1…) — the same RawChat the rest of the pipeline consumes.

Parse logic mirrors the user's pplx2tw.py so tiddler output stays consistent.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Iterator, Optional

from ..models import RawChat, RawMessage


def _aslist(x):
    return x if isinstance(x, list) else []


def _ts(created: str) -> Optional[int]:
    try:
        dt = datetime.datetime.fromisoformat((created or "").replace("Z", ""))
        return int(dt.timestamp())
    except Exception:
        return None


def parse_thread_body(body: dict) -> dict:
    """{id, title, created, queries:[{query, answer_md, sources, model}]}."""
    md_meta = body.get("thread_metadata") or {}
    out = {"id": body.get("id"), "title": md_meta.get("title", "") or "",
           "created": md_meta.get("created_at", "") or "", "queries": []}
    for entry in _aslist(body.get("entries")):
        raw = entry.get("text")
        if not raw:
            continue
        try:
            steps = json.loads(raw)
        except Exception:
            continue
        q = {"query": "", "answer_md": "", "sources": [],
             "model": entry.get("display_model", "") or ""}
        for st in _aslist(steps):
            content = st.get("content") or {}
            if st.get("step_type") == "INITIAL_QUERY":
                q["query"] = content.get("query", "") or ""
            elif st.get("step_type") == "FINAL":
                ans_raw = content.get("answer")
                if not ans_raw:
                    continue
                try:
                    ans = json.loads(ans_raw)
                except Exception:
                    ans = {}
                if not isinstance(ans, dict):
                    ans = {}
                md = ""
                for b in _aslist(ans.get("structured_answer")):
                    if isinstance(b, dict) and b.get("type") == "markdown" and b.get("text"):
                        md = b["text"]
                        break
                q["answer_md"] = md or ans.get("answer", "") or ""
                seen = set()
                for r in _aslist(ans.get("web_results")):
                    if isinstance(r, dict) and r.get("url") and r["url"] not in seen:
                        seen.add(r["url"])
                        q["sources"].append(r["url"])
        if q["query"] or q["answer_md"]:
            out["queries"].append(q)
    return out


def _raw_chat(slug: str, body: dict) -> RawChat:
    p = parse_thread_body(body)
    tid = p["id"] or slug
    created = _ts(p["created"])
    seq: list[tuple[str, str, str, Optional[str]]] = []
    for qi, q in enumerate(p["queries"]):
        ans = q["answer_md"]
        if q["sources"]:                              # keep source urls as artifacts
            ans += "\n\nSources:\n" + "\n".join(f"- {u}" for u in q["sources"])
        seq.append((f"{tid}_q{qi}", "user", q["query"], None))
        seq.append((f"{tid}_a{qi}", "assistant", ans, q["model"] or "perplexity"))

    tree: dict[str, RawMessage] = {}
    for i, (mid, role, content, model) in enumerate(seq):
        tree[mid] = RawMessage(
            id=mid, parent_id=seq[i - 1][0] if i > 0 else None,
            children_ids=[seq[i + 1][0]] if i + 1 < len(seq) else [],
            role=role, content=content, timestamp=created, model_name=model)

    return RawChat(
        id=tid, title=p["title"], source="perplexity:export",
        models=sorted({m for *_, m in seq if m}),
        created_at=created, tree=tree,
        current_id=seq[-1][0] if seq else None)


def is_perplexity_export(path: str | Path) -> bool:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    vals = list(data.values()) if isinstance(data, dict) else data
    return bool(vals) and isinstance(vals[0], dict) and "entries" in vals[0]


def _items(path: str | Path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return list(data.items())
    return [(str(b.get("id", i)), b) for i, b in enumerate(data)]


def load_export(path: str | Path, chat_id: Optional[str] = None) -> RawChat:
    items = _items(path)
    if chat_id:
        for slug, body in items:
            if slug == chat_id or body.get("id") == chat_id:
                return _raw_chat(slug, body)
        pref = [(s, b) for s, b in items
                if s.startswith(chat_id) or str(b.get("id", "")).startswith(chat_id)]
        if len(pref) == 1:
            return _raw_chat(*pref[0])
        if len(pref) > 1:
            raise ValueError(f"id prefix {chat_id!r} matches {len(pref)} threads")
        raise KeyError(f"no perplexity thread with id/slug (or prefix) {chat_id!r}")
    if len(items) == 1:
        return _raw_chat(*items[0])
    raise ValueError(f"{path} holds {len(items)} threads — pass --id <slug|prefix>")


def iter_export(path: str | Path) -> Iterator[RawChat]:
    for slug, body in _items(path):
        yield _raw_chat(slug, body)
