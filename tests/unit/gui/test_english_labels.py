"""Story 16.1: the English app shows the English of every label that has one
(L1, L2, X1, controls K1, K2, K4, K6).

Written by the BMAD dev agent (Claude), tests first. The 37 pairs of the
story's table, (context, French as the code builds it at run time), are
asked of the shipped ``en.qm`` with a standalone ``QTranslator`` that is
never installed, so no other test sees English. Only X1 installs English,
through ``switch_language``, and an autouse fixture restores French.

* L1: rows 1 to 29 give the table's English, exactly (the nine with a
  symbol get it back: no string holding ``u25b6`` and the like can pass).
* L2: rows N1 to N5, the five labels of the same cause, give their English.
* X1: a real ``EntityPanel`` in the English app shows English.
* K1: each row's French is the literal source of a ``tr()`` call in the
  row's file and class (ties the table to the code).
* K2: rows W1 to W3 already work and keep working.
* K4: ``fr.qm`` holds no translation (French is the source).
* K6: the file-filter message is in ``en.ts`` and left out of ``en.qm``.

The French and English are written with real letters and with ``\\u``
escapes for the symbols, so the reader sees each code point. Every file is
located from this test file's own checkout; a PRE checks that the
translator module loads from the same directory. Preconditions fail with
``pytest.fail("PRE: ...")``, never with an ``assert``; the first ``assert``
after them is the expected failure on the unfixed code (``# expected
failure``). No spaCy, no database, no window shown.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree

import pytest
from PySide6.QtCore import QCoreApplication, QTranslator
from pytestqt.qtbot import QtBot

from gdpr_pseudonymizer.gui.i18n import switch_language
from gdpr_pseudonymizer.gui.i18n import translator as translator_module
from gdpr_pseudonymizer.gui.widgets.entity_panel import EntityPanel

ROOT = Path(__file__).resolve().parents[3]
GUI_DIR = ROOT / "gdpr_pseudonymizer" / "gui"
I18N_DIR = GUI_DIR / "i18n"

# (row, file under gdpr_pseudonymizer/gui/, context, French, English)
ROWS: list[tuple[str, str, str, str, str]] = [
    ("1", "widgets/entity_panel.py", "EntityPanel", "Entités (0)", "Entities (0)"),
    ("2", "widgets/entity_panel.py", "EntityPanel", "Entités (%1)", "Entities (%1)"),
    (
        "3",
        "widgets/entity_panel.py",
        "EntityPanel",
        "Masquer les rejetées",
        "Hide rejected",
    ),
    (
        "4",
        "widgets/entity_panel.py",
        "EntityPanel",
        "Filtrer les entités...",
        "Filter entities...",
    ),
    (
        "5",
        "widgets/entity_panel.py",
        "EntityPanel",
        "Accepter les déjà connues",
        "Accept already known",
    ),
    ("6", "widgets/entity_panel.py", "EntityPanel", "déjà connu", "already known"),
    ("7", "widgets/entity_panel.py", "EntityPanel", "Toutes vérifiées", "All verified"),
    (
        "8",
        "widgets/entity_panel.py",
        "EntityPanel",
        "Accepter la sélection (%1)",
        "Accept selection (%1)",
    ),
    (
        "9",
        "widgets/entity_panel.py",
        "EntityPanel",
        "Rejeter la sélection (%1)",
        "Reject selection (%1)",
    ),
    (
        "10",
        "widgets/entity_editor.py",
        "EntityEditor",
        "Éditeur de document",
        "Document Editor",
    ),
    (
        "11",
        "widgets/entity_editor.py",
        "EntityEditor",
        "Affiche le document avec les entités surlignées en couleur",
        "Displays the document with color-highlighted entities",
    ),
    (
        "12",
        "widgets/entity_editor.py",
        "EntityEditor",
        "Ajouter comme entité",
        "Add as entity",
    ),
    (
        "13",
        "widgets/passphrase_dialog.py",
        "PassphraseDialog",
        "Phrase secrète",
        "Passphrase",
    ),
    (
        "14",
        "widgets/passphrase_dialog.py",
        "PassphraseDialog",
        "Phrase secrète :",
        "Passphrase:",
    ),
    (
        "15",
        "widgets/passphrase_dialog.py",
        "PassphraseDialog",
        "Entrez votre phrase secrète",
        "Enter your passphrase",
    ),
    (
        "16",
        "widgets/passphrase_dialog.py",
        "PassphraseDialog",
        "Afficher/masquer la phrase secrète",
        "Show/hide passphrase",
    ),
    (
        "17",
        "widgets/passphrase_dialog.py",
        "PassphraseDialog",
        "Mémoriser pour cette session",
        "Remember for this session",
    ),
    (
        "18",
        "widgets/passphrase_dialog.py",
        "PassphraseDialog",
        "Continuer ▶",
        "Continue ▶",
    ),
    (
        "19",
        "widgets/passphrase_dialog.py",
        "PassphraseDialog",
        "Aucune base détectée — créez-en une nouvelle",
        "No database detected — create a new one",
    ),
    (
        "20",
        "screens/processing.py",
        "ProcessingScreen",
        "Continuer ▶",
        "Continue ▶",
    ),
    (
        "21",
        "screens/validation.py",
        "ValidationScreen",
        "◀ Retour",
        "◀ Back",
    ),
    (
        "22",
        "screens/validation.py",
        "ValidationScreen",
        "Finaliser ▶",
        "Finalize ▶",
    ),
    ("23", "screens/batch.py", "BatchScreen", "◀ Retour", "◀ Back"),
    ("24", "screens/database.py", "DatabaseScreen", "◀ Retour", "◀ Back"),
    ("25", "screens/settings.py", "SettingsScreen", "← Retour", "← Back"),
    (
        "26",
        "screens/stub.py",
        "StubScreen",
        "← Retour à l'accueil",
        "← Back to home",
    ),
    ("27", "widgets/step_indicator.py", "StepIndicator", "Sélection", "Selection"),
    ("28", "widgets/step_indicator.py", "StepIndicator", "Résumé", "Summary"),
    ("29", "widgets/step_indicator.py", "StepIndicator", "Résultat", "Result"),
    (
        "N1",
        "screens/validation.py",
        "ValidationScreen",
        "◀ Précédent",
        "◀ Previous",
    ),
    (
        "N2",
        "screens/validation.py",
        "ValidationScreen",
        "Suivant ▶",
        "Next ▶",
    ),
    (
        "N3",
        "screens/validation.py",
        "ValidationScreen",
        "Valider et terminer ▶",
        "Validate and finish ▶",
    ),
    (
        "N4",
        "screens/validation.py",
        "ValidationScreen",
        "Valider et continuer ▶",
        "Validate and continue ▶",
    ),
    (
        "N5",
        "widgets/entity_panel.py",
        "EntityPanel",
        "Masquer les validées",
        "Hide confirmed",
    ),
    (
        "W1",
        "screens/database.py",
        "DatabaseScreen",
        "… et %1 autre(s)",
        "… and %1 more",
    ),
    (
        "W2",
        "screens/database.py",
        "DatabaseScreen",
        "• %1 → %2 (mot : %3)",
        "• %1 → %2 (word: %3)",
    ),
    (
        "W3",
        "screens/database.py",
        "DatabaseScreen",
        "• %1 → %2",
        "• %1 → %2",
    ),
]
BY_ROW = {row[0]: row for row in ROWS}
BROKEN_ROWS = [row for row in ROWS if row[0].isdigit()]
NEW_ROWS = [row for row in ROWS if row[0].startswith("N")]
WORKING_ROWS = [row for row in ROWS if row[0].startswith("W")]

FILE_FILTER = "Documents (*.txt *.md *.pdf *.docx *.xlsx *.csv);;Tous (*)"
FILTER_CONTEXTS = ["BatchScreen", "DropZone", "MainWindow"]


@pytest.fixture(autouse=True)
def _restore_french(qapp: QCoreApplication) -> Iterator[None]:
    """Restore French (the source language) after each test."""
    yield
    switch_language(qapp, "fr")


def _pre_same_checkout() -> None:
    """The translator module loads from this checkout's i18n directory."""
    loaded = Path(translator_module._I18N_DIR).resolve()
    if loaded != I18N_DIR.resolve():
        pytest.fail(
            f"PRE: translator._I18N_DIR is {loaded}, not this checkout's {I18N_DIR}"
        )


