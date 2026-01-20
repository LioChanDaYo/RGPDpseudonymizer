"""Context snippet precomputation for validation workflow.

This module precomputes context snippets (surrounding text) for detected entities
to enable fast display during validation without repeated text processing.
"""

from __future__ import annotations

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity


class ContextPrecomputer:
    """Precomputes and caches context snippets for entities."""

    def __init__(self, context_words: int = 10) -> None:
        """Initialize context precomputer.

        Args:
            context_words: Number of words to include before/after entity
        """
        self.context_words = context_words

    def extract_context(self, document_text: str, entity: DetectedEntity) -> str:
        """Extract context snippet for an entity.

        Gets N words before and after the entity, with the entity highlighted.

        Args:
            document_text: Full document text
            entity: Entity to extract context for

        Returns:
            Context snippet with entity highlighted
        """
        # Get text before and after entity
        text_before = document_text[: entity.start_pos]
        entity_text = document_text[entity.start_pos : entity.end_pos]
        text_after = document_text[entity.end_pos :]

        # Extract N words before
        words_before = text_before.split()
        context_before = " ".join(words_before[-self.context_words :])

        # Extract N words after
        words_after = text_after.split()
        context_after = " ".join(words_after[: self.context_words])

        # Build context with highlighted entity
        context_parts = []

        if context_before:
            context_parts.append(f"...{context_before}")

        # Highlight entity
        context_parts.append(f"[bold cyan]{entity_text}[/bold cyan]")

        if context_after:
            context_parts.append(f"{context_after}...")

        return " ".join(context_parts)

    def precompute_all(
        self, document_text: str, entities: list[DetectedEntity]
    ) -> dict[str, str]:
        """Precompute context snippets for all entities.

        Args:
            document_text: Full document text
            entities: List of detected entities

        Returns:
            Dictionary mapping entity text to context snippet
        """
        context_cache = {}

        for entity in entities:
            # Use entity position as key to handle duplicate entity text
            cache_key = f"{entity.text}_{entity.start_pos}"
            context_cache[cache_key] = self.extract_context(document_text, entity)

        return context_cache

    def get_context_for_entity(
        self, entity: DetectedEntity, context_cache: dict[str, str]
    ) -> str:
        """Get precomputed context for an entity.

        Args:
            entity: Entity to get context for
            context_cache: Precomputed context cache

        Returns:
            Context snippet, or empty string if not found
        """
        cache_key = f"{entity.text}_{entity.start_pos}"
        return context_cache.get(cache_key, "")
