from pathlib import Path
import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

import markdown

from app.config import get_config

cfg = get_config()
DOCS_DIR = cfg.docs_path
GITHUB_REPO = cfg.github_repo
GITHUB_BRANCH = cfg.github_branch

app = FastAPI(title=f"{cfg.title} Docs", version=cfg.version)


def _discover_docs() -> dict[str, Path]:
    files: dict[str, Path] = {}
    for md_file in sorted(DOCS_DIR.rglob("*.md")):
        rel = md_file.relative_to(DOCS_DIR)
        rel_str = str(rel)
        if cfg.is_ignored(rel_str):
            continue
        url_path = str(rel.with_suffix(""))
        files[url_path] = md_file
    return files


_MD_LINK_SUFFIX = re.compile(r"\.md(?=#|$)")
_MERMAID_BLOCK = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)


def _prepare_mermaid(raw: str) -> str:
    """Replace fenced mermaid blocks with divs before markdown/codehilite runs."""

    def repl(match: re.Match[str]) -> str:
        return f'<div class="mermaid">\n{match.group(1).strip()}\n</div>'

    return _MERMAID_BLOCK.sub(repl, raw)


def _rewrite_doc_links(html: str) -> str:
    """Strip .md from relative hrefs so links match URL routes (no file extension)."""

    def rewrite_href(match: re.Match[str]) -> str:
        quote = match.group(1)
        href = match.group(2)
        if href.startswith(("http://", "https://", "mailto:", "#", "//")):
            return match.group(0)
        new_href = _MD_LINK_SUFFIX.sub("", href)
        if new_href == href:
            return match.group(0)
        return f"href={quote}{new_href}{quote}"

    return re.sub(r'href=(["\'])(.*?)\1', rewrite_href, html)


def _render_md(md_path: Path) -> str:
    raw = md_path.read_text(encoding="utf-8")
    raw = _prepare_mermaid(raw)
    html_body = markdown.markdown(
        raw,
        extensions=["fenced_code", "codehilite", "tables", "toc"],
    )
    return _rewrite_doc_links(html_body)


