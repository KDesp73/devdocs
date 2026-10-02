"""Configuration loading for devdocs."""

from __future__ import annotations

import fnmatch
import os
import re
import warnings
from dataclasses import dataclass, field, fields
from pathlib import Path

import yaml

CONFIG_FILENAMES = ("devdocs.yml", "devdocs.yaml", "devdocs.json")

#: Set by the CLI so that ``--reload`` subprocesses inherit the overrides.
ENV_CONFIG = "DEVDOCS_CONFIG"
ENV_DOCS_DIR = "DEVDOCS_DOCS_DIR"
ENV_THEME = "DEVDOCS_THEME"
ENV_FILE_TYPES = "DEVDOCS_FILE_TYPES"

_DEFAULT_IGNORE = [
    ".git",
    ".git/**",
    "__pycache__",
    "__pycache__/**",
    "node_modules",
    "node_modules/**",
    ".venv",
    ".venv/**",
    ".idea",
    ".vscode",
    "*.pyc",
    ".DS_Store",
    "*~",
]


@dataclass
class Config:
    """Settings read from ``devdocs.yml``.

    ``github_repo`` and ``github_branch`` default to empty, which means "work
    it out from the local git checkout".  ``config_dir`` is not read from the
    config file itself; it is where the config file was found.
    """

    title: str = "Docs"
    tagline: str = ""
    version: str = "0.1.0"
    author: str = ""
    docs_dir: str = ""
    theme: str = "original"
    file_types: list[str] = field(default_factory=lambda: ["md"])
    github_repo: str = ""
    github_branch: str = ""
    ignore: list[str] = field(default_factory=lambda: list(_DEFAULT_IGNORE))
    config_dir: str = ""

    @property
    def docs_path(self) -> Path:
        if self.docs_dir:
            path = Path(self.docs_dir).expanduser()
            if not path.is_absolute():
                path = Path(self.config_dir or ".") / path
            return path.resolve()
        return (Path(self.config_dir or ".") / "docs").resolve()

    def is_ignored(self, rel_path: str) -> bool:
        for pattern in self.ignore:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            parts = rel_path.split("/")
            for i in range(len(parts)):
                prefix = "/".join(parts[: i + 1])
                if fnmatch.fnmatch(prefix, pattern):
                    return True
        return False


#: Keys accepted in ``devdocs.yml``.
YAML_FIELDS = frozenset(f.name for f in fields(Config)) - {"config_dir"}

_global_cfg: Config | None = None


def configure(cfg: Config) -> None:
    global _global_cfg
    _global_cfg = cfg


def get_config() -> Config:
    global _global_cfg
    if _global_cfg is None:
        _global_cfg = load_config()
    return _global_cfg


def _find_config_file(start: Path | None = None) -> Path | None:
    from_env = os.environ.get(ENV_CONFIG, "").strip()
    if from_env:
        candidate = Path(from_env).expanduser()
        return candidate if candidate.is_file() else None
    search = start or Path.cwd()
    for directory in (search, *search.parents):
        for name in CONFIG_FILENAMES:
            candidate = directory / name
            if candidate.is_file():
                return candidate
    return None


def _as_str_list(value: object) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if isinstance(item, (str, int))]
    return None


def _as_csv(value: str) -> list[str]:
    """Split a comma (or whitespace) separated environment value."""
    return [item for item in re.split(r"[,\s]+", value.strip()) if item]


def _apply_env(cfg: Config) -> Config:
    """Apply the ``DEVDOCS_*`` overrides on top of whatever was read from YAML."""
    docs_dir = os.environ.get(ENV_DOCS_DIR, "").strip()
    if docs_dir and not cfg.docs_dir:
        cfg.docs_dir = docs_dir
    theme = os.environ.get(ENV_THEME, "").strip()
    if theme:
        cfg.theme = theme
    file_types = _as_csv(os.environ.get(ENV_FILE_TYPES, ""))
    if file_types:
        cfg.file_types = file_types
    return cfg


def load_config(path: Path | str | None = None) -> Config:
    """Read a config file, falling back to defaults when there is none."""
    if path is None:
        candidate = _find_config_file()
        if candidate is None:
            return _apply_env(Config())
    else:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        if not candidate.is_file():
            warnings.warn(f"devdocs: config file not found: {candidate}", stacklevel=2)
            return _apply_env(Config())

    config_file: Path = candidate
    raw = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        warnings.warn(f"devdocs: ignoring {config_file}: expected a mapping", stacklevel=2)
        return _apply_env(Config())

    values = {key: value for key, value in raw.items() if key in YAML_FIELDS}
    unknown = sorted(key for key in raw if key not in YAML_FIELDS)
    if unknown:
        warnings.warn(
            "devdocs: unknown config keys in "
            f"{config_file}: {', '.join(unknown)}",
            stacklevel=2,
        )

    for key in ("file_types", "ignore"):
        if key in values:
            coerced = _as_str_list(values[key])
            if coerced is None:
                warnings.warn(f"devdocs: {key} must be a list of strings", stacklevel=2)
                coerced = []
            values[key] = coerced

    for key in ("title", "tagline", "version", "author", "docs_dir", "theme",
                "github_repo", "github_branch"):
        if key in values and not isinstance(values[key], str):
            warnings.warn(f"devdocs: {key} must be a string", stacklevel=2)
            values.pop(key)

    values["config_dir"] = str(config_file.resolve().parent)
    return _apply_env(Config(**values))
