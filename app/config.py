from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_FILENAMES = ("devdocs.yml", "devdocs.yaml", "devdocs.json")

_DEFAULT_IGNORE = [
    ".git",
    ".git/**",
    "__pycache__",
    "__pycache__/**",
    "node_modules",
    "node_modules/**",
    ".venv",
    ".venv/**",
    "*.pyc",
]


@dataclass
class Config:
    title: str = "Docs"
    tagline: str = ""
    version: str = "0.1.0"
    author: str = ""
    docs_dir: str = ""
    github_repo: str = ""
    github_branch: str = "main"
    ignore: list[str] = field(default_factory=lambda: list(_DEFAULT_IGNORE))

    @property
    def docs_path(self) -> Path:
        if self.docs_dir:
            return Path(self.docs_dir).expanduser().resolve()
        return Path("docs").resolve()

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
    search = start or Path.cwd()
    for name in CONFIG_FILENAMES:
        candidate = search / name
        if candidate.is_file():
            return candidate
    return None


def load_config(path: Path | str | None = None) -> Config:
    if path is None:
        candidate = _find_config_file()
        if candidate is None:
            return Config()
        path = candidate
    else:
        path = Path(path).expanduser().resolve()
        if not path.is_file():
            return Config()

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return Config()

    fields = {f.name for f in Config.__dataclass_fields__.values()}
    filtered = {k: v for k, v in raw.items() if k in fields}
    return Config(**filtered)