HTML_LAYOUT = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — {site_name} Docs</title>
<style>
  :root {{
    --slate-50: #f8fafc;
    --slate-100: #f1f5f9;
    --slate-200: #e2e8f0;
    --slate-300: #cbd5e1;
    --slate-400: #94a3b8;
    --slate-500: #64748b;
    --slate-600: #475569;
    --slate-700: #334155;
    --slate-800: #1e293b;
    --slate-900: #0f172a;
    --blue-50: #eff6ff;
    --blue-100: #dbeafe;
    --blue-500: #3b82f6;
    --blue-600: #2563eb;
    --blue-700: #1d4ed8;
  }}

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
      Oxygen, Ubuntu, Cantarell, sans-serif;
    font-size: 16px;
    line-height: 1.7;
    color: var(--slate-800);
    background: var(--slate-100);
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }}

  /* ---- header ---- */
  .top-bar {{
    background: #fff;
    border-bottom: 1px solid var(--slate-200);
    height: 56px;
    display: flex;
    align-items: center;
    padding: 0 1.5rem;
    position: sticky;
    top: 0;
    z-index: 50;
  }}
  .top-bar h1 {{
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--slate-900);
    letter-spacing: -0.01em;
  }}
  .top-bar h1 a {{
    text-decoration: none;
    color: inherit;
  }}
  .top-bar h1 span {{
    color: var(--blue-500);
  }}
  .top-bar .tagline {{
    margin-left: 1rem;
    font-size: 0.85rem;
    color: var(--slate-400);
    font-weight: 400;
  }}

  /* ---- wrapper (sidebar + main) ---- */
  .wrapper {{
    display: flex;
    flex: 1;
  }}

  /* ---- sidebar ---- */
  nav {{
    width: 270px;
    background: #fff;
    border-right: 1px solid var(--slate-200);
    padding: 1rem 0;
    position: sticky;
    top: 56px;
    height: calc(100vh - 56px);
    overflow-y: auto;
    flex-shrink: 0;
  }}
  nav .nav-label {{
    padding: 0.6rem 1.25rem 0.25rem;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--slate-400);
  }}
  nav a {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.45rem 1.25rem;
    color: var(--slate-600);
    text-decoration: none;
    font-size: 0.875rem;
    border-left: 2px solid transparent;
    transition: background 0.12s, color 0.12s, border-color 0.12s;
  }}
  nav a:hover {{
    background: var(--blue-50);
    color: var(--blue-700);
  }}
  nav a.active {{
    background: var(--blue-50);
    color: var(--blue-700);
    border-left-color: var(--blue-500);
    font-weight: 500;
  }}

  /* ---- main ---- */
  .content {{
    flex: 1;
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem 2.5rem;
  }}

  /* breadcrumbs */
  .breadcrumbs {{
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    color: var(--slate-400);
    margin-bottom: 1.25rem;
  }}
  .breadcrumbs a {{
    color: var(--slate-500);
    text-decoration: none;
  }}
  .breadcrumbs a:hover {{
    color: var(--blue-600);
  }}

  /* doc card */
  .doc-card {{
    background: #fff;
    border: 1px solid var(--slate-200);
    border-radius: 10px;
    padding: 2rem 2.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }}

  /* headings */
  .doc-card h1 {{
    font-size: 1.85rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin-bottom: 1.5rem;
    color: var(--slate-900);
  }}
  .doc-card h2 {{
    font-size: 1.35rem;
    font-weight: 600;
    margin-top: 2rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid var(--slate-200);
    color: var(--slate-900);
  }}
  .doc-card h3 {{
    font-size: 1.1rem;
    font-weight: 600;
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
    color: var(--slate-800);
  }}
  .doc-card h4 {{
    font-size: 1rem;
    font-weight: 600;
    margin-top: 1.25rem;
    margin-bottom: 0.5rem;
    color: var(--slate-700);
  }}

  .doc-card p {{ margin-bottom: 1rem; }}
  .doc-card ul, .doc-card ol {{ margin-bottom: 1rem; padding-left: 1.5rem; }}
  .doc-card li {{ margin-bottom: 0.3rem; }}
  .doc-card li > ul, .doc-card li > ol {{ margin-bottom: 0; }}

  /* tables */
  .doc-card table {{
    border-collapse: collapse;
    width: 100%;
    margin-bottom: 1.25rem;
    font-size: 0.9rem;
  }}
  .doc-card th, .doc-card td {{
    border: 1px solid var(--slate-200);
    padding: 0.55rem 0.85rem;
    text-align: left;
    vertical-align: top;
  }}
  .doc-card th {{
    background: var(--slate-50);
    font-weight: 600;
    color: var(--slate-700);
  }}
  .doc-card tr:nth-child(even) td {{
    background: var(--slate-50);
  }}

  /* inline code */
  .doc-card code {{
    background: var(--slate-100);
    padding: 0.15rem 0.4rem;
    border-radius: 4px;
    font-size: 0.85em;
    font-family: "SF Mono", "Fira Code", "Fira Mono", Menlo, Consolas, monospace;
    color: #be123c;
  }}

  /* code blocks */
  .doc-card pre {{
    background: var(--slate-900);
    color: #e2e8f0;
    border-radius: 8px;
    padding: 1.1rem 1.25rem;
    overflow-x: auto;
    margin-bottom: 1.25rem;
    font-size: 0.85rem;
    line-height: 1.55;
    font-family: "SF Mono", "Fira Code", "Fira Mono", Menlo, Consolas, monospace;
  }}
  .doc-card pre code {{
    background: transparent;
    padding: 0;
    border-radius: 0;
    font-size: inherit;
    color: inherit;
  }}

  /* blockquote */
  .doc-card blockquote {{
    border-left: 4px solid var(--blue-500);
    padding: 0.65rem 1.1rem;
    margin-bottom: 1rem;
    background: var(--blue-50);
    border-radius: 0 6px 6px 0;
    color: var(--slate-700);
  }}
  .doc-card blockquote p:last-child {{ margin-bottom: 0; }}

  .doc-card a {{
    color: var(--blue-600);
    text-decoration: none;
  }}
  .doc-card a:hover {{
    text-decoration: underline;
  }}
  .doc-card img {{
    max-width: 100%;
    height: auto;
    border-radius: 6px;
    border: 1px solid var(--slate-200);
    margin: 0.5rem 0;
  }}
  .doc-card hr {{
    border: none;
    border-top: 1px solid var(--slate-200);
    margin: 1.5rem 0;
  }}

  /* mermaid diagrams */
  .doc-card .mermaid {{
    margin: 1.25rem 0;
    padding: 1rem;
    background: var(--slate-50);
    border: 1px solid var(--slate-200);
    border-radius: 8px;
    overflow-x: auto;
    text-align: center;
    cursor: zoom-in;
    transition: border-color 0.15s, box-shadow 0.15s;
  }}
  .doc-card .mermaid:hover {{
    border-color: var(--blue-500);
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.12);
  }}
  .doc-card .mermaid:focus-visible {{
    outline: 2px solid var(--blue-500);
    outline-offset: 2px;
  }}
  .mermaid-hint {{
    display: block;
    margin-top: 0.35rem;
    font-size: 0.75rem;
    color: var(--slate-400);
    text-align: center;
  }}

  /* mermaid explorer dialog */
  .mermaid-dialog {{
    border: none;
    border-radius: 12px;
    padding: 0;
    width: min(96vw, 1200px);
    height: min(92vh, 900px);
    max-width: none;
    max-height: none;
    margin: 0;
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: #fff;
    box-shadow: 0 25px 50px rgba(15, 23, 42, 0.25);
  }}
  .mermaid-dialog[open] {{
    display: flex;
    flex-direction: column;
  }}
  .mermaid-dialog::backdrop {{
    background: rgba(15, 23, 42, 0.55);
  }}
  .mermaid-dialog-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.85rem 1.25rem;
    border-bottom: 1px solid var(--slate-200);
    background: var(--slate-50);
    border-radius: 12px 12px 0 0;
    flex-shrink: 0;
  }}
  .mermaid-dialog-title {{
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--slate-800);
  }}
  .mermaid-dialog-toolbar {{
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }}
  .mermaid-dialog-toolbar button {{
    border: 1px solid var(--slate-200);
    background: #fff;
    color: var(--slate-700);
    border-radius: 6px;
    padding: 0.35rem 0.65rem;
    font-size: 0.8rem;
    cursor: pointer;
    line-height: 1.2;
  }}
  .mermaid-dialog-toolbar button:hover {{
    border-color: var(--blue-500);
    color: var(--blue-700);
    background: var(--blue-50);
  }}
  .mermaid-dialog-close {{
    border: none;
    background: transparent;
    color: var(--slate-500);
    font-size: 1.4rem;
    line-height: 1;
    cursor: pointer;
    padding: 0.15rem 0.35rem;
    border-radius: 6px;
  }}
  .mermaid-dialog-close:hover {{
    background: var(--slate-200);
    color: var(--slate-800);
  }}
  .mermaid-dialog-body {{
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }}
  .mermaid-dialog-viewport {{
    flex: 1;
    overflow: hidden;
    cursor: grab;
    background:
      radial-gradient(circle at 1px 1px, var(--slate-200) 1px, transparent 0);
    background-size: 20px 20px;
    background-color: #fff;
    position: relative;
    touch-action: none;
  }}
  .mermaid-dialog-viewport.is-dragging {{
    cursor: grabbing;
  }}
  .mermaid-dialog-canvas {{
    position: absolute;
    top: 50%;
    left: 50%;
    transform-origin: center center;
    will-change: transform;
  }}
  .mermaid-dialog-canvas .mermaid {{
    margin: 0;
    padding: 1.5rem;
    border: none;
    background: transparent;
    cursor: inherit;
  }}
  .mermaid-dialog-footer {{
    padding: 0.5rem 1.25rem;
    border-top: 1px solid var(--slate-200);
    font-size: 0.75rem;
    color: var(--slate-400);
    background: var(--slate-50);
    border-radius: 0 0 12px 12px;
    flex-shrink: 0;
  }}

  /* edit link */
  .edit-link {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    margin-top: 2rem;
    font-size: 0.8rem;
    color: var(--slate-400);
    text-decoration: none;
  }}
  .edit-link:hover {{
    color: var(--blue-600);
  }}

  /* ---- index page ---- */
  .index-section {{
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--slate-400);
    margin: 1.5rem 0 0.6rem;
  }}
  .index-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 0.75rem;
    margin-bottom: 0.5rem;
  }}
  .index-card {{
    background: #fff;
    border: 1px solid var(--slate-200);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    display: block;
    text-decoration: none;
    color: inherit;
    transition: border-color 0.15s, box-shadow 0.15s;
  }}
  .index-card:hover {{
    border-color: var(--blue-500);
    box-shadow: 0 2px 8px rgba(59,130,246,0.1);
  }}
  .index-card .title {{
    font-weight: 500;
    font-size: 0.92rem;
    color: var(--slate-900);
  }}
  .index-card .path {{
    font-size: 0.78rem;
    color: var(--slate-400);
    margin-top: 0.15rem;
    font-family: "SF Mono", "Fira Code", Menlo, Consolas, monospace;
  }}