def _qm(name: str) -> QTranslator:
    """A standalone translator on this checkout's *name*, never installed."""
    _pre_same_checkout()
    path = I18N_DIR / name
    if not path.is_file():
        pytest.fail(f"PRE: {path} not found")
    translator = QTranslator()
    if not translator.load(str(path)):
        pytest.fail(f"PRE: {path} does not load")
    return translator


# ---------------------------------------------------------------------------
# L1, L2: the shipped en.qm on the 29 broken keys and the 5 new labels
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("row", "file", "context", "french", "english"),
    BROKEN_ROWS,
    ids=[f"row{row[0]}" for row in BROKEN_ROWS],
)
def test_l1_broken_key_gives_english(
    qapp: QCoreApplication,
    row: str,
    file: str,
    context: str,
    french: str,
    english: str,
) -> None:
    got = _qm("en.qm").translate(context, french)
    # expected failure
    assert got == english, f"row {row} [{context}]: en.qm gives {got!r}"


@pytest.mark.parametrize(
    ("row", "file", "context", "french", "english"),
    NEW_ROWS,
    ids=[row[0] for row in NEW_ROWS],
)
def test_l2_new_label_gives_english(
    qapp: QCoreApplication,
    row: str,
    file: str,
    context: str,
    french: str,
    english: str,
) -> None:
    got = _qm("en.qm").translate(context, french)
    # expected failure
    assert got == english, f"row {row} [{context}]: en.qm gives {got!r}"


