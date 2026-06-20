# CHATDRILL — Planning

## Goal
CHATDRILL is a **semantic compiler for chat histories** — the conversational sibling of
PDFDRILL. Given a single chat (URL / OpenWebUI chat-id / JSON), it runs a multi-pass
pipeline that recovers latent semantic states and transitions, computes frustration /
personality metrics, and emits a queryable **hypergraph** + **trajectory graph**,
exportable to TiddlyWiki. Full design: [docs/CHATDRILL_DESIGN.md](docs/CHATDRILL_DESIGN.md).

## Inputs (start phase)
- Chat histories converted to **OpenWebUI JSON**, in `~/myopenwebui/webui.db`
  (`chat` table, 1327 chats). Messages are a **tree** (`history.messages` keyed by id,
  `parentId`/`childrenIds`, `history.currentId` = leaf of the canonical path).
  Branches off the current path = "forgotten branches" — first-class signal.
- Later: control via a **REPL-like UI** in two versions — a terminal version and a web
  HTML version that calls the terminal version over a WebSocket (PDFDRILL `drillui`
  pattern: `drillui_chat.py` brain + `drillui_bridge.ts` + `drillui_term.html`).

## Status
- Project scaffolded: folders (`tiddlers/`, `oldstuff/`, `tmp/`), `tiddlywiki.info`,
  `SKILL.md`, `PLANNING.md`; pushed to GitHub (WulfKolbe/CHATDRILL, private).
- `oldstuff/perplexport/` = legacy TS reference copy from nopi (gitignored, kept for
  comparison; delete later).
- API keys organized in `.env` (gitignored) + `.env.example` template.
- **Design RFC written**: `docs/CHATDRILL_DESIGN.md` (pipeline, data models, metrics).

## Open questions (carried from the RFC)
- [ ] Embedding model for novelty/loop similarity (local MiniLM vs API) — affects offline-safety.
- [ ] Frame-boundary threshold for semantic-state segmentation (pass08).
- [ ] Corpus-level concept identity resolution aggressiveness.

## Tasks
### Now
- [ ] Scaffold `src/` layout per RFC Appendix A (chatmodel / chatops / adapters / features).
- [ ] Implement `pass01_loadAndNormalize` over the OpenWebUI tree + a `RawChat` model.
- [ ] `chatdrill load <chat-id>` returning a prose tree summary.

### Next
- [ ] Stage-1 passes 02–05 (linearize/branch, segment, artifacts, entities).
- [ ] TiddlyWiki projector (projC) → `tiddlers/`.

### Later
- [ ] LLM-assisted passes (06 speech-acts, 12 insights) with heuristic fallbacks.
- [ ] drillui REPL (terminal + Bun bridge + xterm UI).
- [ ] Corpus build + per-model personality UMAP.

## Decisions
- Scratch files go in `tmp/`, never `/tmp`.
- Legacy code is archived in `oldstuff/` (read-only reference).
- Mirror PDFDRILL conventions: config-ordered passes, `.chatdrill.json` sidecar,
  flat prose CLI, `commands.yaml` SSOT, Python+Pydantic live path / Bun only for the bridge.
- Offline-safe by construction: only LLM passes need keys; they degrade to heuristics.
