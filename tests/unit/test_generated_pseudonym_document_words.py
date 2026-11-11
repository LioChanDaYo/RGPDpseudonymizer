"""Story 11.6: a pseudonym the library draws is never a word of the document.

Written by the BMAD dev agent (Claude). Each test drives the real
``DocumentProcessor`` paths on a real database; detection is replaced by a
stand-in that finds the names given (``_found``, ``_detection``), or by the
entities given (``_cli``). The library's draw is forced (``_forced``): a word
is put at the head of its own list, and the first ``secrets.choice`` that
meets it there returns it; every other choice is real. The "offered" words
are cleared when ``_resolve_pseudonyms`` starts, so the forced word is the
first draw at write time, whatever a review's preview drew before.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``, so a strict ``xfail(raises=AssertionError)`` never absorbs one.
The first ``assert`` after them is the expected failure on the unfixed code
(``# expected failure``). Invented names and main-corpus words only. No
spaCy model, no Qt.
"""

from __future__ import annotations

import json
import secrets
import unicodedata
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import gdpr_pseudonymizer.pseudonym.library_manager as library_module
from gdpr_pseudonymizer.cli.commands.batch import _process_single_document_worker
from gdpr_pseudonymizer.core.custom_pseudonym import check_custom_pseudonym, fold
from gdpr_pseudonymizer.core.document_processor import (
    DocumentProcessor,
    ProcessingResult,
)
from gdpr_pseudonymizer.data.database import open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.resources import PSEUDONYMS_DIR
from gdpr_pseudonymizer.utils.text_form import word_pattern
from tests.unit.test_custom_pseudonym_fixes_cli import (
    PASSPHRASE,
    _cli,
    _new_db,
    _replacements,
    _row_count,
    _stored,
    _words,
    pre,
)
from tests.unit.test_parallel_saved_pseudonym import (
    _detection,
    _found,
    _output,
    _process,
    _settings,  # noqa: F401 (autouse: no settings file read or written)
    _spans,
)

PERSON, ORG, LOCATION = "PERSON", "ORG", "LOCATION"
ZQ = "Zorbal Quentrix"

# The own-word document (T1): each name's own words head their own lists
OWN_DOC = "Zorbal Quentrix a signé le contrat de Zorbtech à Zorbaville."
OWN_NAMES = [(ZQ, PERSON), ("Zorbtech", ORG), ("Zorbaville", LOCATION)]
OWN_FRONT = {
    "first": ["Zorbal"],
    "last": ["Quentrix"],
    "place": ["Zorbaville"],
    "org": ["Zorbtech"],
}
OWN_WORDS = {"zorbal", "quentrix", "zorbtech", "zorbaville"}

# Lionel-approved texts are not involved: this is today's exhaustion error
OUT_OF_LAST_NAMES = (
    "RuntimeError: Unable to find unique last name component after 100 "
    "attempts. Library may be exhausted."
)

_WORD = word_pattern()


# ---------------------------------------------------------------------------
# The forced draw
# ---------------------------------------------------------------------------


class _Offers:
    """The library's ``secrets``: ``choice(seq)`` returns ``seq[0]`` when it
    is a forced word not yet offered, else the real ``secrets.choice``."""

    def __init__(self, words: set[str]) -> None:
        self.words = words
        self.offered: set[str] = set()
        self.n = 0

    def choice(self, seq: Sequence[str]) -> str:
        if seq and seq[0] in self.words and seq[0] not in self.offered:
            self.offered.add(seq[0])
            self.n += 1
            return seq[0]
        return secrets.choice(seq)


def _to_head(values: list[str], word: str, insert: bool) -> bool:
    """Move ``word`` to the head of ``values`` (inserted if absent and
    ``insert``). Whether it now heads the list."""
    if word in values:
        values.remove(word)
    elif not insert:
        return False
    values.insert(0, word)
    return True


