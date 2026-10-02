from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.config import Config
from app.site import FALLBACK_BRANCH, build_site


def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=path, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    (path / "docs").mkdir(parents=True)
    try:
        _git(path, "init", "-q", "-b", "trunk")
        _git(path, "config", "user.email", "dev@example.com")
        _git(path, "config", "user.name", "Dev")
        (path / "docs" / "index.md").write_text("# Home\n", encoding="utf-8")
        _git(path, "add", ".")
        _git(path, "commit", "-qm", "init")
        _git(path, "remote", "add", "origin", "git@github.com:acme/widgets.git")
    except (OSError, subprocess.CalledProcessError):  # pragma: no cover
        pytest.skip("git is not available")
    return path


def test_detects_branch_and_repo(repo: Path) -> None:
    info = build_site(Config(docs_dir=str(repo / "docs")))
    assert info.branch == "trunk"
    assert info.repo == "acme/widgets"
    assert info.docs_prefix == "docs"


def test_config_overrides_detection(repo: Path) -> None:
    info = build_site(
        Config(
            docs_dir=str(repo / "docs"),
            github_branch="main",
            github_repo="other/repo",
        )
    )
    assert info.branch == "trunk"
    assert info.repo == "other/repo"


def test_source_url_points_at_the_branch(repo: Path) -> None:
    info = build_site(Config(docs_dir=str(repo / "docs")))
    assert info.source_url("guides/setup.md") == (
        "https://github.com/acme/widgets/blob/trunk/docs/guides/setup.md"
    )


def test_source_url_empty_without_repo(tmp_path: Path) -> None:
    info = build_site(Config(docs_dir=str(tmp_path / "docs")))
    assert info.repo == ""
    assert info.source_url("a.md") == ""


def test_branch_falls_back_to_main(tmp_path: Path) -> None:
    info = build_site(Config(docs_dir=str(tmp_path / "docs"), config_dir=str(tmp_path)))
    assert info.branch == FALLBACK_BRANCH


def test_nested_docs_dir_prefix(repo: Path) -> None:
    (repo / "site" / "guide").mkdir(parents=True)
    info = build_site(Config(docs_dir=str(repo / "site" / "guide")))
    assert info.docs_prefix == "site/guide"
    assert info.source_url("a.md").endswith("/blob/trunk/site/guide/a.md")


def test_unknown_theme_falls_back_to_default(tmp_path: Path) -> None:
    info = build_site(Config(docs_dir=str(tmp_path / "docs"), theme="nope"))
    assert info.theme.name == "original"


def test_unknown_file_types_warn(tmp_path: Path, caught_warnings) -> None:
    build_site(Config(docs_dir=str(tmp_path / "docs"), file_types=["md", "wat"]))
    assert any("wat" in str(w.message) for w in caught_warnings)


def test_missing_docs_dir_is_fine(tmp_path: Path) -> None:
    info = build_site(Config(docs_dir=str(tmp_path / "nope")))
    assert not info.docs_dir.exists()
    assert info.types.extensions
