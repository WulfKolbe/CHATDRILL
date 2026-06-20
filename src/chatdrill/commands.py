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

from .models import ChatModel
from .passes.linearize import linearize
from .sidecar import Sidecar
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


def cmd_summary(ctx: Ctx) -> str:
    """Print the Q&A summary from the PERSISTED ChatModel (requires: model)."""
    full_id = openwebui.resolve_id(ctx.chat_id, db=ctx.db)
    sc = Sidecar(full_id, work=ctx.work)
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
    "summary": cmd_summary,
    "status": cmd_status,
    "steps": cmd_steps,
}
