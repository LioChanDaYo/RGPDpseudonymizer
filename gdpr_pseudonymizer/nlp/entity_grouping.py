"""Entity variant grouping for validation deduplication.

Groups variant forms of the same real-world entity (e.g., "Marie Dubois",
"Pr. Dubois", "Dubois") into single validation items, reducing user
validation fatigue.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.utils.french_patterns import (
    strip_french_prepositions,
    strip_french_titles,
)
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)

K = tuple[str, str]


class UnionFind:
    """Disjoint-set (Union-Find) with path compression.

    Generic over any hashable key type. Used for clustering entity
    variants that should be merged into a single validation group.
    """

    def __init__(self, keys: list[K]) -> None:
        self._parent: dict[K, K] = {k: k for k in keys}

    def find(self, k: K) -> K:
        """Find root representative with path compression."""
        while self._parent[k] != k:
            self._parent[k] = self._parent[self._parent[k]]
            k = self._parent[k]
        return k

    def union(self, a: K, b: K) -> None:
        """Merge the sets containing *a* and *b*."""
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb

    def clusters(self) -> list[list[K]]:
        """Return all disjoint clusters as lists of keys."""
        groups: dict[K, list[K]] = defaultdict(list)
        for k in self._parent:
            groups[self.find(k)].append(k)
        return list(groups.values())


def _normalize_person(text: str) -> str:
    """Normalize PERSON entity text for variant comparison.

    Strips French titles iteratively and normalizes whitespace.

    Args:
        text: Raw entity text

    Returns:
        Normalized text without titles
    """
    return strip_french_titles(text)


def _normalize_location(text: str) -> str:
    """Normalize LOCATION entity text for variant comparison.

    Strips leading French prepositions and normalizes case.

    Args:
        text: Raw entity text

    Returns:
        Normalized text without prepositions, lowercased
    """
    return strip_french_prepositions(text).lower()


def _normalize_org(text: str) -> str:
    """Normalize ORG entity text for variant comparison.

    Case-normalizes only (conservative approach — ORG variants are harder
    to heuristically link).

    Args:
        text: Raw entity text

    Returns:
        Lowercased text
    """
    return text.strip().lower()


def _is_person_variant(norm_a: str, norm_b: str) -> bool:
    """Check if two normalized PERSON texts are variants of the same entity.

    Grouping rules:
    - Exact match after normalization → group
    - One is a suffix of the other → group (e.g., "Dubois" is suffix of "Marie Dubois")
    - BUT: different first names sharing same last name → NOT grouped
      (e.g., "Marie Dubois" and "Jean Dubois" are different people)

    Args:
        norm_a: First normalized person text
        norm_b: Second normalized person text

    Returns:
        True if entities should be grouped as variants
    """
    if not norm_a or not norm_b:
        return False

    if norm_a == norm_b:
        return True

    # Identify which is longer (potential full name) and shorter (potential surname)
    longer, shorter = (
        (norm_a, norm_b) if len(norm_a) >= len(norm_b) else (norm_b, norm_a)
    )

    # Check if shorter is a suffix of longer (last name match)
    # "Dubois" is suffix of "Marie Dubois"
    longer_parts = longer.split()
    shorter_parts = shorter.split()

    if len(shorter_parts) == 1:
        # Single word — check if it's the last name (last part) of the longer form
        if longer_parts[-1].lower() == shorter_parts[0].lower():
            return True

    elif len(shorter_parts) >= 2 and len(longer_parts) >= 2:
        # Both have multiple parts — check if they share the same last name
        # but have different first names (→ different people)
        if shorter_parts[-1].lower() == longer_parts[-1].lower():
            if shorter_parts[0].lower() != longer_parts[0].lower():
                # Different first names, same last name → NOT the same person
                return False
            # Same first name, same last name → same person
            return True

    return False


def group_entity_variants(
    entities: list[DetectedEntity],
) -> list[tuple[DetectedEntity, list[DetectedEntity], set[str]]]:
    """Group entities that are variant forms of the same real-world entity.

    Returns groups as tuples of (canonical_entity, all_occurrences, variant_texts).
    The canonical entity is the longest/most complete form in each group.

    Args:
        entities: List of detected entities to group

    Returns:
        List of (canonical_entity, occurrences, variant_texts) tuples.
        - canonical_entity: representative entity (longest form)
        - occurrences: all DetectedEntity instances in this group
        - variant_texts: set of unique text forms in the group
    """
    if not entities:
        return []

    # Step 1: Group by exact (text, entity_type) first
    exact_groups: dict[tuple[str, str], list[DetectedEntity]] = defaultdict(list)
    for entity in entities:
        key = (entity.text, entity.entity_type)
        exact_groups[key].append(entity)

    # Step 2: Build variant clusters per entity type
    # Each cluster is a list of exact-group keys that should merge
    type_keys: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for key in exact_groups:
        type_keys[key[1]].append(key)

    merged_clusters: list[list[tuple[str, str]]] = []

    for entity_type, keys in type_keys.items():
        if entity_type == "PERSON":
            clusters = _cluster_person_variants(keys)
        elif entity_type == "LOCATION":
            clusters = _cluster_location_variants(keys)
        elif entity_type == "ORG":
            clusters = _cluster_org_variants(keys)
        else:
            # Unknown type — no merging
            clusters = [[k] for k in keys]

        merged_clusters.extend(clusters)

    # Step 3: Build output groups
    results: list[tuple[DetectedEntity, list[DetectedEntity], set[str]]] = []

    for cluster in merged_clusters:
        # Collect all occurrences from all keys in cluster
        all_occurrences: list[DetectedEntity] = []
        variant_texts: set[str] = set()

        for key in cluster:
            all_occurrences.extend(exact_groups[key])
            variant_texts.add(key[0])

        # Sort occurrences by position
        all_occurrences.sort(key=lambda e: e.start_pos)

        # Canonical entity: the one with the longest text
        canonical = max(all_occurrences, key=lambda e: len(e.text))

        results.append((canonical, all_occurrences, variant_texts))

    # Sort groups by first occurrence position
    results.sort(key=lambda g: g[1][0].start_pos)

    logger.debug(
        "entity_variant_grouping_complete",
        input_entities=len(entities),
        exact_groups=len(exact_groups),
        variant_groups=len(results),
    )

    return results


def _cluster_by_normalization(
    keys: list[K],
    normalizer: Callable[[str], str],
) -> list[list[K]]:
    """Cluster entity keys by normalized equality.

    Generic clustering: two keys are merged when their text normalizes
    to the same string.  Used for LOCATION and ORG entity types.

    Args:
        keys: List of (text, entity_type) keys
        normalizer: Function that maps raw text → normalized form

    Returns:
        List of clusters (each cluster is a list of merged keys)
    """
    if len(keys) <= 1:
        return [[k] for k in keys]

    normalized = {k: normalizer(k[0]) for k in keys}
    uf = UnionFind(keys)

    key_list = list(keys)
    for i in range(len(key_list)):
        for j in range(i + 1, len(key_list)):
            if normalized[key_list[i]] == normalized[key_list[j]]:
                uf.union(key_list[i], key_list[j])

    return uf.clusters()


def _cluster_person_variants(keys: list[K]) -> list[list[K]]:
    """Cluster PERSON entity keys by variant relationship.

    Handles ambiguous single-word names: if a surname like "Durand" matches
    multiple full names with different first names (e.g., "Olivier Durand" and
    "Alice Durand"), the surname is kept as its own group to prevent incorrect
    transitive merging via Union-Find.
    """
    if len(keys) <= 1:
        return [[k] for k in keys]

    normalized = {k: _normalize_person(k[0]) for k in keys}
    key_list = list(keys)

    # Pre-scan: detect ambiguous single-word names that would bridge
    # different people via Union-Find transitivity.
    last_name_to_full_keys: dict[str, list[K]] = defaultdict(list)
    for key in key_list:
        parts = normalized[key].split()
        if len(parts) >= 2:
            last_name_to_full_keys[parts[-1].lower()].append(key)

    ambiguous_keys: set[K] = set()
    for key in key_list:
        parts = normalized[key].split()
        if len(parts) == 1:
            surname = parts[0].lower()
            matching_full_keys = last_name_to_full_keys.get(surname, [])
            if len(matching_full_keys) >= 2:
                first_names = {
                    normalized[k].split()[0].lower() for k in matching_full_keys
                }
                if len(first_names) >= 2:
                    ambiguous_keys.add(key)

    if ambiguous_keys:
        logger.debug(
            "ambiguous_person_names_detected",
            ambiguous=[k[0] for k in ambiguous_keys],
        )

    uf = UnionFind(keys)
    for i in range(len(key_list)):
        for j in range(i + 1, len(key_list)):
            ka, kb = key_list[i], key_list[j]
            if ka in ambiguous_keys or kb in ambiguous_keys:
                continue
            if _is_person_variant(normalized[ka], normalized[kb]):
                uf.union(ka, kb)

    return uf.clusters()


def _cluster_location_variants(keys: list[K]) -> list[list[K]]:
    """Cluster LOCATION entity keys by normalized equality."""
    return _cluster_by_normalization(keys, _normalize_location)


def _cluster_org_variants(keys: list[K]) -> list[list[K]]:
    """Cluster ORG entity keys by normalized equality."""
    return _cluster_by_normalization(keys, _normalize_org)
