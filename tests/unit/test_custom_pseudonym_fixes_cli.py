"""Story 10.16: custom pseudonym fixes in the command line and finalization
(T1-T8, T16, T17; Codex release review #8 and #6, Lionel's 10.16 Q1).

CL = ``DocumentProcessor.process_document`` with its interactive review, as
Story 10.11's ``test_custom_pseudonym_cli.py``: detection is replaced, the
keys and the typed texts come from lists, the final confirmation answers
yes, and the warning lines and the groups shown are recorded. CO =
``DocumentProcessor.finalize_document``, the path both desktop workers call.
The library's draw is forced as in Story 10.11's T41: for one real word, the
first ``secrets.choice`` of each call returns the offered value and later
ones the real choice, so every check of the library after the draw is real.

Preconditions fail with ``pytest.fail("PRE: ...")`` (``pre``), never with an
``assert``, so a strict ``xfail(raises=AssertionError)`` never absorbs one.
The first ``assert`` after them is the expected failure on the unfixed code
(``# expected failure``). A refusal when the pseudonym is set is asserted as
exactly one warning, not empty, never its wording; the finalization errors
are Lionel's approved texts, byte for byte. No Qt import. Invented names,
Lionel's preview values and main-corpus words only.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import gdpr_pseudonymizer.pseudonym.library_manager as library_module
from gdpr_pseudonymizer.core.document_processor import (
    DocumentProcessor,
    ProcessingResult,
)
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.validation.ui import ReviewScreen

PASSPHRASE = "zorbalia_pass_A_123!"
QZ = "Quentrel Zorbalia"
QZ_LOW = "quentrel zorbalia"
CUSTOM = "Xantor Vellion"

# Lionel's approved finalization errors: 10.16 Q1 ("Add the new reason
# (Rec.)", 2026-10-16) and 10.11 Q-A's database reason.
IN_DOCUMENT = (
    "CustomPseudonymError: A pseudonym you chose can no longer be used: "
    "it now matches a name in this document. Nothing was written."
)
IN_DATABASE = (
    "CustomPseudonymError: A pseudonym you chose can no longer be used: "
    "it now matches a name in the mapping database. Nothing was written."
)

LOW = "quentrel zorbalia a signé le contrat."
LOW_FIRST = "quentrix a signé avec quentrel zorbalia."
LOW_ORG = "quentrel zorbalia a signé avec zorbaville."
KNOWN_FIRST = "quentrix zorbix a signé le contrat."
KNOWN_DOC = "quentrix zorbix a signé avec quentrel zorbalia."
QCDOC = "Zorbaville a signé avec Quentrel Zorbalia en avril, grâce à son petit groupe."
FIRST_DOC = "Quentrel Zorbalia a signé le contrat."
LATER = "Quentrix Zorbix a signé le contrat."
LATER_OWN = "Zorbalia Quentrix a signé le contrat."
OWN = "Quentrel Zorbix a signé. Le contrat est avec Zorbalia et Quentrel."
ADD_DOC = "quentrel zorbalia a signé avec quovan et quovix."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def pre(condition: bool, message: str) -> None:
    """A precondition: fails the test with "PRE: ..." (``pytest.fail``
    raises ``Failed``, not ``AssertionError``)."""
    if not condition:
        pytest.fail(f"PRE: {message}")


def _fold(text: str) -> str:
    """Accents and capitals ignored."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def _words(text: str) -> list[str]:
    """The folded whole words of ``text``."""
    return re.findall(r"\w+", _fold(text))


def _at(
    text: str, name: str, entity_type: str, start: int | None = None
) -> DetectedEntity:
    start = text.find(name) if start is None else start
    pre(start >= 0 and text[start : start + len(name)] == name, f"slice {name!r}")
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
    if match is None:
        pytest.fail(f"PRE: text damaged or a span not replaced: {output!r}")
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


def _one_warning(warnings: list[str]) -> bool:
    """Exactly one warning was shown, and it is not empty."""
    return len(warnings) == 1 and bool(warnings[0].strip())


def _row_count(db: str) -> int:
    with open_database(db, PASSPHRASE) as session:
        return len(SQLiteMappingRepository(session).find_all())


@dataclass
class _Run:
    """One command-line run: the written text (None if it failed), the
    warnings shown, the groups shown (first-shown order, no repeats), the
    result and the output path."""

    written: str | None
    warnings: list[str]
    order: list[str]
    result: ProcessingResult
    output: Path


