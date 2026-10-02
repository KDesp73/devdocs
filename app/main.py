"""FastAPI application: discovery, navigation and routes."""

from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app import templates
from app.config import get_config
from app.naming import prettify
from app.render import (
    FileType,
    classify,
    first_heading,
    is_asset,
    language_label,
    media_type,
    plain_title,
    render_document,
    theme_style_css,
)
from app.site import Site, site
from app.themes import theme_css

STATIC_DIR = Path(__file__).parent / "static"
_ASSET_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    # Keeps standalone SVG (and friends) from executing scripts.
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:",
}

# devdocs serves the user's documentation, so FastAPI's own interactive
# reference (``/docs``, ``/redoc``, ``/openapi.json``) is turned off: those
# paths belong to the published docs, not to the devdocs API.
app = FastAPI(
    title=f"{get_config().title} Docs",
    version=get_config().version,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@dataclass(frozen=True)
class Entry:
    """A published file."""

    url: str
    rel: str
    path: Path
    file_type: FileType

    @property
    def label(self) -> str:
        return prettify(self.path.stem)


@dataclass(frozen=True)
class Discovery:
    """Files found under the docs directory, keyed by URL."""

    documents: dict[str, Entry]
    assets: dict[str, Entry]

    def get(self, url: str) -> Entry | None:
        return self.documents.get(url) or self.assets.get(url)


def _url_for(rel: str, file_type: FileType) -> str:
    """Markdown pages get extension-less URLs; everything else keeps its name."""
    if file_type.kind == "markdown":
        return rel.rsplit(".", 1)[0]
    return rel


def discover(current: Site) -> Discovery:
    """Walk the docs directory, honouring ignore rules and file types."""
    documents: dict[str, Entry] = {}
    assets: dict[str, Entry] = {}
    root = current.docs_dir
    if not root.is_dir():
        return Discovery(documents, assets)
    root = root.resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:  # pragma: no cover - rglob only yields descendants
            continue
        if current.config.is_ignored(rel):
            continue
        if path.is_symlink() and not path.resolve().is_relative_to(root):
            continue
        file_type = classify(path.suffix, current.types)
        if file_type is None:
            continue
        entry = Entry(_url_for(rel, file_type), rel, path, file_type)
        (assets if is_asset(file_type) else documents)[entry.url] = entry
    return Discovery(documents, assets)


_CHEVRON = (
    '<svg class="folder-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="9 18 15 12 9 6"/></svg>'
)
_FOLDER_ICON = (
    '<svg class="folder-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>'
)
_FILE_ICON = (
    '<svg class="file-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
    '<polyline points="14 2 14 8 20 8"/></svg>'
)
_PENCIL = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>'
    '<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>'
)


def _render_nav(tree: dict, current_path: str | None) -> list[str]:
    folders = sorted((name, node) for name, node in tree.items() if isinstance(node, dict))
    files = sorted(
        ((name, node) for name, node in tree.items() if not isinstance(node, dict)),
        key=lambda item: item[0].lower(),
    )
    lines: list[str] = []
    for name, node in folders:
        is_open = current_path is not None and _contains(node, current_path)
        open_cls = " open" if is_open else ""
        lines.append(
            f'<div class="nav-folder{open_cls}">'
            f'<div class="nav-folder-toggle" role="button" tabindex="0" '
            f'aria-expanded="{"true" if is_open else "false"}">'
            f"{_CHEVRON}{_FOLDER_ICON}"
            f'<span class="label">{html.escape(prettify(name))}</span>'
            f"</div>"
            f'<div class="nav-folder-items{open_cls}">'
            f"{chr(10).join(_render_nav(node, current_path))}"
            f"</div></div>"
        )
    for _name, entry in files:
        active = ' class="active" aria-current="page"' if entry.url == current_path else ""
        # ``entry.label`` rather than the URL segment: a page is called
        # "Openapi", not "Openapi Json" — the file type is shown as a tag.
        lines.append(
            f'<a href="/{html.escape(entry.url, quote=True)}"{active}>'
            f'{_FILE_ICON}<span class="label">{html.escape(entry.label)}</span></a>'
        )
    return lines


def _contains(node: dict, url: str) -> bool:
    for value in node.values():
        if isinstance(value, dict):
            if _contains(value, url):
                return True
        elif value.url == url:
            return True
    return False


