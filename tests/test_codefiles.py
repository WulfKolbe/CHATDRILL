"""Explo `!!! path/file` splitter + provider registry tests.

Run: PYTHONPATH=src python3 tests/test_codefiles.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chatdrill.models import ChatModel, Exchange, Turn          # noqa: E402
from chatdrill.passes.codefiles import split_explo, extract_virtual_files  # noqa: E402
from chatdrill.sources import registry                          # noqa: E402


def test_split_two_files_with_and_without_fence():
    text = (
        "Here is the code:\n"
        "!!! src/csp.ts\n"
        "```typescript\nexport class CSP {}\n```\n"
        "!!! README.md\n"
        "# Title\nsome prose\n")
    files = split_explo(text)
    assert [p for p, _, _ in files] == ["src/csp.ts", "README.md"]
    assert files[0][1] == "typescript"
    assert files[0][2] == "export class CSP {}"        # fence stripped
    assert files[1][1] == "markdown"
    assert "# Title" in files[1][2]


def test_latest_version_per_path_wins():
    def ex(i, content):
        q = Turn(id=f"u{i}", role="user", index=2 * i, content="here")
        a = Turn(id=f"a{i}", role="assistant", index=2 * i + 1, content=content)
        return Exchange(id=f"ex_{i:04d}", index=i, query=q, answer=a)

    m = ChatModel(id="c1", exchanges=[
        ex(0, "!!! app.py\nx = 1\n"),
        ex(1, "!!! app.py\nx = 2  # newer\n"),
    ])
    extract_virtual_files(m)
    assert len(m.virtual_files) == 1
    vf = m.virtual_files[0]
    assert vf.path == "app.py" and vf.lang == "python"
    assert "x = 2" in vf.content and vf.revisions == 2 and len(vf.superseded) == 1
    assert vf.exchange_index == 1                      # the latest


def test_no_headers_yields_nothing():
    assert split_explo("just prose, no headers here.\nand a line.") == []


def test_registry_known_and_awaiting():
    # local chat-id → openwebui encoder
    src = registry.for_ref("d2d8e37c")
    assert src.name == "openwebui"
    # a perplexity URL → precise awaiting message (encoder not built yet)
    try:
        registry.for_ref("https://www.perplexity.ai/search/abc-123")
        assert False, "should have raised"
    except NotImplementedError as e:
        assert "perplexity" in str(e)
    # chatgpt + perplexity are export-implemented; kimi/zai/deepseek await samples
    assert {"chatgpt", "perplexity"} & set(registry.awaiting()) == set()
    assert {"kimi", "zai", "deepseek"} <= set(registry.awaiting())


def test_parse_url_link_structures():
    cases = {
        "https://chatgpt.com/c/6a3b8a1f-0f30-83eb-b19d-a4fecf9ddb05":
            ("chatgpt", "6a3b8a1f-0f30-83eb-b19d-a4fecf9ddb05"),
        "https://www.kimi.com/chat/19eeffa8-9422-87d1-8000-094978712354?x=1":
            ("kimi", "19eeffa8-9422-87d1-8000-094978712354"),
        "https://chat.z.ai/c/cbbfe8d3-3dcb-4557-86a8-e516deef0f0e":
            ("zai", "cbbfe8d3-3dcb-4557-86a8-e516deef0f0e"),
        "https://chat.deepseek.com/a/chat/s/acebc758-b3a9-4f40-979d-9636de61bc1f":
            ("deepseek", "acebc758-b3a9-4f40-979d-9636de61bc1f"),
    }
    for url, (prov, cid) in cases.items():
        p, c = registry.parse_url(url)
        assert p.name == prov and c == cid, (url, p.name, c)


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} passed")


if __name__ == "__main__":
    _run()
