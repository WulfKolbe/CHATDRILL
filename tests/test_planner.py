"""Sidecar + planner tests — isolated work dir under tmp/, no real db needed.

Run: PYTHONPATH=src python3 tests/test_planner.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatdrill import planner                              # noqa: E402
from chatdrill.sidecar import Sidecar                      # noqa: E402


def test_sidecar_roundtrip():
    work = tempfile.mkdtemp(prefix="cd_")
    try:
        sc = Sidecar("chatX", work=work)
        assert sc.facts == set() and sc.transitions == []
        sc.add_fact("MODEL_BUILT")
        sc.set_evidence("exchange_count", 7)
        sc.write_blob("chatmodel.json", '{"ok": true}')
        sc.log_transition("model", "INIT", "MODEL_BUILT", 12.3, "7 exchanges")
        sc.save()
        # reload from disk → state persisted
        sc2 = Sidecar("chatX", work=work)
        assert sc2.has("MODEL_BUILT")
        assert sc2.get_evidence("exchange_count") == 7
        assert sc2.has_blob("chatmodel.json")
        assert sc2.read_blob("chatmodel.json") == '{"ok": true}'
        assert len(sc2.transitions) == 1 and sc2.transitions[0]["to"] == "MODEL_BUILT"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_plan_orders_prereqs_deepest_first():
    requires = {"summary": ["model"], "tiddlers": ["summary"]}
    # nothing satisfied → full chain, target last
    assert planner.plan("tiddlers", requires, set()) == ["model", "summary", "tiddlers"]
    # model already done → it drops out, target still runs
    assert planner.plan("summary", requires, {"model"}) == ["summary"]


def test_done_when_detect_fact_and_model():
    work = tempfile.mkdtemp(prefix="cd_")
    try:
        sc = Sidecar("chatY", work=work)
        assert not planner.detect("fact:MODEL_BUILT", sc)
        assert not planner.detect("model", sc)
        sc.add_fact("MODEL_BUILT")
        sc.write_blob("chatmodel.json", "{}")
        sc.save()
        assert planner.detect("fact:MODEL_BUILT", sc)
        assert planner.detect("model", sc)              # artifact exists
        assert planner.detect("artifact:chatmodel.json", sc)
        assert not planner.detect("artifact:nope.json", sc)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_resolve_steps_uses_manifest():
    work = tempfile.mkdtemp(prefix="cd_")
    try:
        sc = Sidecar("chatZ", work=work)
        # summary requires model (per commands.yaml); model not built yet
        steps, sat = planner.resolve_steps("summary", sc)
        assert steps == ["model", "summary"] and "model" not in sat
        # build model → satisfied, prereq drops out
        sc.add_fact("MODEL_BUILT"); sc.save()
        steps2, sat2 = planner.resolve_steps("summary", sc)
        assert steps2 == ["summary"] and "model" in sat2
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} passed")


if __name__ == "__main__":
    _run()
