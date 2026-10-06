"""spaCy-free unit tests for Story 10.3a (boundaries + run-on spans).

- R-LB (AC1): regex name patterns join tokens with horizontal whitespace
  only, never across a line break.
- R-ORG (AC3, AC4): the regex organisation name shape.
- R-SPLIT late (AC2): spans that still cross a line break after the dedup
  are cut, the pieces trimmed and filtered again.
- REL-004 option (b) (AC5): no sentence-start exception in the V3 guard.
- W-JOIN (Lionel 2026-10-06): a PERSON hard-wrapped over one line break.

Unmarked on purpose: ``HybridDetector()`` and ``RegexMatcher()`` load no
spaCy model, so this file runs on every CI leg. Names are invented; the
other words are the generic words of the rules (connectors, particles,
legal forms, title words) or words of the main-corpus text (AC11).
"""

from __future__ import annotations

import random
import re
import time

import pytest

from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector
from gdpr_pseudonymizer.nlp.regex_matcher import RegexMatcher

LINE_BREAKS = ["\n", "\r\n", "\v", "\f", "\x85", " "]
NO_BREAK_SPACES = [" ", " "]


@pytest.fixture(scope="module")
def matcher() -> RegexMatcher:
    m = RegexMatcher()
    m.load_patterns()
    return m


@pytest.fixture
def detector() -> HybridDetector:
    return HybridDetector()


def _ent(
    text: str, entity_type: str, start: int, source: str = "spacy"
) -> DetectedEntity:
    return DetectedEntity(
        text=text,
        entity_type=entity_type,
        start_pos=start,
        end_pos=start + len(text),
        source=source,
    )


def _at(doc: str, text: str, entity_type: str, source: str = "spacy") -> DetectedEntity:
    return _ent(text, entity_type, doc.index(text), source)


def _pattern(matcher: RegexMatcher, category: str, index: int = 0) -> re.Pattern[str]:
    return matcher.patterns[category][index]["regex"]  # type: ignore[no-any-return]


def _org_texts(matcher: RegexMatcher, text: str) -> list[str]:
    return [e.text for e in matcher.match_entities(text) if e.entity_type == "ORG"]


# ---------------------------------------------------------------------------
# R-LB (AC1)
# ---------------------------------------------------------------------------


