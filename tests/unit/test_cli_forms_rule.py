"""Story 10.21: one forms rule for names of two words or more (Lionel,
2026-11-01), in the command-line review and in ``delete-mapping`` (Ex1 CLI,
Ex2, Ex5, Ex6, Ex8, T21, K3, K4), and what must not change (Ex3, Ex4, Ex7,
Ex9, G7, K1, K2).

A name of two words or more is reached wherever its letters are written,
accents and capitals set aside, any capitals, small letters included; a name
of one word keeps 10.19's rule (accents kept but at a place written entirely
in capitals, never a place written entirely in small letters).

Written by the BMAD dev agent (Claude), before the fix. Each test drives the
real ``gdpr-pseudo process`` or ``delete-mapping`` command through
``CliRunner``, on a database made by the real ``init`` command, as Story
10.19's harness (``test_cli_capitals_forms.py``). Detection is replaced by a
fake that finds every occurrence of each (name, type) given, with its exact
capitals; the keys, the typed texts and the yes/no answers come from lists.
The assertions read the written file, the stored rows and the lines shown.

Preconditions call ``pytest.fail("PRE: ...")``, never ``assert``; the first
``assert`` after them is the expected failure on the unfixed code
(``# expected failure``). Invented names and main-corpus words only; the
combining marks T21 and K1 to K3 need are made at run time with
``unicodedata.lookup`` or ``unicodedata.normalize``: no combining mark is
written in this file. No spaCy model, no Qt.

K1 to K4 (v3.1, the first Codex review's four P0; the orchestrator's ruling,
one word count, ``name_words``): a title, or a place's preposition, is not a
word of the name; a person's « Du », « de » is.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import readchar
from rich.prompt import Confirm, Prompt
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.main import app
from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.core.mapping_key import _key_steps
from gdpr_pseudonymizer.data.database import open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.workflow import ADD_MISSED_NAME_QUESTION

PASSPHRASE = "zorbalia_pass_A_123!"
ENV = {"GDPR_PSEUDO_PASSPHRASE": PASSPHRASE}
PERSON = "PERSON"
LOCATION = "LOCATION"

ENTER = "\r"
SPACE = " "
MAX_KEYS = 60

DELETED = "deleted successfully"
NAME_LINE = "Name:       "

# A name the detector finds, so that the review opens before [A].
SEEN = "Éloria"
SEEN_TEXT = f"Signé : {SEEN}. "

EX1_TEXT = "Élorine du Prélis a signé le bail. ÉLORINE DU PRÉLIS valide."

_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

Names = Sequence[tuple[str, str]]


def _pre(condition: bool, what: str) -> None:
    """A precondition: a red failure on every leg, never an AssertionError."""
    if not condition:
        pytest.fail(f"PRE: {what}")


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No user or project settings file is read or written."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "gdpr_pseudonymizer.gui.config._config_path",
        lambda: tmp_path / ".gdpr-pseudo.yaml",
    )


@pytest.fixture
def db(tmp_path: Path) -> Path:
    """A new database, made by the real ``init`` command."""
    path = tmp_path / "mappings.db"
    result = CliRunner().invoke(
        app, ["init", "--db", str(path)], env=ENV, catch_exceptions=False
    )
    _pre(result.exit_code == 0 and path.is_file(), "init made the database")
    return path


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


class FakeDetector:
    """Finds every occurrence of each (name, type) given, with its exact
    capitals (``str.find``), and drops an occurrence that lies inside a longer
    one it found."""

    def __init__(self, names: Names) -> None:
        self.names = list(names)

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        found: list[DetectedEntity] = []
        for name, entity_type in self.names:
            start = text.find(name)
            while start != -1:
                found.append(
                    DetectedEntity(
                        text=name,
                        entity_type=entity_type,
                        start_pos=start,
                        end_pos=start + len(name),
                        confidence=0.9,
                        source="spacy",
                    )
                )
                start = text.find(name, start + 1)
        return [
            entity
            for entity in found
            if not any(
                other.start_pos <= entity.start_pos
                and entity.end_pos <= other.end_pos
                and other.end_pos - other.start_pos > entity.end_pos - entity.start_pos
                for other in found
            )
        ]


class Keys:
    """``readchar.readkey``: the keys in order, then Space."""

    def __init__(self, keys: Sequence[str]) -> None:
        self.keys = list(keys)
        self.read = 0

    def __call__(self) -> str:
        self.read += 1
        if self.read > MAX_KEYS:
            raise RuntimeError("more than 60 keys read")
        return self.keys.pop(0) if self.keys else SPACE


class Typed:
    """``Prompt.ask``: the typed texts in order."""

    def __init__(self, texts: Sequence[str]) -> None:
        self.texts = list(texts)

    def __call__(self, prompt: Any, *args: Any, **kwargs: Any) -> str:
        if not self.texts:
            raise RuntimeError("no typed text left")
        return self.texts.pop(0)


class Answers:
    """``Confirm.ask``: no to Story 10.18's question, yes otherwise."""

    def __call__(self, prompt: Any, *args: Any, **kwargs: Any) -> bool:
        return str(prompt) != ADD_MISSED_NAME_QUESTION


