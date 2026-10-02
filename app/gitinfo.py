"""Best effort Git repository introspection.

Used to build "Edit on GitHub" links without forcing users to spell out the
branch in their config. Every function is failure tolerant: when git is
missing, the directory is not a repository, or no remote is configured the
result is ``None`` and the caller falls back to configured values.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

__all__ = ["current_branch", "parse_remote", "remote_slug", "repo_root"]

_TIMEOUT = 3.0
_GITHUB_HOSTS = {"github.com", "www.github.com"}
_SCP_LIKE = re.compile(r"^(?:[\w.+-]+@)?([\w.-]+):(?!\d)(.+)$")


def _git(*args: str, cwd: Path | None = None) -> str | None:
    executable = shutil.which("git")
    if not executable:
        return None
    try:
        proc = subprocess.run(  # noqa: S603
            [executable, *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    output = proc.stdout.strip()
    return output or None


def _start_dir(path: Path | None) -> Path | None:
    """Nearest existing directory at or above ``path``; git needs a real cwd."""
    if path is None:
        return None
    candidate = path if path.is_dir() else path.parent
    for directory in (candidate, *candidate.parents):
        if directory.is_dir():
            return directory
    return None


def repo_root(start: Path | None = None) -> Path | None:
    """Absolute path of the repository containing ``start``."""
    output = _git("rev-parse", "--show-toplevel", cwd=_start_dir(start))
    if not output:
        return None
    root = Path(output)
    return root if root.is_dir() else None


def current_branch(start: Path | None = None) -> str | None:
    """Name of the checked out branch, or the commit SHA when detached.

    CI environments are checked first: on GitHub Actions ``GITHUB_HEAD_REF``
    holds the source branch of a pull request while ``GITHUB_REF_NAME`` holds
    the branch that was pushed.
    """
    head_ref = os.environ.get("GITHUB_HEAD_REF", "").strip()
    if head_ref:
        return head_ref
    ref_name = os.environ.get("GITHUB_REF_NAME", "").strip()
    if ref_name and not re.search(r"/\d+/merge$", ref_name):
        return ref_name
    start = _start_dir(start)
    if branch := _git("symbolic-ref", "--quiet", "--short", "HEAD", cwd=start):
        return branch
    return _git("rev-parse", "--short", "HEAD", cwd=start)


def parse_remote(url: str) -> tuple[str, str] | None:
    """Extract ``(host, owner/repo)`` from a git remote URL."""
    url = url.strip()
    if not url:
        return None
    if "://" in url:
        scheme, _, rest = url.partition("://")
        if scheme not in {"http", "https", "ssh", "git", "git+ssh"}:
            return None
        rest = rest.rsplit("@", 1)[-1]
        host, _, path = rest.partition("/")
    elif match := _SCP_LIKE.match(url):
        host, path = match.group(1), match.group(2)
    else:
        return None

    host = host.rstrip("/").lower()
    if not host or not path:
        return None

    segments = [segment for segment in path.split("/") if segment]
    if len(segments) < 2:
        return None
    slug = "/".join(segments[:2])
    if slug.endswith(".git"):
        slug = slug[: -len(".git")]
    return host, slug


def remote_slug(start: Path | None = None) -> str | None:
    """``owner/repo`` of the GitHub ``origin`` remote, if there is one."""
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if "/" in repository:
        return repository.strip("/")

    start = _start_dir(start)
    url = _git("remote", "get-url", "origin", cwd=start)
    if not url:
        url = _git("config", "--get", "remote.origin.url", cwd=start)
    if not url:
        return None
    parsed = parse_remote(url)
    if not parsed or parsed[0] not in _GITHUB_HOSTS:
        return None
    return parsed[1]
