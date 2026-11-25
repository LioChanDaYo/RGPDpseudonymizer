"""Story 16.1: the guard against English labels that show in French
(G1, G2, controls K3).

Written by the BMAD dev agent (Claude), tests first. ``pyside6-lupdate``
extracts a ``tr()`` source written with a ``\\u`` escape without its
backslash, so the ``.ts`` key holds ``u`` and four hex digits, the English
is stored under that key and the app, which asks with the real characters,
never finds it.

* G1 reads every ``tr()`` and ``translate(context, ...)`` call under
  ``gdpr_pseudonymizer/gui/`` whose source is a string literal, with ``ast``
  and ``ast.get_source_segment``, and fails on any escape that writes a
  character by its code or name (``\\u``, ``\\U``, ``\\x``, ``\\N{...}``,
  octal). ``\\n`` and the quote, backslash and control escapes are allowed;
  an escaped backslash is consumed as one escape.
* G2 parses ``en.ts`` and ``fr.ts`` and fails on a ``u`` or ``U`` followed
  by four hex digits in any ``<source>`` or ``<translation>``, outside
  ``REAL_WORDS`` (empty); every ``REAL_WORDS`` entry must still match a
  message of its file.
* K3 checks the scanner itself on invented code snippets.

Every file is located from this test file's own checkout. Preconditions
fail with ``pytest.fail("PRE: ...")``, never with an ``assert``; the first
``assert`` after them is the expected failure on the unfixed code
(``# expected failure``). No Qt, no spaCy, no database.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from xml.etree import ElementTree

import pytest

ROOT = Path(__file__).resolve().parents[2]
GUI_DIR = ROOT / "gdpr_pseudonymizer" / "gui"
I18N_DIR = GUI_DIR / "i18n"

# One escape: an escaped backslash is consumed whole (the ``.`` branch), so
# ``\\u00e9`` (a backslash then ``u00e9``) is not read as ``\u00e9``.
ESCAPE = re.compile(
    r"\\(u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|x[0-9a-fA-F]{2}|N\{[^}]*\}|[0-7]{1,3}|.)",
    re.DOTALL,
)

# A ``u`` or ``U`` run that ``lupdate`` leaves when it drops the backslash.
BROKEN_RUN = re.compile(r"[uU][0-9a-fA-F]{4}")

# Real words of a ``.ts`` file that match BROKEN_RUN, per file:
# (context, field, matched text, full text). Empty: none measured (SM, PO).
# An entry is added only with the PO's yes and a comment saying why.
REAL_WORDS: dict[str, frozenset[tuple[str, str, str, str]]] = {
    "en": frozenset(),
    "fr": frozenset(),
}


def _flagged(escape: str) -> bool:
    """True for an escape that writes a character by its code or name."""
    return escape[0] in "uUxN" or escape[0] in "01234567"


class _TrCalls(ast.NodeVisitor):
    """Collect (line, context, raw literal text) of each literal tr() source."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.classes: list[str] = []
        self.found: list[tuple[int, str, str]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        context: str | None = None
        arg: ast.expr | None = None
        if isinstance(func, ast.Attribute) and func.attr == "tr" and node.args:
            context = self.classes[-1] if self.classes else "<module>"
            arg = node.args[0]
        elif (
            isinstance(func, ast.Attribute)
            and func.attr == "translate"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            context = node.args[0].value
            arg = node.args[1]
        if (
            context is not None
            and isinstance(arg, ast.Constant)
            and isinstance(arg.value, str)
        ):
            raw = ast.get_source_segment(self.text, arg) or ""
            self.found.append((arg.lineno, context, raw))
        self.generic_visit(node)


def tr_literals(text: str) -> list[tuple[int, str, str]]:
    """(line, context, raw source text) of every literal tr()/translate() source."""
    visitor = _TrCalls(text)
    visitor.visit(ast.parse(text))
    return visitor.found


def scan(text: str, name: str) -> list[str]:
    """``name:line [context] \\escape ...`` for each call with a flagged escape."""
    hits = []
    for line, context, raw in tr_literals(text):
        flagged = [
            "\\" + m.group(1) for m in ESCAPE.finditer(raw) if _flagged(m.group(1))
        ]
        if flagged:
            hits.append(f"{name}:{line} [{context}] {' '.join(flagged)}")
    return hits


# ---------------------------------------------------------------------------
# G1: the code
# ---------------------------------------------------------------------------


def test_g1_no_escape_by_code_or_name_in_tr_literals() -> None:
    files = sorted(GUI_DIR.rglob("*.py"))
    if not files:
        pytest.fail(f"PRE: no .py file under {GUI_DIR}")
    n_literals = 0
    hits: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        n_literals += len(tr_literals(text))
        hits.extend(scan(text, path.relative_to(ROOT).as_posix()))
    if n_literals < 400:
        pytest.fail(f"PRE: only {n_literals} literal tr() sources found under gui/")
    # expected failure
    assert not hits, (
        f"{len(hits)} tr()/translate() literal(s) with an escape by code or "
        "name (write the character itself):\n" + "\n".join(hits)
    )


# ---------------------------------------------------------------------------
# G2: the .ts files
# ---------------------------------------------------------------------------


def _ts_messages(lang: str) -> list[tuple[str, str, str]]:
    """(context, field, text) of every <source> and <translation> of *lang*.ts."""
    path = I18N_DIR / f"{lang}.ts"
    if not path.is_file():
        pytest.fail(f"PRE: {path} not found")
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        pytest.fail(f"PRE: {path} does not parse: {exc}")
    rows = []
    for context in root.findall("context"):
        name = context.findtext("name") or ""
        for message in context.findall("message"):
            for field in ("source", "translation"):
                element = message.find(field)
                if element is not None and element.text:
                    rows.append((name, field, element.text))
    return rows


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_g2_no_broken_run_in_ts(lang: str) -> None:
    rows = _ts_messages(lang)
    n_messages = sum(1 for _, field, _ in rows if field == "source")
    if n_messages < 300:
        pytest.fail(f"PRE: only {n_messages} messages in {lang}.ts")
    allowed = REAL_WORDS[lang]
    hits = []
    seen: set[tuple[str, str, str, str]] = set()
    for context, field, text in rows:
        runs = []
        for m in BROKEN_RUN.finditer(text):
            entry = (context, field, m.group(0), text)
            if entry in allowed:
                seen.add(entry)
            else:
                runs.append(m.group(0))
        if runs:
            hits.append(f"{lang}.ts [{context}] <{field}> {' '.join(runs)}")
    stale = sorted(allowed - seen)
    message = (
        f"{len(hits)} <source>/<translation> text(s) of {lang}.ts with a "
        "u+4-hex run (extracted without its backslash):\n" + "\n".join(hits)
    )
    if stale:
        message += f"\nREAL_WORDS entries matching no message: {stale}"
    # expected failure
    assert not hits and not stale, message


# ---------------------------------------------------------------------------
# K3: the scanner itself (invented code snippets, not product text)
# ---------------------------------------------------------------------------

FLAGS = [
    r'self.tr("\u00e9")',
    r'self.tr("\U0001F600")',
    r'self.tr("\x41")',
    r'self.tr("\N{BULLET}")',
    r'self.tr("\351")',
    r'QCoreApplication.translate("C", "\u00e9")',
]
LEAVES = [
    r'self.tr("a\nb")',
    r'self.tr("a\\u00e9")',
    'self.tr("é")',
]


@pytest.mark.parametrize("kind", ["flags", "leaves"])
def test_k3_scanner(kind: str) -> None:
    snippets = FLAGS if kind == "flags" else LEAVES
    for snippet in snippets:
        if len(tr_literals(snippet)) != 1:
            pytest.fail(f"PRE: {snippet!r} is not read as one tr() literal")
    counts = [len(scan(snippet, "snippet")) for snippet in snippets]
    expected = [1] * len(snippets) if kind == "flags" else [0] * len(snippets)
    assert counts == expected, list(zip(snippets, counts))