# ---------------------------------------------------------------------------
# X1: a real EntityPanel in the English app
# ---------------------------------------------------------------------------


def test_x1_entity_panel_shows_english(qapp: QCoreApplication, qtbot: QtBot) -> None:
    _pre_same_checkout()
    if not switch_language(qapp, "en"):
        pytest.fail("PRE: switch_language(qapp, 'en') returned False")
    panel = EntityPanel()
    qtbot.addWidget(panel)
    panel.retranslateUi()
    shown = (
        panel._title_label.text(),
        panel._hide_rejected_cb.text(),
        panel._hide_confirmed_cb.text(),
        panel._find_field.placeholderText(),
        panel._accept_known_btn.text(),
    )
    expected = tuple(BY_ROW[r][4] for r in ("1", "3", "N5", "4", "5"))
    # expected failure
    assert shown == expected


# ---------------------------------------------------------------------------
# K1: each row's French is a literal tr() source in its file and class
# ---------------------------------------------------------------------------


def _tr_sources(path: Path) -> set[tuple[str, str]]:
    """(context, run-time string) of every literal tr()/translate() source."""
    text = path.read_text(encoding="utf-8")
    found: set[tuple[str, str]] = set()

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.classes: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
            self.classes.append(node.name)
            self.generic_visit(node)
            self.classes.pop()

        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
            func = node.func
            context: str | None = None
            arg: ast.expr | None = None
            if isinstance(func, ast.Attribute) and func.attr == "tr" and node.args:
                context = self.classes[-1] if self.classes else None
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
                found.add((context, arg.value))
            self.generic_visit(node)

    Visitor().visit(ast.parse(text))
    return found


@pytest.mark.parametrize(
    ("row", "file", "context", "french", "english"),
    ROWS,
    ids=[f"row{row[0]}" for row in ROWS],
)
def test_k1_french_is_a_tr_source_of_its_class(
    row: str, file: str, context: str, french: str, english: str
) -> None:
    path = GUI_DIR / file
    if not path.is_file():
        pytest.fail(f"PRE: {path} not found")
    assert (context, french) in _tr_sources(path), (
        f"row {row}: no literal tr() source of [{context}] in {file} "
        "evaluates to the table's French"
    )


# ---------------------------------------------------------------------------
# K2: the three labels that already work
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("row", "file", "context", "french", "english"),
    WORKING_ROWS,
    ids=[row[0] for row in WORKING_ROWS],
)
def test_k2_working_label_keeps_english(
    qapp: QCoreApplication,
    row: str,
    file: str,
    context: str,
    french: str,
    english: str,
) -> None:
    got = _qm("en.qm").translate(context, french)
    assert got == english, f"row {row} [{context}]: en.qm gives {got!r}"


# ---------------------------------------------------------------------------
# K4: fr.qm holds no translation
# ---------------------------------------------------------------------------


def test_k4_fr_qm_is_empty(qapp: QCoreApplication) -> None:
    assert _qm("fr.qm").isEmpty()


# ---------------------------------------------------------------------------
# K6: the file filter is in en.ts and left out of en.qm (BACKLOG-EN-QM)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("context", FILTER_CONTEXTS)
def test_k6_file_filter_left_out_of_en_qm(qapp: QCoreApplication, context: str) -> None:
    ts_path = I18N_DIR / "en.ts"
    if not ts_path.is_file():
        pytest.fail(f"PRE: {ts_path} not found")
    root = ElementTree.parse(ts_path).getroot()
    in_ts = any(
        (ctx.findtext("name") or "") == context
        and (message.findtext("source") or "") == FILE_FILTER
        for ctx in root.findall("context")
        for message in ctx.findall("message")
    )
    assert in_ts, f"en.ts holds no file-filter message in [{context}]"
    assert _qm("en.qm").translate(context, FILE_FILTER) == ""
