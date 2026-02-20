"""Shared fixtures for GUI integration tests."""

from __future__ import annotations

from typing import Any

import pytest

from gdpr_pseudonymizer.gui.config import _DEFAULT_CONFIG
from gdpr_pseudonymizer.gui.main_window import MainWindow
from gdpr_pseudonymizer.gui.workers.detection_worker import DetectionResult
from gdpr_pseudonymizer.nlp.entity_detector import DetectedEntity


@pytest.fixture()
def gui_config() -> dict[str, Any]:
    config = dict(_DEFAULT_CONFIG)
    config["recent_files"] = []
    config["validation_hints_shown"] = True  # Skip hints in integration tests
    return config


@pytest.fixture()
def integration_window(qtbot, gui_config: dict[str, Any]) -> MainWindow:  # type: ignore[no-untyped-def]
    """Full main window with all screens for integration testing."""
    window = MainWindow(config=gui_config)
    qtbot.addWidget(window)

    from gdpr_pseudonymizer.gui.screens.batch import BatchScreen
    from gdpr_pseudonymizer.gui.screens.database import DatabaseScreen
    from gdpr_pseudonymizer.gui.screens.home import HomeScreen
    from gdpr_pseudonymizer.gui.screens.processing import ProcessingScreen
    from gdpr_pseudonymizer.gui.screens.results import ResultsScreen
    from gdpr_pseudonymizer.gui.screens.settings import SettingsScreen
    from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

    window.add_screen("home", HomeScreen(window))
    window.add_screen("settings", SettingsScreen(window))
    window.add_screen("processing", ProcessingScreen(window))
    window.add_screen("validation", ValidationScreen(window))
    window.add_screen("results", ResultsScreen(window))
    window.add_screen("batch", BatchScreen(window))
    window.add_screen("database", DatabaseScreen(window))
    window.navigate_to("home")
    return window


@pytest.fixture()
def sample_detection_result(tmp_path: object) -> DetectionResult:
    """DetectionResult for integration testing."""
    entities = [
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
            text="Paris",
            entity_type="LOCATION",
            start_pos=45,
            end_pos=50,
            confidence=0.97,
            source="spacy",
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

    doc_text = (
        "Le contrat entre "
        + "  "
        + "Jean Dupont"
        + " résidant au "
        + "Paris"
        + " avec "
        + "Marie Martin"
        + " et la société "
        + "Nexia Corp"
        + " basée à Lyon."
    )

    previews = {
        f"{e.text}_{e.start_pos}": f"Pseudo_{e.text.replace(' ', '_')}"
        for e in entities
    }

    return DetectionResult(
        document_text=doc_text,
        detected_entities=entities,
        pseudonym_previews=previews,
        entity_type_counts={"PERSON": 2, "LOCATION": 1, "ORG": 1},
        db_path=str(tmp_path) + "/integration.db",  # type: ignore[operator]
        passphrase="integration_test_pass",
        theme="neutral",
        input_file="integration_doc.txt",
        detection_time_seconds=1.0,
    )
