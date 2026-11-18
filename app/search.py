"""Search and retrieval over published documentation.

Provides:
- a lightweight in-memory index for normal (keyword) search
- pluggable semantic search hooks
- chunk retrieval used by the docs-only chatbot
"""

from __future__ import annotations

import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.frontmatter import strip_frontmatter

__all__ = [
    "DocChunk",
    "SearchHit",
    "SearchIndex",
    "build_index",
    "get_index",
    "invalidate_index",
]

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+(?:[.'-][A-Za-z0-9_]+)*")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
_CODE_FENCE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _normalize_text(text: str) -> str:
    text = _CODE_FENCE_RE.sub(" ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s{0,3}[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}\d+\.\s+", "", text, flags=re.MULTILINE)
    text = _HTML_TAG_RE.sub(" ", text)
    text = re.sub(r"[#>*_|~`-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _excerpt(text: str, query_tokens: list[str], max_len: int = 220) -> str:
    clean = _normalize_text(text)
    if not clean:
        return ""
    lower = clean.lower()
    pos = -1
    for tok in query_tokens:
        i = lower.find(tok)
        if i != -1 and (pos == -1 or i < pos):
            pos = i
    if pos == -1:
        snippet = clean[:max_len]
    else:
        start = max(0, pos - 60)
        end = min(len(clean), start + max_len)
        snippet = clean[start:end]
        if start > 0:
            snippet = "…" + snippet.lstrip()
    if len(clean) > (pos - 60 if pos != -1 else 0) + max_len:
        snippet = snippet.rstrip() + "…"
    return snippet


@dataclass
class DocChunk:
    url: str
    title: str
    heading: str
    text: str
    rel: str
    tags: list[str] = field(default_factory=list)
    order: int = 0

    @property
    def display_heading(self) -> str:
        return self.heading or self.title

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "heading": self.heading,
            "text": self.text,
            "rel": self.rel,
            "tags": list(self.tags),
        }


@dataclass
class SearchHit:
    url: str
    title: str
    excerpt: str
    score: float
    rel: str = ""
    heading: str = ""
    tags: list[str] = field(default_factory=list)
    mode: str = "normal"

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "excerpt": self.excerpt,
            "score": round(self.score, 4),
            "rel": self.rel,
            "heading": self.heading,
            "tags": list(self.tags),
            "mode": self.mode,
        }


@dataclass
class _DocRecord:
    url: str
    title: str
    rel: str
    tags: list[str]
    description: str
    chunks: list[DocChunk]
    full_text: str
    tf: Counter[str]
    length: int


class SearchIndex:
    def __init__(self) -> None:
        self.docs: dict[str, _DocRecord] = {}
        self.df: Counter[str] = Counter()
        self.avg_len: float = 1.0
        self.built_at: float = 0.0

    def _idf(self, term: str) -> float:
        n = len(self.docs) or 1
        df = self.df.get(term, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def _normal_score(self, rec: _DocRecord, q_terms: list[str], phrase: str) -> tuple[float, str, str]:
        score = 0.0
        matched = 0
        k1 = 1.2
        b = 0.75
        for term in q_terms:
            tf = rec.tf.get(term, 0)
            if tf <= 0:
                continue
            matched += 1
            idf = self._idf(term)
            denom = tf + k1 * (1 - b + b * (rec.length / (self.avg_len or 1.0)))
            score += idf * (tf * (k1 + 1)) / (denom or 1.0)
        if matched == 0:
            return 0.0, "", rec.description or rec.full_text
        title_l = rec.title.lower()
        desc_l = rec.description.lower()
        rel_l = rec.rel.lower()
        for term in q_terms:
            if term in title_l:
                score += 2.5
            if term in rel_l:
                score += 0.8
            if term in desc_l:
                score += 1.2
            if any(term in t.lower() for t in rec.tags):
                score += 1.5
        if phrase and phrase in rec.full_text.lower():
            score += 2.0
        score *= 1 + (matched / max(1, len(q_terms))) * 0.5
        excerpt_source = rec.description or rec.full_text
        heading = ""
        best_chunk = None
        best_chunk_score = -1
        for chunk in rec.chunks:
            ctext = (chunk.heading + " " + chunk.text).lower()
            cs = sum(1 for t in q_terms if t in ctext)
            if phrase and phrase in ctext:
                cs += 2
            if cs > best_chunk_score:
                best_chunk_score = cs
                best_chunk = chunk
        if best_chunk and best_chunk_score > 0:
            excerpt_source = (best_chunk.heading + ". " if best_chunk.heading else "") + best_chunk.text
            heading = best_chunk.heading
        return score, heading, excerpt_source

    def _semantic_score(self, rec: _DocRecord, q_terms: list[str], q_counts: Counter[str]) -> tuple[float, str, str]:
        # Lightweight local "semantic" similarity: cosine over term vectors with
        # IDF weighting and soft partial coverage. No external embedding model.
        if not q_counts:
            return 0.0, "", rec.description or rec.full_text
        dot = 0.0
        q_norm = 0.0
        d_norm = 0.0
        matched = 0
        # Precompute query norm
        q_weights: dict[str, float] = {}
        for term, qtf in q_counts.items():
            idf = self._idf(term)
            qw = (1.0 + math.log(qtf)) * idf
            q_weights[term] = qw
            q_norm += qw * qw
        if q_norm == 0:
            return 0.0, "", rec.description or rec.full_text
        # Document norm over terms present in query + small global signal
        for term, qw in q_weights.items():
            dtf = rec.tf.get(term, 0)
            if dtf > 0:
                matched += 1
                dw = (1.0 + math.log(dtf)) * self._idf(term)
                dot += qw * dw
        # Full doc norm approximation: sum squared weights for doc terms
        # (cheap enough for typical doc sets; could be cached if needed)
        for term, dtf in rec.tf.items():
            idf = self._idf(term)
            dw = (1.0 + math.log(dtf)) * idf
            d_norm += dw * dw
        if d_norm == 0 or matched == 0:
            return 0.0, "", rec.description or rec.full_text
        cosine = dot / (math.sqrt(q_norm) * math.sqrt(d_norm))
        coverage = matched / max(1, len(q_counts))
        score = cosine * 10.0 + coverage * 2.0
        title_l = rec.title.lower()
        desc_l = rec.description.lower()
        for term in q_counts:
            if term in title_l:
                score += 0.8
            if term in desc_l:
                score += 0.4
            if any(term in t.lower() for t in rec.tags):
                score += 0.5
        excerpt_source = rec.description or rec.full_text
        heading = ""
        best_chunk = None
        best_chunk_score = -1.0
        for chunk in rec.chunks:
            c_tokens = Counter(_tokenize(chunk.heading + " " + chunk.text))
            cdot = 0.0
            cnorm = 0.0
            cmatched = 0
            for term, qw in q_weights.items():
                ctf = c_tokens.get(term, 0)
                if ctf:
                    cmatched += 1
                    cw = 1.0 + math.log(ctf)
                    cdot += qw * cw
            if cmatched == 0:
                continue
            for ctf in c_tokens.values():
                cw = 1.0 + math.log(ctf)
                cnorm += cw * cw
            csim = cdot / (math.sqrt(q_norm) * math.sqrt(cnorm or 1.0))
            cs = csim + 0.15 * cmatched
            if chunk.heading and any(t in chunk.heading.lower() for t in q_counts):
                cs += 0.1
            if cs > best_chunk_score:
                best_chunk_score = cs
                best_chunk = chunk
        if best_chunk and best_chunk_score > 0:
            excerpt_source = (best_chunk.heading + ". " if best_chunk.heading else "") + best_chunk.text
            heading = best_chunk.heading
        return score, heading, excerpt_source

    def search(self, query: str, *, limit: int = 10, mode: str = "normal") -> list[SearchHit]:
        q = (query or "").strip()
        if not q:
            return []
        q_tokens = _tokenize(q)
        if not q_tokens:
            return []
        q_terms = list(dict.fromkeys(q_tokens))
        q_counts = Counter(q_tokens)
        phrase = q.lower()
        mode = (mode or "normal").lower()
        use_semantic = mode in {"semantic", "vector"}
        hits: list[SearchHit] = []
        for rec in self.docs.values():
            if use_semantic:
                score, heading, excerpt_source = self._semantic_score(rec, q_terms, q_counts)
            else:
                score, heading, excerpt_source = self._normal_score(rec, q_terms, phrase)
            if score <= 0:
                continue
            hits.append(
                SearchHit(
                    url=rec.url,
                    title=rec.title,
                    excerpt=_excerpt(excerpt_source, q_tokens),
                    score=score,
                    rel=rec.rel,
                    heading=heading,
                    tags=list(rec.tags),
                    mode="semantic" if use_semantic else "normal",
                )
            )
        hits.sort(key=lambda h: (-h.score, h.title.lower(), h.url))
        return hits[: max(1, limit)]

    def retrieve(self, query: str, *, limit: int = 5) -> list[DocChunk]:
        """Return the most relevant chunks for chatbot/context use."""
        q = (query or "").strip()
        if not q:
            return []
        q_tokens = _tokenize(q)
        if not q_tokens:
            return []
        q_terms = list(dict.fromkeys(q_tokens))
        phrase = q.lower()
        scored: list[tuple[float, DocChunk]] = []
        for rec in self.docs.values():
            doc_boost = 0.0
            title_l = rec.title.lower()
            for term in q_terms:
                if term in title_l:
                    doc_boost += 0.7
                if any(term in t.lower() for t in rec.tags):
                    doc_boost += 0.5
            for chunk in rec.chunks:
                text = (chunk.heading + "\n" + chunk.text).lower()
                score = doc_boost
                matched = 0
                for term in q_terms:
                    c = text.count(term)
                    if c:
                        matched += 1
                        score += 1.0 + min(c, 6) * 0.25
                if matched == 0:
                    continue
                if phrase and phrase in text:
                    score += 1.5
                if chunk.heading:
                    hl = chunk.heading.lower()
                    if any(t in hl for t in q_terms):
                        score += 0.8
                score *= 1 + (matched / max(1, len(q_terms))) * 0.4
                scored.append((score, chunk))
        scored.sort(key=lambda x: (-x[0], x[1].url, x[1].order))
        # Deduplicate by (url, heading/text prefix)
        out: list[DocChunk] = []
        seen: set[tuple[str, str]] = set()
        for _score, chunk in scored:
            key = (chunk.url, chunk.heading or chunk.text[:80])
            if key in seen:
                continue
            seen.add(key)
            out.append(chunk)
            if len(out) >= limit:
                break
        return out


def _chunk_markdown(url: str, title: str, rel: str, tags: list[str], body: str) -> tuple[list[DocChunk], str]:
    text = body.replace("\r\n", "\n")
    headings = list(_HEADING_RE.finditer(text))
    chunks: list[DocChunk] = []
    full_parts: list[str] = []
    if not headings:
        clean = _normalize_text(text)
        if clean:
            chunks.append(DocChunk(url=url, title=title, heading="", text=clean, rel=rel, tags=tags, order=0))
            full_parts.append(clean)
        return chunks, " ".join(full_parts)

    # Intro before first heading
    intro = text[: headings[0].start()].strip()
    if intro:
        clean = _normalize_text(intro)
        if clean:
            chunks.append(DocChunk(url=url, title=title, heading="", text=clean, rel=rel, tags=tags, order=0))
            full_parts.append(clean)
    for i, m in enumerate(headings):
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        heading = m.group(2).strip()
        section = text[start:end].strip()
        clean = _normalize_text(section)
        if not clean and not heading:
            continue
        # Keep chunks reasonably sized.
        if len(clean) > 1200:
            parts = re.split(r"\n\s*\n", section)
            buf = ""
            sub = 0
            for part in parts:
                part_clean = _normalize_text(part)
                if not part_clean:
                    continue
                if buf and len(buf) + 1 + len(part_clean) > 900:
                    chunks.append(
                        DocChunk(url=url, title=title, heading=heading, text=buf.strip(), rel=rel, tags=tags, order=i * 10 + sub)
                    )
                    full_parts.append(heading + " " + buf)
                    buf = part_clean
                    sub += 1
                else:
                    buf = (buf + " " + part_clean).strip() if buf else part_clean
            if buf:
                chunks.append(
                    DocChunk(url=url, title=title, heading=heading, text=buf.strip(), rel=rel, tags=tags, order=i * 10 + sub)
                )
                full_parts.append(heading + " " + buf)
        else:
            chunks.append(DocChunk(url=url, title=title, heading=heading, text=clean, rel=rel, tags=tags, order=i + 1))
            full_parts.append((heading + " " + clean).strip())
    if not chunks:
        clean = _normalize_text(text)
        if clean:
            chunks.append(DocChunk(url=url, title=title, heading="", text=clean, rel=rel, tags=tags, order=0))
            full_parts.append(clean)
    return chunks, " ".join(full_parts)


def build_index(site, discovered=None) -> SearchIndex:
    """Build a search index from the site's published markdown documents."""
    # Import here to avoid circular imports at module import time.
    if discovered is None:
        from app.main import discover

        discovered = discover(site)

    index = SearchIndex()
    lengths: list[int] = []
    for entry in discovered.documents.values():
        if entry.file_type.kind != "markdown":
            continue
        try:
            raw = entry.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        body = strip_frontmatter(raw)
        title = entry.display_title or entry.label
        tags = list(getattr(entry, "tags", []) or [])
        desc = getattr(entry, "description", "") or ""
        chunks, full_text = _chunk_markdown(entry.url, title, entry.rel, tags, body)
        combined = " ".join([title, desc, " ".join(tags), entry.rel.replace("/", " "), full_text])
        tokens = _tokenize(combined)
        tf = Counter(tokens)
        rec = _DocRecord(
            url=entry.url,
            title=title,
            rel=entry.rel,
            tags=tags,
            description=desc,
            chunks=chunks,
            full_text=combined,
            tf=tf,
            length=len(tokens),
        )
        index.docs[entry.url] = rec
        lengths.append(len(tokens))
        for term in tf.keys():
            index.df[term] += 1
    index.avg_len = (sum(lengths) / len(lengths)) if lengths else 1.0
    index.built_at = time.time()
    return index


_cached: dict[str, Any] = {"key": None, "sig": None, "index": None}


def _cache_key(site) -> tuple:
    # Rebuild when docs/config identity changes; content freshness is handled by signature.
    cfg = site.config
    return (
        str(site.docs_dir),
        tuple(sorted(site.types.extensions)),
        site.types.dynamic_code,
        tuple(cfg.ignore),
        cfg.title,
    )


def _content_signature(discovered) -> tuple:
    items = []
    for url, entry in discovered.documents.items():
        if entry.file_type.kind != "markdown":
            continue
        try:
            st = entry.path.stat()
            items.append((url, st.st_mtime_ns, st.st_size))
        except OSError:
            items.append((url, None, None))
    items.sort()
    return tuple(items)


def get_index(site) -> SearchIndex:
    from app.main import discover

    key = _cache_key(site)
    discovered = discover(site)
    sig = _content_signature(discovered)
    if _cached.get("key") == key and _cached.get("sig") == sig and _cached.get("index") is not None:
        return _cached["index"]
    idx = build_index(site, discovered=discovered)
    _cached["key"] = key
    _cached["sig"] = sig
    _cached["index"] = idx
    return idx


def invalidate_index() -> None:
    _cached["key"] = None
    _cached["sig"] = None
    _cached["index"] = None
