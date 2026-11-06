"""Story 11.2: custom pseudonyms refused at finalization, in the command line
and in ``finalize_document`` (T1-T5, T7, T20).

Two names of one document share a real first name, « Xantor », and each
gets a custom pseudonym: « Dravin Brontel » for « Xantor Velmar » and
« Dravin Le Vorlan » (or « Dravin de La Vorlan ») for « Xantor Quentrel ».
The review splits the particle surname after « Dravin », because the other
custom pseudonym already gives « Xantor » the part « Dravin » (MW-001 (b)).
Finalization used to split it with the stored parts only, as « Dravin Le » +
« Vorlan », so « Dravin Brontel » then broke Q-D and nothing was written; in
the other order, the second custom pseudonym was refused during review.

CL = ``DocumentProcessor.process_document`` with its interactive review and
CO = ``DocumentProcessor.finalize_document`` (the desktop's finalization
path), through the harness of Story 10.16's
``test_custom_pseudonym_fixes_cli.py``. The case names ``velmar_first`` and
``quentrel_first`` say whose custom pseudonym is set first (CL) or comes
first in the ``custom_pseudonyms`` dict (CO). The command line reviews the
names in the order of the document, so its ``quentrel_first`` case names
« Xantor Quentrel » first in the document.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``, so a strict expected-failure marker never absorbs one.
The first ``assert`` after them is the expected failure on the unfixed code
(``# expected failure``). The finalization error is Lionel's approved text,
byte for byte. Invented names and main-corpus words only. No Qt.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gdpr_pseudonymizer.core.custom_pseudonym import (
    CustomPseudonymRefusal,
    check_custom_pseudonym,
)
from gdpr_pseudonymizer.data.database import open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from tests.unit.test_custom_pseudonym_fixes_cli import (
    PASSPHRASE,
    _at,
    _cli,
    _finalize,
    _new_db,
    _replacements,
    _row_count,
    _spans,
    _stored,
    pre,
)

# Lionel's approved finalization error for a part changed in the database
# (Story 10.11, Q-A); unchanged by Story 11.2 (AC7).
PART_CHANGED = (
    "CustomPseudonymError: A pseudonym you chose can no longer be used: "
    "the first or last name now has a different part in the mapping "
    "database. Nothing was written."
)

VELMAR = "Xantor Velmar"
QUENTREL = "Xantor Quentrel"
PLAIN = "Dravin Brontel"
PARTICLE = "Dravin Le Vorlan"
DOUBLE = "Dravin de La Vorlan"

DOC = (
    "Présents : Xantor Velmar et Xantor Quentrel. " "Xantor Velmar a signé le contrat."
)
# The same words, « Xantor Quentrel » named first (the command line reviews
# the names in the order of the document).
DOC_QUENTREL_FIRST = (
    "Présents : Xantor Quentrel et Xantor Velmar. " "Xantor Velmar a signé le contrat."
)
ONE_DOC = "Xantor Velmar a signé le contrat."

ORDERS = ["velmar_first", "quentrel_first"]


def _entities(text: str) -> list[DetectedEntity]:
    """Both places of « Xantor Velmar » and the place of « Xantor
    Quentrel »."""
    first = text.find(VELMAR)
    return [
        _at(text, VELMAR, "PERSON", first),
        _at(text, QUENTREL, "PERSON"),
        _at(text, VELMAR, "PERSON", text.find(VELMAR, first + 1)),
    ]


def _customs(order: str, particle: str) -> dict[tuple[str, str], str]:
    """The two custom pseudonyms, in the dict order the case names."""
    pairs = [((VELMAR, "PERSON"), PLAIN), ((QUENTREL, "PERSON"), particle)]
    if order == "quentrel_first":
        pairs.reverse()
    return dict(pairs)


def _places(written: str, text: str, entities: list[DetectedEntity]) -> list[str]:
    """What is written at each place, in the order of ``entities``."""
    spans = _spans(entities)
    replaced = _replacements(written, text, spans)
    return [replaced[spans.index((e.start_pos, e.end_pos))] for e in entities]


def _rows(db: str) -> list[Entity]:
    with open_database(db, PASSPHRASE) as session:
        return SQLiteMappingRepository(session).find_all()


# ---------------------------------------------------------------------------
# Marked: the review's custom pseudonyms are written (T1, T2, T3, T20)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("order", ORDERS)
def test_cli_shared_first_name_particle_surname_written(
    tmp_path: Path, order: str
) -> None:
    """T1 (AC1): [C] « Dravin Brontel » on « Xantor Velmar » and [C]
    « Dravin Le Vorlan » on « Xantor Quentrel », in either order: no warning,
    both written at their places, stored with the parts the review used."""
    db = _new_db(tmp_path)
    if order == "velmar_first":
        text, typed, shown = DOC, [PLAIN, PARTICLE], [VELMAR, QUENTREL]
    else:
        text, typed = DOC_QUENTREL_FIRST, [PARTICLE, PLAIN]
        shown = [QUENTREL, VELMAR]
    entities = _entities(text)
    # The happy path is two [C]; the confirms after them finish the run
    # when a set is refused and its group is shown again.
    keys = ["change_pseudonym", "change_pseudonym", "confirm", "confirm", "confirm"]
    run = _cli(tmp_path, db, "doc.txt", text, entities, keys, typed)
    pre(run.order == shown, f"the groups shown in order: {run.order!r}")
    assert run.warnings == [], run.warnings  # expected failure (quentrel_first)
    assert run.result.success, run.result.error_message  # expected (velmar_first)
    if run.written is None:
        pytest.fail("PRE: written")
    assert _places(run.written, text, entities) == [PLAIN, PARTICLE, PLAIN]
    assert _stored(db, VELMAR, "PERSON") == (
        VELMAR,
        "Xantor",
        "Velmar",
        PLAIN,
        "Dravin",
        "Brontel",
    )
    assert _stored(db, QUENTREL, "PERSON") == (
        QUENTREL,
        "Xantor",
        "Quentrel",
        PARTICLE,
        "Dravin",
        "Le Vorlan",
    )


@pytest.mark.parametrize("order", ORDERS)
def test_finalization_accepts_what_the_review_accepted(
    tmp_path: Path, order: str
) -> None:
    """T2 (AC1): ``finalize_document`` with « Dravin Brontel » and « Dravin
    Le Vorlan » on an empty database writes both and stores the parts the
    review used."""
    db = _new_db(tmp_path)
    entities = _entities(DOC)
    output = tmp_path / "out.txt"
    result = _finalize(db, DOC, entities, output, _customs(order, PARTICLE))
    assert result.success, result.error_message  # expected failure
    written = output.read_text(encoding="utf-8")
    assert _places(written, DOC, entities) == [PLAIN, PARTICLE, PLAIN]
    assert _stored(db, VELMAR, "PERSON") == (
        VELMAR,
        "Xantor",
        "Velmar",
        PLAIN,
        "Dravin",
        "Brontel",
    )
    assert _stored(db, QUENTREL, "PERSON") == (
        QUENTREL,
        "Xantor",
        "Quentrel",
        PARTICLE,
        "Dravin",
        "Le Vorlan",
    )


def test_check_accepts_plain_pseudonym_after_particle_surname() -> None:
    """T3 (AC1): with « Dravin Le Vorlan » already set for « Xantor
    Quentrel », « Dravin Brontel » for « Xantor Velmar » is accepted."""
    refusal = check_custom_pseudonym(
        [],
        VELMAR,
        "PERSON",
        PLAIN,
        DOC,
        {(QUENTREL, "PERSON"): PARTICLE},
    )
    assert refusal is None, refusal  # expected failure


@pytest.mark.parametrize("order", ORDERS)
def test_finalization_accepts_double_particle_next_to_shared_first_name(
    tmp_path: Path, order: str
) -> None:
    """T20 (AC1): ``finalize_document`` with « Dravin Brontel » and « Dravin
    de La Vorlan » writes both and stores (Dravin, Brontel) and (Dravin,
    de La Vorlan). The order change alone fixes it, not the particle rule
    alone."""
    db = _new_db(tmp_path)
    entities = _entities(DOC)
    output = tmp_path / "out.txt"
    result = _finalize(db, DOC, entities, output, _customs(order, DOUBLE))
    assert result.success, result.error_message  # expected failure
    written = output.read_text(encoding="utf-8")
    assert _places(written, DOC, entities) == [PLAIN, DOUBLE, PLAIN]
    velmar = _stored(db, VELMAR, "PERSON")
    assert velmar is not None and velmar[4:] == ("Dravin", "Brontel"), velmar
    quentrel = _stored(db, QUENTREL, "PERSON")
    assert quentrel is not None and quentrel[3:] == (
        DOUBLE,
        "Dravin",
        "de La Vorlan",
    ), quentrel


# ---------------------------------------------------------------------------
# Controls: true conflicts and stored parts still refused (T4, T5, T7)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("order", ORDERS)
@pytest.mark.parametrize(
    "case, velmar_custom, quentrel_custom",
    [
        pytest.param("different_first", PLAIN, "Morvane Vorlan", id="different_first"),
        pytest.param(
            "two_word_first",
            "Dravin Telvo Brontel",
            "Dravin Nalvo Vorlan",
            id="two_word_first",
        ),
    ],
)
def test_first_name_conflict_still_refused(
    case: str, velmar_custom: str, quentrel_custom: str, order: str
) -> None:
    """T4 (AC2, a control): two different first-name parts for « Xantor »:
    the second set is refused (Q-D), and the part required is the first
    one's first-name part."""
    if order == "velmar_first":
        first_name, first_custom = VELMAR, velmar_custom
        second_name, second_custom = QUENTREL, quentrel_custom
    else:
        first_name, first_custom = QUENTREL, quentrel_custom
        second_name, second_custom = VELMAR, velmar_custom
    pre(
        check_custom_pseudonym([], first_name, "PERSON", first_custom, DOC, {}) is None,
        "the first set is accepted",
    )
    refusal = check_custom_pseudonym(
        [],
        second_name,
        "PERSON",
        second_custom,
        DOC,
        {(first_name, "PERSON"): first_custom},
    )
    assert refusal is not None
    assert refusal.reason == CustomPseudonymRefusal.PART_BOUND, refusal
    assert refusal.required == first_custom.rsplit(" ", 1)[0], refusal


