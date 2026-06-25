# Perplexity → CHATDRILL

Perplexity has **no official bulk export** and its pages are JS-rendered behind
bot protection. Extraction is a **browser-console** job in your *logged-in*
Perplexity tab, in two phases:

- **Phase A — index:** capture every thread (slug + url + metadata) from the
  library API. The verbatim, working script is below.
- **Phase B — bodies:** fetch each thread's full `entries[]` (the actual Q&A
  content) into a **bodies dump**, which is what CHATDRILL ingests.

> Run these in **your own browser** — your login/cookies stay local. Never paste
> cookies anywhere.

## Phase A — capture the library index (verbatim)

Paste this into the console at `https://www.perplexity.ai/library?tab=threads`.
It POSTs to `/rest/thread/list_ask_threads` (`{limit, offset}`), paginates the
whole library, dedupes, and downloads `perplexity-library-<N>.html` +
`perplexity-library-<N>.json` (and leaves the array in `window.__pplxThreads`):

```js
(async () => {
  const LIMIT = 100, sleep = ms => new Promise(r => setTimeout(r, ms));
  const all = new Map(); let offset = 0, page = 0;
  while (true) {
    const res = await fetch("https://www.perplexity.ai/rest/thread/list_ask_threads", {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limit: LIMIT, offset })
    });
    if (!res.ok) { console.error("HTTP", res.status, await res.text()); break; }
    const arr = await res.json().then(d => Array.isArray(d) ? d : (d.threads || d.data || []));
    if (!arr.length) break;
    const before = all.size;
    for (const t of arr) {
      const id = t.slug || t.uuid; if (!id) continue;
      if (!all.has(id)) all.set(id, {
        id, url: "https://www.perplexity.ai/search/" + id,
        title: (t.title || t.query_str || "").trim(),
        date: t.last_query_datetime || "", model: t.display_model || t.mode || "",
        queries: t.query_count || 0, preview: (t.answer_preview || "").trim()
      });
    }
    page++;
    console.log(`[pplx] page ${page} | offset ${offset} | +${arr.length} | unique ${all.size}`);
    if (all.size === before) break;          // no new rows → done
    if (arr.length < LIMIT) break;           // short page → last page
    if (page > 500) break;                   // safety cap
    offset += LIMIT; await sleep(300);
  }
  const list = [...all.values()].sort((a,b)=>(b.date||"").localeCompare(a.date||""));
  const qsum = list.reduce((s,t)=>s+t.queries,0);
  console.log(`%c[pplx] DONE — ${list.length} threads · ${qsum} total queries`, "font-weight:bold;color:green");

  const esc = s => (s||"").replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const rows = list.map((t,i)=>`<li><span class=n>${i+1}</span> <a href="${esc(t.url)}">${esc(t.title)||'(untitled)'}</a>`
    +`<div class=m>${esc(t.date)} · ${esc(t.model)}</div>`+(t.preview?`<div class=p>${esc(t.preview)}</div>`:"")+`</li>`).join("\n");
  const html = `<!DOCTYPE html><meta charset=utf-8><title>Perplexity Library — ${list.length} threads</title>
