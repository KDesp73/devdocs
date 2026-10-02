from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Config, _find_config_file, load_config


def _write_config(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_defaults() -> None:
    cfg = Config()
    assert cfg.title == "Docs"
    assert cfg.theme == "original"
    assert cfg.file_types == ["md"]
    assert cfg.github_branch == ""
    assert cfg.github_repo == ""


def test_loads_every_documented_key(tmp_path: Path) -> None:
    _write_config(
        tmp_path / "devdocs.yml",
        """
title: My Project
tagline: Docs
version: 2.1.0
author: Someone
docs_dir: manual
theme: midnight
file_types:
  - md
  - json
github_repo: owner/repo
github_branch: release
ignore:
  - drafts
""",
    )
    cfg = load_config(tmp_path / "devdocs.yml")
    assert cfg.title == "My Project"
    assert cfg.tagline == "Docs"
    assert cfg.version == "2.1.0"
    assert cfg.author == "Someone"
    assert cfg.theme == "midnight"
    assert cfg.file_types == ["md", "json"]
    assert cfg.github_repo == "owner/repo"
    assert cfg.github_branch == "release"
    assert cfg.ignore == ["drafts"]


def test_docs_dir_resolves_against_config_dir(tmp_path: Path) -> None:
    (tmp_path / "site" / "guide").mkdir(parents=True)
    _write_config(tmp_path / "site" / "devdocs.yml", "docs_dir: guide\n")
    cfg = load_config(tmp_path / "site" / "devdocs.yml")
    assert cfg.docs_path == (tmp_path / "site" / "guide").resolve()


def test_docs_dir_defaults_next_to_config(tmp_path: Path) -> None:
    _write_config(tmp_path / "devdocs.yml", "title: x\n")
    cfg = load_config(tmp_path / "devdocs.yml")
    assert cfg.docs_path == (tmp_path / "docs").resolve()


def test_unknown_keys_warn(caught_warnings, tmp_path: Path) -> None:
    _write_config(tmp_path / "devdocs.yml", "title: x\ngithub_brnach: main\n")
    cfg = load_config(tmp_path / "devdocs.yml")
    assert cfg.github_branch == ""
    assert any("github_brnach" in str(w.message) for w in caught_warnings)


def test_wrong_types_warn_and_fall_back(caught_warnings, tmp_path: Path) -> None:
    _write_config(tmp_path / "devdocs.yml", "title: 5\nfile_types: 7\n")
    cfg = load_config(tmp_path / "devdocs.yml")
    assert cfg.title == "Docs"
    assert cfg.file_types == []
    messages = " ".join(str(w.message) for w in caught_warnings)
    assert "title must be a string" in messages
    assert "file_types must be a list" in messages


def test_string_shorthand_for_lists(tmp_path: Path) -> None:
    _write_config(tmp_path / "devdocs.yml", "file_types: json\n")
    assert load_config(tmp_path / "devdocs.yml").file_types == ["json"]


def test_empty_file_is_all_defaults(tmp_path: Path) -> None:
    _write_config(tmp_path / "devdocs.yml", "")
    cfg = load_config(tmp_path / "devdocs.yml")
    assert cfg.title == "Docs"


def test_missing_explicit_path_warns(caught_warnings, tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "nope.yml")
    assert cfg.title == "Docs"
    assert any("not found" in str(w.message) for w in caught_warnings)


def test_finds_config_in_parent_directory(tmp_path: Path, monkeypatch) -> None:
    _write_config(tmp_path / "devdocs.yml", "title: Parent\n")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    found = _find_config_file()
    assert found == tmp_path / "devdocs.yml"
    assert load_config().title == "Parent"


def test_config_env_var_wins(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path / "elsewhere.yml", "title: Explicit\n")
    monkeypatch.setenv("DEVDOCS_CONFIG", str(tmp_path / "elsewhere.yml"))
    assert load_config().title == "Explicit"


def test_docs_dir_env_override(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path / "devdocs.yml", "title: x\n")
    monkeypatch.setenv("DEVDOCS_DOCS_DIR", str(tmp_path / "other"))
    assert load_config(tmp_path / "devdocs.yml").docs_path == (tmp_path / "other").resolve()


def test_ignore_matches_paths_and_ancestors() -> None:
    cfg = Config(ignore=["*.tmp.md", "a/b"])
    assert cfg.is_ignored("notes.tmp.md")
    assert cfg.is_ignored("deep/notes.tmp.md")
    assert cfg.is_ignored("a/b/c.md")
    assert not cfg.is_ignored("guides/b.md")


@pytest.mark.parametrize("filename", ["devdocs.yml", "devdocs.yaml", "devdocs.json"])
def test_all_config_filenames(tmp_path: Path, monkeypatch, filename: str) -> None:
    (tmp_path / filename).write_text('{"title": "From json"}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert load_config().title == "From json"


def test_theme_and_file_types_env_overrides(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path / "devdocs.yml", "theme: original\nfile_types: [md]\n")
    monkeypatch.setenv("DEVDOCS_THEME", "midnight")
    monkeypatch.setenv("DEVDOCS_FILE_TYPES", "md,json")
    cfg = load_config(tmp_path / "devdocs.yml")
    assert cfg.theme == "midnight"
    assert cfg.file_types == ["md", "json"]


def test_env_overrides_apply_without_a_config_file(monkeypatch) -> None:
    monkeypatch.chdir(Path(__file__).parent)
    monkeypatch.setenv("DEVDOCS_THEME", "grape")
    assert load_config().theme == "grape"
