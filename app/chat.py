"""Docs-only chat/retrieval assistant.

The chat feature uses a configured OpenAI-compatible LLM endpoint to answer
questions grounded in retrieved documentation excerpts. If chat is not
configured or the LLM endpoint is unavailable, the feature is disabled.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.config import load_devdocs_dotenv
from app.search import get_index

__all__ = ["chat_answer", "chat_enabled", "chat_status"]


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


_STATUS_TTL_SECONDS = 60.0
_chat_status_cache: dict[str, Any] = {"key": None, "ok": False, "ts": 0.0, "model": None}


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


def _config_key(cfg: dict[str, str]) -> tuple[str, str, str]:
    return (cfg["base_url"], cfg["model"], cfg["api_key"])


def _probe_llm(cfg: dict[str, str]) -> bool:
    """Best-effort availability probe for an OpenAI-compatible endpoint."""
    headers = {"Authorization": f"Bearer {cfg['api_key']}"}
    req = urllib.request.Request(cfg["base_url"] + "/models", headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310
            status = getattr(resp, "status", 200)
            if 200 <= int(status) < 300:
                return True
    except Exception:
        pass

    # Fallback: some providers may not expose /models; try a minimal completion.
    payload = {
        "model": cfg["model"],
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
        "temperature": 0,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        cfg["base_url"] + "/chat/completions",
        data=data,
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            status = getattr(resp, "status", 200)
            return 200 <= int(status) < 300
    except Exception:
        return False


def chat_status(*, force: bool = False) -> dict[str, Any]:
    """Return whether chat is enabled/available and the active model if so."""
    load_devdocs_dotenv()
    cfg = _llm_config()
    if not cfg:
        _chat_status_cache.update({"key": None, "ok": False, "ts": time.time(), "model": None})
        return {"enabled": False, "model": None, "reason": "not_configured"}

    key = _config_key(cfg)
    now = time.time()
    if (
        not force
        and _chat_status_cache.get("key") == key
        and (now - float(_chat_status_cache.get("ts") or 0.0)) < _STATUS_TTL_SECONDS
    ):
        ok = bool(_chat_status_cache.get("ok"))
        return {
            "enabled": ok,
            "model": cfg["model"] if ok else None,
            "reason": None if ok else "unavailable",
        }

    ok = _probe_llm(cfg)
    _chat_status_cache.update({"key": key, "ok": ok, "ts": now, "model": cfg["model"] if ok else None})
    return {
        "enabled": ok,
        "model": cfg["model"] if ok else None,
        "reason": None if ok else "unavailable",
    }


def chat_enabled(*, force: bool = False) -> bool:
    return bool(chat_status(force=force).get("enabled"))


def _build_context(chunks) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        heading = f" — {chunk.heading}" if chunk.heading else ""
        parts.append(
            f"[Source {i}] {chunk.title}{heading} ({'/' + chunk.url})\n{chunk.text}"
        )
    return "\n\n".join(parts)


def _call_llm(
    cfg: dict[str, str] | None,
    question: str,
    chunks,
    history: list[dict[str, str]] | None = None,
) -> str | None:
    if not cfg or not chunks:
        return None
    context = _build_context(chunks)
    system = (
        "You are the documentation assistant for this site. Answer using ONLY the provided "
        "documentation excerpts. Do not use outside knowledge. "
        "Be concise: respond in 1-5 short sentences or a few brief bullets. "
        "Cite relevant source paths inline (e.g. /path/to/page). "
        "If the answer is not in the excerpts, briefly say so and point to the closest relevant source path."
    )
    user = (
        f"Documentation excerpts:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer concisely based only on the excerpts above and include source paths."
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


def _disabled_response(reason: str | None = None) -> dict[str, Any]:
    msg = "Chat is unavailable. Configure a reachable LLM endpoint to enable it."
    if reason == "not_configured":
        msg = "Chat is not configured. Set the LLM environment variables to enable it."
    return {
        "answer": msg,
        "sources": [],
        "mode": "disabled",
        "model": None,
        "docs_only": True,
        "enabled": False,
    }


def chat_answer(site, question: str, *, history: list[dict[str, str]] | None = None, limit: int = 5) -> dict[str, Any]:
    status = chat_status()
    if not status.get("enabled"):
        return _disabled_response(status.get("reason"))

    q = (question or "").strip()
    if not q:
        return {
            "answer": "Ask a question about the documentation.",
            "sources": [],
            "mode": "llm",
            "model": status.get("model"),
            "docs_only": True,
            "enabled": True,
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
    if not chunks:
        return {
            "answer": "No relevant documentation found. Try a different question or use search.",
            "sources": [],
            "mode": "llm",
            "model": status.get("model"),
            "docs_only": True,
            "enabled": True,
        }

    cfg = _llm_config()
    if not cfg:
        return _disabled_response("not_configured")

    answer = _call_llm(cfg, q, chunks, history=history)
    if not answer:
        # Endpoint/config was considered available recently but failed now; disable.
        _chat_status_cache.update({"key": _config_key(cfg), "ok": False, "ts": time.time(), "model": None})
        return _disabled_response("unavailable")

    return {
        "answer": answer,
        "sources": [s.to_dict() for s in sources],
        "mode": "llm",
        "model": cfg["model"],
        "docs_only": True,
        "enabled": True,
    }
