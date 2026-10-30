"""Repository interface and implementation for entity mapping persistence."""

from __future__ import annotations

import re
import unicodedata
from abc import ABC, abstractmethod

from gdpr_pseudonymizer.core.legacy_names import matches_search, title_words
from gdpr_pseudonymizer.core.mapping_key import (
    _key_texts,
    lookup_key,
    saved_name_forms,
)
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.exceptions import DatabaseError, DuplicateEntityError
from gdpr_pseudonymizer.utils.french_patterns import (
    FRENCH_TITLE_PATTERN,
    strip_french_titles,
)
from gdpr_pseudonymizer.utils.text_form import composed, is_mark

# The types a name is looked up under, for its forms (Story 10.20): only a
# LOCATION has forms of its own (its prepositions); every other type has a
# PERSON's.
_FORM_TYPES = ("PERSON", "LOCATION")


def _name_forms(full_name: str, entity_type: str) -> list[str]:
    """Every text a row of this name and type may hold (Story 10.20, Lionel's
    Qa and Qb; v1.7, ``saved_name_forms``), in the order a lookup prefers
    them: the composed name first."""
    return saved_name_forms(full_name, entity_type)


def _same_or_form(text: str, name: str) -> bool:
    """Whether a saved name is erased with ``name`` (Story 10.19, AC4): the
    same letters whatever their capitals, or a form of it (``is_form``:
    written entirely in capitals, accents set aside)."""
    # Imported here: the data layer reads the forms rule of the validation
    # models, which import the core (no gui/ import).
    from gdpr_pseudonymizer.validation.models import is_form

    return text.lower() == name.lower() or is_form(text, name)


def _one_mark(text: str) -> str:
    """``text`` with every accent mark written as one mark (U+0301), so that
    comparing Q3 forms of saved forms, every accent mark counts as a mark,
    whatever its kind (Story 10.19, v1.13; the orchestrator's ruling on the
    second Codex review's third P0): v2.2.0's « VORLAN » + U+0300 + « LORA »
    (from « VORLAN MÈLORA ») meets « VORLAN » + U+0301 + « LORA »."""
    return "".join("\u0301" if is_mark(char) else char for char in text)


# The words 10.20's replay may insert in an old key (a decomposed « Maître »,
# and a place's leading « à »), in capitals with accents set aside.
_INSERTED_TITLE = "MAITRE"
_INSERTED_PREPOSITION = "A"


def _title_words_in_capitals() -> frozenset[str]:
    """The title words of ``FRENCH_TITLE_PATTERN`` (10.20's ``title_words``),
    in capitals with accents set aside, without their « . »."""
    # Imported here: the data layer reads the forms rule of the validation
    # models, which import the core (no gui/ import).
    from gdpr_pseudonymizer.validation.models import fold

    return frozenset(
        fold(word).upper() for word in title_words() if not word.endswith(".")
    )


# The bound v2.2.0's title pattern asks for before a title word, read from
# ``FRENCH_TITLE_PATTERN`` itself: the part before its title words (« \b »)
# (Story 10.19, v1.27; the ninth Codex review's P0). The walk offers a cut
# or an inserted word wherever the old step allowed one: after a space, a
# hyphen, a mark, « ( », « [ », « / », a quotation mark...
_TITLE_BOUND = re.compile(
    FRENCH_TITLE_PATTERN[: FRENCH_TITLE_PATTERN.index("(?:")], re.IGNORECASE
)


def _bound_after(char: str) -> bool:
    """Whether the old title pattern's bound holds between ``char`` and the
    first letter of a title word."""
    return _TITLE_BOUND.match(char + "M", 1) is not None


def _lone_mark(text: str) -> bool:
    """Whether ``text`` holds an accent mark at its start, or right after a
    character that is not a mark and after which the old title pattern's
    bound holds: a mark a cut left alone (10.20's sign, a word starting with
    a mark, read with the same bound; v1.27: after « ( », « [ » or « / »
    too, QA's DEL-1019-10)."""
    return any(
        is_mark(char)
        and (at == 0 or (not is_mark(text[at - 1]) and _bound_after(text[at - 1])))
        for at, char in enumerate(text)
    )


# Room for the words 10.20's replay inserts (« MAITRE » and « A », each with
# a space), for ``_cut_places``'s bound on a row's letters.
_INSERTED_ROOM = len(_INSERTED_TITLE) + len(_INSERTED_PREPOSITION) + 2


# The letters French writes with an accent mark (« É », « Ÿ », « Ç »), in
# capitals with accents set aside, for ``_cut_places`` (Story 10.19, v1.23):
# only such a letter of a name can have carried a mark the old step left.
_MARKED_LETTERS = frozenset("AEIOUYC")


