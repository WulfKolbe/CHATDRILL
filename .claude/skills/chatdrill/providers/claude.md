# Claude.ai → CHATDRILL

Claude has an **official data export**: request it in your account settings' export
feature; Claude produces a **`.zip`** containing `conversations.json` (plus
users/projects/memories files). CHATDRILL ingests the `.zip` directly.

> Verified against a real Claude export `.zip` (177 conversations). The exact UI
> wording may change — use whatever "export data" option your account shows.

## Shape (verified)

`conversations.json` is a JSON **array of conversations**; each has `uuid`, `name`,
`created_at`, and `chat_messages[]`. Each message has `sender` (human/assistant),
a flat `text` (and a `content[]` block list), `created_at`, `parent_message_uuid`.
`sources/claude.py` synthesizes the linear chat tree → `Exchange[]`.

## Ingest

```bash
chatdrill split <claude-export>.zip               # → raw/claude/<uuid>.json (one per chat)
#   (or:  chatdrill ingest <claude-export>.zip --id <uuid>   for one chat)
chatdrill ingest raw/claude/<uuid>.json
chatdrill tiddlers <id-prefix> --ensure           # → wiki/tiddlers/
chatdrill md       <id-prefix>                     # markdown for an LLM
```

`split`/`ingest` auto-detect Claude (chat_messages list, distinct from ChatGPT's
mapping tree).