@contextmanager
def _forced(
    front: Mapping[str, Sequence[str]],
    last_names: Sequence[str] | None = None,
    places: Sequence[str] | None = None,
    insert: bool = True,
) -> Iterator[_Offers]:
    """The library loads as usual, then each word of ``front`` heads only its
    own list: ``"first"`` every non-empty gender list of first names,
    ``"last"`` the last names, ``"place"`` the places' first category,
    ``"org"`` the organisations' first category. ``last_names`` and
    ``places`` replace those lists whole first (after the library's own
    checks). ``insert=False`` moves a word only into a list that holds it. A
    forced word that heads a list of another role leaves its head. Yields the
    offers (``.n``)."""
    words = {word for values in front.values() for word in values}
    offers = _Offers(words)
    original_load = library_module.LibraryBasedPseudonymManager.load_library
    original_resolve = DocumentProcessor._resolve_pseudonyms

    def load(self: Any, theme: str) -> None:
        original_load(self, theme)
        if theme == "neutral_id":
            return
        if last_names is not None:
            self.last_names = list(last_names)
        if places is not None:
            for category in self.locations:
                self.locations[category] = []
            self.locations["cities"] = list(places)
        own: dict[str, list[list[str]]] = {
            "first": [
                self.first_names[gender]
                for gender in ("male", "female", "neutral")
                if self.first_names[gender] or not insert
            ],
            "last": [self.last_names],
            "place": [self.locations["cities"]],
            "org": [self.organizations["companies"]],
        }
        headed: set[int] = set()
        for role, role_words in front.items():
            for word in role_words:
                for values in own[role]:
                    if _to_head(values, word, insert):
                        headed.add(id(values))
        every = [
            *(self.first_names[gender] for gender in ("male", "female", "neutral")),
            self.last_names,
            *self.locations.values(),
            *self.organizations.values(),
        ]
        for values in every:
            if id(values) not in headed and values and values[0] in words:
                values.append(values.pop(0))

    def resolve(self: Any, *args: Any, **kwargs: Any) -> Any:
        offers.offered.clear()
        return original_resolve(self, *args, **kwargs)

    with (
        patch.object(library_module.LibraryBasedPseudonymManager, "load_library", load),
        patch.object(DocumentProcessor, "_resolve_pseudonyms", resolve),
        patch.object(library_module, "secrets", offers),
    ):
        yield offers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finalize(
    db: str,
    text: str,
    names: list[tuple[str, str]],
    output: Path,
    theme: str = "neutral",
) -> ProcessingResult:
    """``finalize_document``: the desktop app's reviews."""
    return DocumentProcessor(
        db_path=db, passphrase=PASSPHRASE, theme=theme
    ).finalize_document(text, _found(text, names), str(output))


def _written_at(output: Path, text: str, names: list[tuple[str, str]]) -> list[str]:
    """The string written at each place of ``names``."""
    return _replacements(output.read_text(encoding="utf-8"), text, _spans(text, names))


def _word_set(text: str) -> set[str]:
    """The folded words of ``text`` as ``_WORD`` cuts them (a hyphen cuts)."""
    return {fold(word) for word in _WORD.findall(text)}


def _library(theme: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (PSEUDONYMS_DIR / f"{theme}.json").read_text(encoding="utf-8")
    )
    return data


def _shared_first_name() -> str:
    """V (T21, T22): the first first name of the default library (male, then
    female) whose folded form is also one of its last names, else its first
    male first name. Read from the file, never written in a test."""
    library = _library("neutral")
    last = {fold(value) for value in library["last_names"]}
    for gender in ("male", "female"):
        for value in library["first_names"][gender]:
            if fold(value) in last:
                return str(value)
    return str(library["first_names"]["male"][0])


def _accented_first_name() -> tuple[str, str]:
    """A and A0 (T22): the first first name of the default library (male,
    then female) with an accent, and its form without accents."""
    library = _library("neutral")
    for gender in ("male", "female"):
        for value in library["first_names"][gender]:
            decomposed = unicodedata.normalize("NFKD", value)
            if decomposed != value:
                plain = "".join(c for c in decomposed if not unicodedata.combining(c))
                return str(value), plain
    pytest.fail("PRE: an accented first name in the default library")


