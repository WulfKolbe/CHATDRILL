"""pass14 (reverse-time fold) tests.

Run: PYTHONPATH=src python3 tests/test_reverse_time.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatdrill.models import ChatModel, Exchange, Turn          # noqa: E402
from chatdrill.passes.artifacts import extract_artifacts        # noqa: E402
from chatdrill.passes.reverse_time import fold, _identity       # noqa: E402
from chatdrill.passes.segment import segment_model              # noqa: E402


def _ex(i, q, a=None, model="m"):
    qt = Turn(id=f"u{i}", role="user", index=2 * i, content=q)
    at = Turn(id=f"a{i}", role="assistant", index=2 * i + 1, content=a,
              model_name=model) if a is not None else None
    return Exchange(id=f"ex_{i:04d}", index=i, query=qt, answer=at,
                    model=model if a else None)


def _build(exchanges):
    return extract_artifacts(segment_model(ChatModel(id="c1", exchanges=exchanges)))


def test_same_symbol_collapses_to_latest():
    # the same class `Parser` defined three times across the chat → 1 canonical (last)
    v1 = "```python\nclass Parser:\n    def run(self): return 1\n```"
    v2 = "```python\nclass Parser:\n    def run(self): return 2\n```"
    v3 = "```python\nclass Parser:\n    def run(self): return 3  # final\n```"
    m = _build([_ex(0, "draft?", v1), _ex(1, "again?", v2), _ex(2, "final?", v3)])
    fold(m)
    code = m.results.artifacts
    assert len(code) == 1
    ca = code[0]
    assert ca.revisions == 3 and len(ca.superseded) == 2
    assert "return 3" in ca.content            # canonical = the LATEST (exchange 2)
    assert ca.exchange_index == 2
    assert ca.identity.startswith("sig:python:Parser")


def test_filename_identity_wins():
    a = "```python\n# loader.py\nx = 1\n```"
    b = "```python\n# loader.py\nx = 2\n```"
    m = _build([_ex(0, "v1", a), _ex(1, "v2", b)])
    fold(m)
    assert len(m.results.artifacts) == 1
    assert m.results.artifacts[0].identity == "file:loader.py"
    assert "x = 2" in m.results.artifacts[0].content


def test_distinct_oneoffs_stay_separate_and_newest_first():
    a = "```bash\nls -la\n```"
    b = "```json\n{\"a\": 1}\n```"
    m = _build([_ex(0, "x", a), _ex(1, "y", b)])
    fold(m)
    arts = m.results.artifacts
    assert len(arts) == 2
    assert arts[0].exchange_index == 1 and arts[1].exchange_index == 0   # newest first


def test_unresolved_questions_collected():
    m = _build([_ex(0, "answered?", "```py\nok\n```"), _ex(1, "dangling question?")])
    fold(m)
    assert [u.exchange_index for u in m.results.unresolved] == [1]
    assert "dangling" in m.results.unresolved[0].text


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} passed")


if __name__ == "__main__":
    _run()
