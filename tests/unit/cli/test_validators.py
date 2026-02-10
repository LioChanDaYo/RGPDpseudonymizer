"""Unit tests for CLI validators module (Story 3.4, AC4)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from gdpr_pseudonymizer.cli.validators import (
    VALID_LOG_LEVELS,
    VALID_THEMES,
    ensure_database,
    parse_entity_type_filter,
    validate_file_path,
    validate_log_level,
    validate_passphrase_strength,
    validate_theme,
    validate_theme_or_exit,
    validate_workers,
)


class TestValidateFilePath:
    """Tests for validate_file_path function."""

    def test_validate_existing_file_returns_true(self, tmp_path: Path) -> None:
        """Test validation succeeds for existing readable file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        is_valid, resolved = validate_file_path(str(test_file))

        assert is_valid is True
        assert resolved is not None
        assert resolved.exists()

    def test_validate_nonexistent_file_returns_false(self, tmp_path: Path) -> None:
        """Test validation fails for nonexistent file."""
        nonexistent = tmp_path / "does_not_exist.txt"

        with patch("gdpr_pseudonymizer.cli.validators.format_styled_error"):
            is_valid, resolved = validate_file_path(str(nonexistent))

        assert is_valid is False
        assert resolved is None

    def test_validate_file_must_exist_false(self, tmp_path: Path) -> None:
        """Test validation succeeds for nonexistent file when must_exist=False."""
        nonexistent = tmp_path / "new_file.txt"

        is_valid, resolved = validate_file_path(str(nonexistent), must_exist=False)

        assert is_valid is True
        assert resolved is not None


class TestValidateTheme:
    """Tests for validate_theme function."""

    def test_validate_neutral_theme(self) -> None:
        """Test neutral theme is valid."""
        is_valid, result = validate_theme("neutral")
        assert is_valid is True
        assert result == "neutral"

    def test_validate_star_wars_theme(self) -> None:
        """Test star_wars theme is valid."""
        is_valid, result = validate_theme("star_wars")
        assert is_valid is True
        assert result == "star_wars"

    def test_validate_lotr_theme(self) -> None:
        """Test lotr theme is valid."""
        is_valid, result = validate_theme("lotr")
        assert is_valid is True
        assert result == "lotr"

    def test_validate_theme_case_insensitive(self) -> None:
        """Test theme validation is case insensitive."""
        is_valid, result = validate_theme("NEUTRAL")
        assert is_valid is True
        assert result == "neutral"

    def test_validate_invalid_theme(self) -> None:
        """Test invalid theme returns false."""
        with patch("gdpr_pseudonymizer.cli.validators.format_styled_error"):
            is_valid, result = validate_theme("invalid_theme")
        assert is_valid is False

    def test_valid_themes_constant(self) -> None:
        """Test VALID_THEMES contains expected themes."""
        assert "neutral" in VALID_THEMES
        assert "star_wars" in VALID_THEMES
        assert "lotr" in VALID_THEMES


class TestValidateWorkers:
    """Tests for validate_workers function."""

    def test_validate_workers_minimum(self) -> None:
        """Test workers=1 is valid."""
        is_valid, result = validate_workers(1)
        assert is_valid is True
        assert result == 1

    def test_validate_workers_maximum(self) -> None:
        """Test workers=8 is valid."""
        is_valid, result = validate_workers(8)
        assert is_valid is True
        assert result == 8

    def test_validate_workers_middle(self) -> None:
        """Test workers=4 is valid."""
        is_valid, result = validate_workers(4)
        assert is_valid is True
        assert result == 4

    def test_validate_workers_below_minimum(self) -> None:
        """Test workers=0 is invalid."""
        with patch("gdpr_pseudonymizer.cli.validators.format_styled_error"):
            is_valid, result = validate_workers(0)
        assert is_valid is False

    def test_validate_workers_above_maximum(self) -> None:
        """Test workers=9 is invalid."""
        with patch("gdpr_pseudonymizer.cli.validators.format_styled_error"):
            is_valid, result = validate_workers(9)
        assert is_valid is False


