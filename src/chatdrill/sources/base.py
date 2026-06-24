"""The input-encoder (Source) interface — one per chat-history provider.

Acquisition is provider-specific and pluggable; every encoder normalizes its
provider's native shape (Appendix C of the design RFC) to the same ``RawChat``,
so the semantic compiler and the code-reconstruction layers never see provider
HTML/JSON. A ``Source`` is selected by reference (URL host, file, or local db).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from ..models import RawChat


class Source(ABC):
    """A provider input-encoder."""

    name: str = "source"

    @abstractmethod
    def matches(self, ref: str) -> bool:
        """True if this encoder handles the given reference (url / file / id)."""

    @abstractmethod
    def load(self, ref: str) -> RawChat:
        """Normalize one chat to a RawChat."""

    # Optional bulk access (db-backed providers override these).
    def list_chats(self, limit: int = 50) -> list[dict]:
        return []

    def iter_chats(self) -> Iterator[RawChat]:
        return iter(())
