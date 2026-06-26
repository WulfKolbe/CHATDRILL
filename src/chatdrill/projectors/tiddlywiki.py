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

import hashlib
import re
from collections import defaultdict
from datetime import datetime, timezone

from ..models import ChatModel
from ..passes.segment import segment_text
from .providers import for_source

_STOP = {"the", "a", "an", "of", "for", "to", "in", "on", "and", "or", "with",
         "is", "are", "how", "what", "why", "do", "i", "my", "me", "please"}
_GENERIC = {"", "new chat", "untitled", "(untitled)", "chat"}

# Store code as RAW text with the tiddler `type` set to the language MIME, so the
# wiki shows it as a proper (browser-highlighted) code tiddler — not a field.
LANG_MIME = {
    "python": "text/x-python", "py": "text/x-python",
    "javascript": "application/javascript", "js": "application/javascript",
    "typescript": "application/typescript", "ts": "application/typescript",
    "tsx": "application/typescript", "jsx": "application/javascript",
    "json": "application/json", "bash": "text/x-sh", "sh": "text/x-sh",
    "shell": "text/x-sh", "console": "text/x-sh", "html": "text/html",
    "css": "text/css", "scss": "text/css", "sql": "text/x-sql",
    "c": "text/x-csrc", "h": "text/x-csrc", "cpp": "text/x-c++src",
    "java": "text/x-java", "go": "text/x-go", "rust": "text/x-rustsrc",
    "rs": "text/x-rustsrc", "ruby": "text/x-ruby", "rb": "text/x-ruby",
    "php": "application/x-httpd-php", "xml": "application/xml",
    "yaml": "text/x-yaml", "yml": "text/x-yaml", "toml": "text/x-toml",
    "latex": "text/x-latex", "tex": "text/x-latex", "markdown": "text/markdown",
    "md": "text/markdown", "lua": "text/x-lua", "kotlin": "text/x-kotlin",
    "swift": "text/x-swift", "r": "text/x-rsrc", "awk": "text/plain",
}


def _mime(lang: str | None) -> str:
    return LANG_MIME.get((lang or "").lower(), "text/plain")


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


_SYMBOL = re.compile(
    r"\b(?:def|class|interface|type|function|func|fn|const|struct|enum)\s+([A-Za-z_]\w*)")


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


# Math: normalize TeX delimiters to $/$$ so markdown-it-katex renders them inline.
_MATH_INLINE = re.compile(r"\\\((.+?)\\\)", re.S)     # \( … \)  → $ … $
_MATH_DISPLAY = re.compile(r"\\\[(.+?)\\\]", re.S)    # \[ … \]  → $$ … $$


