"""Repository interface and implementation for entity mapping persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

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
    def find_by_component(self, component: str, component_type: str) -> List[Entity]:
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
    def save_batch(self, entities: List[Entity]) -> List[Entity]:
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
    ) -> List[Entity]:
        """Query entities with optional filters.

        Args:
            entity_type: Filter by entity type (PERSON, LOCATION, ORG)
            is_ambiguous: Filter by ambiguity flag

        Returns:
            List of entities matching filters
        """
        pass


class SQLiteMappingRepository(MappingRepository):
    """SQLite implementation of MappingRepository interface.

    This is a minimal stub implementation. Full implementation will be completed
    in Epic 2 with encryption support and comprehensive querying.
    """

    def __init__(self, db_path: str) -> None:
        """Initialize repository with database path.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

    def find_by_full_name(self, full_name: str) -> Entity | None:
        """Find entity by full name (stub implementation).

        Args:
            full_name: Complete entity name to search for

        Returns:
            None (stub implementation)
        """
        # Stub: Full implementation in Epic 2
        return None

    def find_by_component(self, component: str, component_type: str) -> List[Entity]:
        """Find entities by name component (stub implementation).

        Args:
            component: Name component to search for
            component_type: Type of component

        Returns:
            Empty list (stub implementation)
        """
        # Stub: Full implementation in Epic 2
        return []

    def save(self, entity: Entity) -> Entity:
        """Save entity (stub implementation).

        Args:
            entity: Entity to save

        Returns:
            Entity unchanged (stub implementation)
        """
        # Stub: Full implementation in Epic 2
        return entity

    def save_batch(self, entities: List[Entity]) -> List[Entity]:
        """Save multiple entities (stub implementation).

        Args:
            entities: Entities to save

        Returns:
            Entities unchanged (stub implementation)
        """
        # Stub: Full implementation in Epic 2
        return entities

    def find_all(
        self,
        entity_type: str | None = None,
        is_ambiguous: bool | None = None,
    ) -> List[Entity]:
        """Query all entities (stub implementation).

        Args:
            entity_type: Entity type filter
            is_ambiguous: Ambiguity filter

        Returns:
            Empty list (stub implementation)
        """
        # Stub: Full implementation in Epic 2
        return []
