"""Docs-only chat/retrieval assistant.

The assistant answers using retrieved chunks from the published documentation.
When an LLM endpoint is configured it can generate a grounded response; otherwise
it falls back to an extractive answer composed from the most relevant docs.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.search import get_index

__all__ = ["chat_answer"]


@dataclass
class ChatSource:
    url: str
    title: str
    heading: str
    excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "heading": self.heading,
            "excerpt": self.excerpt,
        }


def _llm_config() -> dict[str, str] | None:
    api_key = (
        os.environ.get("DEVDOCS_LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    ).strip()
    if not api_key:
        return None
    base_url = (
        os.environ.get("DEVDOCS_LLM_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    ).strip().rstrip("/")
    model = (os.environ.get("DEVDOCS_LLM_MODEL") or "gpt-4o-mini").strip()
    if not model:
        model = "gpt-4o-mini"
    return {"api_key": api_key, "base_url": base_url, "model": model}


def _build_context(chunks) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        heading = f" — {chunk.heading}" if chunk.heading else ""
        parts.append(
            f"[Source {i}] {chunk.title}{heading} ({'/' + chunk.url})\n{chunk.text}"
        )
    return "\n\n".join(parts)


def _call_llm(question: str, chunks, history: list[dict[str, str]] | None = None) -> str | None:
    cfg = _llm_config()
    if not cfg or not chunks:
        return None
    context = _build_context(chunks)
    system = (
        "You are the documentation assistant for this site. Answer the user's question "
        "using ONLY the provided documentation excerpts. Do not use outside knowledge. "
        "If the answer is not contained in the excerpts, say that the documentation does not "
        "cover it and suggest the closest relevant page from the excerpts. Be concise and cite "
        "sources by their path like /path/to/page."
    )
    user = (
        f"Documentation excerpts:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer based only on the excerpts above."
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for msg in (history or [])[-6:]:
        role = str(msg.get("role", "")).strip()
        content = str(msg.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user})
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0.2,
    }
    url = cfg["base_url"] + "/chat/completions"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None
    try:
        choices = body.get("choices") or []
        if not choices:
            return None
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        # Some APIs return content parts.
        if isinstance(content, list):
            texts = []
            for part in content:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    texts.append(part["text"])
            if texts:
                return "\n".join(texts).strip()
    except Exception:
        return None
    return None


def _extractive_answer(question: str, chunks) -> str:
    if not chunks:
        return (
            "I couldn't find relevant information in the published documentation for that question. "
            "Try different keywords or browse the documentation index."
        )
    q_terms = [t.lower() for t in re.findall(r"[A-Za-z0-9_]+", question or "") if len(t) > 2]
    lines = ["Based on the documentation:"]
    for chunk in chunks[:4]:
        text = chunk.text.strip()
        # Pick a sentence that looks relevant.
        sentences = re.split(r"(?<=[.!?])\s+", text)
        picked = ""
        for s in sentences:
            sl = s.lower()
            if q_terms and any(t in sl for t in q_terms):
                picked = s.strip()
                break
        if not picked:
            picked = (sentences[0] if sentences else text[:280]).strip()
        if len(picked) > 320:
            picked = picked[:317].rstrip() + "…"
        ref = f"/{chunk.url}"
        if chunk.heading:
            ref += f" — {chunk.heading}"
        lines.append(f"- {picked} ({ref})")
    lines.append("\nSources: " + ", ".join(f"/{c.url}" for c in chunks[:4]))
    return "\n".join(lines)


def chat_answer(site, question: str, *, history: list[dict[str, str]] | None = None, limit: int = 5) -> dict[str, Any]:
    q = (question or "").strip()
    if not q:
        return {
            "answer": "Ask a question about the documentation.",
            "sources": [],
            "mode": "none",
        }
    index = get_index(site)
    chunks = index.retrieve(q, limit=max(1, limit))
    sources = [
        ChatSource(
            url="/" + c.url,
            title=c.title,
            heading=c.heading,
            excerpt=(c.text[:240] + "…") if len(c.text) > 240 else c.text,
        )
        for c in chunks
    ]
    answer = _call_llm(q, chunks, history=history)
    mode = "llm" if answer else "extractive"
    if not answer:
        answer = _extractive_answer(q, chunks)
    return {
        "answer": answer,
        "sources": [s.to_dict() for s in sources],
        "mode": mode,
        "docs_only": True,
    }
