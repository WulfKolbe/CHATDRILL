"""pass02 (linearize) unit tests — synthetic trees, no DB needed.

Run: PYTHONPATH=src python3 -m pytest tests/ -q
 or: PYTHONPATH=src python3 tests/test_linearize.py   (stdlib fallback runner)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatdrill.models import RawChat, RawMessage          # noqa: E402
from chatdrill.passes.linearize import linearize          # noqa: E402


def _msg(mid, parent, children, role, ts=0, model=None):
    return RawMessage(id=mid, parent_id=parent, children_ids=children,
                      role=role, content=f"{role}:{mid}", timestamp=ts,
                      model_name=model)


def _chat(tree, current):
    return RawChat(id="c1", title="t", source="test",
                   tree={m.id: m for m in tree}, current_id=current)


def test_linear_two_pairs():
    chat = _chat([
        _msg("u1", None, ["a1"], "user", 10),
        _msg("a1", "u1", ["u2"], "assistant", 12, "gpt-4o"),
        _msg("u2", "a1", ["a2"], "user", 20),
        _msg("a2", "u2", [], "assistant", 25, "gpt-4o"),
    ], current="a2")
    m = linearize(chat)
    assert len(m.exchanges) == 2
    e0 = m.exchanges[0]
    assert e0.query.id == "u1" and e0.answer.id == "a1"
    assert e0.answered and e0.model == "gpt-4o"
    assert e0.latency_ms == 2000              # (12-10)*1000
    assert m.exchanges[1].query.id == "u2" and m.exchanges[1].answer.id == "a2"
    assert m.forgotten_branches == []


def test_unanswered_trailing_question():
    chat = _chat([
        _msg("u1", None, ["a1"], "user", 1),
        _msg("a1", "u1", ["u2"], "assistant", 2),
        _msg("u2", "a1", [], "user", 3),       # no answer yet
    ], current="u2")
    m = linearize(chat)
    assert len(m.exchanges) == 2
    assert m.exchanges[1].answer is None and not m.exchanges[1].answered


def test_branch_becomes_forgotten_and_regen_count():
    # u1 has TWO assistant children (a regen); current path goes through a1b.
    chat = _chat([
        _msg("u1", None, ["a1a", "a1b"], "user", 1),
        _msg("a1a", "u1", [], "assistant", 2, "old"),     # abandoned
        _msg("a1b", "u1", [], "assistant", 3, "new"),     # current
    ], current="a1b")
    m = linearize(chat)
    assert len(m.exchanges) == 1
    e = m.exchanges[0]
    assert e.answer.id == "a1b" and e.model == "new"
    assert e.regen_count == 2                  # two assistant children
    assert len(m.forgotten_branches) == 1
    assert m.forgotten_branches[0].root_turn_id == "a1a"


def test_dangling_current_id_falls_back_to_deepest():
    chat = _chat([
        _msg("u1", None, ["a1"], "user", 1),
        _msg("a1", "u1", [], "assistant", 2),
    ], current="does-not-exist")
    m = linearize(chat)
    assert len(m.exchanges) == 1 and m.exchanges[0].answer.id == "a1"


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} passed")


if __name__ == "__main__":
    _run()
