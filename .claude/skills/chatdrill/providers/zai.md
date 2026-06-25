# Z.ai (GLM) → CHATDRILL  ·  ⚠ extraction method needed

**Status: pending.** The URL pattern parses (`chat.z.ai/c/<id>` →
`chatdrill source <url>` reports provider `zai`), but **no verified extraction
method or sample export exists yet**, so there is no `sources/zai.py` encoder.

This file is intentionally a stub — the acquisition method is **not invented here**.

## What's needed (please provide ONE)

- a **sample export** (the JSON/zip Z.ai / GLM produces), or
- the **browser-console script** you use to pull the history, or
- the **API request** (DevTools → Network → Fetch/XHR) returning a chat's messages,
  with the response JSON shape.

Once a real sample is available: `sources/zai.py` + register `zai` as `export`,
then `chatdrill split`/`ingest` work like the others.
