"""chatdrill CLI — flat, prose-returning (PDFDRILL convention).

Commands (pass01→pass02 slice + the state machine):

  chatdrill list [--db PATH] [--limit N]
  chatdrill load   <id> [--db PATH] [--json]      # ephemeral summary (no persistence)
  chatdrill model  <id> [--db PATH] [--force]     # build + persist ChatModel (idempotent)
  chatdrill summary <id> [--ensure] [--json]      # summary from the persisted model
  chatdrill status <id>                           # sidecar facts/evidence/transitions
  chatdrill steps  <cmd> <id>                     # show the prerequisite chain

Idempotency is structural: `model` records the MODEL_BUILT fact and skips on
re-run; `summary` requires `model` and, with `--ensure`, auto-builds it first.
"""
from __future__ import annotations

import argparse
import sys

from . import planner
from .commands import HANDLERS, Ctx
from .sidecar import Sidecar


def _ctx(args) -> Ctx:
    return Ctx(
        chat_id=getattr(args, "chat_id", None),
        db=getattr(args, "db", None),
        work=getattr(args, "work", None),
        force=getattr(args, "force", False),
        as_json=getattr(args, "json", False),
        limit=getattr(args, "limit", 50),
        target=getattr(args, "target", None),
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="chatdrill",
                                 description="Semantic compiler for chat histories.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def db_arg(p):
        p.add_argument("--db", help="path to webui.db (default: $OPENWEBUI_DB)")

    def work_arg(p):
        p.add_argument("--work", help="artifact root (default: $CHATDRILL_WORK or ./drills)")

    p = sub.add_parser("list", help="list chats in webui.db")
    db_arg(p); p.add_argument("--limit", type=int, default=50)
    p.set_defaults(cmd="list")

    p = sub.add_parser("load", help="load a chat, print an ephemeral summary")
    p.add_argument("chat_id"); db_arg(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(cmd="load")

    p = sub.add_parser("model", help="build + persist the ChatModel (idempotent)")
    p.add_argument("chat_id"); db_arg(p); work_arg(p)
    p.add_argument("--force", action="store_true", help="rebuild even if MODEL_BUILT")
    p.set_defaults(cmd="model")

    p = sub.add_parser("summary", help="summary from the persisted ChatModel")
    p.add_argument("chat_id"); db_arg(p); work_arg(p)
    p.add_argument("--ensure", action="store_true", help="auto-run missing prerequisites")
    p.add_argument("--json", action="store_true")
    p.set_defaults(cmd="summary")

    p = sub.add_parser("status", help="show the sidecar state")
    p.add_argument("chat_id"); work_arg(p)
    p.set_defaults(cmd="status")

    p = sub.add_parser("steps", help="show the prerequisite chain for a command")
    p.add_argument("target", help="the command to plan for (e.g. summary)")
    p.add_argument("chat_id"); work_arg(p)
    p.set_defaults(cmd="steps")

    args = ap.parse_args(argv)
    ctx = _ctx(args)

    try:
        # --ensure: run missing offline prerequisites before the target.
        if getattr(args, "ensure", False):
            from .sources import openwebui
            ctx.chat_id = openwebui.resolve_id(ctx.chat_id, db=ctx.db)  # canonical id
            sc = Sidecar(ctx.chat_id, work=ctx.work)
            planner.ensure(args.cmd, sc, HANDLERS, ctx)
        print(HANDLERS[args.cmd](ctx))
        return 0
    except (FileNotFoundError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
