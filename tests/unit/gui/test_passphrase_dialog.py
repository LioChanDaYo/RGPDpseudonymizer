"""Tests for PassphraseDialog widget."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QLineEdit

from gdpr_pseudonymizer.gui.widgets.passphrase_dialog import (
    DB_FILENAME,
    PassphraseDialog,
)


class TestPassphraseDialogCreation:
    """Test dialog construction and UI elements."""

    def test_dialog_creates_with_defaults(self, qtbot):  # type: ignore[no-untyped-def]
        dialog = PassphraseDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Phrase secrète"
        assert dialog.passphrase_edit.echoMode() == QLineEdit.EchoMode.Password
        assert dialog.remember_check.isChecked()
        assert not dialog.confirm_button.isEnabled()

    def test_confirm_disabled_without_passphrase(self, qtbot):  # type: ignore[no-untyped-def]
        dialog = PassphraseDialog()
        qtbot.addWidget(dialog)
        assert not dialog.confirm_button.isEnabled()

    def test_confirm_enabled_with_passphrase_and_db(self, qtbot, tmp_path):  # type: ignore[no-untyped-def]
        db_file = tmp_path / DB_FILENAME
        db_file.touch()
        dialog = PassphraseDialog(file_directory=str(tmp_path))
        qtbot.addWidget(dialog)
        dialog.passphrase_edit.setText("my_secret")
        assert dialog.confirm_button.isEnabled()


class TestPassphraseDialogDBDetection:
    """Test auto-detection of .gdpr-pseudo.db files."""

    def test_detects_db_in_file_directory(self, qtbot, tmp_path):  # type: ignore[no-untyped-def]
        db_file = tmp_path / DB_FILENAME
        db_file.touch()
        dialog = PassphraseDialog(file_directory=str(tmp_path))
        qtbot.addWidget(dialog)
        # First item should be the detected DB path
        assert dialog.db_combo.itemData(0) == str(db_file)

    def test_detects_db_in_home_directory(self, qtbot, tmp_path):  # type: ignore[no-untyped-def]
        home_db = Path.home() / DB_FILENAME
        if home_db.exists():
            dialog = PassphraseDialog(file_directory=str(tmp_path))
            qtbot.addWidget(dialog)
            items = [
                dialog.db_combo.itemData(i) for i in range(dialog.db_combo.count())
            ]
            assert str(home_db) in items

    def test_detects_db_from_settings(self, qtbot, tmp_path):  # type: ignore[no-untyped-def]
        db_file = tmp_path / "custom.db"
        db_file.touch()
        config = {"default_db_path": str(db_file)}
        dialog = PassphraseDialog(config=config)
        qtbot.addWidget(dialog)
        items = [dialog.db_combo.itemData(i) for i in range(dialog.db_combo.count())]
        assert str(db_file) in items

    def test_no_db_detected_shows_hint(self, qtbot, tmp_path):  # type: ignore[no-untyped-def]
        # Use a directory that definitely has no .db file
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        dialog = PassphraseDialog(file_directory=str(empty_dir))
        qtbot.addWidget(dialog)
        hint_text = dialog._db_hint.text()
        assert "Aucune base" in hint_text or "créez" in hint_text


class TestPassphraseDialogResult:
    """Test dialog accept/cancel result."""

    def test_returns_result_on_accept(self, qtbot, tmp_path):  # type: ignore[no-untyped-def]
        db_file = tmp_path / DB_FILENAME
        db_file.touch()
        dialog = PassphraseDialog(file_directory=str(tmp_path))
        qtbot.addWidget(dialog)
        dialog.passphrase_edit.setText("test_pass")
        dialog._on_confirm()
        result = dialog.get_result()
        assert result is not None
        db_path, passphrase, remember = result
        assert db_path == str(db_file)
        assert passphrase == "test_pass"
        assert remember is True

    def test_returns_none_on_cancel(self, qtbot):  # type: ignore[no-untyped-def]
        dialog = PassphraseDialog()
        qtbot.addWidget(dialog)
        dialog.reject()
        assert dialog.get_result() is None

    def test_remember_unchecked(self, qtbot, tmp_path):  # type: ignore[no-untyped-def]
        db_file = tmp_path / DB_FILENAME
        db_file.touch()
        dialog = PassphraseDialog(file_directory=str(tmp_path))
        qtbot.addWidget(dialog)
        dialog.passphrase_edit.setText("pass")
        dialog.remember_check.setChecked(False)
        dialog._on_confirm()
        result = dialog.get_result()
        assert result is not None
        assert result[2] is False


class TestPassphraseDialogVisibility:
    """Test passphrase visibility toggle."""

    def test_toggle_shows_password(self, qtbot):  # type: ignore[no-untyped-def]
        dialog = PassphraseDialog()
        qtbot.addWidget(dialog)
        assert dialog.passphrase_edit.echoMode() == QLineEdit.EchoMode.Password
        dialog.visibility_button.setChecked(True)
        assert dialog.passphrase_edit.echoMode() == QLineEdit.EchoMode.Normal

    def test_toggle_hides_password(self, qtbot):  # type: ignore[no-untyped-def]
        dialog = PassphraseDialog()
        qtbot.addWidget(dialog)
        dialog.visibility_button.setChecked(True)
        dialog.visibility_button.setChecked(False)
        assert dialog.passphrase_edit.echoMode() == QLineEdit.EchoMode.Password


class TestPassphraseDialogBrowse:
    """Test browse and create new DB paths."""

    @patch(
        "gdpr_pseudonymizer.gui.widgets.passphrase_dialog.QFileDialog.getOpenFileName"
    )
    def test_browse_existing_db(self, mock_dialog, qtbot, tmp_path):  # type: ignore[no-untyped-def]
        db_file = tmp_path / "selected.db"
        db_file.touch()
        mock_dialog.return_value = (str(db_file), "")

        dialog = PassphraseDialog()
        qtbot.addWidget(dialog)

        # Find "Parcourir..." index
        browse_idx = -1
        for i in range(dialog.db_combo.count()):
            if dialog.db_combo.itemData(i) == "__browse__":
                browse_idx = i
                break
        assert browse_idx >= 0
        # Manually trigger handler since activated only fires from user interaction
        dialog._on_db_combo_changed(browse_idx)

        items = [dialog.db_combo.itemData(i) for i in range(dialog.db_combo.count())]
        assert str(db_file) in items

    @patch(
        "gdpr_pseudonymizer.gui.widgets.passphrase_dialog.QFileDialog.getSaveFileName"
    )
    def test_create_new_db(self, mock_dialog, qtbot, tmp_path):  # type: ignore[no-untyped-def]
        new_db = tmp_path / "new.db"
        mock_dialog.return_value = (str(new_db), "")

        dialog = PassphraseDialog()
        qtbot.addWidget(dialog)

        # Find "Créer une nouvelle base" index
        create_idx = -1
        for i in range(dialog.db_combo.count()):
            if dialog.db_combo.itemData(i) == "__create__":
                create_idx = i
                break
        assert create_idx >= 0
        # Manually trigger handler since auto-select may have already set this index
        dialog._on_db_combo_changed(create_idx)

        items = [dialog.db_combo.itemData(i) for i in range(dialog.db_combo.count())]
        assert str(new_db) in items
