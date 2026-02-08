"""Validation workflow orchestration.

This module coordinates the human-in-the-loop validation process,
managing the flow between entity detection, user review, and
pseudonym assignment.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.pseudonym.assignment_engine import FRENCH_TITLE_PATTERN
from gdpr_pseudonymizer.validation.context_precomputer import ContextPrecomputer
from gdpr_pseudonymizer.validation.models import ValidationSession
from gdpr_pseudonymizer.validation.ui import (
    FinalConfirmationScreen,
    HelpOverlay,
    ReviewScreen,
    SummaryScreen,
    display_info_message,
    display_warning_message,
    get_confirmation,
    get_text_input,
    get_user_action,
)


class ValidationWorkflow:
    """Orchestrates the multi-step validation workflow."""

    def __init__(self) -> None:
        """Initialize validation workflow with UI components."""
        self.summary_screen = SummaryScreen()
        self.review_screen = ReviewScreen()
        self.final_screen = FinalConfirmationScreen()
        self.help_overlay = HelpOverlay()
        self.context_precomputer = ContextPrecomputer(context_words=10)

    def run(
        self,
        entities: list[DetectedEntity],
        document_text: str,
        document_path: str = "",
        pseudonym_assigner: Callable[[DetectedEntity], str] | None = None,
    ) -> list[DetectedEntity]:
        """Execute the validation workflow.

        Args:
            entities: List of detected entities to validate
            document_text: Full document text
            document_path: Path to document being validated
            pseudonym_assigner: Function to assign pseudonyms (optional)

        Returns:
            List of validated entities after user review

        Raises:
            KeyboardInterrupt: If user cancels validation with Ctrl+C
        """
        # Handle empty entity list
        if not entities:
            display_info_message("No entities detected in document.")
            if get_confirmation("Would you like to manually add entities?"):
                # Allow manual entity addition
                return self._manual_entity_addition_flow(document_text, document_path)
            return []

        # Handle large entity count warning
        if len(entities) >= 100:
            display_warning_message(
                f"Large document detected: {len(entities)} entities. "
                f"Validation may take {(len(entities) * 6) // 60} minutes."
            )
            if not get_confirmation("Continue with validation?"):
                raise KeyboardInterrupt("User cancelled validation")

        # Create validation session
        session = ValidationSession(
            document_path=document_path,
            document_text=document_text,
        )

        # Add entities to session
        for entity in entities:
            session.add_entity(entity)

        # Precompute context snippets for performance
        session.context_cache = self.context_precomputer.precompute_all(
            document_text, entities
        )

        # Step 1: Display summary screen with unique entity count
        self._display_summary(entities, session)

        # Step 2: Review entities by type (PERSON → ORG → LOCATION)
        try:
            self._review_entities_by_type(session, pseudonym_assigner)
        except KeyboardInterrupt as e:
            # If this was an intentional quit (from Q key), don't prompt again
            if str(e) == "User quit validation":
                raise
            # For Ctrl+C, prompt for confirmation
            if get_confirmation("Quit validation? Progress will be lost."):
                raise
            # Continue if user cancels quit
            return self.run(entities, document_text, document_path, pseudonym_assigner)

        # Step 3: Ambiguous entities are handled during review

        # Step 4: Display final confirmation
        summary_stats = session.get_summary_stats()
        self.final_screen.display(summary_stats)

        if not get_confirmation("Ready to process document with validated entities?"):
            display_info_message("Validation cancelled. Returning to review.")
            # Restart validation workflow
            return self.run(entities, document_text, document_path, pseudonym_assigner)

        # Step 5: Return validated entities
        validated_entities = session.get_validated_entities()
        display_info_message(
            f"Validation complete. Processing {len(validated_entities)} entities."
        )

        return validated_entities

    def _display_summary(
        self, entities: list[DetectedEntity], session: ValidationSession | None = None
    ) -> None:
        """Display summary screen with entity statistics.

        Args:
            entities: List of detected entities
            session: Optional validation session for unique entity count
        """
        # Count entities by type
        entity_counts: dict[str, int] = defaultdict(int)
        for entity in entities:
            entity_counts[entity.entity_type] += 1

        # Get unique entity count if session provided
        unique_count = None
        if session:
            unique_count = len(session.get_entity_groups())

        # Display summary
        self.summary_screen.display(len(entities), dict(entity_counts), unique_count)
        self.summary_screen.wait_for_enter()

    def _review_entities_by_type(
        self,
        session: ValidationSession,
        pseudonym_assigner: Callable[[DetectedEntity], str] | None = None,
    ) -> None:
        """Review entities by type in priority order using entity groups.

        Args:
            session: Validation session with entities
            pseudonym_assigner: Function to assign pseudonyms (optional)
        """
        # Review in priority order: PERSON → ORG → LOCATION
        priority_order = ["PERSON", "ORG", "LOCATION"]

        for entity_type in priority_order:
            # Get entity groups for this type
            entity_groups = session.get_entity_groups(entity_type)

            if not entity_groups:
                continue

            # Calculate total occurrences for display
            total_occurrences = sum(group.count for group in entity_groups)
            display_info_message(
                f"Reviewing {entity_type} entities "
                f"({total_occurrences} occurrences, {len(entity_groups)} unique)"
            )

            # Review each entity group
            group_index = 0
            while group_index < len(entity_groups):
                group = entity_groups[group_index]

                # Inner loop for context cycling within a group
                while True:
                    # Get representative entity for current context
                    current_entity = group.get_representative_entity()

                    # Get context and pseudonym
                    context = self.context_precomputer.get_context_for_entity(
                        current_entity, session.context_cache
                    )
                    pseudonym = self._get_pseudonym(current_entity, pseudonym_assigner)

                    # Display ambiguous warning if needed
                    if current_entity.is_ambiguous:
                        reason = self._get_ambiguity_reason(current_entity)
                        self.review_screen.display_ambiguous_warning(
                            current_entity, reason
                        )

                    # Display entity group for review
                    self.review_screen.display_entity(
                        current_entity,
                        context,
                        pseudonym,
                        group_index + 1,
                        len(entity_groups),
                        entity_type,
                        occurrence_count=group.count,
                        context_index=group.current_context_index + 1,
                    )

                    # Get user action
                    action = get_user_action()

                    # Handle context cycling for groups
                    if action == "expand_context" and group.count > 1:
                        group.cycle_context()
                        continue  # Redisplay with new context

                    # Handle other actions - apply to ALL occurrences in group
                    if action == "confirm":
                        for entity in group.occurrences:
                            session.mark_confirmed(entity)
                        group_index += 1
                        break  # Exit inner loop, move to next group

                    elif action == "reject":
                        for entity in group.occurrences:
                            session.mark_rejected(entity)
                        group_index += 1
                        break

                    elif action == "modify":
                        new_text = get_text_input("Enter corrected entity text")
                        if new_text and new_text != current_entity.text:
                            # Apply modification to all occurrences in group
                            for entity in group.occurrences:
                                modified_entity = DetectedEntity(
                                    text=new_text,
                                    entity_type=entity.entity_type,
                                    start_pos=entity.start_pos,
                                    end_pos=entity.end_pos,
                                    confidence=entity.confidence,
                                    gender=entity.gender,
                                    is_ambiguous=False,
                                )
                                session.mark_modified(entity, modified_entity)
                        else:
                            for entity in group.occurrences:
                                session.mark_confirmed(entity)
                        group_index += 1
                        break

                    elif action == "change_pseudonym":
                        new_pseudonym = get_text_input("Enter custom pseudonym")
                        if new_pseudonym:
                            # Apply custom pseudonym to all occurrences in group
                            for entity in group.occurrences:
                                session.change_pseudonym(entity, new_pseudonym)
                        else:
                            for entity in group.occurrences:
                                session.mark_confirmed(entity)
                        group_index += 1
                        break

                    elif action == "add":
                        self._handle_add_entity(session)
                        # Don't advance index, stay on current group
                        break

                    elif action == "next":
                        if group_index < len(entity_groups) - 1:
                            group_index += 1
                        else:
                            display_info_message("Already at last entity of this type")
                        break

                    elif action == "previous":
                        if group_index > 0:
                            group_index -= 1
                        else:
                            display_info_message("Already at first entity of this type")
                        break

                    elif action == "help":
                        self.help_overlay.display()
                        # Stay on current group, redisplay
                        continue

                    elif action == "quit":
                        # Print newline to reset terminal after readchar
                        print()
                        if get_confirmation("Quit validation? Progress will be lost."):
                            raise KeyboardInterrupt("User quit validation")
                        # Continue if cancelled
                        continue

                    elif action == "batch_accept":
                        # Print newline to reset terminal after readchar
                        print()
                        if get_confirmation(
                            f"Accept all {len(entity_groups)} unique {entity_type} entities "
                            f"({total_occurrences} total occurrences)?"
                        ):
                            # Accept all groups
                            for eg in entity_groups:
                                for e in eg.occurrences:
                                    if e not in [
                                        d.original_entity
                                        for d in session.user_decisions
                                    ]:
                                        session.mark_confirmed(e)
                            display_info_message(f"Accepted all {entity_type} entities")
                            # Exit current entity type review, continue to next type
                            group_index = len(entity_groups)  # Force exit of group loop
                            break
                        break  # Exit group if confirmation cancelled

                    elif action == "batch_reject":
                        # Print newline to reset terminal after readchar
                        print()
                        if get_confirmation(
                            f"Reject all {len(entity_groups)} unique {entity_type} entities "
                            f"({total_occurrences} total occurrences)?"
                        ):
                            # Reject all groups
                            for eg in entity_groups:
                                for e in eg.occurrences:
                                    if e not in [
                                        d.original_entity
                                        for d in session.user_decisions
                                    ]:
                                        session.mark_rejected(e)
                            display_info_message(f"Rejected all {entity_type} entities")
                            # Exit current entity type review, continue to next type
                            group_index = len(entity_groups)  # Force exit of group loop
                            break
                        break  # Exit group if confirmation cancelled

                    elif action == "invalid":
                        display_warning_message("Invalid key. Press H for help.")
                        continue

    def _get_pseudonym(
        self,
        entity: DetectedEntity,
        pseudonym_assigner: Callable[[DetectedEntity], str] | None,
    ) -> str:
        """Get pseudonym for entity, preserving title prefixes.

        For PERSON entities, extracts any French title prefix (M., Mme, Maître, etc.)
        from the original text and prepends it to the pseudonym.

        Args:
            entity: Entity to get pseudonym for
            pseudonym_assigner: Optional function to assign pseudonyms

        Returns:
            Assigned pseudonym with preserved title prefix, or placeholder
        """
        if pseudonym_assigner:
            base_pseudonym = pseudonym_assigner(entity)

            # Preserve title prefix for PERSON entities
            if entity.entity_type == "PERSON":
                title_match = re.match(FRENCH_TITLE_PATTERN, entity.text, re.IGNORECASE)
                if title_match:
                    title_prefix = title_match.group(0).rstrip()
                    return f"{title_prefix} {base_pseudonym}"

            return base_pseudonym
        else:
            # Placeholder pseudonym if no assigner provided
            return f"[{entity.entity_type}_{entity.text[:10]}]"

    def _get_ambiguity_reason(self, entity: DetectedEntity) -> str:
        """Get reason for entity ambiguity.

        Args:
            entity: Ambiguous entity

        Returns:
            Human-readable ambiguity reason
        """
        if entity.confidence is not None and entity.confidence < 0.6:
            return "Low confidence score from NLP model"
        elif " " in entity.text and len(entity.text.split()) == 1:
            return "Partial compound name detected"
        else:
            return "Entity flagged as ambiguous by detection algorithm"

    def _handle_add_entity(self, session: ValidationSession) -> None:
        """Handle manual entity addition flow.

        Args:
            session: Validation session to add entity to
        """
        display_info_message("Add manual entity")

        entity_text = get_text_input("Entity text")
        if not entity_text:
            display_warning_message("Entity text cannot be empty")
            return

        entity_type = get_text_input("Entity type (PERSON/LOCATION/ORG)").upper()
        if entity_type not in ["PERSON", "LOCATION", "ORG"]:
            display_warning_message("Invalid entity type")
            return

        # Find position in document
        start_pos = session.document_text.find(entity_text)
        if start_pos == -1:
            display_warning_message(f"'{entity_text}' not found in document")
            return

        end_pos = start_pos + len(entity_text)

        # Create new entity
        new_entity = DetectedEntity(
            text=entity_text,
            entity_type=entity_type,
            start_pos=start_pos,
            end_pos=end_pos,
            confidence=None,
            gender=None,
            is_ambiguous=False,
        )

        session.add_manual_entity(new_entity)
        display_info_message(f"Added {entity_type} entity: {entity_text}")

    def _manual_entity_addition_flow(
        self, document_text: str, document_path: str
    ) -> list[DetectedEntity]:
        """Handle manual entity addition when no entities detected.

        Args:
            document_text: Full document text
            document_path: Path to document

        Returns:
            List of manually added entities
        """
        session = ValidationSession(
            document_path=document_path,
            document_text=document_text,
        )

        display_info_message("Manual entity addition mode")

        while True:
            self._handle_add_entity(session)

            if not get_confirmation("Add another entity?"):
                break

        return session.get_validated_entities()


def create_validation_session(
    document_path: str, document_text: str, entities: list[DetectedEntity]
) -> ValidationSession:
    """Create validation session from detected entities.

    Args:
        document_path: Path to document being validated
        document_text: Full document text
        entities: List of entities detected by NLP engine

    Returns:
        Initialized ValidationSession with precomputed context
    """
    session = ValidationSession(
        document_path=document_path, document_text=document_text
    )

    for entity in entities:
        session.add_entity(entity)

    # Precompute context snippets
    precomputer = ContextPrecomputer(context_words=10)
    session.context_cache = precomputer.precompute_all(document_text, entities)

    return session


def run_validation_workflow(
    entities: list[DetectedEntity],
    document_text: str,
    document_path: str = "",
    pseudonym_assigner: Callable[[DetectedEntity], str] | None = None,
) -> list[DetectedEntity]:
    """Execute interactive validation workflow.

    This is the main entry point for running the validation workflow.

    Args:
        entities: List of detected entities to validate
        document_text: Full document text
        document_path: Path to document being validated (optional)
        pseudonym_assigner: Function to assign pseudonyms (optional)

    Returns:
        List of validated entities after user review

    Raises:
        KeyboardInterrupt: If user cancels validation
    """
    workflow = ValidationWorkflow()
    return workflow.run(entities, document_text, document_path, pseudonym_assigner)
