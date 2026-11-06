"""Story 11.2: a particle surname split from its surname (T6, T14-T19).

Lionel's D1 (2026-11-05, "2: widen the rule (Recommended)"): in a custom
pseudonym of three or more words, a linking word of the Q-I list just before
the last word stays with the last name, so « Dravin Le Vorlan » is
« Dravin » + « Le Vorlan ». Before, Q4/Q-G split it at the last space,
« Dravin Le » + « Vorlan », and a later name with the same real first name
took « Dravin Le » as its first name. Otherwise Q4/Q-G apply as before, a
part a real name already has still comes first (MW-001 (b)), and rows
already stored keep their stored split.

``finalize_document`` on databases made by ``_new_db``, and
``split_custom_pseudonym`` or ``check_custom_pseudonym`` directly, with the
helpers of Story 10.16's ``test_custom_pseudonym_fixes_cli.py``.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``, so a strict expected-failure marker never absorbs one.
The first ``assert`` after them is the expected failure on the unfixed code
(``# expected failure``). Invented names and main-corpus words only. No Qt.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import gdpr_pseudonymizer.core.custom_pseudonym as custom_module
from gdpr_pseudonymizer.core.custom_pseudonym import (
    CustomPseudonymRefusal,
    check_custom_pseudonym,
    split_custom_pseudonym,
)
from gdpr_pseudonymizer.data.database import open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from tests.unit.test_custom_pseudonym_fixes_cli import (
    PASSPHRASE,
    _at,
    _finalize,
    _new_db,
    _replacements,
    _stored,
    pre,
)

PARTICLE_SPLIT = pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 11.2 tests first: particle surname split from its surname",
)

ZQ = "Zorbal Quentrix"
PARTICLE = "Dravin Le Vorlan"
ZQ_DOC = "Zorbal Quentrix a signé le contrat."


def _store_custom(tmp_path: Path, db: str, custom: str) -> None:
    """« Zorbal Quentrix » finalized with ``custom`` (PRE: stored)."""
    result = _finalize(
        db,
        ZQ_DOC,
        [_at(ZQ_DOC, ZQ, "PERSON", 0)],
        tmp_path / "first.txt",
        {(ZQ, "PERSON"): custom},
    )
    pre(result.success, f"{custom!r} finalized: {result.error_message!r}")
    stored = _stored(db, ZQ, "PERSON")
    pre(stored is not None and stored[3] == custom, f"{custom!r} stored")


def _rows(db: str) -> list[Entity]:
    with open_database(db, PASSPHRASE) as session:
        return SQLiteMappingRepository(session).find_all()


def _save(
    db: str,
    full: str,
    first: str,
    last: str,
    pseudonym: str,
    pseudonym_first: str,
    pseudonym_last: str,
    theme: str,
) -> None:
    """A stored person row with fixed parts, as an earlier version wrote."""
    with open_database(db, PASSPHRASE) as session:
        SQLiteMappingRepository(session).save(
            Entity(
                entity_type="PERSON",
                full_name=full,
                first_name=first,
                last_name=last,
                pseudonym_full=pseudonym,
                pseudonym_first=pseudonym_first,
                pseudonym_last=pseudonym_last,
                theme=theme,
            )
        )


def _lone_first_name(tmp_path: Path, db: str) -> str:
    """What a later lone « Zorbal » is written as."""
    text = "Zorbal a signé."
    output = tmp_path / "lone.txt"
    result = _finalize(db, text, [_at(text, "Zorbal", "PERSON", 0)], output)
    pre(result.success, f"lone « Zorbal »: {result.error_message!r}")
    (written,) = _replacements(
        output.read_text(encoding="utf-8"), text, [(0, len("Zorbal"))]
    )
    return written


# ---------------------------------------------------------------------------
# Marked: the linking word stays with the last name (T6, T14, T15, T16)
# ---------------------------------------------------------------------------


@PARTICLE_SPLIT
@pytest.mark.parametrize(
    "custom, parts",
    [
        pytest.param(PARTICLE, ("Dravin", "Le Vorlan"), id="le"),
        pytest.param("Dravin De Vorlan", ("Dravin", "De Vorlan"), id="de"),
        pytest.param("Dravin du Vorlan", ("Dravin", "du Vorlan"), id="du_lowercase"),
        pytest.param("DRAVIN LE VORLAN", ("DRAVIN", "LE VORLAN"), id="all_capitals"),
        pytest.param(
            "Dravin Telvo Le Vorlan",
            ("Dravin Telvo", "Le Vorlan"),
            id="after_two_first_words",
        ),
    ],
)
def test_particle_surname_stays_with_last_name(
    tmp_path: Path, custom: str, parts: tuple[str, str]
) -> None:
    """T6 (AC5): a custom pseudonym for « Zorbal Quentrix » whose word just
    before the last word is a linking word is stored with that word in its
    last-name part, each part spelt as typed."""
    db = _new_db(tmp_path)
    _store_custom(tmp_path, db, custom)
    stored = _stored(db, ZQ, "PERSON")
    if stored is None:
        pytest.fail("PRE: stored")
    assert stored[4:] == parts, stored  # expected failure


@PARTICLE_SPLIT
def test_later_full_name_takes_first_part_without_particle(tmp_path: Path) -> None:
    """T14 (AC5): after « Dravin Le Vorlan » is stored for « Zorbal
    Quentrix », a later « Zorbal Brindel » (generated) takes « Dravin » as
    its first-name part, and its written pseudonym is « Dravin » followed by
    its own last-name part. (The library may draw a two-word last name, so
    the check is on the parts, not on the word after « Dravin ».)"""
    db = _new_db(tmp_path)
    _store_custom(tmp_path, db, PARTICLE)
    text = "Zorbal Brindel a signé le contrat."
    output = tmp_path / "later.txt"
    result = _finalize(db, text, [_at(text, "Zorbal Brindel", "PERSON", 0)], output)
    pre(result.success, f"later document: {result.error_message!r}")
    (written,) = _replacements(
        output.read_text(encoding="utf-8"), text, [(0, len("Zorbal Brindel"))]
    )
    stored = _stored(db, "Zorbal Brindel", "PERSON")
    if stored is None:
        pytest.fail("PRE: « Zorbal Brindel » stored")
    pre(stored[3] == written, "the stored pseudonym is the one written")
    assert stored[4] == "Dravin", stored  # expected failure
    assert stored[5] and written == f"Dravin {stored[5]}", written


@PARTICLE_SPLIT
def test_later_lone_first_name_takes_first_part(tmp_path: Path) -> None:
    """T15 (AC5): after « Dravin Le Vorlan » is stored for « Zorbal
    Quentrix », a later lone « Zorbal » is written « Dravin »."""
    db = _new_db(tmp_path)
    _store_custom(tmp_path, db, PARTICLE)
    written = _lone_first_name(tmp_path, db)
    assert written == "Dravin", written  # expected failure


@PARTICLE_SPLIT
@pytest.mark.parametrize("case", ["accepted", "refused"])
def test_later_custom_must_start_with_first_part(tmp_path: Path, case: str) -> None:
    """T16 (AC5): after « Dravin Le Vorlan » is stored for « Zorbal
    Quentrix », a custom pseudonym for « Zorbal Velmar » must start with
    « Dravin »: « Dravin Brontel » is accepted, « Morvane Brontel » is
    refused with « Dravin » required."""
    db = _new_db(tmp_path)
    _store_custom(tmp_path, db, PARTICLE)
    text = "Zorbal Velmar a signé le contrat."
    custom = "Dravin Brontel" if case == "accepted" else "Morvane Brontel"
    refusal = check_custom_pseudonym(
        _rows(db), "Zorbal Velmar", "PERSON", custom, text, {}
    )
    if case == "accepted":
        assert refusal is None, refusal  # expected failure
    else:
        assert refusal is not None
        assert refusal.reason == CustomPseudonymRefusal.PART_BOUND, refusal
        assert refusal.required == "Dravin", refusal  # expected failure


# ---------------------------------------------------------------------------
# Controls: the split is unchanged elsewhere (T17, T18, T19)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "custom, parts",
    [
        pytest.param(
            "Dravin Telvo Brontel", ("Dravin Telvo", "Brontel"), id="two_given_names"
        ),
        pytest.param(
            "Dravin De Vellion", ("Dravin", "De Vellion"), id="library_name_linking"
        ),
        pytest.param(
            "Dravin Quor Vellion",
            ("Dravin", "Quor Vellion"),
            id="library_name_no_linking",
        ),
        pytest.param(
            "Le Vorlan Dravin", ("Le Vorlan", "Dravin"), id="linking_word_first"
        ),
        pytest.param("Le Vorlan", ("Le", "Vorlan"), id="two_words"),
        pytest.param(
            "Dravin Le Vorlan Brontel",
            ("Dravin Le Vorlan", "Brontel"),
            id="linking_word_inside",
        ),
    ],
)
def test_split_unchanged_without_particle_before_last_word(
    monkeypatch: pytest.MonkeyPatch, custom: str, parts: tuple[str, str]
) -> None:
    """T17 (AC5, a control): without a linking word just before the last
    word, or with fewer than three words, the split is Q4/Q-G's: at the last
    space, one of the library's two-word last names kept whole (the
    library's set is replaced by the invented « De Vellion » and « Quor
    Vellion », as T37 does)."""
    monkeypatch.setattr(
        custom_module,
        "library_two_word_last_names",
        lambda: ("de vellion", "quor vellion"),
        raising=False,
    )
    assert split_custom_pseudonym(custom, "PERSON") == parts


def test_stored_split_kept(tmp_path: Path) -> None:
    """T18 (AC5, a control): a row stored as 2.3.0 stored it, « Zorbal
    Quentrix » → « Dravin Le Vorlan » with the parts « Dravin Le » +
    « Vorlan », keeps its split: for « Zorbal Velmar », « Dravin Brontel »
    is refused (« Dravin Le » required) and « Dravin Le Brontel » accepted;
    a lone « Zorbal » is still written « Dravin Le »."""
    db = _new_db(tmp_path)
    _save(db, ZQ, "Zorbal", "Quentrix", PARTICLE, "Dravin Le", "Vorlan", "custom")
    text = "Zorbal Velmar a signé le contrat."
    refusal = check_custom_pseudonym(
        _rows(db), "Zorbal Velmar", "PERSON", "Dravin Brontel", text, {}
    )
    assert refusal is not None
    assert refusal.reason == CustomPseudonymRefusal.PART_BOUND, refusal
    assert refusal.required == "Dravin Le", refusal
    assert (
        check_custom_pseudonym(
            _rows(db), "Zorbal Velmar", "PERSON", "Dravin Le Brontel", text, {}
        )
        is None
    )
    assert _lone_first_name(tmp_path, db) == "Dravin Le"


def test_stored_last_part_comes_first(tmp_path: Path) -> None:
    """T19 (AC5, a control; MW-001 (b)): with « Xantor Brindel » →
    « Morvane Vorlan » stored (parts Morvane, Vorlan), « Dravin Le Vorlan »
    for « Zorbal Brindel » is written and stored as « Dravin Le » +
    « Vorlan »: the part the real last name already has comes first."""
    db = _new_db(tmp_path)
    _save(
        db,
        "Xantor Brindel",
        "Xantor",
        "Brindel",
        "Morvane Vorlan",
        "Morvane",
        "Vorlan",
        "neutral",
    )
    text = "Zorbal Brindel a signé le contrat."
    output = tmp_path / "out.txt"
    result = _finalize(
        db,
        text,
        [_at(text, "Zorbal Brindel", "PERSON", 0)],
        output,
        {("Zorbal Brindel", "PERSON"): PARTICLE},
    )
    assert result.success, result.error_message
    assert output.read_text(encoding="utf-8") == f"{PARTICLE} a signé le contrat."
    assert _stored(db, "Zorbal Brindel", "PERSON") == (
        "Zorbal Brindel",
        "Zorbal",
        "Brindel",
        PARTICLE,
        "Dravin Le",
        "Vorlan",
    )
