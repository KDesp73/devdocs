"""HTML shell for every page.

The document is intentionally plain: semantic markup, inline colour theme and
Pygments styles, and two static assets served from ``/static``.
"""

from __future__ import annotations

import html
import json

__all__ = ["MERMAID_CDN", "page"]

MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"
_STATIC = "/static"

_HOME_ICON = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
    '<polyline points="9 22 9 12 15 12 15 22"/></svg>'
)

_DIALOG = """<dialog id="mermaid-dialog" class="mermaid-dialog" aria-labelledby="mermaid-dialog-title">
  <div class="mermaid-dialog-header">
    <span id="mermaid-dialog-title" class="mermaid-dialog-title">Diagram</span>
    <div class="mermaid-dialog-toolbar">
      <button type="button" id="mermaid-zoom-out" title="Zoom out" aria-label="Zoom out">&minus;</button>
      <button type="button" id="mermaid-zoom-reset" title="Reset zoom">Reset</button>
      <button type="button" id="mermaid-zoom-in" title="Zoom in" aria-label="Zoom in">+</button>
      <span id="mermaid-zoom-level" class="zoom-level" aria-live="polite">100%</span>
      <button type="button" id="mermaid-zoom-fit" title="Fit to view">Fit</button>
      <button type="button" class="mermaid-dialog-close" id="mermaid-dialog-close" title="Close" aria-label="Close">&times;</button>
    </div>
  </div>
  <div class="mermaid-dialog-body">
    <div class="mermaid-dialog-viewport" id="mermaid-dialog-viewport">
      <div class="mermaid-dialog-canvas" id="mermaid-dialog-canvas"></div>
    </div>
    <div class="mermaid-dialog-footer">Scroll to zoom &middot; drag to pan &middot; double click to fit &middot; Esc to close</div>
  </div>
</dialog>"""


def _topbar(site_name: str, tagline: str, branch: str) -> str:
    branch_html = ""
    if branch:
        branch_html = (
            '<span class="branch" title="Branch used for &quot;Edit on GitHub&quot; links">'
            f"{html.escape(branch)}</span>"
        )
    return f"""<div class="top-bar">
  <h1><a href="/"><span>{html.escape(site_name)}</span> Docs</a></h1>
  <span class="tagline">{html.escape(tagline)}</span>
  <span class="spacer"></span>
  {branch_html}
</div>"""


def page(
    *,
    title: str,
    site_name: str,
    tagline: str,
    branch: str = "",
    theme: str = "original",
    theme_css: str = "",
    code_css: str = "",
    mermaid_theme: str = "neutral",
    content: str,
    breadcrumbs: str = "",
    edit_link: str = "",
    nav_links: str = "",
    root_active: str = "",
) -> str:
    """Assemble a full HTML document."""
    document_title = html.escape(f"{title} — {site_name} Docs")
    client_config = json.dumps({"mermaid": {"theme": mermaid_theme, "url": MERMAID_CDN}})
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="{html.escape(theme)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{document_title}</title>
<style>
{theme_css}
</style>
<style>
{code_css}
</style>
<link rel="stylesheet" href="{_STATIC}/devdocs.css">
<script type="application/json" id="devdocs-config">{client_config}</script>
</head>
<body>
{_topbar(site_name, tagline, branch)}
<div class="wrapper">
<nav aria-label="Documentation">
  <a href="/" class="{root_active}">{_HOME_ICON} <span class="label">Home</span></a>
{nav_links}
</nav>
<main class="content">
{breadcrumbs}
<div class="doc-card">
{content}
{edit_link}
</div>
</main>
</div>
{_DIALOG}
<script src="{MERMAID_CDN}"></script>
<script src="{_STATIC}/devdocs.js" defer></script>
</body>
</html>"""
