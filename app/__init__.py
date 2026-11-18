"""devdocs package."""

from __future__ import annotations

__all__ = ["__version__"]

try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("devdocs")
except PackageNotFoundError:
    __version__ = "1.1.0"
except Exception:  # pragma: no cover - defensive fallback
    __version__ = "1.1.0"
