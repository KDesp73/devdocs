from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from app.config import configure, load_config
from app.site import Site
from app.themes import theme_names


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devdocs",
        description="Start the documentation server.",
    )
    parser.add_argument(
        "root_dir",
        nargs="?",
        default=None,
        help="Root directory containing the docs (default: docs/ next to the config).",
    )
    parser.add_argument(
        "-c", "--config",
        default=None,
        help="Path to a devdocs.yml config file (default: searched upwards from the CWD).",
    )
    parser.add_argument(
        "-H", "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1).",
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000).",
    )
    parser.add_argument(
        "--theme",
        default=None,
        metavar="NAME",
        help=f"Colour theme, one of: {', '.join(theme_names())} (default: from config).",
    )
    parser.add_argument(
        "--type",
        dest="types",
        action="append",
        metavar="TYPE",
        help=(
            "File type to publish, repeatable. Accepts a group (md, images, json, yaml, "
            "toml, xml, text, code), an extension (.py) or 'all'."
        ),
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    cfg = load_config(args.config)
    if args.root_dir is not None:
        cfg.docs_dir = str(Path(args.root_dir).expanduser().resolve())
    if args.theme:
        cfg.theme = args.theme
    if args.types:
        cfg.file_types = list(args.types)
    configure(cfg)

    # Propagate the overrides so that ``--reload`` subprocesses, which import
    # the app from scratch, see the same configuration.
    if args.config:
        os.environ["DEVDOCS_CONFIG"] = str(Path(args.config).expanduser().resolve())
    else:
        os.environ.setdefault("DEVDOCS_CONFIG", _discover_config_path())
    if args.root_dir is not None:
        os.environ["DEVDOCS_DOCS_DIR"] = cfg.docs_dir
    if args.theme:
        os.environ["DEVDOCS_THEME"] = args.theme
    if args.types:
        os.environ["DEVDOCS_FILE_TYPES"] = ",".join(args.types)

    from app.site import build_site, set_site

    info = build_site(cfg)
    set_site(info)
    _report(info)

    import uvicorn

    reload_dirs = None
    if args.reload:
        reload_dirs = []
        # Add config file directory
        cfg_path = os.environ.get("DEVDOCS_CONFIG", "")
        if cfg_path:
            reload_dirs.append(str(Path(cfg_path).parent))
        # Also add cwd and docs dir as fallback
        if not reload_dirs:
            reload_dirs.append(str(Path.cwd()))
        # Add docs dir
        reload_dirs.append(cfg.docs_dir)
        # Deduplicate
        reload_dirs = list(dict.fromkeys(reload_dirs))

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        reload_dirs=reload_dirs if args.reload else None,
    )


def _discover_config_path() -> str:
    from app.config import _find_config_file

    found = _find_config_file()
    return str(found) if found else ""


def _report(info: Site) -> None:
    types = ", ".join(sorted(info.types.extensions)) or "none"
    if info.types.dynamic_code:
        types += "+code"
    lines = [
        f"devdocs: serving {info.docs_dir}",
        f"devdocs: theme {info.theme.name} · file types {types}",
        f"devdocs: branch {info.branch}" + (f" · repo {info.repo}" if info.repo else " · no git remote"),
    ]
    print("\n".join(lines), file=sys.stderr)


if __name__ == "__main__":
    main()
