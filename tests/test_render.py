from __future__ import annotations

import json
from pathlib import Path

from app.render import (
    classify,
    first_heading,
    is_asset,
    language_label,
    media_type,
    plain_title,
    render_document,
    render_markdown,
    render_source,
    resolve_types,
)


def test_default_types_are_markdown_only() -> None:
    types = resolve_types(["md"])
    assert classify(".md", types).kind == "markdown"
    assert classify(".json", types) is None
    assert classify(".py", types) is None


def test_group_names_resolve() -> None:
    types = resolve_types(["md", "images", "json", "yaml", "code"])
    assert classify(".png", types).kind == "image"
    assert classify(".JPG", types).kind == "image"
    assert classify(".json", types).kind == "json"
    assert classify(".yml", types).kind == "yaml"
    assert classify(".py", types).kind == "code"
    assert classify(".rs", types).kind == "code"
    assert classify(".png", types).renderable is False
    assert is_asset(classify(".png", types)) is True
    assert is_asset(classify(".py", types)) is False


def test_explicit_extension_entry() -> None:
    types = resolve_types([".rs"])
    assert classify(".rs", types).kind == "code"
    assert classify(".py", types) is None


def test_all_includes_everything() -> None:
    types = resolve_types(["all"])
    assert classify(".md", types) is not None
    assert classify(".png", types) is not None
    assert classify(".py", types) is not None
    assert classify(".rs", types) is not None
    assert classify(".weird", types) is None


def test_unknown_entries_are_reported() -> None:
    types = resolve_types(["md", "nope"])
    assert types.unknown == ("nope",)


def test_string_and_none_inputs() -> None:
    assert resolve_types("json").extensions == frozenset({".json", ".jsonc"})
    assert resolve_types(None).extensions == frozenset({".md", ".markdown", ".mdown"})
    assert resolve_types(123).extensions == frozenset()


def test_media_types() -> None:
    assert media_type(Path("a.md")) == "text/markdown; charset=utf-8"
    assert media_type(Path("a.svg")) == "image/svg+xml"
    assert media_type(Path("a.json")) == "application/json; charset=utf-8"
    assert media_type(Path("a.png")) == "image/png"
    assert media_type(Path("a.unknownext")) == "application/octet-stream"


def test_mermaid_block_becomes_div(tmp_path: Path) -> None:
    path = tmp_path / "d.md"
    path.write_text("```mermaid\ngraph TD\nA-->B\n```\n", encoding="utf-8")
    html = render_markdown(path)
    assert '<div class="mermaid">' in html
    assert "A--&gt;B" in html
    assert "```" not in html


def test_mermaid_with_info_string_and_tildes(tmp_path: Path) -> None:
    path = tmp_path / "d.md"
    path.write_text("~~~mermaid title=x\ngraph TD\nA-->B\n~~~\n", encoding="utf-8")
    assert '<div class="mermaid">' in render_markdown(path)


def test_mermaid_source_is_escaped(tmp_path: Path) -> None:
    path = tmp_path / "d.md"
    path.write_text("```mermaid\ngraph TD\nA[\"a<b\"]-->B\n```\n", encoding="utf-8")
    html = render_markdown(path)
    assert "&lt;b" in html
    assert "<b>" not in html


def test_markdown_links_drop_extension(tmp_path: Path) -> Path:
    path = tmp_path / "d.md"
    path.write_text(
        "[a](other.md) [b](https://x.test/other.md) [c](#frag) [d](img.png)\n",
        encoding="utf-8",
    )
    html = render_markdown(path)
    assert 'href="other"' in html
    assert 'href="https://x.test/other.md"' in html
    assert 'href="#frag"' in html
    assert 'href="img.png"' in html


def test_render_json_is_pretty_printed(tmp_path: Path) -> None:
    path = tmp_path / "c.json"
    path.write_text('{"b":1,"a":[1,2]}', encoding="utf-8")
    html = render_source(path)
    assert "\n  " in html
    assert "&quot;b&quot;" in html or '"b"' in html
    # the raw text is not the compact original any more
    assert '{"b":1,"a":[1,2]}' not in html


def test_render_invalid_json_keeps_content(tmp_path: Path) -> None:
    path = tmp_path / "c.json"
    path.write_text("{not json", encoding="utf-8")
    assert "{not json" in render_source(path)


def test_render_source_has_line_numbers(tmp_path: Path) -> None:
    path = tmp_path / "a.py"
    path.write_text("x = 1\ny = 2\n", encoding="utf-8")
    html = render_source(path)
    assert "codehilitetable" in html
    assert 'class="linenos"' in html


def test_render_source_truncates(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.render.MAX_RENDER_BYTES", 10)
    path = tmp_path / "big.txt"
    path.write_text("y" * 500, encoding="utf-8")
    html = render_source(path)
    assert "Truncated" in html
    assert "y" * 500 not in html


def test_render_document_dispatches(tmp_path: Path) -> None:
    md = tmp_path / "a.md"
    md.write_text("# Title\n", encoding="utf-8")
    types = resolve_types(["md"])
    assert "<h1" in render_document(md, classify(".md", types))
    code = tmp_path / "a.txt"
    code.write_text("plain\n", encoding="utf-8")
    assert "plain" in render_document(code, classify(".txt", resolve_types(["text"])))


def test_first_heading(tmp_path: Path) -> None:
    path = tmp_path / "a.md"
    path.write_text("intro\n\n# Real Title\n\n# Second\n", encoding="utf-8")
    assert first_heading(path) == "Real Title"
    assert first_heading(tmp_path / "missing.md") is None


def test_plain_title_strips_markup() -> None:
    assert plain_title("<h1>Hello <code>world</code></h1>", "fallback") == "Hello world"
    assert plain_title("<p>no heading</p>", "fallback") == "fallback"
    assert plain_title("<h1>AT&amp;T</h1>", "fallback") == "AT&T"


def test_language_label(tmp_path: Path) -> None:
    types = resolve_types(["md", "json", "code", "text"])
    assert language_label(Path("a.md"), classify(".md", types)) == "Markdown"
    assert language_label(Path("a.json"), classify(".json", types)) == "JSON"
    assert language_label(Path("a.py"), classify(".py", types)) == "PY"
    assert language_label(Path("a.weird"), classify(".weird", resolve_types([".weird"]))) == "WEIRD"


def test_json_dumps_is_used_for_scalars_too(tmp_path: Path) -> None:
    path = tmp_path / "a.json"
    path.write_text(json.dumps(42), encoding="utf-8")
    assert "42" in render_source(path)
