"""Repository interface and implementation for entity mapping persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

from gdpr_pseudonymizer.core.mapping_key import saved_name_forms, search_forms
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.exceptions import DatabaseError, DuplicateEntityError
from gdpr_pseudonymizer.utils.text_form import composed

# The types a name is looked up under, for its forms (Story 10.20): only a
# LOCATION has forms of its own (its prepositions); every other type has a
# PERSON's.
_FORM_TYPES = ("PERSON", "LOCATION")


def _form_type(entity_type: str) -> str:
    """The type whose forms a row of ``entity_type`` is compared with."""
    return "LOCATION" if entity_type == "LOCATION" else "PERSON"


def _name_forms(full_name: str, entity_type: str) -> list[str]:
    """Every text a row of this name and type may hold (Story 10.20, Lionel's
    Qa and Qb; v1.7, ``saved_name_forms``), in the order a lookup prefers
    them: the composed name first."""
    return saved_name_forms(full_name, entity_type)


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
        # (v1.5) a row an earlier version saved with letters lost, through
        # the search's former forms for the row's type (``search_forms``)
        if search_term:
            search_lower = composed(search_term).lower()
            forms = {kind: search_forms(search_term, kind) for kind in _FORM_TYPES}
            entities = [
                e
                for e in entities
                if any(
                    form in composed(e.full_name).lower()
                    for form in forms[_form_type(e.entity_type)]
                )
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
