"""Sidecar — persistent per-chat state (mirrors PDFDRILL's sidecar.py).

A chat has no source file on disk (it lives in webui.db), so artifacts are keyed
by chat id under a work root (``CHATDRILL_WORK``, default ``./drills``):

    <work>/<id>.chatdrill.json   state: facts, evidence, layers, transitions
    <work>/<id>.chatdrill/       heavy blobs: chatmodel.json, tiddlers, reports

The sidecar is the single source of truth. Each command reads it on entry, does
its work, appends to it, writes on exit. Facts are cumulative — milestones that
accumulate, not a linear sequence.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

VERSION = "0.1.0"


def work_root(work: Optional[str] = None) -> Path:
    """Resolve the docmodel artifact root: explicit arg > $CHATDRILL_WORK > ./drill."""
    p = work or os.environ.get("CHATDRILL_WORK") or "drill"
    return Path(p).expanduser()


def resolve_local_id(chat_id: str, work: Optional[str] = None) -> str:
    """Canonical id from an existing sidecar, by exact match or unique prefix —
    DB-free (globs the work dir). Used by status/steps so they need no webui.db.
    Returns chat_id unchanged when nothing local matches."""
    root = work_root(work)
    if (root / f"{chat_id}.chatdrill.json").exists():
        return chat_id
    matches = sorted(root.glob(f"{chat_id}*.chatdrill.json"))
    if len(matches) == 1:
        return matches[0].name[: -len(".chatdrill.json")]
    if len(matches) > 1:
        raise ValueError(f"chat id prefix {chat_id!r} matches {len(matches)} "
                         f"local sidecars — give more characters.")
    return chat_id


class Sidecar:
    """Read/write the per-chat ``.chatdrill.json`` state file."""

    def __init__(self, chat_id: str, work: Optional[str] = None):
        self.chat_id = chat_id
        root = work_root(work)
        self.json_path = root / f"{chat_id}.chatdrill.json"
        self.blob_dir = root / f"{chat_id}.chatdrill"
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self.json_path.exists():
            self._data = json.loads(self.json_path.read_text(encoding="utf-8"))
        else:
            self._data = {
                "chat_id": self.chat_id,
                "chatdrill_version": VERSION,
                "facts": [],
                "evidence": {},
                "layers": {},
                "transitions": [],
            }

    def save(self) -> None:
        self._data["chatdrill_version"] = VERSION
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        self.json_path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    # -- Facts (cumulative state) --
    @property
    def facts(self) -> set[str]:
        return set(self._data.get("facts", []))

    def add_fact(self, fact: str) -> None:
        facts = self._data.setdefault("facts", [])
        if fact not in facts:
            facts.append(fact)

    def remove_fact(self, fact: str) -> None:
        facts = self._data.get("facts", [])
        if fact in facts:
            facts.remove(fact)

    def has(self, fact: str) -> bool:
        return fact in self.facts

    # -- Evidence --
    @property
    def evidence(self) -> dict:
        return self._data.setdefault("evidence", {})

    def set_evidence(self, key: str, value: Any) -> None:
        self._data.setdefault("evidence", {})[key] = value

    def get_evidence(self, key: str, default: Any = None) -> Any:
        return self._data.get("evidence", {}).get(key, default)

    # -- Layers (references to blobs) --
    @property
    def layers(self) -> dict:
        return self._data.setdefault("layers", {})

    def set_layer(self, name: str, meta: dict) -> None:
        self._data.setdefault("layers", {})[name] = meta

    def get_layer(self, name: str) -> dict | None:
        return self._data.get("layers", {}).get(name)

    # -- Blob storage --
    def write_blob(self, name: str, content: str) -> str:
        self.blob_dir.mkdir(parents=True, exist_ok=True)
        path = self.blob_dir / name
        path.write_text(content, encoding="utf-8")
        return str(path)

    def read_blob(self, name: str) -> str | None:
        path = self.blob_dir / name
        return path.read_text(encoding="utf-8") if path.exists() else None

    def blob_path(self, name: str) -> Path:
        return self.blob_dir / name

    def has_blob(self, name: str) -> bool:
        return (self.blob_dir / name).exists()

    # -- Transition log --
    def log_transition(self, node: str, from_facts: str, to_fact: str,
                       cost_ms: float = 0, detail: str = "") -> None:
        self._data.setdefault("transitions", []).append({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "node": node,
            "from": from_facts,
            "to": to_fact,
            "cost_ms": round(cost_ms, 1),
            "detail": detail,
        })

    @property
    def transitions(self) -> list[dict]:
        return self._data.get("transitions", [])
