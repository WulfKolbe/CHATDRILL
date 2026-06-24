# CHATDRILL — Project Skill & Conventions

This file captures the working conventions for the CHATDRILL project. Read it
before starting work so you follow the project's layout and rules.

## Project layout (llmwiki structure: raw → drill → wiki)

| Path                  | Purpose                                                              |
| --------------------- | ------------------------------------------------------------------- |
| `raw/`                | **Input** conversation files + per-chat splits (`raw/<provider>/`). Big; git-ignored. |
| `drill/`              | **docmodel structure**: per-chat `<id>.chatdrill.json` sidecar + `<id>.chatdrill/` blobs (chatmodel/docmodel/results/files). Git-ignored. |
| `wiki/`               | **Results**: the TiddlyWiki folder. Run the TW server here.         |
| `wiki/tiddlers/`      | Generated tiddlers (+ seed). Generated chat tiddlers git-ignored.   |
| `wiki/tiddlywiki.info`| TW server/build config.                                             |
| `oldstuff/`           | Existing / legacy code, read-only reference.                        |
| `tmp/`                | **Scratch space. Use this instead of `/tmp`.**                      |
| `SKILL.md` / `PLANNING.md` | Conventions / living plan.                                     |

Flow: `split <bulk> → raw/` · `ingest raw/<p>/<id>.json → drill/` ·
`tiddlers --ensure → wiki/tiddlers/`. Env: `CHATDRILL_RAW`, `CHATDRILL_WORK`
(drill), `CHATDRILL_TIDDLERS` (wiki/tiddlers).

## Conventions

### Temp files → `tmp/`, never `/tmp`
All scratch files, intermediate output, downloads, generated artifacts, and
throwaway scripts go in `./tmp/`. Do **not** write to the system `/tmp`. The
folder is git-ignored, so anything there is safe to delete at any time.

### `oldstuff/` is the archive
When migrating or rewriting, move the existing/legacy code into `oldstuff/`
rather than deleting it. Treat it as read-only reference material — don't run
or build from it; copy what's needed into the live tree.

### TiddlyWiki server
`wiki/` is the TiddlyWiki folder (results). Run the server from there:

```sh
tiddlywiki wiki --listen       # or:  npx tiddlywiki wiki --listen
```

Tiddlers live as individual files in `tiddlers/`. When the filesystem plugin is
active, edits in the browser are written back to `tiddlers/` automatically.

## Workflow notes
- Keep `PLANNING.md` current — it is the source of truth for what's in progress.
- Don't commit anything under `tmp/`.