def test_stored_part_still_required(tmp_path: Path) -> None:
    """T5 (AC2, a control): after « Xantor Velmar » → « Dravin Brontel » is
    stored, « Morvane Vorlan » for « Xantor Quentrel » is refused (required
    « Dravin »), and « Dravin Le Vorlan » is written and stored (Dravin,
    Le Vorlan)."""
    db = _new_db(tmp_path)
    first = _finalize(
        db,
        ONE_DOC,
        [_at(ONE_DOC, VELMAR, "PERSON", 0)],
        tmp_path / "first.txt",
        {(VELMAR, "PERSON"): PLAIN},
    )
    pre(
        first.success
        and _stored(db, VELMAR, "PERSON")
        == (VELMAR, "Xantor", "Velmar", PLAIN, "Dravin", "Brontel"),
        "« Dravin Brontel » stored with its parts",
    )
    text = "Xantor Quentrel a signé le contrat."
    refusal = check_custom_pseudonym(
        _rows(db), QUENTREL, "PERSON", "Morvane Vorlan", text, {}
    )
    assert refusal is not None
    assert refusal.reason == CustomPseudonymRefusal.PART_BOUND, refusal
    assert refusal.required == "Dravin", refusal
    output = tmp_path / "out.txt"
    result = _finalize(
        db,
        text,
        [_at(text, QUENTREL, "PERSON", 0)],
        output,
        {(QUENTREL, "PERSON"): PARTICLE},
    )
    assert result.success, result.error_message
    assert output.read_text(encoding="utf-8") == f"{PARTICLE} a signé le contrat."
    assert _stored(db, QUENTREL, "PERSON") == (
        QUENTREL,
        "Xantor",
        "Quentrel",
        PARTICLE,
        "Dravin",
        "Le Vorlan",
    )