def _save_person(
    db: str, name: str, first: str, last: str, pseudo_first: str, pseudo_last: str
) -> None:
    """A saved row of the default library, with its parts."""
    with open_database(db, PASSPHRASE) as session:
        SQLiteMappingRepository(session).save(
            Entity(
                entity_type=PERSON,
                first_name=first,
                last_name=last,
                full_name=name,
                pseudonym_first=pseudo_first,
                pseudonym_last=pseudo_last,
                pseudonym_full=f"{pseudo_first} {pseudo_last}",
                theme="neutral",
            )
        )


# ---------------------------------------------------------------------------
# T1: no own word, on every write path
# ---------------------------------------------------------------------------


def _own_word_written(tmp_path: Path, case: str) -> str | None:
    """The own-word document written through ``case``, forced; the written
    text, or None when the path failed."""
    db = _new_db(tmp_path)
    with _forced(OWN_FRONT) as offers:
        if case == "finalize":
            output = tmp_path / "own_out.txt"
            result = _finalize(db, OWN_DOC, OWN_NAMES, output)
            written = output.read_text(encoding="utf-8") if result.success else None
        elif case == "cli_review":
            run = _cli(
                tmp_path,
                db,
                "own.txt",
                OWN_DOC,
                _found(OWN_DOC, OWN_NAMES),
                ["confirm"] * 6,
                [],
            )
            pre(
                set(run.order) == {name for name, _ in OWN_NAMES},
                f"every group shown: {run.order!r}",
            )
            written = run.written
        elif case == "no_review":
            with _detection(OWN_NAMES):
                result = _process(db, tmp_path, "own", OWN_DOC)()
            written = _output(tmp_path, "own") if result.success else None
        elif case == "parallel_worker":
            source, output = tmp_path / "own.txt", tmp_path / "own_out.txt"
            source.write_text(OWN_DOC, encoding="utf-8")
            with _detection(OWN_NAMES):
                outcome = _process_single_document_worker(
                    (str(source), str(output), db, PASSPHRASE, "neutral", "spacy", None)
                )
            written = _output(tmp_path, "own") if outcome["success"] else None
        else:
            source, output = tmp_path / "own.csv", tmp_path / "own_out.csv"
            source.write_text(f"contrat\n{OWN_DOC}\n", encoding="utf-8")
            with _detection(OWN_NAMES):
                result = DocumentProcessor(
                    db_path=db, passphrase=PASSPHRASE
                ).process_document(str(source), str(output), skip_validation=True)
            written = _output(tmp_path, "own", ".csv") if result.success else None
    pre(offers.n > 0, "the forced words offered")
    return written


@pytest.mark.parametrize(
    "case", ["finalize", "cli_review", "no_review", "parallel_worker", "csv"]
)
def test_own_word_never_written(tmp_path: Path, case: str) -> None:
    """T1 (AC1): with each name's own word first in its own list, no path
    writes « Zorbal », « Quentrix », « Zorbtech » or « Zorbaville »."""
    written = _own_word_written(tmp_path, case)
    if written is None:
        pytest.fail(f"PRE: {case} wrote the document")
    assert not OWN_WORDS & set(_words(written)), written  # expected failure


# ---------------------------------------------------------------------------
# T2-T6: the rule
# ---------------------------------------------------------------------------


def test_other_name_of_the_document_never_drawn(tmp_path: Path) -> None:
    """T2 (AC2): « Brontel », another name sent, is never drawn as « Zorbal
    Quentrix »'s last name."""
    db = _new_db(tmp_path)
    text = "Zorbal Quentrix et Xantor Brontel ont signé le contrat."
    names = [(ZQ, PERSON), ("Xantor Brontel", PERSON)]
    output = tmp_path / "out.txt"
    with _forced({"last": ["Brontel"]}) as offers:
        result = _finalize(db, text, names, output)
    pre(offers.n > 0 and result.success, "« Brontel » offered, document written")
    written = _written_at(output, text, names)[0]
    assert written.split()[-1] != "Brontel", written  # expected failure
    stored = _stored(db, ZQ, PERSON)
    assert stored is not None and stored[5] != "Brontel", stored


