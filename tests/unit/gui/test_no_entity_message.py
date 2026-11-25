"""Story 14.1: the desktop panel shown when nothing is found (Q2).

The texts are the ones Lionel approved on 2026-11-25, word for word: the
French in his own wording, and its English. He approved them as test strings
too, so they are held here as literals.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from gdpr_pseudonymizer.gui.screens.processing import ProcessingScreen

APPROVED_FR = (
    "Aucun nom détecté. Un nom peut malgré tout échapper à la détection, "
    "en particulier un prénom seul dans un texte court : relisez le texte "
    "à l'étape suivante. Pour ajouter un nom oublié : sélectionnez-le, "
    "clic droit, « Ajouter comme entité », puis « Personne » ou le type voulu."
)
APPROVED_EN = (
    "No name detected. A name can still escape detection, especially a first "
    "name on its own in a short text: read the text in the next step. To add "
    'a missed name: select it, right-click, "Add as entity", then "Person" or '
    "the right type."
)

REASSURES = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 14.1 tests first: the no-entity message says the document may "
        "hold nothing personal"
    ),
)


def pre(condition: bool, message: str) -> None:
    """Fail a precondition outside strict AssertionError-only xfail handling."""
    if not condition:
        pytest.fail(f"PRE: {message}")


@pytest.fixture()
def processing_screen(qtbot, main_window):  # type: ignore[no-untyped-def]
    idx = main_window._screens["processing"]
    screen = main_window.stack.widget(idx)
    assert isinstance(screen, ProcessingScreen)
    return screen


@pytest.fixture()
def english(qapp, main_window) -> Iterator[None]:  # type: ignore[no-untyped-def]
    """Use English after window setup and restore French even on failure."""
    from gdpr_pseudonymizer.gui.i18n.translator import switch_language

    try:
        pre(switch_language(qapp, "en"), "switch_language_en")
        qapp.processEvents()
        yield
    finally:
        switch_language(qapp, "fr")
        qapp.processEvents()


def _show_no_entity_panel(screen: ProcessingScreen) -> str:
    from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult

    result = DetectionResult(
        document_text="Le rapport est prêt.",
        detected_entities=[],
        pseudonym_previews={},
        entity_type_counts={},
        db_path="test.db",
        passphrase="test_pass_secure",
        theme="neutral",
        input_file="test.txt",
        detection_time_seconds=1.0,
    )
    screen._on_finished(result)
    pre(not screen.warning_panel.isHidden(), "warning_panel_shown")
    return screen._warning_label.text()


@REASSURES
def test_no_entity_panel_french(processing_screen):  # type: ignore[no-untyped-def]
    assert _show_no_entity_panel(processing_screen) == APPROVED_FR


@REASSURES
def test_no_entity_panel_english(processing_screen, english):  # type: ignore[no-untyped-def]
    assert _show_no_entity_panel(processing_screen) == APPROVED_EN