def _build_tree(documents: dict[str, Entry]) -> dict:
    tree: dict = {}
    for entry in documents.values():
        parts = entry.url.split("/")
        node = tree
        for part in parts[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                child = {}
                node[part] = child
            node = child
        node[parts[-1]] = entry
    return tree


def _build_nav(documents: dict[str, Entry], current_path: str | None) -> str:
    return "\n".join(_render_nav(_build_tree(documents), current_path))


def _build_breadcrumbs(url: str, documents: dict[str, Entry]) -> str:
    if not url:
        return ""
    entry = documents.get(url)
    parts = url.split("/")
    crumbs = ['<div class="breadcrumbs"><a href="/">Home</a>']
    for index, part in enumerate(parts):
        # The last crumb is a page, so it uses the page's own label.
        text = entry.label if index == len(parts) - 1 and entry else prettify(part)
        label = html.escape(text)
        if index == len(parts) - 1:
            crumbs.append(f'<span class="sep">/</span><span>{label}</span>')
        else:
            href = html.escape("/" + "/".join(parts[: index + 1]), quote=True)
            crumbs.append(f'<span class="sep">/</span><a href="{href}">{label}</a>')
    crumbs.append("</div>")
    return "".join(crumbs)


def _build_edit_link(current: Site, entry: Entry) -> str:
    url = current.source_url(entry.rel)
    if not url:
        return ""
    label = "Edit this page on GitHub" if entry.file_type.kind == "markdown" else "View on GitHub"
    return (
        f'<a href="{html.escape(url, quote=True)}" class="edit-link" '
        f'target="_blank" rel="noopener">{_PENCIL}{label}</a>'
    )


def _build_raw_link(entry: Entry) -> str:
    if entry.file_type.kind == "markdown":
        return ""
    href = html.escape(f"/raw/{entry.url}", quote=True)
    return f'<a href="{href}" class="edit-link">{_FILE_ICON}View raw</a>'


def _document_body(entry: Entry) -> str:
    if entry.file_type.kind == "markdown":
        return render_document(entry.path, entry.file_type)
    header = (
        f"<h1>{html.escape(entry.label)}</h1>"
        '<div class="doc-meta">'
        f'<span class="path">{html.escape(entry.rel)}</span>'
        f'<span class="tag">{html.escape(language_label(entry.path, entry.file_type))}</span>'
        "</div>"
    )
    return header + render_document(entry.path, entry.file_type)


def _build_index(current: Site, documents: dict[str, Entry]) -> str:
    groups: dict[str, list[Entry]] = {}
    for entry in documents.values():
        parts = entry.url.split("/")
        groups.setdefault(parts[0] if len(parts) > 1 else "", []).append(entry)

    sections: list[str] = ["<h1>Documentation</h1>"]
    if not documents:
        sections.append(
            f'<p class="empty-state">Nothing published yet in '
            f"{html.escape(str(current.docs_dir))}.</p>"
        )
    for key in sorted(groups, key=lambda item: (item != "", item)):
        if key:
            sections.append(f'<div class="index-section">{html.escape(prettify(key))}</div>')
        sections.append('<div class="index-grid">')
        for entry in sorted(groups[key], key=lambda item: item.url):
            label = first_heading(entry.path) if entry.file_type.kind == "markdown" else entry.label
            label = label or entry.label
            sections.append(
                f'<a href="/{html.escape(entry.url, quote=True)}" class="index-card">'
                f'<div class="title">{html.escape(label)}</div>'
                f'<div class="path">/{html.escape(entry.url)}</div>'
                f"</a>"
            )
        sections.append("</div>")
    return "\n".join(sections)


def _page(
    current: Site,
    documents: dict[str, Entry],
    *,
    title: str,
    content: str,
    current_path: str | None = None,
    breadcrumbs: str = "",
    footer: str = "",
    status_code: int = 200,
) -> HTMLResponse:
    theme = current.theme
    document = templates.page(
        title=title,
        site_name=current.config.title,
        tagline=current.config.tagline,
        branch=current.branch,
        theme=current.config.theme or theme.name,
        theme_css=theme_css(theme.name),
        code_css=theme_style_css(theme.pygments),
        mermaid_theme=theme.mermaid,
        content=content,
        breadcrumbs=breadcrumbs,
        edit_link=footer,
        nav_links=_build_nav(documents, current_path),
        root_active="active" if not current_path else "",
    )
    return HTMLResponse(document, status_code=status_code)


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    current = site()
    documents = discover(current).documents
    return _page(
        current,
        documents,
        title="Documentation",
        content=_build_index(current, documents),
    )


@app.get("/raw/{url:path}")
async def raw_file(url: str) -> FileResponse:
    current = site()
    entry = discover(current).get(url.strip("/"))
    if entry is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(
        entry.path,
        media_type=media_type(entry.path),
        headers=dict(_ASSET_HEADERS),
    )


@app.get("/{url:path}", response_class=HTMLResponse)
async def render(url: str):
    current = site()
    key = url.strip("/")
    found = discover(current)
    asset = found.assets.get(key)
    if asset is not None:
        return FileResponse(
            asset.path,
            media_type=media_type(asset.path),
            headers=dict(_ASSET_HEADERS),
        )
    entry = found.documents.get(key)
    if entry is None:
        raise HTTPException(status_code=404, detail="Document not found")
    body = _document_body(entry)
    footer = _build_edit_link(current, entry) + _build_raw_link(entry)
    return _page(
        current,
        found.documents,
        title=plain_title(body, entry.label),
        content=body,
        current_path=entry.url,
        breadcrumbs=_build_breadcrumbs(entry.url, found.documents),
        footer=footer,
    )


@app.exception_handler(404)
async def handle_404(request: Request, exc: HTTPException) -> HTMLResponse:
    current = site()
    path = html.escape(request.url.path)
    return _page(
        current,
        discover(current).documents,
        title="Not found",
        content=(
            "<h1>404 &middot; Not found</h1>"
            f"<p>No document lives at <code>{path}</code>.</p>"
            '<p><a href="/">Back to the index</a></p>'
        ),
        status_code=404,
    )