def _invoke(
    args: Sequence[str],
    detector: FakeDetector | None = None,
    keys: Sequence[str] = (),
    typed: Sequence[str] = (),
) -> tuple[int, str]:
    """One real ``gdpr-pseudo`` command run: its exit code and what it showed."""
    with ExitStack() as stack:
        if detector is not None:
            fake = detector
            stack.enter_context(
                patch.object(DocumentProcessor, "_get_detector", new=lambda self: fake)
            )
            stack.enter_context(
                patch.object(
                    DocumentProcessor,
                    "_detect_and_filter_entities",
                    new=lambda self, text, entity_type_filter=None: (
                        fake.detect_entities(text)
                    ),
                )
            )
        stack.enter_context(patch.object(readchar, "readkey", new=Keys(keys)))
        stack.enter_context(patch.object(Prompt, "ask", new=Typed(typed)))
        stack.enter_context(patch.object(Confirm, "ask", new=Answers()))
        result = CliRunner().invoke(app, list(args), env=ENV, catch_exceptions=False)
    return result.exit_code, _ANSI.sub("", result.output)


def _process(
    tmp_path: Path,
    db: Path,
    text: str,
    names: Names,
    keys: Sequence[str],
    typed: Sequence[str] = (),
) -> str:
    """One real ``gdpr-pseudo process`` run of ``text``: the written text."""
    source, output = tmp_path / "in.txt", tmp_path / "out.txt"
    source.write_text(text, encoding="utf-8")
    code, shown = _invoke(
        ["process", str(source), "--db", str(db), "-o", str(output)],
        FakeDetector(names),
        keys,
        typed,
    )
    _pre(code == 0, f"exit code 0: {shown!r}")
    _pre(output.is_file(), "the output file is written")
    return output.read_text(encoding="utf-8")


def _add(tmp_path: Path, db: Path, text: str, name: str) -> tuple[str, str]:
    """[A] in the review: ``name`` added as PERSON to « Signé : Éloria. » +
    ``text``. The written text after « Signé : <pseudonym>. », and the
    pseudonym stored for ``name``."""
    written = _process(
        tmp_path,
        db,
        SEEN_TEXT + text,
        [(SEEN, PERSON)],
        [ENTER, "a", SPACE],
        [name, PERSON],
    )
    seen = _pseudonym(db, SEEN)
    head = f"Signé : {seen}. "
    _pre(written.startswith(head), f"the found name written: {written!r}")
    return written[len(head) :], _pseudonym(db, name)


def _delete(
    db: Path, name: str, *, found: bool = True
) -> tuple[str, list[tuple[str, str]]]:
    """One real ``delete-mapping`` run of ``name``, confirmed: what it showed
    before the success lines, and the (full name, type) rows left, sorted.
    With ``found``, the run ends with exit code 0 (a precondition); without
    it, the unfixed code may find no row and end otherwise."""
    code, shown = _invoke(["delete-mapping", name, "--db", str(db)], typed=["yes"])
    if found:
        _pre(code == 0, f"exit code 0: {shown!r}")
    return shown.split(DELETED)[0], _names(db)


def _entities(db: Path) -> list[Entity]:
    """Every stored row, decrypted."""
    with open_database(str(db), PASSPHRASE) as session:
        return SQLiteMappingRepository(session).find_all()


def _names(db: Path) -> list[tuple[str, str]]:
    """Every stored (full_name, entity_type), sorted."""
    return sorted((row.full_name, row.entity_type) for row in _entities(db))


def _pseudonym(db: Path, name: str, entity_type: str = PERSON) -> str:
    """The pseudonym of the one row stored for (name, type)."""
    found = [
        row.pseudonym_full
        for row in _entities(db)
        if (row.full_name, row.entity_type) == (name, entity_type)
    ]
    _pre(len(found) == 1, f"one row stored for ({name}, {entity_type})")
    return str(found[0])


