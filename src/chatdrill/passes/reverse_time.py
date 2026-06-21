"""pass14 — reverse-time fold → ResultsView (the reuse surface).

A chat's value sits at the END (the working code, the answer that stuck), so we
read it newest→oldest. Per artifact *identity* the first occurrence seen (= the
latest in time) is canonical; earlier ones collapse into a `superseded` lineage.
Five drafts of the same code become one canonical block + a 4-deep history.

Identity, most-specific first:
  1. file:<name>   — a filename in a leading comment (e.g. `# parser.py`, `// a.ts`)
  2. sig:<lang>:<symbols> — the top-level definitions the code declares
     (def/class/interface/type/function/const/…); same primary symbol ⇒ same artifact
  3. sha1:<hash>   — fallback: exact-content identity (unique one-offs)

Time order uses exchange_index (later index = later turn), robust even when
timestamps are missing.
"""
from __future__ import annotations

import re

from ..models import (Artifact, CanonicalArtifact, ChatModel, ResultsView,
                      UnresolvedQuestion)

_FILENAME = re.compile(
    r"(?:#|//|/\*|\*|<!--|--|;)\s*([A-Za-z0-9_.\-/]+\.[A-Za-z]{1,5})\b")
_DEF = re.compile(
    r"\b(?:def|class|interface|type|function|func|fn|enum|struct|const|let|var)\s+"
    r"([A-Za-z_]\w*)")


def _filename(content: str) -> str | None:
    for line in content.splitlines()[:4]:
        m = _FILENAME.search(line)
        if m:
            return m.group(1).rsplit("/", 1)[-1]      # basename
    return None


def _signature(content: str, lang: str | None) -> str | None:
    names = sorted(set(_DEF.findall(content)))
    if names:
        return f"{lang or '?'}:{'|'.join(names[:5])}"
    return None


def _identity(a: Artifact) -> str:
    fn = _filename(a.content)
    if fn:
        return f"file:{fn}"
    sig = _signature(a.content, a.lang)
    if sig:
        return f"sig:{sig}"
    return f"sha1:{a.sha1}"


def fold(model: ChatModel) -> ChatModel:
    code = [a for a in model.artifacts if a.kind == "code"]
    # newest first; within an exchange preserve encounter order (stable sort)
    code.sort(key=lambda a: a.exchange_index, reverse=True)

    canon: dict[str, CanonicalArtifact] = {}
    order: list[str] = []
    for a in code:
        ident = _identity(a)
        if ident not in canon:
            canon[ident] = CanonicalArtifact(
                id=f"res_{len(order):04d}", identity=ident, lang=a.lang,
                latest_turn_id=a.turn_id, exchange_index=a.exchange_index,
                content=a.content, line_count=a.line_count, sha1=a.sha1)
            order.append(ident)
        else:                                          # an OLDER draft
            ca = canon[ident]
            ca.superseded.append(a.turn_id)
            ca.revisions += 1

    artifacts = [canon[i] for i in order]
    unresolved = [
        UnresolvedQuestion(turn_id=ex.query.id, exchange_index=ex.index,
                           text=" ".join(ex.query.content.split())[:120])
        for ex in model.exchanges if not ex.answered]

    model.results = ResultsView(artifacts=artifacts, unresolved=unresolved)
    return model
