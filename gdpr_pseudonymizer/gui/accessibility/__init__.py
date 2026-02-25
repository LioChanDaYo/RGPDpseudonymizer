"""Accessibility module for keyboard navigation and screen reader support."""

from gdpr_pseudonymizer.gui.accessibility.focus_manager import (
    setup_focus_order_batch,
    setup_focus_order_database,
    setup_focus_order_home,
    setup_focus_order_processing,
    setup_focus_order_results,
    setup_focus_order_settings,
    setup_focus_order_validation,
)

__all__ = [
    "setup_focus_order_home",
    "setup_focus_order_processing",
    "setup_focus_order_validation",
    "setup_focus_order_results",
    "setup_focus_order_batch",
    "setup_focus_order_database",
    "setup_focus_order_settings",
]
