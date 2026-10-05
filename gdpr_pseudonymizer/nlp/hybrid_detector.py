"""
Hybrid Entity Detector combining spaCy NER with regex pattern matching

Implements EntityDetector interface using a hybrid approach:
1. Run spaCy NER (baseline detection)
2. Run regex pattern matching
3. Merge results with deduplication
4. Return combined entity list
"""

from __future__ import annotations

import dataclasses
import functools
import json
import re
from dataclasses import dataclass

import yaml

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity, EntityDetector
from gdpr_pseudonymizer.nlp.model_names import DEFAULT_SPACY_MODEL
from gdpr_pseudonymizer.nlp.regex_matcher import RegexMatcher
from gdpr_pseudonymizer.nlp.spacy_detector import SpaCyDetector
from gdpr_pseudonymizer.resources import FRENCH_GEOGRAPHY_PATH, ORG_ROLE_FILTER_PATH
from gdpr_pseudonymizer.utils.french_patterns import (
    FRENCH_TITLE_PATTERN,
    strip_french_prepositions,
    strip_french_titles,
)
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# ORG role filter (Story 10.2, AC3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrgRoleFilter:
    """Role list loaded from ``org_role_filter.yaml`` plus runtime region words."""

    acronyms: frozenset[str]
    vp_prefixes: tuple[str, ...]
    functions: frozenset[str]
    connectors: frozenset[str]
    region_phrases: tuple[tuple[str, ...], ...]


_ROLE_TOKEN_RE = re.compile(r"/|(?i:d')|[^\s/]+")

# Connectors that join two place words into one place ("Europe du Nord")
_PLACE_JOINERS = frozenset({"de", "du", "des", "d'"})

# Clause boundaries for the ORG segment trim (Story 10.2, V3): a line break;
# ",", ";" or ":" followed by whitespace; a sentence period followed by
# whitespace (guarded, see ``_clause_boundaries``).
_CLAUSE_BOUNDARY_RE = re.compile(r"\n|[,;:](?=\s)|\.(?=\s+\S)")
_LAST_WORD_RE = re.compile(r"([A-Za-zÀ-ÿ]+)$")
# A period after one of these is an abbreviation, not a sentence end
_PERIOD_TITLES = frozenset({"mme", "mlle", "prof", "dr", "pr", "me", "m"})
# Types whose spans are cut at clause boundaries. Not PERSON: a comma is part
# of the "Last, First" name form.
_SEGMENT_TRIM_TYPES = frozenset({"ORG"})


# A word: a letter followed by letters, digits, apostrophes or hyphens
_WORD_RE = re.compile(r"[^\W\d_][\w'’-]*")
_TITLE_WORD_RE = re.compile(FRENCH_TITLE_PATTERN, re.IGNORECASE)


def _is_sentence_period(raw: str, index: int) -> bool:
    """Whether the period at ``raw[index]`` ends a sentence.

    Not a sentence end after a word shorter than three letters, an all-caps
    word, or a title (Mme, Mlle, Prof, Dr, Pr, Me, M). Not either after an
    abbreviation (REL-002): a capitalised word of at most four letters
    ("Corp", "Inc", "Cie", "Ltd") followed by a capitalised word.
    """
    word = _LAST_WORD_RE.search(raw[:index])
    last = word.group(1) if word else ""
    if len(last) < 3 or last.lower() in _PERIOD_TITLES or last.isupper():
        return False
    following = raw[index + 1 :].lstrip()
    if len(last) <= 4 and last[0].isupper() and following[:1].isupper():
        return False
    return True


def _clause_boundaries(raw: str) -> list[tuple[int, int]]:
    """(start, end) offsets of the clause boundaries in ``raw``.

    A period counts only when it ends a sentence (``_is_sentence_period``).
    """
    found: list[tuple[int, int]] = []
    for match in _CLAUSE_BOUNDARY_RE.finditer(raw):
        if match.group() == "." and not _is_sentence_period(raw, match.start()):
            continue
        found.append((match.start(), match.end()))
    return found


def _discards_capitalised_word(context: str, regions: list[tuple[int, int]]) -> bool:
    """Whether any region of ``context`` holds a capitalised word (V3 guard).

    Excepted: a title from the French title pattern (it is not a name), and
    the first word of a sentence, i.e. a word whose preceding non-space text
    in ``context`` ends with a sentence period (``_is_sentence_period``).
    """
    for start, end in regions:
        for match in _WORD_RE.finditer(context, start, end):
            word = match.group()
            if not word[0].isupper():
                continue
            if _TITLE_WORD_RE.fullmatch(word) or _TITLE_WORD_RE.fullmatch(word + "."):
                continue
            before = context[: match.start()].rstrip()
            if before.endswith(".") and _is_sentence_period(context, len(before) - 1):
                continue
            return True
    return False


def _role_token_spans(text: str) -> list[tuple[str, int, int]]:
    """Split a VP-form remainder into (token, start, end).

    Whitespace tokens, with "/" and the elision "d'" split off. "&" is a
    connector only as a standalone token ("Sales & Marketing"); inside a word
    ("R&D") it stays part of the word.
    """
    return [(m.group(), m.start(), m.end()) for m in _ROLE_TOKEN_RE.finditer(text)]