def test_capitalised_word_not_detected_never_drawn(tmp_path: Path) -> None:
    """T3 (AC2): « Brontel », capitalised in the document but not detected,
    is never drawn."""
    db = _new_db(tmp_path)
    text = "Zorbal Quentrix a signé le contrat avec Maitre Brontel."
    names = [(ZQ, PERSON)]
    output = tmp_path / "out.txt"
    with _forced({"last": ["Brontel"]}) as offers:
        result = _finalize(db, text, names, output)
    pre(offers.n > 0 and result.success, "« Brontel » offered, document written")
    (written,) = _written_at(output, text, names)
    assert written.split()[-1] != "Brontel", written  # expected failure


def test_lone_name_never_gets_its_own_word(tmp_path: Path) -> None:
    """T4 (AC2): a one-word name draws a last part with no real last name
    attached; that part is never the name itself."""
    db = _new_db(tmp_path)
    text = "Quentrix a signé le contrat."
    output = tmp_path / "out.txt"
    with _forced({"last": ["Quentrix"]}) as offers:
        result = _finalize(db, text, [("Quentrix", PERSON)], output)
    pre(offers.n > 0 and result.success, "« Quentrix » offered, document written")
    written = output.read_text(encoding="utf-8")
    stored = _stored(db, "Quentrix", PERSON)
    pre(stored is not None, "the name saved")
    assert stored is not None
    assert "quentrix" not in _words(stored[3]), stored  # expected failure
    assert "quentrix" not in _words(written), written


def test_word_in_small_letters_is_kept(tmp_path: Path) -> None:
    """T5 (a control; Q-C): a word in small letters of the document is not a
    real name: « Brontel » next to « brontel » is kept."""
    db = _new_db(tmp_path)
    text = "Zorbal Quentrix a signé le contrat brontel."
    output = tmp_path / "out.txt"
    with _forced({"last": ["Brontel"]}) as offers:
        result = _finalize(db, text, [(ZQ, PERSON)], output)
    pre(offers.n > 0 and result.success, "« Brontel » offered, document written")
    stored = _stored(db, ZQ, PERSON)
    assert stored is not None and stored[5] == "Brontel", stored
    (written,) = _written_at(output, text, [(ZQ, PERSON)])
    assert written.endswith(" Brontel"), written


def test_linking_word_not_compared_alone(tmp_path: Path) -> None:
    """T6 (a control; Q-I): « Le Vellion » is kept although « Le » starts a
    sentence of the document."""
    db = _new_db(tmp_path)
    text = "Zorbal Quentrix a signé le contrat. Le contrat est signé."
    output = tmp_path / "out.txt"
    with _forced({"last": ["Le Vellion"]}) as offers:
        result = _finalize(db, text, [(ZQ, PERSON)], output)
    pre(offers.n > 0 and result.success, "« Le Vellion » offered, document written")
    stored = _stored(db, ZQ, PERSON)
    assert stored is not None and stored[5] == "Le Vellion", stored


# ---------------------------------------------------------------------------
# T7, T8: when the library runs out
# ---------------------------------------------------------------------------


def test_library_out_of_last_names(tmp_path: Path) -> None:
    """T7 (AC4): the only last name is the name's own: today's exhaustion
    error, no file, no row."""
    db = _new_db(tmp_path)
    text = "Zorbal Quentrix a signé le contrat."
    output = tmp_path / "out.txt"
    with _forced({"last": ["Quentrix"]}, last_names=["Quentrix"]) as offers:
        result = _finalize(db, text, [(ZQ, PERSON)], output)
    pre(offers.n > 0, "« Quentrix » offered")
    assert not result.success, output.read_text(encoding="utf-8")  # expected failure
    assert result.error_message == OUT_OF_LAST_NAMES, result.error_message
    assert not output.exists() or output.read_text(encoding="utf-8") == ""
    assert _row_count(db) == 0


