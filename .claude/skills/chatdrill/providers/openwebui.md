# OpenWebUI → CHATDRILL

**No export needed** — OpenWebUI stores every chat as a JSON blob in a local
SQLite database (`webui.db`, `chat` table). CHATDRILL reads it **read-only**
directly. (Verified against a 1327- and a 1343-chat `webui.db`.)

## Use it

```bash
# point at the db (or set OPENWEBUI_DB in .env)
chatdrill list --db ~/myopenwebui/webui.db                 # browse chats (full ids)
chatdrill model   <id-prefix> --db ~/myopenwebui/webui.db  # build the model
chatdrill tiddlers <id-prefix> --ensure                    # → wiki/tiddlers/
chatdrill md       <id-prefix>                             # markdown for an LLM
```

`<id-prefix>` is any unique prefix of the chat id from `chatdrill list`.

## Shape (for reference)

`chat.history.messages` is a **tree** (`parentId` / `childrenIds`, `currentId` =
canonical leaf); messages carry `role`, `content`, `timestamp`, `modelName`.
CHATDRILL reduces the tree to the canonical `Exchange[]` (`sources/openwebui.py`).
No token counts in this format — that's fine, they're optional enrichment.