def _cli(
    tmp_path: Path,
    db: str,
    name: str,
    text: str,
    entities: list[DetectedEntity],
    keys: list[str],
    typed: list[str],
) -> _Run:
    """One ``process`` run with its interactive review (CL)."""
    source = tmp_path / name
    source.write_text(text, encoding="utf-8")
    output = tmp_path / f"{name}.out.txt"
    warnings: list[str] = []
    shown: list[str] = []
    original_display = ReviewScreen.display_entity

    def display(self: Any, entity: DetectedEntity, *args: Any, **kwargs: Any) -> Any:
        shown.append(entity.text)
        return original_display(self, entity, *args, **kwargs)

    with (
        patch.object(
            DocumentProcessor,
            "_detect_and_filter_entities",
            side_effect=lambda *a, **k: [DetectedEntity(**vars(e)) for e in entities],
        ),
        patch.object(ReviewScreen, "display_entity", display),
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
    order = list(dict.fromkeys(shown))
    written = output.read_text(encoding="utf-8") if result.success else None
    return _Run(written, warnings, order, result, output)


def _finalize(
    db: str,
    text: str,
    entities: list[DetectedEntity],
    output: Path,
    custom_pseudonyms: dict[tuple[str, str], str] | None = None,
) -> ProcessingResult:
    """``finalize_document`` (CO)."""
    return DocumentProcessor(db_path=db, passphrase=PASSPHRASE).finalize_document(
        text, entities, str(output), custom_pseudonyms=custom_pseudonyms
    )


@contextmanager
def _forced_draw(method: str, real: str, offered: str) -> Iterator[dict[str, int]]:
    """The library's ``method`` (``_select_first_name`` or
    ``_select_last_name``), called for the real word ``real``, gets
    ``offered`` from its first ``secrets.choice``; later choices and every
    other call are real (Story 10.11's T41). Yields the number of offers."""
    original = getattr(library_module.LibraryBasedPseudonymManager, method)
    real_choice = library_module.secrets.choice
    offers = {"n": 0}

    def offering(self: Any, *args: Any, **kwargs: Any) -> Any:
        if real not in args and real not in kwargs.values():
            return original(self, *args, **kwargs)
        calls = {"n": 0}

        def choice(seq: Any) -> Any:
            calls["n"] += 1
            if calls["n"] == 1:
                offers["n"] += 1
                return offered
            return real_choice(seq)

        with patch.object(library_module.secrets, "choice", choice):
            return original(self, *args, **kwargs)

    with patch.object(library_module.LibraryBasedPseudonymManager, method, offering):
        yield offers


def _store_first_doc(tmp_path: Path, db: str) -> None:
    """FIRST_DOC finalized with the custom "Xantor Vellion" (PRE: stored with
    the parts "Xantor" and "Vellion")."""
    result = _finalize(
        db,
        FIRST_DOC,
        [_at(FIRST_DOC, QZ, "PERSON", 0)],
        tmp_path / "first.txt",
        {(QZ, "PERSON"): CUSTOM},
    )
    pre(result.success, "custom stored")
    pre(
        _stored(db, QZ, "PERSON")
        == (QZ, "Quentrel", "Zorbalia", CUSTOM, "Xantor", "Vellion"),
        "stored with its parts",
    )


# ---------------------------------------------------------------------------
# #8 in the command line (T1, T2)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.16: reproduces Codex #8 on the unfixed code; fixed in Task 2",
)
@pytest.mark.parametrize(
    "case",
    [
        "whole_name",
        "surname",
        "other_name_accepted",
        "other_name_pending",
        "known_name",
    ],
)
def test_cli_lowercase_review_name_refused(tmp_path: Path, case: str) -> None:
    """T1 (AC1, #8): [C] with the lowercase name itself, its surname,
    another lowercase name of the review (accepted before, or still to
    review) or a name known in the database is refused with one warning;
    the name is written with a generated pseudonym."""
    db = _new_db(tmp_path)
    if case == "known_name":
        known = _cli(
            tmp_path,
            db,
            "known.txt",
            KNOWN_FIRST,
            [_at(KNOWN_FIRST, "quentrix zorbix", "PERSON", 0)],
            ["confirm"],
            [],
        )
        pre(
            known.written is not None
            and _stored(db, "quentrix zorbix", "PERSON") is not None,
            "« quentrix zorbix » stored",
        )
        text = KNOWN_DOC
        entities = [
            _at(text, "quentrix zorbix", "PERSON", 0),
            _at(text, QZ_LOW, "PERSON"),
        ]
        keys, typed, order = ["change_pseudonym", "confirm"], "Xantor Zorbix", [QZ_LOW]
    elif case == "other_name_accepted":
        text = LOW_FIRST
        entities = [_at(text, "quentrix", "PERSON", 0), _at(text, QZ_LOW, "PERSON")]
        keys = ["confirm", "change_pseudonym", "confirm"]
        typed, order = "Xantor Quentrix", ["quentrix", QZ_LOW]
    elif case == "other_name_pending":
        text = LOW_ORG
        entities = [_at(text, QZ_LOW, "PERSON", 0), _at(text, "zorbaville", "ORG")]
        keys = ["change_pseudonym", "confirm", "confirm"]
        typed, order = "Xantor Zorbaville", [QZ_LOW, "zorbaville"]
    else:
        text = LOW
        entities = [_at(text, QZ_LOW, "PERSON", 0)]
        keys = ["change_pseudonym", "confirm"]
        typed = QZ_LOW if case == "whole_name" else "Xantor Zorbalia"
        order = [QZ_LOW]
    run = _cli(tmp_path, db, "doc.txt", text, entities, keys, [typed])
    pre(run.order == order, f"the groups shown in order: {run.order!r}")
    assert _one_warning(run.warnings), run.warnings  # expected failure
    if run.written is None:
        pytest.fail("PRE: written")
    name = next(e for e in entities if e.text == QZ_LOW)
    spans = _spans(entities)
    place = _replacements(run.written, text, spans)[
        spans.index((name.start_pos, name.end_pos))
    ]
    assert _fold(place) != _fold(typed), run.written
    assert not {"quentrel", "zorbalia"} & set(_words(place)), run.written
    stored = _stored(db, QZ_LOW, "PERSON")
    assert stored is not None and stored[3] == place and stored[3] != typed


