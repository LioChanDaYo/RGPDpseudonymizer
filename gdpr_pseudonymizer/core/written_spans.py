"""What the end writes over a list of places (Story 15.1, Fix design E).

``written_parts`` holds the writer's one rule. The end
(``DocumentProcessor._resolve_pseudonyms`` and ``_apply_replacements``), the
desktop review state and the command-line review all call it, so a review
row is marked « not written » exactly where the end does not write it.

The rule, within each cell (a text document is the one cell ``""``):

1. **Today's rule.** The places are taken by start, then longest first, ties
   in the order given; a place that overlaps none already kept is written
   whole. (This is ``_apply_replacements``' loop before Story 15.1, on every
   input, empty and equal places included.)
2. **The crossing rule** (Lionel's Q3). In the same order, a place not kept
   that overlaps exactly one place kept whole, starts inside it and ends
   after it, is written over its own words after it: from the first letter
   or digit at or after that place's end to its own end, when that part is
   not empty and no part of step 2 is written there already. Every other
   place is not written.

Nothing here logs: the places are positions in a user's document.
"""

from __future__ import annotations

import bisect
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

# A place: (cell, start, end); a text document has the cell ""
Place = tuple[str, int, int]


@dataclass(frozen=True)
class NotWritten:
    """A review row whose pseudonym the end does not write at some of its
    places (Story 15.1, Fix design B.1).

    Attributes:
        lost: The row's places with nothing written
        places: The row's places sent
        by: The distinct (text, type) of the rows written over its lost
            places, in the document's order
        by_known: One per entry of ``by``: True when that row is a name
            already in the mapping database that the command line writes
            without review (it cannot be rejected there)
    """

    lost: int
    places: int
    by: tuple[tuple[str, str], ...]
    by_known: tuple[bool, ...]


def _first_letter(text: str, start: int, end: int) -> int:
    """The first position in ``[start, end)`` holding a letter or a digit,
    else ``end``."""
    position = start
    while position < end and not (position < len(text) and text[position].isalnum()):
        position += 1
    return position


def written_parts(
    places: Sequence[Place], texts: Mapping[str, str]
) -> list[tuple[int, int] | None]:
    """For each (cell, start, end) in order, the part the end writes: the
    whole place, its own words after the place it crosses (the crossing
    rule), or None. ``texts`` maps each cell to its text. O(n log n).
    """
    result: list[tuple[int, int] | None] = [None] * len(places)
    by_cell: dict[str, list[int]] = {}
    for index, (cell, _, _) in enumerate(places):
        by_cell.setdefault(cell, []).append(index)
    for cell, members in by_cell.items():
        text = texts.get(cell, "")
        # Sorted by start, longest first; Python's sort keeps the order
        # given for equal places
        order = sorted(members, key=lambda i: (places[i][1], -places[i][2]))
        # Step 1. The places kept whole that hold a character are disjoint
        # and taken by start, so a place overlaps one of them only if it
        # overlaps the last one; an empty place kept overlaps no later place
        # (none starts before it).
        starts: list[int] = []
        ends: list[int] = []
        empties: list[int] = []
        kept: set[int] = set()
        for index in order:
            _, start, end = places[index]
            if starts and start < ends[-1] and end > starts[-1]:
                continue
            kept.add(index)
            result[index] = (start, end)
            if end > start:
                starts.append(start)
                ends.append(end)
            else:
                empties.append(start)
        # Step 2. The crossing rule: one part at most after each place kept
        crossed: set[int] = set()
        for index in order:
            if index in kept:
                continue
            _, start, end = places[index]
            # The places kept that it overlaps, by today's test: those ending
            # after its start and starting before its end (contiguous, being
            # disjoint), and the empty ones strictly inside it
            low = bisect.bisect_right(ends, start)
            high = bisect.bisect_left(starts, end)
            inside = bisect.bisect_left(empties, end) - bisect.bisect_right(
                empties, start
            )
            if high - low != 1 or inside > 0 or low in crossed:
                continue
            kept_start, kept_end = starts[low], ends[low]
            if not (kept_start <= start < kept_end and end > kept_end):
                continue
            part_start = _first_letter(text, kept_end, end)
            if part_start >= end:
                continue
            crossed.add(low)
            result[index] = (part_start, end)
    return result
