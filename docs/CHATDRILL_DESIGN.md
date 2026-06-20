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

## 0.5 The hostile environment & the reverse-time principle

> *"A chat is the most hostile environment for a semantic compiler."*

It is — for two reasons a document never has:

1. **No authority of order.** A PDF is written once, front-to-back, by one mind that
   already knew the conclusion. A chat is groped out *forward in time* by two parties who
   did **not** know the conclusion — full of dead ends, contradictions later retracted,
   and the same artifact rewritten five times.
2. **The value is at the end, not the start.** A document's thesis is up front; a chat's
   payoff (the working code, the answer that stuck, the settled conclusion) is wherever it
   finally clicked — usually late, and usually preceded by broken drafts of the same thing.

**Consequence — read the chat backwards.** A document compiler linearizes front→back.
CHATDRILL's load order *for value extraction* is the inverse: **newest turn first.** The
user does not want a transcript; they want a **results view** — the latest/best version of
each artifact, ready to reuse, with the messy history collapsed behind it. The user's view
is explicitly **not chronological**; it is a reuse surface.

Concretely, the **reverse-time fold** (pass14) walks turns newest→oldest and, per
*artifact identity* (a code file by name/lineage, a question's final answer, a concept's
settled state), keeps the **first occurrence seen = the latest in time** as canonical and
files every earlier occurrence as `superseded` history. Five drafts of `parser.py` across a
chat collapse to one canonical `parser.py` (the last working one) with a four-deep
evolution chain you can still inspect. This inversion *is* the user's reuse view, and it is
why CHATDRILL is not merely "PDFDRILL for chats."

Chronological order is still computed (it is how trajectory, loops and frustration are
derived); reverse order is the **presentation & dedup** principle layered on top.

---

## 1. High-level compiler pipeline

Two stages, both **config-ordered** (a JSON array of `{title, path, type}` descriptors,
exactly like PDFDRILL's `config.json`; `type: "application/python"` enables a pass,
any other value disables it silently). Stage 1 **builds** the `ChatModel`; Stage 2
**projects** artifacts from it.

```
SOURCE (url | chat-id | json | openwebui-db)
   │
   ▼  ── STAGE 0: acquire (optional, never auto-run) ───────────────────────────
pass00_acquire               url           → normalized RawChat  (host adapters; OR
                                              shortcut: read straight from webui.db)
   ▼  ── STAGE 1: chatmodel (build) ───────────────────────────────────────────
pass01_loadAndNormalize      source        → RawChat (message tree)
pass02_linearizeAndBranch    RawChat       → Exchange[] + forgottenBranches  (tree reduced)
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
pass14_reverseTimeFold       all           → ResultsView (newest-first, deduped by identity)
   │
   ▼  ── STAGE 2: chatops (project) ────────────────────────────────────────────
projA_emitModelJson          ChatModel     → <id>.chatmodel.json   (full IR)
projB_emitGraphJson          Hypergraph    → <id>.graph.json + <id>.trajectory.json
projC_emitTiddlers           ChatModel     → <id>.tiddlers.json     (TiddlyWiki import)
projD_emitMetricsReport      metrics       → <id>.report.{md,html}
projE_emitResultsView        ResultsView   → <id>.results.json + code blobs in .chatdrill/code/
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
abandoned branches, **and reduce the tree to the canonical `Exchange[]`** (the Q&A unit
every downstream pass consumes). The `TurnTree` is a transient here; the model keeps
`Exchange[]` + `forgottenBranches`, not the tree. *in→out:* `RawChat → Exchange[] +
forgottenBranches`. *logic:*
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

**pass14_reverseTimeFold** — *purpose:* build the **ResultsView**, the user's reuse
surface (§0.5). *in→out:* `ChatModel → ResultsView`. *logic:*
```
seen = {}                                  # identity → CanonicalArtifact
for turn in reversed(all_turns_by_timestamp):     # NEWEST first
    for art in artifacts_of(turn):         # code files, settled answers, conclusions
        key = identity(art)                # filename | normalized-question | concept key
        if key not in seen:                # first seen == latest in time == canonical
            seen[key] = canonical(art, latestTurnId=turn.id)
        else:
            seen[key].superseded.append(turn.id)   # older draft → evolution chain