def test_library_out_of_places(tmp_path: Path) -> None:
    """T8 (AC4): the only place is the place itself: today's fallback."""
    db = _new_db(tmp_path)
    text = "Zorbal Quentrix a signé le contrat à Zorbaville."
    output = tmp_path / "out.txt"
    with _forced({"place": ["Zorbaville"]}, places=["Zorbaville"]) as offers:
        result = _finalize(db, text, [("Zorbaville", LOCATION)], output)
    pre(offers.n > 0 and result.success, "« Zorbaville » offered, document written")
    written = output.read_text(encoding="utf-8")
    expected = "Zorbal Quentrix a signé le contrat à Location-001."
    assert written == expected, written  # expected failure


# ---------------------------------------------------------------------------
# T9-T11: what stays as it is (controls)
# ---------------------------------------------------------------------------


def test_stored_row_keeps_its_pseudonym(tmp_path: Path) -> None:
    """T9 (a control; AC5): a saved row keeps its pseudonym, even one that
    holds a word of the name (Story 11.7 handles those rows)."""
    db = _new_db(tmp_path)
    _save_person(db, ZQ, "Zorbal", "Quentrix", "Zorbal", "Brontel")
    text = "Zorbal Quentrix a signé le contrat."
    output = tmp_path / "out.txt"
    result = _finalize(db, text, [(ZQ, PERSON)], output)
    pre(result.success, "document written")
    assert output.read_text(encoding="utf-8") == "Zorbal Brontel a signé le contrat."


def test_part_kept_for_consistency_is_not_redrawn(tmp_path: Path) -> None:
    """T10 (a control; AC5, KL-008): a first part saved for « Zorbal » is kept
    for « Zorbal Mestrix » although « Xantor » is a name of the new
    document."""
    db = _new_db(tmp_path)
    first = "Zorbal Quentrix a signé le contrat."
    with _forced({"first": ["Xantor"]}) as offers:
        result = _finalize(db, first, [(ZQ, PERSON)], tmp_path / "first.txt")
    stored = _stored(db, ZQ, PERSON)
    pre(
        offers.n > 0
        and result.success
        and stored is not None
        and stored[4] == "Xantor",
        "« Zorbal Quentrix » saved with the first part « Xantor »",
    )
    text = "Zorbal Mestrix et Xantor Brontel ont signé le contrat."
    names = [("Zorbal Mestrix", PERSON), ("Xantor Brontel", PERSON)]
    result = _finalize(db, text, names, tmp_path / "second.txt")
    pre(result.success, "second document written")
    later = _stored(db, "Zorbal Mestrix", PERSON)
    assert later is not None and later[4] == "Xantor", later


def test_neutral_id_unchanged(tmp_path: Path) -> None:
    """T11 (a control; AC5): ``neutral_id`` writes its identifiers, as
    today."""
    db = _new_db(tmp_path)
    output = tmp_path / "out.txt"
    result = _finalize(db, OWN_DOC, OWN_NAMES, output, theme="neutral_id")
    pre(result.success, "document written")
    written = _written_at(output, OWN_DOC, OWN_NAMES)
    assert written == ["PER-001", "ORG-001", "LOC-001"], written


# ---------------------------------------------------------------------------
# T12-T18: every word of a drawn value, hyphen parts, the custom check
# ---------------------------------------------------------------------------


def test_drawn_organisation_word_is_a_place_of_the_document(tmp_path: Path) -> None:
    """T12 (AC3, Lionel's "widen"): a drawn « Groupe Zorbaville » is drawn
    again in a document that names Zorbaville."""
    db = _new_db(tmp_path)
    text = "Zorbtech a signé le contrat à Zorbaville."
    names = [("Zorbtech", ORG), ("Zorbaville", LOCATION)]
    output = tmp_path / "out.txt"
    with _forced({"org": ["Groupe Zorbaville"]}) as offers:
        result = _finalize(db, text, names, output)
    pre(offers.n > 0 and result.success, "offered, document written")
    written = output.read_text(encoding="utf-8")
    assert "zorbaville" not in _words(written), written  # expected failure
    stored = _stored(db, "Zorbtech", ORG)
    assert stored is not None and stored[3] != "Groupe Zorbaville", stored


