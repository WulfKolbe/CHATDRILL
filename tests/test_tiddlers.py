"""projC (tiddlers) tests.

Run: PYTHONPATH=src python3 tests/test_tiddlers.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatdrill.models import ChatModel, Exchange, Turn          # noqa: E402
from chatdrill.passes.artifacts import extract_artifacts        # noqa: E402
from chatdrill.passes.segment import segment_model              # noqa: E402
from chatdrill.passes.tiddlers import (                         # noqa: E402
    build_tiddlers, chat_key, to_tid_text, _safe_filename)


def _model():
    q = Turn(id="u1", role="user", index=0, content="how do I list files in python?")
    a = Turn(id="a1", role="assistant", index=1, content=(
        "Use os.listdir. See https://docs.python.org/3/library/os.html\n"
        "python\nimport os\nos.listdir('.')\n\nThat returns the names."),
        model_name="gpt-4o", timestamp=12)
    q.timestamp = 0
    m = ChatModel(id="abc12345-rest", title="List Files!", models=["gpt-4o"],
                  exchanges=[Exchange(id="ex_0000", index=0, query=q, answer=a,
                                      model="gpt-4o", asked_at=0, answered_at=12)])
    return extract_artifacts(segment_model(m))


def test_key_and_titles():
    m = _model()
    key = chat_key(m)
    assert key == "List-Files_abc12345"
    titles = {t["title"] for t in build_tiddlers(m)}
    assert key in titles                       # chat overview
    assert f"{key}_Q0" in titles               # exchange
    assert f"{key}_Code_0" in titles           # code


def test_code_is_refenced_even_when_stripped():
    m = _model()                               # source code had NO ``` fences
    code = [t for t in build_tiddlers(m) if t["title"].endswith("_Code_0")][0]
    assert code["text"].startswith("```python\n")    # re-fenced for TW rendering
    assert "import os" in code["text"]
    assert code["lang"] == "python"


def test_chat_tiddler_lists_links_and_urls():
    m = _model()
    chat = [t for t in build_tiddlers(m) if t["tags"] == "chatdrill chat"][0]
    assert "!! Exchanges" in chat["text"]
    assert "[[List-Files_abc12345_Q0]]" in chat["text"]
    assert "https://docs.python.org/3/library/os.html" in chat["text"]


def test_tid_serialization_roundtrips_fields():
    m = _model()
    t = build_tiddlers(m)[0]
    text = to_tid_text(t)
    head, _, body = text.partition("\n\n")
    assert "title: " in head and "tags: " in head
    assert body.strip()                        # has a body
    assert _safe_filename("List-Files_abc12345_Q0") == "List-Files_abc12345_Q0.tid"


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} passed")


if __name__ == "__main__":
    _run()