def _cut_places(
    words: list[str], row: str, location: bool, titles: frozenset[str]
) -> set[frozenset[int]]:
    """The sets of the name's letters which, accented, may have let v2.2.0's
    title step turn the name into ``row`` (Story 10.19, v1.21; v1.23, the
    seventh Codex review's P0 and the orchestrator's "any sequence of cuts
    the old title step could make").

    ``words`` is the name in capitals, accents set aside; the letters are
    offsets in ``" ".join(words)``. ``row`` is a saved row decomposed, in
    capitals, its spaces collapsed, its marks kept. The old step took title
    words off between word bounds, again until nothing changed, and never
    took a mark off: each mark of the row is the accent of the name's letter
    read just before it, whether that letter stayed or went with a title
    word, and a mark bounds the next word whatever cut left it there
    (« MÈME TESTAR » saved as a mark + « TESTAR »). Reading the name and the
    row side by side, each step may:

    - match a letter;
    - read a mark of the row as the accent of the letter just read, when
      French writes that letter with an accent (``_MARKED_LETTERS``: never
      the « R » of « DR », so « Drlime » never meets « MÉLIME »'s old row);
    - take off a title word of the name starting there, with or without the
      spaces after it, where the old title pattern's own bound can stand
      before it (``bound_before``; v1.27: the name's start or the row's, or
      after any character the pattern lets a title word follow, a space, a
      hyphen, a mark, « ( », « [ », « / »...);
    - pass over a « MAITRE » word, or a place's « A », which 10.20's replay
      inserts, where the same bound can stand before it as before a title
      cut (``bound_before``; v1.25, the eighth Codex review's P0): a
      cut may have glued it to the mark before it (« QUOVÔME MAÎTRE
      TESTAR » saved as « QUOVO » + a mark + « MAI » + a mark + « TRE
      TESTAR »), and after the name's last word, the space before it is its
      bound (« MÉLORA VORLAN MAÎTRE » saved as a mark + « LORA VORLAN MAI »
      + a mark + « TRE »).

    The walk only offers sets: the caller replays the old step on the name
    accented at each set (``_name_forms``) and keeps a row only when that
    replay gives it. Memoised on the two positions. A row with more
    characters other than marks than the name and the inserted words have is
    not walked: no step adds one.
    """
    name = " ".join(words)
    if sum(not is_mark(char) for char in row) > len(name) + _INSERTED_ROOM:
        return set()
    memo: dict[tuple[int, int], set[frozenset[int]]] = {}
    inserted = [_INSERTED_TITLE] + ([_INSERTED_PREPOSITION] if location else [])

    def past_spaces(i: int) -> int:
        while i < len(name) and name[i] == " ":
            i += 1
        return i

    def past_inserted(j: int, word: str) -> int | None:
        """The row's position after ``word`` (each letter with its marks,
        then a space or the end) written at ``j``, or None."""
        for letter in word:
            if j >= len(row) or row[j] != letter:
                return None
            j += 1
            while j < len(row) and is_mark(row[j]):
                j += 1
        if j == len(row):
            return j
        return j + 1 if row[j] == " " else None

    def bound_before(i: int, j: int) -> bool:
        """Whether the old title pattern's bound can stand before the name's
        ``i`` read at the row's ``j``: the text's start, or a character
        before it, in the name or in the row, after which the bound holds
        (``_bound_after``, v1.27)."""
        return i == 0 or j == 0 or _bound_after(name[i - 1]) or _bound_after(row[j - 1])

    def walk(i: int, j: int) -> set[frozenset[int]]:
        if (i, j) in memo:
            return memo[(i, j)]
        found: set[frozenset[int]] = set()
        if i == len(name) and j == len(row):
            found.add(frozenset())
        if i < len(name) and j < len(row) and name[i] == row[j]:
            found |= walk(i + 1, j + 1)
        if (
            j < len(row)
            and is_mark(row[j])
            and i > 0
            and name[i - 1] in _MARKED_LETTERS
        ):
            found |= {places | {i - 1} for places in walk(i, j + 1)}
        if i < len(name) and bound_before(i, j):
            for title in titles:
                if name.startswith(title, i):
                    end = i + len(title)
                    found |= walk(end, j)
                    found |= walk(past_spaces(end), j)
        if bound_before(i, j):
            for word in inserted:
                after = past_inserted(j, word)
                if after is not None:
                    found |= walk(i, after)
        if i == len(name) and j < len(row) and row[j] == " ":
            # only « MAITRE » follows the name's last word: 10.20's replay
            # puts a place's « à » in front of it only (v1.27)
            for word in [_INSERTED_TITLE]:
                if past_inserted(j + 1, word) == len(row):
                    found |= walk(i, len(row))
        memo[(i, j)] = found
        return found

    return walk(0, 0)


