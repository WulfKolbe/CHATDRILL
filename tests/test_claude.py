"""Claude export encoder tests.  Run: PYTHONPATH=src python3 tests/test_claude.py"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatdrill.passes.linearize import linearize          # noqa: E402
from chatdrill.sources import claude                       # noqa: E402


def _conv():
    def msg(uuid, parent, sender, text):
        return {"uuid": uuid, "parent_message_uuid": parent, "sender": sender,
                "text": text, "content": [{"type": "text", "text": text}],
                "created_at": "2026-05-20T12:26:46.475253Z"}
    return {"uuid": "3e726c42-x", "name": "Demo Chat",
            "created_at": "2026-05-20T12:00:00Z",
            "chat_messages": [
                msg("m0", None, "human", "first question?"),
                msg("m1", "m0", "assistant", "an answer\n```python\nx=1\n```"),
                msg("m2", "m1", "human", "second?"),
                msg("m3", "m2", "assistant", "second answer")]}


def test_linear_chat_from_chat_messages():
    raw = claude._raw_chat(_conv())
    assert raw.id == "3e726c42-x" and raw.title == "Demo Chat"
    assert raw.source == "claude:export" and raw.models == ["claude"]
    m = linearize(raw)
    assert len(m.exchanges) == 2
    assert m.exchanges[0].query.content == "first question?"
    assert "```python" in m.exchanges[0].answer.content
    assert m.exchanges[0].query.role == "user"          # 'human' → 'user'


def test_detect_and_load_export():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump([_conv()], f)
        path = f.name
    try:
        assert claude.is_claude_export(path)
        raw = claude.load_export(path)                  # single conv → no id
        assert raw.id == "3e726c42-x"
        assert claude.load_export(path, chat_id="3e726c42").id == "3e726c42-x"
    finally:
        Path(path).unlink()


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} passed")


if __name__ == "__main__":
    _run()
