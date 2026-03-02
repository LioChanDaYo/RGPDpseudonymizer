"""Unified entry point for standalone PyInstaller bundles.

Dispatches to GUI (default) or CLI when CLI-specific subcommands are
detected in sys.argv.  Also handles frozen-bundle resource path
resolution and spaCy model path setup.

This module is the Analysis entry point in ``gdpr-pseudo-gui.spec``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# CLI subcommands that trigger CLI mode instead of GUI
# ---------------------------------------------------------------------------
CLI_SUBCOMMANDS = frozenset(
    {
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
    }
)

# Flags that also indicate CLI intent
CLI_FLAGS = frozenset({"--cli", "--help", "-h", "--version"})


# ---------------------------------------------------------------------------
# Frozen-bundle helpers
# ---------------------------------------------------------------------------
def is_frozen() -> bool:
    """Return True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_bundle_dir() -> Path:
    """Return the PyInstaller bundle directory (or project root if not frozen)."""
    if is_frozen():
        # sys._MEIPASS is set by PyInstaller in both --onefile and --onedir modes
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    # Not frozen — return the project root (parent of scripts/)
    return Path(__file__).resolve().parent.parent


def resource_path(relative_path: str) -> Path:
    """Resolve a resource path that works in both frozen and non-frozen contexts.

    Parameters
    ----------
    relative_path:
        Path relative to the bundle root (e.g.
        ``"gdpr_pseudonymizer/resources/french_names.json"``).

    Returns
    -------
    Path
        Absolute path to the resource.
    """
    return get_bundle_dir() / relative_path


# ---------------------------------------------------------------------------
# spaCy model setup for frozen bundles
# ---------------------------------------------------------------------------
def _setup_spacy_model() -> None:
    """Configure spaCy to find the bundled fr_core_news_lg model.

    In frozen bundles, the model directory sits at the bundle root.
    We add the bundle dir to ``sys.path`` so that
    ``spacy.load("fr_core_news_lg")`` can import it as a package.
    """
    if not is_frozen():
        return

    bundle_dir = get_bundle_dir()
    model_path = bundle_dir / "fr_core_news_lg"

    if model_path.exists():
        bundle_str = str(bundle_dir)
        if bundle_str not in sys.path:
            sys.path.insert(0, bundle_str)


# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------
def _should_use_cli() -> bool:
    """Determine whether to route to CLI based on argv or executable name."""
    # If launched via the CLI executable (gdpr-pseudo, not gdpr-pseudonymizer),
    # always use CLI mode.
    exe_name = Path(sys.argv[0]).stem.lower() if sys.argv else ""
    if exe_name == "gdpr-pseudo":
        return True

    args = sys.argv[1:]

    if not args:
        return False

    # Explicit --cli flag
    if "--cli" in args:
        return True

    # First positional argument matches a known CLI subcommand
    for arg in args:
        if arg.startswith("-"):
            # --help / --version at top level → CLI handles these
            if arg in CLI_FLAGS:
                return True
            continue
        # First non-flag argument — check if it's a subcommand
        return arg in CLI_SUBCOMMANDS

    return False


def main() -> None:
    """Entry point: dispatch to CLI or GUI."""
    # Set up frozen-bundle paths
    _setup_spacy_model()

    if _should_use_cli():
        # Remove --cli flag if present (not a real Typer argument)
        if "--cli" in sys.argv:
            sys.argv.remove("--cli")

        from gdpr_pseudonymizer.cli.main import cli_main

        cli_main()
    else:
        from gdpr_pseudonymizer.gui.app import main as gui_main

        gui_main()


if __name__ == "__main__":
    # Required for multiprocessing in frozen PyInstaller bundles (e.g. batch CLI).
    # Must be called before any other code in the __main__ guard.
    import multiprocessing

    multiprocessing.freeze_support()
    main()
