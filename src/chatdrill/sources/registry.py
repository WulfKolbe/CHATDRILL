"""Provider registry — pick the input-encoder for a reference, and report which
providers still await an encoder (build one when a test link arrives).

Today only OpenWebUI (local webui.db) is implemented. The other providers are
declared with their selector + native shape so the registry can give a precise
"awaiting encoder" message and so adding one is a drop-in.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from .base import Source
from .openwebui import OpenWebUISource


@dataclass(frozen=True)
class ProviderInfo:
    name: str
    hosts: tuple[str, ...]            # url hosts this provider serves
    shape: str                        # native shape, for the awaiting message
    implemented: bool


# Declared providers (status mirrors docs/CODE_RECONSTRUCTION.md).
PROVIDERS: list[ProviderInfo] = [
    ProviderInfo("openwebui", (), "local webui.db message tree", True),
    ProviderInfo("perplexity", ("perplexity.ai", "www.perplexity.ai"),
                 "flat entries[] Q&A blocks", False),
    ProviderInfo("chatgpt", ("chatgpt.com", "chat.openai.com"),
                 "mapping tree", False),
    ProviderInfo("deepseek", ("chat.deepseek.com", "deepseek.com"),
                 "JSON export", False),
    ProviderInfo("qwen", ("tongyi.aliyun.com", "qwen.ai", "chat.qwen.ai"),
                 "JSON export", False),
    ProviderInfo("gemini", ("gemini.google.com",), "DOM scrape", False),
]

# Implemented encoders, in match priority order.
_SOURCES: list[Source] = [OpenWebUISource()]


def _provider_for_host(host: str) -> ProviderInfo | None:
    host = host.lower()
    for p in PROVIDERS:
        if any(host == h or host.endswith("." + h) for h in p.hosts):
            return p
    return None


def for_ref(ref: str) -> Source:
    """Return the encoder for a reference, or raise a precise NotImplementedError
    naming the provider whose encoder still needs building from a test link."""
    for src in _SOURCES:
        if src.matches(ref):
            return src
    if ref.startswith(("http://", "https://")):
        prov = _provider_for_host(urlparse(ref).netloc)
        if prov and not prov.implemented:
            raise NotImplementedError(
                f"no encoder yet for {prov.name} ({prov.shape}). Send a test link "
                f"for {prov.name} and I'll build sources/{prov.name}.py.")
        raise NotImplementedError(
            f"no encoder matches URL host {urlparse(ref).netloc!r}.")
    raise NotImplementedError(
        f"no encoder matches {ref!r} (try a chat-id/prefix for the local webui.db).")


def awaiting() -> list[str]:
    return [p.name for p in PROVIDERS if not p.implemented]
