# Provider extraction howtos

How to get chat history OUT of each provider and INTO CHATDRILL. Open the file for
the provider you're importing from.

| Provider | Status | Method | Howto |
|---|---|---|---|
| **OpenWebUI** | ✅ verified | local `webui.db` (no export) | [openwebui.md](openwebui.md) |
| **ChatGPT** | ✅ verified | official data export (.zip → conversations.json) | [chatgpt.md](chatgpt.md) |
| **Claude** | ✅ verified | official data export (.zip → conversations.json) | [claude.md](claude.md) |
| **DeepSeek** | ✅ verified | data export (.zip) OR public share link (headed fetch) | [deepseek.md](deepseek.md) |
| **Perplexity** | ✅ verified | browser-console: index + bodies (user's scripts) | [perplexity.md](perplexity.md) |
| **Kimi** | ⚠ pending | URL parses; **extraction method needed** | [kimi.md](kimi.md) |
| **Z.ai (GLM)** | ⚠ pending | URL parses; **extraction method needed** | [zai.md](zai.md) |
| **Gemini** | ⚠ pending | URL parses; **extraction method needed** | [gemini.md](gemini.md) |

"Verified" = a real export/sample was processed end-to-end through CHATDRILL.
"Pending" = the URL is recognized but no extraction method has been provided yet —
those howtos are honest stubs that **ask** for the method rather than invent one.

After you have an export file, the pipeline is the same for every provider:

```bash
chatdrill split  <export.json|.zip>           # → raw/<provider>/<id>.json
chatdrill ingest raw/<provider>/<id>.json      # build the model
chatdrill tiddlers <id-prefix> --ensure        # → wiki/tiddlers/
chatdrill md       <id-prefix>                 # markdown for an LLM
```
