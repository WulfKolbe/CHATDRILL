"""Explo multi-file splitter — Layer 0+4 (the deterministic, header-given case).

Your chats often exchange a whole codebase in one block, each file demarcated by
a header line:

    !!! path/to/file.ts
    <file content>
    !!! other/file.py
    <file content>

This pass slices a message at those headers into VirtualFiles, strips a wrapping
``` fence per file, infers the language from the extension, and (reverse-time)
keeps the LATEST version per path as canonical with older ones in `superseded`.

This is the explicit case of Layer 4 "file hypotheses": no reconstruction needed
— the path is given. Implicit (header-less) file synthesis is a later, LLM/
unification-assisted layer (see docs/CODE_RECONSTRUCTION.md).
"""
from __future__ import annotations

import hashlib
import re

from ..models import ChatModel, VirtualFile

_HEADER = re.compile(r"(?m)^[ \t]*!!!\s+([\w./\-]+\.[A-Za-z][\w]{0,5})[ \t]*$")
_FENCE_OPEN = re.compile(r"^\s*```[\w+#.-]*\s*$")
_FENCE_CLOSE = re.compile(r"^\s*```\s*$")

LANG_BY_EXT = {
    "py": "python", "ts": "typescript", "tsx": "typescript", "js": "javascript",
    "jsx": "javascript", "md": "markdown", "json": "json", "sh": "bash",
    "bash": "bash", "html": "html", "htm": "html", "css": "css", "scss": "scss",
    "sql": "sql", "yaml": "yaml", "yml": "yaml", "toml": "toml", "c": "c",
    "h": "c", "cpp": "cpp", "hpp": "cpp", "java": "java", "go": "go", "rs": "rust",
    "rb": "ruby", "php": "php", "xml": "xml", "tex": "latex", "awk": "awk",
    "lua": "lua", "kt": "kotlin", "swift": "swift", "r": "r",
}


def _lang_for(path: str) -> str | None:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return LANG_BY_EXT.get(ext)


def _strip_fence(text: str) -> str:
    lines = text.split("\n")
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()
    if lines and _FENCE_OPEN.match(lines[0]) and _FENCE_CLOSE.match(lines[-1]):
        lines = lines[1:-1]
    return "\n".join(lines)


def split_explo(text: str) -> list[tuple[str, str | None, str]]:
    """[(path, lang, content)] for each `!!! path` file in `text` (in order)."""
    heads = list(_HEADER.finditer(text or ""))
    out: list[tuple[str, str | None, str]] = []
    for i, m in enumerate(heads):
        path = m.group(1)
        start = m.end()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        content = _strip_fence(text[start:end].strip("\n"))
        if content.strip():
            out.append((path, _lang_for(path), content))
    return out


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def extract_virtual_files(model: ChatModel) -> ChatModel:
    """Populate model.virtual_files: latest version per path (newest exchange
    wins), older versions collapsed into `superseded`."""
    # gather every (path) occurrence with its exchange index, newest first
    occ: list[tuple[int, str, str, str | None, str]] = []   # (ex_idx, turn_id, path, lang, content)
    for ex in model.exchanges:
        for turn in (ex.query, ex.answer):
            if turn is None:
                continue
            for path, lang, content in split_explo(turn.content):
                occ.append((ex.index, turn.id, path, lang, content))
    occ.sort(key=lambda t: t[0], reverse=True)               # newest exchange first

    by_path: dict[str, VirtualFile] = {}
    order: list[str] = []
    for ex_idx, turn_id, path, lang, content in occ:
        if path not in by_path:
            by_path[path] = VirtualFile(
                path=path, lang=lang, content=content, latest_turn_id=turn_id,
                exchange_index=ex_idx, sha1=_sha1(content))
            order.append(path)
        else:
            vf = by_path[path]
            vf.superseded.append(turn_id)
            vf.revisions += 1

    model.virtual_files = [by_path[p] for p in order]
    return model