class TestHorizontalWhitespace:
    # (category, pattern index, text with {sep} between two name tokens,
    #  expected full match when {sep} is a space)
    CASES = [
        ("titles", 0, "M.{sep}Zorbalia", "M. Zorbalia"),
        ("titles", 0, "M. Zorbalia{sep}Quentrix", "M. Zorbalia Quentrix"),
        ("last_first_names", 0, "Quentrix,{sep}Zorbalia", "Quentrix, Zorbalia"),
        ("location_indicators", 0, "à{sep}Zorbaville", "à Zorbaville"),
        ("location_indicators", 0, "à Zorbaville{sep}Nord", "à Zorbaville Nord"),
        ("organizations", 0, "Quentrix{sep}SA", "Quentrix SA"),
        ("organizations", 0, "Quentrix{sep}Vardel SA", "Quentrix Vardel SA"),
        ("organizations", 1, "Institut{sep}Zorbal", "Institut Zorbal"),
        (
            "organizations",
            1,
            "Institut Zorbal{sep}Quentrix",
            "Institut Zorbal Quentrix",
        ),
    ]

    @pytest.mark.parametrize(("category", "index", "template", "whole"), CASES)
    def test_pattern_never_crosses_a_line_break(
        self,
        matcher: RegexMatcher,
        category: str,
        index: int,
        template: str,
        whole: str,
    ) -> None:
        regex = _pattern(matcher, category, index)
        match = regex.search(template.format(sep=" "))
        assert match is not None and match.group(0) == whole
        for brk in LINE_BREAKS:
            for found in regex.finditer(template.format(sep=brk)):
                assert not any(c in found.group(0) for c in "\n\r\v\f\x85 ")

    @pytest.mark.parametrize(("category", "index", "template", "whole"), CASES)
    def test_pattern_still_crosses_a_no_break_space(
        self,
        matcher: RegexMatcher,
        category: str,
        index: int,
        template: str,
        whole: str,
    ) -> None:
        regex = _pattern(matcher, category, index)
        for nbsp in NO_BREAK_SPACES:
            text = template.format(sep=nbsp)
            match = regex.search(text)
            assert match is not None and match.group(0) == text

    def test_full_names_never_cross_a_line_break(
        self, matcher: RegexMatcher, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert matcher.name_dictionary is not None
        monkeypatch.setattr(
            matcher.name_dictionary,
            "is_full_name",
            lambda first, last: (first, last) == ("Zorb", "Zorb"),
        )
        assert [e.text for e in matcher._match_full_names("Zorb Zorb")] == ["Zorb Zorb"]
        assert [e.text for e in matcher._match_full_names("Zorb Zorb")] == ["Zorb Zorb"]
        for brk in LINE_BREAKS:
            assert matcher._match_full_names(f"Zorb{brk}{brk}Zorb") == []
            assert matcher._match_full_names(f"Zorb{brk}Zorb") == []

    def test_geography_never_crosses_a_line_break(
        self, matcher: RegexMatcher, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert matcher.geography_dictionary is not None
        monkeypatch.setattr(
            matcher.geography_dictionary,
            "is_location",
            lambda name: name.replace(" ", " ") == "Zorbaville sur Quentrix",
        )
        assert [e.text for e in matcher._match_geography("Zorbaville sur Quentrix")]
        assert [e.text for e in matcher._match_geography("Zorbaville sur Quentrix")]
        for brk in LINE_BREAKS:
            assert matcher._match_geography(f"Zorbaville{brk}sur Quentrix") == []
            assert matcher._match_geography(f"Zorbaville sur{brk}Quentrix") == []

    def test_hard_wrapped_name_is_no_longer_one_regex_span(
        self, matcher: RegexMatcher
    ) -> None:
        # Known risk documented at STOP R: a name wrapped by PDF extraction is
        # cut by the regex layer at the line; the title pattern keeps the
        # first line only. W-JOIN (below) restores the PERSON span later.
        found = [
            e.text
            for e in matcher.match_entities("signé par M. Zorbalia\nQuentrix, hier")
            if e.entity_type == "PERSON"
        ]
        assert "M. Zorbalia" in found
        assert all("\n" not in t for t in found)


# ---------------------------------------------------------------------------
# R-ORG (AC3, AC4)
# ---------------------------------------------------------------------------


class TestOrgNameShape:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Quand la direction de Quentrix SA a signé", ["Quentrix SA"]),
            ("La société Quentrix SAS", ["Quentrix SAS"]),
            ("Oui, Quentrix SA", ["Quentrix SA"]),
            ("Institut Zorbal à Zorbaville, notamment le Dr", ["Institut Zorbal"]),
            ("Agence Zorbalienne des Quentrix", ["Agence Zorbalienne des Quentrix"]),
            ("Quentrix SA, Vardel SA", ["Quentrix SA", "Vardel SA"]),
            ("Société Quentrix a été notre premier client", ["Société Quentrix"]),
            ("Cour d'Zorbal de Quentrix SA", ["Cour d'Zorbal de Quentrix SA"]),
            (
                "Chambre d’Zorbal de la Quentrix SA",
                ["Chambre d’Zorbal de la Quentrix SA"],
            ),
            ("Quentrix & Vardel SA", ["Quentrix & Vardel SA"]),
            ("Quentrix SA.", ["Quentrix SA"]),
            ("Institut Zorbal.", ["Institut Zorbal"]),
        ],
    )
    def test_name_shape(
        self, matcher: RegexMatcher, text: str, expected: list[str]
    ) -> None:
        assert _org_texts(matcher, text) == expected

    def test_connector_never_starts_or_ends_a_name(self, matcher: RegexMatcher) -> None:
        assert _org_texts(matcher, "Institut Zorbal de la ville") == ["Institut Zorbal"]
        assert _org_texts(matcher, "de Quentrix SA") == ["Quentrix SA"]

    def test_at_most_six_tokens(self, matcher: RegexMatcher) -> None:
        name = "Zorb Quen Vard Morr Alpa Beto"
        assert _org_texts(matcher, f"Institut {name} Gamo") == [f"Institut {name}"]

    def test_adversarial_line_is_linear(self, matcher: RegexMatcher) -> None:
        # Technical Constraints: a 50 KB line of capitalised words, commas and
        # connectors must not trigger catastrophic backtracking. A ratio check
        # on the same machine, not an absolute limit (10.3a follow-up): 8x the
        # line length must cost under 24x the time, best of five. Linear
        # matching gives about 8, quadratic backtracking about 64.
        lines = [
            "Zorbal Quentrix " * 3200,
            "Zorbal, Quentrix de Vardel " * 2000,
            "Zorbal de la Quentrix d'Vardel " * 2000,
        ]
        regexes = [
            _pattern(matcher, "organizations", 0),
            _pattern(matcher, "organizations", 1),
        ]

        def best_time(length: int) -> float:
            cut = [line[:length] for line in lines]
            best = float("inf")
            for _ in range(5):
                start = time.perf_counter()
                for line in cut:
                    for regex in regexes:
                        for _ in regex.finditer(line):
                            pass
                best = min(best, time.perf_counter() - start)
            return best

        ratio = best_time(50_000) / best_time(6_250)
        assert ratio < 24, ratio

    def test_heading_line_no_longer_feeds_a_union_leak(
        self, matcher: RegexMatcher, detector: HybridDetector
    ) -> None:
        # Story 10.3a AC4 (the 10.2 TechSolutions shape, invented names): a
        # heading line above the organisation, a short spaCy ORG on the
        # heading and a partial spaCy ORG on the name. The organisation name
        # stays covered by one clean ORG span.
        doc = "ZORBAL DU CONSEIL D'QUENTRIX\nQuentrix Vardel SAS\nDate: 3 mars"
        regex_e = matcher.match_entities(doc)
        spacy_e = [_at(doc, "CONSEIL", "ORG"), _at(doc, "Vardel SAS", "ORG")]
        merged = detector._merge_entities(spacy_e, regex_e, doc)
        name = doc.index("Quentrix Vardel SAS")
        assert any(
            e.entity_type == "ORG"
            and e.start_pos <= name
            and name + len("Quentrix Vardel SAS") <= e.end_pos
            and "\n" not in e.text
            for e in merged
        ), merged


