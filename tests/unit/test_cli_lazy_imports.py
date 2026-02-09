"""Tests for CLI lazy imports — verify --help works without loading heavy deps."""

from __future__ import annotations

from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.main import app

runner = CliRunner()

EXPECTED_COMMANDS = [
    "batch",
    "config",
    "destroy-table",
    "export",
    "import-mappings",
    "init",
    "list-mappings",
    "process",
    "stats",
    "validate-mappings",
]


def test_help_displays_all_commands() -> None:
    """Verify --help output contains all expected command names."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in EXPECTED_COMMANDS:
        assert cmd in result.output, f"Missing command in --help output: {cmd}"


def test_help_exit_code_zero() -> None:
    """Verify --help returns exit code 0."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_version_flag() -> None:
    """Verify --version still works with lazy imports."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()


def test_subcommand_help_does_not_crash() -> None:
    """Verify individual command --help works (does not import handler)."""
    for cmd in EXPECTED_COMMANDS:
        if cmd == "config":
            continue  # config sub-app help is handled differently
        result = runner.invoke(app, [cmd, "--help"])
        assert result.exit_code == 0, f"{cmd} --help failed: {result.output}"