def test_drawn_place_word_is_a_name_of_the_document(tmp_path: Path) -> None:
    """T13 (AC3): a drawn place « Vellionne de Quentrix » is drawn again in a
    document that names « Zorbal Quentrix »."""
    db = _new_db(tmp_path)
    text = "Zorbal Quentrix a signé le contrat à Zorbaville."
    names = [(ZQ, PERSON), ("Zorbaville", LOCATION)]
    output = tmp_path / "out.txt"
    with _forced({"place": ["Vellionne de Quentrix"]}) as offers:
        result = _finalize(db, text, names, output)
    pre(offers.n > 0 and result.success, "offered, document written")
    written = output.read_text(encoding="utf-8")
    assert "quentrix" not in _words(written), written  # expected failure
    stored = _stored(db, "Zorbaville", LOCATION)
    assert stored is not None and stored[3] != "Vellionne de Quentrix", stored


def test_custom_place_or_organisation_still_compared_whole() -> None:
    """T14 (a control; AC3, AC6): the custom-pseudonym check still compares a
    custom organisation as a whole value."""
    refusal = check_custom_pseudonym(
        [],
        "Zorbtech",
        ORG,
        "Groupe Zorbaville",
        "Zorbtech a signé le contrat à Zorbaville.",
        {},
        review_names=["Zorbaville"],
    )
    assert refusal is None, refusal


def test_linking_word_of_a_drawn_place_not_compared_alone(tmp_path: Path) -> None:
    """T15 (a control; Q-I inside a place): « Le Vellionnais » is kept
    although « Le » starts a sentence of the document."""
    db = _new_db(tmp_path)
    text = "Zorbal Quentrix a signé le contrat à Zorbaville. Le contrat est signé."
    names = [(ZQ, PERSON), ("Zorbaville", LOCATION)]
    output = tmp_path / "out.txt"
    with _forced({"place": ["Le Vellionnais"]}) as offers:
        result = _finalize(db, text, names, output)
    pre(offers.n > 0 and result.success, "offered, document written")
    assert _written_at(output, text, names)[1] == "Le Vellionnais"


def test_drawn_compound_first_name_holding_the_first_name(tmp_path: Path) -> None:
    """T16 (AC3, the orchestrator's ruling): a drawn first name
    « Xantor-Zorbal » is drawn again for « Zorbal Quentrix »."""
    db = _new_db(tmp_path)
    text = "Zorbal Quentrix a signé le contrat."
    output = tmp_path / "out.txt"
    with _forced({"first": ["Xantor-Zorbal"]}) as offers:
        result = _finalize(db, text, [(ZQ, PERSON)], output)
    pre(offers.n > 0 and result.success, "offered, document written")
    written = output.read_text(encoding="utf-8")
    assert "zorbal" not in _word_set(written), written  # expected failure
    stored = _stored(db, ZQ, PERSON)
    assert stored is not None and stored[4] != "Xantor-Zorbal", stored


def test_drawn_hyphenated_place_holding_a_name(tmp_path: Path) -> None:
    """T17 (AC3, the orchestrator's ruling): a drawn place
    « Vellionne-Quentrix » is drawn again in a document naming « Zorbal
    Quentrix »."""
    db = _new_db(tmp_path)
    text = "Zorbal Quentrix a signé le contrat à Zorbaville."
    names = [(ZQ, PERSON), ("Zorbaville", LOCATION)]
    output = tmp_path / "out.txt"
    with _forced({"place": ["Vellionne-Quentrix"]}) as offers:
        result = _finalize(db, text, names, output)
    pre(offers.n > 0 and result.success, "offered, document written")
    written = output.read_text(encoding="utf-8")
    assert "quentrix" not in _word_set(written), written  # expected failure
    stored = _stored(db, "Zorbaville", LOCATION)
    assert stored is not None and stored[3] != "Vellionne-Quentrix", stored