unresolved = [q for q in questions if not answered_on_current_path(q)]
emit ResultsView{ artifacts: newest-first(seen.values()), unresolved }
```
Reusability is set from validation signals (user confirmation, "it worked", an `Error`
the next code block resolved). This pass owns nothing new — it re-presents prior passes in
reverse, deduped by identity.

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

// The Q&A PAIR — the CANONICAL internal unit (decided 2026-06-20). pass02 reduces
// the source tree to Exchange[] (the current-path spine) + a forgotten-branch list;
// off-path forks survive only as `regenCount` + ForgottenBranch entries. Everything
// past `query` is OPTIONAL enrichment that varies by source (Appendix C), never assumed.
interface Exchange {
  id: Id; index: number;                    // position on its path
  query: Turn;                              // the user turn (always present)
  answer?: Turn;                            // assistant turn (absent ⇒ unanswered)
  onCurrentPath: boolean;                   // false ⇒ inside a forgotten branch
  // ---- enrichment (source-dependent, frequently partial) ----
  model?: string;                           // answering model: modelName | model_slug | display_model
  askedAt?: number; answeredAt?: number;    // unix seconds; latencyMs = answeredAt − askedAt
  tokensIn?: number; tokensOut?: number;    // USUALLY ABSENT — never a key, only a metric
  mode?: string;                            // perplexity CONCISE/search_focus; chatgpt thinking; …
  citations?: Url[];                        // perplexity blocks / chatgpt content_references
  attachments?: Upload[];                   // files referenced in the pair
  regenCount?: number;                      // sibling answers at this branch point (contested)
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

// ── Reverse-time results view (pass14) — the user's REUSE surface (§0.5) ──────
interface CanonicalArtifact {
  id: Id;
  kind: "CodeFile" | "Answer" | "Conclusion" | "Command" | "Config";
  identity: string;                 // filename | normalized question | concept key
  latestTurnId: Id;                 // where the canonical (latest) version lives
  content: string; lang?: string;
  superseded: Id[];                 // earlier turn ids, newest→oldest = evolution chain
  reusable: boolean;                // confirmed / "worked" / resolved an Error
}
interface ResultsView {             // reverse-chronological, deduped by identity
  artifacts: CanonicalArtifact[];   // newest canonical first
  unresolved: Id[];                 // questions never answered on the current path
  generatedAt: number;
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
  exchanges: Exchange[];                    // CANONICAL spine — Q&A pairs on the current path
  forgottenBranches: ForgottenBranch[];     // off-path subtrees reduced from the source tree
  turns: Turn[];                            // raw turns, kept only as provenance for segments/affect
  states: SemanticState[];
  transitions: StateTransition[];
  loops: Loop[];
  graph: Hypergraph;
  metrics: { perChat: FrustrationMetrics; perModel: Record<string, FrustrationMetrics> };
  insights: InsightCandidate[];
  resultsView: ResultsView;                 // pass14 — the reverse-time reuse surface
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
5. **`<id>.results.json`** — the reverse-time **ResultsView** (§0.5): the canonical
   (latest) version of every code file / answer / conclusion, deduped by identity,
   newest-first, each with its `superseded` evolution chain and a `reusable` flag. This is
   the user's reuse surface. A chat often carries **multiple source files and fragments**;
   each canonical code body is also written as an individual blob under
   `.chatdrill/code/<identity>` and surfaced as a `Code` tiddler (below).

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
    "text": "Frame: debugging the importer. Concepts: {{...}}. Transition in: misunderstanding." },
  { "title": "<chatkey>_Code_parser_py",
    "tags": "chatdrill code canonical reusable [[<chatkey>]] python",
    "fields": { "lang": "python", "latest_turn": "t_9c1", "superseded": "4", "reusable": "yes" },
    "type": "text/vnd.tiddlywiki",
    "text": "Canonical (latest) `parser.py`; 4 earlier drafts collapsed (see `superseded`).\n\n```python\n# … final working code …\n```" }
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

## 8. Storage & state machine (grounded in PDFDRILL's `sidecar.py` + `planner.py`)

Persistence is two artifacts per source — copied verbatim from PDFDRILL:

```
<source>.chatdrill.json     ← SIDECAR: state, the single source of truth
<source>.chatdrill/         ← BLOB DIR: heavy content (chatmodel.json, tiddlers,
                              reports, results.json, code/<file>)
```

