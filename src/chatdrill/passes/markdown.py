"""Render a ChatModel as one clean Markdown document.

This is the analog of PDFDRILL's `md`: a single, self-contained transcript you
can open as a file or paste straight into an LLM chat. Code is re-fenced (via
pass03 segments) so stripped-fence code comes back as proper ```blocks```.
"""
from __future__ import annotations

from ..models import ChatModel
from .segment import render_turn


def render_chat_markdown(model: ChatModel) -> str:
    answered = sum(1 for e in model.exchanges if e.answered)
    meta = (f"Source: `{model.source}` · "
            f"Models: {', '.join(model.models) or '—'} · "
            f"{len(model.exchanges)} exchanges ({answered} answered)")
    out: list[str] = [f"# {model.title or model.id}", "", f"> {meta}", ""]

    for ex in model.exchanges:
        out += [f"## Q{ex.index}", "", render_turn(ex.query), ""]
        tag = f" — {ex.model}" if ex.model else ""
        lat = f" ({ex.latency_ms // 1000}s)" if ex.latency_ms is not None else ""
        body = render_turn(ex.answer) if ex.answer else "_(no answer)_"
        out += [f"### Answer{tag}{lat}", "", body, "", "---", ""]

    return "\n".join(out)
