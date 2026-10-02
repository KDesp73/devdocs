from __future__ import annotations

import pytest

from app.naming import prettify


def test_index_lists_documents(write, client) -> None:
    write("index.md", "# Home\n")
    write("guides/setup.md", "# Setup\n")
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert "Home" in body
    assert 'href="/guides/setup"' in body
    assert '<div class="index-section">Guides</div>' in body


def test_navigation_uses_pretty_labels(write, client) -> None:
    write("NativeBackendSetup.md", "# Native\n")
    write("getting-started/install.md", "# Install\n")
    write("reference/APIReference.md", "# API\n")
    body = client.get("/").text
    assert ">Native Backend Setup<" in body
    assert ">Getting Started<" in body
    assert ">Install<" in body
    assert ">API Reference<" in body
    assert "Nativebackendsetup" not in body
    assert "Apireference" not in body


def test_breadcrumbs_use_pretty_labels(write, client) -> None:
    write("NativeBackendSetup/gettingStarted.md", "# Page\n")
    response = client.get("/NativeBackendSetup/gettingStarted")
    assert response.status_code == 200
    body = response.text
    assert '<a href="/NativeBackendSetup">Native Backend Setup</a>' in body
    assert "<span>Getting Started</span>" in body
    assert "<title>Page — Docs Docs</title>" in body


def test_current_folder_is_expanded(write, client) -> None:
    write("guides/deep/page.md", "# Page\n")
    body = client.get("/guides/deep/page").text
    open_folders = body.count('class="nav-folder open"')
    assert open_folders == 2
    assert 'class="active" aria-current="page"' in body


def test_folder_that_only_prefix_matches_stays_closed(write, client) -> None:
    write("guide.md", "# Guide\n")
    write("guides/page.md", "# Page\n")
    body = client.get("/guide").text
    assert 'class="nav-folder open"' not in body


def test_mermaid_block_is_rendered(write, client) -> None:
    write("index.md", "```mermaid\ngraph TD\n  A-->B\n```\n")
    body = client.get("/index").text
    assert '<div class="mermaid">' in body
    assert "A--&gt;B" in body


def test_static_assets_are_served(client) -> None:
    for name in ("devdocs.css", "devdocs.js"):
        response = client.get(f"/static/{name}")
        assert response.status_code == 200
        assert response.content


def test_missing_document_renders_404_page(client) -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    assert "Not found" in response.text
    assert 'href="/"' in response.text


def test_trailing_slash_is_ignored(write, client) -> None:
    write("a.md", "# A\n")
    assert client.get("/a/").status_code == 200


def test_html_in_names_is_escaped(write, client) -> None:
    write("<script>x</script>.md", "# Safe\n")
    response = client.get("/")
    assert "<script>x</script>" not in response.text
    assert "&lt;script&gt;" in response.text


def test_mermaid_config_and_theme_are_emitted(make_client, write) -> None:
    write("index.md", "# Home\n")
    client = make_client(theme="midnight")
    body = client.get("/").text
    assert 'data-theme="midnight"' in body
    assert '"theme": "dark"' in body
    assert '--bg: #0b1220;' in body


def test_branch_badge_and_edit_link(make_client, write) -> None:
    write("index.md", "# Home\n")
    write("guides/setup.md", "# Setup\n")
    client = make_client(github_repo="acme/widgets", github_branch="trunk")
    body = client.get("/guides/setup").text
    assert 'class="branch"' in body
    assert ">trunk<" in body
    # no git repository here, so the file path is relative to the docs dir
    assert "https://github.com/acme/widgets/blob/trunk/guides/setup.md" in body


def test_no_edit_link_without_repo(make_client, write) -> None:
    write("index.md", "# Home\n")
    body = make_client().get("/").text
    assert "github.com" not in body


