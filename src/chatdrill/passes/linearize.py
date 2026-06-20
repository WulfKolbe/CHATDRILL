"""pass02 — reduce a RawChat tree to the canonical Exchange[] + forgotten branches.

The canonical path is root → ``current_id`` (walked up via parent_id, which is
robust even when childrenIds ordering is unreliable). Consecutive turns on that
path are paired into Exchanges: each user turn opens an exchange; the next
assistant turn closes it. Any branch point on the path with off-path children
yields ForgottenBranch entries, and contributes regen_count to the exchange
whose answer sits at that branch.

See docs/CHATDRILL_DESIGN.md §1 (pass02) and §2.
"""
from __future__ import annotations

from ..models import ChatModel, Exchange, ForgottenBranch, RawChat, Turn


def _current_path(chat: RawChat) -> list[str]:
    """Ordered message ids root → current_id, via parent_id back-walk."""
    tree = chat.tree
    leaf = chat.current_id
    if leaf is None or leaf not in tree:
        # fall back to the deepest reachable leaf from a root
        leaf = _fallback_leaf(chat)
        if leaf is None:
            return []
    path: list[str] = []
    seen: set[str] = set()
    cur = leaf
    while cur is not None and cur in tree and cur not in seen:
        seen.add(cur)
        path.append(cur)
        cur = tree[cur].parent_id
    path.reverse()
    return path


def _fallback_leaf(chat: RawChat) -> str | None:
    """Deepest node from any root — used when current_id is missing/dangling."""
    tree = chat.tree
    roots = [mid for mid, m in tree.items() if not m.parent_id or m.parent_id not in tree]
    best, best_depth = None, -1

    def depth(mid: str, d: int, seen: set[str]) -> None:
        nonlocal best, best_depth
        if mid in seen:
            return
        seen.add(mid)
        if d > best_depth:
            best, best_depth = mid, d
        for c in tree[mid].children_ids:
            if c in tree:
                depth(c, d + 1, seen)

    for r in roots:
        depth(r, 0, set())
    return best


def _turn(chat: RawChat, mid: str, index: int, on_path: bool) -> Turn:
    m = chat.tree[mid]
    return Turn(
        id=m.id, role=m.role, index=index, content=m.content,
        timestamp=m.timestamp, model_name=m.model_name, on_current_path=on_path,
    )


def _collect_branch(chat: RawChat, root: str) -> list[Turn]:
    """Every turn in the off-path subtree rooted at `root` (pre-order)."""
    turns: list[Turn] = []
    seen: set[str] = set()

    def walk(mid: str, idx: int) -> None:
        if mid in seen or mid not in chat.tree:
            return
        seen.add(mid)
        turns.append(_turn(chat, mid, idx, on_path=False))
        for c in chat.tree[mid].children_ids:
            walk(c, idx + 1)

    walk(root, 0)
    return turns


def linearize(chat: RawChat) -> ChatModel:
    """RawChat → ChatModel{exchanges, forgotten_branches}."""
    path = _current_path(chat)
    path_set = set(path)

    # forgotten branches: off-path children of any node on the path
    branches: list[ForgottenBranch] = []
    for mid in path:
        for c in chat.tree[mid].children_ids:
            if c not in path_set and c in chat.tree:
                branches.append(ForgottenBranch(
                    root_turn_id=c, turns=_collect_branch(chat, c),
                    reason="regenerate"))

    # pair turns on the path into exchanges
    exchanges: list[Exchange] = []
    turns = [_turn(chat, mid, i, on_path=True) for i, mid in enumerate(path)]
    i, ex_index = 0, 0
    n = len(turns)
    while i < n:
        t = turns[i]
        if t.role != "user":
            i += 1                            # skip leading system/assistant noise
            continue
        answer = None
        if i + 1 < n and turns[i + 1].role == "assistant":
            answer = turns[i + 1]
        # regen_count = # assistant children of the user turn (contested answer)
        regen = sum(1 for c in chat.tree[t.id].children_ids
                    if c in chat.tree and chat.tree[c].role == "assistant") or 1
        exchanges.append(Exchange(
            id=f"ex_{ex_index:04d}", index=ex_index, query=t, answer=answer,
            on_current_path=True,
            model=answer.model_name if answer else None,
            asked_at=t.timestamp,
            answered_at=answer.timestamp if answer else None,
            regen_count=regen,
        ))
        ex_index += 1
        i += 2 if answer else 1

    return ChatModel(
        id=chat.id, title=chat.title, source=chat.source, models=chat.models,
        created_at=chat.created_at, exchanges=exchanges,
        forgotten_branches=branches,
    )
