# CHATDRILL — Code reconstruction from chat histories (plan)

> **A code fragment is not text. It is an incomplete projection of a graph.**

Chats deliver code **incrementally and out of order**: drafts, patches ("replace
line 42"), re-pastes, multi-file dumps. GraphRAG-style token chunking throws that
structure away. The right model is borrowed from **compilers + LSP symbol tables +
git + genome assembly**: isolate fragments, lift them to symbols, track versions,
and synthesize virtual files. This doc maps that 12-layer model onto CHATDRILL and
marks what exists, what's next, and what waits for test data / an LLM.

## Status legend
`DONE` shipped · `PARTIAL` partly there · `NEXT` build soon, deterministic ·
`DATA` needs the incoming per-provider test links · `LLM` needs a model call.

## Layer map

| L | Layer | CHATDRILL status | Where / note |
|---|-------|------------------|--------------|
| 0 | **Isolate code** (vs prose, LaTeX, console, traceback, HTML, OCR junk) | `DONE` / `PARTIAL` | pass03 `segment` (prose/code, fenced + stripped-fence recovery); pass04 lifts code/url/error. *Still to split out:* LaTeX envs, console sessions, OCR artifacts ("Copy/Edit/Run") as their own kinds. |
| — | **Explo multi-file** `!!! path/file` | `DONE (today)` | pass `files` / `codefiles.py` — the deterministic, header-given case of Layers 0+4. 29 corpus chats, 523 paths. |
| 1 | **Symbol objects** (language, kind, symbols[], imports[]) | `PARTIAL` → `NEXT` | `_signature` (def/class/interface names) already used by pass14; promote to a real symbol extractor with `imports` + `kind`. Deterministic (regex/tree-sitter). |
| 2 | **Fragment graph** (versions, not duplicates) | `PARTIAL` | pass14 already groups by identity; needs an explicit version-DAG per identity (git-commit-like). |
| 3 | **Reconstruction by unification** (fragments may unify; confidence) | `LLM` / `NEXT` | Prolog-style: stitch `class A:` + `def foo()`. Start deterministic (containment by indentation/symbol), escalate uncertain joins to an LLM with a confidence score. |
| 4 | **File hypotheses** (synthesize `src/csp.py` from pieces) | `DONE` (explicit) / `DATA` (implicit) | Explicit `!!!`-header files = done today. Implicit (no header) file synthesis needs unification (L3). |
| 5 | **Symbol database** (call/dependency/import graph) | `NEXT` | LSP-index style; build once symbols (L1) exist. tree-sitter per language. |
| 6 | **Patch objects** ("replace line 42", "add …") | `DATA` | Detect imperative edits → `{operation, target, payload}` instead of new code. Needs real examples to nail the phrasings. |
| 7 | **Signature fingerprints** (normalize `process(*,*)` + hash) | `NEXT` | Rename-invariant matching; strengthens L2/L3 identity beyond today's symbol-name signature. |
| 8 | **Missing-hole objects** (`__HOLE__` between constructor and process) | `LLM` | Record gaps; an LLM infers the missing region later. |
| 9 | **Evolution chain** (v1→v2→v3, not one canonical) | `DONE` | pass14 reverse-time fold: canonical latest + `superseded` lineage. Verified: "Json to Gawk" folds 74 blocks → 26 canonical (48 collapsed). The DAG (L2) makes this branch-aware. |
| 10 | **Cross-language entities** (`class User` ≡ `CREATE TABLE users`) | `LLM` | GraphRAG entity extraction over symbols; one `ENTITY User` spanning py/sql/REST/HTML/tests. |
| 11 | **Contextual summaries** (describe before embedding) | `LLM` | Generate a one-line summary per symbol/file; embed the summary, not raw code. |
| 12 | **Compiler-style pipeline** (the whole thing) | in progress | RAW→listing→language→fragment→symbol→patch→unify→virtual-files→graph→summary→embed. CHATDRILL's pass pipeline already IS this shape. |

Crazy-but-tracked: **genome-assembly** (k-mer overlap graph over fragments to
assemble files) is an alternative to L3 unification for the implicit case — a good
fit because source code is hugely redundant. Held as a research spike behind test
data. **First-class tiddlers** (`$virtual_file/…`, `$symbol/…`, `$patch/…`,
`$entity/…`) is the storage/΄UI target once L1–L5 exist.

## Build order (deterministic-first, LLM-last)
1. **Explo virtual files** (`files`) — today. ✅
2. **Symbol extractor** (L1) + **signature fingerprints** (L7) — deterministic, next.
3. **Symbol DB / call graph** (L5) — tree-sitter, deterministic.
4. **Patch detector** (L6) — once test data shows the phrasings.
5. **Unification / file hypotheses** (L3/L4 implicit) — deterministic core, LLM for uncertain joins.
6. **Summaries + embeddings** (L11) and **cross-language entities** (L10) — LLM.

Rationale: every deterministic layer makes the LLM layers cheaper and more
accurate. We do not embed raw `process()`; we embed after symbols + summaries.

---

## Input-encoder layer (per chat-history provider)

> "Organize different input encoder layers per chat-history provider given in the URL."

Acquisition (pass00) is **provider-specific and pluggable**; the semantic compiler
only ever sees a normalized `RawChat`. A registry selects the encoder by reference
(URL host, file schema, or local db). One encoder per provider:

| Provider | Selector | Native shape (Appendix C) | Status |
|----------|----------|---------------------------|--------|
| **OpenWebUI** | local `webui.db` / chat-id | message **tree** (`history.messages`) | `DONE` — `sources/openwebui.py` |
| **Perplexity** | `perplexity.ai` host / `*.json` export | flat `entries[]` Q&A blocks | `DATA` — send a link |
| **ChatGPT** | `chatgpt.com` / `conversations*.json` | `mapping` tree | `DATA` — send a link |
| **DeepSeek** | `chat.deepseek.com` | JSON export (instant) | `DATA` — send a link |
| **Qwen / Tongyi** | `tongyi`/`qwen` host | JSON export | `DATA` — send a link |
| **Gemini** | `gemini.google.com` | DOM/scrape | `DATA` — send a link |

Each encoder implements the `Source` interface (`matches(ref)` + `load(ref) ->
RawChat`). The registry (`sources/registry.py`) maps host→encoder and reports which
providers still await an encoder. **When you send a test link per provider, I build
that encoder** so its chats normalize to the same `Exchange[]` everything else
consumes — and the explo/symbol layers above then work uniformly across providers.

## What I need from the test data (per link)
- one representative chat URL (or exported JSON) per provider;
- ideally one that contains an **explo `!!!` multi-file** dump and one with
  **iterative code drafts** (for L2/L9), so each encoder is validated against the
  code-reconstruction path, not just plain Q&A.
