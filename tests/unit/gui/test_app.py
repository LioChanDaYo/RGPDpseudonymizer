"""Tests for GUI app entry point."""

from __future__ import annotations

from pathlib import Path


class TestPySide6ImportError:
    """Test PySide6 import error handling (BUG-UX-004 fix)."""

    def test_error_message_contains_both_install_methods(self) -> None:
        """Test error message includes both Poetry and pip installation commands."""
        # Read the app.py source code
        app_file = (
            Path(__file__).parent.parent.parent.parent
            / "gdpr_pseudonymizer"
            / "gui"
            / "app.py"
        )
        source = app_file.read_text(encoding="utf-8")

        # Verify both installation methods are present in the error message
        assert "poetry install --extras gui" in source
        assert "pip install gdpr-pseudonymizer[gui]" in source

        # Verify it's in the ImportError handling section
        assert "except ImportError:" in source