def _seed_key(text: str) -> str:
    """A capitals text as the damaged forms are compared, whatever way its
    marks compose (Story 10.19, v1.17; the fourth Codex review's P0-2).

    Read decomposed, in small letters: a letter's own accent (the first mark
    right after it) is set aside, as Q3 does in capitals, and every other
    mark is written as one mark (U+0301), whatever its kind. So « QUOVO » +
    U+0302 + U+0301 + « LORA » (v2.2.0's row of « QUOVÔME MÉLORA ») meets
    « QUOVO » + U+0301 + U+0301 + « LORA », and « VORLAN » + U+0300 +
    « LORA » meets « VORLAN » + U+0301 + « LORA »."""
    out: list[str] = []
    after_letter = False
    for char in unicodedata.normalize("NFD", text):
        if is_mark(char):
            if not after_letter:
                out.append("\u0301")
            after_letter = False
            continue
        after_letter = char.isalpha()
        out.append(char)
    return "".join(out).lower()


def _keeps_words(words: list[str], form_words: list[str]) -> bool:
    """Whether every word of ``words`` is among ``form_words``, in order: a
    saved form that keeps every word of the name as typed (a title or a
    preposition may be added), as opposed to one that lost letters or a
    word."""
    remaining = iter(form_words)
    return all(word in remaining for word in words)


class MappingRepository(ABC):
    """Abstract interface for entity mapping persistence.

    This interface defines the contract for storing and retrieving entity mappings.
    Implementations must handle encryption/decryption transparently.
    """

    @abstractmethod
    def find_by_full_name_and_type(
        self, full_name: str, entity_type: str
    ) -> Entity | None:
        """Find the entity stored for a text under one type (Story 10.7).

        A row is identified by its text and its type: the same text under
        another type is another row, with its own pseudonym.

        Args:
            full_name: Complete entity name to search for
            entity_type: Entity type (PERSON, LOCATION, ORG)

        Returns:
            Entity if found, None otherwise
        """
        pass

    @abstractmethod
    def find_all_by_full_name(self, full_name: str) -> list[Entity]:
        """Find every entity stored for a text, whatever its type (Story 10.7).

        Args:
            full_name: Complete entity name to search for

        Returns:
            Every matching entity, ordered by type (empty list if none)
        """
        pass

    @abstractmethod
    def find_all_by_full_name_any_capitals(self, full_name: str) -> list[Entity]:
        """Find every entity stored for a text, whatever its type or its
        capitals (Story 10.19, AC4).

        The rows ``find_all_by_full_name`` finds, then every row whose name
        differs from the text only in capitals, or is written entirely in
        capitals with the text's letters once accents are set aside, or (as
        an earlier version saved it) is one of the text's saved forms in
        other capitals.

        Args:
            full_name: Complete entity name to search for

        Returns:
            Every matching entity (empty list if none)
        """
        pass

    @abstractmethod
    def find_by_component(self, component: str, component_type: str) -> list[Entity]:
        """Find entities with matching name component for compositional logic.

        Args:
            component: Name component to search for (e.g., "Marie")
            component_type: Type of component ("first_name" or "last_name")

        Returns:
            List of entities with matching component
        """
        pass

    @abstractmethod
    def save(self, entity: Entity) -> Entity:
        """Persist new entity or update existing.

        Args:
            entity: Entity to save

        Returns:
            Saved entity with generated ID
        """
        pass

    @abstractmethod
    def save_batch(self, entities: list[Entity]) -> list[Entity]:
        """Persist multiple entities in single transaction.

        Args:
            entities: List of entities to save

        Returns:
            List of saved entities
        """
        pass

    @abstractmethod
    def find_all(
        self,
        entity_type: str | None = None,
        is_ambiguous: bool | None = None,
    ) -> list[Entity]:
        """Query entities with optional filters.

        Args:
            entity_type: Filter by entity type (PERSON, LOCATION, ORG)
            is_ambiguous: Filter by ambiguity flag

        Returns:
            List of entities matching filters
        """
        pass

    @abstractmethod
    def delete_entities_by_full_name(self, full_name: str) -> list[Entity]:
        """Delete every entity stored for a text, whatever its type (Story 10.7).

        All rows are deleted in one transaction, so a name is never erased in
        part.

        Args:
            full_name: Plaintext full name of the entities to delete

        Returns:
            Decrypted entities that were deleted, ordered by type (empty list
            if none)
        """
        pass

    @abstractmethod
    def delete_entities_by_full_name_any_capitals(self, full_name: str) -> list[Entity]:
        """Delete every entity ``find_all_by_full_name_any_capitals`` finds for
        a text, in one transaction (Story 10.19, AC4).

        Args:
            full_name: Plaintext full name of the entities to delete

        Returns:
            Decrypted entities that were deleted (empty list if none)
        """
        pass

    @abstractmethod
    def delete_entity_by_id(self, entity_id: str) -> Entity | None:
        """Delete entity by UUID.

        Args:
            entity_id: UUID of entity to delete

        Returns:
            Decrypted entity that was deleted, or None if not found
        """
        pass

    @abstractmethod
    def search_entities(
        self,
        search_term: str | None = None,
        entity_type: str | None = None,
    ) -> list[Entity]:
        """Search entities with optional name and type filters.

        Args:
            search_term: Case-insensitive substring to match against entity names
            entity_type: Filter by entity type (PERSON, LOCATION, ORG)

        Returns:
            List of matching decrypted entities
        """
        pass


