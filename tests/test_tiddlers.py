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


def test_code_stored_raw_with_language_type():
    bk = bibkey(_model())
    by = {t["title"]: t for t in build_tiddlers(_model())}
    code = by[f"{bk}_CODE000"]
    # RAW code in TEXT (no ``` fence, no `code` field), type = the language MIME
    assert code["type"] == "text/x-python"
    assert code["text"].startswith("import matplotlib") and "```" not in code["text"]
    assert "x={1}}" in code["text"]                     # `}}` inside code is intact
    assert "code" not in code                            # never a field
    # metadata + a git/svn-style comment live in FIELDS
    assert code["lang"] == "python" and int(code["lines"]) >= 1 and code["sha1"]
    assert code["caption"] and code["comment"].startswith("ex0 ·")


def test_exchange_uses_coderef_and_normalizes_math():
    bk = bibkey(_model())
    by = {t["title"]: t for t in build_tiddlers(_model())}
    ex = by[f"{bk}_EX0000"]["text"]
    assert f"{{{{{bk}_CODE000||CODEREF}}}}" in ex        # compact link+desc reference
    assert "$E=mc^2$" in ex                              # \(...\) → inline $
    assert "[\\[1\\]](https://matplotlib.org)" in ex     # [1] → markdown citation link


def test_coderef_template_present_others_gone():
    titles = {t["title"] for t in build_tiddlers(_model())}
    assert "CODEREF" in titles                           # the one reference template
    assert {"CODE", "FO", "EQ", "URL", "CIT"} & titles == set()
    assert f"{bibkey(_model())}_preamble" in titles


def test_comment_field_on_every_kind():
    bk = bibkey(_model())
    by = {t["title"]: t for t in build_tiddlers(_model())}
    assert by[bk]["comment"]                              # chat root
    assert by[f"{bk}_EX0000"]["comment"].startswith("ex0 ·")   # exchange
    assert by[f"{bk}_CODE000"]["comment"]                # code
    # prose tiddlers stay markdown; code carries its language MIME
    assert by[f"{bk}_EX0000"]["type"] == "text/markdown"


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
