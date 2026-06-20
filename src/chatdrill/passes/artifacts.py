"""pass04 — lift first-class Artifacts (code / url / error) from the model.

Reads the segments pass03 produced (for code) plus regex over raw content (for
urls and error tracebacks). Each artifact records where it came from
(exchange_index, turn_id, role) so the reverse-time fold and tiddler export can
reference it. Code carries a sha1 for later dedup / lineage.
"""
from __future__ import annotations

import hashlib
import re

from ..models import Artifact, ChatModel, Turn

_URL = re.compile(r"https?://[^\s)>\]\"'`]+")
_URL_TRAILING = ".,;:!?)]}​"             # strip trailing punctuation/zero-width

# error / traceback cues
_TRACEBACK = re.compile(r"Traceback \(most recent call last\):")
_ERRLINE = re.compile(r"^\s*[\w.]*(Error|Exception)\b.*", re.MULTILINE)


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def _urls(text: str) -> list[str]:
    out, seen = [], set()
    for m in _URL.finditer(text):
        u = m.group(0).rstrip(_URL_TRAILING)
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _errors(text: str) -> list[str]:
    out: list[str] = []
    if _TRACEBACK.search(text):
        # grab from the Traceback line to the first blank line
        idx = text.index("Traceback (most recent call last):")
        block = text[idx:].split("\n\n", 1)[0]
        out.append(block.strip())
    for m in _ERRLINE.finditer(text):
        line = m.group(0).strip()
        if line and line not in out:
            out.append(line)
    return out


def extract_artifacts(model: ChatModel) -> ChatModel:
    """Populate ``model.artifacts`` from segments + regex (replaces any prior)."""
    arts: list[Artifact] = []
    counters = {"code": 0, "url": 0, "error": 0}

    def add(kind: str, **kw) -> None:
        arts.append(Artifact(id=f"{kind}_{counters[kind]:04d}", kind=kind, **kw))
        counters[kind] += 1

    for ex in model.exchanges:
        for turn in (ex.query, ex.answer):
            if turn is None:
                continue
            where = dict(exchange_index=ex.index, turn_id=turn.id, role=turn.role)
            for seg in turn.segments:
                if seg.kind == "code" and seg.text.strip():
                    body = seg.text
                    add("code", content=body, lang=seg.lang, fenced=seg.fenced,
                        line_count=len(body.splitlines()), sha1=_sha1(body),
                        **where)
            for u in _urls(turn.content):
                add("url", content=u, **where)
            for e in _errors(turn.content):
                add("error", content=e, **where)

    model.artifacts = arts
    return model
