"""Keyboard shortcut definitions for all screens.

Centralizes shortcut key sequences for consistency and documentation.
All shortcuts follow platform conventions where applicable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ShortcutDefinition:
    """Definition of a keyboard shortcut."""

    key: str  # QKeySequence string (e.g., "Ctrl+O")
    action: str  # Human-readable action description
    context: str  # Screen or context where shortcut applies


# Global navigation shortcuts (available from most screens)
GLOBAL_SHORTCUTS = [
    ShortcutDefinition("Ctrl+O", "Ouvrir un fichier", "Global"),
    ShortcutDefinition("Ctrl+B", "Traitement par lot", "Global"),
    ShortcutDefinition("Ctrl+,", "Paramètres", "Global"),
    ShortcutDefinition("Ctrl+D", "Base de données", "Global"),
    ShortcutDefinition("F1", "Aide", "Global"),
]

# Home screen shortcuts
HOME_SHORTCUTS = [
    ShortcutDefinition("Ctrl+O", "Ouvrir un fichier", "Home"),
    ShortcutDefinition("Ctrl+B", "Ouvrir le traitement par lot", "Home"),
]

# Validation screen shortcuts
VALIDATION_SHORTCUTS = [
    # Navigation
    ShortcutDefinition("Tab", "Entité suivante", "Validation"),
    ShortcutDefinition("Shift+Tab", "Entité précédente", "Validation"),
    # Actions
    ShortcutDefinition("Enter", "Accepter l'entité courante", "Validation"),
    ShortcutDefinition("Delete", "Rejeter l'entité courante", "Validation"),
    ShortcutDefinition("Ctrl+A", "Accepter toutes les entités", "Validation"),
    ShortcutDefinition("Ctrl+R", "Rejeter toutes les entités", "Validation"),
    # Edit
    ShortcutDefinition("Ctrl+Z", "Annuler", "Validation"),
    ShortcutDefinition("Ctrl+Shift+Z", "Rétablir", "Validation"),
    ShortcutDefinition("Ctrl+Y", "Rétablir", "Validation"),
    ShortcutDefinition("Ctrl+F", "Rechercher", "Validation"),
]

# Results screen shortcuts
RESULTS_SHORTCUTS = [
    ShortcutDefinition("Ctrl+S", "Enregistrer le document", "Results"),
    ShortcutDefinition("Ctrl+N", "Nouveau document", "Results"),
    ShortcutDefinition("Ctrl+D", "Ouvrir la base de données", "Results"),
]

# Batch screen shortcuts
BATCH_SHORTCUTS = [
    ShortcutDefinition("Ctrl+O", "Parcourir le dossier", "Batch"),
    ShortcutDefinition("Ctrl+A", "Ajouter des fichiers", "Batch"),
    ShortcutDefinition("Ctrl+Return", "Démarrer le traitement", "Batch"),
]

# Database screen shortcuts
DATABASE_SHORTCUTS = [
    ShortcutDefinition("Ctrl+O", "Ouvrir une base de données", "Database"),
    ShortcutDefinition("Ctrl+F", "Rechercher", "Database"),
    ShortcutDefinition("Delete", "Supprimer l'entité sélectionnée", "Database"),
    ShortcutDefinition("Ctrl+E", "Exporter en CSV", "Database"),
]

# Settings screen shortcuts
SETTINGS_SHORTCUTS = [
    ShortcutDefinition("Ctrl+S", "Enregistrer les paramètres", "Settings"),
]


def get_all_shortcuts() -> dict[str, list[ShortcutDefinition]]:
    """Get all shortcut definitions organized by screen.

    Returns:
        Dictionary mapping screen names to their shortcut lists
    """
    return {
        "Global": GLOBAL_SHORTCUTS,
        "Home": HOME_SHORTCUTS,
        "Validation": VALIDATION_SHORTCUTS,
        "Results": RESULTS_SHORTCUTS,
        "Batch": BATCH_SHORTCUTS,
        "Database": DATABASE_SHORTCUTS,
        "Settings": SETTINGS_SHORTCUTS,
    }


def get_shortcuts_for_screen(screen_name: str) -> list[ShortcutDefinition]:
    """Get shortcuts for a specific screen.

    Args:
        screen_name: Name of the screen (e.g., "Validation")

    Returns:
        List of shortcut definitions for that screen
    """
    all_shortcuts = get_all_shortcuts()
    return all_shortcuts.get(screen_name, [])
