# CHATDRILL — Planning

## Goal
CHATDRILL is a **semantic compiler for chat histories** — the conversational sibling of
PDFDRILL. Given a single chat (URL / OpenWebUI chat-id / JSON), it runs a multi-pass
pipeline that recovers latent semantic states and transitions, computes frustration /
personality metrics, and emits a queryable **hypergraph** + **trajectory graph**,
exportable to TiddlyWiki. Full design: [docs/CHATDRILL_DESIGN.md](docs/CHATDRILL_DESIGN.md).

## Inputs (start phase) — surveyed real corpora, see RFC Appendix C
- **OpenWebUI** `~/myopenwebui/webui.db` (`chat` JSON, 1327): message **tree**
  (`history.messages`, `parentId`/`childrenIds`, `currentId`). No token counts here.
  → start by extracting chats from here (`chatdrill load --db <chat-id>`).
- **Perplexity JSON** `oldstuff/perplexport/perplexports/*.json`: flat `entries[]` =
  Q&A blocks (`query_str`, `blocks[]`, `display_model`, `mode`, ISO timestamps).
- **Perplexity MD/URLs** `~/perplexport/perplexports/*.md` (689) + `urllist.txt` (688).
- **ChatGPT export** `~/Downloads/conversations.old.json` (625): `mapping` **tree**,
  `metadata.model_slug` (gpt-4o…gpt-5-2-thinking), citations/attachments; the bulk
  "download conversion" with all chats in one file → split by separate tools.
- Reality: only **two shapes** (tree | flat Q&A list); **tokens usually absent**;
  **model + timestamps almost always present**. Adapters normalize all to `Exchange[]`.
- Later: control via a **REPL-like UI** in two versions — terminal + web HTML over a
  WebSocket (PDFDRILL `drillui` trio: `drillui_chat.py` + `drillui_bridge.ts` + `_term.html`).

## Current focus
The **semantic-compiling algorithm at the Exchange layer** (RFC §11): assume access is
solved; operate on a normalized `Exchange[]` (Q&A pairs + optional model/time/token/
citation enrichment). Each extra field has one job (latency→frustration, model→escalation
+ fingerprint + provenance, citations→insight refs, etc.); consumers degrade when absent.

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
- [x] Scaffold `src/chatdrill/` (models, sources/openwebui, passes/linearize, cli).
- [x] `pass01` — load OpenWebUI chat from `webui.db` (read-only SQLite) → `RawChat`.
- [x] `pass02` — reduce tree → canonical `Exchange[]` + forgotten branches.
- [x] `chatdrill list` / `chatdrill load <id> [--json]` prose Q&A-pair summary.
- [x] `chatdrill md <id> [--out F]` — whole chat as one Markdown doc (stdout pure +
      .md file; code re-fenced) to open/copy into an LLM, like PDFDRILL's `md`.
- [x] Tests (synthetic trees) + full-corpus smoke test: 1327 chats, 5482 exchanges, 0 errors.

### Next
- [x] Sidecar (`drills/<id>.chatdrill.json` + blob dir) + facts/evidence/layers/transitions.
- [x] `commands.yaml` SSOT + planner (`requires`/`done_when`, `steps`, `--ensure`).
- [x] `model` (idempotent build+persist), `summary` (reads persisted), `status`, `steps`.
- [x] `pass03` segment (prose/code; fenced + stripped-fence language-token recovery).
- [x] `pass04` artifacts (code/url/error) with sha1 for code lineage.
- [x] `segment`/`artifacts` commands gated by SEGMENTED/ARTIFACTS facts; chain
      `model → segment → artifacts` via planner + `--ensure`.
- [x] TiddlyWiki projector (projC) → `tiddlers/`: chat overview + exchange + Code
      tiddlers (code re-fenced even when source fences were stripped); `<id>.tiddlers.json`
      import blob in the drill dir. Chain: `model → segment → artifacts → tiddlers`.
      Generated `.tid` files gitignored (data, not source).
- [x] `pass14` reverse-time fold → ResultsView: collapse code drafts by identity
      (filename > top-level-symbol signature > sha1) to the canonical latest +
      `superseded` lineage; list unresolved questions. `results` cmd + `results.json`.
      Verified: "Json to Gawk" chat folds 74 code blocks → 26 canonical (48 collapsed).
- [x] Code-reconstruction plan ([docs/CODE_RECONSTRUCTION.md](docs/CODE_RECONSTRUCTION.md)):
      12-layer model (compiler/LSP/git/genome-assembly) mapped onto CHATDRILL passes.
- [x] Provider input-encoder layer: `sources/base.py` (Source interface) +
      `sources/registry.py` (host→encoder, awaiting list). OpenWebUI implemented;
      perplexity/chatgpt/deepseek/qwen/gemini declared, awaiting test links.
- [x] Explo `!!! path/file` virtual-file splitter (Layer 0+4 header case): `files`
      command reconstructs latest-per-path files to `<id>.chatdrill/files/`.
      Corpus: 29 explo chats → 519 files, 764 drafts collapsed.
- [ ] **Awaiting**: per-provider test links → build each `sources/<provider>.py` encoder.
- [ ] Code layers next (deterministic-first): L1 symbol extractor + L7 signature
      fingerprints → L5 symbol/call graph → L6 patch detector → L3/L4 unification.
- [ ] `pass05` entity extraction; `pass07` affect markers.
- [ ] Surface ResultsView + virtual files in tiddlers ($virtual_file/$symbol).

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
- **Reverse-time principle (core):** value extraction reads the chat newest→oldest. The
  user's view is a *results/reuse surface* (latest canonical version of each code file /
  answer / conclusion, deduped by identity, older drafts collapsed as `superseded`), NOT a
  chronological transcript. Implemented as `pass14_reverseTimeFold → ResultsView`.
- **Storage/state machine = PDFDRILL's sidecar+planner verbatim:** cumulative `facts` set +
  `evidence` + blob `layers` + transition log; declarative `requires`/`done_when` so
  layer-by-layer reruns skip satisfied passes (idempotency is structural). Only offline
  prerequisites auto-run via `--ensure`; acquisition/LLM passes never auto-run.
- **Acquisition (`pass00`) is pluggable and out of core:** URL → host-specific adapters /
  browser extension (hard for Western providers; Chinese give JSON). For the compiler
  phase, shortcut via `webui.db` (`chatdrill load --db <chat-id>`).
- Chat code fragments → `Code` tiddlers + blobs under `.chatdrill/code/`.
- **Canonical internal unit = `Exchange` (Q&A pair)** (decided 2026-06-20). Source message
  trees (OpenWebUI, ChatGPT) are reduced at pass02 to `Exchange[]` (current-path spine) +
  a `forgottenBranches` list + per-exchange `regenCount`. Matches Perplexity natively;
  keeps the algorithm simple. The full tree is not the canonical IR.