</style>
</head>
<body>
<div class="top-bar">
  <h1><a href="/"><span>{site_name}</span> Docs</a></h1>
  <span class="tagline">{tagline}</span>
</div>
<div class="wrapper">
<nav>
  <a href="/" class="{root_active}"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg> Home</a>
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
<dialog id="mermaid-dialog" class="mermaid-dialog" aria-labelledby="mermaid-dialog-title">
  <div class="mermaid-dialog-header">
    <span id="mermaid-dialog-title" class="mermaid-dialog-title">Diagram</span>
    <div class="mermaid-dialog-toolbar">
      <button type="button" id="mermaid-zoom-out" title="Zoom out">−</button>
      <button type="button" id="mermaid-zoom-reset" title="Reset view">Reset</button>
      <button type="button" id="mermaid-zoom-in" title="Zoom in">+</button>
      <button type="button" id="mermaid-zoom-fit" title="Fit to view">Fit</button>
      <button type="button" class="mermaid-dialog-close" id="mermaid-dialog-close" title="Close" aria-label="Close">&times;</button>
    </div>
  </div>
  <div class="mermaid-dialog-body">
    <div class="mermaid-dialog-viewport" id="mermaid-dialog-viewport">
      <div class="mermaid-dialog-canvas" id="mermaid-dialog-canvas"></div>
    </div>
    <div class="mermaid-dialog-footer">Scroll to zoom · drag to pan · Esc to close</div>
  </div>