def test_cli_qc_lowercase_word_still_does_not_block(tmp_path: Path) -> None:
    """T2 (a guard; Lionel's Q-C preview): a lowercase common word of the
    document still does not block: "Grace Vellion" next to « grâce » is
    accepted, without a warning, and written at the name."""
    db = _new_db(tmp_path)
    entities = [_at(QCDOC, QZ, "PERSON")]
    run = _cli(
        tmp_path,
        db,
        "qc.txt",
        QCDOC,
        entities,
        ["change_pseudonym"],
        ["Grace Vellion"],
    )
    assert run.warnings == [], run.warnings
    assert run.written is not None
    assert _replacements(run.written, QCDOC, _spans(entities)) == ["Grace Vellion"]


# ---------------------------------------------------------------------------
# #8 at finalization (T3, T4)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.16: reproduces Codex #8 on the unfixed code; fixed in Task 2",
)
@pytest.mark.parametrize("case", ["own_surname", "other_name_sent"])
def test_finalization_counts_names_sent(tmp_path: Path, case: str) -> None:
    """T3 (AC1, #8; Lionel's 10.16 Q1): finalization refuses a custom
    pseudonym that repeats the lowercase surname of its own name, or another
    lowercase name sent; nothing is written or stored, and the error is
    Lionel's new reason."""
    db = _new_db(tmp_path)
    if case == "own_surname":
        text, custom = LOW, "Xantor Zorbalia"
        entities = [_at(text, QZ_LOW, "PERSON", 0)]
    else:
        text, custom = LOW_FIRST, "Xantor Quentrix"
        entities = [_at(text, "quentrix", "PERSON", 0), _at(text, QZ_LOW, "PERSON")]
    output = tmp_path / "out.txt"
    result = _finalize(db, text, entities, output, {(QZ_LOW, "PERSON"): custom})
    assert not result.success, output.read_text(encoding="utf-8")  # expected failure
    assert not output.exists() or output.read_text(encoding="utf-8") == ""
    assert _row_count(db) == 0
    assert result.error_message == IN_DOCUMENT, result.error_message


