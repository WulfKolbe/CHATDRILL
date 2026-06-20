"""CHATDRILL core data models (pydantic v2).

The canonical internal unit is the ``Exchange`` (a Q&A pair). Source message
trees are reduced at pass02 to ``Exchange[]`` + a forgotten-branch list. See
docs/CHATDRILL_DESIGN.md §2 for the full contract.

Only the fields needed for the pass01→pass02 slice are populated today; the rest
of the model (semantic states, hypergraph, …) lands as later passes are built.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["user", "assistant", "system"]


class RawMessage(BaseModel):
    """One node of the source message tree (OpenWebUI ``history.messages``)."""
    id: str
    parent_id: Optional[str] = None
    children_ids: list[str] = Field(default_factory=list)
    role: Role
    content: str = ""
    timestamp: Optional[int] = None          # unix seconds
    model_name: Optional[str] = None
    model_idx: Optional[int] = None


class RawChat(BaseModel):
    """A normalized chat straight from a source adapter (pass01 output)."""
    id: str
    title: str = ""
    source: str = ""                          # e.g. "openwebui:webui.db"
    models: list[str] = Field(default_factory=list)
    created_at: Optional[int] = None
    tree: dict[str, RawMessage] = Field(default_factory=dict)   # id -> message
    current_id: Optional[str] = None          # leaf of the canonical path


class Turn(BaseModel):
    """A single message lifted onto a path, with its index."""
    id: str
    role: Role
    index: int
    content: str = ""
    timestamp: Optional[int] = None
    model_name: Optional[str] = None
    on_current_path: bool = True


class Exchange(BaseModel):
    """The CANONICAL unit: one Q&A pair. Enrichment past ``query`` is optional
    and source-dependent (Appendix C) — consumers degrade when a field is None."""
    id: str
    index: int
    query: Turn
    answer: Optional[Turn] = None             # absent ⇒ unanswered
    on_current_path: bool = True
    model: Optional[str] = None               # answering model
    asked_at: Optional[int] = None
    answered_at: Optional[int] = None
    regen_count: int = 1                       # sibling answers at this branch point

    @property
    def answered(self) -> bool:
        return self.answer is not None

    @property
    def latency_ms(self) -> Optional[int]:
        if self.asked_at is None or self.answered_at is None:
            return None
        return (self.answered_at - self.asked_at) * 1000


class ForgottenBranch(BaseModel):
    """A subtree that hangs off the canonical path — an abandoned side-quest."""
    root_turn_id: str
    turns: list[Turn] = Field(default_factory=list)
    reason: Optional[Literal["regenerate", "edit", "manual_switch"]] = None


class ChatModel(BaseModel):
    """The model that flows through the passes. Today: exchanges + branches."""
    id: str
    title: str = ""
    source: str = ""
    models: list[str] = Field(default_factory=list)
    created_at: Optional[int] = None
    exchanges: list[Exchange] = Field(default_factory=list)
    forgotten_branches: list[ForgottenBranch] = Field(default_factory=list)
