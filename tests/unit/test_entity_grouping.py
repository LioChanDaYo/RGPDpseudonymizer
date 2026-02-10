"""Tests for entity variant grouping logic."""

from __future__ import annotations

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.nlp.entity_grouping import (
    UnionFind,
    _cluster_by_normalization,
    group_entity_variants,
)


def _make_entity(text: str, entity_type: str, start: int = 0) -> DetectedEntity:
    """Helper to create DetectedEntity for tests."""
    return DetectedEntity(
        text=text,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(text),
    )


class TestPersonGrouping:
    """Tests for PERSON entity variant grouping."""

    def test_full_name_and_surname_grouped(self) -> None:
        """'Marie Dubois' + 'Dubois' → one group."""
        entities = [
            _make_entity("Marie Dubois", "PERSON", 0),
            _make_entity("Dubois", "PERSON", 50),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 1
        canonical, occurrences, variants = groups[0]
        assert canonical.text == "Marie Dubois"
        assert len(occurrences) == 2
        assert variants == {"Marie Dubois", "Dubois"}

    def test_titled_and_plain_grouped(self) -> None:
        """'Marie Dubois' + 'Pr. Dubois' + 'Dubois' → one group."""
        entities = [
            _make_entity("Marie Dubois", "PERSON", 0),
            _make_entity("Pr. Dubois", "PERSON", 50),
            _make_entity("Dubois", "PERSON", 100),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 1
        canonical, occurrences, variants = groups[0]
        assert canonical.text == "Marie Dubois"
        assert len(occurrences) == 3
        assert "Pr. Dubois" in variants
        assert "Dubois" in variants

    def test_different_first_names_not_grouped(self) -> None:
        """'Marie Dubois' + 'Jean Dubois' → separate groups."""
        entities = [
            _make_entity("Marie Dubois", "PERSON", 0),
            _make_entity("Jean Dubois", "PERSON", 50),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 2

    def test_single_entity_no_variants(self) -> None:
        """Single entity → group of one."""
        entities = [_make_entity("Marie Dubois", "PERSON", 0)]
        groups = group_entity_variants(entities)
        assert len(groups) == 1
        canonical, occurrences, variants = groups[0]
        assert canonical.text == "Marie Dubois"
        assert len(occurrences) == 1
        assert variants == {"Marie Dubois"}

    def test_exact_duplicates_grouped(self) -> None:
        """Multiple exact same entities → one group."""
        entities = [
            _make_entity("Marie Dubois", "PERSON", 0),
            _make_entity("Marie Dubois", "PERSON", 50),
            _make_entity("Marie Dubois", "PERSON", 100),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 1
        assert groups[0][1].__len__() == 3

    def test_titled_surname_groups_with_full_name(self) -> None:
        """'Pr. Dubois' normalized to 'Dubois' groups with 'Marie Dubois'."""
        entities = [
            _make_entity("Pr. Dubois", "PERSON", 0),
            _make_entity("Marie Dubois", "PERSON", 50),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 1
        canonical = groups[0][0]
        assert canonical.text == "Marie Dubois"

    def test_ambiguous_surname_does_not_bridge_different_people(self) -> None:
        """'Mme Durand' must NOT merge 'Olivier Durand' and 'Alice Durand'.

        Regression test: a single-word surname that matches multiple full names
        with different first names is ambiguous and must stay in its own group
        to prevent Union-Find transitive bridging.
        """
        entities = [
            _make_entity("M. Olivier Durand", "PERSON", 0),
            _make_entity("Mme Alice Durand", "PERSON", 50),
            _make_entity("Mme Durand", "PERSON", 100),
        ]
        groups = group_entity_variants(entities)
        # Three separate groups: Olivier, Alice, and ambiguous "Durand"
        assert len(groups) == 3
        texts = {g[0].text for g in groups}
        assert "M. Olivier Durand" in texts
        assert "Mme Alice Durand" in texts
        assert "Mme Durand" in texts

    def test_titled_surname_with_two_people_stays_separate(self) -> None:
        """'Pr. Dubois' stays separate when both 'Marie Dubois' and 'Jean Dubois' exist."""
        entities = [
            _make_entity("Marie Dubois", "PERSON", 0),
            _make_entity("Jean Dubois", "PERSON", 50),
            _make_entity("Pr. Dubois", "PERSON", 100),
        ]
        groups = group_entity_variants(entities)
        # Three separate groups: Marie, Jean, and ambiguous Pr. Dubois
        assert len(groups) == 3


class TestLocationGrouping:
    """Tests for LOCATION entity variant grouping."""

    def test_preposition_variants_grouped(self) -> None:
        """'à Lyon' + 'Lyon' → one group."""
        entities = [
            _make_entity("à Lyon", "LOCATION", 0),
            _make_entity("Lyon", "LOCATION", 50),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 1
        canonical, occurrences, variants = groups[0]
        assert len(occurrences) == 2
        assert "à Lyon" in variants
        assert "Lyon" in variants

    def test_different_locations_not_grouped(self) -> None:
        """'Lyon' + 'Paris' → separate groups."""
        entities = [
            _make_entity("Lyon", "LOCATION", 0),
            _make_entity("Paris", "LOCATION", 50),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 2

    def test_de_preposition_stripped(self) -> None:
        """'de Paris' + 'Paris' → one group."""
        entities = [
            _make_entity("de Paris", "LOCATION", 0),
            _make_entity("Paris", "LOCATION", 50),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 1

    def test_des_preposition_stripped(self) -> None:
        """'des Champs-Élysées' + 'Champs-Élysées' → one group."""
        entities = [
            _make_entity("des Champs-Élysées", "LOCATION", 0),
            _make_entity("Champs-Élysées", "LOCATION", 50),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 1

    def test_la_article_preserved_in_city_names(self) -> None:
        """'La Rochelle' must NOT be stripped to 'Rochelle' — article is part of the name."""
        entities = [
            _make_entity("La Rochelle", "LOCATION", 0),
            _make_entity("Rochelle", "LOCATION", 50),
        ]
        groups = group_entity_variants(entities)
        # These should be SEPARATE groups — "La Rochelle" ≠ "Rochelle"
        assert len(groups) == 2

    def test_le_article_preserved_in_city_names(self) -> None:
        """'Le Mans' must NOT be stripped to 'Mans' — article is part of the name."""
        entities = [
            _make_entity("Le Mans", "LOCATION", 0),
            _make_entity("Mans", "LOCATION", 50),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 2

    def test_les_article_preserved_in_city_names(self) -> None:
        """'Les Ulis' must NOT be stripped to 'Ulis' — article is part of the name."""
        entities = [
            _make_entity("Les Ulis", "LOCATION", 0),
            _make_entity("Ulis", "LOCATION", 50),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 2


class TestOrgGrouping:
    """Tests for ORG entity variant grouping."""

    def test_case_variants_grouped(self) -> None:
        """'ACME Corp' + 'acme corp' → one group (case-insensitive)."""
        entities = [
            _make_entity("ACME Corp", "ORG", 0),
            _make_entity("acme corp", "ORG", 50),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 1

    def test_different_orgs_not_grouped(self) -> None:
        """'ACME Corp' + 'Globex Inc' → separate groups."""
        entities = [
            _make_entity("ACME Corp", "ORG", 0),
            _make_entity("Globex Inc", "ORG", 50),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 2


class TestCrossTypeNoGrouping:
    """Tests that different entity types are never grouped together."""

    def test_same_text_different_types_not_grouped(self) -> None:
        """'Dubois' (PERSON) + 'Dubois' (ORG) → separate groups."""
        entities = [
            _make_entity("Dubois", "PERSON", 0),
            _make_entity("Dubois", "ORG", 50),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 2
        types = {g[0].entity_type for g in groups}
        assert types == {"PERSON", "ORG"}


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_entities_list(self) -> None:
        """Empty input → empty output."""
        groups = group_entity_variants([])
        assert groups == []

    def test_sorted_by_first_occurrence(self) -> None:
        """Groups are sorted by first occurrence position."""
        entities = [
            _make_entity("Paris", "LOCATION", 100),
            _make_entity("Marie Dubois", "PERSON", 0),
            _make_entity("Lyon", "LOCATION", 50),
        ]
        groups = group_entity_variants(entities)
        positions = [g[1][0].start_pos for g in groups]
        assert positions == sorted(positions)

    def test_canonical_is_longest_form(self) -> None:
        """Canonical entity is the longest text form."""
        entities = [
            _make_entity("Dubois", "PERSON", 0),
            _make_entity("Marie Dubois", "PERSON", 50),
            _make_entity("Pr. Dubois", "PERSON", 100),
        ]
        groups = group_entity_variants(entities)
        assert len(groups) == 1
        canonical = groups[0][0]
        assert canonical.text == "Marie Dubois"


class TestUnionFind:
    """Tests for the UnionFind data structure."""

    def test_singleton_clusters(self) -> None:
        """Without any unions, each key is its own cluster."""
        keys = [("a", "T"), ("b", "T"), ("c", "T")]
        uf = UnionFind(keys)
        clusters = uf.clusters()
        assert len(clusters) == 3

    def test_union_merges_clusters(self) -> None:
        """Unioning two keys merges their clusters."""
        keys = [("a", "T"), ("b", "T"), ("c", "T")]
        uf = UnionFind(keys)
        uf.union(("a", "T"), ("b", "T"))
        clusters = uf.clusters()
        assert len(clusters) == 2

    def test_find_with_path_compression(self) -> None:
        """Find returns consistent root after chain of unions."""
        keys = [("a", "T"), ("b", "T"), ("c", "T"), ("d", "T")]
        uf = UnionFind(keys)
        uf.union(("a", "T"), ("b", "T"))
        uf.union(("b", "T"), ("c", "T"))
        uf.union(("c", "T"), ("d", "T"))
        # All should share the same root
        assert uf.find(("a", "T")) == uf.find(("d", "T"))
        clusters = uf.clusters()
        assert len(clusters) == 1

    def test_transitive_merging(self) -> None:
        """Union is transitive: a-b and b-c → a,b,c in one cluster."""
        keys = [("a", "T"), ("b", "T"), ("c", "T")]
        uf = UnionFind(keys)
        uf.union(("a", "T"), ("b", "T"))
        uf.union(("b", "T"), ("c", "T"))
        clusters = uf.clusters()
        assert len(clusters) == 1
        assert len(clusters[0]) == 3


class TestClusterByNormalization:
    """Tests for _cluster_by_normalization()."""

    def test_groups_by_normalized_equality(self) -> None:
        """Keys that normalize to the same string are clustered."""
        keys = [("Paris", "LOC"), ("paris", "LOC"), ("Lyon", "LOC")]
        clusters = _cluster_by_normalization(keys, lambda t: t.lower())
        assert len(clusters) == 2

    def test_single_key_returns_singleton(self) -> None:
        """Single key returns one singleton cluster."""
        keys = [("Paris", "LOC")]
        clusters = _cluster_by_normalization(keys, lambda t: t.lower())
        assert len(clusters) == 1
        assert clusters[0] == [("Paris", "LOC")]

    def test_empty_keys_returns_empty(self) -> None:
        """Empty input returns empty output."""
        clusters = _cluster_by_normalization([], lambda t: t)
        assert clusters == []

    def test_all_different_no_merging(self) -> None:
        """When all normalizations differ, no merging occurs."""
        keys = [("a", "T"), ("b", "T"), ("c", "T")]
        clusters = _cluster_by_normalization(keys, lambda t: t)
        assert len(clusters) == 3
