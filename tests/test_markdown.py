"""`md` renderer tests.  Run: PYTHONPATH=src python3 tests/test_markdown.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatdrill.models import ChatModel, Exchange, Turn          # noqa: E402
from chatdrill.projectors.markdown import render_chat_markdown      # noqa: E402
from chatdrill.passes.segment import segment_model              # noqa: E402


def _model():
    q = Turn(id="u1", role="user", index=0, content="how do I list files?",
             timestamp=0)
    a = Turn(id="a1", role="assistant", index=1, model_name="gpt-4o", timestamp=9,
             content="Use this:\npython\nimport os\nos.listdir('.')\n\nThat is all.")
    return segment_model(ChatModel(id="abc12345-x", title="Files", models=["gpt-4o"],
                                   exchanges=[Exchange(id="ex_0000", index=0, query=q,
                                                       answer=a, model="gpt-4o",
                                                       asked_at=0, answered_at=9)]))


def test_structure_and_refencing():
    md = render_chat_markdown(_model())
    assert md.startswith("# Files")
    assert "## Q0" in md
    assert "### Answer — gpt-4o (9s)" in md
    assert "```python\nimport os" in md           # stripped fence recovered + re-fenced
    assert md.count("---") >= 1                    # exchange separator


def test_unanswered_renders_placeholder():
    q = Turn(id="u1", role="user", index=0, content="pending?")
    m = ChatModel(id="z", exchanges=[Exchange(id="ex_0000", index=0, query=q)])
    md = render_chat_markdown(m)
    assert "_(no answer)_" in md


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} passed")


if __name__ == "__main__":
    _run()
