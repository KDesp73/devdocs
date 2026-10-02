"""Runtime context: config plus everything discovered about the repository."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

from app import gitinfo
from app.config import Config
from app.render import ResolvedTypes, resolve_types
from app.themes import Theme, get_theme

__all__ = ["Site", "build_site", "set_site", "site"]

FALLBACK_BRANCH = "main"
GITHUB_BLOB = "https://github.com/{repo}/blob/{branch}/{path}"


@dataclass(frozen=True)
class Site:
    """Everything the request handlers need to know about the served tree."""

    config: Config
    docs_dir: Path
    theme: Theme
    types: ResolvedTypes
    repo: str
    branch: str
    docs_prefix: str

    @property
    def title(self) -> str:
        return self.config.title

    @property
    def edit_url(self) -> str | None:
        if not self.repo:
            return None
        return GITHUB_BLOB.format(repo=self.repo, branch=self.branch, path="{path}")

    def source_url(self, rel_path: str) -> str:
        """GitHub URL of a file inside the served tree, if that is knowable."""
        base = self.edit_url
        if not base:
            return ""
        prefix = f"{self.docs_prefix}/" if self.docs_prefix else ""
        return base.format(path=prefix + rel_path)


def _docs_prefix(docs_dir: Path, root: Path | None) -> str:
    if root is None:
        return ""
    try:
        return docs_dir.relative_to(root).as_posix()
    except ValueError:
        return ""


def build_site(config: Config) -> Site:
    """Resolve config into a :class:`Site`, auto-detecting git details."""
    docs_dir = config.docs_path
    root = gitinfo.repo_root(docs_dir)
    types = resolve_types(config.file_types)
    if types.unknown:
        warnings.warn(
            "devdocs: unknown file_types entries: " + ", ".join(types.unknown),
            stacklevel=2,
        )
    return Site(
        config=config,
        docs_dir=docs_dir,
        theme=get_theme(config.theme),
        types=types,
        repo=config.github_repo or gitinfo.remote_slug(docs_dir) or "",
        branch=gitinfo.current_branch(docs_dir) or config.github_branch or FALLBACK_BRANCH,
        docs_prefix=_docs_prefix(docs_dir, root),
    )


_site: Site | None = None


def site() -> Site:
    global _site
    if _site is None:
        from app.config import get_config

        _site = build_site(get_config())
    return _site


def set_site(value: Site | None) -> None:
    """Override the cached site (used by the CLI and the test suite)."""
    global _site
    _site = value
