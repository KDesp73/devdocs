"""YAML front matter parsing for documentation files.

Documents may begin with a YAML header delimited by ``---`` lines, for example::

    ---
    title: Getting started
    description: Install and run the project.
    tags: [setup, intro]
    order: 10
    ---
    # Body starts here

The header is optional. When present, metadata is used for titles, search and
navigation, while the body is rendered as usual.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "DocumentMeta",
    "load_document",
    "parse_frontmatter",
    "read_frontmatter",
    "split_frontmatter",
    "strip_frontmatter",
]

_FM_RE = re.compile(
    r"\A---[ \t]*\r?\n(?P<meta>.*?\r?\n)(?:---|\.\.\.)[ \t]*(?:\r?\n|\Z)",
    re.DOTALL,
)


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return ``(metadata, body)`` from a document string.

    Invalid or non-mapping front matter is ignored so existing documents keep
    rendering exactly as before.
    """
    match = _FM_RE.match(text)
    if not match:
        return {}, text
    raw = match.group("meta")
    try:
        data = yaml.safe_load(raw)
    except Exception:
        return {}, text
    if data is None:
        return {}, text[match.end() :]
    if not isinstance(data, dict):
        return {}, text
    return data, text[match.end() :]


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Return only the metadata mapping from a document string."""
    return split_frontmatter(text)[0]


def strip_frontmatter(text: str) -> str:
    """Return the document body without front matter."""
    return split_frontmatter(text)[1]


def read_frontmatter(path: Path, *, max_bytes: int = 65_536) -> dict[str, Any]:
    """Read front matter from ``path`` without loading the whole file."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            head = handle.read(max_bytes)
    except OSError:
        return {}
    # If the header is larger than the prefix we read, fall back to a full read.
    if head.startswith("---") and "\n---" not in head[4:] and "\n..." not in head[4:]:
        try:
            head = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return {}
    return parse_frontmatter(head)


def _as_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def _as_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = re.split(r"[,]+", value)
    elif isinstance(value, (list, tuple, set)):
        items = value
    else:
        return []
    tags: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _as_str(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        tags.append(text)
    return tags


def _as_order(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


class DocumentMeta:
    """Normalized view of a document's front matter."""

    __slots__ = (
        "raw",
        "title",
        "label",
        "description",
        "tags",
        "order",
        "draft",
        "hidden",
    )

    def __init__(self, raw: dict[str, Any] | None = None) -> None:
        data = raw or {}
        self.raw: dict[str, Any] = data
        self.title: str = _as_str(data.get("title"))
        self.label: str = _as_str(
            data.get("sidebar_label") or data.get("nav_label") or data.get("label")
        )
        self.description: str = _as_str(
            data.get("description") or data.get("summary") or data.get("excerpt")
        )
        self.tags: list[str] = _as_tags(data.get("tags") or data.get("labels"))
        self.order: float | None = _as_order(
            data.get("order") if "order" in data else data.get("weight")
        )
        self.draft: bool = bool(data.get("draft", False))
        self.hidden: bool = bool(data.get("hidden", False))

    @property
    def visible(self) -> bool:
        return not (self.draft or self.hidden)

    @property
    def nav_title(self) -> str:
        return self.label or self.title

    def get(self, key: str, default: Any = None) -> Any:
        return self.raw.get(key, default)


def load_document(path: Path) -> tuple[DocumentMeta, str, str]:
    """Read a document and return ``(meta, body, raw_text)``."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return DocumentMeta(), "", ""
    data, body = split_frontmatter(raw)
    return DocumentMeta(data), body, raw

