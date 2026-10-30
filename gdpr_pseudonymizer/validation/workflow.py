"""Validation workflow orchestration.

This module coordinates the human-in-the-loop validation process,
managing the flow between entity detection, user review, and
pseudonym assignment.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import replace

from gdpr_pseudonymizer.core.custom_pseudonym import (
    NameKey,
    PseudonymChecker,
    cli_refusal_message,
    normalize_custom_pseudonym,
)
from gdpr_pseudonymizer.core.mapping_key import mapping_key
from gdpr_pseudonymizer.exceptions import NoAnswerError
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.utils.french_patterns import FRENCH_TITLE_PATTERN
from gdpr_pseudonymizer.utils.text_form import is_mark
from gdpr_pseudonymizer.validation.context_precomputer import ContextPrecomputer
from gdpr_pseudonymizer.validation.models import (
    CORRECTED_BY_HAND_SOURCE,
    EntityGroup,
    EntityReviewState,
    ValidationSession,
    fold,
    is_form,
    whole_word_places,
)
from gdpr_pseudonymizer.validation.ui import (
    FinalConfirmationScreen,
    HelpOverlay,
    ReviewScreen,
    SummaryScreen,
    display_info_message,
    display_success_message,
    display_warning_message,
    get_confirmation,
    get_text_input,
    get_user_action,
)

# Story 10.19 (v1.19; the fifth Codex review's P0-1, "fix the class, not the
# case"): a word is read by what it is, not by the characters that end it:
# letters and accent marks, with a hyphen or an apostrophe only when a letter
# follows it (« Testar-Brimel », the elision « D'Émerine »). Anything else
# ends it: an ellipsis, a dash, a slash, a quotation mark of any kind, a
# bracket, a comma, a full stop, a guillemet, a digit.
_WORD_JOINERS = frozenset("-\u2010\u2011'\u2019")


def _next_word(text: str, position: int) -> tuple[int, int] | None:
    """The (start, end) of the word written after the whitespace at
    ``position`` (at least one whitespace character, a line break included),
    or None when no word starts there."""
    at = position
    if at >= len(text) or not text[at].isspace():
        return None
    while at < len(text) and text[at].isspace():
        at += 1
    start = at
    if at >= len(text) or not text[at].isalpha():
        return None
    at += 1
    while at < len(text):
        char = text[at]
        if char.isalpha() or is_mark(char):
            at += 1
        elif char in _WORD_JOINERS and at + 1 < len(text) and text[at + 1].isalpha():
            at += 1
        else:
            break
    return start, at


# Story 10.15 (AC14 (e), Lionel's approved Q2 text): [A] of a name whose every
# place is already in the review. %1 is the text typed, %2 the type typed.
ALREADY_IN_REVIEW_LINE = (
    "'%1' is already in the review as %2 at every place: nothing added"
)

# Story 10.18 (Lionel's approved texts, Q1, Q4 and Q5, 2026-10-16), each on
# one line so that it can be checked byte for byte. ``display_info_message``
# gives the lines their « ℹ️  », ``Confirm.ask`` gives the question its
# « [y/n]: », and ``_sanitize_error_message`` gives the error its
# "NoAnswerError: ".
NO_NAMES_FOUND_LINE = "No names were found in this document."
NO_NEW_NAMES_LINE = (
    "No new names to review: every name found is already in your mapping database."
)
SELECTED_NO_NAMES_FOUND_LINE = (
    "No names of the selected types were found in this document."
)
SELECTED_NO_NEW_NAMES_LINE = "No new names of the selected types to review: every one found is already in your mapping database."
ADD_MISSED_NAME_QUESTION = "Add a name the detector missed before the file is written?"
NO_ANSWER_TEXT = "No answer could be read, so this document was not processed: the command line must ask whether to add a name the detector missed. Run it in a terminal to answer. No output was written for this file."


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
        pseudonym_checker: PseudonymChecker | None = None,
        custom_pseudonyms: dict[NameKey, str] | None = None,
        sent_without_review: list[DetectedEntity] | None = None,
        cells: dict[str, str] | None = None,
    ) -> list[DetectedEntity]:
        """Execute the validation workflow.

        Args:
            entities: List of detected entities to validate
            document_text: Full document text
            document_path: Path to document being validated
            pseudonym_assigner: Function to assign pseudonyms (optional)
            pseudonym_checker: Checks a custom pseudonym set with [C]
                (Story 10.11; optional)
            custom_pseudonyms: When given, filled at the end with the custom
                pseudonyms of the names sent, keyed by (mapping key, type)
                (Story 10.11; optional)
            sent_without_review: Known entities written without review, included
                in Story 10.13 coverage per Lionel's decision of 2026-10-16.
            cells: Cell reference -> cell text of a spreadsheet, whose
                entities' positions point into their cells (Story 10.15);
                None for a text document.

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
                return self._manual_entity_addition_flow(
                    document_text, document_path, cells=cells
                )
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
            cell_texts=dict(cells or {}),
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
            self._review_entities_by_type(
                session, pseudonym_assigner, pseudonym_checker
            )
        except KeyboardInterrupt as e:
            # If this was an intentional quit (from Q key), don't prompt again
            if str(e) == "User quit validation":
                raise
            # For Ctrl+C, prompt for confirmation
            if get_confirmation("Quit validation? Progress will be lost."):
                raise
            # Continue if user cancels quit
            return self.run(
                entities,
                document_text,
                document_path,
                pseudonym_assigner,
                pseudonym_checker,
                custom_pseudonyms,
                sent_without_review=sent_without_review,
                cells=cells,
            )

        # Step 3: Ambiguous entities are handled during review

        # Step 4: Display final confirmation
        summary_stats = session.get_summary_stats()
        # Story 10.13: count pending names that finalization leaves in clear.
        still_to_review = session.names_left_in_clear(
            sent_without_review=sent_without_review or []
        )
        self.final_screen.display(summary_stats, still_to_review=still_to_review)

        if not get_confirmation("Ready to process document with validated entities?"):
            display_info_message("Validation cancelled. Returning to review.")
            # Restart validation workflow
            return self.run(
                entities,
                document_text,
                document_path,
                pseudonym_assigner,
                pseudonym_checker,
                custom_pseudonyms,
                sent_without_review=sent_without_review,
                cells=cells,
            )

        # Step 5: Return validated entities (and, Story 10.11, the custom
        # pseudonyms of the names sent)
        validated_entities = session.get_validated_entities()
        if custom_pseudonyms is not None:
            custom_pseudonyms.clear()
            custom_pseudonyms.update(session.get_custom_pseudonyms())
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
        pseudonym_checker: PseudonymChecker | None = None,
    ) -> None:
        """Review entities by type in priority order using entity groups.

        Args:
            session: Validation session with entities
            pseudonym_assigner: Function to assign pseudonyms (optional)
            pseudonym_checker: Checks a custom pseudonym set with [C]
                (Story 10.11; optional)
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
                    # Get canonical entity for display and context entity for snippet
                    current_entity = group.get_representative_entity()
                    context_entity = group.get_current_context_entity()

                    # Get context from current cycling entity, pseudonym from canonical
                    context = self.context_precomputer.get_context_for_entity(
                        context_entity, session.context_cache
                    )
                    # Story 10.11 (PO R9): the group's custom pseudonym, with
                    # the title prefix a suggestion has, in place of the
                    # suggestion
                    custom = self._group_custom_pseudonym(session, group)
                    pseudonym = (
                        self._with_title(current_entity, custom)
                        if custom
                        else self._get_pseudonym(current_entity, pseudonym_assigner)
                    )

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
                        variant_texts=(
                            group.non_canonical_variants if group.has_variants else None
                        ),
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
                            # Apply modification to all occurrences in group.
                            # Story 10.15: each is located in the text its
                            # positions point into (its own cell on a
                            # spreadsheet) and keeps its cell. Every place
                            # the correction reaches is a place the user
                            # typed (v1.4/v1.5), widened over a name it
                            # partly overlaps before the document is written.
                            # Story 10.19 (QA's CAPS-001; the orchestrator's
                            # ruling): in a joined group, the places the
                            # correction does not reach come back to the
                            # review right after this group.
                            sent_back = self._apply_correction(session, group, new_text)
                            entity_groups[group_index + 1 : group_index + 1] = sent_back
                        else:
                            for entity in group.occurrences:
                                session.mark_confirmed(entity)
                        group_index += 1
                        break

                    elif action == "change_pseudonym":
                        new_pseudonym = get_text_input("Enter custom pseudonym")
                        pseudonym = (
                            normalize_custom_pseudonym(
                                new_pseudonym, current_entity.entity_type
                            )
                            if new_pseudonym
                            else ""
                        )
                        if pseudonym:
                            # Story 10.11: the name is the entity the group's
                            # representative sends (its correction kept)
                            name = self._sent_name(session, current_entity)
                            if pseudonym_checker is not None:
                                others = {
                                    key: value
                                    for key, value in (
                                        session.get_custom_pseudonyms().items()
                                    )
                                    if key != name
                                }
                                # Story 10.16: with the review's names
                                refusal = pseudonym_checker(
                                    name[0],
                                    name[1],
                                    pseudonym,
                                    others,
                                    self._review_names(session),
                                )
                                if refusal is not None:
                                    display_warning_message(
                                        cli_refusal_message(refusal)
                                    )
                                    continue  # Redisplay the same group
                            # The occurrences that send the name take it; a
                            # variant that sends another name (a lone first
                            # or last name) is confirmed and gets the
                            # matching part at finalization (Q4, PO R2)
                            for entity in group.occurrences:
                                if self._sent_name(session, entity) == name:
                                    session.change_pseudonym(entity, pseudonym)
                                else:
                                    session.mark_confirmed(entity)
                        else:
                            for entity in group.occurrences:
                                session.mark_confirmed(entity)
                        group_index += 1
                        break

                    elif action == "change_type":
                        new_type = (
                            get_text_input("New entity type (PERSON/LOCATION/ORG)")
                            .strip()
                            .upper()
                        )
                        if new_type not in ("PERSON", "LOCATION", "ORG"):
                            display_warning_message("Invalid entity type")
                            continue  # Redisplay the same group
                        for entity in group.occurrences:
                            session.change_entity_type(entity, new_type)
                        display_info_message(
                            f"Changed {group.count} occurrence(s) to {new_type}"
                        )
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
                            # Accept all groups, counting affected entities
                            decided = [
                                d.original_entity for d in session.user_decisions
                            ]
                            affected = 0
                            for eg in entity_groups:
                                for e in eg.occurrences:
                                    if e not in decided:
                                        session.mark_confirmed(e)
                                        affected += 1
                            display_success_message(
                                f"Accepted all {affected} {entity_type} entities "
                                f"({total_occurrences} total occurrences)"
                            )
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
                            # Reject all groups, counting affected entities
                            decided = [
                                d.original_entity for d in session.user_decisions
                            ]
                            affected = 0
                            for eg in entity_groups:
                                for e in eg.occurrences:
                                    if e not in decided:
                                        session.mark_rejected(e)
                                        affected += 1
                            display_info_message(
                                f"✗ Rejected all {affected} {entity_type} entities "
                                f"({total_occurrences} total occurrences)"
                            )
                            # Exit current entity type review, continue to next type
                            group_index = len(entity_groups)  # Force exit of group loop
                            break
                        break  # Exit group if confirmation cancelled

                    elif action == "invalid":
                        display_warning_message("Invalid key. Press H for help.")
                        continue

    @staticmethod
    def _sent_name(session: ValidationSession, entity: DetectedEntity) -> NameKey:
        """(mapping key, type) of the entity an occurrence's review sends:
        its correction when it has one, else the detected entity (10.11)."""
        review = session.get_entity_review(entity)
        sent = (
            review.modified_entity
            if review is not None and review.modified_entity is not None
            else entity
        )
        return (mapping_key(sent.text, sent.entity_type), sent.entity_type)

    @staticmethod
    def _review_names(session: ValidationSession) -> list[str]:
        """The mapping keys of the names of the review that are not
        rejected: the entity each review still to review, confirmed,
        modified or added sends (Story 10.16, Codex #8)."""
        names: dict[str, None] = {}
        for review in session._entity_reviews:
            if review.state == EntityReviewState.REJECTED:
                continue
            sent = ValidationSession._sent_entity(review)
            names[mapping_key(sent.text, sent.entity_type)] = None
        return list(names)

    @staticmethod
    def _group_custom_pseudonym(session: ValidationSession, group: EntityGroup) -> str:
        """The custom pseudonym of a group: the first occurrence's that holds
        one, or "" (Story 10.11)."""
        for entity in group.occurrences:
            review = session.get_entity_review(entity)
            if review is not None and review.custom_pseudonym:
                return review.custom_pseudonym
        return ""

    @staticmethod
    def _with_title(entity: DetectedEntity, pseudonym: str) -> str:
        """A person's pseudonym with the entity's title prefix in front, as
        ``_get_pseudonym`` shows a suggestion (Story 10.11, PO R9)."""
        if entity.entity_type == "PERSON":
            title_match = re.match(FRENCH_TITLE_PATTERN, entity.text, re.IGNORECASE)
            if title_match:
                return f"{title_match.group(0).rstrip()} {pseudonym}"
        return pseudonym

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

    def _apply_correction(
        self, session: ValidationSession, group: EntityGroup, new_text: str
    ) -> list[EntityGroup]:
        """[E] on a group: every place it reaches takes ``new_text``.

        A group the forms join did not touch (no ``joined_parts``): every
        place takes the correction at the span ``_locate_modified_span``
        gives, the old span when the text is not found there, as before.

        A joined group (Story 10.19, QA's CAPS-001; the orchestrator's
        ruling, 2026-10-26): a place where neither the correction nor a
        capitals form of it is found (``_reached_span``), one of the group's
        own or one a join brought in, is never written with a partial span.
        It is left unmodified and goes back to the review as its own name:
        the group's own such places as one group, then each joined part's,
        in that order (key and canonical entity: the group's first place).

        Returns:
            The groups sent back to the review, possibly none
        """
        part_of = {
            id(entity): index + 1
            for index, part in enumerate(group.joined_parts)
            for entity in part
        }
        unreached: dict[int, list[DetectedEntity]] = {}
        for entity in group.occurrences:
            text = session.text_of(entity)
            if group.joined_parts:
                reached = self._reached_span(text, entity, new_text)
                if reached is None:
                    unreached.setdefault(part_of.get(id(entity), 0), []).append(entity)
                    continue
                start_pos, end_pos = reached
            else:
                start_pos, end_pos = self._locate_modified_span(text, entity, new_text)
            modified_entity = replace(
                entity,
                text=new_text,
                start_pos=start_pos,
                end_pos=end_pos,
                is_ambiguous=False,
                source=CORRECTED_BY_HAND_SOURCE,
            )
            session.mark_modified(entity, modified_entity)
        return [
            EntityGroup(
                unique_key=(places[0].text, places[0].entity_type),
                occurrences=places,
                variant_texts={place.text for place in places},
                canonical_entity=places[0],
            )
            for _, places in sorted(unreached.items())
        ]

    @staticmethod
    def _locate_modified_span(
        document_text: str, entity: DetectedEntity, new_text: str
    ) -> tuple[int, int]:
        """The span ``_reached_span`` finds for the edited text; else the
        original span widened over the words the correction adds, when they
        are written right after it (``_widened_over_added_words``); else the
        original span."""
        reached = ValidationWorkflow._reached_span(document_text, entity, new_text)
        if reached is not None:
            return reached
        widened = ValidationWorkflow._widened_over_added_words(
            document_text, entity, new_text
        )
        if widened is not None:
            return widened
        return entity.start_pos, entity.end_pos

    @staticmethod
    def _widened_over_added_words(
        document_text: str, entity: DetectedEntity, new_text: str
    ) -> tuple[int, int] | None:
        """The original span widened over the words a correction adds
        (Story 10.19, v1.13; Lionel, 2026-10-26, "fix it in 10.19").

        When the correction starts with the words the original span holds,
        accents set aside, in any capitals, and the words written right after
        the span, past any whitespace (a line break too), are the words it
        adds, each with a capital letter (never a word written in small
        letters only) and each a Q3 form of the typed word, or the typed word
        of it (``is_form`` either way round: « Tèstar » for « TESTAR », never
        « Mèzor » for « Mézor »; v1.15, the orchestrator's rulings 1 and 2),
        the span covers them: « Zélvine » corrected as « ZELVINE TESTAR »
        covers « Zélvine Testar », so « Testar » is not left in clear beside
        the pseudonym. A word is read by what it is (``_next_word``, v1.19):
        quotation marks, an ellipsis, a dash or a digit after it are not part
        of it; an elision inside it stays.

        Returns:
            (start_pos, end_pos) of the widened span, or None
        """
        held = document_text[entity.start_pos : entity.end_pos].split()
        typed = new_text.split()
        if not held or len(typed) <= len(held):
            return None
        if any(fold(a).lower() != fold(b).lower() for a, b in zip(held, typed)):
            return None
        end = entity.end_pos
        for word in typed[len(held) :]:
            found = _next_word(document_text, end)
            if found is None:
                return None
            word_start, word_end = found
            written = document_text[word_start:word_end]
            if not any(char.isupper() for char in written) or not (
                is_form(written, word) or is_form(word, written)
            ):
                return None
            end = word_end
        return entity.start_pos, end

    @staticmethod
    def _reached_span(
        document_text: str, entity: DetectedEntity, new_text: str
    ) -> tuple[int, int] | None:
        """Find where the edited text sits relative to the original span.

        Replacement is offset-based, so editing "Thanks, Aino" down to "Aino"
        must move the span onto "Aino"; keeping the original offsets would
        replace (erase) "Thanks, " as well. Extending a truncated name
        ("Dr. Marja" -> "Dr. Marja-Liisa") widens the span the same way.
        Story 10.20 (AC4): a place that starts on a combining mark, or ends
        just before one, is skipped: it would part a letter from its accent.
        Story 10.19 (AC3): when the exact text is not there, the first form of
        it (``whole_word_places``: other capitals, or capitals without its
        accents, never a word in small letters) inside the same window that
        overlaps the original span is taken, so « ZORBAL » corrected as
        « Zorbal Quentrix » covers « ZORBAL QUENTRIX » whole. The forms are
        searched in the window only, with one character more on each side
        for the word bounds (QA's PERF-001).

        Args:
            document_text: Full document text
            entity: Entity being edited (original span)
            new_text: Text entered by the user

        Returns:
            (start_pos, end_pos) of the edited text (or of a form of it)
            overlapping the original span, or None if neither is found there
        """
        window_start = max(0, entity.start_pos - len(new_text))
        window_end = min(len(document_text), entity.end_pos + len(new_text))
        pos = document_text.find(new_text, window_start, window_end)
        while pos != -1:
            end = pos + len(new_text)
            splits_a_letter = is_mark(document_text[pos]) or (
                end < len(document_text) and is_mark(document_text[end])
            )
            if pos < entity.end_pos and end > entity.start_pos and not splits_a_letter:
                return pos, end
            pos = document_text.find(new_text, pos + 1, window_end)
        low = max(0, window_start - 1)
        high = min(len(document_text), window_end + 1)
        for start, end in whole_word_places(new_text, document_text[low:high]):
            start, end = start + low, end + low
            if (
                window_start <= start
                and end <= window_end
                and start < entity.end_pos
                and end > entity.start_pos
            ):
                return start, end
        return None

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

        # Story 10.15 (AC14): every whole-word place of the text, in the text
        # or in every cell. A place already in the review (found by the
        # detector with this type, or added before) keeps its own review.
        places = session.places_of(entity_text, entity_type)
        if not places:
            display_warning_message(f"'{entity_text}' not found in document")
            return

        new_places = [place for place in places if not session.is_listed_place(place)]
        for place in new_places:
            session.add_manual_entity(place)

        if new_places:
            display_info_message(f"Added {entity_type} entity: {entity_text}")
        else:
            # %2 first: the type is a fixed word, the typed text may hold "%2"
            display_info_message(
                ALREADY_IN_REVIEW_LINE.replace("%2", entity_type).replace(
                    "%1", entity_text
                )
            )

    def _manual_entity_addition_flow(
        self,
        document_text: str,
        document_path: str,
        cells: dict[str, str] | None = None,
    ) -> list[DetectedEntity]:
        """Handle manual entity addition when no entities detected.

        Args:
            document_text: Full document text
            document_path: Path to document
            cells: Cell reference -> cell text of a spreadsheet (Story 10.15);
                None for a text document

        Returns:
            List of manually added entities
        """
        session = ValidationSession(
            document_path=document_path,
            document_text=document_text,
            cell_texts=dict(cells or {}),
        )

        display_info_message("Manual entity addition mode")

        while True:
            self._handle_add_entity(session)

            if not get_confirmation("Add another entity?"):
                break

        return session.get_validated_entities()


def ask_for_missed_names(
    document_text: str,
    document_path: str = "",
    *,
    nothing_found: bool,
    cells: dict[str, str] | None = None,
    types_selected: bool = False,
) -> list[DetectedEntity]:
    """Ask whether to add a name the detector missed (Story 10.18).

    Called in place of the review when nothing is left to review: the
    detector found no name, or only names already stored under the same
    type. Shows which case it is (with ``types_selected``, the lines speak
    of the types selected with ``--entity-types``), then asks the question;
    with yes, the manual flow adds names with [A]'s rules (every place, in
    each cell of a spreadsheet), until the answer to « Add another
    entity? » is no.

    Args:
        document_text: Full document text (on a spreadsheet, its cells joined)
        document_path: Path to the document
        nothing_found: True when the detector found no name at all
        cells: Cell reference -> cell text of a spreadsheet; None for a text
            document
        types_selected: True when ``--entity-types`` was given

    Returns:
        The places added by hand (empty when the answer is no)

    Raises:
        NoAnswerError: If no answer can be read (end of input), at the
            question or at a prompt of the manual flow. ``isatty()`` is never
            read: it is True on Windows when stdin is NUL.
        KeyboardInterrupt: On Ctrl+C, not caught here: the command cancels
            at once, as the review's empty-list path does.
    """
    if types_selected:
        line = (
            SELECTED_NO_NAMES_FOUND_LINE
            if nothing_found
            else SELECTED_NO_NEW_NAMES_LINE
        )
    else:
        line = NO_NAMES_FOUND_LINE if nothing_found else NO_NEW_NAMES_LINE
    display_info_message(line)
    try:
        if not get_confirmation(ADD_MISSED_NAME_QUESTION):
            return []
        return ValidationWorkflow()._manual_entity_addition_flow(
            document_text, document_path, cells=cells
        )
    except EOFError as error:
        raise NoAnswerError(NO_ANSWER_TEXT) from error


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
    pseudonym_checker: PseudonymChecker | None = None,
    custom_pseudonyms: dict[NameKey, str] | None = None,
    sent_without_review: list[DetectedEntity] | None = None,
    cells: dict[str, str] | None = None,
) -> list[DetectedEntity]:
    """Execute interactive validation workflow.

    This is the main entry point for running the validation workflow.

    Args:
        entities: List of detected entities to validate
        document_text: Full document text
        document_path: Path to document being validated (optional)
        pseudonym_assigner: Function to assign pseudonyms (optional)
        pseudonym_checker: Checks a custom pseudonym set with [C]
            (Story 10.11; optional)
        custom_pseudonyms: When given, filled with the custom pseudonyms of
            the names sent, keyed by (mapping key, type) (Story 10.11)
        sent_without_review: Known entities written without review, included
            in Story 10.13 coverage per Lionel's decision of 2026-10-16.
        cells: Cell reference -> cell text of a spreadsheet (Story 10.15);
            None for a text document.

    Returns:
        List of validated entities after user review

    Raises:
        KeyboardInterrupt: If user cancels validation
    """
    workflow = ValidationWorkflow()
    return workflow.run(
        entities,
        document_text,
        document_path,
        pseudonym_assigner,
        pseudonym_checker,
        custom_pseudonyms,
        sent_without_review=sent_without_review,
        cells=cells,
    )