**Sidecar shape** (mirrors `class Sidecar`): every command **reads on entry, appends,
writes on exit**.
- `facts: list[str]` — a **cumulative set** of milestones, *not* a linear sequence
  ("states are facts that accumulate"). e.g. `LOADED`, `SEGMENTED`, `STATES_BUILT`,
  `GRAPH_BUILT`, `RESULTS_FOLDED`, `TIDDLERS_BUILT`.
- `evidence: dict` — small structured counts/pointers (`turn_count`, `branch_count`,
  `state_count`, `graph_nodes`, …).
- `layers: dict[name → meta]` — **references** to blobs in the `.chatdrill/` dir
  (relative path + meta), never the blob bytes.
- `transitions: list` — append-only log of `{ts, node, from, to, cost_ms, detail}` for
  every pass that ran. (`log_transition`)
- Helpers to copy: `add_fact/has/remove_fact`, `set_evidence/get_evidence`,
  `set_layer/get_layer`, `write_blob/read_blob`.

**The state machine = declarative prerequisites + done detectors** (mirrors `planner.py`
+ `commands.yaml`, the SSOT). This is exactly the "shallow, layer-by-layer processing
that reruns without repeating work":
- each command declares `requires: [...]` and a `done_when:` spec.
- `done_when` detector kinds (extend for CHATDRILL): `model` (the chatmodel artifact
  exists), `fact:NAME` (the sidecar carries the fact), `file:<name>` (an artifact exists).
- `plan(target)` = the **ordered set of unsatisfied transitive prerequisites,
  deepest-first, then the target itself** (cycle-safe `add()` walk).
- `chatdrill steps <cmd> <source>` prints the chain (done vs would-run);
  `chatdrill <cmd> <source> --ensure` runs the missing **offline** prerequisites first.
- **Idempotency is structural, not incidental:** a pass whose `done_when` already holds is
  skipped; `--force` clears the fact to redo it. A second `chatdrill analyze <id>` does
  nothing if nothing changed.
- **Safety rule carried over:** only offline, idempotent steps are auto-inserted.
  Acquisition / LLM passes (`pass00`, `pass06`, `pass12`) are **never** auto-run — they
  cost money or hit the network. The target the user named always runs; only its missing
  *offline* prerequisites are inserted.

CHATDRILL fact ladder — the rerun-skip checkpoints, one per layer:
```
LOADED → SEGMENTED → ARTIFACTS → ENTITIES → SPEECH_ACTS? → STATES_BUILT
       → TRAJECTORY → LOOPS → METRICS → INSIGHTS? → GRAPH_BUILT
       → RESULTS_FOLDED → TIDDLERS_BUILT
```
(`?` = LLM-assisted; without keys, degrade to a heuristic stub and record a `*_HEURISTIC`
fact so the gap is visible and re-doable when keys appear.)

---

## 9. drillui REPL — grounded in the real three-file pattern

