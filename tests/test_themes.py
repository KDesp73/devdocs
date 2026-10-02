from __future__ import annotations

import re

from app.themes import DEFAULT_THEME, THEMES, get_theme, theme_css, theme_names


def test_original_is_the_default_and_keeps_the_old_palette() -> None:
    theme = get_theme(None)
    assert theme.name == DEFAULT_THEME == "original"
    assert theme.colors["--bg"] == "#f1f5f9"  # slate-100
    assert theme.colors["--surface"] == "#ffffff"
    assert theme.colors["--accent"] == "#3b82f6"  # blue-500
    assert theme.colors["--code-bg"] == "#0f172a"
    assert theme.colors["--inline-code-text"] == "#be123c"


def test_unknown_theme_falls_back() -> None:
    assert get_theme("nope").name == "original"
    assert get_theme("  MIDNIGHT ").name == "midnight"


def test_theme_names_include_auto() -> None:
    names = theme_names()
    assert names[: len(THEMES)] == list(THEMES)
    assert names[-1] == "auto"


def test_every_theme_defines_the_same_variables() -> None:
    variables = {frozenset(theme.colors) for theme in THEMES.values()}
    assert len(variables) == 1
    assert next(iter(variables)) >= {
        "--bg",
        "--surface",
        "--border",
        "--text",
        "--accent",
        "--code-bg",
        "--shadow",
        "--overlay",
    }


def test_dark_themes_pair_with_dark_mermaid() -> None:
    assert THEMES["midnight"].mermaid == "dark"
    assert THEMES["grape"].mermaid == "dark"
    assert THEMES["original"].mermaid == "neutral"


def test_css_covers_every_theme_and_auto() -> None:
    css = theme_css("original")
    for theme in THEMES:
        assert f':root[data-theme="{theme}"]' in css
    assert ':root[data-theme="auto"]' in css
    assert "@media (prefers-color-scheme: dark)" in css
    # the dark override of "auto" has to come last to win the cascade
    assert css.index(':root[data-theme="auto"] {') < css.index("@media (prefers-color-scheme")


def test_css_contains_no_unescaped_placeholders() -> None:
    css = theme_css("original")
    assert "{{" not in css
    assert re.search(r"^\s*--[a-z0-9-]+: (#[0-9a-f]{3,8}|rgba?\()", css, re.MULTILINE)
