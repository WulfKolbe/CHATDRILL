"""TiddlyWiki projector tests — bibkey, native-markdown rendering, tags, integrity.

Run: PYTHONPATH=src python3 tests/test_tiddlers.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatdrill.models import ChatModel, Exchange, Turn          # noqa: E402
from chatdrill.passes.artifacts import extract_artifacts        # noqa: E402
from chatdrill.passes.segment import segment_model              # noqa: E402
from chatdrill.projectors.tiddlywiki import (                   # noqa: E402
    bibkey, build_tiddlers, tiddler_integrity, to_tid_text, _safe_filename)


def _model(source="perplexity:export"):
    q = Turn(id="u1", role="user", index=0, content="how to plot in python?", timestamp=0)
    a = Turn(id="a1", role="assistant", index=1, model_name="sonar", timestamp=12,
             content=("Use matplotlib [1].\n"
                      "```python\nimport matplotlib.pyplot as plt\nplt.plot(x)  # x={1}}\n```\n"
                      "The energy is \\(E=mc^2\\).\n\n"
                      "Sources:\n- https://matplotlib.org\n"))
    return segment_model(extract_artifacts(ChatModel(
        id="abc12345-z", title="Plotting Help", source=source, models=["sonar"],
        created_at=1696325104,                       # 2023-10-03
        exchanges=[Exchange(id="ex_0000", index=0, query=q, answer=a, model="sonar",
                            asked_at=0, answered_at=12)])))


def test_bibkey_provider_date_title():
    assert bibkey(_model()) == "Pplx20231003_PlottingHelp"
    m = _model(); m.title = "New chat"
    assert bibkey(m).startswith("Pplx20231003_")


def test_native_markdown_references():
    tids = build_tiddlers(_model())
    by = {t["title"]: t for t in tids}
    bk = bibkey(_model())
    ex = by[f"{bk}_EX0000"]["text"]
    assert f"{{{{{bk}_CODE000}}}}" in ex                # code → PLAIN {{title}} transclusion
    assert "||CODE" not in ex and "||FO" not in ex      # no field-based templates
    assert "$E=mc^2$" in ex                             # \(...\) normalized to inline $
    assert "[\\[1\\]](https://matplotlib.org)" in ex    # [1] → markdown citation link
    # the code tiddler holds the code as a fenced BLOCK in its text (not a field)
    code = by[f"{bk}_CODE000"]
    assert code["text"].startswith("```python\n") and "code" not in code  # no `code` field
    assert "x={1}}" in code["text"]                     # `}}` inside code is intact


def test_no_templates_preamble_present():
    titles = {t["title"] for t in build_tiddlers(_model())}
    assert {"CODE", "FO", "EQ", "URL", "CIT"} & titles == set()   # templates gone
    assert f"{bibkey(_model())}_preamble" in titles


def test_everything_is_markdown():
    tids = build_tiddlers(_model())
    assert {t["type"] for t in tids} == {"text/markdown"}
    by = {t["title"]: t for t in tids}
    assert by[f"{bibkey(_model())}_EX0000"]["text"].startswith("## Question")


def test_integrity_no_dangling():
    integ = tiddler_integrity(build_tiddlers(_model()))
    assert integ["transclusions"] > 0
    assert integ["dangling"] == []                     # every {{title}} target exists


def test_tid_serialization():
    t = build_tiddlers(_model())[0]
    text = to_tid_text(t)
    assert "title: " in text and "tags: " in text
    assert _safe_filename("Pplx_x_EX0000") == "Pplx_x_EX0000.tid"


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} passed")


if __name__ == "__main__":
    _run()
