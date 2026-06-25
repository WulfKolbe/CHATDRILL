# ChatGPT → CHATDRILL

ChatGPT has an **official data export**: request it in your account settings'
data-export feature; ChatGPT emails a link to a **`.zip`** that contains
`conversations.json` (plus users/feedback files). CHATDRILL ingests the `.zip`
directly (it extracts `conversations.json` for you).

> Verified against real exports (`~/Downloads/conversations*.json`, 381–625
> conversations). The exact menu wording in the ChatGPT UI may change — use
> whatever "export your data" option your account currently shows.

## Shape (verified)

`conversations.json` is a JSON **array of conversations**; each has a `mapping`
tree (`{id, message, parent, children}`) and a `current_node` leaf. Messages carry
`author.role`, `content.parts`, `create_time`, and `metadata.model_slug`.
`sources/chatgpt.py` lifts that to the canonical `Exchange[]`.

## Ingest

```bash
chatdrill split <export>.zip                      # → raw/chatgpt/<id>.json (one per chat)
#   (or:  chatdrill ingest <export>.zip --id <conversation-id>   for one chat)
chatdrill ingest raw/chatgpt/<id>.json
chatdrill tiddlers <id-prefix> --ensure           # → wiki/tiddlers/
chatdrill md       <id-prefix>                     # markdown for an LLM
```

`split`/`ingest` auto-detect ChatGPT (and accept either the `.zip` or a bare
`conversations.json`).
