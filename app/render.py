"""File type registry and renderers.

``devdocs.yml`` decides which file types are published through the
``file_types`` list.  Types that cannot sensibly be rendered as a page
(images) are served verbatim and left out of the navigation tree; everything
else becomes a page in the documentation layout.
"""

from __future__ import annotations

import html
import json
import mimetypes
import re
from dataclasses import dataclass, field
from functools import cache, lru_cache
from pathlib import Path

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_for_filename
from pygments.util import ClassNotFound

__all__ = [
    "FileType",
    "ResolvedTypes",
    "classify",
    "default_types",
    "first_heading",
    "is_asset",
    "language_label",
    "media_type",
    "plain_title",
    "render_document",
    "resolve_types",
    "theme_style_css",
]

MAX_RENDER_BYTES = 2_000_000
_HEADING_SCAN_LINES = 200
MARKDOWN_EXTENSIONS = ["fenced_code", "codehilite", "tables", "toc", "sane_lists"]

_MD_LINK_SUFFIX = re.compile(r"\.md(?=#|$)")
_MERMAID_BLOCK = re.compile(
    r"^(?P<fence>`{3,}|~{3,})[ \t]*mermaid[^\n]*\n(?P<body>.*?)^(?P=fence)[ \t]*$",
    re.DOTALL | re.MULTILINE,
)
_HTML = re.compile(r"<[^>]+>")

_IMAGE_EXTS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".webp",
        ".avif",
        ".ico",
        ".bmp",
        ".tif",
        ".tiff",
    }
)
_ASSET_CONTENT_TYPES = {
    ".md": "text/markdown; charset=utf-8",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".avif": "image/avif",
}


@dataclass(frozen=True)
class FileType:
    """How a family of file extensions is published."""

    kind: str
    exts: frozenset[str] | None = None
    label: str = ""
    dynamic: bool = False

    @property
    def renderable(self) -> bool:
        return self.kind != "image"


_GROUPS: dict[str, FileType] = {
    "md": FileType("markdown", frozenset({".md", ".markdown", ".mdown"}), "Markdown"),
    "markdown": FileType("markdown", frozenset({".md", ".markdown", ".mdown"}), "Markdown"),
    "images": FileType("image", _IMAGE_EXTS, "Image"),
    "image": FileType("image", _IMAGE_EXTS, "Image"),
    "json": FileType("json", frozenset({".json", ".jsonc"}), "JSON"),
    "yaml": FileType("yaml", frozenset({".yaml", ".yml"}), "YAML"),
    "toml": FileType("code", frozenset({".toml", ".ini", ".cfg", ".properties"}), "TOML"),
    "xml": FileType("code", frozenset({".xml", ".xsd", ".xsl", ".plist", ".svgz"}), "XML"),
    "text": FileType(
        "code",
        frozenset({".txt", ".text", ".log", ".csv", ".tsv", ".rst", ".env", ".editorconfig"}),
        "Text",
    ),
    "code": FileType("code", None, "Code", dynamic=True),
}

_EXT_LANGUAGES = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".mdown": "markdown",
    ".json": "json",
    ".jsonc": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".env": "bash",
    ".log": "text",
    ".txt": "text",
}


@dataclass(frozen=True)
class ResolvedTypes:
    """The set of file types enabled by configuration."""

    extensions: frozenset[str] = frozenset()
    dynamic_code: bool = False
    unknown: tuple[str, ...] = field(default=())

    def matches(self, suffix: str) -> bool:
        if suffix in self.extensions:
            return True
        if not self.dynamic_code:
            return False
        return _is_known_code(suffix)


def default_types() -> list[str]:
    return ["md"]


def resolve_types(names: object) -> ResolvedTypes:
    """Turn the ``file_types`` config value into a :class:`ResolvedTypes`."""
    if names is None:
        names = default_types()
    if isinstance(names, str):
        names = [names]
    if not isinstance(names, (list, tuple, set)):
        return ResolvedTypes()

    extensions: set[str] = set()
    dynamic_code = False
    unknown: list[str] = []
    for raw in names:
        if not isinstance(raw, str):
            continue
        name = raw.strip().lower()
        if not name:
            continue
        if name in {"all", "*"}:
            for group in _GROUPS.values():
                if group.dynamic:
                    dynamic_code = True
                elif group.exts:
                    extensions.update(group.exts)
            continue
        if name.startswith("."):
            extensions.add(name)
            continue
        group = _GROUPS.get(name)
        if group is None:
            unknown.append(raw.strip())
            continue
        if group.dynamic:
            dynamic_code = True
        elif group.exts:
            extensions.update(group.exts)
    return ResolvedTypes(
        extensions=frozenset(extensions),
        dynamic_code=dynamic_code,
        unknown=tuple(unknown),
    )


@cache
def _known_code_extensions() -> frozenset[str]:
    from pygments.lexers import get_all_lexers

    found: set[str] = set()
    for _name, _aliases, filenames, _mimetypes in get_all_lexers():
        for pattern in filenames:
            if pattern.startswith("*.") and len(pattern) > 2:
                found.add("." + pattern[2:].rsplit(".", 1)[-1].lower())
    return frozenset(found)


def _is_known_code(suffix: str) -> bool:
    return suffix in _known_code_extensions()