class TestValidateLogLevel:
    """Tests for validate_log_level function."""

    def test_validate_debug_level(self) -> None:
        """Test DEBUG level is valid."""
        is_valid, result = validate_log_level("DEBUG")
        assert is_valid is True
        assert result == "DEBUG"

    def test_validate_info_level(self) -> None:
        """Test INFO level is valid."""
        is_valid, result = validate_log_level("INFO")
        assert is_valid is True
        assert result == "INFO"

    def test_validate_warning_level(self) -> None:
        """Test WARNING level is valid."""
        is_valid, result = validate_log_level("WARNING")
        assert is_valid is True
        assert result == "WARNING"

    def test_validate_error_level(self) -> None:
        """Test ERROR level is valid."""
        is_valid, result = validate_log_level("ERROR")
        assert is_valid is True
        assert result == "ERROR"

    def test_validate_log_level_case_insensitive(self) -> None:
        """Test log level validation is case insensitive."""
        is_valid, result = validate_log_level("debug")
        assert is_valid is True
        assert result == "DEBUG"

    def test_validate_invalid_log_level(self) -> None:
        """Test invalid log level returns false."""
        with patch("gdpr_pseudonymizer.cli.validators.format_styled_error"):
            is_valid, result = validate_log_level("TRACE")
        assert is_valid is False

    def test_valid_log_levels_constant(self) -> None:
        """Test VALID_LOG_LEVELS contains expected levels."""
        assert "DEBUG" in VALID_LOG_LEVELS
        assert "INFO" in VALID_LOG_LEVELS
        assert "WARNING" in VALID_LOG_LEVELS
        assert "ERROR" in VALID_LOG_LEVELS


class TestValidatePassphraseStrength:
    """Tests for validate_passphrase_strength function."""

    def test_empty_passphrase_fails(self) -> None:
        """Test empty passphrase fails validation."""
        is_valid, message = validate_passphrase_strength("")
        assert is_valid is False
        assert "empty" in message.lower()

    def test_short_passphrase_fails(self) -> None:
        """Test passphrase under 12 chars fails."""
        is_valid, message = validate_passphrase_strength("short")
        assert is_valid is False
        assert "12" in message

    def test_minimum_length_passphrase_passes(self) -> None:
        """Test 12 character passphrase passes."""
        is_valid, message = validate_passphrase_strength("123456789012")
        assert is_valid is True
        assert "accepted" in message.lower()

    def test_strong_passphrase_passes(self) -> None:
        """Test strong passphrase passes."""
        is_valid, message = validate_passphrase_strength("MyStr0ng!Pass#2024")
        assert is_valid is True
        assert "accepted" in message.lower()

    def test_weak_passphrase_shows_warning(self) -> None:
        """Test weak passphrase shows warning but passes if length ok."""
        # 12 chars but all lowercase - should pass with warning
        with patch(
            "gdpr_pseudonymizer.cli.validators.format_warning_message"
        ) as mock_warn:
            is_valid, message = validate_passphrase_strength("abcdefghijkl")

        assert is_valid is True
        # Should have shown warning about diversity
        assert mock_warn.called


# ===========================================================================
# Shared CLI command helpers (R6)
# ===========================================================================


class TestParseEntityTypeFilter:
    """Tests for parse_entity_type_filter()."""

    def test_none_returns_none(self) -> None:
        """No entity_types arg returns None (no filter)."""
        result = parse_entity_type_filter(None, Console())
        assert result is None

    def test_valid_types_parsed(self) -> None:
        """Valid comma-separated types are returned as a set."""
        result = parse_entity_type_filter("PERSON,ORG", Console())
        assert result == {"PERSON", "ORG"}

    def test_case_insensitive(self) -> None:
        """Types are uppercased automatically."""
        result = parse_entity_type_filter("person,location", Console())
        assert result == {"PERSON", "LOCATION"}

    def test_invalid_types_exit(self) -> None:
        """All-invalid types causes sys.exit(1)."""
        with pytest.raises(SystemExit) as exc_info:
            parse_entity_type_filter("INVALID", Console())
        assert exc_info.value.code == 1

    def test_mixed_valid_invalid_keeps_valid(self) -> None:
        """Mix of valid and invalid keeps only valid types."""
        result = parse_entity_type_filter("PERSON,INVALID", Console())
        assert result == {"PERSON"}


class TestValidateThemeOrExit:
    """Tests for validate_theme_or_exit()."""

    def test_valid_theme_passes(self) -> None:
        """Valid theme does not exit."""
        validate_theme_or_exit("neutral")  # should not raise

    def test_invalid_theme_exits(self) -> None:
        """Invalid theme causes sys.exit(1)."""
        with pytest.raises(SystemExit) as exc_info:
            validate_theme_or_exit("invalid_theme")
        assert exc_info.value.code == 1


class TestEnsureDatabase:
    """Tests for ensure_database()."""

    @patch("gdpr_pseudonymizer.cli.validators.init_database")
    def test_creates_db_when_missing(
        self, mock_init: MagicMock, tmp_path: Path
    ) -> None:
        """Initializes DB when file does not exist."""
        db_path = str(tmp_path / "new.db")
        ensure_database(db_path, "test_pass_12345", Console())
        mock_init.assert_called_once_with(db_path, "test_pass_12345")

    @patch("gdpr_pseudonymizer.cli.validators.init_database")
    def test_skips_when_exists(self, mock_init: MagicMock, tmp_path: Path) -> None:
        """Does nothing when DB file already exists."""
        db_path = tmp_path / "existing.db"
        db_path.write_text("data")
        ensure_database(str(db_path), "test_pass_12345", Console())
        mock_init.assert_not_called()
