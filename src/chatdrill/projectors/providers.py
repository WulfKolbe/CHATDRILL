"""Per-provider preambles + structure — a chat's host determines its conventions.

Each provider (host) differs: bibkey code, math delimiters, citation style, the
preamble tiddler, and which sections the chat-root lists. The projector reads a
``Provider`` so different hosts produce different (but consistently transcluded)
TiddlyWiki structures. Analogous to PDFDRILL's per-document LaTeX preamble.
"""
from __future__ import annotations

from dataclasses import dataclass

# math delimiter pairs, matched LONGEST-OPEN first so `$$`/`\[` beat `$`/`\(`.
_DELIMS_DOLLAR = ((r"$$", r"$$"), (r"\[", r"\]"), (r"\(", r"\)"), (r"$", r"$"))
_DELIMS_BRACKET = ((r"\[", r"\]"), (r"$$", r"$$"), (r"\(", r"\)"), (r"$", r"$"))


@dataclass(frozen=True)
class Provider:
    key: str                     # source prefix, e.g. "perplexity"
    code: str                    # bibkey prefix code, e.g. "Pplx"
    label: str                   # the provider tag, e.g. "perplexity"
    math: tuple                  # (open, close) delimiter pairs
    citation: bool               # True ⇒ `[n]` bracket citations map to sources
    sections: tuple              # chat-root structure (in order)
    preamble: str                # the provider preamble tiddler body


_COMMON = ("Math is transcluded through the FO (inline) / EQ (display) templates "
           "and rendered by TiddlyWiki's `<$latex>` (KaTeX). Code blocks become "
           "CODE tiddlers, URLs become URL tiddlers; every reference is a "
           "templated transclusion (a title rendered through a template).")

PROVIDERS: dict[str, Provider] = {
    "openwebui": Provider(
        "openwebui", "Owui", "openwebui", _DELIMS_DOLLAR, False,
        ("Exchanges", "Code", "Files", "Links"),
        "OpenWebUI chat (local db). " + _COMMON),
    "chatgpt": Provider(
        "chatgpt", "Gpt", "chatgpt", _DELIMS_DOLLAR, False,
        ("Exchanges", "Code", "Files", "Links"),
        "ChatGPT export (mapping tree). Math uses `$…$`/`$$…$$`. " + _COMMON),
    "claude": Provider(
        "claude", "Cla", "claude", _DELIMS_DOLLAR, False,
        ("Exchanges", "Code", "Files", "Links"),
        "Claude.ai export (chat_messages). Math uses `$…$`/`$$…$$`. " + _COMMON),
    "perplexity": Provider(
        "perplexity", "Pplx", "perplexity", _DELIMS_BRACKET, True,
        ("Exchanges", "Code", "Links", "Sources"),
        "Perplexity export. Answers cite sources as `[n]`; these map to the "
        "Sources list and become CIT transclusions. Math uses `\\(…\\)`. " + _COMMON),
    "kimi": Provider(
        "kimi", "Kimi", "kimi", _DELIMS_DOLLAR, False,
        ("Exchanges", "Code", "Links"), "Kimi export. " + _COMMON),
    "zai": Provider(
        "zai", "Zai", "zai", _DELIMS_DOLLAR, False,
        ("Exchanges", "Code", "Links"), "Z.ai (GLM) export. " + _COMMON),
    "deepseek": Provider(
        "deepseek", "Dsk", "deepseek", _DELIMS_DOLLAR, False,
        ("Exchanges", "Code", "Links"), "DeepSeek export. " + _COMMON),
    "gemini": Provider(
        "gemini", "Gem", "gemini", _DELIMS_DOLLAR, False,
        ("Exchanges", "Code", "Links"), "Gemini export. " + _COMMON),
}


def for_source(source: str) -> Provider:
    """Provider for a model.source like 'perplexity:export' or 'openwebui:webui.db'."""
    key = (source or "").split(":")[0]
    return PROVIDERS.get(key, PROVIDERS["openwebui"])
