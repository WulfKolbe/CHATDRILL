"""Perplexity export encoder tests.  Run: PYTHONPATH=src python3 tests/test_perplexity.py"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatdrill.passes.linearize import linearize          # noqa: E402
from chatdrill.sources import perplexity                  # noqa: E402


def _body():
    def step_text(q, a, url):
        return json.dumps([
            {"step_type": "INITIAL_QUERY", "content": {"query": q}},
            {"step_type": "FINAL", "content": {"answer": json.dumps({
                "structured_answer": [{"type": "markdown", "text": a}],
                "web_results": [{"name": "S", "url": url}]})}}])
    return {
        "id": "t1",
        "thread_metadata": {"title": "Demo", "created_at": "2024-10-03T08:45:04Z"},
        "entries": [
            {"display_model": "turbo", "text": step_text("first?", "ans **one**", "https://a.com")},
            {"display_model": "sonar", "text": step_text("second?", "ans two", "https://b.com")},
        ]}


def test_thread_becomes_linear_chat():
    raw = perplexity._raw_chat("slug-xyz", _body())
    assert raw.id == "t1" and raw.title == "Demo" and raw.source == "perplexity:export"
    assert sorted(raw.models) == ["sonar", "turbo"]
    m = linearize(raw)
    assert len(m.exchanges) == 2
    e0 = m.exchanges[0]
    assert e0.query.content == "first?" and "ans **one**" in e0.answer.content
    assert "https://a.com" in e0.answer.content          # source appended
    assert e0.model == "turbo"
    assert m.exchanges[1].query.content == "second?" and m.exchanges[1].model == "sonar"


def test_load_export_by_id_and_detect():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"slug-xyz": _body()}, f)
        path = f.name
    try:
        assert perplexity.is_perplexity_export(path)
        raw = perplexity.load_export(path)               # single thread → no id needed
        assert raw.id == "t1"
        raw2 = perplexity.load_export(path, chat_id="t1")
        assert raw2.id == "t1"
    finally:
        Path(path).unlink()


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} passed")


if __name__ == "__main__":
    _run()
