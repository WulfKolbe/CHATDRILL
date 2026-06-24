# CHATDRILL ⇄ PDFDRILL docmodel/docpack alignment

**The correction:** TiddlyWiki, Markdown, LaTeX, `results.json`, `tiddlers.json`
are **output projections**. They are not the model. The model is a
**docmodel** — the same stratified anchored graph PDFDRILL uses — and every
projector reads it. CHATDRILL must produce (or export to) that structure so the
two integrate.

## The docmodel (verified from `src/docmodel/core.py`)

A `Document` is four strata:

| Stratum | What it is |
|---|---|
| **meta** | small header (source, ids, models, …) |
| **streams** | `name → {anchors:[a_…], payload:{anchor: {...}}}` — ordered content with opaque-anchor identity |
| **objects** | `[{id, type, props, realizations[], children[], parent}]` — every typed entity |
| **alignments** | `[{kind, left:Range, right:Range, props}]` — typed relations between ranges |

Primitives: **Anchor** (opaque stable id), **Stream** (anchors + per-anchor
payload), **Range** `(stream,start,end)`, **Realization** (how an object surfaces
in one stream: `stream,start,end,role,props,provenance,score,region`),
**DocObject** (`type,id,props,realizations,children,parent`), **Alignment**
(typed `left↔right`). Identity is anchor-based, so edits never invalidate
cross-references. `Document.to_dict/from_dict` round-trips losslessly.

**docpack** = the same data, value-interned for storage (`unpack(pack(m))==m`).
Not a different model — a zip. Projectors read the unpacked docmodel.

> The whole architecture: **input → docmodel → projectors.** The semantic
> compiler is the set of passes that *enrich the docmodel* with recovered
> objects/relations. tiddlers/md/latex/semantic are projectors at the end.

## Chat → docmodel

| docmodel | Chat realization |
|---|---|
| **stream `turns`** | anchors = messages; payload = `{role, text, timestamp, model, exchange_index}` (analog of `mathpix_lines`) |
| **DocObject `Exchange`** | realization = range over `turns` (query→answer); props = `{index, model, latency, regen_count}` |
| **DocObject `CodeBlock`** | realization into its turn anchor, role `code`; props `{lang, sha1, line_count, fenced}` |
| **DocObject `Url` / `Error`** | realization into its turn anchor, role `url`/`error` |
| **DocObject `VirtualFile`** | synthesized file; `children` = the CodeBlock fragments; props `{path, lang, revisions}` |
| **DocObject `Symbol`** (L1, next) | props `{name, kind, lang}`; realization into the defining code |
| **Alignment `supersedes`** | reverse-time lineage: canonical realization ↔ each superseded turn (the v1→v2→v3 chain) |
| **Alignment `composes`** | VirtualFile ↔ its fragment ranges |
| **Alignment `defines` / `references` / `corrects`** | Code↔Symbol, Exchange↔Url, answer↔prior (L3/L5) |

So CHATDRILL's existing models are **already DocObject types**, and the
reverse-time `superseded` list is **already an Alignment** (`supersedes`). Nothing
is wasted — it just needs to be *named* in docmodel terms.

### Current models → DocObject types
`Exchange → Exchange` · `Artifact(code/url/error) → CodeBlock/Url/Error` ·
`VirtualFile → VirtualFile` · `CanonicalArtifact + superseded → CodeBlock + supersedes-Alignment` ·
`UnresolvedQuestion → Question`. Projectors (`tiddlers.py`, `markdown.py`) become
docmodel projectors.

## Modular structure (one processor per object type)

Mirror docmodel's processor pipeline (PageProcessor, EquationProcessor, … loaded
from config in `procOrder`). CHATDRILL's passes already are this, re-labelled:

```
turns          (pass02 linearize)      → stream `turns` + Exchange objects
CodeBlock      (pass03/04)             → CodeBlock/Url/Error objects
VirtualFile    (explo / Layer 4)       → VirtualFile objects + composes-alignments
Supersedes     (pass14 reverse-time)   → supersedes-alignments
Symbol         (L1, next)              → Symbol objects + defines-alignments
Patch          (L6)                    → Patch objects + patch-alignments
SemanticUnit   (semantic compiler)     → SemanticUnit objects (below)
```
Each is a module that adds its object type + relations to the Document and is
config-ordered. Deterministic processors first; LLM processors last.

## The Semantic Compiler (operating on the docmodel)

The "Semantic Compiler Mode" spec recovers the **hidden architecture** — objects,
transformations, constraints, invariants, goals — not wording. It runs over the
docmodel and emits typed objects, so its output is itself docmodel-native.

**Per "section"** (for a chat, a *section* = a SemanticState/topic cluster, a
reconstructed VirtualFile, or an Exchange run) it produces a **`SemanticUnit`**
DocObject:

```
SemanticUnit props:
  section, purpose, inputs[], outputs[], objects[], transformations[],
  constraints[], invariants[], dependencies[], algorithms[],
  evidence[]  (short quotes, as Realizations into `turns`),
  hidden_abstractions[], analogies[], open_questions[]
```
`evidence` entries are **Realizations** (ranges into the turn stream) — the model
stays grounded. `objects/transformations/…` become their own DocObjects
(`Object`, `Transformation`, `Constraint`, `Invariant`) linked by Alignments
(`transforms` A→B, `constrains`, `preserves`, `depends_on`).

**Global passes → Document-level objects:**

| Pass | docmodel output |
|---|---|
| 1 Object Graph | `Object` nodes + `relates` alignments |
| 2 Transformation Graph | `Transformation` nodes + `composes`/`transforms` alignments |
| 3 Invariants | `Invariant` objects spanning ranges they hold over |
| 4 Architecture | one `Architecture` object (inputs/IR/algorithms/outputs in props) |
| 5 Category structures | `CategoryStructure` objects (functor/adjunction/…), only when strongly suggested |
| 6 Cross-domain correspondences | `Correspondence` objects (this ↔ compiler/db/type-theory/…) |
| 7 Implementation view | `ImplementationView` object (modules/pipelines/IRs) |
| 8 Research opportunities | `OpenProblem` objects (missing proofs/algorithms/experiments) |

These are **LLM passes** (recovering adjunctions/IRs is not regex work). Per the
deterministic-first rule they run last, on a docmodel already rich with
CodeBlock/Symbol/VirtualFile objects, and they cite evidence by anchor range.

## Migration path (integrate-easily-later, no disruptive rewrite)

1. **Now — exporter.** `passes/docmodel_export.py`: `to_document(ChatModel) → docmodel
   dict` (meta/streams/objects/alignments), loadable by PDFDRILL's
   `Document.from_dict`. A `docmodel` command writes `<id>.docmodel.json`. This
   makes CHATDRILL docmodel-*integrable today* without rewriting the passes.
2. **Next — docpack.** Reuse PDFDRILL's `docpack.py` to store `<id>.docpack.json`
   (shared compaction format).
3. **Then — native.** Move the passes to build the Document directly (the
   ChatModel becomes a thin typed view over the docmodel), and reuse PDFDRILL's
   projectors. CHATDRILL's projectors (`tiddlers.py`, `markdown.py`) and
   PDFDRILL's then read the *same* Document.
4. **Semantic compiler.** Add the `SemanticUnit` + global-pass processors as
   config-ordered LLM modules over the Document.

The exporter (step 1) is the proof of alignment and the integration seam; the
rest is incremental and never throws away the working deterministic passes.