# ---------------------------------------------------------------------------
# R-SPLIT late (AC2)
# ---------------------------------------------------------------------------


class TestLineBreakSplit:
    def test_pieces_have_document_offsets(self, detector: HybridDetector) -> None:
        doc = "Zorbalia\n\nZorbalia Quentrix\nQuentrix SA"
        out = detector._merge_entities([_ent(doc, "PERSON", 0)], [], doc)
        assert [e.text for e in out] == ["Zorbalia", "Zorbalia Quentrix", "Quentrix SA"]
        for e in out:
            assert doc[e.start_pos : e.end_pos] == e.text
            assert e.entity_type == "PERSON" and e.source == "spacy"

    @pytest.mark.parametrize("brk", LINE_BREAKS + [" "])
    def test_every_line_break_character_splits(
        self, detector: HybridDetector, brk: str
    ) -> None:
        doc = f"Quentrix Vardel{brk}Zorbal SA"
        out = detector._merge_entities([_ent(doc, "ORG", 0)], [], doc)
        assert [e.text for e in out] == ["Quentrix Vardel", "Zorbal SA"]

    def test_piece_without_capital_or_digit_is_dropped(
        self, detector: HybridDetector
    ) -> None:
        doc = "Quentrix SA\nfournit le projet"
        out = detector._merge_entities([_ent(doc, "ORG", 0)], [], doc)
        assert [e.text for e in out] == ["Quentrix SA"]

    def test_piece_with_digit_is_kept(self, detector: HybridDetector) -> None:
        doc = "Quentrix SA\nprojet 42"
        out = detector._merge_entities([_ent(doc, "ORG", 0)], [], doc)
        assert [e.text for e in out] == ["Quentrix SA", "projet 42"]

    def test_pieces_are_edge_trimmed(self, detector: HybridDetector) -> None:
        doc = "Innovation\n- Caisse des Quentrix"
        out = detector._merge_entities([_ent(doc, "ORG", 0)], [], doc)
        assert [e.text for e in out] == ["Innovation", "Caisse des Quentrix"]
        assert out[1].start_pos == doc.index("Caisse")

    def test_pieces_go_through_the_post_filters(self, detector: HybridDetector) -> None:
        # label word (label filter) and role acronym (ORG role filter)
        doc = "Quentrix SA\nLieu"
        out = detector._merge_entities([_ent(doc, "ORG", 0)], [], doc)
        assert [e.text for e in out] == ["Quentrix SA"]
        doc = "DRH\n\nZorbal Vardel"
        out = detector._merge_entities([_ent(doc, "ORG", 0)], [], doc)
        assert [e.text for e in out] == ["Zorbal Vardel"]

    def test_merged_union_is_split_too(self, detector: HybridDetector) -> None:
        doc = "Quentrix Vardel SA\nSiège Zorbaville"
        regex_e = _ent("Quentrix Vardel SA", "ORG", 0, "regex")
        spacy_e = _ent("Vardel SA\nSiège Zorbaville", "ORG", 9, "spacy")
        out = detector._merge_entities([spacy_e], [regex_e], doc)
        assert [e.text for e in out] == ["Quentrix Vardel SA", "Siège Zorbaville"]

    def test_split_log_has_no_entity_text(
        self, detector: HybridDetector, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from gdpr_pseudonymizer.nlp import hybrid_detector as hd

        events: list[tuple[str, dict[str, object]]] = []

        class _Log:
            def debug(self, event: str, **fields: object) -> None:
                events.append((event, fields))

            info = warning = error = debug

        monkeypatch.setattr(hd, "logger", _Log())
        doc = "Zorbalia\n\nQuentrix\nfournit"
        detector._merge_entities([_ent(doc, "PERSON", 0)], [], doc)
        split = [f for e, f in events if e == "span_split_linebreak"]
        assert split == [
            {
                "entity_type": "PERSON",
                "source": "spacy",
                "segments_kept": 2,
                "segments_dropped": 1,
            }
        ]

    def test_invariant_split_and_join_never_uncover_a_name_character(
        self, detector: HybridDetector
    ) -> None:
        """Random spans over text with line breaks: every upper-case letter
        or digit an input span covers stays covered by a span of the same
        type after the split (with its edge trim) and the wrapped-name join."""
        rng = random.Random(1031)
        words = ["Zorbalia", "Quentrix", "de", "x7", "-", "Vardel", "et", ":"]
        seps = [" ", " ", "\n", "\n\n", "\r\n", " \n "]
        for _ in range(500):
            tokens = [rng.choice(words) for _ in range(rng.randint(3, 9))]
            doc = tokens[0]
            starts = [0]
            for tok in tokens[1:]:
                doc += rng.choice(seps)
                starts.append(len(doc))
                doc += tok
            entities: list[DetectedEntity] = []
            for _ in range(rng.randint(1, 4)):
                i = rng.randrange(len(tokens))
                j = rng.randint(i + 1, min(len(tokens), i + 5))
                start, end = starts[i], starts[j - 1] + len(tokens[j - 1])
                entities.append(
                    _ent(doc[start:end], rng.choice(["PERSON", "ORG"]), start)
                )
            out, _ = detector._split_at_line_breaks(list(entities), doc)
            out = detector._join_wrapped_names(out, doc)
            for e in entities:
                for pos in range(e.start_pos, e.end_pos):
                    if doc[pos].isupper() or doc[pos].isdigit():
                        assert any(
                            k.entity_type == e.entity_type
                            and k.start_pos <= pos < k.end_pos
                            for k in out
                        ), (doc, e, out)


# ---------------------------------------------------------------------------
# REL-004 option (b) (AC5)
# ---------------------------------------------------------------------------


class TestSentenceStartGuard:
    def test_qa_probe_keeps_the_sentence_start_name_covered(
        self, detector: HybridDetector
    ) -> None:
        # QA's 10.2 probe, rephrased with a main-corpus sentence (Lionel,
        # STOP R decision 7): a run-on ORG over "arrivons. … Conseil" and
        # "Zorbalia Conseil" detected. "Quentrix" must stay covered.
        doc = "Nous y arrivons. Quentrix, Zorbalia Conseil"
        outer = _ent(
            doc[doc.index("arrivons") :], "ORG", doc.index("arrivons"), "regex"
        )
        inner = _at(doc, "Zorbalia Conseil", "ORG")
        out = detector._merge_entities([inner], [outer], doc)
        q = doc.index("Quentrix")
        assert any(
            e.entity_type == "ORG" and e.start_pos <= q < e.end_pos for e in out
        ), out

    def test_title_after_a_period_is_still_excepted(
        self, detector: HybridDetector
    ) -> None:
        doc = "Quentrix SA fournit. M. le projet"
        outer = _ent(doc, "ORG", 0, "regex")
        inner = _at(doc, "Quentrix SA", "ORG")
        out = detector._merge_entities([inner], [outer], doc)
        assert [e.text for e in out] == ["Quentrix SA fournit"]


# ---------------------------------------------------------------------------
# W-JOIN (STOP R decision 11, tightened form, Lionel 2026-10-06)
# ---------------------------------------------------------------------------


def _persons(detector: HybridDetector, doc: str, *names: str) -> list[str]:
    spacy_e = [_at(doc, n, "PERSON") for n in names]
    out = detector._merge_entities(spacy_e, [], doc)
    return [e.text for e in out if e.entity_type == "PERSON"]


class TestWrappedNameJoin:
    def test_wrapped_full_name_is_joined(self, detector: HybridDetector) -> None:
        doc = "le contrat est signé par Zorbalia\nQuentrix, avec le projet"
        assert _persons(detector, doc, "Zorbalia") == ["Zorbalia\nQuentrix"]

    def test_wrapped_name_with_title_is_joined(self, detector: HybridDetector) -> None:
        doc = "le contrat est signé par M. Zorbalia\nQuentrix et le projet"
        assert _persons(detector, doc, "M. Zorbalia") == ["M. Zorbalia\nQuentrix"]

    def test_wrapped_particle_surname_is_joined(self, detector: HybridDetector) -> None:
        doc = "le contrat est signé par Zorbalia\nde Quentrix."
        assert _persons(detector, doc, "Zorbalia") == ["Zorbalia\nde Quentrix"]
        doc = "le contrat est signé par Zorbalia van\nQuentrix, hier"
        assert _persons(detector, doc, "Zorbalia") == ["Zorbalia van\nQuentrix"]

    def test_surname_piece_is_absorbed(self, detector: HybridDetector) -> None:
        doc = "le contrat est signé par Zorbalia\nQuentrix, avec le projet"
        assert _persons(detector, doc, "Zorbalia", "Quentrix") == ["Zorbalia\nQuentrix"]

    def test_wrapped_name_at_end_of_text(self, detector: HybridDetector) -> None:
        doc = "le contrat est signé par Zorbalia\nQuentrix"
        assert _persons(detector, doc, "Zorbalia") == ["Zorbalia\nQuentrix"]

    def test_crlf_wrap_is_joined(self, detector: HybridDetector) -> None:
        doc = "le contrat est signé par Zorbalia\r\nQuentrix, avec le projet"
        assert _persons(detector, doc, "Zorbalia") == ["Zorbalia\r\nQuentrix"]

    # --- negatives --------------------------------------------------------

    def test_blank_line_is_not_joined(self, detector: HybridDetector) -> None:
        doc = "le contrat est signé par Zorbalia\n\nQuentrix, avec le projet"
        assert _persons(detector, doc, "Zorbalia") == ["Zorbalia"]

    def test_punctuation_at_line_end_is_not_joined(
        self, detector: HybridDetector
    ) -> None:
        doc = "le contrat est signé par Zorbalia,\nQuentrix, avec le projet"
        assert _persons(detector, doc, "Zorbalia") == ["Zorbalia"]

    def test_name_followed_by_a_role_line_is_not_joined(
        self, detector: HybridDetector
    ) -> None:
        doc = "Zorbalia Quentrix\nDirecteur Commercial\n"
        assert _persons(detector, doc, "Zorbalia Quentrix") == ["Zorbalia Quentrix"]
        doc = "Cordialement,\nZorbalia\nDirecteur"
        assert _persons(detector, doc, "Zorbalia") == ["Zorbalia"]

    def test_two_names_on_consecutive_lines_are_not_joined(
        self, detector: HybridDetector
    ) -> None:
        doc = "Zorbalia Quentrix\nVardel Morrix\n"
        assert _persons(detector, doc, "Zorbalia Quentrix", "Vardel Morrix") == [
            "Zorbalia Quentrix",
            "Vardel Morrix",
        ]
        doc = "le contrat est signé par Zorbalia\nVardel Morrix et le projet"
        assert _persons(detector, doc, "Zorbalia", "Vardel Morrix") == [
            "Zorbalia",
            "Vardel Morrix",
        ]

    def test_label_line_is_not_joined(self, detector: HybridDetector) -> None:
        # The first draft fired on this main-corpus shape (a name, then a
        # "Responsable:" label line); ":" and ";" are not followers.
        doc = "le prestataire est Zorbalia\nResponsable: M. Vardel"
        assert _persons(detector, doc, "Zorbalia") == ["Zorbalia"]

    def test_two_word_name_is_not_extended(self, detector: HybridDetector) -> None:
        doc = "le contrat est signé par Zorbalia Quentrix\nVardel, avec le projet"
        assert _persons(detector, doc, "Zorbalia Quentrix") == ["Zorbalia Quentrix"]

    def test_only_person_is_joined(self, detector: HybridDetector) -> None:
        doc = "le contrat est signé par Zorbal\nQuentrix, avec le projet"
        out = detector._merge_entities([_at(doc, "Zorbal", "ORG")], [], doc)
        assert [e.text for e in out] == ["Zorbal"]

    def test_residual_over_wide_join_is_accepted(
        self, detector: HybridDetector
    ) -> None:
        # Accepted residual (Lionel 2026-10-06): a one-word name at the end of
        # a prose line followed by a capitalised role word and a lower-case
        # word is joined (over-coverage, nothing left in clear).
        doc = "le contrat est signé avec Zorbalia\nDirectrice de la société"
        assert _persons(detector, doc, "Zorbalia") == ["Zorbalia\nDirectrice"]


# ---------------------------------------------------------------------------
# W-JOIN cost and order (10.3a QA PERF-001)
# ---------------------------------------------------------------------------


def _join_input(units: int, wrapped: bool) -> tuple[str, list[DetectedEntity]]:
    """``units`` copies of one line, two one-word PERSON entities per copy."""
    sep = "\n" if wrapped else " "
    line = f"le contrat est signé par Zorbalia{sep}Quentrix, avec le projet\n"
    entities: list[DetectedEntity] = []
    for i in range(units):
        base = i * len(line)
        for name in ("Zorbalia", "Quentrix"):
            entities.append(_ent(name, "PERSON", base + line.index(name)))
    return line * units, entities


class TestWrappedNameJoinCost:
    def test_join_time_grows_linearly(self) -> None:
        # The join used to scan the whole entity list once per PERSON
        # (quadratic: 8x the entities took about 64x the time). A ratio check
        # on the same machine, best of five runs: linear work gives about 8.
        def best_time(units: int, wrapped: bool) -> float:
            doc, entities = _join_input(units, wrapped)
            best = float("inf")
            for _ in range(5):
                start = time.perf_counter()
                out = HybridDetector._join_wrapped_names(entities, doc)
                best = min(best, time.perf_counter() - start)
            assert len(out) == (units if wrapped else 2 * units)
            return best

        for wrapped in (False, True):
            ratio = best_time(8000, wrapped) / best_time(1000, wrapped)
            assert ratio < 24, (wrapped, ratio)

    def test_order_is_kept_inputs_then_joined_spans(self) -> None:
        # Output order is unchanged by the PERF-001 rewrite: the kept input
        # entities in input order, then the joined spans in the order made.
        # A later join that covers an earlier joined span drops it.
        doc = (
            "le contrat est signé par M. Zorbalia\nQuentrix, avec le projet\n"
            "Vardel SA et le projet\n"
            "le contrat est signé par Morrix\nde Quentrix."
        )
        z = doc.index("Zorbalia")
        entities = [
            _ent("Zorbalia", "PERSON", z, "regex"),
            _at(doc, "Vardel SA", "ORG"),
            _at(doc, "Morrix", "PERSON"),
            _at(doc, "M. Zorbalia", "PERSON"),
            _ent("Quentrix", "PERSON", doc.rindex("Quentrix")),
        ]
        out = HybridDetector._join_wrapped_names(entities, doc)
        assert [(e.text, e.source) for e in out] == [
            ("Vardel SA", "spacy"),
            ("Morrix\nde Quentrix", "spacy"),
            ("M. Zorbalia\nQuentrix", "spacy"),
        ]
        assert out[0] is entities[1]
