"""Provider registry — input sources by host, with URL link structures.

Each provider declares its url hosts and the path pattern that carries the chat
id, so `parse_url` turns a chat URL into (provider, chat_id) deterministically —
no auth/fetch needed. Loading the chat's *content* is separate: OpenWebUI reads
the local db; ChatGPT reads an exported conversations.json; the others await a
sample export (their URLs are auth-gated, so a server-side fetch can't see them).

Link structures (verified from real URLs):
  chatgpt    https://chatgpt.com/c/<id>
  deepseek   https://chat.deepseek.com/a/chat/s/<id>
  kimi       https://www.kimi.com/chat/<id>?...
  zai (GLM)  https://chat.z.ai/c/<id>
  perplexity https://www.perplexity.ai/search/<slug-id>
  gemini     https://gemini.google.com/app/<id>
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from .base import Source
from .openwebui import OpenWebUISource


@dataclass(frozen=True)
class ProviderInfo:
    name: str
    hosts: tuple[str, ...]
    path_re: str | None          # regex with group 1 = chat id (None for local db)
    shape: str
    status: str                  # "db" | "export" | "awaiting"


PROVIDERS: list[ProviderInfo] = [
    ProviderInfo("openwebui", (), None, "local webui.db message tree", "db"),
    ProviderInfo("chatgpt", ("chatgpt.com", "chat.openai.com"),
                 r"/c/([0-9A-Za-z-]{8,})", "mapping tree", "export"),
    ProviderInfo("claude", ("claude.ai",),
                 r"/chat/([0-9A-Za-z-]{8,})", "chat_messages list", "export"),
    ProviderInfo("deepseek", ("chat.deepseek.com", "deepseek.com"),
                 r"/a/chat/s/([0-9A-Za-z-]{8,})", "JSON export", "awaiting"),
    ProviderInfo("kimi", ("kimi.com", "www.kimi.com"),
                 r"/chat/([0-9A-Za-z-]{8,})", "JSON export", "awaiting"),
    ProviderInfo("zai", ("chat.z.ai", "z.ai"),
                 r"/c/([0-9A-Za-z-]{8,})", "GLM JSON export", "awaiting"),
    ProviderInfo("perplexity", ("perplexity.ai", "www.perplexity.ai"),
                 r"/search/([\w-]+)", "entries[] Q&A blocks", "export"),
    ProviderInfo("gemini", ("gemini.google.com",),
                 r"/app/(\w+)", "DOM scrape", "awaiting"),
]
_BY_NAME = {p.name: p for p in PROVIDERS}

# Implemented ref-loadable encoders (match priority order).
_SOURCES: list[Source] = [OpenWebUISource()]


def provider_for_host(host: str) -> ProviderInfo | None:
    host = host.lower().split(":")[0]
    for p in PROVIDERS:
        if any(host == h or host.endswith("." + h) for h in p.hosts):
            return p
    return None


def parse_url(url: str) -> tuple[ProviderInfo, str]:
    """(provider, chat_id) for a chat URL. Raises ValueError if unrecognized."""
    u = urlparse(url)
    prov = provider_for_host(u.netloc)
    if prov is None:
        raise ValueError(f"unknown provider host {u.netloc!r}")
    if prov.path_re:
        m = re.search(prov.path_re, u.path)
        if m:
            return prov, m.group(1)
    raise ValueError(f"could not find a chat id in {url!r} for {prov.name}")


def for_ref(ref: str) -> Source:
    """Encoder for a directly-loadable reference (local db chat-id), else a
    precise NotImplementedError telling you how to ingest this provider."""
    for src in _SOURCES:
        if src.matches(ref):
            return src
    if ref.startswith(("http://", "https://")):
        try:
            prov, cid = parse_url(ref)
        except ValueError as e:
            raise NotImplementedError(str(e))
        if prov.status == "export":
            raise NotImplementedError(
                f"{prov.name} chat {cid}: export the conversation as JSON and run "
                f"`chatdrill ingest <export.json>` (auth-gated URL can't be fetched).")
        raise NotImplementedError(
            f"no content encoder yet for {prov.name} ({prov.shape}). Send a sample "
            f"export and I'll build sources/{prov.name}.py. (chat id: {cid})")
    raise NotImplementedError(
        f"no encoder matches {ref!r} (use a webui.db chat-id, or a provider URL).")


def awaiting() -> list[str]:
    return [p.name for p in PROVIDERS if p.status == "awaiting"]
