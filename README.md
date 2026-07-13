# devdocs

A lightweight documentation server that renders Markdown files as a styled website.

## Features

- Markdown rendering with syntax highlighting (Pygments)
- Collapsible folder tree sidebar with auto-expand for the current page
- Breadcrumb navigation
- Mermaid diagram support with zoomable modal viewer
- "Edit on GitHub" links
- Configurable via YAML

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

# Custom host/port
devdocs -H 0.0.0.0 -p 3000

# Development mode with auto-reload
devdocs --reload
```

## Configuration

Create a `devdocs.yml` in your project root:

```yaml
title: "My Project"
tagline: "Documentation"
version: "1.0.0"

github_repo: "user/repo"
github_branch: "main"

ignore:
  - ".git"
  - "__pycache__"
  - "node_modules"
```

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
```

Subdirectories are displayed as collapsible folders in the sidebar tree.