def test_custom_hyphenated_word_still_compared_whole() -> None:
    """T18 (a control; AC3, AC6): the custom check keeps a hyphenated word
    whole: « Xantor-Zorbal Brontel » is accepted for « Zorbal Quentrix »."""
    refusal = check_custom_pseudonym(
        [],
        ZQ,
        PERSON,
        "Xantor-Zorbal Brontel",
        "Zorbal Quentrix a signé le contrat.",
        {},
    )
    assert refusal is None, refusal


# ---------------------------------------------------------------------------
# T21, T22: two names never share a pseudonym from the lists
# ---------------------------------------------------------------------------


def test_lone_first_and_last_names_never_share_a_pseudonym(tmp_path: Path) -> None:
    """T21 (AC15): a value drawn as « Zorbal »'s first part in one document
    is never drawn as « Quentrix »'s last part in the next, so a lone
    « Zorbal » and a lone « Quentrix » are never written alike."""
    db = _new_db(tmp_path)
    shared = _shared_first_name()
    pre(shared in _library("neutral")["first_names"]["male"], "V a male first name")
    others = [
        value
        for value in _library("neutral")["last_names"]
        if fold(value) != fold(shared)
    ]
    first = "Zorbal Brontel a signé le contrat."
    with _forced({"first": [shared]}, last_names=others, insert=False) as offers:
        result = _finalize(db, first, [("Zorbal Brontel", PERSON)], tmp_path / "1.txt")
    saved = _stored(db, "Zorbal Brontel", PERSON)
    pre(
        offers.n > 0 and result.success and saved is not None and saved[4] == shared,
        "document 1 written, « Zorbal »'s first part the offered value",
    )
    assert saved is not None
    text = "Xantor Quentrix a signé le contrat. Zorbal a signé. Quentrix a signé."
    names = [("Xantor Quentrix", PERSON), ("Zorbal", PERSON), ("Quentrix", PERSON)]
    output = tmp_path / "2.txt"
    with _forced({"last": [shared]}, insert=False):
        result = _finalize(db, text, names, output)
    pre(result.success, "document 2 written")
    _, lone_first, lone_last = _written_at(output, text, names)
    assert fold(lone_first) != fold(lone_last)  # expected failure
    later = _stored(db, "Xantor Quentrix", PERSON)
    assert later is not None and fold(saved[4]) != fold(later[5] or "")


@pytest.mark.parametrize("case", ["other_role", "accent_variant"])
def test_saved_part_is_not_drawn_again(tmp_path: Path, case: str) -> None:
    """T22 (AC15, the guard): in a database used before, a first part drawn
    for « Zorbal » is never a saved last part of another name, nor a saved
    first part of another name with other accents."""
    db = _new_db(tmp_path)
    if case == "other_role":
        offered = _shared_first_name()
        _save_person(db, "Xantor Quentrix", "Xantor", "Quentrix", "Morvane", offered)
        saved_part, lone = offered, "Quentrix"
    else:
        offered, saved_part = _accented_first_name()
        pre(offered != saved_part, "A0 differs from A")
        _save_person(db, "Xantor Quentrix", "Xantor", "Quentrix", saved_part, "Morvane")
        lone = "Xantor"
    text = f"Zorbal Brontel a signé le contrat. Zorbal a signé. {lone} a signé."
    names = [("Zorbal Brontel", PERSON), ("Zorbal", PERSON), (lone, PERSON)]
    output = tmp_path / "out.txt"
    with _forced({"first": [offered]}) as offers:
        result = _finalize(db, text, names, output)
    pre(offers.n > 0 and result.success, "offered, document written")
    _, lone_zorbal, lone_other = _written_at(output, text, names)
    stored = _stored(db, "Zorbal Brontel", PERSON)
    pre(stored is not None, "« Zorbal Brontel » saved")
    assert stored is not None
    assert fold(stored[4] or "") != fold(saved_part), stored  # expected failure
    assert fold(lone_zorbal) != fold(lone_other), (lone_zorbal, lone_other)