<style>body{font:14px/1.5 system-ui,sans-serif;max-width:64rem;margin:2rem auto;padding:0 1rem}
.n{display:inline-block;width:4em;color:#999;text-align:right;margin-right:.5em}ol{list-style:none;padding:0}
li{margin:.5em 0;padding:.4em 0;border-bottom:1px solid #eee}a{color:#1352d4;text-decoration:none;font-weight:600}
.m{color:#888;font-size:12px;margin-left:4.5em}.p{color:#555;font-size:12.5px;margin:.2em 0 0 4.5em}</style>
<h1>Perplexity Library — ${list.length} threads</h1><p>Captured ${new Date().toISOString()}</p>
<ol>\n${rows}\n</ol>`;
  const dl = (data,type,name)=>Object.assign(document.createElement("a"),
    {href:URL.createObjectURL(new Blob([data],{type})),download:name}).click();
  dl(html, "text/html", `perplexity-library-${list.length}.html`);
  dl(JSON.stringify(list,null,2), "application/json", `perplexity-library-${list.length}.json`);
  window.__pplxThreads = list;
  console.log("[pplx] downloaded HTML + JSON · array in window.__pplxThreads");
})();
```

**Output of Phase A:** `perplexity-library-<N>.json` — an array of
`{ id, url, title, date, model, queries, preview }`. This is the **index** (one
row per thread, with its `/search/<slug>` URL), *not* the bodies yet.

## Phase B — fetch the bodies (verbatim, refined version)

Run this **after** Phase A (it reads `window.__pplxThreads`). It GETs
`/rest/thread/<slug>`, follows thread-body pagination via `next_cursor` /
`has_next_page`, accumulates `entries` + `background_entries`, adapts its delay to
avoid 429s (honoring `retry-after`), **resumes** (skips already-fetched), and
downloads `pplx-bodies-partial-<N>.json` every 50 plus a final `pplx-bodies-<N>.json`:

```js
(async () => {
  const slugs = (window.__pplxThreads || []).map(t => t.id);
  if (!slugs.length) { console.error("window.__pplxThreads empty — run the index script first."); return; }
  window.__pplxBodies = window.__pplxBodies || {};
  const done = window.__pplxBodies, sleep = ms => new Promise(r => setTimeout(r, ms));
  const FLOOR = 5000, CEIL = 45000, DUMP_EVERY = 50, PAGE_CAP = 40;
  let delay = 7000;                       // adaptive; grows on 429, decays on success
  const truncated = [];
  const dl = (data,name)=>Object.assign(document.createElement("a"),
    {href:URL.createObjectURL(new Blob([data],{type:"application/json"})),download:name}).click();

  // one GET, with 429 handling; returns parsed json or null
  const get = async (url) => {
    for (let t=1; t<=6; t++) {
      const res = await fetch(url, { credentials:"include" });
      if (res.status === 429) {
        const ra = parseInt(res.headers.get("retry-after")||"0",10)*1000;
        const wait = ra || Math.min(delay*2, 90000);
        delay = Math.min(delay*1.5, CEIL);
        console.warn(`  429 → wait ${Math.round(wait/1000)}s, base delay now ${Math.round(delay/1000)}s`);
        await sleep(wait); continue;
      }
      if (!res.ok) { console.error("  HTTP", res.status, url); return null; }
      return res.json();
    }
    return null;
  };

  let i = 0, fetched = 0;
  for (const slug of slugs) {
    i++;
    if (done[slug]) continue;                                  // resume
    const first = await get("https://www.perplexity.ai/rest/thread/" + slug);
    if (!first) continue;
    const entries = [...(first.entries||[])];
    const bg = [...(first.background_entries||[])];
    let cursor = first.next_cursor, more = first.has_next_page, pages = 1;
    const seen = new Set();
    while (more && cursor && !seen.has(cursor) && pages < PAGE_CAP) {  // follow thread-body pagination
      seen.add(cursor); pages++;
      const nxt = await get("https://www.perplexity.ai/rest/thread/" + slug +
                            "?next_cursor=" + encodeURIComponent(cursor));
      if (!nxt) break;
      entries.push(...(nxt.entries||[])); bg.push(...(nxt.background_entries||[]));
      cursor = nxt.next_cursor; more = nxt.has_next_page;
      await sleep(delay);
    }
    if (more) truncated.push(slug);                            // couldn't fully paginate → revisit later
    done[slug] = { id: slug, thread_metadata: first.thread_metadata, status: first.status,
                   entries, background_entries: bg, pages };
    fetched++;
    delay = Math.max(FLOOR, delay - 250);                      // decay back down after success
    console.log(`[body] ${i}/${slugs.length} ✓ ${slug}  entries=${entries.length} pages=${pages}  (got ${fetched}, delay ${Math.round(delay/1000)}s)`);
    if (fetched % DUMP_EVERY === 0)
      dl(JSON.stringify(done), `pplx-bodies-partial-${Object.keys(done).length}.json`);
    if (i < slugs.length) await sleep(delay);
  }
  dl(JSON.stringify(done), `pplx-bodies-${Object.keys(done).length}.json`);
  if (truncated.length) { console.warn("Truncated (re-run to finish):", truncated); window.__pplxTruncated = truncated; }
  console.log(`%c[body] DONE — ${Object.keys(done).length} bodies captured`, "font-weight:bold;color:green");
})();
```

**Output:** a bodies dump keyed by slug — exactly what `sources/perplexity.py`
parses: `{ "<slug>": { id, thread_metadata, entries[], background_entries[], pages } }`.
Each `entry.text` decodes to `steps[]` with INITIAL_QUERY (the question) and FINAL
(the answer JSON: `structured_answer` markdown + `web_results` sources).

Notes:
- It's deliberately **slow** (5–45 s/thread, adaptive) to stay under Perplexity's
  rate limit; a full library takes a while. It **resumes** — re-run after a 429
  storm or to finish `window.__pplxTruncated`, and it skips what's already in
  `window.__pplxBodies`.
- Keep the `pplx-bodies-partial-<N>.json` files (every 50) as checkpoints; the
  final `pplx-bodies-<N>.json` is the complete dump.

## Phase C — ingest into CHATDRILL

```bash
chatdrill split pplx-bodies-1053.json          # → raw/perplexity/<slug>.json (one per thread)
chatdrill ingest raw/perplexity/<slug>.json    # build the model
chatdrill tiddlers <id-prefix> --ensure        # → wiki/tiddlers/  (TiddlyWiki)
chatdrill md       <id-prefix>                  # whole chat as one Markdown doc
```

Verified: all 1053 threads of a real dump ingest cleanly → 3967 exchanges
(matches the standalone `pplx2tw.py` tiddler count), 4905 code blocks, 36340 urls.
