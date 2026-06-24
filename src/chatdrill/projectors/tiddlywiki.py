"""TiddlyWikiProjector — project a ChatModel into tiddlers (PDFDRILL conventions).

Every non-prose element becomes a **templated transclusion** `{{title||TPL}}`
(exactly like PDFDRILL: `{{<bibkey>_FO0817||FO}}`), backed by template tiddlers:

  CODE  `<$codeblock code={{!!code}} language={{!!lang}}/>`
  FO    `<$latex text={{!!latex}} displayMode=false/>`   (inline math)
  EQ    `<$latex text={{!!latex}} displayMode=true/>`    (display math)
  URL   external link to {{!!url}}
  CIT   `[n]` citation → its source url

Title scheme (bibkey-prefixed, PDFDRILL style):
  <bibkey>            chat root        <bibkey>_EX<NNNN>   exchange
  <bibkey>_CODE<NNN>  code             <bibkey>_FO<NNNN>   inline formula
  <bibkey>_EQ<NNNN>   display equation <bibkey>_URL<NNN>   url
  <bibkey>_CIT<NNN>   citation         <bibkey>_FILE<NNN>  virtual file
  <bibkey>_preamble   provider preamble

Every chat tiddler carries **provider + type tags** plus the bibkey namespace,
e.g. `code perplexity [[Pplx20241003_Foo]]`. References — math, code, urls, `[n]`
citations, and simple spoken refs ("the code above") — all become transclusions.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone

from ..models import ChatModel
from ..passes.segment import segment_text
from .providers import for_source

_STOP = {"the", "a", "an", "of", "for", "to", "in", "on", "and", "or", "with",
         "is", "are", "how", "what", "why", "do", "i", "my", "me", "please"}
_GENERIC = {"", "new chat", "untitled", "(untitled)", "chat"}
_URL_RE = re.compile(r"https?://[^\s)>\]\"'`]+")
_SPOKEN_RE = re.compile(
    r"\bthe (code|script|function|snippet|example) (above|below|earlier|"
    r"shown (?:above|earlier)|i (?:gave|showed|wrote)(?: (?:above|earlier))?)\b",
    re.IGNORECASE)


def _camel(s: str, words: int = 3) -> str:
    toks = [t for t in re.findall(r"[A-Za-z0-9]+", s or "") if t.lower() not in _STOP]
    return "".join(t[:1].upper() + t[1:] for t in toks[:words])[:32]


def _date(ts) -> str:
    if not ts:
        return "00000000"
    if ts > 1_000_000_000_000:                 # milliseconds → seconds
        ts //= 1000
    try:
        return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y%m%d")
    except (OverflowError, OSError, ValueError):
        return "00000000"


def _first_query(model: ChatModel) -> str:
    return next((ex.query.content for ex in model.exchanges if ex.query.content), "")


def bibkey(model: ChatModel) -> str:
    """`<ProvCode><YYYYMMDD>_<TitleCamel|shortid>` — the tiddler namespace."""
    prov = for_source(model.source)
    title = (model.title or "").strip()
    disc = _camel(title if title.lower() not in _GENERIC else _first_query(model))
    return f"{prov.code}{_date(model.created_at)}_{disc or model.id[:8]}"


def chat_title(model: ChatModel) -> str:
    t = (model.title or "").strip()
    if t.lower() not in _GENERIC:
        return t
    q = _first_query(model)
    return " ".join(q.split()[:10]) or model.id[:8]


def _bibtag(key: str) -> str:
    return f"[[{key}]]" if " " in key else key


# ---- template tiddlers (shared; one set, transcluded by every instance) ------
def _templates() -> list[dict]:
    def tpl(title, text):
        return {"title": title, "tags": "$:/tags/chatdrill/template",
                "type": "text/markdown", "text": text}
    return [
        tpl("CODE", "<$codeblock code={{!!code}} language={{!!lang}}/>"),
        tpl("FO", "<$latex text={{!!latex}} displayMode=false/>"),
        tpl("EQ", "<$latex text={{!!latex}} displayMode=true/>"),
        tpl("URL", '<a class="tc-tiddlylink-external" rel="noopener" '
                   'target="_blank" href={{!!url}}>{{!!caption}}</a>'),
        tpl("CIT", '<a class="tc-tiddlylink-external" href={{!!url}}>[{{!!n}}]</a>'),
    ]


class _Builder:
    def __init__(self, model: ChatModel):
        self.model = model
        self.prov = for_source(model.source)
        self.bibkey = bibkey(model)
        self.suffix = f"{self.prov.label} {_bibtag(self.bibkey)}"
        self.out: list[dict] = []
        self.n: dict[str, int] = defaultdict(int)
        self.code_titles: list[str] = []          # for spoken-ref resolution
        self.url_titles: list[str] = []
        self.source_urls: list[str] = []          # provider Sources section

    # -- low level --
    def _title(self, code: str, width: int = 4) -> str:
        i = self.n[code]; self.n[code] += 1
        return f"{self.bibkey}_{code}{i:0{width}d}"

    def _tid(self, title: str, text: str, type_tag: str, **fields) -> str:
        # text/markdown is the default for all content tiddlers; embedded
        # transclusions/widgets/math still render (renderWikiText=true + katex).
        t = {"title": title, "tags": f"{type_tag} {self.suffix}",
             "type": "text/markdown", "text": text}
        t.update({k: str(v) for k, v in fields.items() if v is not None})
        self.out.append(t)
        return title

    # -- instance tiddlers (each transcluded via its template) --
    def add_code(self, code: str, lang: str | None) -> str:
        title = self._tid(self._title("CODE", 3),
                          "<$codeblock code={{!!code}} language={{!!lang}}/>",
                          "code", code=code, lang=lang or "")
        self.code_titles.append(title)
        return title

    def add_formula(self, latex: str, display: bool) -> tuple[str, str]:
        tpl = "EQ" if display else "FO"
        title = self._tid(self._title(tpl),
                          f"<$latex text={{{{!!latex}}}} displayMode={str(display).lower()}/>",
                          "formula", latex=latex, caption=latex,
                          displayMode=str(display).lower())
        return title, tpl

    def add_url(self, url: str, caption: str = "") -> str:
        title = self._tid(self._title("URL", 3),
                          '<a class="tc-tiddlylink-external" target="_blank" '
                          'href={{!!url}}>{{!!caption}}</a>',
                          "url", url=url, caption=caption or url)
        self.url_titles.append(title)
        return title

    def add_citation(self, n: str, url: str) -> str:
        return self._tid(self._title("CIT", 3),
                         '<a class="tc-tiddlylink-external" href={{!!url}}>[{{!!n}}]</a>',
                         "citation", n=n, url=url)

    # -- reference substitutions over prose --
    def _sub_math(self, text: str) -> str:
        for open_d, close_d in self.prov.math:
            display = open_d in ("$$", r"\[")
            pat = re.compile(re.escape(open_d) + r"(.+?)" + re.escape(close_d), re.S)

            def repl(m, display=display):
                inner = m.group(1).strip()
                if not inner or (open_d == "$" and not re.search(r"[\\^_{}]", inner)):
                    return m.group(0)             # skip "$5" style non-math
                title, tpl = self.add_formula(inner, display)
                return f"{{{{{title}||{tpl}}}}}"
            text = pat.sub(repl, text)
        return text

    def _sub_urls(self, text: str) -> str:
        def repl(m):
            title = self.add_url(m.group(0).rstrip(".,;:)]"))
            return f"{{{{{title}||URL}}}}"
        return _URL_RE.sub(repl, text)

    def _sub_citations(self, text: str, sources: list[str]) -> str:
        if not self.prov.citation or not sources:
            return text
        def repl(m):
            k = int(m.group(1))
            if 1 <= k <= len(sources):
                title = self.add_citation(str(k), sources[k - 1])
                return f"{{{{{title}||CIT}}}}"
            return m.group(0)
        return re.sub(r"\[(\d{1,3})\]", repl, text)

    def _sub_spoken(self, text: str) -> str:
        if not self.code_titles:
            return text
        def repl(m):
            return f"{m.group(0)} {{{{{self.code_titles[-1]}||CODE}}}}"
        return _SPOKEN_RE.sub(repl, text)

    def render_segments(self, segments, sources: list[str]) -> str:
        """Segments with every reference turned into a transclusion."""
        parts: list[str] = []
        for seg in segments:
            if seg.kind == "code":
                parts.append(f"{{{{{self.add_code(seg.text, seg.lang)}||CODE}}}}")
            else:
                t = self._sub_math(seg.text)
                t = self._sub_citations(t, sources)
                t = self._sub_urls(t)
                t = self._sub_spoken(t)
                parts.append(t)
        return "\n\n".join(p for p in parts if p.strip())

    @staticmethod
    def _split_sources(answer_text: str) -> tuple[str, list[str]]:
        """Pull the encoder-appended 'Sources:\\n- url' block off the answer."""
        m = re.search(r"\n\nSources:\n((?:- \S+\n?)+)\s*$", answer_text or "")
        if not m:
            return answer_text, []
        urls = re.findall(r"-\s*(\S+)", m.group(1))
        return answer_text[:m.start()], urls


def build_tiddlers(model: ChatModel) -> list[dict]:
    b = _Builder(model)
    out = b.out
    out.extend(_templates())

    # preamble (per provider)
    out.append({"title": f"{b.bibkey}_preamble",
                "tags": f"preamble {b.suffix}", "type": "text/markdown",
                "text": b.prov.preamble})

    ex_links, code_links = [], []
    for ex in model.exchanges:
        # answer: strip the Sources block (perplexity) → CIT mapping + Sources section
        sources: list[str] = []
        if ex.answer is None:
            a_text = "//(no answer)//"
        else:
            content = ex.answer.content
            if b.prov.citation:
                content, sources = b._split_sources(content)
                b.source_urls.extend(sources)
            # re-segment only if the Sources block was stripped, else reuse pass03
            segs = ex.answer.segments if content == ex.answer.content else segment_text(content)
            a_text = b.render_segments(segs, sources)
        q_text = b.render_segments(ex.query.segments, sources)
        lat = f" · {ex.latency_ms // 1000}s" if ex.latency_ms is not None else ""
        ex_title = b._tid(
            f"{b.bibkey}_EX{ex.index:04d}",
            f"## Question\n\n{q_text}\n\n## Answer ⟨{ex.model or '?'}{lat}⟩\n\n{a_text}",
            "exchange", index=ex.index, model=ex.model or "",
            answered=str(ex.answered).lower(),
            **({"latency_s": ex.latency_ms // 1000} if ex.latency_ms is not None else {}))
        ex_links.append(f"* {{{{{ex_title}}}}}")

    for vf in model.virtual_files:
        title = b._tid(f"{b.bibkey}_FILE{b.n['FILE']:03d}",
                       "<$codeblock code={{!!code}} language={{!!lang}}/>",
                       "file", code=vf.content, lang=vf.lang or "", path=vf.path,
                       revisions=vf.revisions)
        b.n["FILE"] += 1
        code_links.append(f"* [[{vf.path}|{title}]] — `{vf.lang or '?'}` ({vf.revisions}×)")

    # chat root — provider-specific structure
    answered = sum(1 for e in model.exchanges if e.answered)
    body = [f"# {chat_title(model)}", "",
            f"Provider: {b.prov.label} · Models: {', '.join(model.models) or '—'} · "
            f"{len(model.exchanges)} exchanges ({answered} answered) · "
            f"see {{{{{b.bibkey}_preamble}}}}", ""]
    structure = {
        "Exchanges": ex_links,
        "Code": code_links,
        "Files": code_links,
        "Links": sorted({f"* {{{{{t}||URL}}}}" for t in b.url_titles}),
        "Sources": [f"* {u}" for u in dict.fromkeys(b.source_urls)],
    }
    for sec in b.prov.sections:
        items = structure.get(sec)
        if items:
            body += [f"## {sec}", *items, ""]

    out.insert(len(_templates()) + 1,
               {"title": b.bibkey, "tags": f"chat {b.suffix}",
                "type": "text/markdown", "text": "\n".join(body),
                "source": model.source, "chat_id": model.id,
                "provider": b.prov.label, "models": ", ".join(model.models),
                "exchanges": str(len(model.exchanges))})
    return out


# ---- integrity audit (ported from PDFDRILL tiddler_integrity) ----------------
_TRANSCLUDE_RE = re.compile(r"\{\{([^{}]+?)\}\}")


def tiddler_integrity(tiddlers: list[dict]) -> dict:
    """{transclusions, dangling} — every `{{target||tpl}}` whose target or template
    tiddler is missing would render nothing. `{{!!field}}` is ignored."""
    titles = {t.get("title") for t in tiddlers}
    dangling: set[str] = set()
    n = 0
    for t in tiddlers:
        for m in _TRANSCLUDE_RE.finditer(t.get("text") or ""):
            inner = m.group(1).strip()
            if inner.startswith("!!"):
                continue
            n += 1
            target = inner.split("||")[0].split("!!")[0].strip()
            tpl = inner.split("||", 1)[1].strip() if "||" in inner else None
            if target and target not in titles:
                dangling.add(target)
            if tpl and tpl not in titles:
                dangling.add(tpl)
    return {"transclusions": n, "dangling": sorted(dangling)}


# ---- serialization ----------------------------------------------------------
def _safe_filename(title: str) -> str:
    return re.sub(r"[^\w.-]+", "_", title) + ".tid"


def to_tid_text(t: dict) -> str:
    header = "\n".join(f"{k}: {v}" for k, v in t.items() if k != "text")
    return f"{header}\n\n{t.get('text', '')}\n"
