from __future__ import annotations

import warnings
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Config, configure
from app.site import build_site, set_site

_ENV_KEYS = (
    "DEVDOCS_CONFIG",
    "DEVDOCS_DOCS_DIR",
    "GITHUB_HEAD_REF",
    "GITHUB_REF_NAME",
    "GITHUB_REPOSITORY",
)


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """Keep config, site and CI environment state from leaking between tests."""
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    configure(Config(docs_dir=str(tmp_path / "docs"), config_dir=str(tmp_path)))
    set_site(None)
    yield
    set_site(None)


@pytest.fixture
def docs_dir(tmp_path: Path) -> Path:
    path = tmp_path / "docs"
    path.mkdir()
    return path


@pytest.fixture
def make_client(docs_dir: Path):
    """Build a TestClient for the current docs directory plus config overrides."""

    def _make(**overrides) -> TestClient:
        config = Config(docs_dir=str(docs_dir), config_dir=str(docs_dir.parent), **overrides)
        configure(config)
        set_site(build_site(config))
        from app.main import app

        return TestClient(app)

    return _make


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()


@pytest.fixture
def write(docs_dir: Path):
    def _write(rel: str, content: str) -> Path:
        target = docs_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    return _write


@pytest.fixture
def write_bytes(docs_dir: Path):
    def _write(rel: str, content: bytes) -> Path:
        target = docs_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target

    return _write


@pytest.fixture
def tiny_png() -> bytes:
    """Smallest possible valid PNG."""
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c6300010000050001"
        "0d0a2db40000000049454e44ae426082"
    )


@pytest.fixture
def caught_warnings():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        yield caught