class _Builder:
    def __init__(self, model: ChatModel):
        self.model = model
        self.prov = for_source(model.source)
        self.bibkey = bibkey(model)
        self.suffix = f"{self.prov.label} {_bibtag(self.bibkey)}"
        self.out: list[dict] = []
        self.n: dict[str, int] = defaultdict(int)
        self.code_titles: list[tuple] = []        # (title, lang, lines, caption)
        self.source_urls: list[str] = []          # provider Sources section
        self.cur_ex = 0                            # exchange context for code comments
        self.cur_query = ""

    # -- low level --
    def _tid(self, title: str, text: str, type_tag: str, *, type="text/markdown",
             comment: str = "", **fields) -> str:
        # text/markdown by default; code tiddlers pass their language MIME. A
        # git/svn-style `comment` header field is added to every tiddler.
        t = {"title": title, "tags": f"{type_tag} {self.suffix}", "type": type,
             "text": text}
        if comment:
            t["comment"] = comment
        t.update({k: str(v) for k, v in fields.items() if v is not None})
        self.out.append(t)
        return title

    def _code_caption(self, code: str, lang: str | None) -> str:
        m = _SYMBOL.search(code)
        if m:
            return m.group(1)
        first = next((ln.strip() for ln in code.splitlines() if ln.strip()), "")
        return first[:48] or f"{lang or 'code'} snippet"

    def add_code(self, code: str, lang: str | None) -> str:
        """A standalone code tiddler: RAW code in TEXT, `type` = the language MIME
        (so the wiki shows it as a highlighted code tiddler), with metadata + a
        git/svn-style comment in FIELDS. `}}` and newlines are safe (not a field,
        not markdown)."""
        title = f"{self.bibkey}_CODE{self.n['CODE']:03d}"; self.n["CODE"] += 1
        lines = len(code.splitlines())
        caption = self._code_caption(code, lang)
        comment = f"ex{self.cur_ex} · {' '.join(self.cur_query.split())[:80]}"
        self._tid(title, code, "code", type=_mime(lang), comment=comment,
                  lang=lang or "", lines=lines, sha1=_sha1(code),
                  exchange=self.cur_ex, caption=caption)
        self.code_titles.append((title, lang or "?", lines, caption))
        return title

    # -- markdown rendering of a turn --
    def _normalize_math(self, text: str) -> str:
        text = _MATH_DISPLAY.sub(lambda m: f"$${m.group(1).strip()}$$", text)
        return _MATH_INLINE.sub(lambda m: f"${m.group(1).strip()}$", text)

    def _sub_citations(self, text: str, sources: list[str]) -> str:
        """`[n]` → a markdown link to source n (Perplexity)."""
        if not self.prov.citation or not sources:
            return text
        def repl(m):
            k = int(m.group(1))
            return f"[\\[{k}\\]]({sources[k - 1]})" if 1 <= k <= len(sources) else m.group(0)
        return re.sub(r"\[(\d{1,3})\]", repl, text)

    def render_segments(self, segments, sources: list[str]) -> str:
        """Render a turn as native markdown. A code segment becomes a compact
        reference — `{{title||CODEREF}}` shows a LINK to the (separately stored)
        code tiddler plus its descriptive fields; prose gets math/citation
        normalization."""
        parts: list[str] = []
        for seg in segments:
            if seg.kind == "code":
                parts.append(f"{{{{{self.add_code(seg.text, seg.lang)}||CODEREF}}}}")
            else:
                t = self._normalize_math(seg.text)
                t = self._sub_citations(t, sources)
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

    # CODEREF template — a compact reference: link to the code tiddler + fields.
    out.append({"title": "CODEREF", "tags": "$:/tags/chatdrill/template",
                "type": "text/vnd.tiddlywiki",
                "text": "<$link to=<<currentTiddler>>>''{{!!caption}}''</$link>"
                        " · //{{!!lang}}, {{!!lines}} lines// — {{!!comment}}"})

    # preamble (per provider)
    out.append({"title": f"{b.bibkey}_preamble",
                "tags": f"preamble {b.suffix}", "type": "text/markdown",
                "comment": f"{b.prov.label} chat conventions",
                "text": b.prov.preamble})

    ex_links = []
    for ex in model.exchanges:
        b.cur_ex, b.cur_query = ex.index, ex.query.content   # context for code comments
        # answer: strip the Sources block (perplexity) → citation links + Sources section
        sources: list[str] = []
        if ex.answer is None:
            a_text = "_(no answer)_"
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
            "exchange", comment=f"ex{ex.index} · {' '.join(ex.query.content.split())[:80]}",
            index=ex.index, model=ex.model or "", answered=str(ex.answered).lower(),
            **({"latency_s": ex.latency_ms // 1000} if ex.latency_ms is not None else {}))
        ex_links.append(f"* {{{{{ex_title}}}}}")

    # code tiddlers (created during rendering) → CODEREF index links
    code_links = [f"* {{{{{t}||CODEREF}}}}" for t, *_ in b.code_titles]
    # virtual files → typed code tiddlers (raw code in text + language MIME)
    file_links = []
    for vf in model.virtual_files:
        title = f"{b.bibkey}_FILE{b.n['FILE']:03d}"; b.n["FILE"] += 1
        b._tid(title, vf.content, "file", type=_mime(vf.lang),
               comment=f"reconstructed {vf.path} · {vf.revisions} revision(s)",
               path=vf.path, lang=vf.lang or "", caption=vf.path,
               lines=len(vf.content.splitlines()), revisions=vf.revisions)
        file_links.append(f"* {{{{{title}||CODEREF}}}}")

    urls = sorted({a.content for a in model.artifacts if a.kind == "url"})

    # chat root — provider-specific structure (markdown links + exchange transclusions)
    answered = sum(1 for e in model.exchanges if e.answered)
    body = [f"# {chat_title(model)}", "",
            f"Provider: {b.prov.label} · Models: {', '.join(model.models) or '—'} · "
            f"{len(model.exchanges)} exchanges ({answered} answered) · "
            f"see [[{b.bibkey}_preamble]]", ""]
    structure = {
        "Exchanges": ex_links,
        "Code": code_links,
        "Files": file_links,
        "Links": [f"* <{u}>" for u in urls],
        "Sources": [f"* <{u}>" for u in dict.fromkeys(b.source_urls)],
    }
    for sec in b.prov.sections:
        items = structure.get(sec)
        if items:
            body += [f"## {sec}", *items, ""]

    out.insert(0,
               {"title": b.bibkey, "tags": f"chat {b.suffix}",
                "type": "text/markdown", "text": "\n".join(body),
                "comment": f"{b.prov.label} · {chat_title(model)} · "
                           f"{len(model.exchanges)} exchanges",
                "caption": chat_title(model),
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
