# CHATDRILL

**A semantic compiler for chat histories.** CHATDRILL turns chaotic, multi-turn LLM
chat exports into structured, queryable knowledge — normalizing any provider's
export to a common Q&A model, differentiating items (code / urls / errors /
formulas), reconstructing files and the latest-version-per-artifact, and projecting
to a PDFDRILL-compatible **docmodel** and to **TiddlyWiki**.

It is the conversational sibling of [PDFDRILL](../MX/PDFDRILL): same docmodel IR,
same config-ordered passes, same flat prose CLI, same `.drill` sidecar state machine.

> A chat is not a document — it is a *trajectory through semantic space*. The value
> sits at the end (the working code, the answer that stuck), so CHATDRILL reads it
> **reverse-time** to surface the deliverable, with the messy path collapsed behind.

## Layout (llmwiki: raw → drill → wiki)

```
raw/    input conversation files + per-chat splits (raw/<provider>/)   [git-ignored]
drill/  docmodel structure: <id>.chatdrill.json sidecar + blobs         [git-ignored]
wiki/   the TiddlyWiki results (run the TW server here); wiki/tiddlers/
src/chatdrill/   the package (models, sources, passes, projectors)
docs/            design RFCs (see below)
.claude/skills/chatdrill/   the skill + per-provider extraction howtos
```

## Install / run

Python 3 + pydantic v2 + pyyaml. The `./chatdrill` wrapper loads `.env` and sets
`PYTHONPATH=src`.

```bash
cp .env.example .env            # set OPENWEBUI_DB, provider API keys (offline path needs none)
./chatdrill list                # browse chats in the local OpenWebUI db
```

## Pipeline

Acquisition (get a chat in) → a fact-gated, idempotent build chain → projections.

```bash
# acquisition (see the per-provider howtos)
chatdrill split  <export.json|.zip>          # bulk export → raw/<provider>/<id>.json
chatdrill ingest raw/<provider>/<id>.json    # → model in drill/  (auto-detects provider)

# build chain (each step is a fact-gated pass; --ensure runs prerequisites)
chatdrill tiddlers <id> --ensure   # model→segment→artifacts→tiddlers  → wiki/tiddlers/
chatdrill docmodel <id> --ensure   # …→results→files→docmodel          → drill/<id>.chatdrill/docmodel.json
chatdrill md       <id>             # whole chat as one Markdown doc to paste into an LLM
chatdrill results  <id> --ensure   # reverse-time "deliverable" view
chatdrill status   <id>            # sidecar facts / evidence / transitions
chatdrill steps <cmd> <id>         # show a command's prerequisite chain
```

Full command surface: `list · source · split · ingest · model · segment · artifacts ·
results · files · docmodel · tiddlers · md · summary · status · steps`.

## Providers

| Provider | Status | Get it via |
|---|---|---|
| OpenWebUI | ✅ | local `webui.db` (no export) |
| ChatGPT | ✅ | official data export (.zip) |
| Claude | ✅ | official data export (.zip) |
| DeepSeek | ✅ | data export (.zip) or public share link |
| Perplexity | ✅ | browser-console index + bodies scripts |
| Kimi · Z.ai · Gemini | ⚠ pending | URL parses; extraction method needed |

All normalize to the same `Exchange[]`. Per-provider extraction instructions:
[.claude/skills/chatdrill/providers/](.claude/skills/chatdrill/providers/README.md).

## TiddlyWiki output

Tiddlers are `text/markdown` (KaTeX math, highlighted code) with PDFDRILL-style
templated transclusion (`{{X||CODE}}`), provider+type tags, and a bibkey namespace
(`Pplx20231003_Foo`). Serve the wiki with:

```bash
tiddlywiki wiki --listen        # or: npx tiddlywiki wiki --listen
```

## Design docs

- [docs/CHATDRILL_DESIGN.md](docs/CHATDRILL_DESIGN.md) — the semantic-compiler RFC (passes, data models, metrics)
- [docs/DOCMODEL_ALIGNMENT.md](docs/DOCMODEL_ALIGNMENT.md) — how the model maps to PDFDRILL's docmodel/docpack
- [docs/CODE_RECONSTRUCTION.md](docs/CODE_RECONSTRUCTION.md) — the 12-layer code-reconstruction plan
- [PLANNING.md](PLANNING.md) — living plan & status · [SKILL.md](SKILL.md) — repo conventions

## Tests

```bash
for t in tests/test_*.py; do PYTHONPATH=src python3 "$t"; done   # 11 test files
```

## Status

Acquisition + the deterministic pipeline (load → segment → artifacts → reverse-time
→ explo files → docmodel/tiddlers/md) are implemented and tested. The LLM-assisted
semantic passes (speech-acts, insight scoring, the §11 SemanticUnit + global passes)
and the drillui REPL are designed but not yet built. See `PLANNING.md`.