def _role_tokens(text: str) -> list[str]:
    """Tokens of a VP-form remainder (see ``_role_token_spans``)."""
    return [t for t, _, _ in _role_token_spans(text)]


def _load_geography_region_words() -> list[str]:
    """Country and French region names from the existing geography resource."""
    with open(FRENCH_GEOGRAPHY_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("countries_and_international", [])) + list(
        data.get("regions", [])
    )


@functools.lru_cache(maxsize=1)
def load_org_role_filter() -> OrgRoleFilter:
    """Load the ORG role filter resource once (no spaCy import)."""
    with open(ORG_ROLE_FILTER_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    regions = [e["term"] for e in data["vp_regions"]] + _load_geography_region_words()
    phrases = {tuple(t.casefold() for t in _role_tokens(r)) for r in regions}
    return OrgRoleFilter(
        acronyms=frozenset(e["term"] for e in data["acronyms"]),
        vp_prefixes=tuple(e["term"] for e in data["vp_prefixes"]),
        functions=frozenset(e["term"].casefold() for e in data["vp_functions"]),
        connectors=frozenset(c.casefold() for c in data["connectors"]),
        region_phrases=tuple(sorted(phrases, key=len, reverse=True)),
    )


def _vp_remainder(text: str, prefixes: tuple[str, ...]) -> str | None:
    """Return the text after a VP prefix ("" for a bare prefix), else None.

    "VP" is case-sensitive; spelled-out prefixes compare case-insensitively.
    """
    for prefix in prefixes:
        if prefix == "VP":
            if text == "VP":
                return ""
            if text.startswith("VP "):
                return text[3:]
        else:
            folded = text.casefold()
            if folded == prefix.casefold():
                return ""
            if folded.startswith(prefix.casefold() + " "):
                return text[len(prefix) + 1 :]
    return None


def _match_org_role_places(text: str) -> tuple[str | None, list[str]]:
    """Classify an ORG text as a role and return the place phrases it names.

    Returns:
        (reason, places): reason is "role_acronym", "vp_form" or None; places
        are the place phrases of a VP form, as they appear in the normalized
        text (e.g. ["Europe"] for "VP Europe", [] for "VP Engineering").
        Consecutive place words joined only by de/du/des/d' form one place
        ("Europe du Nord"); "et", "&" and "/" separate places.
    """
    role_filter = load_org_role_filter()
    normalized = " ".join(strip_french_titles(text).split())
    if normalized in role_filter.acronyms:
        return "role_acronym", []
    rest = _vp_remainder(normalized, role_filter.vp_prefixes)
    if rest is None:
        return None, []
    if rest == "":
        return "vp_form", []
    spans = _role_token_spans(rest)
    tokens = [t.casefold() for t, _, _ in spans]
    i = 0
    has_content = False
    places: list[list[int]] = []  # [start_token, end_token) per place
    while i < len(tokens):
        for phrase in role_filter.region_phrases:
            if tuple(tokens[i : i + len(phrase)]) == phrase:
                has_content = True
                if (
                    places
                    and i > places[-1][1]
                    and all(
                        tokens[k] in _PLACE_JOINERS for k in range(places[-1][1], i)
                    )
                ):
                    places[-1][1] = i + len(phrase)
                else:
                    places.append([i, i + len(phrase)])
                i += len(phrase)
                break
        else:
            if tokens[i] in role_filter.functions:
                has_content = True
                places.append([i, i])  # a function word ends the current place
            elif tokens[i] not in role_filter.connectors:
                return None, []
            i += 1
    if not has_content:
        return None, []
    phrases = [rest[spans[a][1] : spans[b - 1][2]] for a, b in places if b > a]
    return "vp_form", phrases


def match_org_role(text: str) -> str | None:
    """Classify an ORG text as a role (Story 10.2, AC3).

    The whole normalized text (titles stripped, whitespace collapsed, case
    kept) must be a role acronym, a bare VP prefix, or a VP prefix followed
    only by function words, region words and connectors, with at least one
    function or region word.

    Returns:
        "role_acronym", "vp_form", or None when the text is not a role
    """
    return _match_org_role_places(text)[0]


class HybridDetector(EntityDetector):
    """Hybrid entity detector combining spaCy NER with regex pattern matching.

    Detection Pipeline:
        1. Run spaCy NER (baseline detection)
        2. Run regex pattern matching
        3. Merge results with deduplication
        4. Return combined entity list

    Deduplication Rules:
        - Exact overlap (same span or same title-stripped text) → Keep spaCy entity
        - No overlap → Keep both entities
        - Different-type partial overlap → Flag regex entity as ambiguous, keep both
        - Same-type overlap → One span kept (Story 10.2 AC1, PR #81 review):
          containment keeps the containing span, unless C1 (lower-case,
          digit-free extra words → inner span) or the C2 trim (a containing
          span crossing a line break is cut at the break when it still
          contains the inner span) applies; a partial overlap becomes the
          union span (source "merged"); ties broken deterministically
        - ORG whose whole text is a job title or role acronym → Dropped (AC3);
          the place named in a dropped VP title is kept as a LOCATION

    Attributes:
        spacy_detector: SpaCyDetector instance for NLP-based detection
        regex_matcher: RegexMatcher instance for pattern-based detection
    """

    def __init__(self, default_model: str = DEFAULT_SPACY_MODEL) -> None:
        """Initialize hybrid detector with spaCy and regex components.

        Args:
            default_model: spaCy model loaded lazily on first detection when
                load_model() was not called (e.g., "en_core_web_trf")
        """
        self.spacy_detector = SpaCyDetector()
        self.regex_matcher = RegexMatcher()
        self.default_model = default_model
        self._model_loaded = False

    def load_model(self, model_name: str) -> None:
        """Load spaCy model and regex patterns.

        Args:
            model_name: spaCy model name (e.g., "fr_core_news_lg")

        Raises:
            ModelNotFoundError: If spaCy model is not installed
            FileNotFoundError: If regex pattern config not found
        """
        # Load spaCy model
        self.spacy_detector.load_model(model_name)

        # Load regex patterns
        self.regex_matcher.load_patterns()

        self._model_loaded = True
        logger.info(
            "hybrid_detector_loaded",
            spacy_model=model_name,
            regex_patterns_loaded=self.regex_matcher.get_pattern_stats()[
                "total_patterns"
            ],
        )

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        """Detect entities using hybrid spaCy + regex approach.

        Args:
            text: Document text to process

        Returns:
            List of DetectedEntity objects from combined detection

        Raises:
            ValueError: If text is empty or invalid
            ModelNotLoadedError: If models not loaded
        """
        if not text:
            raise ValueError("Text cannot be empty")

        if not self._model_loaded:
            # Lazy load with default model
            logger.warning(
                "hybrid_detector_lazy_loading_model", model=self.default_model
            )
            self.load_model(self.default_model)

        # Step 1: spaCy NER
        spacy_entities = self.spacy_detector.detect_entities(text)
        for entity in spacy_entities:
            entity.source = "spacy"

        # Trim non-name tokens (timestamps, punctuation) off span edges before
        # merging, so dedup and mapping lookup see the bare name
        spacy_entities = self._trim_entity_boundaries(spacy_entities)

        logger.debug("spacy_detection_complete", entities_found=len(spacy_entities))

        # Step 2: Regex pattern matching (pass spaCy Doc for POS disambiguation)
        regex_entities = self.regex_matcher.match_entities(
            text, spacy_doc=self.spacy_detector.last_doc
        )
        for entity in regex_entities:
            entity.source = "regex"

        logger.debug("regex_detection_complete", entities_found=len(regex_entities))

        # Step 3: Merge with deduplication
        merged_entities = self._merge_entities(spacy_entities, regex_entities, text)

        logger.info(
            "hybrid_detection_complete",
            spacy_count=len(spacy_entities),
            regex_count=len(regex_entities),
            merged_count=len(merged_entities),
        )

        return merged_entities

    def _merge_entities(
        self,
        spacy_entities: list[DetectedEntity],
        regex_entities: list[DetectedEntity],
        text: str | None = None,
    ) -> list[DetectedEntity]:
        """Merge spaCy and regex entities with deduplication logic.

        Deduplication Rules:
            - Exact overlap (same span) → Keep spaCy entity (prefer NLP confidence)
            - No overlap → Keep both entities
            - Partial overlap, different types → Flag regex entity as ambiguous,
              keep both
            - Partial overlap, same type → Keep both here; the same-type dedup
              pass below keeps one (Story 10.2 AC1)
            - Special case: Regex ORG with "Cabinet" overlapping spaCy PERSON → Prefer ORG

        Post-filters, in order: title-only PERSON, label words, ORG roles
        (AC3), same-type overlap dedup (AC1), then sort by start position.

        Args:
            spacy_entities: Entities detected by spaCy
            regex_entities: Entities detected by regex patterns
            text: Document text, used to slice spans built by the post-filters
                (union, trimmed and place spans). When None, the entity texts
                are used and are assumed to be raw slices of the document.

        Returns:
            Merged and deduplicated list of entities, sorted by position
        """
        merged: list[DetectedEntity] = list(spacy_entities)
        # Track spaCy entities to remove (when regex ORG supersedes spaCy PERSON)
        entities_to_remove: list[DetectedEntity] = []

        for regex_entity in regex_entities:
            overlap_found = False

            for spacy_entity in spacy_entities:
                if self._has_overlap(spacy_entity, regex_entity):
                    overlap_found = True

                    if self._is_exact_match(spacy_entity, regex_entity):
                        # Exact match → Skip regex entity (prefer spaCy)
                        logger.debug(
                            "duplicate_entity_removed",
                            text=regex_entity.text,
                            reason="exact_match_with_spacy",
                        )
                        break
                    elif self._should_prefer_regex_org(regex_entity, spacy_entity):
                        # Special case: Regex ORG (Cabinet pattern) supersedes spaCy PERSON
                        # Remove spaCy PERSON and add regex ORG (not ambiguous)
                        entities_to_remove.append(spacy_entity)
                        merged.append(regex_entity)
                        logger.debug(
                            "org_supersedes_person",
                            regex_text=regex_entity.text,
                            spacy_text=spacy_entity.text,
                            reason="cabinet_pattern_preferred",
                        )
                        break
                    elif regex_entity.entity_type != spacy_entity.entity_type:
                        # Partial overlap, different types → Flag regex entity
                        # as ambiguous, keep both
                        regex_entity.is_ambiguous = True
                        merged.append(regex_entity)
                        logger.debug(
                            "ambiguous_entity_added",
                            regex_text=regex_entity.text,
                            spacy_text=spacy_entity.text,
                            reason="partial_overlap",
                        )
                        break
                    else:
                        # Partial overlap, same type → keep for now, unflagged;
                        # _dedup_same_type_overlaps decides (Story 10.2 AC1)
                        merged.append(regex_entity)
                        break

            if not overlap_found:
                # No overlap → Add regex entity (new detection)
                merged.append(regex_entity)

        # Remove superseded spaCy entities
        for entity in entities_to_remove:
            if entity in merged:
                merged.remove(entity)

        # Filter out title-only entities (e.g., "Maître" without a name)
        merged = self._filter_title_only_entities(merged)

        # Filter out common French label words detected as entities
        merged = self._filter_label_words(merged)

        # Filter out job titles / role acronyms detected as ORG (Story 10.2 AC3)
        merged = self._filter_org_roles(merged, text)

        # Keep one entity per same-type overlap (Story 10.2 AC1)
        merged = self._dedup_same_type_overlaps(merged, text)

        # Sort by start position
        merged.sort(key=lambda e: e.start_pos)

        return merged

    def _should_prefer_regex_org(
        self, regex_entity: DetectedEntity, spacy_entity: DetectedEntity
    ) -> bool:
        """Check if regex ORG entity should supersede spaCy PERSON entity.

        This handles the "Cabinet" pattern case where spaCy incorrectly detects
        "Cabinet Mercier" as PERSON, but regex correctly detects
        "Cabinet Mercier & Associés" as ORG.

        Args:
            regex_entity: Regex-detected entity
            spacy_entity: spaCy-detected entity

        Returns:
            True if regex ORG should replace spaCy PERSON
        """
        # Only apply when regex is ORG and spaCy is PERSON
        if regex_entity.entity_type != "ORG" or spacy_entity.entity_type != "PERSON":
            return False

        # Check if regex entity starts with organization prefix patterns
        org_prefixes = ("Cabinet", "Société", "Entreprise", "Groupe", "Compagnie")
        if not regex_entity.text.startswith(org_prefixes):
            return False

        # Check if spaCy entity is contained within regex entity
        # (i.e., regex detected a larger span that includes the spaCy detection)
        if (
            regex_entity.start_pos <= spacy_entity.start_pos
            and regex_entity.end_pos >= spacy_entity.end_pos
        ):
            return True

        return False

    @staticmethod
    def _is_edge_junk_token(token: str, entity_type: str) -> bool:
        """Check if a span-edge token cannot be part of an entity name.

        Tokens with letters are always kept. PERSON names never contain
        letterless tokens, so any is junk. ORG/LOCATION keep bare numbers
        ("Studio 54", "Paris 2024") and only lose timestamps and punctuation.

        Args:
            token: Whitespace-delimited token at the edge of an entity span
            entity_type: PERSON, LOCATION, or ORG

        Returns:
            True if the token should be trimmed off the span
        """
        if any(char.isalpha() for char in token):
            return False
        if entity_type == "PERSON":
            return True
        is_timestamp = ":" in token and any(char.isdigit() for char in token)
        is_punctuation = not any(char.isalnum() for char in token)
        return is_timestamp or is_punctuation

    def _trim_entity_boundaries(
        self, entities: list[DetectedEntity]
    ) -> list[DetectedEntity]:
        """Trim timestamps and punctuation that NER models glue to entity spans.

        Transformer models (e.g. en_core_web_trf) often draw spans too wide on
        transcripts: "Aino Virtanen        24:85:01" comes back as one PERSON.
        Since mappings are keyed on the full entity text, every timestamp would
        otherwise create a new entity with its own pseudonym.

        Args:
            entities: List of detected entities

        Returns:
            Entities with edge junk trimmed; entities that are only junk are dropped
        """
        trimmed = []
        for entity in entities:
            tokens = list(re.finditer(r"\S+", entity.text))
            first, last = 0, len(tokens) - 1
            while first <= last and self._is_edge_junk_token(
                tokens[first].group(), entity.entity_type
            ):
                first += 1
            while last >= first and self._is_edge_junk_token(
                tokens[last].group(), entity.entity_type
            ):
                last -= 1

            if first > last:
                logger.debug(
                    "junk_only_entity_filtered",
                    text=entity.text,
                    entity_type=entity.entity_type,
                    reason="no_name_tokens",
                )
                continue

            start = tokens[first].start()
            end = tokens[last].end()
            if start != 0 or end != len(entity.text):
                logger.debug(
                    "entity_boundary_trimmed",
                    original=entity.text,
                    trimmed=entity.text[start:end],
                )
                entity.start_pos += start
                entity.end_pos = entity.start_pos + (end - start)
                entity.text = entity.text[start:end]
            trimmed.append(entity)

        return trimmed

    def _filter_title_only_entities(
        self, entities: list[DetectedEntity]
    ) -> list[DetectedEntity]:
        """Filter out entities that are just titles without actual names.

        Entities like "Maître" or "Dr." alone (without a following name) are
        sometimes incorrectly detected by spaCy as PERSON entities. This filter
        removes such false positives.

        Args:
            entities: List of detected entities

        Returns:
            Filtered list with title-only entities removed
        """
        filtered = []
        for entity in entities:
            # Only filter PERSON entities (titles don't apply to ORG/LOCATION)
            if entity.entity_type != "PERSON":
                filtered.append(entity)
                continue

            # Check if entity becomes empty after stripping titles
            normalized = self._normalize_entity_text(entity.text)
            if normalized:
                filtered.append(entity)
            else:
                logger.debug(
                    "title_only_entity_filtered",
                    text=entity.text,
                    source=entity.source,
                    reason="entity_is_title_only",
                )

        return filtered

    def _filter_label_words(
        self, entities: list[DetectedEntity]
    ) -> list[DetectedEntity]:
        """Filter out common French label words incorrectly detected as entities.

        Words like "Lieu" (Location label), "Date", etc. are sometimes detected
        by spaCy as named entities when they appear as document labels.

        Args:
            entities: List of detected entities

        Returns:
            Filtered list with label words removed
        """
        # Common French label words that are not actual named entities
        # These appear in documents as field labels (e.g., "Lieu: Paris")
        label_words = {
            "lieu",  # Location label
            "date",  # Date label
            "heure",  # Time label
            "objet",  # Subject label
            "sujet",  # Subject label
            "titre",  # Title label
            "nom",  # Name label
            "adresse",  # Address label
        }

        filtered = []
        for entity in entities:
            # Check if entity text (lowercase) is just a label word
            if entity.text.lower().strip() in label_words:
                logger.debug(
                    "label_word_entity_filtered",
                    text=entity.text,
                    entity_type=entity.entity_type,
                    source=entity.source,
                    reason="entity_is_label_word",
                )
            else:
                filtered.append(entity)

        return filtered

    def _filter_org_roles(
        self, entities: list[DetectedEntity], text: str | None = None
    ) -> list[DetectedEntity]:
        """Drop ORG detections whose whole normalized text is a job title.

        Role acronyms ("CTO", "DRH", "COMEX") and VP forms ("VP", "VP Sales",
        "VP Europe") are roles, not organisations (Story 10.2, AC3). The list
        lives in ``resources/org_role_filter.yaml``. ORG only, any source.
        When a dropped VP form names a place ("VP Europe"), the place part is
        kept as a LOCATION detection (Lionel, PR #81 review), so the place is
        still pseudonymized. Places come from the role list's region words and
        the geography resource only.

        Args:
            entities: List of detected entities
            text: Document text (see ``_merge_entities``)

        Returns:
            Filtered list with role ORG detections removed and place spans added
        """
        filtered = []
        for entity in entities:
            if entity.entity_type == "ORG":
                reason, places = _match_org_role_places(entity.text)
                if reason is not None:
                    emitted = self._place_entities(entity, places, text)
                    filtered.extend(emitted)
                    logger.debug(
                        "org_role_filtered",
                        entity_type=entity.entity_type,
                        source=entity.source,
                        reason=reason,
                        places_emitted=len(emitted),
                    )
                    continue
            filtered.append(entity)
        return filtered

    @staticmethod
    def _place_entities(
        entity: DetectedEntity, places: list[str], text: str | None
    ) -> list[DetectedEntity]:
        """LOCATION detections for the place phrases of a dropped VP form."""
        raw = entity.text
        if text is not None and entity.end_pos <= len(text):
            raw = text[entity.start_pos : entity.end_pos]
        result: list[DetectedEntity] = []
        cursor = 0
        for phrase in places:
            # whole words only: never inside a longer word ("est" in "investir")
            pattern = (
                r"(?<!\w)"
                + r"\s+".join(re.escape(tok) for tok in phrase.split())
                + r"(?!\w)"
            )
            match = re.compile(pattern).search(raw, cursor)
            if match is None:
                continue
            cursor = match.end()
            result.append(
                DetectedEntity(
                    text=match.group(),
                    entity_type="LOCATION",
                    start_pos=entity.start_pos + match.start(),
                    end_pos=entity.start_pos + match.end(),
                    confidence=entity.confidence,
                    source=entity.source,
                )
            )
        return result

    # ------------------------------------------------------------------
    # Same-type overlap dedup (Story 10.2, AC1/AC2)
    # ------------------------------------------------------------------

    @staticmethod
    def _dedup_norm(entity: DetectedEntity) -> str:
        """App normalization: titles stripped; prepositions too on LOCATION."""
        text = strip_french_titles(entity.text)
        if entity.entity_type == "LOCATION":
            text = strip_french_prepositions(text)
        return text

    @classmethod
    def _dedup_key(cls, entity: DetectedEntity) -> str:
        """Normalized text, lower-cased, whitespace collapsed (mapping key)."""
        return " ".join(cls._dedup_norm(entity).lower().split())

    @classmethod
    def _dedup_core(cls, entity: DetectedEntity) -> tuple[int, int]:
        """Character span of the normalized text inside the raw span."""
        norm = cls._dedup_norm(entity)
        i = entity.text.find(norm) if norm else -1
        if i >= 0:
            return (entity.start_pos + i, entity.start_pos + i + len(norm))
        return (entity.start_pos, entity.end_pos)

    @classmethod
    def _containment_added_text(
        cls, outer: DetectedEntity, inner: DetectedEntity
    ) -> str:
        """Text of the outer core outside the inner core (left + right)."""
        oc, ic = cls._dedup_core(outer), cls._dedup_core(inner)
        off = outer.start_pos
        left = outer.text[oc[0] - off : ic[0] - off]
        right = outer.text[ic[1] - off : oc[1] - off]
        return left + " " + right if left and right else left + right

    @staticmethod
    def _slice(entity: DetectedEntity, text: str | None) -> str:
        """Raw text of an entity's span: from the document when available."""
        if text is not None and entity.end_pos <= len(text):
            return text[entity.start_pos : entity.end_pos]
        return entity.text

    @classmethod
    def _union(
        cls, a: DetectedEntity, b: DetectedEntity, text: str | None
    ) -> DetectedEntity:
        """One span covering both a and b (source "merged")."""
        start, end = min(a.start_pos, b.start_pos), max(a.end_pos, b.end_pos)
        if text is not None and end <= len(text):
            union_text = text[start:end]
        else:
            left, right = (a, b) if a.start_pos <= b.start_pos else (b, a)
            union_text = left.text
            if right.end_pos > left.end_pos:
                union_text += right.text[left.end_pos - right.start_pos :]
        base = a if a.source == "spacy" or b.source != "spacy" else b
        return dataclasses.replace(
            base,
            text=union_text,
            start_pos=start,
            end_pos=end,
            source="merged",
            is_ambiguous=False,
        )

    @classmethod
    def _trim_at_line_break(
        cls, entity: DetectedEntity, text: str | None
    ) -> DetectedEntity | None:
        """The entity cut at its first line break, or None if it has none."""
        raw = cls._slice(entity, text)
        cut = raw.find("\n")
        if cut < 0:
            return None
        kept = raw[:cut].rstrip()
        if not kept:
            return None
        return dataclasses.replace(
            entity, text=kept, end_pos=entity.start_pos + len(kept)
        )

    @classmethod
    def _clause_segment(
        cls, entity: DetectedEntity, anchor: tuple[int, int], text: str | None
    ) -> DetectedEntity | None:
        """The part of ``entity`` between the clause boundaries around ``anchor``.

        Returns None when the anchor itself crosses a boundary, when the
        segment would be the whole span, or when it is empty.
        """
        raw = cls._slice(entity, text)
        a0, a1 = anchor[0] - entity.start_pos, anchor[1] - entity.start_pos
        bounds = _clause_boundaries(raw)
        if any(s < a1 and e > a0 for s, e in bounds):
            return None
        left = max((e for s, e in bounds if e <= a0), default=0)
        right = min((s for s, e in bounds if s >= a1), default=len(raw))
        if left == 0 and right == len(raw):
            return None
        segment = raw[left:right]
        lead = len(segment) - len(segment.lstrip())
        segment = segment.strip()
        if not segment:
            return None
        start = entity.start_pos + left + lead
        return dataclasses.replace(
            entity, text=segment, start_pos=start, end_pos=start + len(segment)
        )

    @classmethod
    def _resolve_same_type_pair(
        cls, a: DetectedEntity, b: DetectedEntity, text: str | None = None
    ) -> tuple[DetectedEntity | None, str]:
        """Pairwise decision, with the ORG segment trim (Story 10.2, V3).

        After the base decision, for ORG pairs: a containment kept by the
        outer span (``containment`` or ``containment_outer_trimmed_linebreak``)
        is replaced by the outer span cut to the clause segment around the
        inner core, when that segment still contains the inner core (reason
        ``containment_outer_trimmed_boundary``). A union is cut the same way
        around the overlap of the two cores (``partial_overlap_union_trimmed``).
        """
        result, reason = cls._resolve_same_type_pair_base(a, b, text)
        if a.entity_type not in _SEGMENT_TRIM_TYPES or result is None:
            return result, reason
        ca, cb = cls._dedup_core(a), cls._dedup_core(b)
        if reason in ("containment", "containment_outer_trimmed_linebreak"):
            a_contains = ca[0] <= cb[0] and cb[1] <= ca[1]
            outer, inner = (a, b) if a_contains else (b, a)
            inner_core = cls._dedup_core(inner)
            segment = cls._clause_segment(outer, inner_core, text)
            if segment is not None and not cls._cut_discards_name(outer, segment, text):
                sc = cls._dedup_core(segment)
                if sc[0] <= inner_core[0] and inner_core[1] <= sc[1]:
                    return segment, "containment_outer_trimmed_boundary"
        elif reason == "partial_overlap_union":
            anchor = (max(ca[0], cb[0]), min(ca[1], cb[1]))
            segment = cls._clause_segment(result, anchor, text)
            if segment is not None and not cls._cut_discards_name(
                result, segment, text
            ):
                return segment, "partial_overlap_union_trimmed"
        return result, reason

    @classmethod
    def _cut_discards_name(
        cls, entity: DetectedEntity, segment: DetectedEntity, text: str | None
    ) -> bool:
        """V3 guard (Lionel, 2026-10-05): a cut may only discard text with no
        capitalised word, titles and sentence-start words excepted. The words
        are read in the document when available, else in the entity text."""
        if text is not None and entity.end_pos <= len(text):
            context, offset = text, 0
        else:
            context, offset = entity.text, entity.start_pos
        regions = [
            (entity.start_pos - offset, segment.start_pos - offset),
            (segment.end_pos - offset, entity.end_pos - offset),
        ]
        return _discards_capitalised_word(context, regions)

    @classmethod
    def _resolve_same_type_pair_base(
        cls, a: DetectedEntity, b: DetectedEntity, text: str | None = None
    ) -> tuple[DetectedEntity | None, str]:
        """Pairwise decision for two same-type entities with overlapping spans.

        ``a`` precedes ``b`` in walk order. Returns (result, reason): result is
        a, b, a new entity replacing both (union or trimmed span), or None when
        both are kept (cores disjoint).
        """
        ca, cb = cls._dedup_core(a), cls._dedup_core(b)
        equal = ca == cb or cls._dedup_key(a) == cls._dedup_key(b)
        if not equal:
            if not (ca[0] < cb[1] and cb[0] < ca[1]):
                return None, "cores_disjoint"
            a_contains = ca[0] <= cb[0] and cb[1] <= ca[1]
            b_contains = cb[0] <= ca[0] and ca[1] <= cb[1]
            if a_contains or b_contains:
                outer, inner = (a, b) if a_contains else (b, a)
                added = cls._containment_added_text(outer, inner)
                tokens = added.split()
                if tokens and all(
                    not any(ch.isupper() or ch.isdigit() for ch in tok)
                    for tok in tokens
                ):
                    return inner, "containment_inner_preferred"
                if "\n" in added:
                    trimmed = cls._trim_at_line_break(outer, text)
                    if trimmed is not None:
                        tc, ic = cls._dedup_core(trimmed), cls._dedup_core(inner)
                        if tc[0] <= ic[0] and ic[1] <= tc[1]:
                            return trimmed, "containment_outer_trimmed_linebreak"
                return outer, "containment"
            return cls._union(a, b, text), "partial_overlap_union"
        # Tie: spaCy first, longer raw span, earlier start, earlier in walk
        if a.source != b.source:
            return (a if a.source == "spacy" else b), "tie"
        raw_a, raw_b = a.end_pos - a.start_pos, b.end_pos - b.start_pos
        if raw_a != raw_b:
            return (a if raw_a > raw_b else b), "tie"
        if a.start_pos != b.start_pos:
            return (a if a.start_pos < b.start_pos else b), "tie"
        return a, "tie"

    def _dedup_same_type_overlaps(
        self, entities: list[DetectedEntity], text: str | None = None
    ) -> list[DetectedEntity]:
        """Keep one entity per same-type overlap (Story 10.2, AC1).

        Walks entities by (start, -end, spaCy first). A new entity that loses
        to any kept same-type rival it conflicts with is dropped. When a pair
        resolves to a new span (union of a partial overlap, or an outer span
        trimmed at a line break), that span replaces both and is compared
        again with the kept entities. Otherwise every conflicting kept rival
        is dropped and the new entity is kept. Cross-type pairs are never
        compared (a LOCATION nested in an ORG is legitimate, GUIDELINES G7).

        Args:
            entities: Merged, filtered entity list
            text: Document text (see ``_merge_entities``)

        Returns:
            Entity list without same-type overlaps (order not guaranteed)
        """
        ordered = sorted(
            entities, key=lambda e: (e.start_pos, -e.end_pos, e.source != "spacy")
        )
        # Active window: kept entities that end at or before the walk position
        # can never overlap a later entity, so they are retired. A replacement
        # (union / trimmed span) can start before the walk position; only then
        # are the retired entities that reach into it compared again. Entries
        # carry their insertion number so that comparisons and the result keep
        # the exact insertion order (same outcome as a full scan).
        active: list[tuple[int, DetectedEntity]] = []
        retired: list[tuple[int, DetectedEntity]] = []
        seq = 0
        for entity in ordered:
            walk_pos = entity.start_pos
            still_active: list[tuple[int, DetectedEntity]] = []
            for item in active:
                (retired if item[1].end_pos <= walk_pos else still_active).append(item)
            active = still_active
            current: DetectedEntity | None = entity
            while current is not None:
                candidates = active
                if current.start_pos < walk_pos:
                    reach = [r for r in retired if r[1].end_pos > current.start_pos]
                    if reach:
                        candidates = sorted(active + reach, key=lambda item: item[0])
                rivals: list[tuple[tuple[int, DetectedEntity], str]] = []
                replaced: (
                    tuple[tuple[int, DetectedEntity], DetectedEntity, str] | None
                ) = None
                lost: tuple[DetectedEntity, str] | None = None
                for item in candidates:
                    other = item[1]
                    if (
                        other.entity_type != current.entity_type
                        or other.end_pos <= current.start_pos
                        or current.end_pos <= other.start_pos
                    ):
                        continue
                    result, reason = self._resolve_same_type_pair(other, current, text)
                    if result is None:
                        continue
                    if result is other:
                        lost = (other, reason)
                        break
                    if result is current:
                        rivals.append((item, reason))
                        continue
                    replaced = (item, result, reason)
                    break
                if lost is not None:
                    self._log_dedup(lost[0], current, lost[1])
                    current = None
                elif replaced is not None:
                    item, result, reason = replaced
                    self._remove_kept(item, active, retired)
                    self._log_dedup(result, item[1], reason)
                    self._log_dedup(result, current, reason)
                    current = result
                else:
                    for item, reason in rivals:
                        self._remove_kept(item, active, retired)
                        self._log_dedup(current, item[1], reason)
                    active.append((seq, current))
                    seq += 1
                    current = None
        return [e for _, e in sorted(active + retired, key=lambda item: item[0])]

    @staticmethod
    def _remove_kept(
        item: tuple[int, DetectedEntity],
        active: list[tuple[int, DetectedEntity]],
        retired: list[tuple[int, DetectedEntity]],
    ) -> None:
        """Remove a kept entry from whichever window list holds it."""
        if item in active:
            active.remove(item)
        else:
            retired.remove(item)

    @staticmethod
    def _log_dedup(kept: DetectedEntity, dropped: DetectedEntity, reason: str) -> None:
        """Log a same-type dedup decision without any entity text (AC2)."""
        logger.debug(
            "same_type_overlap_resolved",
            entity_type=kept.entity_type,
            reason=reason,
            kept_source=kept.source,
            dropped_source=dropped.source,
            kept_start=kept.start_pos,
            kept_end=kept.end_pos,
            dropped_start=dropped.start_pos,
            dropped_end=dropped.end_pos,
        )

    def _has_overlap(self, e1: DetectedEntity, e2: DetectedEntity) -> bool:
        """Check if two entities overlap in text span.

        Args:
            e1: First entity
            e2: Second entity

        Returns:
            True if entities overlap, False otherwise
        """
        return not (e1.end_pos <= e2.start_pos or e2.end_pos <= e1.start_pos)

    def _normalize_entity_text(self, text: str) -> str:
        """Normalize entity text by stripping French titles.

        This ensures that "Dr. Marie Dubois" and "Marie Dubois" are recognized as
        the same entity during deduplication, preventing duplicate validation prompts.

        Args:
            text: Entity text potentially containing titles

        Returns:
            Text with titles removed and whitespace normalized

        Examples:
            "Dr. Marie Dubois" → "Marie Dubois"
            "Mme Fontaine" → "Fontaine"
            "Marie Dubois" → "Marie Dubois" (unchanged)
        """
        return strip_french_titles(text)

    def _is_exact_match(self, e1: DetectedEntity, e2: DetectedEntity) -> bool:
        """Check if two entities have identical span OR normalized text.

        Checks both positional exact match and normalized text match to handle
        cases where one detector includes a title and the other doesn't
        (e.g., "Dr. Marie Dubois" from regex vs "Marie Dubois" from spaCy).

        Args:
            e1: First entity
            e2: Second entity

        Returns:
            True if entities have same start/end positions OR same normalized text
        """
        # Check positional exact match
        if e1.start_pos == e2.start_pos and e1.end_pos == e2.end_pos:
            return True

        # Check normalized text match (strips titles for comparison)
        # This handles "Dr. Marie Dubois" == "Marie Dubois" cases
        if self._normalize_entity_text(e1.text) == self._normalize_entity_text(e2.text):
            return True

        return False

    def get_model_info(self) -> dict[str, str]:
        """Get model metadata for audit logging.

        Returns:
            Dictionary with hybrid detector information
        """
        spacy_info = self.spacy_detector.get_model_info()
        regex_stats = self.regex_matcher.get_pattern_stats()

        return {
            "name": "hybrid_detector",
            "version": "1.0",
            "library": "hybrid",
            "language": "fr",
            "spacy_model": spacy_info.get("name", "unknown"),
            "spacy_version": spacy_info.get("version", "unknown"),
            "regex_patterns_count": str(regex_stats.get("total_patterns", 0)),
        }

    @property
    def supports_gender_classification(self) -> bool:
        """Whether this detector provides gender information.

        Returns:
            True if spaCy detector supports gender classification
        """
        return self.spacy_detector.supports_gender_classification
