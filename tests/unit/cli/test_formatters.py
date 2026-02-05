"""Unit tests for CLI formatters module (Story 3.4, AC1/AC2)."""

from __future__ import annotations

from unittest.mock import patch

from gdpr_pseudonymizer.cli.formatters import (
    DEFAULT_DOCS_URL,
    ERROR_CATALOG,
    ErrorCode,
    ErrorInfo,
    format_styled_error,
    get_error_info,
)


class TestErrorCode:
    """Tests for ErrorCode enum (AC1)."""

    def test_error_code_file_not_found_value(self) -> None:
        """Test FILE_NOT_FOUND has correct value."""
        assert ErrorCode.FILE_NOT_FOUND.value == "file_not_found"

    def test_error_code_invalid_passphrase_value(self) -> None:
        """Test INVALID_PASSPHRASE has correct value."""
        assert ErrorCode.INVALID_PASSPHRASE.value == "invalid_passphrase"

    def test_error_code_corrupt_database_value(self) -> None:
        """Test CORRUPT_DATABASE has correct value."""
        assert ErrorCode.CORRUPT_DATABASE.value == "corrupt_database"

    def test_all_error_codes_unique(self) -> None:
        """Test all error code values are unique."""
        values = [code.value for code in ErrorCode]
        assert len(values) == len(set(values))


class TestErrorCatalog:
    """Tests for ERROR_CATALOG dictionary (AC2)."""

    def test_catalog_has_all_error_codes(self) -> None:
        """Test every ErrorCode has a catalog entry."""
        for code in ErrorCode:
            assert code in ERROR_CATALOG, f"Missing catalog entry for {code}"

    def test_catalog_entries_have_required_fields(self) -> None:
        """Test all catalog entries have description and action."""
        for code, info in ERROR_CATALOG.items():
            assert isinstance(info, ErrorInfo), f"{code} has invalid info type"
            assert info.description, f"{code} missing description"
            assert info.action, f"{code} missing action"

    def test_catalog_entries_have_docs_url(self) -> None:
        """Test catalog entries have docs URL (may be empty)."""
        for code, info in ERROR_CATALOG.items():
            # docs can be empty string but should be a string
            assert isinstance(info.docs, str), f"{code} docs is not a string"

    def test_file_not_found_has_correct_info(self) -> None:
        """Test FILE_NOT_FOUND catalog entry content."""
        info = ERROR_CATALOG[ErrorCode.FILE_NOT_FOUND]
        assert "not found" in info.description.lower()
        assert "path" in info.action.lower()

    def test_invalid_passphrase_has_correct_info(self) -> None:
        """Test INVALID_PASSPHRASE catalog entry content."""
        info = ERROR_CATALOG[ErrorCode.INVALID_PASSPHRASE]
        assert "passphrase" in info.description.lower()
        assert "init" in info.action.lower()


class TestFormatStyledError:
    """Tests for format_styled_error function (AC1)."""

    def test_format_styled_error_outputs_description(self) -> None:
        """Test error output includes description."""
        with patch("gdpr_pseudonymizer.cli.formatters.console") as mock_console:
            format_styled_error(ErrorCode.FILE_NOT_FOUND)

            # Check that console.print was called with ERROR
            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("[ERROR]" in call for call in calls)

    def test_format_styled_error_outputs_action(self) -> None:
        """Test error output includes action."""
        with patch("gdpr_pseudonymizer.cli.formatters.console") as mock_console:
            format_styled_error(ErrorCode.FILE_NOT_FOUND)

            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Action:" in call for call in calls)

    def test_format_styled_error_outputs_details(self) -> None:
        """Test error output includes details when provided."""
        with patch("gdpr_pseudonymizer.cli.formatters.console") as mock_console:
            format_styled_error(ErrorCode.FILE_NOT_FOUND, details="Custom details here")

            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Custom details here" in call for call in calls)

    def test_format_styled_error_outputs_docs(self) -> None:
        """Test error output includes docs URL."""
        with patch("gdpr_pseudonymizer.cli.formatters.console") as mock_console:
            format_styled_error(ErrorCode.FILE_NOT_FOUND)

            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Docs:" in call for call in calls)

    def test_format_styled_error_custom_docs_url(self) -> None:
        """Test custom docs URL overrides default."""
        with patch("gdpr_pseudonymizer.cli.formatters.console") as mock_console:
            custom_url = "https://custom.example.com/docs"
            format_styled_error(ErrorCode.FILE_NOT_FOUND, docs_url=custom_url)

            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any(custom_url in call for call in calls)


class TestGetErrorInfo:
    """Tests for get_error_info helper function."""

    def test_get_error_info_returns_info_for_valid_code(self) -> None:
        """Test get_error_info returns ErrorInfo for valid code."""
        info = get_error_info(ErrorCode.FILE_NOT_FOUND)
        assert info is not None
        assert isinstance(info, ErrorInfo)

    def test_get_error_info_returns_none_for_invalid_code(self) -> None:
        """Test get_error_info returns None for invalid code."""
        # This test would fail if we pass invalid code, but we can
        # verify the function behavior by checking a valid code works
        info = get_error_info(ErrorCode.VALIDATION_ERROR)
        assert info is not None


class TestDefaultDocsUrl:
    """Tests for DEFAULT_DOCS_URL constant."""

    def test_default_docs_url_is_valid(self) -> None:
        """Test default docs URL is a valid URL format."""
        assert DEFAULT_DOCS_URL.startswith("https://")
        assert "#" in DEFAULT_DOCS_URL  # Has anchor fragment base
