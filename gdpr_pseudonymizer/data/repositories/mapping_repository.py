"""Repository interface and implementation for entity mapping persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

from gdpr_pseudonymizer.data.models import Entity


class MappingRepository(ABC):
    """Abstract interface for entity mapping persistence.

    This interface defines the contract for storing and retrieving entity mappings.
    Implementations must handle encryption/decryption transparently.
    """

    @abstractmethod
    def find_by_full_name(self, full_name: str) -> Entity | None:
        """Find existing entity by full name for idempotency.

        Args:
            full_name: Complete entity name to search for

        Returns:
            Entity if found, None otherwise
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


class SQLiteMappingRepository(MappingRepository):
    """SQLite implementation of MappingRepository with column-level encryption.

    Transparently handles encryption/decryption of sensitive fields using
    DatabaseSession's EncryptionService. Leverages AES-256-SIV deterministic
    encryption for queryable encrypted fields.
    """

    def __init__(self, db_session: "DatabaseSession") -> None:  # type: ignore  # noqa: F821
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

    def find_by_full_name(self, full_name: str) -> Entity | None:
        """Find entity by encrypted full name.

        Args:
            full_name: Plaintext full name to search for

        Returns:
            Entity with decrypted fields, or None if not found

        Example:
            >>> entity = repo.find_by_full_name("Marie Dubois")
            >>> print(entity.full_name)  # "Marie Dubois" (decrypted)
        """
        # Encrypt search term for deterministic lookup
        encrypted_full_name = self._encryption.encrypt(full_name)

        # Query by encrypted field
        db_entity = (
            self._session.query(Entity)
            .filter(Entity.full_name == encrypted_full_name)
            .first()
        )

        if not db_entity:
            return None

        # Decrypt and return
        return self._decrypt_entity(db_entity)

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

        # Encrypt search term
        encrypted_component = self._encryption.encrypt(component)

        # Query by encrypted component field
        if component_type == "first_name":
            db_entities = (
                self._session.query(Entity)
                .filter(Entity.first_name == encrypted_component)
                .all()
            )
        else:  # last_name
            db_entities = (
                self._session.query(Entity)
                .filter(Entity.last_name == encrypted_component)
                .all()
            )

        # Decrypt and return
        return [self._decrypt_entity(e) for e in db_entities]

    def save(self, entity: Entity) -> Entity:
        """Persist entity with encrypted sensitive fields.

        Args:
            entity: Entity with plaintext fields

        Returns:
            Saved entity with plaintext fields and generated ID

        Raises:
            DuplicateEntityError: If entity with same full_name exists
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
        """Persist multiple entities in single transaction.

        Args:
            entities: List of entities with plaintext fields

        Returns:
            List of saved entities with plaintext fields

        Raises:
            DatabaseError: If batch operation fails (transaction rolled back)

        Note:
            All-or-nothing semantics: if any entity fails, entire batch rolled back.

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

        except (IntegrityError, OperationalError) as e:
            self._session.rollback()
            raise DatabaseError(f"Batch save failed: {e}") from e

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


class DuplicateEntityError(Exception):
    """Raised when attempting to save entity with duplicate full_name."""

    pass


class DatabaseError(Exception):
    """Raised when database operation fails."""

    pass
