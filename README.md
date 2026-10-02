# devdocs

A lightweight documentation server that renders Markdown files as a styled website.

## Features

- Markdown rendering with syntax highlighting (Pygments) and line numbers for source files
- Pretty labels everywhere: `NativeBackendSetup.md` shows up as **Native Backend Setup**,
  `getting-started/` as **Getting Started**, `apiReference.md` as **API Reference**
- Collapsible folder tree sidebar with auto-expand for the current page
- Breadcrumb navigation
- Mermaid diagram support: diagrams are rendered at their natural size instead of being
  squeezed into the page width, and can be opened in a zoomable/panable viewer
- "Edit on GitHub" links that follow the branch you actually have checked out
- Seven themes, configurable in `devdocs.yml`
- Publishes more than Markdown when you ask it to: JSON/YAML/TOML/XML, plain text,
  source code, and images
- Configurable via YAML or environment variables

## Install

```bash
pip install -e .
```

## Usage

```bash
# Serve docs from the default docs/ directory
devdocs

# Serve from a custom directory
devdocs path/to/docs

# With a config file
devdocs -c devdocs.yml

# Pick a theme and extra file types without editing the config
devdocs --theme midnight --type md --type images --type json

# Custom host/port
devdocs -H 0.0.0.0 -p 3000

# Development mode with auto-reload
devdocs --reload
```

Run `devdocs --help` for the full list of options.

## Configuration

Create a `devdocs.yml` in your project root (see the bundled
[`devdocs.yml`](devdocs.yml) for a documented example). Every key is optional:

```yaml
title: "My Project"
tagline: "Documentation"
version: "1.0.0"
author: ""

# docs_dir: "docs"

# Empty values are detected from the Git checkout:
# the branch from `git rev-parse --abbrev-ref HEAD` and the
# repository from the GitHub `origin` remote.
github_repo: ""
github_branch: ""

# original (default), midnight, emerald, sunset, grape, mono, auto
theme: "auto"

# md, images, json, yaml, toml, xml, text, code, all, or a single
# extension such as ".rs"
file_types:
  - md
  - images

ignore:
  - ".git"
  - "__pycache__"
  - "node_modules"
```

### Themes

`original` reproduces the look devdocs has always had. `midnight`, `emerald`,
`sunset`, `grape`, and `mono` are additional palettes, and `auto` follows the
operating system's light/dark preference. Syntax highlighting and Mermaid
diagrams are recolored to match.

Themes are applied when the server starts; edit `devdocs.yml` and restart (or use
`--reload` during development) to switch.

### File types

Anything that is not listed in `file_types` is neither published nor linked, so
`--type` on the command line replaces the configured list rather than adding to it.

| Group    | Extensions                                                                   | Rendering                             |
| -------- | ---------------------------------------------------------------------------- | ------------------------------------- |
| `md`     | `.md` `.markdown`                                                             | Full page with a Mermaid viewer      |
| `images` | `.png` `.jpg` `.jpeg` `.gif` `.svg` `.webp` `.bmp` `.ico` `.avif`             | Served as assets, shown in the tree   |
| `json`   | `.json` `.jsonc` `.json5`                                                     | Pretty-printed, highlighted, numbered |
| `yaml`   | `.yaml` `.yml`                                                                | Pretty-printed, highlighted, numbered |
| `toml`   | `.toml`                                                                       | Pretty-printed, highlighted, numbered |
| `xml`    | `.xml` `.xsd` `.xsl` `.plist` `.svgz`                                         | Pretty-printed, highlighted, numbered |
| `text`   | `.txt` `.rst` `.adoc`                                                         | Highlighted, numbered                 |
| `code`   | every extension Pygments can lex (`.py`, `.rs`, `.go`, `.sql`, …)             | Highlighted, numbered                 |
| `all`    | every group above                                                             | As above                              |

A single extension (`.rs`) can be listed on its own. Markdown pages are served
without their extension (`/guides/setup`); other documents keep theirs
(`/openapi.json`) and expose the untouched bytes at `/raw/<path>`.

Images are the exception: they are served at their real path and stay out of the
navigation tree, so linking `![diagram](./assets/flow.png)` just works.

### Environment variables

`DEVDOCS_CONFIG`, `DEVDOCS_DOCS_DIR`, `DEVDOCS_THEME`, and `DEVDOCS_FILE_TYPES`
override the corresponding settings, which is what makes `--reload` pick up an
edited `devdocs.yml` while keeping `--theme`/`--type` in effect.

## Project Structure

```
your-docs/
  index.md
  getting-started/
    install.md
    setup.md
  guides/
    basics.md
    advanced/
      intro.md
  assets/
    flow.png
```

Subdirectories are displayed as collapsible folders in the sidebar tree, and both
folder and page names are prettified: `NativeBackendSetup/gettingStarted.md`
becomes **Native Backend Setup › Getting Started**.

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest
```
