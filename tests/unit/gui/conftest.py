"""Shared fixtures for GUI unit tests.

Uses pytest-qt's qapp fixture for QApplication lifecycle.
"""

from __future__ import annotations

from typing import Any

import pytest

from gdpr_pseudonymizer.gui.config import _DEFAULT_CONFIG
from gdpr_pseudonymizer.gui.main_window import MainWindow
from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity


@pytest.fixture()
def gui_config(tmp_path: object) -> dict[str, Any]:
    """Fresh config dict for each test."""
    config = dict(_DEFAULT_CONFIG)
    config["recent_files"] = []
    config["validation_hints_shown"] = True  # Skip hints dialog in tests
    return config


@pytest.fixture()
def main_window(qtbot, gui_config: dict[str, Any]) -> MainWindow:  # type: ignore[no-untyped-def]
    """Create a MainWindow with test config."""
    window = MainWindow(config=gui_config)
    qtbot.addWidget(window)

    # Register screens
    from gdpr_pseudonymizer.gui.screens.home import HomeScreen
    from gdpr_pseudonymizer.gui.screens.processing import ProcessingScreen
    from gdpr_pseudonymizer.gui.screens.results import ResultsScreen
    from gdpr_pseudonymizer.gui.screens.settings import SettingsScreen
    from gdpr_pseudonymizer.gui.screens.stub import StubScreen
    from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

    window.add_screen("home", HomeScreen(window))
    window.add_screen("settings", SettingsScreen(window))
    window.add_screen("processing", ProcessingScreen(window))
    window.add_screen("validation", ValidationScreen(window))
    window.add_screen("results", ResultsScreen(window))
    window.add_screen("batch", StubScreen("Traitement par lot", window))
    window.navigate_to("home")
    return window


@pytest.fixture()
def sample_entities() -> list[DetectedEntity]:
    """Sample detected entities for testing (3 PERSON, 2 LOCATION, 1 ORG)."""
    return [
        DetectedEntity(
            text="Jean Dupont",
            entity_type="PERSON",
            start_pos=20,
            end_pos=31,
            confidence=0.95,
            gender="male",
            source="spacy",
        ),
        DetectedEntity(
            text="Marie Martin",
            entity_type="PERSON",
            start_pos=55,
            end_pos=67,
            confidence=0.92,
            gender="female",
            source="spacy",
        ),
        DetectedEntity(
            text="Sophie Bernard",
            entity_type="PERSON",
            start_pos=120,
            end_pos=134,
            confidence=0.88,
            gender="female",
            source="spacy",
        ),
        DetectedEntity(
            text="Paris",
            entity_type="LOCATION",
            start_pos=45,
            end_pos=50,
            confidence=0.97,
            source="spacy",
        ),
        DetectedEntity(
            text="Lyon",
            entity_type="LOCATION",
            start_pos=100,
            end_pos=104,
            confidence=None,
            source="regex",
        ),
        DetectedEntity(
            text="Nexia Corp",
            entity_type="ORG",
            start_pos=80,
            end_pos=90,
            confidence=0.85,
            source="hybrid",
        ),
    ]


@pytest.fixture()
def sample_document_text() -> str:
    """Sample document text matching sample_entities positions."""
    # Construct text that matches the entity start/end positions
    text = (
        "Le contrat entre "  # 0-18
        + "  "  # 18-20
        + "Jean Dupont"  # 20-31
        + " résidant au "  # 31-45
        + "Paris"  # 45-50
        + " avec "  # 50-55 (padding added)
        + "Marie Martin"  # 55-67
        + " et la société "  # 67-80 (padding adjusted)
        + "Nexia Corp"  # 80-90
        + " basée à "  # 90-100
        + "Lyon"  # 100-104
        + " représentée par "  # 104-120 (padding adjusted)
        + "Sophie Bernard"  # 120-134
        + ", directrice."  # 134+
    )
    return text


@pytest.fixture()
def sample_detection_result(
    sample_entities: list[DetectedEntity],
    sample_document_text: str,
    tmp_path: object,
) -> DetectionResult:
    """DetectionResult factory fixture with sample data."""
    previews: dict[str, str] = {}
    for entity in sample_entities:
        key = f"{entity.text}_{entity.start_pos}"
        previews[key] = f"Pseudo_{entity.text.replace(' ', '_')}"
    return DetectionResult(
        document_text=sample_document_text,
        detected_entities=sample_entities,
        pseudonym_previews=previews,
        entity_type_counts={"PERSON": 3, "LOCATION": 2, "ORG": 1},
        db_path=str(tmp_path) + "/test.db",  # type: ignore[operator]
        passphrase="test_passphrase_secure",
        theme="neutral",
        input_file="test_document.txt",
        detection_time_seconds=1.5,
    )
