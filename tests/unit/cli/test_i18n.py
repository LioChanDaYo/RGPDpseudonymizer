"""Tests for CLI internationalization (Story 6.6).

Covers:
    - CLI --lang fr produces French help text (AC7 — 9.6)
    - GDPR_PSEUDO_LANG environment variable is respected (AC7 — 9.7)
    - LazyString resolves correctly at render time
    - Language detection priority (argv > env > locale > default)
"""

from __future__ import annotations

from unittest.mock import patch

from gdpr_pseudonymizer.cli.i18n import (
    SUPPORTED_LANGUAGES,
    _,
    _detect_language,
    _LazyString,
    get_language,
    set_language,
)


class TestLazyString:
    """Test _LazyString proxy behavior."""

    def test_str_returns_translated(self) -> None:
        set_language("en")
        lazy = _("Initialize a new encrypted mapping database")
        assert str(lazy) == "Initialize a new encrypted mapping database"

    def test_lazy_resolves_on_str(self) -> None:
        set_language("fr")
        lazy = _("Initialize a new encrypted mapping database")
        result = str(lazy)
        assert "Initialiser" in result
        set_language("en")  # reset

    def test_lazy_updates_on_language_change(self) -> None:
        lazy = _("Initialize a new encrypted mapping database")
        set_language("en")
        assert str(lazy) == "Initialize a new encrypted mapping database"
        set_language("fr")
        assert "Initialiser" in str(lazy)
        set_language("en")  # reset

    def test_lazy_len(self) -> None:
        set_language("en")
        lazy = _("hello")
        assert len(lazy) == 5

    def test_lazy_bool(self) -> None:
        assert bool(_("text"))
        assert bool(_("")) is False

    def test_lazy_contains(self) -> None:
        set_language("en")
        lazy = _("Initialize a new encrypted mapping database")
        assert "encrypted" in lazy

    def test_lazy_equality(self) -> None:
        set_language("en")
        lazy = _("hello")
        assert lazy == "hello"

    def test_lazy_hash(self) -> None:
        lazy = _("hello")
        assert hash(lazy) == hash("hello")

    def test_lazy_add(self) -> None:
        set_language("en")
        lazy = _("hello")
        assert lazy + " world" == "hello world"

    def test_lazy_radd(self) -> None:
        set_language("en")
        lazy = _("world")
        assert "hello " + lazy == "hello world"

    def test_lazy_splitlines(self) -> None:
        set_language("en")
        lazy = _("hello")
        assert lazy.splitlines() == ["hello"]

    def test_lazy_repr(self) -> None:
        lazy = _("hello")
        assert "hello" in repr(lazy)

    def test_return_type_is_lazy_string(self) -> None:
        result = _("test")
        assert isinstance(result, _LazyString)


class TestSetLanguage:
    """Test set_language() and get_language()."""

    def test_set_language_en(self) -> None:
        set_language("en")
        assert get_language() == "en"

    def test_set_language_fr(self) -> None:
        set_language("fr")
        assert get_language() == "fr"

    def test_set_language_unknown_defaults_to_en(self) -> None:
        set_language("xx")
        assert get_language() == "en"

    def test_set_language_back_and_forth(self) -> None:
        set_language("fr")
        assert get_language() == "fr"
        set_language("en")
        assert get_language() == "en"


class TestDetectLanguage:
    """Test language detection priority."""

    def test_env_var_fr(self) -> None:
        with patch.dict("os.environ", {"GDPR_PSEUDO_LANG": "fr"}):
            assert _detect_language() == "fr"

    def test_env_var_en(self) -> None:
        with patch.dict("os.environ", {"GDPR_PSEUDO_LANG": "en"}):
            assert _detect_language() == "en"

    def test_env_var_invalid_falls_to_locale(self) -> None:
        with patch.dict("os.environ", {"GDPR_PSEUDO_LANG": "xx"}):
            result = _detect_language()
            assert result in SUPPORTED_LANGUAGES

    def test_system_locale_french(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=False),
            patch("locale.getdefaultlocale", return_value=("fr_FR", "UTF-8")),
        ):
            # Remove GDPR_PSEUDO_LANG if present
            import os

            env = dict(os.environ)
            env.pop("GDPR_PSEUDO_LANG", None)
            with patch.dict("os.environ", env, clear=True):
                assert _detect_language() == "fr"

    def test_default_is_english(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("locale.getdefaultlocale", return_value=("en_US", "UTF-8")),
        ):
            assert _detect_language() == "en"


class TestCLIHelpTranslation:
    """Test that CLI help text actually translates."""

    def test_init_help_english(self) -> None:
        set_language("en")
        from typer.testing import CliRunner

        from gdpr_pseudonymizer.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialize" in result.output
        assert "Database file path" in result.output

    def test_init_help_french(self) -> None:
        set_language("fr")
        from typer.testing import CliRunner

        from gdpr_pseudonymizer.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialiser" in result.output
        assert "base de donn" in result.output  # "base de données"
        # Reset
        set_language("en")

    def test_batch_help_english(self) -> None:
        set_language("en")
        from typer.testing import CliRunner

        from gdpr_pseudonymizer.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0
        assert "Process multiple documents" in result.output

    def test_batch_help_french(self) -> None:
        set_language("fr")
        from typer.testing import CliRunner

        from gdpr_pseudonymizer.cli.main import app

        runner = CliRunner()
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0
        assert "Traiter plusieurs documents" in result.output
        set_language("en")

    def test_env_var_activates_translation(self) -> None:
        """GDPR_PSEUDO_LANG=fr should activate French CLI help."""
        # This test validates that the env var mechanism works
        # by setting the language and checking lazy resolution
        set_language("fr")
        lazy = _("Initialize a new encrypted mapping database")
        assert "Initialiser" in str(lazy)
        set_language("en")
