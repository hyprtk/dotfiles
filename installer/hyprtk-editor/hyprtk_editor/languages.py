"""Language detection and the language menu.

Pygments ships 600+ lexers; the editor exposes them by alias, detects by file
name first and by shebang second, and keeps a curated short list for the
language picker (the full set stays available through Settings).
"""

from __future__ import annotations

import os
from functools import lru_cache

from pygments.lexers import TextLexer, get_lexer_by_name, get_lexer_for_filename, guess_lexer
from pygments.util import ClassNotFound

# (display name, Pygments alias) — the picker's short list, in the order a
# desktop editor usually shows it.
CURATED = [
    ("Plain Text", "text"),
    ("Python", "python"),
    ("Shell", "bash"),
    ("JavaScript", "javascript"),
    ("TypeScript", "typescript"),
    ("JSON", "json"),
    ("YAML", "yaml"),
    ("TOML", "toml"),
    ("INI", "ini"),
    ("Markdown", "markdown"),
    ("HTML", "html"),
    ("CSS", "css"),
    ("SCSS", "scss"),
    ("XML", "xml"),
    ("C", "c"),
    ("C++", "cpp"),
    ("C#", "csharp"),
    ("Java", "java"),
    ("Kotlin", "kotlin"),
    ("Rust", "rust"),
    ("Go", "go"),
    ("Lua", "lua"),
    ("QML", "qml"),
    ("Qt Style Sheets", "qss"),
    ("SQL", "sql"),
    ("PHP", "php"),
    ("Ruby", "ruby"),
    ("Perl", "perl"),
    ("Swift", "swift"),
    ("Dart", "dart"),
    ("R", "r"),
    ("Julia", "julia"),
    ("Haskell", "haskell"),
    ("Elixir", "elixir"),
    ("Erlang", "erlang"),
    ("Scala", "scala"),
    ("Nix", "nix"),
    ("Dockerfile", "docker"),
    ("Makefile", "make"),
    ("CMake", "cmake"),
    ("Diff", "diff"),
    ("Regex", "regex"),
    ("LaTeX", "tex"),
    ("reStructuredText", "rst"),
    ("AsciiDoc", "asciidoc"),
    ("Org", "org"),
    ("Vimscript", "vim"),
    ("Git Config", "gitconfig"),
]

# Comment tokens for the line-comment action. Block comments are optional.
COMMENTS = {
    "python": ("#", ("'''", "'''")),
    "pycon": ("#", None),
    "bash": ("#", None),
    "zsh": ("#", None),
    "fish": ("#", None),
    "shell": ("#", None),
    "yaml": ("#", None),
    "toml": ("#", None),
    "nix": ("#", None),
    "make": ("#", None),
    "cmake": ("#", None),
    "docker": ("#", None),
    "gitconfig": ("#", None),
    "ruby": ("#", None),
    "perl": ("#", None),
    "r": ("#", None),
    "julia": ("#", None),
    "elixir": ("#", None),
    "nim": ("#", None),
    "ini": (";", None),
    "qss": ("//", ("/*", "*/")),
    "c": ("//", ("/*", "*/")),
    "cpp": ("//", ("/*", "*/")),
    "csharp": ("//", ("/*", "*/")),
    "java": ("//", ("/*", "*/")),
    "javascript": ("//", ("/*", "*/")),
    "typescript": ("//", ("/*", "*/")),
    "kotlin": ("//", ("/*", "*/")),
    "rust": ("//", ("/*", "*/")),
    "go": ("//", ("/*", "*/")),
    "swift": ("//", ("/*", "*/")),
    "dart": ("//", ("/*", "*/")),
    "scala": ("//", ("/*", "*/")),
    "php": ("//", ("/*", "*/")),
    "qml": ("//", ("/*", "*/")),
    "css": ("/*", ("/*", "*/")),
    "scss": ("//", ("/*", "*/")),
    "less": ("//", ("/*", "*/")),
    "sql": ("--", ("/*", "*/")),
    "lua": ("--", ("--[[", "]]")),
    "haskell": ("--", ("{-", "-}")),
    "elm": ("--", ("{-", "-}")),
    "tex": ("%", None),
    "erlang": ("%", None),
    "matlab": ("%", None),
    "vim": ('"', None),
    "xml": ("<!--", ("<!--", "-->")),
    "html": ("<!--", ("<!--", "-->")),
    "markdown": ("<!--", ("<!--", "-->")),
    "rst": ("..", None),
}


