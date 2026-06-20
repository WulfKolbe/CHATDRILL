# CHATDRILL — Project Skill & Conventions

This file captures the working conventions for the CHATDRILL project. Read it
before starting work so you follow the project's layout and rules.

## Project layout

| Path              | Purpose                                                           |
| ----------------- | ---------------------------------------------------------------- |
| `tiddlers/`       | TiddlyWiki tiddlers. The project root is served as a TW server.  |
| `tiddlywiki.info` | TiddlyWiki server/build config (loads `tiddlers/`).              |
| `oldstuff/`       | Existing / legacy code collected here for reference. Read-only.  |
| `tmp/`            | **Scratch space. Use this instead of `/tmp`.** See below.        |
| `SKILL.md`        | This file — project conventions.                                 |
| `PLANNING.md`     | Living plan, goals, and task tracking.                           |

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
The project root is a TiddlyWiki folder. Run the server with:

```sh
tiddlywiki . --listen          # or:  npx tiddlywiki . --listen
```

Tiddlers live as individual files in `tiddlers/`. When the filesystem plugin is
active, edits in the browser are written back to `tiddlers/` automatically.

## Workflow notes
- Keep `PLANNING.md` current — it is the source of truth for what's in progress.
- Don't commit anything under `tmp/`.
