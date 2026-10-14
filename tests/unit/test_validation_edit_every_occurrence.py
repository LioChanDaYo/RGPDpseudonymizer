"""Story 10.9, T10: the CLI applies a text edit to every occurrence (guard).

The desktop app is brought in line with this behaviour (AC1); the CLI itself
does not change (AC6), so this test passes before and after the fix. No Qt
import. Invented names only (AC8).
"""

from __future__ import annotations

from unittest.mock import patch

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.models import ValidationSession
from gdpr_pseudonymizer.validation.workflow import ValidationWorkflow

NAME = "Quentrel Zorbalia"
EDIT = "Quentrel Zorbalia Quentrix"

# PERSON "Quentrel Zorbalia" at 0 and 72; the edit is found at both places.
EXT_TEXT = (
    "Quentrel Zorbalia Quentrix rejoint le projet. "
    "Le contrat est signé avec Quentrel Zorbalia Quentrix."
)


def _entity(document_text: str, name: str, nth: int) -> DetectedEntity:
    """The nth occurrence of ``name`` in ``document_text`` (0-based)."""
    start = -1
    for _ in range(nth + 1):
        start = document_text.find(name, start + 1)
    end = start + len(name)
    assert start >= 0
    assert document_text[start:end] == name
    return DetectedEntity(
        text=name,
        entity_type="PERSON",
        start_pos=start,
        end_pos=end,
        confidence=0.9,
        source="spacy",
    )


def _assigner(entity: DetectedEntity) -> str:
    return "X"


def test_cli_edit_applies_to_every_occurrence() -> None:
    """T10 (AC6): "modify" in the CLI sends the edit at every occurrence."""
    session = ValidationSession(document_path="zorbalia.txt", document_text=EXT_TEXT)
    for nth in (0, 1):
        session.add_entity(_entity(EXT_TEXT, NAME, nth))
    # Precondition: the session holds the two occurrences.
    assert [(e.start_pos, e.end_pos) for e in session.entities] == [
        (0, 17),
        (72, 89),
    ]

    with (
        patch(
            "gdpr_pseudonymizer.validation.workflow.get_user_action",
            side_effect=["modify"],
        ),
        patch(
            "gdpr_pseudonymizer.validation.workflow.get_text_input",
            side_effect=[EDIT],
        ),
        patch("gdpr_pseudonymizer.validation.workflow.display_warning_message"),
        patch("gdpr_pseudonymizer.validation.workflow.display_info_message"),
    ):
        ValidationWorkflow()._review_entities_by_type(session, _assigner)

    assert sorted(
        (e.entity_type, e.start_pos, e.end_pos, e.text)
        for e in session.get_validated_entities()
    ) == [
        ("PERSON", 0, 26, EDIT),
        ("PERSON", 72, 98, EDIT),
    ]
