"""DeepSeek encoder tests (share + bulk shapes).

Run: PYTHONPATH=src python3 tests/test_deepseek.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatdrill.passes.linearize import linearize          # noqa: E402
from chatdrill.sources import deepseek                     # noqa: E402

SHARE = {"code": 0, "data": {"biz_data": {"title": "Demo", "model_type": "expert",
    "messages": [
        {"message_id": 1, "parent_id": None, "role": "USER", "inserted_at": 1782292225.5,
         "fragments": [{"type": "REQUEST", "content": "the question?"}]},
        {"message_id": 2, "parent_id": 1, "role": "ASSISTANT", "inserted_at": 1782292230.0,
         "fragments": [{"type": "THINK", "content": "secret reasoning"},
                       {"type": "RESPONSE", "content": "answer\n```py\nx=1\n```"}]}]}}}

BULK = [{"id": "c1", "title": "Bulk", "inserted_at": "2025-01-28T18:16:35.828000+08:00",
    "mapping": {
        "n0": {"id": "n0", "parent": None, "children": ["n1"],
               "message": {"model": "deepseek", "inserted_at": "2025-01-28T18:16:35Z",
                           "fragments": [{"type": "REQUEST", "content": "hi?"}]}},
        "n1": {"id": "n1", "parent": "n0", "children": [],
               "message": {"fragments": [{"type": "RESPONSE", "content": "hello there"}]}}}}]


def test_share_shape_roles_and_think_dropped():
    raw = deepseek._raw_chat_share(SHARE["data"]["biz_data"], "dsk_x")
    m = linearize(raw)
    assert len(m.exchanges) == 1
    e = m.exchanges[0]
    assert e.query.content == "the question?"
    assert "```py" in e.answer.content
    assert "secret reasoning" not in e.answer.content      # THINK dropped
    assert e.query.role == "user" and e.answer.role == "assistant"


def test_bulk_shape_role_inferred_and_iso_ts():
    raw = deepseek._raw_chat_mapping(BULK[0])
    assert raw.created_at and raw.created_at > 1_700_000_000   # ISO parsed
    m = linearize(raw)
    assert len(m.exchanges) == 1
    assert m.exchanges[0].query.content == "hi?"             # REQUEST → user
    assert m.exchanges[0].answer.content == "hello there"    # RESPONSE → assistant


def test_detection():
    import json, tempfile, os
    for obj, kind in [(SHARE, "share"), (BULK, "bulk")]:
        fd, p = tempfile.mkstemp(suffix=".json"); os.close(fd)
        Path(p).write_text(json.dumps(obj))
        try:
            assert deepseek.is_deepseek_export(p), kind
            raw = next(deepseek.iter_export(p))
            assert raw.source == "deepseek:export"
        finally:
            os.unlink(p)


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} passed")


if __name__ == "__main__":
    _run()
