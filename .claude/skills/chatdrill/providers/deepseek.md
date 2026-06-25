# DeepSeek → CHATDRILL

Two verified routes — a **bulk data export** (best for everything) and a **public
share link** (one chat).

## Route 1 — bulk data export (.zip)  ·  verified

Request a data export in your DeepSeek account settings; you get a
**`deepseek_data-<date>.zip`** (or a bare `deepseek_conversations.json`) containing
`conversations.json`. CHATDRILL ingests it directly.

> Verified against `~/Downloads/deepseek_conversations.json` (326 conversations)
> and several `deepseek_data-*.zip`.

```bash
chatdrill split ~/Downloads/deepseek_data-2026-06-24.zip   # → raw/deepseek/<id>.json
chatdrill ingest raw/deepseek/<id>.json
chatdrill tiddlers <id-prefix> --ensure
```

**Shape (verified):** a list of conversations, each with a `mapping` tree like
ChatGPT's — but DeepSeek messages have no `author.role`; role is inferred from
`fragments` types (REQUEST=user, RESPONSE=assistant, THINK=reasoning, dropped).
`sources/deepseek.py` handles it.

## Route 2 — public share link  ·  verified

A public share URL is `https://chat.deepseek.com/share/<id>`. A plain `curl`/fetch
gets **403 "Human Verification"** (CloudFront bot protection); a **headed browser**
with stealth passes it. The page's SPA fetches
`https://chat.deepseek.com/api/v0/share/content?share_id=<id>` — that JSON is the
conversation. `tools/share_fetch.mjs` captures it:

```bash
# needs a display + a Chrome at $CHROME (default google-chrome-beta) and
# puppeteer-extra under $PUPPETEER_NM (default ~/perplexport/node_modules)
node tools/share_fetch.mjs "https://chat.deepseek.com/share/<id>" raw/deepseek/<id>.json
chatdrill ingest raw/deepseek/<id>.json
```

**Shape (verified):** `{ data: { biz_data: { title, messages: [...] } } }`, messages
with explicit USER/ASSISTANT roles + `fragments`. Same `sources/deepseek.py`.

> A *private* (logged-in, non-shared) DeepSeek chat URL — `/a/chat/s/<id>` — is not
> server-fetchable. Use Route 1 for those.