def test_finalization_ignores_words_not_sent(tmp_path: Path) -> None:
    """T4 (a guard): a lowercase word of the document that is not sent does
    not count: with only the name sent, "Xantor Quentrix" is written."""
    db = _new_db(tmp_path)
    entities = [_at(LOW_FIRST, QZ_LOW, "PERSON")]
    output = tmp_path / "out.txt"
    result = _finalize(
        db, LOW_FIRST, entities, output, {(QZ_LOW, "PERSON"): "Xantor Quentrix"}
    )
    assert result.success, result.error_message
    written = output.read_text(encoding="utf-8")
    assert _replacements(written, LOW_FIRST, _spans(entities)) == ["Xantor Quentrix"]


# ---------------------------------------------------------------------------
# #6, the generation guard (T5-T8)
# ---------------------------------------------------------------------------

_T5_CASES = {
    "first_part_as_last": ("_select_last_name", "Zorbix", "Xantor", LATER),
    "last_part_as_first": ("_select_first_name", "Quentrix", "Vellion", LATER),
    "own_word_other_role": ("_select_first_name", "Zorbalia", "Vellion", LATER_OWN),
    "first_part_accented": ("_select_first_name", "Quentrix", "Xántor", LATER),
    "last_part_accented": ("_select_last_name", "Zorbix", "Véllion", LATER),
    "first_part_same_role": ("_select_first_name", "Quentrix", "Xantor", LATER),
    "last_part_same_role": ("_select_last_name", "Zorbix", "Vellion", LATER),
}


def _later_with_forced_draw(tmp_path: Path, case: str) -> None:
    """T5 and T6: after FIRST_DOC with "Xantor Vellion", a later name is
    finalized with the library's draw forced; the written name, its stored
    row and its parts take neither "Xantor" nor "Vellion" in any role or
    spelling."""
    db = _new_db(tmp_path)
    _store_first_doc(tmp_path, db)
    method, real, offered, text = _T5_CASES[case]
    name = text[: text.find(" a signé")]
    output = tmp_path / "later.txt"
    with _forced_draw(method, real, offered) as offers:
        result = _finalize(db, text, [_at(text, name, "PERSON", 0)], output)
    pre(offers["n"] >= 1, f"{offered!r} offered for {real!r}")
    pre(result.success, "later document")
    (written,) = _replacements(
        output.read_text(encoding="utf-8"), text, [(0, len(name))]
    )
    assert not {"xantor", "vellion"} & set(_words(written)), written  # expected failure
    stored = _stored(db, name, "PERSON")
    assert stored is not None and stored[3] == written
    parts = {_fold(part) for part in (stored[4], stored[5]) if part}
    assert not {"xantor", "vellion"} & parts, stored


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.16: reproduces Codex #6 on the unfixed code; fixed in Task 2",
)
@pytest.mark.parametrize(
    "case",
    [
        "first_part_as_last",
        "last_part_as_first",
        "own_word_other_role",
        "first_part_accented",
        "last_part_accented",
    ],
)
def test_generation_keeps_roles_and_spellings(tmp_path: Path, case: str) -> None:
    """T5 (AC2, #6): a generated pseudonym never takes a part of the stored
    custom "Xantor Vellion" in the other role ("Xantor" as a last name,
    "Vellion" as a first name, also for the custom's own real last name
    "Zorbalia" used later as a first name) or with another spelling
    ("Xántor", "Véllion")."""
    _later_with_forced_draw(tmp_path, case)


@pytest.mark.parametrize("case", ["first_part_same_role", "last_part_same_role"])
def test_generation_same_role_same_spelling_redrawn(tmp_path: Path, case: str) -> None:
    """T6 (a guard; QA's control): "Xantor" offered as another first name, or
    "Vellion" as another last name, is drawn again by the library itself."""
    _later_with_forced_draw(tmp_path, case)


