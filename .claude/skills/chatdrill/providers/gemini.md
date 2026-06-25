# Gemini → CHATDRILL  ·  ⚠ extraction method needed

**Status: pending.** The URL pattern parses (`gemini.google.com/app/<id>` →
`chatdrill source <url>` reports provider `gemini`), but **no verified extraction
method or sample export exists yet**, so there is no `sources/gemini.py` encoder.
Gemini history may be reachable via Google Takeout or a DOM scrape — **not
documented here because it isn't verified**.

This file is intentionally a stub — the acquisition method is **not invented here**.

## What's needed (please provide ONE)

- a **Google Takeout** export sample of Gemini/Bard activity, or
- the **browser-console script** / DOM-scrape you use, or
- the **API request** (DevTools → Network) returning a conversation, with its JSON shape.

Once a real sample is available: `sources/gemini.py` + register `gemini` as
`export`, then `chatdrill split`/`ingest` work like the others.