def _save(db: Path, rows: Sequence[tuple[str, str, str]]) -> None:
    """Rows saved as given, (full_name, type, pseudonym), as an earlier
    version saved them."""
    with open_database(str(db), PASSPHRASE) as session:
        repo = SQLiteMappingRepository(session)
        for full_name, entity_type, pseudonym in rows:
            repo.save(
                Entity(
                    entity_type=entity_type,
                    full_name=full_name,
                    pseudonym_full=pseudonym,
                    theme="neutral",
                )
            )
    _pre(len(_names(db)) == len(rows), f"{len(rows)} rows saved")


# ---------------------------------------------------------------------------
# AC1, AC2: a name of two words or more, accents and capitals set aside
# ---------------------------------------------------------------------------


def test_Ex1_cli_correction_in_capitals_reaches_the_name_written_in_title_case(  # noqa: N802
    tmp_path: Path, db: Path
) -> None:
    """Ex1 (AC1, AC2; Lionel: "yes"): « Élorine du Prélis … ÉLORINE DU
    PRÉLIS », « Élorine » and « ÉLORINE » found, the name corrected
    « ELORINE DU PRELIS » at [E]: both places covered, nothing in clear."""
    written = _process(
        tmp_path,
        db,
        EX1_TEXT,
        [("Élorine", PERSON), ("ÉLORINE", PERSON)],
        [ENTER, "e"],
        ["ELORINE DU PRELIS"],
    )
    assert (
        "Prélis" not in written and "PRÉLIS" not in written
    ), written  # expected failure


def test_Ex2_add_reaches_the_name_without_its_accents(  # noqa: N802
    tmp_path: Path, db: Path
) -> None:
    """Ex2 (AC1; Lionel: "yes"): « Zélvine Vorlanne … Zelvine Vorlanne », the
    name added as « Zélvine Vorlanne »: both places covered."""
    written, p = _add(
        tmp_path,
        db,
        "Zélvine Vorlanne a signé. Zelvine Vorlanne valide.",
        "Zélvine Vorlanne",
    )
    assert "Vorlanne" not in written, written  # expected failure
    assert written == f"{p} a signé. {p} valide."


def test_Ex3_one_word_name_never_reaches_another_accent(  # noqa: N802
    tmp_path: Path, db: Path
) -> None:
    """Ex3 (AC1, AC5; Lionel, re-asked, then the split rule): « Mme Mèzor …
    M. Mezor », two people; « Mezor » added (one word, accents kept):
    « Mèzor » is not reached."""
    written, p = _add(tmp_path, db, "Mme Mèzor a signé. M. Mezor valide.", "Mezor")
    assert written == f"Mme Mèzor a signé. M. {p} valide."


def test_Ex4_one_word_name_never_reaches_an_accented_word_at_a_sentence_start(  # noqa: N802
    tmp_path: Path, db: Path
) -> None:
    """Ex4 (AC1, AC5; Lionel: "yes, i prefer this split"): « Arvele » added
    (one word): « Arvelé » at the start of a sentence is not reached."""
    written, p = _add(
        tmp_path,
        db,
        "Zélvine Arvele a signé. Arvelé depuis dix ans, il valide.",
        "Arvele",
    )
    assert written == f"Zélvine {p} a signé. Arvelé depuis dix ans, il valide."


def test_Ex5_delete_mapping_also_deletes_the_name_saved_without_its_accents(  # noqa: N802
    tmp_path: Path, db: Path
) -> None:
    """Ex5 (AC1, AC3; Lionel: "yes, it should"): delete-mapping « Zélvine
    Vorlanne » lists and deletes a saved « Zelvine Vorlanne » too; another
    name stays."""
    _save(
        db,
        [
            ("Zélvine Vorlanne", PERSON, "Arvélis Quentrix"),
            ("Zelvine Vorlanne", PERSON, "Mézor Brimel"),
            ("Éloria Mèzor", PERSON, "Vorlan Zorbal"),
        ],
    )
    screen, left = _delete(db, "Zélvine Vorlanne")
    assert f"{NAME_LINE}Zelvine Vorlanne" in screen, screen  # expected failure
    assert left == [("Éloria Mèzor", PERSON)]


def test_Ex6_add_reaches_the_name_written_in_small_letters(  # noqa: N802
    tmp_path: Path, db: Path
) -> None:
    """Ex6 (AC1; Lionel: "yes"): « … signé par élorine du prélis », the name
    added as « Élorine du Prélis »: the place in small letters is covered."""
    written, _p = _add(
        tmp_path,
        db,
        "Élorine du Prélis valide. Le bail est signé par élorine du prélis.",
        "Élorine du Prélis",
    )
    assert (
        "prélis" not in written and "Prélis" not in written
    ), written  # expected failure