def test_part_changed_in_database_keeps_its_message(tmp_path: Path) -> None:
    """T7 (AC7, a control): the review accepts « Dravin Brontel » for
    « Xantor Velmar »; before finalization another run stores « Xantor
    Brindel » → « Morvane Vorlan »; finalization then fails with Lionel's
    database-part text, byte for byte, and nothing is written."""
    db = _new_db(tmp_path)
    entities = _entities(DOC)
    pre(
        check_custom_pseudonym(_rows(db), VELMAR, "PERSON", PLAIN, DOC, {}) is None,
        "the review accepts « Dravin Brontel »",
    )
    with open_database(db, PASSPHRASE) as session:
        SQLiteMappingRepository(session).save(
            Entity(
                entity_type="PERSON",
                full_name="Xantor Brindel",
                first_name="Xantor",
                last_name="Brindel",
                pseudonym_full="Morvane Vorlan",
                pseudonym_first="Morvane",
                pseudonym_last="Vorlan",
                theme="neutral",
            )
        )
    pre(_row_count(db) == 1, "the other run's row stored")
    output = tmp_path / "out.txt"
    result = _finalize(db, DOC, entities, output, {(VELMAR, "PERSON"): PLAIN})
    assert not result.success
    assert result.error_message == PART_CHANGED, result.error_message
    assert not output.exists() or output.read_text(encoding="utf-8") == ""
    assert _row_count(db) == 1
