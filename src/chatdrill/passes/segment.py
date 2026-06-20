"""pass03 — segment each turn's content into prose / code blocks.

Two code shapes, because chats are a hostile environment:
  1. Standard markdown ```fences``` (exact, fenced=True).
  2. Stripped fences — a lone language-token line (`typescript`, `python`,
     `bash`, `json`, …) followed by code, with the ``` markers lost in the
     source (verified in real OpenWebUI/Perplexity exports). Recovered
     heuristically (fenced=False) by reading code-ish lines until a clear prose
     sentence resumes.

Everything not code is prose. URLs/errors are not split here — pass04 lifts them
straight out of the (prose+code) content.
"""
from __future__ import annotations

import re

from ..models import ChatModel, Segment, Turn

# Lone-line tokens we trust as a code-block start even without ``` fences.
# Deliberately conservative: only words that are ~never a prose line on their own
# (so no "go", "r", "make", "text", "java", "sh").
HEURISTIC_LANGS = {
    "python", "bash", "shell", "console", "typescript", "javascript", "json",
    "yaml", "html", "css", "scss", "sql", "tsx", "jsx", "dockerfile", "golang",
    "rust", "kotlin", "graphql", "toml",
}

_FENCE = re.compile(r"^```\s*([\w+#.-]*)\s*$")
_FENCE_CLOSE = re.compile(r"^```\s*$")
_TOKEN = re.compile(r"^([A-Za-z+#]+)\s*$")

# strong code signals on a single line
_CODE_RE = re.compile(
    r"[{}=;]|::|=>|->|\(\)|</?\w+>|"
    r"^\s*(import|from|def|class|const|let|var|function|public|private|"
    r"protected|return|interface|type|async|await|export|for|while|if)\b|"
    r"\b\w+\([^)]*\)|\w+\.\w+\(")


def _looks_code(line: str) -> bool:
    if not line.strip():
        return False
    if line[:1] in (" ", "\t"):               # indented
        return True
    s = line.strip()
    if s.startswith(("#", "//", "$", ">>>", "python ", "bash ", "npm ", "pip ",
                     "git ", "curl ", "cd ", "sudo ", "import ", "export ")):
        return True
    if _CODE_RE.search(s):
        return True
    if "=" in s and len(s) < 80:
        return True
    return False


def _is_sentence(line: str) -> bool:
    s = line.strip()
    return bool(re.match(r"^[A-Z][^=<>{}]*[.!?:]$", s)) and len(s.split()) >= 5


def segment_text(content: str) -> list[Segment]:
    if not content:
        return []
    lines = content.split("\n")
    segs: list[Segment] = []
    prose: list[str] = []

    def flush_prose() -> None:
        if prose:
            text = "\n".join(prose).strip()
            if text:
                segs.append(Segment(kind="prose", text=text))
            prose.clear()

    i, n = 0, len(lines)
    while i < n:
        line = lines[i]

        m = _FENCE.match(line)
        if m:                                 # ``` fenced block (exact)
            flush_prose()
            lang = m.group(1) or None
            j, code = i + 1, []
            while j < n and not _FENCE_CLOSE.match(lines[j]):
                code.append(lines[j])
                j += 1
            segs.append(Segment(kind="code", lang=lang, fenced=True,
                                text="\n".join(code)))
            i = j + 1
            continue

        t = _TOKEN.match(line)
        if t and t.group(1).lower() in HEURISTIC_LANGS:   # stripped-fence recovery
            lang = t.group(1).lower()
            j, code = i + 1, []
            while j < n:
                ln = lines[j]
                if ln.strip() == "":
                    break
                if _is_sentence(ln) and not _looks_code(ln):
                    break
                code.append(ln)
                j += 1
            if code:                          # only a block if real code followed
                flush_prose()
                segs.append(Segment(kind="code", lang=lang, fenced=False,
                                    text="\n".join(code)))
                i = j
                continue
            # else: a bare word that wasn't code — fall through as prose

        prose.append(line)
        i += 1

    flush_prose()
    return segs


def render_turn(turn: Turn) -> str:
    """Reconstruct a turn's text with code segments re-fenced (```lang```), so
    stripped-fence code renders correctly. Falls back to raw content if the turn
    hasn't been segmented yet."""
    if not turn.segments:
        return turn.content
    parts: list[str] = []
    for s in turn.segments:
        if s.kind == "code":
            parts.append(f"```{s.lang or ''}\n{s.text}\n```")
        else:
            parts.append(s.text)
    return "\n\n".join(p for p in parts if p.strip())


def _segment_turn(turn: Turn) -> None:
    turn.segments = segment_text(turn.content)


def segment_model(model: ChatModel) -> ChatModel:
    """Populate ``segments`` on every query/answer turn (in place)."""
    for ex in model.exchanges:
        _segment_turn(ex.query)
        if ex.answer is not None:
            _segment_turn(ex.answer)
    return model
