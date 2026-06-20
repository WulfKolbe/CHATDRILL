"""projC — project a ChatModel into TiddlyWiki tiddlers.

Emits, per chat:
  - one **Chat** tiddler (overview: metadata, exchange list, code list, links)
  - one **Exchange** tiddler per Q&A pair (question + answer, code re-fenced)
  - one **Code** tiddler per unique code artifact (deduped by sha1), as a
    fenced block so TiddlyWiki's highlighter renders it

Naming mirrors PDFDRILL's ``KEY_<type>_<id>``: a per-chat ``key`` (slug of the
title + short id) namespaces every tiddler, so a chat's tiddlers group under
``[tag[<key>]]`` and never collide across chats.

Because pass03 segmented the (often stripped-fence) code, we can wrap code
segments back in ```fences``` here — so code that arrived bare renders correctly.
"""
from __future__ import annotations

import re

from ..models import ChatModel
from .segment import render_turn as _render_turn


def slugify(s: str, n: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", s or "").strip("-")
    return (s[:n].strip("-") or "chat")


def chat_key(model: ChatModel) -> str:
    return f"{slugify(model.title)}_{model.id[:8]}"


def _tid(title: str, tags: str, text: str, **fields) -> dict:
    t = {"title": title, "tags": tags, "type": "text/vnd.tiddlywiki", "text": text}
    t.update({k: str(v) for k, v in fields.items()})
    return t


def build_tiddlers(model: ChatModel) -> list[dict]:
    key = chat_key(model)
    tiddlers: list[dict] = []

    # ---- Exchange tiddlers + collect previews -------------------------------
    ex_links: list[str] = []
    for ex in model.exchanges:
        qprev = " ".join(ex.query.content.split())[:80]
        ex_links.append(f"* [[{key}_Q{ex.index}]] — {qprev}")
        lat = f" · {ex.latency_ms // 1000}s" if ex.latency_ms is not None else ""
        body = (f"!! Question\n\n{_render_turn(ex.query)}\n\n"
                f"!! Answer ⟨{ex.model or '?'}{lat}⟩\n\n"
                + (_render_turn(ex.answer) if ex.answer else "//(no answer)//"))
        tiddlers.append(_tid(
            f"{key}_Q{ex.index}", f"chatdrill exchange [[{key}]]", body,
            index=ex.index, model=ex.model or "", answered=str(ex.answered).lower(),
            **({"latency_s": ex.latency_ms // 1000} if ex.latency_ms is not None else {})))

    # ---- Code tiddlers (dedup by sha1) --------------------------------------
    code_links: list[str] = []
    seen: set[str] = set()
    for a in (a for a in model.artifacts if a.kind == "code"):
        if a.sha1 in seen:
            continue
        seen.add(a.sha1)
        n = len(code_links)
        title = f"{key}_Code_{n}"
        code_links.append(f"* [[{title}]] — `{a.lang or '?'}`, {a.line_count} lines "
                          f"(exchange {a.exchange_index})")
        tiddlers.append(_tid(
            title, f"chatdrill code {a.lang or 'text'} [[{key}]]",
            f"```{a.lang or ''}\n{a.content}\n```",
            lang=a.lang or "", lines=a.line_count, sha1=a.sha1,
            exchange=a.exchange_index, fenced=str(a.fenced).lower()))

    # ---- Links (urls) -------------------------------------------------------
    urls = sorted({a.content for a in model.artifacts if a.kind == "url"})

    # ---- Chat overview tiddler ----------------------------------------------
    answered = sum(1 for e in model.exchanges if e.answered)
    overview = [
        f"!! {model.title or key}",
        "",
        f"Source: `{model.source}` · Models: {', '.join(model.models) or '—'} · "
        f"{len(model.exchanges)} exchanges ({answered} answered)",
        "",
        "!! Exchanges", *ex_links,
    ]
    if code_links:
        overview += ["", "!! Code artifacts", *code_links]
    if urls:
        overview += ["", "!! Links", *[f"* {u}" for u in urls]]
    tiddlers.insert(0, _tid(
        key, "chatdrill chat", "\n".join(overview),
        source=model.source, chat_id=model.id,
        models=", ".join(model.models), exchanges=len(model.exchanges),
        code_artifacts=len(code_links)))

    return tiddlers


# -- serialization -----------------------------------------------------------

def _safe_filename(title: str) -> str:
    return re.sub(r"[^\w.-]+", "_", title) + ".tid"


def to_tid_text(t: dict) -> str:
    """A single .tid file: 'field: value' header, blank line, then text."""
    header = "\n".join(f"{k}: {v}" for k, v in t.items() if k != "text")
    return f"{header}\n\n{t.get('text', '')}\n"