@lru_cache(maxsize=512)
def lexer_for(alias: str):
    try:
        return get_lexer_by_name(alias or "text", stripnl=False, ensurenl=False)
    except ClassNotFound:
        return TextLexer(stripnl=False, ensurenl=False)


# Filenames Pygments has no lexer for, or resolves to a name that reads wrong in
# the status bar. Values are Pygments aliases. `.conf`/`.cfg` are decided by
# content instead (see `_conf_alias`) because that extension covers INI-shaped
# config, Hyprland-style `key = value`, and files that are neither.
EXPLICIT_ALIASES = {
    ".rasi": "css",   # rofi themes: CSS-shaped; guess_lexer calls them "css+lasso"
}

CONF_SUFFIXES = (".conf", ".cfg")

# Enough to see the first section header or a handful of key = value lines.
CONF_SAMPLE_BYTES = 4096


def _conf_alias(text: str) -> str:
    """INI if ``text`` is section/key-value shaped, plain text otherwise.

    A generic `.conf` is either an INI-ish config (`[section]`, `key = value`,
    which is what Hyprland, dunst and most app configs look like) or something
    with its own grammar (Apache, nginx). Colouring the second kind as INI would
    be a guess presented as fact, so only the first gets a lexer.
    """
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped[0] in "#;":
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            return "ini"
        if "=" in stripped and "{" not in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key and all(char.isalnum() or char in "._-$" for char in key):
                return "ini"
    return "text"


def _sample(path: str, text: str) -> str:
    if text:
        return text[:CONF_SAMPLE_BYTES]
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read(CONF_SAMPLE_BYTES)
    except OSError:
        return ""


def detect(path: str, first_line: str = "", text: str = "") -> str:
    """Return the Pygments alias best matching ``path`` (``text`` if unknown).

    ``text`` is optional context: a generic `.conf` is only coloured when its
    content is INI-shaped, and callers that already hold the document pass it
    instead of making this read the file.
    """
    if path:
        name = os.path.basename(path)
        lowered = name.lower()
        for suffix, alias in EXPLICIT_ALIASES.items():
            if lowered.endswith(suffix):
                return alias
        if lowered.endswith(CONF_SUFFIXES):
            return _conf_alias(_sample(path, text) or first_line)
        try:
            lexer = get_lexer_for_filename(name, stripnl=False, ensurenl=False)
            return (lexer.aliases or ["text"])[0]
        except ClassNotFound:
            pass
    if first_line:
        try:
            lexer = guess_lexer(first_line, stripnl=False, ensurenl=False)
            alias = (lexer.aliases or ["text"])[0]
            # guess_lexer over-eagerly claims plain prose; keep it conservative.
            if alias in ("text", "pycon"):
                return "text"
            return alias
        except ClassNotFound:
            pass
    return "text"



def display_name(alias: str) -> str:
    for name, known in CURATED:
        if known == alias:
            return name
    try:
        lexer = get_lexer_by_name(alias)
        return lexer.name
    except ClassNotFound:
        return alias.title() if alias else "Plain Text"


def languages() -> list[dict]:
    return [{"name": name, "alias": alias} for name, alias in CURATED]


def comment_tokens(alias: str) -> tuple[str, tuple[str, str] | None]:
    return COMMENTS.get(alias, ("#", None))
