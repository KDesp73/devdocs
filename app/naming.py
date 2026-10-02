"""Turn file and directory names into human readable labels.

Handles every naming convention found in the wild: ``kebab-case``,
``snake_case``, ``camelCase``, ``PascalCase``, dot separated and space
separated names, while keeping acronyms (``API``, ``HTTP``), mixed case
words (``iOS``, ``eBay``) and numbered identifiers (``P4.4``, ``v1.2.3``)
intact.
"""

from __future__ import annotations

import re

__all__ = ["prettify", "split_words", "title_word"]

#: One pass over a name yields either a word or a separator.  A dot that
#: glues digits together (``P4.4``, ``1.2.3``) is not a separator, which is why
#: this cannot be a plain ``re.split``.
_TOKENS = re.compile(
    r"[A-Za-z]?\d+(?:\.\d+)+"  # version-like run, e.g. "v1.2.3" or "4.4.1"
    r"|[A-Z]{1,4}\d+(?:\.\d+)*"  # acronym plus number, e.g. "P4" or "HTTP2"
    r"|[A-Z]+(?![a-z])"  # acronym run, e.g. "API" in "APIReference"
    r"|[A-Z][a-z0-9]*"  # capitalised word, e.g. "Native"
    r"|[a-z][a-z0-9]*"  # lowercase word, e.g. "backend" or "v2"
    r"|[0-9]+[a-z0-9]*"  # digit run, e.g. "5" or "2fa"
    r"|\.(?![0-9])"  # extension separator, e.g. the dot in "openapi.json"
    r"|[^A-Za-z0-9.]+"  # runs of dashes, underscores, spaces, dots
    r"|[^A-Za-z0-9]"  # anything else, e.g. a stray trailing dot
)
_MAX_MERGE = 4
#: A two or three letter all-lowercase name is almost always an acronym
#: (``er.md``, ``api.md``, ``faq.md``); title casing those reads as a mistake.
_SHORT_ACRONYM_MAX = 3


def split_words(name: str) -> list[str]:
    """Split a name into words, keeping acronyms glued to their neighbours."""
    words: list[str] = []
    previous_end = -1
    for match in _TOKENS.finditer(name):
        token = match.group()
        if not token[:1].isalnum():
            continue
        # A short all-caps run directly after a lowercase run is almost
        # always part of the same word: "iOS", "macOSX" -- but only when no
        # separator sits between them, so "read_ME" stays two words.
        adjacent = match.start() == previous_end
        if (
            words
            and adjacent
            and token.isupper()
            and words[-1].islower()
            and len(token) <= _MAX_MERGE
        ):
            words[-1] += token
        else:
            words.append(token)
        previous_end = match.end()
    return words


def title_word(word: str) -> str:
    """Capitalise a single word without destroying acronyms or camel case."""
    if len(word) < 2:
        return word.upper() if word.isalpha() else word
    if word.isupper():
        return word
    if any(char.isupper() for char in word[1:]):
        return word
    for index, char in enumerate(word):
        if char.isalpha():
            return word[:index] + char.upper() + word[index + 1 :].lower()
    return word


def prettify(name: str) -> str:
    """Return a display label for a file or directory name.

    >>> prettify("NativeBackendSetup")
    'Native Backend Setup'
    >>> prettify("getting_started")
    'Getting Started'
    >>> prettify("APIReference")
    'API Reference'
    >>> prettify("er")
    'er'
    """
    words = split_words(name)
    if not words:
        return name.strip()
    if len(words) == 1 and len(words[0]) <= _SHORT_ACRONYM_MAX and words[0].islower():
        return words[0]
    return " ".join(title_word(word) for word in words)
