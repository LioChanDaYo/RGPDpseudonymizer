"""Tests for the standalone entry point routing logic.

Validates that the unified entry point correctly dispatches to CLI
or GUI based on sys.argv contents.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module import helper — standalone_entry.py lives in scripts/, not in the
# package.  We import it dynamically to avoid path issues.
# ---------------------------------------------------------------------------
@pytest.fixture()
def standalone_entry():
    """Import standalone_entry module from scripts/."""
    from pathlib import Path

    scripts_dir = str(Path(__file__).resolve().parent.parent.parent / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    import importlib

    mod = importlib.import_module("standalone_entry")
    yield mod

    # Clean up sys.path addition
    if scripts_dir in sys.path:
        sys.path.remove(scripts_dir)


# =========================================================================
# _should_use_cli() tests
# =========================================================================
class TestShouldUseCli:
    """Test CLI vs GUI routing logic."""

    def test_no_args_returns_false(self, standalone_entry):
        """No arguments → GUI mode."""
        with patch.object(sys, "argv", ["gdpr-pseudonymizer"]):
            assert standalone_entry._should_use_cli() is False

    @pytest.mark.parametrize(
        "subcommand",
        [
            "init",
            "process",
            "batch",
            "list-mappings",
            "validate-mappings",
            "stats",
            "import-mappings",
            "export",
            "delete-mapping",
            "list-entities",
            "destroy-table",
            "config",
        ],
    )
    def test_cli_subcommands_detected(self, standalone_entry, subcommand):
        """Known CLI subcommands trigger CLI mode."""
        with patch.object(sys, "argv", ["gdpr-pseudonymizer", subcommand]):
            assert standalone_entry._should_use_cli() is True

    def test_cli_flag_triggers_cli(self, standalone_entry):
        """Explicit --cli flag triggers CLI mode."""
        with patch.object(sys, "argv", ["gdpr-pseudonymizer", "--cli", "process"]):
            assert standalone_entry._should_use_cli() is True

    def test_help_flag_triggers_cli(self, standalone_entry):
        """--help at top level triggers CLI mode."""
        with patch.object(sys, "argv", ["gdpr-pseudonymizer", "--help"]):
            assert standalone_entry._should_use_cli() is True

    def test_version_flag_triggers_cli(self, standalone_entry):
        """--version triggers CLI mode."""
        with patch.object(sys, "argv", ["gdpr-pseudonymizer", "--version"]):
            assert standalone_entry._should_use_cli() is True

    def test_unknown_arg_returns_false(self, standalone_entry):
        """Unknown first positional arg → GUI mode."""
        with patch.object(sys, "argv", ["gdpr-pseudonymizer", "unknown-command"]):
            assert standalone_entry._should_use_cli() is False

    def test_subcommand_with_options(self, standalone_entry):
        """Subcommand with additional options still triggers CLI."""
        with patch.object(
            sys, "argv", ["gdpr-pseudonymizer", "process", "file.txt", "-o", "out.txt"]
        ):
            assert standalone_entry._should_use_cli() is True

    def test_h_short_flag_triggers_cli(self, standalone_entry):
        """-h short help flag triggers CLI mode."""
        with patch.object(sys, "argv", ["gdpr-pseudonymizer", "-h"]):
            assert standalone_entry._should_use_cli() is True


# =========================================================================
# is_frozen() tests
# =========================================================================
class TestIsFrozen:
    """Test frozen-bundle detection."""

    def test_not_frozen_normally(self, standalone_entry):
        """Not frozen in normal Python execution."""
        assert standalone_entry.is_frozen() is False

    def test_frozen_when_sys_frozen_and_meipass(self, standalone_entry):
        """Frozen when both sys.frozen and sys._MEIPASS are set."""
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", "/tmp/bundle", create=True):
                assert standalone_entry.is_frozen() is True

    def test_not_frozen_without_meipass(self, standalone_entry):
        """Not frozen if sys.frozen is set but _MEIPASS is missing."""
        with patch.object(sys, "frozen", True, create=True):
            # Ensure _MEIPASS does not exist
            if hasattr(sys, "_MEIPASS"):
                delattr(sys, "_MEIPASS")
            assert standalone_entry.is_frozen() is False


# =========================================================================
# get_bundle_dir() tests
# =========================================================================
class TestGetBundleDir:
    """Test bundle directory resolution."""

    def test_non_frozen_returns_project_root(self, standalone_entry):
        """Non-frozen: returns parent of scripts/ directory."""
        from pathlib import Path

        result = standalone_entry.get_bundle_dir()
        # Should be the project root (parent of scripts/)
        assert result == Path(standalone_entry.__file__).resolve().parent.parent

    def test_frozen_returns_meipass(self, standalone_entry):
        """Frozen: returns sys._MEIPASS path."""
        from pathlib import Path

        fake_meipass = "/tmp/pyinstaller_bundle"
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", fake_meipass, create=True):
                result = standalone_entry.get_bundle_dir()
                assert result == Path(fake_meipass)


# =========================================================================
# resource_path() tests
# =========================================================================
class TestResourcePath:
    """Test resource path resolution."""

    def test_non_frozen_resource_path(self, standalone_entry):
        """Non-frozen: resource_path returns path relative to project root."""
        from pathlib import Path

        result = standalone_entry.resource_path(
            "gdpr_pseudonymizer/resources/french_names.json"
        )
        expected = (
            Path(standalone_entry.__file__).resolve().parent.parent
            / "gdpr_pseudonymizer"
            / "resources"
            / "french_names.json"
        )
        assert result == expected

    def test_frozen_resource_path(self, standalone_entry):
        """Frozen: resource_path returns path relative to _MEIPASS."""
        from pathlib import Path

        fake_meipass = "/tmp/pyinstaller_bundle"
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", fake_meipass, create=True):
                result = standalone_entry.resource_path(
                    "gdpr_pseudonymizer/resources/french_names.json"
                )
                expected = (
                    Path(fake_meipass)
                    / "gdpr_pseudonymizer"
                    / "resources"
                    / "french_names.json"
                )
                assert result == expected


# =========================================================================
# main() dispatch tests
# =========================================================================
class TestMainDispatch:
    """Test the main() function routes correctly."""

    def test_gui_mode_default(self, standalone_entry):
        """No args → launches GUI via main()."""
        mock_gui = MagicMock()
        mock_module = MagicMock()
        mock_module.main = mock_gui

        with patch.object(sys, "argv", ["gdpr-pseudonymizer"]):
            with patch("standalone_entry._setup_spacy_model"):
                with patch.dict(
                    "sys.modules", {"gdpr_pseudonymizer.gui.app": mock_module}
                ):
                    standalone_entry.main()

        mock_gui.assert_called_once()

    def test_cli_mode_removes_cli_flag(self, standalone_entry):
        """--cli flag is removed from sys.argv before CLI dispatch."""
        mock_cli = MagicMock()
        mock_module = MagicMock()
        mock_module.cli_main = mock_cli

        with patch.object(sys, "argv", ["gdpr-pseudonymizer", "--cli", "--help"]):
            with patch("standalone_entry._setup_spacy_model"):
                with patch.dict(
                    "sys.modules", {"gdpr_pseudonymizer.cli.main": mock_module}
                ):
                    standalone_entry.main()

            mock_cli.assert_called_once()
            # --cli should have been removed from sys.argv before cli_main was called
            assert "--cli" not in sys.argv
            assert "--help" in sys.argv


# =========================================================================
# _setup_spacy_model() tests
# =========================================================================
class TestSetupSpacyModel:
    """Test spaCy model path setup."""

    def test_no_op_when_not_frozen(self, standalone_entry):
        """Does nothing when not in frozen context."""
        original_path = list(sys.path)
        standalone_entry._setup_spacy_model()
        assert sys.path == original_path

    def test_adds_bundle_dir_to_path_when_frozen(self, standalone_entry, tmp_path):
        """Adds bundle dir to sys.path when frozen and model exists."""
        # Create fake model directory
        model_dir = tmp_path / "fr_core_news_lg"
        model_dir.mkdir()

        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", str(tmp_path), create=True):
                standalone_entry._setup_spacy_model()
                assert str(tmp_path) in sys.path

        # Clean up
        sys.path.remove(str(tmp_path))

    def test_no_op_when_frozen_but_model_missing(self, standalone_entry, tmp_path):
        """Does not modify sys.path when model directory is missing."""
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", str(tmp_path), create=True):
                standalone_entry._setup_spacy_model()

        # sys.path should not have tmp_path added
        assert str(tmp_path) not in sys.path
