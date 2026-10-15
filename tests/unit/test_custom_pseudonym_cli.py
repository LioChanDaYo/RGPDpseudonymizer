"""Story 10.11: a custom pseudonym in the command-line review, and the review's
last decision (T25-T35; after QA's FAIL, T36c, T38 and T41).

Each test runs ``DocumentProcessor.process_document`` with its interactive
validation: detection is replaced, the keys ([C], [E], [T], [R], [P], Space)
and the typed texts come from lists, the final confirmation answers yes, and
the warning lines are recorded. The assertions read the written file and the
stored rows. Each test asserts its preconditions (messages start with "PRE:")
before the behaviour under test; the first assertion after them is the
expected failure on the unfixed code. A refusal test asserts that exactly one
warning was shown and that it is not empty, never its wording. No Qt import.
Invented names only.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import gdpr_pseudonymizer.pseudonym.library_manager as library_module
from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.pseudonym.library_manager import LibraryBasedPseudonymManager

PASSPHRASE = "zorbalia_pass_A_123!"
QZ = "Quentrel Zorbalia"
CUSTOM = "Xantor Vellion"

CLI1 = "Quentrel Zorbalia a signé avec Zorbaville. Le contrat est avec Zorbalia."
CLI2 = "Quentrel Zorbalia rejoint le projet. Le projet est avec Quentrel."
ORGDOC = "Zorbaville a signé."
CORR = "Quentrel Zorbalia a signé le contrat."
ONE = (
    "Quentrel Zorbalia a signé avec Zorbaville. Le contrat est avec Quentrel Zorbalia."
)
QZZ = "Quentrel Zorbalia a signé avec Zorbal."
# The corrected name and the lone "Zorbal" of QZZ.
QZZ_SPANS = [(0, len(QZ)), (QZZ.find("Zorbal."), QZZ.find("Zorbal.") + len("Zorbal"))]


def _at(text: str, name: str, entity_type: str, start: int) -> DetectedEntity:
    assert text[start : start + len(name)] == name, "PRE: entity slice"
    return DetectedEntity(
        text=name,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(name),
        confidence=0.9,
        source="spacy",
    )


def _spans(entities: list[DetectedEntity]) -> list[tuple[int, int]]:
    return sorted((e.start_pos, e.end_pos) for e in entities)


def _replacements(output: str, source: str, spans: list[tuple[int, int]]) -> list[str]:
    """The string written in place of each span (in span order); every other
    character of the source unchanged."""
    segments: list[str] = []
    position = 0
    for start, end in sorted(spans):
        segments.append(source[position:start])
        position = end
    segments.append(source[position:])
    pattern = "(.+?)".join(re.escape(segment) for segment in segments)
    match = re.fullmatch(pattern, output, flags=re.DOTALL)
    assert match is not None, f"text damaged or a span not replaced: {output!r}"
    return list(match.groups())


def _new_db(tmp_path: Path) -> str:
    db = str(tmp_path / "mappings.db")
    init_database(db, PASSPHRASE)
    return db


def _stored(db: str, key: str, entity_type: str) -> tuple[Any, ...] | None:
    """(full_name, first_name, last_name, pseudonym_full, pseudonym_first,
    pseudonym_last) of the stored row of (key, type), or None."""
    with open_database(db, PASSPHRASE) as session:
        row = SQLiteMappingRepository(session).find_by_full_name_and_type(
            key, entity_type
        )
        if row is None:
            return None
        return (
            row.full_name,
            row.first_name,
            row.last_name,
            row.pseudonym_full,
            row.pseudonym_first,
            row.pseudonym_last,
        )


def _cli(
    tmp_path: Path,
    db: str,
    name: str,
    text: str,
    entities: list[DetectedEntity],
    keys: list[str],
    typed: list[str],
) -> tuple[str | None, list[str]]:
    """One ``process`` run: (the written text, or None if it failed; the
    warning lines shown)."""
    source = tmp_path / name
    source.write_text(text, encoding="utf-8")
    output = tmp_path / f"{name}.out.txt"
    warnings: list[str] = []
    with (
        patch.object(
            DocumentProcessor,
            "_detect_and_filter_entities",
            side_effect=lambda *a, **k: [DetectedEntity(**vars(e)) for e in entities],
        ),
        patch("gdpr_pseudonymizer.validation.ui.readchar.readkey", return_value="\r"),
        patch(
            "gdpr_pseudonymizer.validation.workflow.get_user_action", side_effect=keys
        ),
        patch(
            "gdpr_pseudonymizer.validation.workflow.get_text_input", side_effect=typed
        ),
        patch(
            "gdpr_pseudonymizer.validation.workflow.get_confirmation", return_value=True
        ),
        patch(
            "gdpr_pseudonymizer.validation.workflow.display_warning_message",
            side_effect=lambda message: warnings.append(str(message)),
        ),
    ):
        result = DocumentProcessor(db_path=db, passphrase=PASSPHRASE).process_document(
            str(source), str(output)
        )
    if not result.success:
        return None, warnings
    return output.read_text(encoding="utf-8"), warnings


def _cli1_entities() -> list[DetectedEntity]:
    return [
        _at(CLI1, QZ, "PERSON", 0),
        _at(CLI1, "Zorbaville", "ORG", CLI1.find("Zorbaville")),
        _at(CLI1, "Zorbalia", "PERSON", CLI1.rfind("Zorbalia")),
    ]


def _qzz(first: str) -> list[DetectedEntity]:
    """QZZ with ``first`` found at the start and the lone "Zorbal"."""
    return [_at(QZZ, first, "PERSON", 0), _at(QZZ, "Zorbal", "PERSON", QZZ_SPANS[1][0])]


def test_cli_custom_written_stored_and_reused(tmp_path: Path) -> None:
    """T25 (AC4, AC1, AC2, Q4): [C] is written at the name, its lone last name
    takes the last part, the row is stored split, and a later run reuses the
    pseudonym and its first part."""
    db = _new_db(tmp_path)
    written, warnings = _cli(
        tmp_path,
        db,
        "one.txt",
        CLI1,
        _cli1_entities(),
        ["change_pseudonym", "confirm"],
        [CUSTOM],
    )
    assert written is not None and warnings == [], "PRE: processed"
    parts = _replacements(written, CLI1, _spans(_cli1_entities()))
    assert [parts[0], parts[2]] == [CUSTOM, "Vellion"], written  # expected failure
    assert _stored(db, QZ, "PERSON") == (
        QZ,
        "Quentrel",
        "Zorbalia",
        CUSTOM,
        "Xantor",
        "Vellion",
    )
    later = [
        _at(CLI2, QZ, "PERSON", 0),
        _at(CLI2, "Quentrel", "PERSON", CLI2.rfind("Quentrel")),
    ]
    written2, _ = _cli(tmp_path, db, "two.txt", CLI2, later, ["confirm"], [])
    assert written2 is not None
    assert _replacements(written2, CLI2, _spans(later)) == [CUSTOM, "Xantor"]


def test_cli_pseudonym_of_another_name_is_refused(tmp_path: Path) -> None:
    """T26 (Q2): the stored pseudonym of another name is refused with one
    warning; the document is still written, with another pseudonym."""
    db = _new_db(tmp_path)
    written0, _ = _cli(
        tmp_path,
        db,
        "org.txt",
        ORGDOC,
        [_at(ORGDOC, "Zorbaville", "ORG", 0)],
        ["confirm"],
        [],
    )
    other = _stored(db, "Zorbaville", "ORG")
    assert written0 is not None and other is not None, "PRE: other name stored"
    written, warnings = _cli(
        tmp_path,
        db,
        "corr.txt",
        CORR,
        [_at(CORR, QZ, "PERSON", 0)],
        ["change_pseudonym", "confirm"],
        [other[3]],
    )
    assert len(warnings) == 1 and warnings[0].strip(), warnings  # expected failure
    assert written is not None
    stored = _stored(db, QZ, "PERSON")
    assert stored is not None and stored[3] != other[3]


def test_cli_real_name_of_the_document_is_refused(tmp_path: Path) -> None:
    """T27 (Q2, Q-C): a real name of the document is refused with one
    warning."""
    db = _new_db(tmp_path)
    entities = [
        _at(ONE, QZ, "PERSON", 0),
        _at(ONE, "Zorbaville", "ORG", ONE.find("Zorbaville")),
        _at(ONE, QZ, "PERSON", ONE.rfind(QZ)),
    ]
    written, warnings = _cli(
        tmp_path,
        db,
        "one.txt",
        ONE,
        entities,
        ["change_pseudonym", "confirm", "confirm"],
        ["Zorbaville"],
    )
    assert len(warnings) == 1 and warnings[0].strip(), warnings  # expected failure
    assert written is not None
    assert _replacements(written, ONE, _spans(entities))[0] != "Zorbaville"


def test_cli_without_custom_unchanged(tmp_path: Path) -> None:
    """T28 (AC13, a guard): without [C] nothing changes: stored and written,
    no warning."""
    db = _new_db(tmp_path)
    written, warnings = _cli(
        tmp_path, db, "one.txt", CLI1, _cli1_entities(), ["confirm", "confirm"], []
    )
    assert written is not None and warnings == []
    parts = _replacements(written, CLI1, _spans(_cli1_entities()))
    stored = _stored(db, QZ, "PERSON")
    assert stored is not None and parts[0] == stored[3] and "orbal" not in written


def test_cli_correction_after_custom_keeps_stored_pseudonym(tmp_path: Path) -> None:
    """T29 (AC5, a guard): [C] on "Quentrel", then [P] back to it and [E] to
    a stored name: the stored name keeps its pseudonym."""
    db = _new_db(tmp_path)
    written0, _ = _cli(
        tmp_path, db, "corr.txt", CORR, [_at(CORR, QZ, "PERSON", 0)], ["confirm"], []
    )
    before = _stored(db, QZ, "PERSON")
    assert written0 is not None and before is not None, "PRE: stored"
    custom = f"{before[4]} Vellion"  # Q-D: "Quentrel" already has before[4]
    written, warnings = _cli(
        tmp_path,
        db,
        "qzz.txt",
        QZZ,
        _qzz("Quentrel"),
        ["change_pseudonym", "previous", "modify", "confirm"],
        [custom, QZ],
    )
    assert warnings == [], "PRE: the pseudonym was accepted"
    assert written is not None
    assert written.startswith(before[3] + " a signé avec "), written
    assert _stored(db, QZ, "PERSON") == before


def test_cli_custom_after_correction_keeps_both(tmp_path: Path) -> None:
    """T30 (AC11, PO R2): [E], [P], [C] keeps the correction and the
    pseudonym."""
    db = _new_db(tmp_path)
    written, warnings = _cli(
        tmp_path,
        db,
        "qzz.txt",
        QZZ,
        _qzz("Quentrel"),
        ["modify", "previous", "change_pseudonym", "confirm"],
        [QZ, CUSTOM],
    )
    assert written is not None and warnings == [], "PRE: processed"
    assert written.startswith(CUSTOM + " a signé avec "), written  # expected failure
    assert _stored(db, QZ, "PERSON") == (
        QZ,
        "Quentrel",
        "Zorbalia",
        CUSTOM,
        "Xantor",
        "Vellion",
    )


def test_cli_correction_kept_after_back_and_space(tmp_path: Path) -> None:
    """T31 (AC11, Q-F leak 1): [E], [P], Space keeps the correction."""
    db = _new_db(tmp_path)
    written, _ = _cli(
        tmp_path,
        db,
        "qzz.txt",
        QZZ,
        _qzz("Quentrel"),
        ["modify", "previous", "confirm", "confirm"],
        [QZ],
    )
    assert written is not None, "PRE: processed"
    name = _replacements(written, QZZ, QZZ_SPANS)[0]
    assert "orbal" not in name and "Quentrel" not in name, written  # expected failure
    assert _stored(db, QZ, "PERSON") is not None


def test_cli_accept_after_reject_writes_the_name(tmp_path: Path) -> None:
    """T32 (AC11, Q-F leak 2): [R], [P], Space writes the name."""
    db = _new_db(tmp_path)
    entities = _qzz(QZ)
    written, _ = _cli(
        tmp_path,
        db,
        "qzz.txt",
        QZZ,
        entities,
        ["reject", "previous", "confirm", "confirm"],
        [],
    )
    assert written is not None, "PRE: processed"
    name = _replacements(written, QZZ, _spans(entities))[0]
    assert "Quentrel" not in name and "orbal" not in name, written  # expected failure


def test_cli_name_with_a_stored_part_requires_it(tmp_path: Path) -> None:
    """T33 (Q-D "Refuse", first name): one warning, then the pseudonym that
    starts with the stored part is accepted, written and stored."""
    db = _new_db(tmp_path)
    written0, _ = _cli(
        tmp_path, db, "corr.txt", CORR, [_at(CORR, QZ, "PERSON", 0)], ["confirm"], []
    )
    stored = _stored(db, QZ, "PERSON")
    assert written0 is not None and stored is not None and stored[4], "PRE: part"
    text = "Quentrel Zorbal a signé le contrat."
    good = f"{stored[4]} Vellion"
    written, warnings = _cli(
        tmp_path,
        db,
        "qd.txt",
        text,
        [_at(text, "Quentrel Zorbal", "PERSON", 0)],
        ["change_pseudonym", "change_pseudonym"],
        [CUSTOM, good],
    )
    assert len(warnings) == 1 and warnings[0].strip(), warnings  # expected failure
    assert written == f"{good} a signé le contrat."
    assert _stored(db, "Quentrel Zorbal", "PERSON") == (
        "Quentrel Zorbal",
        "Quentrel",
        "Zorbal",
        good,
        stored[4],
        "Vellion",
    )


@pytest.mark.parametrize(
    "case", ["last_part_same_run", "last_part_later_run", "one_word_later_run"]
)
def test_cli_generated_never_reuses_a_custom_part(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """T34 (AC3, PO R8): a generated pseudonym never reuses a value of a
    custom pseudonym that the library does not track (the last part on a
    one-word name; a one-word custom pseudonym). The library is forced to
    offer "Vellion" for the last name the test generates."""
    original = LibraryBasedPseudonymManager._select_last_name
    target = "Zorbal" if case == "one_word_later_run" else "Zorbalia"

    def forced(
        self: LibraryBasedPseudonymManager, real_last_name: str | None = None
    ) -> str:
        if real_last_name == target:
            return "Vellion"
        return original(self, real_last_name)

    monkeypatch.setattr(LibraryBasedPseudonymManager, "_select_last_name", forced)
    db = _new_db(tmp_path)
    if case == "last_part_same_run":
        text = "Zorbal a signé avec Quentrel Zorbalia."
        entities = [_at(text, "Zorbal", "PERSON", 0), _at(text, QZ, "PERSON", 20)]
        written, _ = _cli(
            tmp_path,
            db,
            "one.txt",
            text,
            entities,
            ["change_pseudonym", "confirm"],
            [CUSTOM],
        )
        assert written is not None, "PRE: processed"
        parts = _replacements(written, text, _spans(entities))
        assert parts[0] == CUSTOM, written  # expected failure
        generated = parts[1]
        custom_name, custom_row = "Zorbal", (
            "Zorbal",
            "Zorbal",
            None,
            CUSTOM,
            "Xantor",
            "Vellion",
        )
        other = QZ
    else:
        if case == "last_part_later_run":
            first_text, custom_name, typed = (
                "Zorbal a signé le contrat.",
                "Zorbal",
                CUSTOM,
            )
            custom_row = ("Zorbal", "Zorbal", None, CUSTOM, "Xantor", "Vellion")
            later_text, other = "Quentrel Zorbalia a signé le contrat.", QZ
        else:
            first_text, custom_name, typed = CORR, QZ, "Vellion"
            custom_row = (QZ, None, None, "Vellion", None, None)
            later_text, other = "Quentrix Zorbal a signé le contrat.", "Quentrix Zorbal"
        written, _ = _cli(
            tmp_path,
            db,
            "one.txt",
            first_text,
            [_at(first_text, custom_name, "PERSON", 0)],
            ["change_pseudonym"],
            [typed],
        )
        assert written is not None, "PRE: processed"
        assert written.startswith(typed + " a signé"), written  # expected failure
        written2, _ = _cli(
            tmp_path,
            db,
            "two.txt",
            later_text,
            [_at(later_text, other, "PERSON", 0)],
            ["confirm"],
            [],
        )
        assert written2 is not None
        generated = _replacements(written2, later_text, [(0, len(other))])[0]
    assert _stored(db, custom_name, "PERSON") == custom_row
    assert "Vellion" not in generated.split(), generated
    row = _stored(db, other, "PERSON")
    assert row is not None and "Vellion" not in (row[3].split() + [row[4], row[5]])


def test_cli_type_change_after_correction_keeps_it(tmp_path: Path) -> None:
    """T35 (AC11, PO F2): [E], [P], [T] keeps the correction."""
    db = _new_db(tmp_path)
    written, _ = _cli(
        tmp_path,
        db,
        "qzz.txt",
        QZZ,
        _qzz("Quentrel"),
        ["modify", "previous", "change_type", "confirm"],
        [QZ, "ORG"],
    )
    assert written is not None, "PRE: processed"
    name = _replacements(written, QZZ, QZZ_SPANS)[0]
    assert "orbal" not in name and "Quentrel" not in name, written  # expected failure
    assert _stored(db, QZ, "ORG") is not None


# ---------------------------------------------------------------------------
# Amendment after QA's FAIL (Task 8): MW-001, GUARD-001, the PO's A1. Stored
# rows with fixed parts (AC20).
# ---------------------------------------------------------------------------


def _store_qz(db: str, pseudonym_first: str, pseudonym_last: str) -> None:
    """ "Quentrel Zorbalia" stored with fixed parts, as the library stores a
    row (a last part of two words is stored whole)."""
    with open_database(db, PASSPHRASE) as session:
        SQLiteMappingRepository(session).save(
            Entity(
                entity_type="PERSON",
                full_name=QZ,
                first_name="Quentrel",
                last_name="Zorbalia",
                pseudonym_full=f"{pseudonym_first} {pseudonym_last}",
                pseudonym_first=pseudonym_first,
                pseudonym_last=pseudonym_last,
                theme="neutral",
            )
        )


def test_cli_two_word_stored_last_part_example_accepted(tmp_path: Path) -> None:
    """T38 (Q-D "Refuse", last name; QA MW-001): the real last name's stored
    part has two words; [C] shows one warning holding the example, then the
    example is accepted, written and stored with that part whole."""
    db = _new_db(tmp_path)
    _store_qz(db, "Quorix", "Le Velmar")
    text = "Quentrix Zorbalia a signé le contrat."
    good = "Xantor Le Velmar"
    written, warnings = _cli(
        tmp_path,
        db,
        "qd.txt",
        text,
        [_at(text, "Quentrix Zorbalia", "PERSON", 0)],
        ["change_pseudonym", "change_pseudonym", "confirm"],
        [CUSTOM, good],
    )
    assert len(warnings) == 1 and good in warnings[0], warnings  # expected failure
    assert written == f"{good} a signé le contrat."
    assert _stored(db, "Quentrix Zorbalia", "PERSON") == (
        "Quentrix Zorbalia",
        "Quentrix",
        "Zorbalia",
        good,
        "Xantor",
        "Le Velmar",
    )


def test_cli_own_part_on_lone_name_keeps_later_full_names(tmp_path: Path) -> None:
    """T36c (AC19; QA GUARD-001; the command line has no pre-filled value,
    so Q-H does not apply): [C] on a lone "Quentrel" typed with the part it
    already has; a later run's "Quentrel Zorbix" still starts with it, in
    the file and in its stored row."""
    db = _new_db(tmp_path)
    _store_qz(db, "Quorix", "Velmar")
    text = "Quentrel a signé le contrat."
    written, warnings = _cli(
        tmp_path,
        db,
        "lone.txt",
        text,
        [_at(text, "Quentrel", "PERSON", 0)],
        ["change_pseudonym"],
        ["Quorix"],
    )
    assert written == "Quorix a signé le contrat." and warnings == [], "PRE: set"
    later = "Quentrel Zorbix a signé. Le contrat est avec Quentrel."
    entities = [
        _at(later, "Quentrel Zorbix", "PERSON", 0),
        _at(later, "Quentrel", "PERSON", later.rfind("Quentrel")),
    ]
    written2, _ = _cli(tmp_path, db, "later.txt", later, entities, ["confirm"], [])
    assert written2 is not None, "PRE: later run"
    full_written, lone_written = _replacements(written2, later, _spans(entities))
    assert lone_written == "Quorix", "PRE: the lone name again"
    assert full_written.startswith("Quorix "), full_written  # expected failure
    stored = _stored(db, "Quentrel Zorbix", "PERSON")
    assert stored is not None and stored[3] == full_written and stored[4] == "Quorix"


@pytest.mark.parametrize("case", ["offered_first", "offered_last"])
def test_cli_generation_never_takes_a_beginning_or_ending(
    tmp_path: Path, case: str
) -> None:
    """T41 (AC3, AC19; PO A1; core): after "Xantor Quovan Velmar" is stored
    for "Quentrel Zorbalia" (parts "Xantor Quovan" + "Velmar"), the library is
    made to offer "Xantor" (a first name) or "Velmar" (a last name) first for
    a new name, through ``secrets.choice``, so its own check still runs: the
    written name neither starts with "Xantor " nor ends with " Velmar", and
    its stored row matches the file."""
    db = _new_db(tmp_path)
    first_doc = "Quentrel Zorbalia a signé le contrat."
    result = DocumentProcessor(db_path=db, passphrase=PASSPHRASE).finalize_document(
        first_doc,
        [_at(first_doc, QZ, "PERSON", 0)],
        str(tmp_path / "one.txt"),
        custom_pseudonyms={(QZ, "PERSON"): "Xantor Quovan Velmar"},
    )
    assert result.success, "PRE: custom stored"
    assert _stored(db, QZ, "PERSON") == (
        QZ,
        "Quentrel",
        "Zorbalia",
        "Xantor Quovan Velmar",
        "Xantor Quovan",
        "Velmar",
    ), "PRE: stored with its parts"
    offered, method, real = (
        ("Xantor", "_select_first_name", "Quentrix")
        if case == "offered_first"
        else ("Velmar", "_select_last_name", "Zorbix")
    )
    original = getattr(library_module.LibraryBasedPseudonymManager, method)
    real_choice = library_module.secrets.choice

    def offering(self: Any, *args: Any, **kwargs: Any) -> Any:
        if real not in args and real not in kwargs.values():
            return original(self, *args, **kwargs)
        calls = {"n": 0}

        def choice(seq: Any) -> Any:
            calls["n"] += 1
            return offered if calls["n"] == 1 else real_choice(seq)

        with patch.object(library_module.secrets, "choice", choice):
            return original(self, *args, **kwargs)

    later = "Quentrix Zorbix a signé le contrat."
    output = tmp_path / "two.txt"
    with patch.object(library_module.LibraryBasedPseudonymManager, method, offering):
        result = DocumentProcessor(db_path=db, passphrase=PASSPHRASE).finalize_document(
            later, [_at(later, "Quentrix Zorbix", "PERSON", 0)], str(output)
        )
    assert result.success, "PRE: later document"
    written = _replacements(
        output.read_text(encoding="utf-8"), later, [(0, len("Quentrix Zorbix"))]
    )[0]
    if case == "offered_first":
        assert not written.startswith("Xantor "), written  # expected failure
    else:
        assert not written.endswith(" Velmar"), written  # expected failure
    stored = _stored(db, "Quentrix Zorbix", "PERSON")
    assert stored is not None and stored[3] == written
