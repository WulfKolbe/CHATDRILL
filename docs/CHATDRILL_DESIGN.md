# CHATDRILL — Semantic Compiler for Chat Histories (Design RFC)

**Status:** Draft v0.1 · **Audience:** implementers · **Scope:** architecture, passes, data
models, metrics. Not the final implementation.

CHATDRILL converts chaotic multi-turn chat histories into a structured, queryable
**hypergraph** plus a **trajectory graph**, exportable to TiddlyWiki. It is the
conversational sibling of **PDFDRILL** and deliberately mirrors its proven shape:

- a **unified model** (`chatmodel`, analog of PDFDRILL's `docmodel`) built by a
  **config-ordered pass pipeline**;
- a **two-stage** flow — *build the model* (mutating passes) then *project artifacts*
  (projectors: JSON, TiddlyWiki, metrics report);
- a flat **prose-returning CLI** (`chatdrill <cmd> <source>`) with a `.chatdrill.json`
  **sidecar** recording state-machine facts/transitions;
- a **drillui** REPL: Python brain + Bun WebSocket bridge + xterm.js browser UI.

The governing metaphor: **a chat is not a document, it is a trajectory through semantic
space** — Brownian motion with misunderstandings, loops, frustration spikes and
abandoned branches. We extract not *what was said* but *how the semantic state evolved*.

---

## 0. Grounding: the real input shape

The primary corpus is OpenWebUI (`~/myopenwebui/webui.db`, 1327 chats). The `chat`
table stores a JSON blob per chat. Verified structure:

```jsonc
{
  "id": "...", "title": "...",
  "models": ["gpt-3.5-turbo", "gpt-4o"],   // model pool for the chat
  "system": "...", "params": {...},
  "timestamp": 1710000000,
  "tags": [...], "files": [...],
  "messages": [ /* flat list, current-path order */ ],
  "history": {
     "currentId": "<leaf message id>",
     "messages": {                          // id -> message, the SOURCE OF TRUTH
        "<id>": {
           "id": "...", "parentId": "<id|null>", "childrenIds": ["..."],
           "role": "user" | "assistant",
           "content": "...",
           "timestamp": 1710000000,         // int (seconds)
           "models": [...], "modelName": "gpt-4o", "modelIdx": 0
        }
     }
  }
}
```

**Critical fact: messages form a TREE, not a list.** `history.messages` is keyed by id;
`parentId`/`childrenIds` define the tree; `history.currentId` points at the leaf of the
*currently visible* path. This is not incidental — it is the single most important
structural signal CHATDRILL exploits:

- The **current path** (root → `currentId`) is the "official" conversation.
- Any node with **>1 child** is a **branch point** (regen, edit, "try again").
- Subtrees not on the current path are **forgotten branches** — abandoned semantic
  side-quests. They are first-class evidence, not noise to discard.

Other providers (raw ChatGPT/Claude exports) are normalized to this same tree by
**adapters** that live *outside* the compiler. The compiler always receives a
normalized `RawChat` (§2).

---

## 1. High-level compiler pipeline

Two stages, both **config-ordered** (a JSON array of `{title, path, type}` descriptors,
exactly like PDFDRILL's `config.json`; `type: "application/python"` enables a pass,
any other value disables it silently). Stage 1 **builds** the `ChatModel`; Stage 2
**projects** artifacts from it.

```
SOURCE (url | chat-id | json | openwebui-db)
   │
   ▼  ── STAGE 1: chatmodel (build) ───────────────────────────────────────────
pass01_loadAndNormalize      source        → RawChat (message tree)
pass02_linearizeAndBranch    RawChat       → TurnTree (current path + branches[])
pass03_segmentContent        TurnTree      → Turns w/ segments (prose|code|url|quote)
pass04_detectArtifacts       segments      → CodeBlock / Url / Upload / Error nodes
pass05_extractEntities       turns         → Entity mentions (concepts, papers, libs…)
pass06_classifySpeechActs    turns         → SpeechAct per turn (LLM-assisted)
pass07_scoreAffect           turns         → AffectMarkers (frustration/confusion side-ch.)
pass08_buildSemanticStates   turns         → SemanticState[] (clustered frames)
pass09_buildTrajectory       states        → StateTransition[] (typed edges)
pass10_detectLoops           trajectory    → Loop[] (repeated Q/A cycles)
pass11_computeMetrics        all           → FrustrationMetrics + ChannelMetrics
pass12_scoreInsights         all           → InsightCandidate[] (novelty/consistency/refs)
pass13_buildHypergraph       all           → Hypergraph (nodes + hyperedges)
   │
   ▼  ── STAGE 2: chatops (project) ────────────────────────────────────────────
projA_emitModelJson          ChatModel     → <id>.chatmodel.json   (full IR)
projB_emitGraphJson          Hypergraph    → <id>.graph.json + <id>.trajectory.json
projC_emitTiddlers           ChatModel     → <id>.tiddlers.json     (TiddlyWiki import)
projD_emitMetricsReport      metrics       → <id>.report.{md,html}
```

Design rules carried over from PDFDRILL:

- **Idempotent, resumable.** Each pass records a transition in the sidecar
  (`from`→`to`, `cost_ms`, `detail`). Re-running skips satisfied passes unless `--force`.
- **Offline-safe by construction.** Passes that need an LLM (06, 12) are the *only* ones
  requiring keys. Without keys they degrade to heuristic stubs and mark the fact in the
  sidecar; the model still builds. Never auto-run network passes.
- **Provenance everywhere.** Every derived field carries `provenance` ∈
  {`heuristic`, `regex`, `llm`, `manual`} and an optional `score`, mirroring PDFDRILL's
  `Realization.provenance`.

### Pass details

Each pass below: *purpose · in→out · core logic*. Types defined in §2.

**pass01_loadAndNormalize** — *purpose:* resolve a `source` to a `RawChat`.
*in→out:* `source:str → RawChat`. *logic:*
```
if source is openwebui chat-id or db row:    parse history.messages tree directly
elif source is a URL:                         hand to provider adapter → tree
elif source is a .json file:                  detect schema, adapter → tree
validate: every parentId resolves; exactly one root (parentId==null);
          currentId exists. Repair orphans by attaching to nearest ancestor.
```

**pass02_linearizeAndBranch** — *purpose:* split the tree into the canonical path plus
abandoned branches. *in→out:* `RawChat → TurnTree`. *logic:*
```
current = path(root → history.currentId)         # ordered Turns
branches = []
for node with len(childrenIds) > 1:              # branch point
    for child not on current path:
        branches.append(subtree(child))          # a ForgottenBranch
emit TurnTree{ current, branches, branch_points }
```
This single pass is what makes CHATDRILL *not* a document compiler: forgotten branches
become measurable ("3 abandoned threads, 1 never resolved").

**pass03_segmentContent** — split each turn's `content` into typed `Segment`s
(prose / fenced-code / inline-code / blockquote / url / list). Markdown-aware; never
treat a code fence as prose. *in→out:* `TurnTree → Turn.segments[]`.

**pass04_detectArtifacts** — promote segments to graph-ready nodes: `CodeBlock`
(language, hash, line count), `Url`, `Upload` (from `files`), `Error` (stack
traces / tracebacks / `Error:` lines via regex). *in→out:* `segments → ArtifactNode[]`.

**pass05_extractEntities** — named entities & concepts: libraries, papers (arXiv ids,
DOIs), commands, file paths, domain terms. Always-on regex extractors (URL/DOI/arXiv/
path/identifier) like PDFDRILL's `features/`; optional NLP/LLM enrichment. *out:*
`EntityMention[]` linked to the turn range that surfaced them.

**pass06_classifySpeechActs** — per turn, classify intent (§2 `SpeechAct.intent`).
LLM-assisted with a strict enum; heuristic fallback uses cue lexicons ("actually",
"no,", "I meant", "thanks", "sorry", "?"). *Batch* turns to control cost. *out:*
`SpeechAct` per turn with `confidence` + `provenance`.

**pass07_scoreAffect** — purely lexical side-channel (no LLM): per-turn `AffectMarkers`
(`?`/`!`/ellipsis density, caps ratio, single-word replies, profanity, "still not
working"). Cheap, deterministic, reproducible. *out:* `AffectMarkers` per turn.

**pass08_buildSemanticStates** — cluster consecutive turns into stable **frames**: a
contiguous run sharing a topic/goal. Boundary = topic shift (entity-set Jaccard drop),
speech-act reset (new top-level question), or explicit "new topic". Each `SemanticState`
summarizes concepts-in-play, certainty, open questions. *in→out:* `turns → SemanticState[]`.

**pass09_buildTrajectory** — connect consecutive states with typed `StateTransition`s
(`misunderstanding`, `correction`, `clarification`, `example`, `synthesis`,
`sidetrack`, `loop`, `frustration_spike`, `resolution`). Cause inferred from the
speech-acts + affect at the boundary. *out:* directed trajectory graph.

**pass10_detectLoops** — find cycles: near-duplicate Q/A pairs (embedding or shingled
cosine ≥ τ) and "we already tried that" returns. Emits `Loop{members[], period,
resolved}`. *out:* `Loop[]`, and back-annotates transitions as `loop`.

**pass11_computeMetrics** — aggregate `FrustrationMetrics` and `ChannelMetrics`
(signal/noise, novelty curve, assistant-pathology counts) per chat and per assistant
model (§3). Pure functions over prior passes. *out:* metrics block.

**pass12_scoreInsights** — score `InsightCandidate`s (§4): novelty × consistency ×
references. LLM-assisted to judge "is this a genuine insight vs. boilerplate"; heuristic
fallback uses reference presence + novelty + non-repetition. *out:* ranked insights.

**pass13_buildHypergraph** — fold everything into one `Hypergraph`: nodes (Concept,
Question, Url, CodeBlock, Error, Hypothesis, Insight, Model) and hyperedges
(supports, contradicts, corrects, extends, references, answers, raised_by). *out:*
`Hypergraph`.

---

## 2. Core data models

TypeScript-style for clarity; implement in Python with Pydantic v2 (PDFDRILL's choice).
Every derived object carries `provenance` and optional `score`.

```typescript
type Provenance = "heuristic" | "regex" | "llm" | "manual";
type Id = string;                 // stable, e.g. "t_3f9a", "st_0007", "cn_http"

interface RawChat {
  id: Id; title: string; source: string;     // db path | url | file
  models: string[];                            // model pool
  createdAt: number;                           // unix seconds
  tree: Record<Id, RawMessage>;                // history.messages
  currentId: Id;                               // leaf of canonical path
  files?: Upload[];
}
interface RawMessage {
  id: Id; parentId: Id | null; childrenIds: Id[];
  role: "user" | "assistant" | "system";
  content: string; timestamp: number;
  modelName?: string; modelIdx?: number;
}

interface Turn {
  id: Id; role: "user" | "assistant" | "system";
  index: number;                    // position on its path
  modelName?: string;               // assistant turns only
  content: string; timestamp: number;
  segments: Segment[];              // pass03
  onCurrentPath: boolean;           // false ⇒ lives in a forgotten branch
  speechAct?: SpeechAct;            // pass06
  affect?: AffectMarkers;           // pass07
}
interface Segment {
  kind: "prose" | "code" | "inline_code" | "quote" | "url" | "list";
  text: string; lang?: string;      // lang for code
}

interface TurnTree {
  current: Turn[];                          // root → currentId
  branches: ForgottenBranch[];             // abandoned subtrees
  branchPoints: Id[];                       // turns with >1 child
}
interface ForgottenBranch {
  rootTurnId: Id; turns: Turn[];
  resolved: boolean;                        // did the user ever return to its topic?
  reason?: "regenerate" | "edit" | "manual_switch";
}

interface SpeechAct {
  intent:
    | "question" | "clarification" | "statement" | "instruction"
    | "correction" | "confirmation" | "apology" | "hallucination"
    | "example" | "sidetrack" | "frustration" | "gratitude" | "abandon";
  target?: Id;                              // turn this responds to / corrects
  confidence: number; provenance: Provenance;
}

interface AffectMarkers {                   // pass07 — deterministic, no LLM
  qDensity: number; bangDensity: number;    // '?' / '!' per 100 chars
  ellipsis: number; capsRatio: number;
  singleWordReply: boolean;                 // "ok", "NO", "no.", "stop"
  repetitionHint: boolean;                  // near-dup of an earlier user turn
}

interface SemanticState {                   // pass08 — a "frame"
  id: Id; turnRange: [Id, Id];              // first..last turn in the frame
  concepts: Id[];                           // Concept node ids in play
  openQuestions: Id[];                      // Question node ids unanswered here
  certainty: number;                        // 0..1, how settled the topic is
  novelty: number;                          // 0..1 vs. prior states
  frustration: number;                      // 0..1 rolled up from AffectMarkers
  summary: string;                          // one line, LLM or heuristic
}
interface StateTransition {                 // pass09 — trajectory edge
  from: Id; to: Id;                          // SemanticState ids
  cause:
    | "misunderstanding" | "correction" | "clarification" | "example"
    | "synthesis" | "sidetrack" | "loop" | "frustration_spike" | "resolution";
  evidenceTurns: Id[]; confidence: number; provenance: Provenance;
}
interface Loop {                            // pass10
  members: Id[];                            // turn ids forming the cycle
  period: number;                           // turns between repeats
  resolved: boolean;
}

// ── Hypergraph (pass13) ──────────────────────────────────────────────────────
type NodeKind =
  | "Concept" | "Question" | "Url" | "CodeBlock" | "Error"
  | "Hypothesis" | "Insight" | "Upload" | "Model";
interface HyperNode {
  id: Id; kind: NodeKind; label: string;
  props: Record<string, unknown>;           // kind-specific
  evidence: Id[];                            // turn ids that support existence
  provenance: Provenance; score?: number;
}
type EdgeRel =
  | "supports" | "contradicts" | "corrects" | "extends"
  | "references" | "answers" | "raised_by" | "produced_by" | "co_occurs";
interface HyperEdge {
  id: Id; rel: EdgeRel;
  members: Id[];                            // ≥2 node ids (true hyperedge)
  evidence: Id[]; confidence: number;
}
interface Hypergraph { nodes: HyperNode[]; edges: HyperEdge[]; }

interface InsightCandidate {                // §4
  id: Id; text: string; turnId: Id;
  novelty: number; consistency: number; references: number;
  score: number;                            // combined (see §4)
}

interface FrustrationMetrics {              // §3 — per chat AND per model
  interruptionRate: number; loopCount: number;
  qDensity: number; bangDensity: number;
  singleWordReplyRate: number;
  empathyBoilerplateCount: number;
  signalToNoise: number;                    // technical nouns / boilerplate phrases
}

// ── the unified model that flows through every pass ──────────────────────────
interface ChatModel {
  meta: { id: Id; title: string; source: string; models: string[]; createdAt: number };
  turns: Turn[];                            // ALL turns (current + branches)
  tree: TurnTree;
  states: SemanticState[];
  transitions: StateTransition[];
  loops: Loop[];
  graph: Hypergraph;
  metrics: { perChat: FrustrationMetrics; perModel: Record<string, FrustrationMetrics> };
  insights: InsightCandidate[];
}
```

The sidecar (`<id>.chatdrill.json`, PDFDRILL's `.drill.json` analog) carries
*state*, not content:

```jsonc
{
  "chat_id": "...", "chatdrill_version": "0.1.0",
  "facts": ["LOADED", "SEGMENTED", "STATES_BUILT", "GRAPH_BUILT", "TIDDLERS_BUILT"],
  "evidence": { "turn_count": 16, "branch_count": 3, "state_count": 5,
                "insight_count": 4, "graph_nodes": 31, "graph_edges": 47 },
  "transitions": [
    { "ts": "2026-06-20T10:00:00Z", "node": "loadAndNormalize",
      "from": "INIT", "to": "LOADED", "cost_ms": 12.4, "detail": "openwebui:<id>" }
  ]
}
```

---

## 3. Frustration & personality fingerprinting (the "ADHS" side)

All metrics are **composable pure functions** over the model. Two scopes: **per chat**
and **per assistant model** (aggregate over all that model's turns across the corpus).

| Metric | Definition | Needs |
|---|---|---|
| **Interruption rate** | user turns whose timestamp − prev assistant timestamp < θ (assistant likely still "typing"), or user edits before an assistant reply exists | timestamps, tree |
| **Loop counter** | `len(loops)` and Σ members; share of turns inside a loop | pass10 |
| **`?`/`!` density** | marks per 100 chars, user vs assistant separately | pass07 |
| **Ellipsis / caps** | `…`/`...` count; ALL-CAPS word ratio | pass07 |
| **Single-word reply rate** | fraction of user turns ≤ 2 tokens ("ok","NO","stop","again") | pass07 |
| **Signal/noise** | technical-noun count ÷ empathy-boilerplate phrase count | pass05 + lexicon |
| **Assistant pathology** | count of canned phrases ("I understand your frustration", "I apologize for the confusion", "You're absolutely right") ÷ info density | lexicon |
| **Self-correction rate** | assistant turns with `intent ∈ {correction}` referencing own prior turn | pass06 |
| **Hallucination rate** | assistant turns flagged `intent=hallucination` or contradicted later | pass06 + contradiction edges |
| **Verbosity** | mean assistant tokens per turn | tokenizer |
| **Hedging frequency** | "might", "possibly", "I think", "it depends" per 100 tokens | lexicon |
| **Code/citation density** | code chars ÷ total; reference nodes ÷ turn | pass04/05 |

**Model personality fingerprint.** For each `modelName`, build a vector
`v = [apologyFreq, verbosity, hallucinationRate, selfCorrectionRate, codeDensity,
citationDensity, hedgingFreq, empathyBoilerplate, signalToNoise]`, z-scored across the
corpus. This vector is the model's "psychological fingerprint" and feeds §7's UMAP.

Aggregation: per-chat metrics are written into `ChatModel.metrics.perChat`; a separate
`chatdrill corpus-fingerprint` command folds all chats into
`ChatModel.metrics.perModel` and a corpus-level `models.fingerprint.json`.

---

## 4. Insight extraction & "gold" recovery

Goal: separate the ~5% signal from ~95% noise. Each candidate statement (assistant
claims, user conclusions, resolved answers) gets three sub-scores in `[0,1]`:

- **Novelty `N`** — semantic distance from everything said earlier in the chat (and,
  in corpus mode, from the global KB). New ≠ repeated boilerplate.
- **Consistency `C`** — was it validated/agreed (user confirmation, no later
  contradiction edge, reproduced in code that "worked")? Contradicted ⇒ `C` low.
- **References `R`** — backed by URLs / arXiv / DOI / runnable code / errors-resolved.

```
score = wN·N + wC·C + wR·R            # default wN=0.4, wC=0.35, wR=0.25
candidate is an Insight if score ≥ τ_insight (default 0.6)
```

Promotion to first-class graph nodes:

- top-scoring candidates → **`Insight`** nodes, `references` edges to their `Url`/`CodeBlock`/`Error`.
- any `Question` never `answers`-ed on the current path → **unresolved question** node
  (high query value: "show me all unresolved questions about X").
- any `CodeBlock` that follows an `Error` it resolves → **`produced_by`** + `corrects`
  edges (recovered working snippet).

Unresolved questions and forgotten-branch topics are deliberately preserved — they are
the highest-value query targets ("what did we never finish?").

---

## 5. Output format & integration

Stage-2 projectors write into `<source>.chatdrill/` (PDFDRILL's `<name>.drill/`
convention):

1. **`<id>.chatmodel.json`** — the full IR (§2 `ChatModel`). Lossless; everything else
   derives from it.
2. **`<id>.graph.json` + `<id>.trajectory.json`** — hypergraph (nodes/edges) and the
   state-transition graph, for programmatic queries and visualization.
3. **`<id>.tiddlers.json`** — a TiddlyWiki import file (array of tiddlers). One tiddler
   per first-class node, plus per-state and per-insight tiddlers. Importable straight
   into the project's TiddlyWiki (served from the repo root) or OpenWebUI KB.
4. **`<id>.report.{md,html}`** — human-readable metrics + trajectory narrative.

**Tiddler schema** (mirrors PDFDRILL's `TiddlyWikiProjector`, `KEY_<type>_<id>` naming):

```jsonc
[
  { "title": "<chatkey>_Insight_0007",
    "tags": "chatdrill insight [[<chatkey>]] semantic-compression",
    "fields": { "score": "0.81", "novelty": "0.9", "turn": "t_3f9a" },
    "type": "text/vnd.tiddlywiki",
    "text": "Brownian-trajectory framing of chats…\n\nReferences: {{<chatkey>_Url_http}}" },
  { "title": "<chatkey>_Question_0002",
    "tags": "chatdrill question unresolved [[<chatkey>]]",
    "fields": { "status": "unresolved" },
    "text": "How to measure semantic compression ratio?" },
  { "title": "<chatkey>_State_0003",
    "tags": "chatdrill state [[<chatkey>]]",
    "fields": { "certainty": "0.4", "frustration": "0.7" },
    "text": "Frame: debugging the importer. Concepts: {{...}}. Transition in: misunderstanding." }
]
```

Cross-references use TiddlyWiki transclusion `{{title}}` / links `[[title]]`, so the
graph is browsable. Tags (`unresolved`, `insight`, `loop`, per-chat key, per-concept)
make the existing TiddlyWiki the query engine — matching the project's plan to
*control the program via tags* (CLAUDE.md note on tag-driven agent swarms).

**Querying.** Three back-ends, increasing power:
- **Tags/filters in TiddlyWiki** — `[tag[unresolved]tag[semantic-compression]]`.
- **`chatdrill query` over `graph.json`** — graph queries: "trajectory where CSP →
  Insight", "all `contradicts` edges for model gpt-4o".
- **Corpus KB** — merge all `graph.json` into one global hypergraph (node identity by
  normalized concept label / strong keys like arXiv-id), enabling cross-chat queries.

---

## 6. Implementation notes

- **CLI, prose-returning, flat** (PDFDRILL pattern). `HANDLERS` dict, one source of
  truth in `.claude/skills/chatdrill/commands.yaml`:
  ```
  chatdrill analyze <source>     # run full pipeline → all artifacts
  chatdrill load <source>        # stage-1 pass01 only; show tree summary
  chatdrill states <source>      # build + print semantic states
  chatdrill graph <source>       # build + emit graph.json
  chatdrill tiddlers <source>    # emit tiddlers.json
  chatdrill metrics <source>     # frustration/channel metrics
  chatdrill query <source> '<q>' # query the built graph
  chatdrill corpus-build         # merge all openwebui chats → global KB
  chatdrill corpus-fingerprint   # per-model personality vectors
  chatdrill doctor               # env/key/dep check
  ```
  `<source>` resolves like PDFDRILL's `_pdf()`: openwebui chat-id, `--db` row, a URL
  (→ adapter), or a local `.json`. `--ensure` auto-runs offline prerequisites;
  network/LLM passes are never auto-run.
- **Adapters are out of scope for the compiler.** It always receives a normalized
  `RawChat`. Provider-specific HTML/JSON parsing lives in `src/adapters/` and is
  selected by URL host / schema sniff.
- **Runtime:** Python 3 + Pydantic v2 on the live path (keeps the Claude.ai web path
  dependency-light, like PDFDRILL); Bun only for the drillui bridge.
- **drillui REPL** (PDFDRILL's three-piece pattern):
  - `tools/drillui_chat.py` — Python brain: runs `chatdrill retrieve/query` for grounded
    context, calls the LLM, logs Q&A back. Terminal-native.
  - `tools/drillui_bridge.ts` — Bun: spawns one brain per WebSocket, serves the UI and
    `<id>.chatdrill/` artifacts. Port from `CHATDRILL_BRIDGE_PORT`.
  - `tools/drillui_term.html` — xterm.js terminal + retrieval rail + outputs panel.
  The terminal version is fully usable alone; the web version *is* the terminal version
  over a socket — no logic duplicated.
- **Secrets:** `.env` (gitignored) / env vars. Offline passes need zero keys; only
  pass06 and pass12 consume `ANTHROPIC_API_KEY` etc. (see `.env.example`).
- **Scaling to the whole corpus:** `analyze` is per-chat and idempotent (sidecar-gated),
  so batch = `for id in chats: chatdrill analyze id`. `corpus-build` merges the
  per-chat graphs into one KB by entity-identity resolution (normalized concept labels;
  strong keys: arXiv-id, DOI, URL). Per-model fingerprints aggregate across the batch.

---

## 7. (Optional) LLM personality UMAP

Given the corpus, each `modelName` has a fingerprint vector `v` (§3). Stack into a matrix
`M` (models × features), z-score columns, then project:

```
emb = UMAP(n_neighbors=8, min_dist=0.1, metric="euclidean").fit_transform(M)
# scatter emb[:,0] vs emb[:,1], label points by model
```

Expected clustering (hypothesis to validate, not assert): verbose/hedging/apologetic
models separate from terse/high-code-density ones (e.g. "Claude = verbose perfectionist,
DeepSeek = terse engineer"). PCA gives a cheaper linear first look; UMAP reveals
non-linear neighborhoods. Ship as `chatdrill corpus-fingerprint --umap`, writing
`models.umap.json` + an HTML scatter. Strictly a side quest — not on the core path.

---

## Appendix A — mapping to PDFDRILL

| PDFDRILL | CHATDRILL | Note |
|---|---|---|
| `docmodel` (`Document`/`DocObject`/`Stream`) | `chatmodel` (`ChatModel`/`Turn`/`TurnTree`) | unified IR built by config-ordered passes |
| `docops` mutators/projectors | stage-2 projectors (`projA..projD`) | model → artifacts |
| `config.json` procOrder | stage-1/stage-2 pass config | enable via `type`, order via array |
| `.drill.json` sidecar | `.chatdrill.json` sidecar | facts + transitions, idempotent |
| `features/` regex extractors | pass05 entity extractors | always-on, lazy optional deps |
| `semantic/` graph + identity | pass13 Hypergraph + corpus-build | evidence-first, strong-key identity |
| `TiddlyWikiProjector` | projC tiddlers | `KEY_<type>_<id>`, transclusion |
| `drillui_{chat.py,bridge.ts,term.html}` | same three pieces | terminal brain + Bun bridge + xterm |
| flat prose CLI + `commands.yaml` SSOT | same | `chatdrill <cmd> <source>` |

## Appendix B — open questions for the implementer

1. Embedding model for novelty/loop similarity (local `all-MiniLM` vs API)? Affects
   offline-safety of pass10/pass12.
2. Frame-boundary threshold τ for pass08 — tune on a labeled handful of chats.
3. Corpus identity resolution: how aggressively to merge near-synonym concepts.
4. Timestamp units across providers (OpenWebUI is seconds; some exports ms) — normalize
   in the adapter, not the compiler.
```
