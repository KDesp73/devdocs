from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app import gitinfo


def _repo(path: Path, *, remote: str | None = "https://github.com/owner/repo.git") -> Path:
    def run(*args: str) -> None:
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True)

    path.mkdir(parents=True, exist_ok=True)
    run("init", "-q", "-b", "main")
    run("config", "user.email", "dev@example.com")
    run("config", "user.name", "Dev")
    (path / "README.md").write_text("hi", encoding="utf-8")
    run("add", "README.md")
    run("commit", "-qm", "init")
    if remote:
        run("remote", "add", "origin", remote)
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    try:
        return _repo(tmp_path / "repo")
    except (OSError, subprocess.CalledProcessError):  # pragma: no cover - no git installed
        pytest.skip("git is not available")


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/owner/repo.git", ("github.com", "owner/repo")),
        ("https://github.com/owner/repo", ("github.com", "owner/repo")),
        ("git@github.com:owner/repo.git", ("github.com", "owner/repo")),
        ("ssh://git@github.com/owner/repo", ("github.com", "owner/repo")),
        ("git://github.com/owner/repo.git", ("github.com", "owner/repo")),
        ("https://user:token@github.com/owner/repo.git", ("github.com", "owner/repo")),
        ("git@gitlab.com:owner/repo.git", ("gitlab.com", "owner/repo")),
        ("https://github.com/owner/repo/tree/main", ("github.com", "owner/repo")),
        ("file:///tmp/repo.git", None),
        ("https://github.com/owner", None),
        ("nonsense", None),
        ("", None),
    ],
)
def test_parse_remote(url: str, expected) -> None:
    assert gitinfo.parse_remote(url) == expected


def test_detects_branch_and_remote(repo: Path) -> None:
    assert gitinfo.current_branch(repo) == "main"
    assert gitinfo.remote_slug(repo) == "owner/repo"
    assert gitinfo.repo_root(repo / "README.md") == repo.resolve()


def test_detects_feature_branch(repo: Path) -> None:
    subprocess.run(["git", "checkout", "-qb", "feature/NativeSetup"], cwd=repo, check=True)
    assert gitinfo.current_branch(repo) == "feature/NativeSetup"


def test_detached_head_falls_back_to_sha(repo: Path) -> None:
    sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    subprocess.run(["git", "checkout", "-q", "--detach", "HEAD"], cwd=repo, check=True)
    assert gitinfo.current_branch(repo) == sha


def test_outside_a_repository(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    assert gitinfo.current_branch(plain) is None
    assert gitinfo.remote_slug(plain) is None
    assert gitinfo.repo_root(plain) is None


def test_ci_environment_overrides(monkeypatch, repo: Path) -> None:
    monkeypatch.setenv("GITHUB_HEAD_REF", "pr-branch")
    monkeypatch.setenv("GITHUB_REF_NAME", "42/merge")
    assert gitinfo.current_branch(repo) == "pr-branch"
    monkeypatch.delenv("GITHUB_HEAD_REF")
    monkeypatch.setenv("GITHUB_REF_NAME", "main")
    assert gitinfo.current_branch(repo) == "main"
    monkeypatch.setenv("GITHUB_REPOSITORY", "ci/owner")
    assert gitinfo.remote_slug(repo) == "ci/owner"
