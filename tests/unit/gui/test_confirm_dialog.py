"""Tests for ConfirmDialog: factory methods, button labels, focus."""

from __future__ import annotations

from gdpr_pseudonymizer.gui.widgets.confirm_dialog import ConfirmDialog


class TestDestructiveDialog:
    """Destructive confirmation dialog."""

    def test_factory_creates_dialog(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dlg = ConfirmDialog.destructive("Supprimer", "Êtes-vous sûr ?", "Supprimer")
        qtbot.addWidget(dlg)
        assert dlg.windowTitle() == "Supprimer"

    def test_confirm_button_label(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dlg = ConfirmDialog.destructive("T", "M", "Supprimer")
        qtbot.addWidget(dlg)
        assert dlg.confirm_button.text() == "Supprimer"

    def test_confirm_button_style(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dlg = ConfirmDialog.destructive("T", "M", "Supprimer")
        qtbot.addWidget(dlg)
        assert dlg.confirm_button.objectName() == "destructiveButton"

    def test_default_focus_on_cancel(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dlg = ConfirmDialog.destructive("T", "M", "Supprimer")
        qtbot.addWidget(dlg)
        # In headless test, hasFocus() may not work; check focusWidget instead
        assert dlg.focusWidget() is dlg.cancel_button


class TestProceedingDialog:
    """Proceeding confirmation dialog."""

    def test_factory_creates_dialog(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dlg = ConfirmDialog.proceeding(
            "Continuer", "Voulez-vous continuer ?", "Continuer"
        )
        qtbot.addWidget(dlg)
        assert dlg.windowTitle() == "Continuer"

    def test_confirm_button_no_destructive_style(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dlg = ConfirmDialog.proceeding("T", "M", "OK")
        qtbot.addWidget(dlg)
        assert dlg.confirm_button.objectName() != "destructiveButton"


class TestInformationalDialog:
    """Informational dialog (single dismiss button)."""

    def test_factory_creates_dialog(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dlg = ConfirmDialog.informational("Info", "Message d'information")
        qtbot.addWidget(dlg)
        assert dlg.windowTitle() == "Info"

    def test_cancel_button_hidden(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dlg = ConfirmDialog.informational("Info", "Message")
        qtbot.addWidget(dlg)
        assert dlg.cancel_button.isHidden()

    def test_default_dismiss_label(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dlg = ConfirmDialog.informational("Info", "Message")
        qtbot.addWidget(dlg)
        assert dlg.confirm_button.text() == "Fermer"

    def test_custom_dismiss_label(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dlg = ConfirmDialog.informational("Info", "Message", dismiss_label="Compris")
        qtbot.addWidget(dlg)
        assert dlg.confirm_button.text() == "Compris"
