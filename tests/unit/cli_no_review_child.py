"""Story 10.18: the child driver of ``tests/unit/test_cli_no_review_add.py``.

Written by the BMAD dev agent (Claude). It runs the real ``gdpr-pseudo``
command (``gdpr_pseudonymizer.cli.main.app``) in a process of its own, so that
the test can close, pipe or run out its standard input as for a real user.
pytest does not collect it (no ``test_`` prefix).

Only detection and two input-level stand-ins are replaced, from environment
variables the test sets:

- ``NO_REVIEW_NAMES``: a JSON list of ``[name, type]``. The detector finds
  every occurrence of each name in each text it is given; the real
  ``--entity-types`` filter still applies after it.
- ``NO_REVIEW_KEYS``: a JSON list of keys for ``readchar.readkey``, used only
  when a review opens (the real one needs a console).
- ``NO_REVIEW_CTRL_C_AT``: N, so that the Nth Rich prompt (``Confirm.ask`` or
  ``Prompt.ask``) raises ``KeyboardInterrupt``, as Ctrl+C typed at
  ``input()`` does. Every other prompt reads standard input as usual.

The desktop settings path points into ``HOME``, which the test sets to its
own temporary folder.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import readchar
from rich.prompt import Confirm, Prompt

import gdpr_pseudonymizer.gui.config as gui_config
from gdpr_pseudonymizer.cli.main import app
from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity


class FakeDetector:
    """Finds every occurrence of each (name, type), and drops an occurrence
    that lies inside a longer one it found."""

    def __init__(self, names: list[tuple[str, str]]) -> None:
        self.names = names

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        found: list[DetectedEntity] = []
        for name, entity_type in self.names:
            start = text.find(name)
            while start != -1:
                found.append(
                    DetectedEntity(
                        text=name,
                        entity_type=entity_type,
                        start_pos=start,
                        end_pos=start + len(name),
                        confidence=0.9,
                        source="spacy",
                    )
                )
                start = text.find(name, start + 1)
        return [
            entity
            for entity in found
            if not any(
                other.start_pos <= entity.start_pos
                and entity.end_pos <= other.end_pos
                and other.end_pos - other.start_pos > entity.end_pos - entity.start_pos
                for other in found
            )
        ]


def _keys(keys: list[str]) -> Callable[[], str]:
    def readkey() -> str:
        if not keys:
            raise RuntimeError("no key left for the review")
        return keys.pop(0)

    return readkey


def _prompts(ctrl_c_at: int) -> None:
    calls = [0]

    def wrap(original: Callable[..., Any]) -> Callable[..., Any]:
        def ask(*args: Any, **kwargs: Any) -> Any:
            calls[0] += 1
            if calls[0] == ctrl_c_at:
                raise KeyboardInterrupt
            return original(*args, **kwargs)

        return ask

    Confirm.ask = wrap(Confirm.ask)  # type: ignore[method-assign]
    Prompt.ask = wrap(Prompt.ask)  # type: ignore[method-assign]


def main() -> None:
    names = [tuple(pair) for pair in json.loads(os.environ["NO_REVIEW_NAMES"])]
    detector = FakeDetector(names)  # type: ignore[arg-type]
    DocumentProcessor._get_detector = lambda self: detector  # type: ignore[assignment,method-assign,return-value]
    readchar.readkey = _keys(json.loads(os.environ.get("NO_REVIEW_KEYS", "[]")))
    ctrl_c_at = int(os.environ.get("NO_REVIEW_CTRL_C_AT", "0"))
    if ctrl_c_at:
        _prompts(ctrl_c_at)
    settings = Path(os.environ["HOME"]) / ".gdpr-pseudo.yaml"
    gui_config._config_path = lambda: settings
    app(args=sys.argv[1:], prog_name="gdpr-pseudo")


if __name__ == "__main__":
    main()
