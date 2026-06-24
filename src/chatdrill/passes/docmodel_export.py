"""Project a ChatModel into a PDFDRILL-compatible docmodel Document (dict form).

This is the integration seam: the output is exactly the meta/streams/objects/
alignments JSON that PDFDRILL's `docmodel.core.Document.from_dict` round-trips, so
CHATDRILL chats become docmodel Documents that PDFDRILL projectors can read.

Mapping (see docs/DOCMODEL_ALIGNMENT.md):
  stream `turns`  — anchors = messages, payload = {role,text,timestamp,model,...}
  Exchange        — realization range (query→answer) over `turns`
  CodeBlock/Url/Error — realization into the turn anchor, child of its Exchange
  VirtualFile     — synthesized file object (+ supersedes alignments)
  supersedes      — reverse-time lineage (canonical ↔ each older turn)
"""
from __future__ import annotations

from ..models import ChatModel

_ARTIFACT_TYPE = {"code": "CodeBlock", "url": "Url", "error": "Error"}


def _realization(stream, start, end=None, role="surface", props=None, prov=""):
    r = {"stream": stream, "start": start, "end": end or start, "role": role,
         "props": props or {}}
    if prov:
        r["provenance"] = prov
    return r


def _range(stream, anchor):
    return {"stream": stream, "start": anchor, "end": anchor}


def to_document(model: ChatModel) -> dict:
    """ChatModel → docmodel dict (meta/streams/objects/alignments)."""
    anchors: list[str] = []
    payload: dict[str, dict] = {}
    anchor_of: dict[str, str] = {}            # turn.id → anchor id

    for ex in model.exchanges:
        for turn in (ex.query, ex.answer):
            if turn is None:
                continue
            aid = f"a_{turn.id}"
            if aid in payload:
                continue
            anchors.append(aid)
            payload[aid] = {"role": turn.role, "text": turn.content,
                            "timestamp": turn.timestamp, "model": turn.model_name,
                            "exchange_index": ex.index}
            anchor_of[turn.id] = aid

    objects: list[dict] = []
    alignments: list[dict] = []
    by_id: dict[str, dict] = {}
    ex_obj: dict[int, str] = {}

    # Exchange objects
    for ex in model.exchanges:
        qa = anchor_of.get(ex.query.id)
        aa = anchor_of.get(ex.answer.id) if ex.answer else qa
        oid = f"obj_ex_{ex.index:04d}"
        ex_obj[ex.index] = oid
        obj = {"id": oid, "type": "Exchange",
               "props": {"index": ex.index, "model": ex.model,
                         "asked_at": ex.asked_at, "answered_at": ex.answered_at,
                         "regen_count": ex.regen_count, "answered": ex.answered},
               "realizations": [_realization("turns", qa, aa, "surface",
                                             prov=model.source)],
               "children": [], "parent": None}
        objects.append(obj)
        by_id[oid] = obj

    # CodeBlock / Url / Error objects (children of their Exchange)
    for i, a in enumerate(model.artifacts):
        aid = anchor_of.get(a.turn_id)
        if aid is None:
            continue
        oid = f"obj_{a.kind}_{i:04d}"
        props = {"role_in_turn": a.role}
        if a.kind == "code":
            props.update({"lang": a.lang, "sha1": a.sha1,
                          "line_count": a.line_count, "fenced": a.fenced,
                          "content": a.content})
        else:
            props["value"] = a.content
        parent = ex_obj.get(a.exchange_index)
        objects.append({"id": oid, "type": _ARTIFACT_TYPE[a.kind], "props": props,
                        "realizations": [_realization("turns", aid, aid, a.kind,
                                                      prov="pass04")],
                        "children": [], "parent": parent})
        if parent in by_id:
            by_id[parent]["children"].append(oid)

    # VirtualFile objects + supersedes alignments
    for i, vf in enumerate(model.virtual_files):
        aid = anchor_of.get(vf.latest_turn_id)
        oid = f"obj_file_{i:04d}"
        objects.append({"id": oid, "type": "VirtualFile",
                        "props": {"path": vf.path, "lang": vf.lang,
                                  "revisions": vf.revisions, "sha1": vf.sha1,
                                  "content": vf.content},
                        "realizations": ([_realization("turns", aid, aid, "file",
                                                        prov="explo")] if aid else []),
                        "children": [], "parent": None})
        for older in vf.superseded:
            oa = anchor_of.get(older)
            if aid and oa:
                alignments.append({"kind": "supersedes", "left": _range("turns", aid),
                                   "right": _range("turns", oa),
                                   "props": {"path": vf.path, "object": oid}})

    # reverse-time canonical code → supersedes alignments
    if model.results:
        for ca in model.results.artifacts:
            la = anchor_of.get(ca.latest_turn_id)
            for older in ca.superseded:
                oa = anchor_of.get(older)
                if la and oa:
                    alignments.append({"kind": "supersedes", "left": _range("turns", la),
                                       "right": _range("turns", oa),
                                       "props": {"identity": ca.identity}})

    return {
        "meta": {"source": model.source, "chat_id": model.id, "title": model.title,
                 "models": model.models, "exchange_count": len(model.exchanges)},
        "streams": {"turns": {"name": "turns", "anchors": anchors, "payload": payload}},
        "objects": objects,
        "alignments": alignments,
    }


def object_counts(doc: dict) -> dict:
    counts: dict[str, int] = {}
    for o in doc["objects"]:
        counts[o["type"]] = counts.get(o["type"], 0) + 1
    return counts
