"""Command handlers — return prose strings (PDFDRILL convention).

A small ``Ctx`` carries the resolved args; each handler takes it, does its work,
and returns text. ``cmd_model`` is the persisting, idempotent build: it writes
chatmodel.json + records the MODEL_BUILT fact, and on re-run detects the fact and
skips unless ``--force``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import json
import os
from pathlib import Path

from .models import ChatModel
from .passes.artifacts import extract_artifacts
from .passes.linearize import linearize
from .passes.segment import segment_model
from .passes.tiddlers import build_tiddlers, to_tid_text, _safe_filename
from .sidecar import Sidecar, resolve_local_id
from .sources import openwebui


@dataclass
class Ctx:
    chat_id: Optional[str] = None
    db: Optional[str] = None
    work: Optional[str] = None
    force: bool = False
    as_json: bool = False
    limit: int = 50
    target: Optional[str] = None      # for `steps`
    out: Optional[str] = None         # tiddlers output dir


# -- views -------------------------------------------------------------------

def _summary(model: ChatModel) -> str:
    exs = model.exchanges
    answered = sum(1 for e in exs if e.answered)
    models = sorted({e.model for e in exs if e.model})
    lines = [
        f"chat {model.id}",
        f"  title:      {model.title!r}",
        f"  source:     {model.source}",
        f"  exchanges:  {len(exs)} ({answered} answered, "
        f"{len(exs) - answered} unanswered)",
        f"  branches:   {len(model.forgotten_branches)} forgotten",
        f"  models:     {', '.join(models) or '(none recorded)'}",
        "",
        "  Q&A pairs:",
    ]
    for e in exs:
        q = " ".join(e.query.content.split())[:72]
        a = " ".join(e.answer.content.split())[:72] if e.answer else "(no answer)"
        lat = f" {e.latency_ms // 1000}s" if e.latency_ms is not None else ""
        regen = f" x{e.regen_count}" if e.regen_count > 1 else ""
        lines.append(f"  [{e.index:>2}] Q: {q}")
        lines.append(f"       A: {a}  ⟨{e.model or '?'}{lat}{regen}⟩")
    return "\n".join(lines)


# -- handlers ----------------------------------------------------------------

def cmd_list(ctx: Ctx) -> str:
    chats = openwebui.list_chats(db=ctx.db, limit=ctx.limit)
    if not chats:
        return "no chats found in webui.db."
    # Print the FULL id (copy-pasteable). Any unique prefix also works, e.g. the
    # first 8 chars: `chatdrill model <prefix>`.
    lines = [f"{len(chats)} chat(s) (most recent first) — id is copy-pasteable; "
             f"a unique prefix also works:"]
    for c in chats:
        lines.append(f"  {c['id']}  msgs={c['messages']:>3}  {c['title']!r}")
    return "\n".join(lines)


def cmd_load(ctx: Ctx) -> str:
    """Ephemeral: pass01+pass02 in memory, no persistence."""
    raw = openwebui.load_chat(ctx.chat_id, db=ctx.db)
    model = linearize(raw)
    return model.model_dump_json(indent=2) if ctx.as_json else _summary(model)


def cmd_model(ctx: Ctx) -> str:
    """Build + persist the ChatModel. Idempotent: skip if MODEL_BUILT + artifact
    present, unless --force."""
    # resolve the prefix to the canonical id FIRST, so the sidecar is keyed
    # consistently (otherwise a prefix would create a second, empty sidecar).
    full_id = openwebui.resolve_id(ctx.chat_id, db=ctx.db)
    sc = Sidecar(full_id, work=ctx.work)
    if sc.has("MODEL_BUILT") and sc.has_blob("chatmodel.json") and not ctx.force:
        n = sc.get_evidence("exchange_count", "?")
        return (f"model already built for {sc.chat_id[:12]}… "
                f"({n} exchanges) — skipped. Use --force to rebuild.")

    t0 = time.perf_counter()
    raw = openwebui.load_chat(full_id, db=ctx.db)
    model = linearize(raw)
    sc.write_blob("chatmodel.json", model.model_dump_json(indent=2))
    cost_ms = (time.perf_counter() - t0) * 1000

    answered = sum(1 for e in model.exchanges if e.answered)
    sc.set_layer("chatmodel", {"path": "chatmodel.json", "format": "ChatModel/json"})
    sc.set_evidence("exchange_count", len(model.exchanges))
    sc.set_evidence("answered_count", answered)
    sc.set_evidence("branch_count", len(model.forgotten_branches))
    sc.set_evidence("models", sorted({e.model for e in model.exchanges if e.model}))
    was = "INIT" if not sc.facts else ",".join(sorted(sc.facts))
    sc.add_fact("MODEL_BUILT")
    sc.log_transition("model", was, "MODEL_BUILT", cost_ms,
                      f"{len(model.exchanges)} exchanges")
    sc.save()
    return (f"built model for {sc.chat_id[:12]}…: {len(model.exchanges)} exchanges "
            f"({answered} answered, {len(model.forgotten_branches)} branches) "
            f"in {cost_ms:.0f} ms → {sc.blob_path('chatmodel.json')}")


def _load_persisted(sc: Sidecar) -> ChatModel:
    blob = sc.read_blob("chatmodel.json")
    if blob is None:
        raise FileNotFoundError(
            f"no persisted model for {sc.chat_id[:12]}… — run "
            f"`chatdrill model {sc.chat_id[:12]}` first, or pass --ensure.")
    return ChatModel.model_validate_json(blob)


def _persist(sc: Sidecar, model: ChatModel) -> None:
    sc.write_blob("chatmodel.json", model.model_dump_json(indent=2))


def _sidecar_for_persisted(ctx: Ctx) -> Sidecar:
    """Sidecar for a chat that should already be built — DB-free prefix resolve."""
    return Sidecar(resolve_local_id(ctx.chat_id, ctx.work), work=ctx.work)


def cmd_segment(ctx: Ctx) -> str:
    """pass03 — segment turns into prose/code; rewrite the model (requires: model)."""
    sc = _sidecar_for_persisted(ctx)
    if sc.has("SEGMENTED") and not ctx.force:
        seg = sc.get_evidence("segment_code_blocks", "?")
        return f"already segmented ({seg} code blocks) — skipped. --force to redo."
    t0 = time.perf_counter()
    model = segment_model(_load_persisted(sc))
    _persist(sc, model)
    cost_ms = (time.perf_counter() - t0) * 1000
    code = sum(1 for ex in model.exchanges for t in (ex.query, ex.answer)
               if t for s in t.segments if s.kind == "code")
    fenced = sum(1 for ex in model.exchanges for t in (ex.query, ex.answer)
                 if t for s in t.segments if s.kind == "code" and s.fenced)
    sc.set_evidence("segment_code_blocks", code)
    sc.add_fact("SEGMENTED")
    sc.log_transition("segment", "MODEL_BUILT", "SEGMENTED", cost_ms,
                      f"{code} code blocks ({fenced} fenced, {code - fenced} recovered)")
    sc.save()
    return (f"segmented {sc.chat_id[:12]}…: {code} code blocks "
            f"({fenced} fenced, {code - fenced} recovered from stripped fences) "
            f"in {cost_ms:.0f} ms")


def cmd_artifacts(ctx: Ctx) -> str:
    """pass04 — lift code/url/error artifacts (requires: segment)."""
    sc = _sidecar_for_persisted(ctx)
    if sc.has("ARTIFACTS") and not ctx.force:
        return _artifacts_report(_load_persisted(sc), prefix="already extracted")
    t0 = time.perf_counter()
    model = extract_artifacts(_load_persisted(sc))
    _persist(sc, model)
    cost_ms = (time.perf_counter() - t0) * 1000
    by = _counts(model)
    sc.set_evidence("artifact_counts", by)
    sc.add_fact("ARTIFACTS")
    sc.log_transition("artifacts", "SEGMENTED", "ARTIFACTS", cost_ms,
                      f"{sum(by.values())} artifacts {by}")
    sc.save()
    return _artifacts_report(model, prefix=f"extracted in {cost_ms:.0f} ms")


def _tiddlers_dir(ctx: Ctx) -> Path:
    return Path(ctx.out or os.environ.get("CHATDRILL_TIDDLERS") or "tiddlers")


def cmd_tiddlers(ctx: Ctx) -> str:
    """projC — write chat/exchange/code tiddlers (requires: artifacts)."""
    sc = _sidecar_for_persisted(ctx)
    out_dir = _tiddlers_dir(ctx)
    if sc.has("TIDDLERS_BUILT") and not ctx.force:
        n = sc.get_evidence("tiddler_count", "?")
        return (f"already exported ({n} tiddlers) — skipped. --force to redo. "
                f"(tiddlers/ dir: {out_dir})")
    t0 = time.perf_counter()
    model = _load_persisted(sc)
    tids = build_tiddlers(model)

    # 1) canonical import blob in the drill dir
    sc.write_blob("tiddlers.json", json.dumps(tids, indent=2, ensure_ascii=False))
    # 2) individual .tid files into the live wiki folder
    out_dir.mkdir(parents=True, exist_ok=True)
    for t in tids:
        (out_dir / _safe_filename(t["title"])).write_text(
            to_tid_text(t), encoding="utf-8")
    cost_ms = (time.perf_counter() - t0) * 1000

    kinds = {"chat": 0, "exchange": 0, "code": 0}
    for t in tids:
        for k in kinds:
            if t["tags"].startswith(f"chatdrill {k}"):
                kinds[k] += 1
    sc.set_evidence("tiddler_count", len(tids))
    sc.set_layer("tiddlers", {"path": "tiddlers.json", "format": "tiddlywiki/json"})
    sc.add_fact("TIDDLERS_BUILT")
    sc.log_transition("tiddlers", "ARTIFACTS", "TIDDLERS_BUILT", cost_ms,
                      f"{len(tids)} tiddlers {kinds}")
    sc.save()
    return (f"exported {len(tids)} tiddlers for {model.id[:12]}… "
            f"({kinds['chat']} chat, {kinds['exchange']} exchange, "
            f"{kinds['code']} code) in {cost_ms:.0f} ms\n"
            f"  → .tid files in {out_dir}/  (live in the TiddlyWiki server)\n"
            f"  → import blob: {sc.blob_path('tiddlers.json')}")


def _counts(model: ChatModel) -> dict:
    by = {"code": 0, "url": 0, "error": 0}
    for a in model.artifacts:
        by[a.kind] += 1
    return by


def _artifacts_report(model: ChatModel, prefix: str) -> str:
    by = _counts(model)
    lines = [f"{prefix}: {by['code']} code, {by['url']} url, {by['error']} error "
             f"for {model.id[:12]}…"]
    code = [a for a in model.artifacts if a.kind == "code"]
    if code:
        lines.append("  code blocks:")
        for a in code[:8]:
            first = next((ln for ln in a.content.splitlines() if ln.strip()), "")
            tag = "fence" if a.fenced else "recov"
            lines.append(f"    [{a.exchange_index}] {a.lang or '?':<10} "
                         f"{a.line_count:>3} lines  {tag}  {first.strip()[:48]!r}")
    urls = [a for a in model.artifacts if a.kind == "url"]
    if urls:
        uniq = sorted({a.content for a in urls})
        lines.append(f"  urls ({len(uniq)} unique):")
        for u in uniq[:8]:
            lines.append(f"    {u[:78]}")
    return "\n".join(lines)


def cmd_summary(ctx: Ctx) -> str:
    """Print the Q&A summary from the PERSISTED ChatModel (requires: model)."""
    sc = _sidecar_for_persisted(ctx)
    model = _load_persisted(sc)
    return model.model_dump_json(indent=2) if ctx.as_json else _summary(model)


def cmd_status(ctx: Ctx) -> str:
    from .sidecar import resolve_local_id
    sc = Sidecar(resolve_local_id(ctx.chat_id, ctx.work), work=ctx.work)
    if not sc.json_path.exists():
        return (f"no sidecar for {ctx.chat_id[:12]}… yet — nothing built. "
                f"Run `chatdrill model {ctx.chat_id[:12]}`.")
    facts = ", ".join(sorted(sc.facts)) or "(none)"
    ev = sc.evidence
    lines = [
        f"sidecar {sc.json_path}",
        f"  facts:      {facts}",
        f"  exchanges:  {ev.get('exchange_count', '?')} "
        f"({ev.get('answered_count', '?')} answered)",
        f"  branches:   {ev.get('branch_count', '?')}",
        f"  models:     {', '.join(ev.get('models', [])) or '(none)'}",
        f"  transitions:{len(sc.transitions)}",
    ]
    for t in sc.transitions[-5:]:
        lines.append(f"    {t['ts']}  {t['node']}: {t['from']} → {t['to']}  "
                     f"({t['cost_ms']} ms) {t['detail']}")
    return "\n".join(lines)


def cmd_steps(ctx: Ctx) -> str:
    from . import planner
    from .sidecar import resolve_local_id
    sc = Sidecar(resolve_local_id(ctx.chat_id, ctx.work), work=ctx.work)
    return planner.describe(ctx.target, sc)


# handler registry (name → fn), used by the CLI and the planner's --ensure
HANDLERS = {
    "list": cmd_list,
    "load": cmd_load,
    "model": cmd_model,
    "segment": cmd_segment,
    "artifacts": cmd_artifacts,
    "tiddlers": cmd_tiddlers,
    "summary": cmd_summary,
    "status": cmd_status,
    "steps": cmd_steps,
}
