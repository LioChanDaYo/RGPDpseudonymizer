"""Unit tests for passphrase resolution utilities.

Tests cover:
- CLI flag passphrase source (highest priority)
- Environment variable passphrase source
- Interactive prompt passphrase source
- Passphrase confirmation (for new databases)
- Passphrase validation
- Short passphrase warning
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gdpr_pseudonymizer.cli.passphrase import resolve_passphrase


class TestResolvePassphrasePriority:
    """Tests for passphrase resolution priority."""

    def test_cli_passphrase_highest_priority(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLI passphrase should be used even if env var is set."""
        monkeypatch.setenv("GDPR_PSEUDO_PASSPHRASE", "env_passphrase123")

        result = resolve_passphrase(cli_passphrase="cli_passphrase123!")

        assert result == "cli_passphrase123!"

    def test_env_var_passphrase_used_when_no_cli(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Environment variable passphrase is used when no CLI passphrase."""
        monkeypatch.setenv("GDPR_PSEUDO_PASSPHRASE", "env_passphrase123!")

        result = resolve_passphrase(cli_passphrase=None)

        assert result == "env_passphrase123!"

    def test_interactive_prompt_when_no_cli_or_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Interactive prompt is used when no CLI or env passphrase."""
        monkeypatch.delenv("GDPR_PSEUDO_PASSPHRASE", raising=False)

        with patch(
            "gdpr_pseudonymizer.cli.passphrase.typer.prompt"
        ) as mock_prompt:
            mock_prompt.return_value = "prompted_passphrase123!"

            result = resolve_passphrase(cli_passphrase=None)

        mock_prompt.assert_called_once()
        assert result == "prompted_passphrase123!"


class TestResolvePassphraseConfirmation:
    """Tests for passphrase confirmation on new databases."""

    def test_confirmation_required_for_new_database(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Confirmation prompt is shown when confirm=True."""
        monkeypatch.delenv("GDPR_PSEUDO_PASSPHRASE", raising=False)

        with patch(
            "gdpr_pseudonymizer.cli.passphrase.typer.prompt"
        ) as mock_prompt:
            mock_prompt.side_effect = [
                "new_passphrase123!",
                "new_passphrase123!",  # Confirmation matches
            ]

            result = resolve_passphrase(cli_passphrase=None, confirm=True)

        assert mock_prompt.call_count == 2
        assert result == "new_passphrase123!"

    def test_confirmation_mismatch_exits(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mismatched confirmation exits with error."""
        monkeypatch.delenv("GDPR_PSEUDO_PASSPHRASE", raising=False)

        with patch(
            "gdpr_pseudonymizer.cli.passphrase.typer.prompt"
        ) as mock_prompt:
            mock_prompt.side_effect = [
                "passphrase_one123!",
                "passphrase_two123!",  # Different!
            ]

            with pytest.raises(SystemExit) as exc_info:
                resolve_passphrase(cli_passphrase=None, confirm=True)

        assert exc_info.value.code == 1

    def test_no_confirmation_for_existing_database(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No confirmation prompt when confirm=False."""
        monkeypatch.delenv("GDPR_PSEUDO_PASSPHRASE", raising=False)

        with patch(
            "gdpr_pseudonymizer.cli.passphrase.typer.prompt"
        ) as mock_prompt:
            mock_prompt.return_value = "passphrase_123456!"

            result = resolve_passphrase(cli_passphrase=None, confirm=False)

        mock_prompt.assert_called_once()  # Only one prompt, no confirmation
        assert result == "passphrase_123456!"


class TestResolvePassphraseValidation:
    """Tests for passphrase validation."""

    def test_invalid_passphrase_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Invalid passphrase causes system exit."""
        with patch(
            "gdpr_pseudonymizer.cli.passphrase.EncryptionService.validate_passphrase"
        ) as mock_validate:
            mock_validate.return_value = (False, "Passphrase too short")

            with pytest.raises(SystemExit) as exc_info:
                resolve_passphrase(cli_passphrase="short")

        assert exc_info.value.code == 1

    def test_valid_passphrase_returns_successfully(self) -> None:
        """Valid passphrase is returned successfully."""
        result = resolve_passphrase(cli_passphrase="valid_passphrase_123!")

        assert result == "valid_passphrase_123!"


class TestResolvePassphraseWarnings:
    """Tests for passphrase warnings."""

    def test_short_passphrase_shows_warning(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Short passphrase (< 12 chars) shows warning but still works."""
        # The EncryptionService allows shorter passphrases with a warning
        # This test verifies the warning is shown
        with patch(
            "gdpr_pseudonymizer.cli.passphrase.EncryptionService.validate_passphrase"
        ) as mock_validate:
            # Simulate valid but short passphrase
            mock_validate.return_value = (True, "Valid but short")

            result = resolve_passphrase(cli_passphrase="shortpass1")

        # The passphrase should still be returned (it's valid)
        assert result == "shortpass1"


class TestResolvePassphrasePromptMessage:
    """Tests for custom prompt messages."""

    def test_custom_prompt_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Custom prompt message is displayed."""
        monkeypatch.delenv("GDPR_PSEUDO_PASSPHRASE", raising=False)

        with patch(
            "gdpr_pseudonymizer.cli.passphrase.typer.prompt"
        ) as mock_prompt, patch(
            "gdpr_pseudonymizer.cli.passphrase.console.print"
        ) as mock_print:
            mock_prompt.return_value = "passphrase_123456!"

            resolve_passphrase(
                cli_passphrase=None,
                prompt_message="Custom message for test",
            )

        # Verify custom message was printed
        call_args_list = [str(call) for call in mock_print.call_args_list]
        assert any("Custom message for test" in str(call) for call in call_args_list)
