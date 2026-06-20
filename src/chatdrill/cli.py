"""chatdrill CLI — flat, prose-returning (PDFDRILL convention).

Today's commands (the pass01→pass02 slice):

  chatdrill list [--db PATH] [--limit N]      list chats in webui.db
  chatdrill load <chat-id> [--db PATH] [--json]   load + reduce to Exchange[], summarize

`load` runs pass01 (openwebui source) → pass02 (linearize) and prints a Q&A-pair
summary, or the full ChatModel as JSON with --json.
"""
from __future__ import annotations

import argparse
import sys

from .passes.linearize import linearize
from .sources import openwebui


def _do_list(args) -> str:
    chats = openwebui.list_chats(db=args.db, limit=args.limit)
    if not chats:
        return "no chats found in webui.db."
    lines = [f"{len(chats)} chat(s) (most recent first):"]
    for c in chats:
        lines.append(f"  {c['id'][:12]}…  msgs={c['messages']:>3}  {c['title']!r}")
    return "\n".join(lines)


def _summary(model) -> str:
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


def _do_load(args) -> str:
    raw = openwebui.load_chat(args.chat_id, db=args.db)
    model = linearize(raw)
    if args.json:
        return model.model_dump_json(indent=2)
    return _summary(model)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="chatdrill",
                                 description="Semantic compiler for chat histories.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list chats in webui.db")
    p_list.add_argument("--db", help="path to webui.db (default: $OPENWEBUI_DB)")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.set_defaults(fn=_do_list)

    p_load = sub.add_parser("load", help="load a chat and reduce to Exchange[]")
    p_load.add_argument("chat_id", help="chat id or unique prefix")
    p_load.add_argument("--db", help="path to webui.db (default: $OPENWEBUI_DB)")
    p_load.add_argument("--json", action="store_true", help="emit the full ChatModel JSON")
    p_load.set_defaults(fn=_do_load)

    args = ap.parse_args(argv)
    try:
        print(args.fn(args))
        return 0
    except (FileNotFoundError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
