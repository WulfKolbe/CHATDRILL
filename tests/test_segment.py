"""pass03 (segment) + pass04 (artifacts) tests.

Run: PYTHONPATH=src python3 tests/test_segment.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatdrill.models import ChatModel, Exchange, Turn      # noqa: E402
from chatdrill.passes.artifacts import extract_artifacts    # noqa: E402
from chatdrill.passes.segment import segment_text, segment_model  # noqa: E402


def test_fenced_code_block():
    segs = segment_text("intro line\n```python\nx = 1\nprint(x)\n```\nafter")
    kinds = [(s.kind, s.lang, s.fenced) for s in segs]
    assert ("code", "python", True) in kinds
    code = [s for s in segs if s.kind == "code"][0]
    assert code.text == "x = 1\nprint(x)"
    assert segs[0].kind == "prose" and segs[-1].kind == "prose"


def test_stripped_fence_language_token():
    # the real OpenWebUI/Perplexity shape: lone "typescript" then code, no ```
    text = ("Each module follows a shared contract:\n"
            "typescript\n"
            "interface CSPObjectModule<TInput, TOutput> {\n"
            "  processObjects(data: TInput[]): Promise<TOutput[]>;\n"
            "}\n"
            "This generalization allows uniform chaining of modules.")
    segs = segment_text(text)
    code = [s for s in segs if s.kind == "code"]
    assert len(code) == 1
    assert code[0].lang == "typescript" and code[0].fenced is False
    assert "interface CSPObjectModule" in code[0].text
    assert "This generalization" not in code[0].text   # stopped at the prose sentence


def test_bare_language_word_in_prose_is_not_code():
    # "python" as a lone line but followed by a prose sentence → NOT a code block
    segs = segment_text("I like\npython\nIt is a nice readable language to use.")
    assert all(s.kind == "prose" for s in segs)


def test_artifacts_code_url_error():
    ans = Turn(id="a1", role="assistant", index=1, content=(
        "See https://example.com/docs for details.\n"
        "```python\nimport os\nos.listdir('.')\n```\n"
        "It failed:\nTraceback (most recent call last):\n"
        "  File 'x.py', line 1\nValueError: bad input\n\n"
        "done."))
    q = Turn(id="u1", role="user", index=0, content="how do I list files?")
    model = ChatModel(id="c1", exchanges=[
        Exchange(id="ex_0000", index=0, query=q, answer=ans)])
    segment_model(model)
    extract_artifacts(model)
    kinds = {a.kind for a in model.artifacts}
    assert kinds == {"code", "url", "error"}
    code = [a for a in model.artifacts if a.kind == "code"][0]
    assert code.lang == "python" and code.line_count == 2 and code.sha1
    url = [a for a in model.artifacts if a.kind == "url"][0]
    assert url.content == "https://example.com/docs"     # trailing punctuation handled
    errs = [a for a in model.artifacts if a.kind == "error"]
    assert any("Traceback" in e.content for e in errs)


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} passed")


if __name__ == "__main__":
    _run()