</dialog>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>
(function () {{
  const dialog = document.getElementById("mermaid-dialog");
  const viewport = document.getElementById("mermaid-dialog-viewport");
  const canvas = document.getElementById("mermaid-dialog-canvas");
  const zoomInBtn = document.getElementById("mermaid-zoom-in");
  const zoomOutBtn = document.getElementById("mermaid-zoom-out");
  const zoomResetBtn = document.getElementById("mermaid-zoom-reset");
  const zoomFitBtn = document.getElementById("mermaid-zoom-fit");
  const closeBtn = document.getElementById("mermaid-dialog-close");

  let scale = 1;
  let panX = 0;
  let panY = 0;
  let dragging = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let panStartX = 0;
  let panStartY = 0;

  function applyTransform() {{
    canvas.style.transform = "translate(calc(-50% + " + panX + "px), calc(-50% + " + panY + "px)) scale(" + scale + ")";
  }}

  function resetView() {{
    scale = 1;
    panX = 0;
    panY = 0;
    applyTransform();
  }}

  function fitToView() {{
    const svg = canvas.querySelector("svg");
    if (!svg || !viewport) return;
    const pad = 48;
    const vw = viewport.clientWidth - pad;
    const vh = viewport.clientHeight - pad;
    const bbox = svg.getBBox();
    const svgW = bbox.width || 1;
    const svgH = bbox.height || 1;
    scale = Math.min(vw / svgW, vh / svgH, 2);
    panX = 0;
    panY = 0;
    applyTransform();
  }}

  function zoomBy(factor) {{
    scale = Math.min(5, Math.max(0.15, scale * factor));
    applyTransform();
  }}

  function closeDialog() {{
    if (dialog.open) dialog.close();
    canvas.innerHTML = "";
    resetView();
  }}

  async function openDialog(source) {{
    const id = "mermaid-modal-" + Date.now();
    const node = document.createElement("div");
    node.className = "mermaid";
    node.id = id;
    node.textContent = source;
    canvas.innerHTML = "";
    canvas.appendChild(node);
    resetView();
    dialog.showModal();
    await mermaid.run({{ nodes: [node] }});
    fitToView();
  }}

  function wirePreview(el) {{
    const source = el.textContent.trim();
    if (!source) return;
    el.dataset.mermaidSource = source;
    el.setAttribute("role", "button");
    el.setAttribute("tabindex", "0");
    el.setAttribute("aria-label", "Open diagram to explore");
    el.addEventListener("click", function () {{ openDialog(el.dataset.mermaidSource); }});
    el.addEventListener("keydown", function (e) {{
      if (e.key === "Enter" || e.key === " ") {{
        e.preventDefault();
        openDialog(el.dataset.mermaidSource);
      }}
    }});
    const hint = document.createElement("span");
    hint.className = "mermaid-hint";
    hint.textContent = "Click to explore";
    el.insertAdjacentElement("afterend", hint);
  }}

  viewport.addEventListener("wheel", function (e) {{
    if (!dialog.open) return;
    e.preventDefault();
    zoomBy(e.deltaY > 0 ? 0.9 : 1.1);
  }}, {{ passive: false }});

  viewport.addEventListener("mousedown", function (e) {{
    if (!dialog.open || e.button !== 0) return;
    dragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    panStartX = panX;
    panStartY = panY;
    viewport.classList.add("is-dragging");
  }});

  window.addEventListener("mousemove", function (e) {{
    if (!dragging) return;
    panX = panStartX + (e.clientX - dragStartX);
    panY = panStartY + (e.clientY - dragStartY);
    applyTransform();
  }});

  window.addEventListener("mouseup", function () {{
    dragging = false;
    viewport.classList.remove("is-dragging");
  }});

  zoomInBtn.addEventListener("click", function () {{ zoomBy(1.2); }});
  zoomOutBtn.addEventListener("click", function () {{ zoomBy(1 / 1.2); }});
  zoomResetBtn.addEventListener("click", resetView);
  zoomFitBtn.addEventListener("click", fitToView);
  closeBtn.addEventListener("click", closeDialog);
  dialog.addEventListener("close", closeDialog);
  dialog.addEventListener("click", function (e) {{
    if (e.target === dialog) closeDialog();
  }});
  dialog.addEventListener("cancel", function (e) {{
    e.preventDefault();
    closeDialog();
  }});

  mermaid.initialize({{ startOnLoad: false, theme: "neutral", securityLevel: "loose" }});

  const previews = document.querySelectorAll(".doc-card .mermaid");
  previews.forEach(wirePreview);
  mermaid.run({{ nodes: previews }}).catch(function (err) {{
    console.error("Mermaid render failed:", err);
  }});
}})();
</script>
</body>
</html>"""


def _build_breadcrumbs(path: str) -> str:
    if not path:
        return ""
    parts = path.split("/")
    crumbs = '<div class="breadcrumbs"><a href="/">Home</a>'
    for i, part in enumerate(parts):
        label = part.replace("-", " ").replace("_", " ").title()
        if i == len(parts) - 1:
            crumbs += f'<span> / </span><span>{label}</span>'
        else:
            href = "/" + "/".join(parts[: i + 1])
            crumbs += f'<span> / </span><a href="{href}">{label}</a>'
    crumbs += "</div>"
    return crumbs


def _build_nav(current_path: str | None) -> str:
    docs = _discover_docs()
    groups: dict[str, list[tuple[str, str]]] = {}
    for url_path in docs:
        parts = url_path.split("/")
        if len(parts) == 1:
            groups.setdefault("", []).append((url_path, parts[-1]))
        else:
            group = parts[0]
            groups.setdefault(group, []).append((url_path, "/".join(parts[1:])))

    lines: list[str] = []
    for key in sorted(groups, key=lambda k: (k != "", k)):
        items = sorted(groups[key], key=lambda x: x[1].lower())
        if key:
            label = key.replace("-", " ").replace("_", " ").title()
            lines.append(f'<div class="nav-label">{label}</div>')
        for url_path, display in items:
            active = ' class="active"' if current_path == url_path else ""
            lines.append(f'<a href="/{url_path}"{active}>{display}</a>')
    return "\n".join(lines)


def _build_edit_link(path: str) -> str:
    if not path:
        return ""
    gh_path = f"docs/{path}.md"
    url = f"https://github.com/{GITHUB_REPO}/blob/{GITHUB_BRANCH}/{gh_path}"
    return (
        f'<a href="{url}" class="edit-link" target="_blank" rel="noopener">'
        f'<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round">'
        f'<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>'
        f'<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>'
        f"</svg>"
        f"Edit this page on GitHub"
        f"</a>"
    )


def _first_heading(md_path: Path) -> str | None:
    for line in md_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# ") or line.startswith("#\t"):
            return line.lstrip("# \t").strip()
    return None


@app.get("/", response_class=HTMLResponse)
async def index():
    docs = _discover_docs()
    groups: dict[str, list[tuple[str, str, str]]] = {}
    for url_path, md_path in docs.items():
        parts = url_path.split("/")
        h1 = _first_heading(md_path) or parts[-1].replace("-", " ").title()
        if len(parts) == 1:
            groups.setdefault("", []).append((url_path, h1, ""))
        else:
            groups.setdefault(parts[0], []).append((url_path, h1, parts[0]))

    sections: list[str] = []
    for key in sorted(groups, key=lambda k: (k != "", k)):
        items = sorted(groups[key], key=lambda x: x[0])
        if key:
            label = key.replace("-", " ").replace("_", " ").title()
            sections.append(f'<div class="index-section">{label}</div>')
        sections.append('<div class="index-grid">')
        for url_path, h1, _ in items:
            sections.append(
                f'<a href="/{url_path}" class="index-card">'
                f'<div class="title">{h1}</div>'
                f'<div class="path">/{url_path}</div>'
                f"</a>"
            )
        sections.append("</div>")

    content = "<h1>Documentation</h1>\n" + "\n".join(sections)
    html = HTML_LAYOUT.format(
        title="Documentation",
        site_name=cfg.title,
        tagline=cfg.tagline,
        content=content,
        breadcrumbs="",
        edit_link="",
        nav_links=_build_nav(None),
        root_active="active",
    )
    return HTMLResponse(html)


@app.get("/{path:path}", response_class=HTMLResponse)
async def render_doc(path: str):
    path = path.rstrip("/")
    docs = _discover_docs()
    if path not in docs:
        raise HTTPException(status_code=404, detail="Document not found")
    md_path = docs[path]
    body = _render_md(md_path)
    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", body)
    title = h1_match.group(1) if h1_match else path.split("/")[-1]
    html = HTML_LAYOUT.format(
        title=title,
        site_name=cfg.title,
        tagline=cfg.tagline,
        content=body,
        breadcrumbs=_build_breadcrumbs(path),
        edit_link=_build_edit_link(path),
        nav_links=_build_nav(path),
        root_active="",
    )
    return HTMLResponse(html)
