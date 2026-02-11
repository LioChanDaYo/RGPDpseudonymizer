"""Package resources (data files bundled with the package)."""

from __future__ import annotations

from pathlib import Path

RESOURCES_DIR = Path(__file__).parent

DETECTION_PATTERNS_PATH = RESOURCES_DIR / "detection_patterns.yaml"
FRENCH_NAMES_PATH = RESOURCES_DIR / "french_names.json"
PSEUDONYMS_DIR = RESOURCES_DIR / "pseudonyms"
