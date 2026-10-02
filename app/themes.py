"""Colour themes.

Every theme is a flat mapping of CSS custom properties consumed by
``app/static/devdocs.css``.  Themes are selected from ``devdocs.yml``
(``theme: original``) and additionally pick a Mermaid and a Pygments style so
diagrams and code blocks stay readable.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

__all__ = ["DEFAULT_THEME", "THEMES", "get_theme", "theme_css", "theme_names"]

DEFAULT_THEME = "original"

_VARS = (
    "--bg",
    "--surface",
    "--surface-2",
    "--surface-3",
    "--border",
    "--border-strong",
    "--text",
    "--text-strong",
    "--text-muted",
    "--accent",
    "--accent-strong",
    "--accent-text",
    "--accent-soft",
    "--code-bg",
    "--code-text",
    "--inline-code-bg",
    "--inline-code-text",
    "--shadow",
    "--shadow-strong",
    "--overlay",
)


@dataclass(frozen=True)
class Theme:
    name: str
    label: str
    colors: dict[str, str]
    mermaid: str = "neutral"
    pygments: str = "monokai"


_ORIGINAL = {
    "--bg": "#f1f5f9",
    "--surface": "#ffffff",
    "--surface-2": "#f8fafc",
    "--surface-3": "#eff6ff",
    "--border": "#e2e8f0",
    "--border-strong": "#cbd5e1",
    "--text": "#1e293b",
    "--text-strong": "#0f172a",
    "--text-muted": "#94a3b8",
    "--accent": "#3b82f6",
    "--accent-strong": "#2563eb",
    "--accent-text": "#1d4ed8",
    "--accent-soft": "#eff6ff",
    "--code-bg": "#0f172a",
    "--code-text": "#e2e8f0",
    "--inline-code-bg": "#f1f5f9",
    "--inline-code-text": "#be123c",
    "--shadow": "rgba(15, 23, 42, 0.04)",
    "--shadow-strong": "rgba(15, 23, 42, 0.25)",
    "--overlay": "rgba(15, 23, 42, 0.55)",
}

_MIDNIGHT = {
    "--bg": "#0b1220",
    "--surface": "#111a2e",
    "--surface-2": "#16203a",
    "--surface-3": "#1e2a4a",
    "--border": "#24324f",
    "--border-strong": "#33436a",
    "--text": "#cbd5e1",
    "--text-strong": "#f1f5f9",
    "--text-muted": "#7c8db0",
    "--accent": "#60a5fa",
    "--accent-strong": "#93c5fd",
    "--accent-text": "#bfdbfe",
    "--accent-soft": "rgba(96, 165, 250, 0.14)",
    "--code-bg": "#0a101d",
    "--code-text": "#dbe4f3",
    "--inline-code-bg": "#1e2a4a",
    "--inline-code-text": "#fca5a5",
    "--shadow": "rgba(0, 0, 0, 0.35)",
    "--shadow-strong": "rgba(0, 0, 0, 0.6)",
    "--overlay": "rgba(2, 6, 15, 0.7)",
}

_EMERALD = {
    "--bg": "#eef5f1",
    "--surface": "#ffffff",
    "--surface-2": "#f4f9f6",
    "--surface-3": "#e6f6ef",
    "--border": "#d3e6dc",
    "--border-strong": "#b3d6c6",
    "--text": "#1f2f28",
    "--text-strong": "#0f1f19",
    "--text-muted": "#7d968b",
    "--accent": "#10b981",
    "--accent-strong": "#059669",
    "--accent-text": "#047857",
    "--accent-soft": "#e6f6ef",
    "--code-bg": "#10241c",
    "--code-text": "#d9ece3",
    "--inline-code-bg": "#e6f6ef",
    "--inline-code-text": "#be123c",
    "--shadow": "rgba(6, 42, 29, 0.05)",
    "--shadow-strong": "rgba(6, 42, 29, 0.28)",
    "--overlay": "rgba(6, 42, 29, 0.5)",
}

_SUNSET = {
    "--bg": "#fdf4ec",
    "--surface": "#ffffff",
    "--surface-2": "#fdf8f3",
    "--surface-3": "#fdece0",
    "--border": "#f0ddca",
    "--border-strong": "#e0c2a6",
    "--text": "#3a2a1f",
    "--text-strong": "#241710",
    "--text-muted": "#a08a79",
    "--accent": "#f97316",
    "--accent-strong": "#ea580c",
    "--accent-text": "#c2410c",
    "--accent-soft": "#fdece0",
    "--code-bg": "#2a1a10",
    "--code-text": "#f6e4d6",
    "--inline-code-bg": "#fdece0",
    "--inline-code-text": "#be123c",
    "--shadow": "rgba(58, 26, 4, 0.05)",
    "--shadow-strong": "rgba(58, 26, 4, 0.28)",
    "--overlay": "rgba(41, 20, 3, 0.5)",
}

_GRAPE = {
    "--bg": "#14101f",
    "--surface": "#1c1730",
    "--surface-2": "#241d3d",
    "--surface-3": "#2f2650",
    "--border": "#322a4f",
    "--border-strong": "#443a68",
    "--text": "#ddd6ee",
    "--text-strong": "#f5f2ff",
    "--text-muted": "#8f85ad",
    "--accent": "#a78bfa",
    "--accent-strong": "#c4b5fd",
    "--accent-text": "#ddd6fe",
    "--accent-soft": "rgba(167, 139, 250, 0.16)",
    "--code-bg": "#100c1a",
    "--code-text": "#e6e0f5",
    "--inline-code-bg": "#2f2650",
    "--inline-code-text": "#fca5a5",
    "--shadow": "rgba(0, 0, 0, 0.4)",
    "--shadow-strong": "rgba(0, 0, 0, 0.65)",
    "--overlay": "rgba(6, 4, 12, 0.72)",
}

_MONO = {
    "--bg": "#f4f4f5",
    "--surface": "#ffffff",
    "--surface-2": "#fafafa",
    "--surface-3": "#f4f4f5",
    "--border": "#e4e4e7",
    "--border-strong": "#d4d4d8",
    "--text": "#3f3f46",
    "--text-strong": "#18181b",
    "--text-muted": "#a1a1aa",
    "--accent": "#71717a",
    "--accent-strong": "#52525b",
    "--accent-text": "#3f3f46",
    "--accent-soft": "#f4f4f5",
    "--code-bg": "#18181b",
    "--code-text": "#e4e4e7",
    "--inline-code-bg": "#f4f4f5",
    "--inline-code-text": "#52525b",
    "--shadow": "rgba(24, 24, 27, 0.05)",
    "--shadow-strong": "rgba(24, 24, 27, 0.25)",
    "--overlay": "rgba(24, 24, 27, 0.5)",
}

THEMES: dict[str, Theme] = {
    "original": Theme("original", "Original", _ORIGINAL),
    "midnight": Theme("midnight", "Midnight", _MIDNIGHT, mermaid="dark"),
    "emerald": Theme("emerald", "Emerald", _EMERALD),
    "sunset": Theme("sunset", "Sunset", _SUNSET),
    "grape": Theme("grape", "Grape", _GRAPE, mermaid="dark"),
    "mono": Theme("mono", "Mono", _MONO),
}

_AUTO_LIGHT = "original"
_AUTO_DARK = "midnight"


def theme_names() -> list[str]:
    """Selectable theme names, including the ``auto`` special case."""
    return [*THEMES, "auto"]


def get_theme(name: str | None) -> Theme:
    """Resolve a theme name, falling back to :data:`DEFAULT_THEME`."""
    if not name:
        return THEMES[DEFAULT_THEME]
    return THEMES.get(name.strip().lower(), THEMES[DEFAULT_THEME])


def _declarations(colors: dict[str, str]) -> str:
    return "\n".join(f"    {var}: {colors[var]};" for var in _VARS if var in colors)


@cache
def theme_css(name: str) -> str:
    """Build the ``<style>`` body holding every theme's custom properties."""
    blocks = [
        ":root,",
        f':root[data-theme="{DEFAULT_THEME}"] {{',
        _declarations(THEMES[DEFAULT_THEME].colors),
        "}",
    ]
    for theme in THEMES.values():
        if theme.name == DEFAULT_THEME:
            continue
        blocks.append(f':root[data-theme="{theme.name}"] {{')
        blocks.append(_declarations(theme.colors))
        blocks.append("}")
    blocks.append(':root[data-theme="auto"] {')
    blocks.append(_declarations(THEMES[_AUTO_LIGHT].colors))
    blocks.append("}")
    blocks.append("@media (prefers-color-scheme: dark) {")
    blocks.append('  :root[data-theme="auto"] {')
    blocks.append(_declarations(THEMES[_AUTO_DARK].colors))
    blocks.append("  }")
    blocks.append("}")
    return "\n".join(blocks)
