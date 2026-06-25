---
name: chatdrill
description: Use when the user wants to import, extract, export, convert, or analyze chat histories from an LLM provider (Perplexity, ChatGPT, Claude, DeepSeek, OpenWebUI, Kimi, Z.ai, Gemini) — turning a raw export into a structured docmodel and TiddlyWiki. Covers acquisition (how to get the history out of each provider, including browser-console extraction) and the CHATDRILL pipeline (split → ingest → segment/artifacts/results/files → docmodel/tiddlers/md).
---

# CHATDRILL — chat history → structured knowledge

CHATDRILL is a semantic compiler for chat histories. It normalizes any provider's
export to a common `Exchange[]` (Q&A pairs), differentiates items (code / urls /
errors / formulas), reconstructs files and the latest-version-per-artifact, and
projects to a PDFDRILL-compatible **docmodel** and to **TiddlyWiki** (markdown
tiddlers with templated transclusions, KaTeX, highlighted code).

## The two halves

1. **Acquisition** — get the history OUT of the provider. This differs per host:
   official export (ChatGPT/Claude/DeepSeek), a local DB (OpenWebUI), or a
   **browser-console / logged-in-session** extraction (Perplexity, and the
   bot-protected share pages). Each provider has a howto under `providers/`.
2. **Pipeline** — feed the export to CHATDRILL.

## How to help the user

When the user wants to import from a provider, **open the matching howto and
follow it**, then run the pipeline:

| Provider | Howto | Get it via |
|---|---|---|
| Perplexity | [providers/perplexity.md](providers/perplexity.md) | browser-console batch extractor (50/batch) |
| ChatGPT | [providers/chatgpt.md](providers/chatgpt.md) | Settings → Data Controls → Export (.zip) |
| Claude | [providers/claude.md](providers/claude.md) | Settings → Export data (.zip) |
| DeepSeek | [providers/deepseek.md](providers/deepseek.md) | Profile → Data export (.zip) OR public share link |
| OpenWebUI | [providers/openwebui.md](providers/openwebui.md) | local `webui.db` (no export needed) |
| Kimi | [providers/kimi.md](providers/kimi.md) | export (encoder pending a sample) |
| Z.ai (GLM) | [providers/zai.md](providers/zai.md) | export (encoder pending a sample) |
| Gemini | [providers/gemini.md](providers/gemini.md) | DOM/Takeout (encoder pending a sample) |

Index of all providers: [providers/README.md](providers/README.md).

## The pipeline (after you have an export file)

```bash
# 1. split a bulk export (.json or .zip) into per-chat files under raw/<provider>/
chatdrill split <export.json|.zip>

# 2. ingest one chat (auto-detects the provider) → builds the model in drill/
chatdrill ingest raw/<provider>/<id>.json

# 3. run the rest of the chain (idempotent, fact-gated) via --ensure
chatdrill tiddlers  <id-prefix> --ensure     # → wiki/tiddlers/  (TiddlyWiki)
chatdrill docmodel  <id-prefix> --ensure     # → drill/<id>.chatdrill/docmodel.json
chatdrill md        <id-prefix>               # whole chat as one Markdown doc
chatdrill results   <id-prefix> --ensure     # reverse-time "deliverable" view
chatdrill files     <id-prefix> --ensure     # reconstruct explo !!! files
```

OpenWebUI needs no export — `chatdrill list` then `chatdrill model <id> --db <webui.db>`.

## Running in the Claude.ai sandbox

CHATDRILL is pure Python (pydantic v2 + pyyaml). In a sandbox:
1. Upload the CHATDRILL `src/` (or the repo) and the provider export.
2. `pip install pydantic pyyaml` if needed.
3. `PYTHONPATH=src python -m chatdrill split <export>` … then `ingest`, `tiddlers`, etc.
The acquisition step (browser-console extraction) runs in the user's **own
browser**, not the sandbox — the sandbox only processes the resulting export file.

## Commands (full surface)
`list · source · split · ingest · model · segment · artifacts · results · files ·
docmodel · tiddlers · md · summary · status · steps`. Run `chatdrill steps <cmd>
<id>` to see a command's prerequisite chain.
