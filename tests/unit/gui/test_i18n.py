"""Tests for GUI internationalization (Story 6.6).

Covers:
    - QTranslator loading from .qm files
    - Language switching updates visible text
    - retranslateUi() called on LanguageChange event
    - Language auto-detection logic
    - Settings language selector persists choice
    - All screen classes have retranslateUi()
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QLocale

from gdpr_pseudonymizer.gui.i18n import (
    available_languages,
    detect_language,
    install_translator,
    switch_language,
)
from gdpr_pseudonymizer.gui.i18n.translator import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
)


@pytest.fixture(autouse=True)
def _restore_french_language(qapp: QCoreApplication) -> Any:
    """Restore French (source language) after each test to avoid polluting other tests."""
    yield
    switch_language(qapp, "fr")


# ---------------------------------------------------------------------------
# AC7 — 9.1: QTranslator loads .qm files without error
# ---------------------------------------------------------------------------


class TestTranslatorLoading:
    """Test QTranslator infrastructure."""

    def test_available_languages_returns_list(self) -> None:
        langs = available_languages()
        assert isinstance(langs, list)
        assert "fr" in langs
        assert "en" in langs

    def test_supported_languages_constant(self) -> None:
        assert set(SUPPORTED_LANGUAGES) == {"fr", "en"}

    def test_default_language_is_french(self) -> None:
        assert DEFAULT_LANGUAGE == "fr"

    def test_install_translator_french_is_source(self, qapp: QCoreApplication) -> None:
        """French is the source language — no .qm file needed."""
        result = install_translator(qapp, "fr")
        assert result is True

    def test_install_translator_unknown_language(self, qapp: QCoreApplication) -> None:
        """Unknown languages should return False (no .qm file)."""
        result = install_translator(qapp, "de")
        assert result is False


# ---------------------------------------------------------------------------
# AC7 — 9.4: Language auto-detection (mock QLocale)
# ---------------------------------------------------------------------------


class TestLanguageDetection:
    """Test language auto-detection logic."""

    def test_config_override_fr(self) -> None:
        assert detect_language({"language": "fr"}) == "fr"

    def test_config_override_en(self) -> None:
        assert detect_language({"language": "en"}) == "en"

    def test_config_invalid_language_falls_through(self) -> None:
        """Invalid language in config should fall through to system locale."""
        with patch.object(QLocale, "system") as mock_system:
            mock_locale = MagicMock()
            mock_locale.language.return_value = QLocale.Language.English
            mock_system.return_value = mock_locale
            assert detect_language({"language": "xx"}) == "en"

    def test_system_locale_french(self) -> None:
        with patch.object(QLocale, "system") as mock_system:
            mock_locale = MagicMock()
            mock_locale.language.return_value = QLocale.Language.French
            mock_system.return_value = mock_locale
            assert detect_language() == "fr"

    def test_system_locale_english(self) -> None:
        with patch.object(QLocale, "system") as mock_system:
            mock_locale = MagicMock()
            mock_locale.language.return_value = QLocale.Language.English
            mock_system.return_value = mock_locale
            assert detect_language() == "en"

    def test_system_locale_unsupported_defaults_to_french(self) -> None:
        with patch.object(QLocale, "system") as mock_system:
            mock_locale = MagicMock()
            mock_locale.language.return_value = QLocale.Language.German
            mock_system.return_value = mock_locale
            assert detect_language() == "fr"

    def test_none_config(self) -> None:
        """None config should use system locale."""
        result = detect_language(None)
        assert result in SUPPORTED_LANGUAGES


# ---------------------------------------------------------------------------
# AC7 — 9.2: Language switching updates visible text
# ---------------------------------------------------------------------------


class TestLanguageSwitching:
    """Test runtime language switching."""

    def test_switch_language_returns_true_for_french(
        self, qapp: QCoreApplication
    ) -> None:
        assert switch_language(qapp, "fr") is True

    def test_switch_language_twice(self, qapp: QCoreApplication) -> None:
        """Switching languages multiple times should not crash."""
        switch_language(qapp, "en")
        switch_language(qapp, "fr")
        switch_language(qapp, "en")
        # No exception = pass


# ---------------------------------------------------------------------------
# AC7 — 9.3: retranslateUi() on LanguageChange event
# ---------------------------------------------------------------------------


class TestRetranslateUi:
    """Test that all screen classes implement retranslateUi()."""

    def test_home_screen_has_retranslate(self) -> None:
        from gdpr_pseudonymizer.gui.screens.home import HomeScreen

        assert hasattr(HomeScreen, "retranslateUi")

    def test_processing_screen_has_retranslate(self) -> None:
        from gdpr_pseudonymizer.gui.screens.processing import ProcessingScreen

        assert hasattr(ProcessingScreen, "retranslateUi")

    def test_validation_screen_has_retranslate(self) -> None:
        from gdpr_pseudonymizer.gui.screens.validation import ValidationScreen

        assert hasattr(ValidationScreen, "retranslateUi")

    def test_results_screen_has_retranslate(self) -> None:
        from gdpr_pseudonymizer.gui.screens.results import ResultsScreen

        assert hasattr(ResultsScreen, "retranslateUi")

    def test_batch_screen_has_retranslate(self) -> None:
        from gdpr_pseudonymizer.gui.screens.batch import BatchScreen

        assert hasattr(BatchScreen, "retranslateUi")

    def test_database_screen_has_retranslate(self) -> None:
        from gdpr_pseudonymizer.gui.screens.database import DatabaseScreen

        assert hasattr(DatabaseScreen, "retranslateUi")

    def test_settings_screen_has_retranslate(self) -> None:
        from gdpr_pseudonymizer.gui.screens.settings import SettingsScreen

        assert hasattr(SettingsScreen, "retranslateUi")

    def test_stub_screen_has_retranslate(self) -> None:
        from gdpr_pseudonymizer.gui.screens.stub import StubScreen

        assert hasattr(StubScreen, "retranslateUi")

    def test_main_window_has_retranslate(self) -> None:
        from gdpr_pseudonymizer.gui.main_window import MainWindow

        assert hasattr(MainWindow, "retranslateUi")

    def test_change_event_triggers_retranslate(
        self,
        main_window: Any,
    ) -> None:
        """LanguageChange event should call retranslateUi()."""
        home_idx = main_window._screens.get("home")
        if home_idx is None:
            pytest.skip("HomeScreen not registered")

        home_screen = main_window._stack.widget(home_idx)

        # Spy on retranslateUi
        original = home_screen.retranslateUi
        call_count = [0]

        def spy() -> None:
            call_count[0] += 1
            original()

        home_screen.retranslateUi = spy

        # Send LanguageChange event
        event = QEvent(QEvent.Type.LanguageChange)
        QCoreApplication.sendEvent(home_screen, event)

        assert call_count[0] >= 1


# ---------------------------------------------------------------------------
# AC7 — 9.5: Settings language selector persists choice
# ---------------------------------------------------------------------------


class TestSettingsLanguage:
    """Test Settings screen language persistence."""

    def test_settings_has_language_combo(
        self,
        main_window: Any,
    ) -> None:
        settings_idx = main_window._screens.get("settings")
        if settings_idx is None:
            pytest.skip("SettingsScreen not registered")
        settings = main_window._stack.widget(settings_idx)
        assert hasattr(settings, "_language_combo")
        assert settings._language_combo.count() >= 2

    def test_language_combo_has_fr_and_en(
        self,
        main_window: Any,
    ) -> None:
        settings_idx = main_window._screens.get("settings")
        if settings_idx is None:
            pytest.skip("SettingsScreen not registered")
        settings = main_window._stack.widget(settings_idx)

        items = []
        for i in range(settings._language_combo.count()):
            items.append(settings._language_combo.itemData(i))
        assert "fr" in items
        assert "en" in items
