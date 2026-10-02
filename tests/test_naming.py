from __future__ import annotations

import pytest

from app.naming import prettify, split_words, title_word


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        # the reported bug
        ("NativeBackendSetup", "Native Backend Setup"),
        ("nativeBackendSetup", "Native Backend Setup"),
        ("Native_Backend_Setup", "Native Backend Setup"),
        ("native-backend-setup", "Native Backend Setup"),
        ("native backend setup", "Native Backend Setup"),
        # acronyms survive
        ("APIReference", "API Reference"),
        ("HTTP-handling", "HTTP Handling"),
        ("HTMLParser", "HTML Parser"),
        ("README", "README"),
        # already friendly
        ("index", "Index"),
        ("getting-started", "Getting Started"),
        ("getting_started", "Getting Started"),
        ("v2_api", "V2 Api"),
        ("iOSSetup", "iOS Setup"),
        # digits and edge cases
        ("2fa", "2fa"),
        ("utf8", "Utf8"),
        ("a", "a"),
        ("__init__", "Init"),
        ("", ""),
        ("---", "---"),
    ],
)
def test_prettify(name: str, expected: str) -> None:
    assert prettify(name) == expected


def test_split_words_keeps_acronyms_glued() -> None:
    assert split_words("iOSSupport") == ["iOS", "Support"]
    assert split_words("HTTP2Server") == ["HTTP2", "Server"]


def test_split_words_does_not_merge_across_separators() -> None:
    assert split_words("read_ME") == ["read", "ME"]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("P4.4-gdpr-technical", "P4.4 Gdpr Technical"),
        ("P3.2-explainability-fairness", "P3.2 Explainability Fairness"),
        ("v1.2.3-notes", "V1.2.3 Notes"),
        ("4.4.1", "4.4.1"),
        ("P4", "P4"),
        ("HTTP2Server", "HTTP2 Server"),
        ("openapi.json", "Openapi Json"),
        ("docusaurus.config", "Docusaurus Config"),
        ("10-setup", "10 Setup"),
    ],
)
def test_numbered_identifiers_stay_glued(name: str, expected: str) -> None:
    assert prettify(name) == expected


@pytest.mark.parametrize(
    ("word", "expected"),
    [("api", "Api"), ("API", "API"), ("iOS", "iOS"), ("v2", "V2"), ("3d", "3D")],
)
def test_title_word(word: str, expected: str) -> None:
    assert title_word(word) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("er", "er"),
        ("api", "api"),
        ("faq", "faq"),
        ("CLI", "CLI"),
        ("iOS", "iOS"),
        ("web", "web"),
        ("docs", "Docs"),
        ("v2", "v2"),
    ],
)
def test_short_lowercase_names(name: str, expected: str) -> None:
    assert prettify(name) == expected
