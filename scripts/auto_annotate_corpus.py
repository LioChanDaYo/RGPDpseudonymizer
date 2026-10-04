r"""RETIRED (Story 10.1, 2026-10-02). Do not use this script.

This script used to regenerate every file in ``tests/test_corpus/annotations/``
from regular expressions. It is retired, not fixed:

* Root cause of the truncated ground truth (epic finding F3): the annotations
  committed in ``c9bc1ed`` came from that commit's patterns. Their name class
  ``[A-Z...][a-z...\-]+`` has no ``\b`` anchor and no capital after a hyphen,
  so "Jean-Luc Moreau" became "Luc Moreau" (17 hits) and
  "Jean-Charles Le Goff" became "Charles Le" (9). The "Last, First" pattern
  produced comma artefacts such as "Rousseau, Responsable". The ORG patterns
  stopped at accented letters ("Microsoft r") or matched "SA" inside words
  ("RÉORGANISA"). ``6c917a2`` rewrote the patterns but never regenerated the
  annotations, so the files kept the old errors.
* Even the rewritten patterns cannot follow ``GUIDELINES.md``: particles
  ("Jean-Charles Le Goff"), Mc/Mac names, nesting (G7), roles vs ORG, and
  aliases all need a reading of the text.
* ``main()`` overwrote every annotation file, which would silently wipe the
  hand-repaired ground truth.

Ground truth is now maintained by hand under
``tests/test_corpus/annotations/GUIDELINES.md`` (main corpus and the
held-out set in ``tests/test_corpus/held_out/``). Never use an automatic
annotator to produce held-out annotations. The last working version is in git
history (``git show 43f6052:scripts/auto_annotate_corpus.py``).
"""

import sys

RETIRED_MESSAGE = (
    "scripts/auto_annotate_corpus.py is retired (Story 10.1): it truncated names "
    "and would overwrite the hand-repaired ground truth. Annotate by hand under "
    "tests/test_corpus/annotations/GUIDELINES.md."
)


def main() -> int:
    """Refuse to run: the auto-annotator is retired."""
    print(RETIRED_MESSAGE, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
