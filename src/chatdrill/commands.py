"""Command handlers — return prose strings (PDFDRILL convention).

A small ``Ctx`` carries the resolved args; each handler takes it, does its work,
and returns text. ``cmd_model`` is the persisting, idempotent build: it writes
chatmodel.json + records the MODEL_BUILT fact, and on re-run detects the fact and
skips unless ``--force``.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

from .models import ChatModel
from .passes.artifacts import extract_artifacts
from .passes.codefiles import extract_virtual_files
from .passes.docmodel_export import object_counts, to_document
from .passes.linearize import linearize
from .passes.reverse_time import fold
from .passes.segment import segment_model
from .projectors.markdown import render_chat_markdown
from .projectors.tiddlywiki import (bibkey, build_tiddlers, to_tid_text,
                                    tiddler_integrity, _safe_filename)
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
    export: Optional[str] = None      # export file for `ingest`
    provider: Optional[str] = None    # provider override for `ingest`


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


def _view_model(ctx: Ctx, segment: bool = False) -> tuple[ChatModel, Sidecar]:
    """A model for a read-only view (load/md), source-agnostic: use the persisted
    model if one exists (any provider, incl. ingested exports), else build it
    ephemerally from the local webui.db. Returns (model, its sidecar)."""
    local = resolve_local_id(ctx.chat_id, ctx.work)
    sc = Sidecar(local, work=ctx.work)
    if sc.has_blob("chatmodel.json"):
        model = _load_persisted(sc)
    else:
        raw = openwebui.load_chat(ctx.chat_id, db=ctx.db)
        sc = Sidecar(raw.id, work=ctx.work)
        model = linearize(raw)
    if segment:
        segment_model(model)
    return model, sc


def cmd_load(ctx: Ctx) -> str:
    """Read-only Q&A summary. Uses the persisted model if present, else builds it
    ephemerally from webui.db."""
    model, _ = _view_model(ctx)
    return model.model_dump_json(indent=2) if ctx.as_json else _summary(model)


def cmd_md(ctx: Ctx) -> str:
    """Render the whole chat as one Markdown doc (like PDFDRILL's `md`).

    Self-contained (pass01→02→03 in memory, no pipeline needed). Prints the
    Markdown to stdout — pure, so you can pipe/copy it — and also writes a .md
    file you can open, reporting its path on STDERR so it never pollutes stdout.
    """
    model, sc = _view_model(ctx, segment=True)   # segment so code re-fences cleanly
    md = render_chat_markdown(model)
    if ctx.out:
        path = Path(ctx.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(md, encoding="utf-8")
        path = str(path)
    else:                                     # default: a stable file in the drill dir
        path = sc.write_blob("chat.md", md)
    print(f"wrote {path}", file=sys.stderr)
    return md


def _build_persist(raw, ctx: Ctx) -> str:
    """Build + persist a ChatModel from a RawChat (any provider). Idempotent:
    skip if MODEL_BUILT + artifact present, unless --force. Sidecar keyed by the
    canonical chat id, so providers and prefixes stay consistent."""
    sc = Sidecar(raw.id, work=ctx.work)
    if sc.has("MODEL_BUILT") and sc.has_blob("chatmodel.json") and not ctx.force:
        n = sc.get_evidence("exchange_count", "?")
        return (f"model already built for {sc.chat_id[:12]}… "
                f"({n} exchanges) — skipped. Use --force to rebuild.")
    t0 = time.perf_counter()
    model = linearize(raw)
    sc.write_blob("chatmodel.json", model.model_dump_json(indent=2))
    cost_ms = (time.perf_counter() - t0) * 1000

    answered = sum(1 for e in model.exchanges if e.answered)
    sc.set_layer("chatmodel", {"path": "chatmodel.json", "format": "ChatModel/json"})
    sc.set_evidence("source", raw.source)
    sc.set_evidence("exchange_count", len(model.exchanges))
    sc.set_evidence("answered_count", answered)
    sc.set_evidence("branch_count", len(model.forgotten_branches))
    sc.set_evidence("models", sorted({e.model for e in model.exchanges if e.model}))
    was = "INIT" if not sc.facts else ",".join(sorted(sc.facts))
    sc.add_fact("MODEL_BUILT")
    sc.log_transition("model", was, "MODEL_BUILT", cost_ms,
                      f"{len(model.exchanges)} exchanges [{raw.source}]")
    sc.save()
    return (f"built model for {sc.chat_id[:12]}… ({raw.source}): "
            f"{len(model.exchanges)} exchanges ({answered} answered, "
            f"{len(model.forgotten_branches)} branches) in {cost_ms:.0f} ms")


def cmd_model(ctx: Ctx) -> str:
    """Build + persist the ChatModel from the local webui.db (idempotent)."""
    full_id = openwebui.resolve_id(ctx.chat_id, db=ctx.db)
    return _build_persist(openwebui.load_chat(full_id, db=ctx.db), ctx)


def cmd_source(ctx: Ctx) -> str:
    """Resolve a provider URL (or local ref) → provider + chat id + how to ingest."""
    from .sources import registry
    ref = ctx.chat_id
    if ref.startswith(("http://", "https://")):
        prov, cid = registry.parse_url(ref)        # ValueError → cli error
        how = {
            "db": "local webui.db",
            "export": f"export the conversation as JSON, then: "
                      f"chatdrill ingest <export.json> --id {cid[:12]}",
            "awaiting": f"send a sample {prov.name} export — I'll build sources/{prov.name}.py",
        }[prov.status]
        return (f"provider: {prov.name}\n  chat id: {cid}\n  shape:   {prov.shape}\n"
                f"  status:  {prov.status}\n  ingest:  {how}")
    src = registry.for_ref(ref)                    # local chat-id → openwebui
    return f"provider: {src.name} (local) — ref {ref!r} is directly loadable."


def _maybe_unzip(path: str) -> str:
    """A provider export may arrive as a .zip (ChatGPT 'Export data'). Extract the
    conversations.json (else the largest .json) to ./tmp and return its path."""
    if not path.lower().endswith(".zip"):
        return path
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        target = next((n for n in names if n.endswith("conversations.json")), None)
        if target is None:
            jsons = [(z.getinfo(n).file_size, n) for n in names if n.endswith(".json")]
            if not jsons:
                raise ValueError(f"no .json inside {path}")
            target = max(jsons)[1]
        out = Path("tmp") / f"{Path(path).stem}__{Path(target).name}"
        out.parent.mkdir(parents=True, exist_ok=True)
        with z.open(target) as src, open(out, "wb") as dst:
            shutil.copyfileobj(src, dst)
        print(f"unzipped {target} → {out}", file=sys.stderr)
        return str(out)


def cmd_split(ctx: Ctx) -> str:
    """Split a bulk export (.json or .zip) into per-chat files under
    raw/<provider>/ — each then ingestable on its own with `chatdrill ingest`."""
    from .sources import chatgpt, claude, perplexity
    if not Path(ctx.export).exists():
        raise FileNotFoundError(f"export file not found: {ctx.export}")
    path = _maybe_unzip(ctx.export)
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if chatgpt.is_chatgpt_export(path):
        prov = "chatgpt"
        items = [(c.get("id") or c.get("conversation_id") or str(i), c)
                 for i, c in enumerate(data if isinstance(data, list) else [data])]
    elif claude.is_claude_export(path):
        prov = "claude"
        items = [(c.get("uuid") or str(i), c) for i, c in enumerate(data)]
    elif perplexity.is_perplexity_export(path):
        prov = "perplexity"
        src = data.items() if isinstance(data, dict) else \
            ((b.get("id", str(i)), b) for i, b in enumerate(data))
        items = [(slug, {slug: body}) for slug, body in src]   # keep dump shape
    else:
        raise ValueError(f"unrecognized bulk export {path}. "
                         f"Supported: chatgpt, claude, perplexity.")

    out_dir = _raw_dir(ctx) / prov
    out_dir.mkdir(parents=True, exist_ok=True)
    for cid, obj in items:
        safe = _safe_relpath(str(cid)) or "chat"
        (out_dir / f"{safe.replace('/', '_')}.json").write_text(
            json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return (f"split {len(items)} {prov} chat(s) → {out_dir}/\n"
            f"  ingest one with:  chatdrill ingest {out_dir}/<id>.json")


def cmd_ingest(ctx: Ctx) -> str:
    """Ingest a provider export file (.json or .zip) → build + persist the ChatModel."""
    from .sources import chatgpt, claude, perplexity
    if not Path(ctx.export).exists():
        raise FileNotFoundError(f"export file not found: {ctx.export}")
    path = _maybe_unzip(ctx.export)
    prov = ctx.provider
    if prov is None:                              # auto-detect
        if chatgpt.is_chatgpt_export(path):
            prov = "chatgpt"
        elif claude.is_claude_export(path):
            prov = "claude"
        elif perplexity.is_perplexity_export(path):
            prov = "perplexity"
    loaders = {"chatgpt": chatgpt.load_export, "claude": claude.load_export,
               "perplexity": perplexity.load_export}
    if prov not in loaders:
        raise ValueError(f"unsupported/undetected export format for {path}. "
                         f"Supported: {', '.join(loaders)}. Use --provider to force.")
    raw = loaders[prov](path, chat_id=ctx.chat_id)
    msg = _build_persist(raw, ctx)
    return (msg + f"\n  chat id: {raw.id}\n  next: chatdrill files {raw.id[:12]} --ensure "
            f"· chatdrill md {raw.id[:12]}")


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


def cmd_results(ctx: Ctx) -> str:
    """pass14 — reverse-time fold → ResultsView (requires: artifacts)."""
    sc = _sidecar_for_persisted(ctx)
    if sc.has("RESULTS_FOLDED") and not ctx.force:
        return _results_report(_load_persisted(sc), prefix="already folded")
    t0 = time.perf_counter()
    model = fold(_load_persisted(sc))
    _persist(sc, model)
    sc.write_blob("results.json", model.results.model_dump_json(indent=2))
    cost_ms = (time.perf_counter() - t0) * 1000
    rv = model.results
    collapsed = sum(len(a.superseded) for a in rv.artifacts)
    sc.set_evidence("canonical_artifacts", len(rv.artifacts))
    sc.set_evidence("superseded_drafts", collapsed)
    sc.set_evidence("unresolved_questions", len(rv.unresolved))
    sc.set_layer("results", {"path": "results.json", "format": "ResultsView/json"})
    sc.add_fact("RESULTS_FOLDED")
    sc.log_transition("results", "ARTIFACTS", "RESULTS_FOLDED", cost_ms,
                      f"{len(rv.artifacts)} canonical, {collapsed} collapsed, "
                      f"{len(rv.unresolved)} unresolved")
    sc.save()
    return _results_report(model, prefix=f"folded in {cost_ms:.0f} ms")


def _results_report(model: ChatModel, prefix: str) -> str:
    rv = model.results
    collapsed = sum(len(a.superseded) for a in rv.artifacts)
    lines = [f"{prefix}: {len(rv.artifacts)} canonical artifact(s) "
             f"({collapsed} older draft(s) collapsed), "
             f"{len(rv.unresolved)} unresolved question(s) — newest first:"]
    for a in rv.artifacts:
        first = next((ln for ln in a.content.splitlines() if ln.strip()), "")
        rev = f" ({a.revisions}× revised)" if a.revisions > 1 else ""
        lines.append(f"  • [{a.lang or '?'}] {a.line_count} lines{rev}  "
                     f"ex {a.exchange_index}  id={a.identity[:40]}")
        lines.append(f"      {first.strip()[:64]!r}")
    if rv.unresolved:
        lines.append("  unresolved questions:")
        for u in rv.unresolved:
            lines.append(f"    [ex {u.exchange_index}] {u.text}")
    return "\n".join(lines)


def _safe_relpath(path: str) -> str | None:
    """A path safe to write under the blob dir — no absolute/.. traversal."""
    p = path.lstrip("/")
    if not p or ".." in Path(p).parts:
        return None
    return p


def cmd_files(ctx: Ctx) -> str:
    """Reconstruct explo `!!! path/file` virtual files to disk (requires: model)."""
    sc = _sidecar_for_persisted(ctx)
    if sc.has("FILES_BUILT") and not ctx.force:
        return _files_report(_load_persisted(sc), sc, prefix="already reconstructed")
    t0 = time.perf_counter()
    model = extract_virtual_files(_load_persisted(sc))
    _persist(sc, model)
    # write each reconstructed (latest) file under <id>.chatdrill/files/<path>
    base = sc.blob_dir / "files"
    written = 0
    for vf in model.virtual_files:
        rel = _safe_relpath(vf.path)
        if rel is None:
            continue
        dest = base / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(vf.content, encoding="utf-8")
        written += 1
    cost_ms = (time.perf_counter() - t0) * 1000
    collapsed = sum(len(v.superseded) for v in model.virtual_files)
    sc.set_evidence("virtual_files", len(model.virtual_files))
    sc.set_evidence("virtual_file_revisions_collapsed", collapsed)
    sc.set_layer("files", {"path": "files/", "count": written})
    sc.add_fact("FILES_BUILT")
    sc.log_transition("files", "MODEL_BUILT", "FILES_BUILT", cost_ms,
                      f"{len(model.virtual_files)} files, {collapsed} drafts collapsed")
    sc.save()
    return _files_report(model, sc, prefix=f"reconstructed {written} file(s) in {cost_ms:.0f} ms")


def _files_report(model: ChatModel, sc: Sidecar, prefix: str) -> str:
    vfs = model.virtual_files
    if not vfs:
        return (f"no explo `!!! path/file` files found in {model.id[:12]}… "
                f"(this chat doesn't use that format).")
    collapsed = sum(len(v.superseded) for v in vfs)
    lines = [f"{prefix}: {len(vfs)} virtual file(s) "
             f"({collapsed} older draft(s) collapsed) for {model.id[:12]}…",
             f"  → files in {sc.blob_dir / 'files'}/"]
    for vf in sorted(vfs, key=lambda v: v.path):
        rev = f"  ({vf.revisions}× revised)" if vf.revisions > 1 else ""
        lines.append(f"    {vf.path:<40} [{vf.lang or '?':<10}] "
                     f"{len(vf.content.splitlines()):>4} lines{rev}")
    return "\n".join(lines)


def cmd_docmodel(ctx: Ctx) -> str:
    """Export the chat as a PDFDRILL-compatible docmodel (requires: artifacts)."""
    sc = _sidecar_for_persisted(ctx)
    if sc.has("DOCMODEL_BUILT") and not ctx.force:
        return (f"already exported docmodel for {sc.chat_id[:12]}… "
                f"→ {sc.blob_path('docmodel.json')}")
    t0 = time.perf_counter()
    doc = to_document(_load_persisted(sc))
    sc.write_blob("docmodel.json", json.dumps(doc, indent=2, ensure_ascii=False))
    cost_ms = (time.perf_counter() - t0) * 1000
    counts = object_counts(doc)
    sc.set_evidence("docmodel_objects", counts)
    sc.set_evidence("docmodel_alignments", len(doc["alignments"]))
    sc.set_layer("docmodel", {"path": "docmodel.json", "format": "pdfdrill/docmodel"})
    sc.add_fact("DOCMODEL_BUILT")
    sc.log_transition("docmodel", "ARTIFACTS", "DOCMODEL_BUILT", cost_ms,
                      f"{sum(counts.values())} objects, {len(doc['alignments'])} alignments")
    sc.save()
    obj_str = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    return (f"exported docmodel for {sc.chat_id[:12]}… in {cost_ms:.0f} ms\n"
            f"  streams: turns ({len(doc['streams']['turns']['anchors'])} anchors)\n"
            f"  objects: {obj_str}\n"
            f"  alignments: {len(doc['alignments'])} (supersedes …)\n"
            f"  → {sc.blob_path('docmodel.json')}")


def _tiddlers_dir(ctx: Ctx) -> Path:
    return Path(ctx.out or os.environ.get("CHATDRILL_TIDDLERS") or "wiki/tiddlers")


def _raw_dir(ctx: Ctx) -> Path:
    return Path(ctx.out or os.environ.get("CHATDRILL_RAW") or "raw")


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

    kinds: dict[str, int] = defaultdict(int)
    for t in tids:
        kinds[t["tags"].split(maxsplit=1)[0]] += 1     # first tag = the type
    integ = tiddler_integrity(tids)
    sc.set_evidence("tiddler_count", len(tids))
    sc.set_evidence("tiddler_kinds", dict(kinds))
    sc.set_evidence("transclusions", integ["transclusions"])
    sc.set_evidence("dangling_transclusions", integ["dangling"])
    sc.set_layer("tiddlers", {"path": "tiddlers.json", "format": "tiddlywiki/json"})
    sc.add_fact("TIDDLERS_BUILT")
    sc.log_transition("tiddlers", "ARTIFACTS", "TIDDLERS_BUILT", cost_ms,
                      f"{len(tids)} tiddlers, {integ['transclusions']} transclusions")
    sc.save()
    kind_str = ", ".join(f"{v} {k}" for k, v in sorted(kinds.items()))
    integ_str = ("all transclusions resolve ✓" if not integ["dangling"]
                 else f"DANGLING: {integ['dangling'][:5]}")
    return (f"exported {len(tids)} tiddlers for {bibkey(model)} in {cost_ms:.0f} ms\n"
            f"  kinds: {kind_str}\n"
            f"  transclusions: {integ['transclusions']} ({integ_str})\n"
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
    "md": cmd_md,
    "source": cmd_source,
    "split": cmd_split,
    "ingest": cmd_ingest,
    "model": cmd_model,
    "segment": cmd_segment,
    "artifacts": cmd_artifacts,
    "results": cmd_results,
    "files": cmd_files,
    "docmodel": cmd_docmodel,
    "tiddlers": cmd_tiddlers,
    "summary": cmd_summary,
    "status": cmd_status,
    "steps": cmd_steps,
}