def test_json_documents_are_published(make_client, write) -> None:
    write("index.md", "# Home\n")
    write("data/config.json", '{"b": 1}')
    client = make_client(file_types=["md", "json"])
    response = client.get("/data/config.json")
    assert response.status_code == 200
    body = response.text
    assert "Config" in body
    assert "codehilitetable" in body
    assert 'href="/raw/data/config.json"' in body
    # the index links to it as well
    assert 'href="/data/config.json"' in client.get("/").text


def test_unlisted_file_types_are_not_published(make_client, write) -> None:
    write("index.md", "# Home\n")
    write("secret.env", "TOKEN=1\n")
    client = make_client()
    assert client.get("/secret.env").status_code == 404


def test_images_are_served_and_navigated(make_client, write, write_bytes, tiny_png) -> None:
    write("index.md", "# Home\n")
    write_bytes("assets/logo.png", tiny_png)
    client = make_client(file_types=["md", "images"])
    response = client.get("/assets/logo.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == tiny_png
    assert response.headers["x-content-type-options"] == "nosniff"
    # images appear in the navigation tree, under their folder
    body = client.get("/").text
    assert 'href="/assets/logo.png"' in body
    assert ">Logo</span>" in body
    assert 'class="image-icon"' in body
    # ...and still on the page it was linked from
    assert 'href="/assets/logo.png"' in client.get("/index").text


def test_images_stay_out_of_the_tree_when_unlisted(
    make_client, write, write_bytes, tiny_png
) -> None:
    write("index.md", "# Home\n")
    write_bytes("assets/logo.png", tiny_png)
    client = make_client(file_types=["md"])
    assert client.get("/assets/logo.png").status_code == 404
    assert 'href="/assets/logo.png"' not in client.get("/").text


def test_image_can_be_linked_from_markdown(make_client, write, write_bytes, tiny_png) -> None:
    write("index.md", "# Home\n\n![logo](assets/logo.png)\n")
    write_bytes("assets/logo.png", tiny_png)
    client = make_client(file_types=["md", "images"])
    assert client.get("/assets/logo.png").status_code == 200
    assert 'src="assets/logo.png"' in client.get("/index").text


def test_raw_route(make_client, write) -> None:
    write("index.md", "# Home\n")
    write("data/a.json", '{"a": 1}')
    client = make_client(file_types=["md", "json"])
    response = client.get("/raw/data/a.json")
    assert response.status_code == 200
    assert response.text == '{"a": 1}'
    assert response.headers["content-type"].startswith("application/json")
    assert client.get("/raw/nope.json").status_code == 404


def test_ignored_files_are_skipped(make_client, write) -> None:
    write("index.md", "# Home\n")
    write("drafts/secret.md", "# Secret\n")
    client = make_client(ignore=["drafts"])
    assert client.get("/drafts/secret").status_code == 404
    assert "Secret" not in client.get("/").text


def test_empty_docs_directory(make_client) -> None:
    response = make_client().get("/")
    assert response.status_code == 200
    assert "Nothing published yet" in response.text


@pytest.mark.parametrize("name", ["NativeBackendSetup", "getting_started", "APIReference"])
def test_label_round_trip(write, client, name: str) -> None:
    write(f"{name}.md", "# Page\n")
    body = client.get("/").text
    assert f">{prettify(name)}<" in body


def test_fastapi_reference_paths_belong_to_the_docs(make_client, write) -> None:
    """devdocs pages win over FastAPI's own /docs, /redoc and /openapi.json."""
    write("index.md", "# Home\n")
    write("docs.md", "# User docs page\n")
    write("openapi.json", '{"openapi": "3.1.0"}')
    client = make_client(file_types=["md", "json"])
    docs_response = client.get("/docs")
    assert docs_response.status_code == 200
    assert "User docs page" in docs_response.text
    # no redoc page published, and FastAPI no longer answers for it either
    redoc = client.get("/redoc")
    assert redoc.status_code == 404
    assert "Not found" in redoc.text
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "codehilite" in response.text