def test_generation_reuses_own_parts(tmp_path: Path) -> None:
    """T7 (a guard; 10.11 AC2, AC19): the reuse 10.11 requires stays: a later
    "Quentrel Zorbix" starts with "Xantor", a lone "Zorbalia" is "Vellion"
    and a lone "Quentrel" is "Xantor"."""
    db = _new_db(tmp_path)
    _store_first_doc(tmp_path, db)
    entities = [
        _at(OWN, "Quentrel Zorbix", "PERSON", 0),
        _at(OWN, "Zorbalia", "PERSON"),
        _at(OWN, "Quentrel", "PERSON", OWN.rfind("Quentrel")),
    ]
    output = tmp_path / "own.txt"
    result = _finalize(db, OWN, entities, output)
    assert result.success, result.error_message
    full, lone_last, lone_first = _replacements(
        output.read_text(encoding="utf-8"), OWN, _spans(entities)
    )
    assert full.startswith("Xantor ") and full != CUSTOM, full
    assert lone_last == "Vellion"
    assert lone_first == "Xantor"


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Story 10.16: reproduces Codex #6 on the unfixed code; fixed in Task 2",
)
def test_cli_generation_other_role(tmp_path: Path) -> None:
    """T8 (AC2, #6; QA's reproduction in the command line): after [C]
    "Xantor Vellion", a later name whose last name the library offers
    "Xantor" is not written with "Xantor" as its last name."""
    db = _new_db(tmp_path)
    first = _cli(
        tmp_path,
        db,
        "first.txt",
        FIRST_DOC,
        [_at(FIRST_DOC, QZ, "PERSON", 0)],
        ["change_pseudonym"],
        [CUSTOM],
    )
    pre(
        first.written == f"{CUSTOM} a signé le contrat." and first.warnings == [],
        "written, no warning",
    )
    name = "Quentrix Zorbix"
    with _forced_draw("_select_last_name", "Zorbix", "Xantor") as offers:
        later = _cli(
            tmp_path,
            db,
            "later.txt",
            LATER,
            [_at(LATER, name, "PERSON", 0)],
            ["confirm"],
            [],
        )
    pre(offers["n"] >= 1, "'Xantor' offered for 'Zorbix'")
    if later.written is None:
        pytest.fail("PRE: later document written")
    written = _replacements(later.written, LATER, [(0, len(name))])[0]
    assert not written.endswith(" Xantor"), written  # expected failure
    stored = _stored(db, name, "PERSON")
    assert stored is not None and stored[3] == written and stored[5] != "Xantor"


# ---------------------------------------------------------------------------
# Lionel's 10.16 Q1: a name marked after the pseudonym (T16), and the
# database reason kept (T17)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "Story 10.16: reproduces Lionel's 10.16 Q1 path on the unfixed code; "
        "fixed in Task 2"
    ),
)
def test_cli_name_added_after_the_pseudonym(tmp_path: Path) -> None:
    """T16 (AC1, AC5; Lionel's 10.16 Q1): [C] "Xantor Quovix" on the name,
    then « quovix » added with [A]: the run fails with Lionel's new reason;
    no file, no row."""
    db = _new_db(tmp_path)
    entities = [_at(ADD_DOC, QZ_LOW, "PERSON", 0), _at(ADD_DOC, "quovan", "PERSON")]
    run = _cli(
        tmp_path,
        db,
        "add.txt",
        ADD_DOC,
        entities,
        ["change_pseudonym", "add", "confirm"],
        ["Xantor Quovix", "quovix", "PERSON"],
    )
    pre(run.warnings == [], f"no warning: {run.warnings!r}")
    pre(run.order == [QZ_LOW, "quovan"], f"the groups shown in order: {run.order!r}")
    assert run.written is None, run.written  # expected failure
    assert run.result.error_message == IN_DOCUMENT, run.result.error_message
    assert not run.output.exists()
    assert _stored(db, QZ_LOW, "PERSON") is None


def test_finalization_stored_name_keeps_the_database_reason(tmp_path: Path) -> None:
    """T17 (a guard; AC5): a full name stored by an earlier document, inside
    the custom pseudonym (Q-C2) and not a name of this document, keeps 10.11's
    database reason."""
    db = _new_db(tmp_path)
    earlier = _finalize(
        db,
        LATER,
        [_at(LATER, "Quentrix Zorbix", "PERSON", 0)],
        tmp_path / "earlier.txt",
    )
    pre(
        earlier.success and _stored(db, "Quentrix Zorbix", "PERSON") is not None,
        "« Quentrix Zorbix » stored",
    )
    output = tmp_path / "out.txt"
    result = _finalize(
        db,
        LOW,
        [_at(LOW, QZ_LOW, "PERSON", 0)],
        output,
        {(QZ_LOW, "PERSON"): "Xantor Quentrix Zorbix"},
    )
    assert not result.success
    assert result.error_message == IN_DATABASE, result.error_message
    assert _stored(db, QZ_LOW, "PERSON") is None