class SQLiteMappingRepository(MappingRepository):
    """SQLite implementation of MappingRepository with column-level encryption.

    Transparently handles encryption/decryption of sensitive fields using
    DatabaseSession's EncryptionService. Leverages AES-256-SIV deterministic
    encryption for queryable encrypted fields.

    Story 10.20 (Lionel, 2026-10-21, Qa "A: Find as they are (Rec.)"): a
    lookup by name or by name component reaches every form a row of the name
    may hold (``_name_forms``) in one indexed query, each form one encryption;
    no saved row is rewritten. When a name and type are saved in several
    forms, the row saved the usual (composed) way comes first (Qb, "A: Usual
    way's one (Rec.)").
    """

    def __init__(self, db_session: DatabaseSession) -> None:  # type: ignore  # noqa: F821
        """Initialize repository with database session.

        Args:
            db_session: DatabaseSession with encryption service

        Note:
            This is a BREAKING CHANGE from the stub constructor signature.
            Previous: __init__(self, db_path: str)
            Current: __init__(self, db_session: DatabaseSession)
        """
        self._session = db_session.session
        self._encryption = db_session.encryption

    def find_by_full_name_and_type(
        self, full_name: str, entity_type: str
    ) -> Entity | None:
        """Find the entity stored for an encrypted full name under one type.

        Args:
            full_name: Plaintext full name to search for
            entity_type: Entity type (PERSON, LOCATION, ORG)

        Story 10.20: every form of the name (``_name_forms``) is looked up in
        one indexed query; of several rows found, the one whose form comes
        first is returned, so the row saved the usual way wins (Lionel's Qb).

        Returns:
            Entity with decrypted fields, or None if not found

        Example:
            >>> entity = repo.find_by_full_name_and_type("Marie Dubois", "PERSON")
            >>> print(entity.full_name)  # "Marie Dubois" (decrypted)
        """
        # Encrypt each form for deterministic lookup; its rank is its order
        rank = self._encrypted_ranks(_name_forms(full_name, entity_type))

        # Query by encrypted field and type: one indexed query, (text, type) unique
        db_entities = (
            self._session.query(Entity)
            .filter(
                Entity.full_name.in_(list(rank)),
                Entity.entity_type == entity_type,
            )
            .all()
        )

        if not db_entities:
            return None

        # Decrypt and return the row of the preferred form
        return self._decrypt_entity(
            min(db_entities, key=lambda db_entity: rank[db_entity.full_name])
        )

    def _encrypted_ranks(self, forms: list[str]) -> dict[str, int]:
        """Each form's encryption (deterministic), with the form's rank."""
        rank: dict[str, int] = {}
        for index, form in enumerate(forms):
            encrypted = self._encryption.encrypt(form)
            if encrypted is not None:
                rank.setdefault(encrypted, index)
        return rank

    def find_all_by_full_name(self, full_name: str) -> list[Entity]:
        """Find every entity stored for an encrypted full name, whatever its type.

        Args:
            full_name: Plaintext full name to search for

        Returns:
            Entities with decrypted fields, ordered by type (empty list if none)
        """
        return [self._decrypt_entity(e) for e in self._query_by_full_name(full_name)]

    def _query_by_full_name(self, full_name: str) -> list[Entity]:
        """Stored (encrypted) rows of a plaintext full name, ordered by type.

        Story 10.20: every form of the name, for every type, in one indexed
        query; a row is kept when its text is a form of the name for its own
        type. Each type's rows are in the order of their forms (the row
        saved the usual way first).
        """
        ranks = {
            form_type: self._encrypted_ranks(_name_forms(full_name, form_type))
            for form_type in _FORM_TYPES
        }
        every_form = {value for rank in ranks.values() for value in rank}
        found: list[Entity] = (
            self._session.query(Entity)
            .filter(Entity.full_name.in_(list(every_form)))
            .all()
        )

        def rank_of(row: Entity) -> dict[str, int]:
            return ranks["LOCATION" if row.entity_type == "LOCATION" else "PERSON"]

        rows = [row for row in found if row.full_name in rank_of(row)]
        rows.sort(key=lambda row: (row.entity_type, rank_of(row)[row.full_name]))
        return rows

    def find_all_by_full_name_any_capitals(self, full_name: str) -> list[Entity]:
        """Find every entity stored for a plaintext full name, whatever its
        type or its capitals (Story 10.19, AC4; Lionel's Q1 and Q3).

        Args:
            full_name: Plaintext full name to search for

        Returns:
            Entities with decrypted fields: those ``find_all_by_full_name``
            finds first, ordered by type, then the others (empty list if none)
        """
        return [
            self._decrypt_entity(e)
            for e in self._query_by_full_name_any_capitals(full_name)
        ]

    def _query_by_full_name_any_capitals(self, full_name: str) -> list[Entity]:
        """Stored (encrypted) rows of a plaintext full name, whatever its type
        or its capitals (Story 10.19, AC4).

        First the rows ``_query_by_full_name`` finds (Story 10.20: every form
        an earlier version saved the name in), in its order. Then every other
        row, its name decrypted and composed, whose name is the same letters
        whatever their capitals (a saved « zorbal » for « Zorbal » too), or a
        form of the name (``is_form``: written entirely in capitals with the
        name's letters once accents are set aside, « HELENE » for « Hélène »),
        or whose name, composed, is the same letters as, or a form of, one of
        the name's saved forms composed (``_name_forms``, for its type as
        ``_query_by_full_name`` reads them): a row an earlier version saved
        damaged, in other capitals or in capitals without an accent (the
        PO's v1.5 M1; Lionel's 10.20 Qa; the Codex review's P0-2). A lone
        mark does not compose, so it stays in the comparison.

        The sign is kept (Lionel's 10.20 P0-1, "Only with a sign"): a saved
        form that lost letters (not every word of the name as typed, accents
        set aside, is among its words in order) matches only a row whose
        saved text carries an accent mark, so a name saved today that is such
        a form once composed (« QUOVÔZORBAL »), another person's, is never
        reached; nor is the name without a title typed with it (10.20's
        clean-database rule).

        v1.13 (the second Codex review's third P0; QA's DEL-1019-01): the
        forms that lost letters of the name's damaged capitals texts
        (« VORLAN MÉLORA » for « Vorlan Mélora » or « Vorlan Melora »;
        v1.19: found row by row; v1.21: ``_cut_places``) reach a row
        written entirely in capitals that carries a mark, every accent mark
        counting there as one mark,
        whatever its kind, so « VORLAN » + U+0300 + « LORA », saved from
        « VORLAN MÈLORA », is erased with « Vorlan Mélora »; v1.17: compared
        by ``_seed_key``, whatever way marks side by side compose. v1.15
        (the third Codex review's P0-3; the orchestrator's ruling 4): the
        name's own saved forms are compared with their marks as they are, so
        « Vorlan » + U+0300 + « lora », saved from « Vorlan Mèlora », another
        name in title case, stays. The sign rule reads the saved text as it
        is.

        A row is compared only when its composed text, accents set aside, in
        small letters, is that of the name or of one of the forms (one
        ``fold`` per row). Every other saved row is decrypted once, as
        ``search_entities`` does.
        """
        # Imported here: the data layer reads the forms rule of the
        # validation models, which import the core (no gui/ import).
        from gdpr_pseudonymizer.validation.models import fold

        rows = self._query_by_full_name(full_name)
        found = {row.id for row in rows}
        name = composed(full_name)
        name_words = fold(name).lower().split()
        letters = {fold(name).lower(), fold(_one_mark(name)).lower()}
        old_forms: dict[str, list[tuple[str, bool]]] = {}
        titles = _title_words_in_capitals()
        caps_words = fold(name).upper().split()
        lost_keys: dict[tuple[frozenset[int], str], set[str]] = {}

        def lost_forms(cut: frozenset[int], form_type: str) -> set[str]:
            """The ``_seed_key`` of every form that lost letters of the name
            in capitals with an accent put back on the letters of ``cut``
            (offsets in the name's words joined by one space)."""
            if (cut, form_type) not in lost_keys:
                letters_of = list(" ".join(caps_words))
                for at in cut:
                    letters_of[at] = composed(letters_of[at] + "\u0301")
                seed = "".join(letters_of)
                # v1.27 (QA's DEL-1019-10): 10.20's replay keeps a key that
                # lost letters only with its sign, a word starting with a
                # mark; a mark a cut left after « ( », « [ » or « / » is the
                # same sign, so the old step's own keys of the seed that hold
                # such a mark are kept too
                old_keys = (
                    " ".join(strip_french_titles(text).split())
                    for text, _inserted in _key_texts(
                        lookup_key(seed, form_type), form_type
                    )
                )
                seed_forms = [
                    *_name_forms(seed, form_type),
                    *(key for key in old_keys if _lone_mark(key)),
                ]
                lost_keys[(cut, form_type)] = {
                    _seed_key(saved)
                    for saved in seed_forms
                    if not _keeps_words(
                        name_words, fold(composed(saved)).lower().split()
                    )
                }
            return lost_keys[(cut, form_type)]

        def reaches_old_row(stored: str, form_type: str) -> bool:
            """Whether a row in capitals is one an earlier version saved
            damaged from the name (Story 10.19, v1.19; v1.21 read at the
            row's marks, ``_cut_places``; v1.23 the old step deciding): for
            some set of accented letters the walk offers, the old step's
            replay on the name accented there gives a form that lost letters
            whose ``_seed_key`` is the row's. v1.25: the empty set too, the
            name in capitals with no letter accented (« ELORIA-MELORA
            MAÎTRE MME VORLAN » saved without its « MME »)."""
            row = " ".join(unicodedata.normalize("NFD", stored).upper().split())
            key = _seed_key(stored)
            return any(
                key in lost_forms(cut, form_type)
                for cut in _cut_places(caps_words, row, form_type == "LOCATION", titles)
            )

        for form_type in _FORM_TYPES:
            forms: list[tuple[str, bool]] = []
            for form in dict.fromkeys(
                composed(saved) for saved in _name_forms(full_name, form_type)
            ):
                folded = fold(form).lower()
                letters.add(folded)
                letters.add(fold(_one_mark(form)).lower())
                forms.append((form, _keeps_words(name_words, folded.split())))
            old_forms[form_type] = forms
        for row in self._session.query(Entity).all():
            if row.id in found:
                continue
            stored = self._encryption.decrypt(row.full_name)
            if stored is None:
                continue
            text = composed(stored)
            form_type = "LOCATION" if row.entity_type == "LOCATION" else "PERSON"
            marked = any(is_mark(char) for char in stored)
            if (
                marked
                and not any(char.islower() for char in text)
                and reaches_old_row(stored, form_type)
            ):
                rows.append(row)
                continue
            if fold(_one_mark(text)).lower() not in letters:
                continue
            if _same_or_form(text, name) or any(
                (keeps or marked) and _same_or_form(text, form)
                for form, keeps in old_forms[form_type]
            ):
                rows.append(row)
        return rows

    def find_by_component(self, component: str, component_type: str) -> list[Entity]:
        """Find entities with matching encrypted name component.

        Args:
            component: Plaintext component to search for (e.g., "Marie")
            component_type: "first_name" or "last_name"

        Returns:
            List of entities with decrypted fields

        Raises:
            ValueError: If component_type invalid

        Example:
            >>> entities = repo.find_by_component("Marie", "first_name")
            >>> for e in entities:
            ...     print(e.first_name)  # "Marie" (decrypted)
        """
        if component_type not in ("first_name", "last_name"):
            raise ValueError(
                f"Invalid component_type: {component_type}. Must be 'first_name' or 'last_name'."
            )

        # Story 10.20: every form of the component, as a PERSON's name, each
        # encrypted (deterministic), in one indexed query
        rank = self._encrypted_ranks(_name_forms(component, "PERSON"))
        column = (
            Entity.first_name if component_type == "first_name" else Entity.last_name
        )
        db_entities = self._session.query(Entity).filter(column.in_(list(rank))).all()

        def rank_of(db_entity: Entity) -> int:
            value = (
                db_entity.first_name
                if component_type == "first_name"
                else db_entity.last_name
            )
            return rank[value] if value is not None else len(rank)

        # Decrypt and return, the usual form's rows first
        return [self._decrypt_entity(e) for e in sorted(db_entities, key=rank_of)]

    def save(self, entity: Entity) -> Entity:
        """Persist entity with encrypted sensitive fields.

        Args:
            entity: Entity with plaintext fields

        Returns:
            Saved entity with plaintext fields and generated ID

        Raises:
            DuplicateEntityError: If an entity with the same full_name and
                entity_type exists
            DatabaseError: If database operation fails

        Example:
            >>> entity = Entity(
            ...     entity_type="PERSON",
            ...     full_name="Marie Dubois",
            ...     pseudonym_full="Leia Organa",
            ...     theme="star_wars"
            ... )
            >>> saved = repo.save(entity)
            >>> print(saved.id)  # UUID generated
        """
        from sqlalchemy.exc import IntegrityError, OperationalError

        try:
            # Create encrypted copy for database
            encrypted_entity = self._encrypt_entity(entity)

            # Add to session and commit
            self._session.add(encrypted_entity)
            self._session.commit()

            # Refresh to get generated fields (id, timestamp)
            self._session.refresh(encrypted_entity)

            # Return decrypted entity
            return self._decrypt_entity(encrypted_entity)

        except IntegrityError as e:
            self._session.rollback()
            raise DuplicateEntityError(
                f"Entity with full_name '{entity.full_name}' already exists"
            ) from e
        except OperationalError as e:
            self._session.rollback()
            raise DatabaseError(f"Database operation failed: {e}") from e

    def save_batch(self, entities: list[Entity]) -> list[Entity]:
        """Persist multiple entities in single transaction with race condition handling.

        Args:
            entities: List of entities with plaintext fields

        Returns:
            List of saved entities with plaintext fields (includes both new and
            existing entities that were found during race condition handling)

        Raises:
            DatabaseError: If batch operation fails after retry attempts

        Note:
            Race condition handling: If batch insert fails due to UNIQUE constraint
            (common in parallel processing), falls back to individual saves with
            duplicate detection. Entities that already exist are looked up and
            returned instead of failing.

        Example:
            >>> entities = [Entity(...), Entity(...), Entity(...)]
            >>> saved = repo.save_batch(entities)
            >>> assert len(saved) == len(entities)
        """
        from sqlalchemy.exc import IntegrityError, OperationalError

        try:
            # Encrypt all entities
            encrypted_entities = [self._encrypt_entity(e) for e in entities]

            # Add all to session (better than bulk_save_objects for tracking)
            self._session.add_all(encrypted_entities)
            self._session.commit()

            # Flush to ensure IDs are generated
            self._session.flush()

            # Return decrypted entities
            return [self._decrypt_entity(e) for e in encrypted_entities]

        except IntegrityError:
            # Race condition: another worker inserted same entity
            # Fall back to individual saves with duplicate handling
            self._session.rollback()
            return self._save_batch_with_retry(entities)

        except OperationalError as e:
            self._session.rollback()
            raise DatabaseError(f"Batch save failed: {e}") from e

    def _save_batch_with_retry(self, entities: list[Entity]) -> list[Entity]:
        """Save entities individually, handling duplicates by lookup.

        Used as fallback when batch save fails due to race condition.

        Args:
            entities: List of entities to save

        Returns:
            List of saved/found entities
        """
        from sqlalchemy.exc import IntegrityError

        saved_entities: list[Entity] = []

        for entity in entities:
            try:
                # Try to save individually
                encrypted_entity = self._encrypt_entity(entity)
                self._session.add(encrypted_entity)
                self._session.commit()
                self._session.refresh(encrypted_entity)
                saved_entities.append(self._decrypt_entity(encrypted_entity))

            except IntegrityError:
                # Entity already exists (race condition) - look it up by its
                # text and type (Story 10.7): a row of the same text under
                # another type does not stop this one from being saved
                self._session.rollback()
                existing = self.find_by_full_name_and_type(
                    entity.full_name, entity.entity_type
                )
                if existing:
                    saved_entities.append(existing)
                else:
                    # Unexpected: integrity error but entity not found
                    # Re-raise as this shouldn't happen
                    raise DatabaseError(
                        f"Race condition but entity not found: {entity.full_name}"
                    )

        return saved_entities

    def find_all(
        self,
        entity_type: str | None = None,
        is_ambiguous: bool | None = None,
    ) -> list[Entity]:
        """Query entities with optional filters.

        Args:
            entity_type: Filter by entity type (PERSON, LOCATION, ORG)
            is_ambiguous: Filter by ambiguity flag

        Returns:
            List of entities with decrypted fields

        Example:
            >>> # Get all ambiguous persons
            >>> entities = repo.find_all(entity_type="PERSON", is_ambiguous=True)
        """
        query = self._session.query(Entity)

        # Apply filters
        if entity_type is not None:
            query = query.filter(Entity.entity_type == entity_type)
        if is_ambiguous is not None:
            query = query.filter(Entity.is_ambiguous == is_ambiguous)

        db_entities = query.all()

        # Decrypt and return
        return [self._decrypt_entity(e) for e in db_entities]

    def delete_entities_by_full_name(self, full_name: str) -> list[Entity]:
        """Delete every entity stored for an encrypted full name, in one transaction.

        Args:
            full_name: Plaintext full name of the entities to delete

        Returns:
            Decrypted entities that were deleted, ordered by type (empty list
            if none)

        Raises:
            DatabaseError: If database operation fails (nothing is deleted)
        """
        from sqlalchemy.exc import OperationalError

        db_entities = self._query_by_full_name(full_name)
        if not db_entities:
            return []

        # Decrypt before deletion (needed for audit log / confirmation)
        decrypted = [self._decrypt_entity(e) for e in db_entities]

        try:
            for db_entity in db_entities:
                self._session.delete(db_entity)
            self._session.commit()
        except OperationalError as e:
            self._session.rollback()
            raise DatabaseError(f"Failed to delete entity: {e}") from e

        return decrypted

    def delete_entities_by_full_name_any_capitals(self, full_name: str) -> list[Entity]:
        """Delete every entity stored for a plaintext full name, whatever its
        type or its capitals, in one transaction (Story 10.19, AC4).

        The rows are those of ``find_all_by_full_name_any_capitals``.

        Args:
            full_name: Plaintext full name of the entities to delete

        Returns:
            Decrypted entities that were deleted (empty list if none)

        Raises:
            DatabaseError: If database operation fails (nothing is deleted)
        """
        from sqlalchemy.exc import OperationalError

        db_entities = self._query_by_full_name_any_capitals(full_name)
        if not db_entities:
            return []

        # Decrypt before deletion (needed for audit log / confirmation)
        decrypted = [self._decrypt_entity(e) for e in db_entities]

        try:
            for db_entity in db_entities:
                self._session.delete(db_entity)
            self._session.commit()
        except OperationalError as e:
            self._session.rollback()
            raise DatabaseError(f"Failed to delete entity: {e}") from e

        return decrypted

    def delete_entity_by_id(self, entity_id: str) -> Entity | None:
        """Delete entity by UUID.

        Args:
            entity_id: UUID of entity to delete

        Returns:
            Decrypted entity that was deleted, or None if not found

        Raises:
            DatabaseError: If database operation fails
        """
        from sqlalchemy.exc import OperationalError

        db_entity = self._session.query(Entity).filter(Entity.id == entity_id).first()

        if not db_entity:
            return None

        decrypted = self._decrypt_entity(db_entity)

        try:
            self._session.delete(db_entity)
            self._session.commit()
        except OperationalError as e:
            self._session.rollback()
            raise DatabaseError(f"Failed to delete entity: {e}") from e

        return decrypted

    def search_entities(
        self,
        search_term: str | None = None,
        entity_type: str | None = None,
    ) -> list[Entity]:
        """Search entities with optional name and type filters.

        Decrypts all entities then applies case-insensitive substring filtering
        on the decrypted names (same pattern as list_mappings.py).

        Args:
            search_term: Case-insensitive substring to match against entity names
            entity_type: Filter by entity type (PERSON, LOCATION, ORG)

        Returns:
            List of matching decrypted entities
        """
        # Use find_all for base query with type filter
        entities = self.find_all(entity_type=entity_type)

        # Apply search filter on decrypted names, both sides composed (Story
        # 10.20): a row saved with separate accent marks is found too, and
        # (v1.10) a row an earlier version cut or kept a title in, through
        # the texts it may stand for (``matches_search``)
        if search_term:
            search_lower = composed(search_term).lower()
            entities = [
                e
                for e in entities
                if matches_search(search_lower, e.full_name, e.entity_type)
                or search_lower in composed(e.pseudonym_full).lower()
            ]

        return entities

    def _encrypt_entity(self, entity: Entity) -> Entity:
        """Create encrypted copy of entity for database storage.

        Args:
            entity: Entity with plaintext fields

        Returns:
            New Entity instance with encrypted sensitive fields
        """
        # Create new instance to avoid modifying original
        encrypted = Entity(
            id=entity.id,
            entity_type=entity.entity_type,
            # Encrypt sensitive fields
            first_name=self._encryption.encrypt(entity.first_name),
            last_name=self._encryption.encrypt(entity.last_name),
            full_name=self._encryption.encrypt(entity.full_name),
            pseudonym_first=self._encryption.encrypt(entity.pseudonym_first),
            pseudonym_last=self._encryption.encrypt(entity.pseudonym_last),
            pseudonym_full=self._encryption.encrypt(entity.pseudonym_full),
            # Copy metadata fields unchanged
            first_seen_timestamp=entity.first_seen_timestamp,
            gender=entity.gender,
            confidence_score=entity.confidence_score,
            theme=entity.theme,
            is_ambiguous=entity.is_ambiguous,
            ambiguity_reason=entity.ambiguity_reason,
        )
        return encrypted

    def _decrypt_entity(self, encrypted_entity: Entity) -> Entity:
        """Decrypt entity fields for application use.

        Args:
            encrypted_entity: Entity from database with encrypted fields

        Returns:
            Entity with decrypted plaintext fields
        """
        # Decrypt sensitive fields
        decrypted = Entity(
            id=encrypted_entity.id,
            entity_type=encrypted_entity.entity_type,
            # Decrypt sensitive fields
            first_name=self._encryption.decrypt(encrypted_entity.first_name),
            last_name=self._encryption.decrypt(encrypted_entity.last_name),
            full_name=self._encryption.decrypt(encrypted_entity.full_name),
            pseudonym_first=self._encryption.decrypt(encrypted_entity.pseudonym_first),
            pseudonym_last=self._encryption.decrypt(encrypted_entity.pseudonym_last),
            pseudonym_full=self._encryption.decrypt(encrypted_entity.pseudonym_full),
            # Copy metadata fields unchanged
            first_seen_timestamp=encrypted_entity.first_seen_timestamp,
            gender=encrypted_entity.gender,
            confidence_score=encrypted_entity.confidence_score,
            theme=encrypted_entity.theme,
            is_ambiguous=encrypted_entity.is_ambiguous,
            ambiguity_reason=encrypted_entity.ambiguity_reason,
        )
        return decrypted