CHATDRILL reuses PDFDRILL's exact `drillui` trio (`tools/drillui_{chat.py,bridge.ts,
term.html}`); only the subprocess it drives changes (`chatdrill`, not `pdfdrill`).

- **`drillui_chat.py` — the brain (Python, stdlib-only, NEVER imports chatdrill).** A
  subprocess client. Per typed line it classifies: quit / help / `commands` /
  `add <source>` / a **known chatdrill command name (or `!cmd`)** → run on the open chat /
  **anything else** → a grounded question. For a question it: `chatdrill retrieve <source>
  "<q>" --json` (top-k grounded units + a citing prompt) → `claude -p … --output-format
  json` → `chatdrill chatlog …` to store the Q&A back as a graph node. A rolling ~2000-char
  history gives continuity. The command table is loaded once from `chatdrill skill --json`,
  so the REPL auto-knows every subcommand and whether to auto-fill the source positional.
  Works standalone in a terminal; no browser required.
- **`drillui_bridge.ts` — the bridge (Bun, plumbing only).** A browser can't spawn a
  process, so the bridge spawns **one brain per WebSocket** and pipes stdin/stdout. It
  knows a turn finished by watching stdout for the REPL's exact prompt tail `"\n? "` (with
  a ~20 ms debounce, so an answer that itself contains `"\n? "` isn't mistaken for the
  prompt), then emits `{output}` + `{ready}`. It also serves the HTML page, serves blob
  artifacts at `/artifact?path=…` **under-root only (no path traversal)**, and can open a
  file/URL in the host browser at `/open`. No business logic lives here.
- **`drillui_term.html` — the UI (browser, xterm.js).** Terminal with bash-style editing +
  history, a retrieval rail (cited unit ids), an Outputs panel. **The browser decides local
  commands first** (`open <url|file>`, `lhelp`, `^L`) and only forwards the rest to Python —
  so `open <url>` opens a window and is *never* an LLM call.

The web version *is* the terminal version over a socket — zero logic duplicated. That
split is the whole point: the terminal REPL is the product; the web page is a transport.

---

## 10. Acquisition layer (`pass00`) — getting the chat in the first place

The "normal" entry is a **single chat URL**, and turning that URL into a clean transcript
is itself adversarial:
- **Chinese providers** (DeepSeek, Qwen, Kimi, …) typically expose a chat as a **JSON
  export/endpoint** — fetch and you're essentially done.
- **Western providers** (OpenAI, Claude, Gemini, …) hide the transcript behind auth,
  lazy-loaded virtual scroll, and shifting DOM — so acquisition needs a **library of
  host-specific tricks**: per-host adapters, a headless/automated browser, and where
  necessary a **browser extension** that scrapes the live DOM and emits the normalized tree.

This layer is **pluggable and outside the compiler core**: `src/adapters/<host>.py` (+ an
optional extension under `tools/`), selected by URL host / schema sniff, all emitting one
normalized `RawChat`. The compiler never sees provider HTML.

**Sanctioned shortcut for the semantic-compiler phase:** we are focused on the *compiler*,
not on scraping. So bypass acquisition entirely and read from **`~/myopenwebui/webui.db`**
(`OPENWEBUI_DB` in `.env`): `chatdrill load --db <chat-id>` pulls the already-normalized
tree straight out of SQLite. `pass00_acquire` stays optional and never auto-run — the
corpus is already in hand.

---

## 11. The semantic compiling algorithm at the Exchange layer

This is the layer the project now focuses on: **assume acquisition is solved** — adapters
have delivered a normalized **`Exchange[]`** (a chronological list of Q&A pairs, each with
the optional enrichment above) plus the branch structure. Everything here runs *after* we
have the chat in hand. It is passes 05–14 restated concretely in Exchange terms, with each
piece of "additional data" wired into the exact place it earns its keep.

**Input contract.** `Exchange[]` in chronological order. Each Exchange = `(query, answer?,
model?, askedAt?, answeredAt?, tokens?, citations?, attachments?, mode?, regenCount?)`.
Only `query` is guaranteed; **every consumer degrades gracefully** when a field is missing
(Appendix C shows how often each is, in the real corpora).

**Step 1 — per-Exchange features (cheap, deterministic, no LLM).** For each Exchange
compute the columns the rest of the algorithm reads:
- `queryAct` — speech-act of the *question* (question / correction / instruction / …).
- `affect` — `?`/`!`/caps/ellipsis/single-word markers (§3) on the query.
- `answered` (is there an answer turn), `answerLen`, code-density, citation-count.
- `latencyMs = answeredAt − askedAt` (when both present); `tokensOut` (when present).

**Step 2 — link Exchanges into the trajectory.** Walk consecutive pairs `E_i → E_{i+1}`
and type the edge from `E_{i+1}`'s *query act* + affect:
- query corrects/contradicts `E_i`'s answer ⇒ `correction` (+ a `contradicts` graph edge);
- query re-asks `E_i` (high similarity) ⇒ `loop`;
- query narrows it ("ok but how do I…") ⇒ `clarification`;
- query confirms and moves on ⇒ `resolution`; new entity-set ⇒ `sidetrack`.
The **extra data sharpens the edge type**: a **model switch** to a stronger model between
`E_i` and `E_{i+1}` implies `E_i`'s answer failed (escalation); a long **`latencyMs`**
before a short, high-affect query is a frustration cue; **`regenCount > 1`** flags a
contested answer.

**Step 3 — segment into semantic states (frames).** Coalesce consecutive Exchanges that
share a goal / entity-set into a `SemanticState`; boundary = entity-Jaccard drop or a new
top-level question. Roll affect / novelty / certainty up to the state.

**Step 4 — loops, metrics, insights** (§3/§4) read straight off the Exchange table:
loop detection on query-similarity; frustration metrics from affect + latency +
model-switches; insight scoring favours answers carrying `citations` / runnable code that
a later Exchange confirmed.

**Step 5 — reverse-time fold (pass14).** Walk Exchanges newest→oldest; per artifact
identity keep the latest as canonical, older as `superseded`. The canonical Exchange's
`model` + `answeredAt` become **provenance** on the result ("final answer:
gpt-5-1-thinking, 2026-02-10").

**The framing in one line:** the additional data is not decoration — *each field has one
job.* times → latency/frustration + reverse-time ordering; model → escalation signal +
per-model fingerprint + result provenance; citations → insight `references` + `Url` nodes;
mode → expected-verbosity baseline; regenCount → contested-answer weight; tokens →
verbosity/cost metrics *when present*. Where a field is absent, its consumer simply omits
that signal — the compiler never blocks on missing enrichment.

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
| `.drill.json` facts + `done_when`/`--ensure` planner | same | idempotent layer-by-layer rerun; skip satisfied facts |
| *(no document analog — a doc is read front→back)* | `pass14` reverse-time fold → `ResultsView` | a chat's value is latest-first; dedup artifacts by identity |
| `retrieve` + `chatlog` grounding | same | drillui brain stays a subprocess client |

## Appendix B — open questions for the implementer

1. Embedding model for novelty/loop similarity (local `all-MiniLM` vs API)? Affects
   offline-safety of pass10/pass12.
2. Frame-boundary threshold τ for pass08 — tune on a labeled handful of chats.
3. Corpus identity resolution: how aggressively to merge near-synonym concepts.
4. Timestamp units across providers (OpenWebUI is seconds; some exports ms) — normalize
   in the adapter, not the compiler.

## Appendix C — Real input survey (what actually arrives)

A scan of the on-disk corpora (2026-06-20) — this is the evidence the `Exchange` contract
is built from, not a guess:

| Source | Store | Native unit | Structure | Time | Model | Tokens | Notable extras |
|---|---|---|---|---|---|---|---|
| **OpenWebUI** | `~/myopenwebui/webui.db` `chat` JSON (1327) | message | **tree** (`history.messages` by id, `parentId`/`childrenIds`, `currentId`) | `timestamp` (s) per msg | `modelName`,`model`,`modelIdx`,`models[]` | ✗ (absent here) | `done`, branch siblings |
| **Perplexity JSON** | `oldstuff/perplexport/perplexports/*.json` | **entry = Q&A block** | **flat `entries[]`** per thread | `updated_datetime`, `entry_updated_datetime` (ISO) | `display_model`,`user_selected_model`,`gpt4` | ✗ | `query_str`, `blocks[]`(intended_usage + markdown), `mode`(CONCISE), `search_focus`, `related_queries`, `social_info` |
| **Perplexity MD** | `~/perplexport/perplexports/*.md` (689) | thread | markdown prose | ✗ | ✗ | ✗ | first line = source URL |
| **Perplexity URLs** | `~/perplexport/urllist.txt` (688) | url | one per line | ✗ | ✗ | ✗ | re-fetch handles |
| **ChatGPT export** | `~/Downloads/conversations.old.json` (625) | message | **tree** (`mapping`, parent/children) | `create_time`/`update_time` (s, float) | `metadata.model_slug` (gpt-4o … gpt-5-2-thinking) | sometimes via `finish_details` | citations, attachments, `content_references`, canvas, dalle, `is_error` |
| **ChatGPT partial** | `~/Downloads/conversations*.json` (381/…) | message | `mapping` tree, many **null** message nodes | partial | partial | ✗ | older/sparser dumps |

Findings baked into the design:
1. **Only two shapes exist:** a *tree* (OpenWebUI, ChatGPT) or a *flat Q&A list*
   (Perplexity). Adapters normalize both to `Exchange[]` + branch info; the compiler sees
   only the normalized form.
2. **Tokens are usually absent.** `tokensIn/Out` is optional enrichment, never required —
   token-cost metrics are best-effort.
3. **Model + timestamps are almost always present**, so latency, model-escalation,
   reverse-time ordering and per-model fingerprints are reliably computable.
4. **Citations/attachments live in the richest sources** (Perplexity `blocks`, ChatGPT
   `metadata`) and feed insight `references` + `Url`/`Upload` nodes.
5. The same chat may exist as **JSON, markdown, and a URL** at once — the markdown/URL
   forms are low-fidelity fallbacks when the JSON isn't available.
```
