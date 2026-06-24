"""docmodel export tests.  Run: PYTHONPATH=src python3 tests/test_docmodel.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatdrill.models import ChatModel, Exchange, Turn          # noqa: E402
from chatdrill.passes.artifacts import extract_artifacts        # noqa: E402
from chatdrill.passes.docmodel_export import to_document        # noqa: E402
from chatdrill.passes.reverse_time import fold                  # noqa: E402
from chatdrill.passes.segment import segment_model              # noqa: E402


def _model():
    def ex(i, q, a):
        qt = Turn(id=f"u{i}", role="user", index=2 * i, content=q)
        at = Turn(id=f"a{i}", role="assistant", index=2 * i + 1, content=a,
                  model_name="gpt-4o")
        return Exchange(id=f"ex_{i:04d}", index=i, query=qt, answer=at, model="gpt-4o")
    m = ChatModel(id="c1", title="T", source="openwebui:webui.db", models=["gpt-4o"],
                  exchanges=[
                      ex(0, "draft?", "```python\nclass P:\n  def r(self): return 1\n```"),
                      ex(1, "final?", "```python\nclass P:\n  def r(self): return 2\n```"),
                  ])
    return fold(extract_artifacts(segment_model(m)))


def test_strata_and_objects():
    doc = to_document(_model())
    assert set(doc) == {"meta", "streams", "objects", "alignments"}
    assert doc["meta"]["chat_id"] == "c1"
    types = {o["type"] for o in doc["objects"]}
    assert {"Exchange", "CodeBlock"} <= types
    # 2 exchanges + 2 code blocks
    assert sum(o["type"] == "Exchange" for o in doc["objects"]) == 2
    assert sum(o["type"] == "CodeBlock" for o in doc["objects"]) == 2


def test_realizations_resolve_to_stream_anchors():
    doc = to_document(_model())
    anchors = set(doc["streams"]["turns"]["anchors"])
    assert anchors and set(doc["streams"]["turns"]["payload"]) == anchors
    for o in doc["objects"]:
        for r in o["realizations"]:
            assert r["stream"] == "turns"
            assert r["start"] in anchors and r["end"] in anchors   # no dangling refs


def test_supersedes_alignment_from_reverse_time():
    doc = to_document(_model())
    sup = [a for a in doc["alignments"] if a["kind"] == "supersedes"]
    assert sup, "the two `class P` drafts should yield a supersedes alignment"
    a = sup[0]
    anchors = set(doc["streams"]["turns"]["anchors"])
    assert a["left"]["start"] in anchors and a["right"]["start"] in anchors


def test_code_objects_are_children_of_their_exchange():
    doc = to_document(_model())
    by_id = {o["id"]: o for o in doc["objects"]}
    for o in doc["objects"]:
        if o["type"] == "CodeBlock":
            assert o["parent"] in by_id
            assert o["id"] in by_id[o["parent"]]["children"]


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} passed")


if __name__ == "__main__":
    _run()
