# Kimi → CHATDRILL  ·  ⚠ extraction method needed

**Status: pending.** The URL pattern parses (`www.kimi.com/chat/<id>` →
`chatdrill source <url>` reports provider `kimi`), but **no verified extraction
method or sample export exists yet**, so there is no `sources/kimi.py` encoder.

This file is intentionally a stub — the acquisition method is **not invented here**.

## What's needed (please provide ONE)

- a **sample export** (the JSON/zip Kimi produces from its data-export feature), or
- the **browser-console script** you use to pull Kimi history (like the Perplexity
  one), or
- the **API request** (DevTools → Network → Fetch/XHR) that returns a chat's
  messages, with the response JSON shape.

Once a real sample is available, the encoder is a drop-in:
`sources/kimi.py` (normalize → `RawChat`) + register `kimi` as `export` in the
registry, then `chatdrill split`/`ingest` work like the others.