def classify(suffix: str, types: ResolvedTypes) -> FileType | None:
    """Return the :class:`FileType` for a lowercase file suffix, if enabled."""
    suffix = suffix.lower()
    if not types.matches(suffix):
        return None
    for group in _GROUPS.values():
        if group.exts and suffix in group.exts:
            return group
    # Enabled explicitly (or via the dynamic "code" group) but not in a named
    # group: treat it as code and let Pygments guess the lexer.
    return _GROUPS["code"]


def is_asset(file_type: FileType) -> bool:
    return not file_type.renderable


def media_type(path: Path) -> str:
    """Best effort content type for serving a file verbatim."""
    suffix = path.suffix.lower()
    if suffix in _ASSET_CONTENT_TYPES:
        return _ASSET_CONTENT_TYPES[suffix]
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed is None:
        return "application/octet-stream"
    if guessed.startswith("text/") or guessed in {"application/json", "image/svg+xml"}:
        return f"{guessed}; charset=utf-8"
    return guessed


def _prepare_mermaid(raw: str) -> str:
    """Replace fenced mermaid blocks with divs before markdown runs.

    The diagram source is HTML escaped so Markdown cannot interpret it and the
    browser hands the original text back to Mermaid through ``textContent``.
    """

    def repl(match: re.Match[str]) -> str:
        body = html.escape(match.group("body").strip(), quote=False)
        return f'<div class="mermaid">\n{body}\n</div>'

    return _MERMAID_BLOCK.sub(repl, raw)


def _rewrite_doc_links(rendered: str) -> str:
    """Strip ``.md`` from relative hrefs so links match the URL routes."""

    def rewrite_href(match: re.Match[str]) -> str:
        quote = match.group(1)
        href = match.group(2)
        if href.startswith(("http://", "https://", "mailto:", "tel:", "#", "//")):
            return match.group(0)
        new_href = _MD_LINK_SUFFIX.sub("", href)
        if new_href == href:
            return match.group(0)
        return f"href={quote}{new_href}{quote}"

    return re.sub(r'href=(["\'])(.*?)\1', rewrite_href, rendered)


def render_markdown(path: Path) -> str:
    """Render a Markdown file to an HTML fragment."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    rendered = markdown.markdown(
        _prepare_mermaid(raw),
        extensions=MARKDOWN_EXTENSIONS,
        extension_configs={"codehilite": {"css_class": "codehilite"}},
    )
    return _rewrite_doc_links(rendered)


def first_heading(path: Path) -> str | None:
    """Read the first level 1 Markdown heading without rendering the file."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for _ in range(_HEADING_SCAN_LINES):
                line = handle.readline()
                if not line:
                    break
                if line.startswith("# ") or line.startswith("#\t"):
                    return line.lstrip("# \t").strip()
    except OSError:
        return None
    return None


@lru_cache(maxsize=128)
def _formatter(line_numbers: bool) -> HtmlFormatter:
    return HtmlFormatter(
        cssclass="codehilite",
        linenos="table" if line_numbers else False,
    )


@lru_cache(maxsize=128)
def theme_style_css(style: str) -> str:
    """Pygments stylesheet for a theme, using the ``codehilite`` class names."""
    formatter = HtmlFormatter(cssclass="codehilite", style=style)
    return formatter.get_style_defs(".codehilite")


def _lexer_for(path: Path):
    if path.suffix.lower() in _EXT_LANGUAGES:
        return None
    try:
        return get_lexer_for_filename(path.name, stripnl=False)
    except ClassNotFound:
        return TextLexer(stripnl=False)


def _read_source(path: Path) -> tuple[str, int, bool]:
    size = path.stat().st_size
    truncated = size > MAX_RENDER_BYTES
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        text = handle.read(MAX_RENDER_BYTES)
    return text, size, truncated


def render_source(path: Path) -> str:
    """Render a source or data file as a highlighted listing."""
    text, size, truncated = _read_source(path)
    if path.suffix.lower() == ".json":
        text = _pretty_json(text)
    lexer = _lexer_for(path) or TextLexer(stripnl=False)
    body = highlight(text, lexer, _formatter(line_numbers=True))
    if truncated:
        body += (
            f'\n<p class="doc-note">Truncated to '
            f"{MAX_RENDER_BYTES // 1000} kB of {size // 1000} kB.</p>"
        )
    return body


def _pretty_json(text: str) -> str:
    try:
        parsed = json.loads(text)
    except (ValueError, RecursionError):
        return text
    if not isinstance(parsed, (dict, list)):
        return text
    return json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"


def render_document(path: Path, file_type: FileType) -> str:
    """Render a file into the HTML body of a documentation page."""
    if file_type.kind == "markdown":
        return render_markdown(path)
    return render_source(path)


def language_label(path: Path, file_type: FileType) -> str:
    """Short label describing what a document is, shown in the page header."""
    if file_type.kind == "markdown":
        return "Markdown"
    if file_type.kind == "json":
        return "JSON"
    if file_type.kind == "yaml":
        return "YAML"
    suffix = path.suffix.lower().lstrip(".")
    if suffix:
        return suffix.upper() if len(suffix) <= 5 else file_type.label
    return file_type.label or "Text"


def plain_title(rendered: str, fallback: str) -> str:
    """Best effort plain text page title from a rendered HTML fragment."""
    match = re.search(r"<h1[^>]*>(.*?)</h1>", rendered, re.DOTALL)
    if not match:
        return fallback
    text = _HTML.sub("", match.group(1))
    text = html.unescape(text).strip()
    return text or fallback
