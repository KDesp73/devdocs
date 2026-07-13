from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="devdocs",
        description="Start the documentation server.",
    )
    parser.add_argument(
        "root_dir",
        nargs="?",
        default=None,
        help="Root directory containing Markdown docs (default: docs/).",
    )
    parser.add_argument(
        "-c", "--config",
        default=None,
        help="Path to a devdocs.yml config file.",
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
        "--reload",
        action="store_true",
        help="Enable auto-reload for development.",
    )
    args = parser.parse_args(argv)

    from app.config import configure, load_config

    cfg = load_config(args.config)

    if args.root_dir is not None:
        cfg.docs_dir = str(Path(args.root_dir).expanduser().resolve())

    configure(cfg)

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