def test_Ex7_one_word_name_never_reaches_a_word_in_small_letters(  # noqa: N802
    tmp_path: Path, db: Path
) -> None:
    """Ex7 (AC1, AC5; Lionel: "no"): « M. Bail … le bail », « Bail » added
    (one word): « bail » in small letters is not reached."""
    written, p = _add(tmp_path, db, "M. Bail a signé le bail.", "Bail")
    assert written == f"M. {p} a signé le bail."


def test_Ex8_two_word_name_reaches_an_ordinary_phrase_in_small_letters(  # noqa: N802
    tmp_path: Path, db: Path
) -> None:
    """Ex8 (AC1, AC4; Lionel: "it is, but we're edging exotic here"; re-asked:
    "yes, that's really an irrealistic edge case btw"): a name of two words
    that is also an ordinary phrase (Lionel's « Rose Blanche »; here « Le
    Bail », main-corpus words) reaches the phrase written in small letters:
    the rule's accepted over-reach."""
    written, p = _add(
        tmp_path, db, "Le Bail valide. Zélvine a signé le bail.", "Le Bail"
    )
    assert "le bail" not in written, written  # expected failure
    assert written == f"{p} valide. Zélvine a signé {p}."


def test_Ex9_one_word_name_never_reaches_itself_in_small_letters(  # noqa: N802
    tmp_path: Path, db: Path
) -> None:
    """Ex9 (AC1, AC5; Lionel: "yes, acceptable"): « Zorbal » added (one word):
    « zorbal » in small letters is not reached."""
    written, p = _add(tmp_path, db, "Zorbal a signé. Le zorbal valide.", "Zorbal")
    assert written == f"{p} a signé. Le zorbal valide."


# ---------------------------------------------------------------------------
# AC3: delete-mapping, the old rows of every variant (P9), and a place name
# saved with its preposition (G7)
# ---------------------------------------------------------------------------


def test_delete_mapping_erases_the_old_rows_of_every_variant_it_reaches(
    tmp_path: Path, db: Path
) -> None:
    """T21 (AC3; the PO's P9, the orchestrator's ruling): delete-mapping
    « Vorlan Melora » reaches « Vorlan Mélora » (Lionel's rule, Ex5), so it
    erases the row v2.2.0 saved damaged for it too (« Vorlan » + U+0301 +
    « lora », 10.20's old-row search run for that variant): both listed,
    both erased; another name stays."""
    acute = unicodedata.lookup("COMBINING ACUTE ACCENT")
    old = _key_steps(unicodedata.normalize("NFD", "Vorlan Mélora"), PERSON)
    _pre(old == "Vorlan " + acute + "lora", f"the old row as v2.2.0 saved it: {old!r}")
    _save(
        db,
        [
            ("Vorlan Mélora", PERSON, "Arvélis Quentrix"),
            (old, PERSON, "Mézor Brimel"),
            ("Éloria Mèzor", PERSON, "Vorlan Zorbal"),
        ],
    )
    screen, left = _delete(db, "Vorlan Melora", found=False)
    assert left == [("Éloria Mèzor", PERSON)], screen  # expected failure
    assert f"{NAME_LINE}{old}" in screen, screen
    assert f"{NAME_LINE}Vorlan Mélora" in screen, screen


def test_delete_mapping_a_place_name_saved_with_its_preposition_is_one_word(
    tmp_path: Path, db: Path
) -> None:
    """G7 (AC3; v2.1, P9): a place name saved with its preposition
    (« à Zorbaville ») is a name of one word for Lionel's rule: delete-mapping
    « ZORBAVILLE » erases « à Zorbaville » and never « à Zòrbaville », another
    place under the one-word rule, as on main."""
    _save(
        db,
        [
            ("à Zorbaville", LOCATION, "Quentrixville"),
            ("à Zòrbaville", LOCATION, "Brimelville"),
        ],
    )
    _screen, left = _delete(db, "ZORBAVILLE")
    assert left == [("à Zòrbaville", LOCATION)]


# ---------------------------------------------------------------------------
# v3.1, AC1 and AC3: one word count (``name_words``), the first Codex
# review's four P0 (K1 to K4)
# ---------------------------------------------------------------------------


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _old(text: str, entity_type: str) -> str:
    """The text v2.2.0 saved for ``text``: 10.20's old key steps on its
    decomposed form."""
    return _key_steps(unicodedata.normalize("NFD", text), entity_type)


def _left_after(
    db: Path, saved: Sequence[tuple[str, str]], typed: str, *, found: bool = True
) -> list[str]:
    """Each (full_name, type) saved, then delete-mapping ``typed``,
    confirmed: the names left, composed, sorted."""
    _save(
        db,
        [
            (text, entity_type, f"Quentrix Brimel{index}")
            for index, (text, entity_type) in enumerate(saved)
        ],
    )
    _delete(db, typed, found=found)
    return sorted(nfc(name) for name, _type in _names(db))


def test_delete_one_word_never_erases_a_titled_name_with_another_accent(
    tmp_path: Path, db: Path
) -> None:
    """K1 (AC1, AC3; Codex review 1, P0-1, its « Barre » shape): « Zorbe »
    saved, and « Maître Zorbé » as v2.2.0 saved it; delete-mapping « Zorbe »
    erases « Zorbe » only: a title is not a word, so « Maître Zorbé » is a
    name of one word, another accent, as on 0be4073."""
    old = _old("Maître Zorbé", PERSON)
    circumflex = unicodedata.lookup("COMBINING CIRCUMFLEX ACCENT")
    acute = unicodedata.lookup("COMBINING ACUTE ACCENT")
    _pre(
        old == "Mai" + circumflex + "tre Zorbe" + acute,
        f"the row as v2.2.0 saved it: {old!r}",
    )
    left = _left_after(db, [("Zorbe", PERSON), (old, PERSON)], "Zorbe")
    assert left == [nfc(old)], left  # expected failure


def test_delete_a_place_with_its_preposition_never_replays_another_accent(
    tmp_path: Path, db: Path
) -> None:
    """K2 (AC1, AC3; P0-2, its « à Macon » shape): « à Zorbacon », « À
    ZORBÂCON » and « à Zorbâcon », each as v2.2.0 saved it; delete-mapping
    « à Zorbacon » keeps « à Zorbâcon », as on 0be4073: with its
    preposition set aside the name has one word, so no variant is
    replayed."""
    saved = [
        (_old(text, LOCATION), LOCATION)
        for text in ("à Zorbacon", "À ZORBÂCON", "à Zorbâcon")
    ]
    left = _left_after(db, saved, "à Zorbacon")
    assert left == [nfc(_old("à Zorbâcon", LOCATION))], left  # expected failure


def test_delete_replays_a_variant_saved_with_a_title(tmp_path: Path, db: Path) -> None:
    """K3 (AC3; P0-3, its « Michel Mérand » shape): « Maître Quovane Mérand »
    saved decomposed and as v2.2.0 damaged it (« Mai » + U+0302 + « tre
    Quovane » + U+0301 + « rand »), and « Éloria Mèzor »; delete-mapping
    « Quovane Merand » erases both rows of the name (its variant, compared
    without its title, is replayed) and keeps the other name. On 0be4073
    the name is found nowhere, so the exit code is not a precondition."""
    old = _old("Maître Quovane Mérand", PERSON)
    circumflex = unicodedata.lookup("COMBINING CIRCUMFLEX ACCENT")
    acute = unicodedata.lookup("COMBINING ACUTE ACCENT")
    _pre(
        old == "Mai" + circumflex + "tre Quovane " + acute + "rand",
        f"the row as v2.2.0 damaged it: {old!r}",
    )
    saved = [
        (unicodedata.normalize("NFD", "Maître Quovane Mérand"), PERSON),
        (old, PERSON),
        ("Éloria Mèzor", PERSON),
    ]
    left = _left_after(db, saved, "Quovane Merand", found=False)
    assert left == ["Éloria Mèzor"], left  # expected failure


@pytest.mark.parametrize(
    ("typed", "other"), [("Du Prelis", "Du Prélis"), ("de Vorlanne", "de Vorlânne")]
)
def test_delete_a_person_whose_surname_starts_with_a_particle(
    tmp_path: Path, db: Path, typed: str, other: str
) -> None:
    """K4 ×2 (AC1, AC3; P0-4, its « Du Pré » shape; QA's REQ-1021-01, « de
    Vorlanne »): a person's name that starts with a preposition is a name of
    two words (a preposition is set aside only for a place): delete-mapping
    « Du Prelis » erases « Du Prélis » too, and « de Vorlanne » « de
    Vorlânne »; « Éloria Mèzor » stays."""
    saved = [(typed, PERSON), (other, PERSON), ("Éloria Mèzor", PERSON)]
    left = _left_after(db, saved, typed)
    assert left == ["Éloria Mèzor"], left  # expected failure
