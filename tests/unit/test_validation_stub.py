"""Unit tests for validation stub module."""

from __future__ import annotations

from pytest_mock import MockerFixture

from gdpr_pseudonymizer.cli.validation_stub import (
    confirm_processing,
    present_entities_for_validation,
)


def test_present_entities_for_validation_displays_table(
    mocker: MockerFixture,
) -> None:
    """Test entity presentation displays Rich table."""
    # Mock Rich console
    mock_console = mocker.patch("gdpr_pseudonymizer.cli.validation_stub.console")

    entities: list[tuple[str, str, int, int, str]] = [
        ("Marie Dubois", "PERSON", 0, 12, "Leia Organa"),
        ("Paris", "LOCATION", 20, 25, "Coruscant"),
    ]

    present_entities_for_validation(entities)

    # Verify console.print was called (table and summary displayed)
    assert mock_console.print.called
    assert mock_console.print.call_count >= 2  # At least table and summary


def test_present_entities_for_validation_handles_empty_list(
    mocker: MockerFixture,
) -> None:
    """Test entity presentation handles empty entity list."""
    # Mock Rich console
    mock_console = mocker.patch("gdpr_pseudonymizer.cli.validation_stub.console")

    entities: list[tuple[str, str, int, int, str]] = []

    present_entities_for_validation(entities)

    # Should display "No entities detected" message
    assert mock_console.print.called
    mock_console.print.assert_called_once()


def test_present_entities_for_validation_deduplicates_entities(
    mocker: MockerFixture,
) -> None:
    """Test entity presentation deduplicates entities for display."""
    # Mock Rich console and Table
    mocker.patch("gdpr_pseudonymizer.cli.validation_stub.console")
    mock_table_class = mocker.patch("gdpr_pseudonymizer.cli.validation_stub.Table")
    mock_table = mock_table_class.return_value

    # Multiple occurrences of same entity
    entities: list[tuple[str, str, int, int, str]] = [
        ("Marie Dubois", "PERSON", 0, 12, "Leia Organa"),
        ("Marie Dubois", "PERSON", 30, 42, "Leia Organa"),
        ("Paris", "LOCATION", 50, 55, "Coruscant"),
    ]

    present_entities_for_validation(entities)

    # Table should have 2 unique entities added (not 3)
    assert mock_table.add_row.call_count == 2


def test_present_entities_for_validation_shows_entity_counts(
    mocker: MockerFixture,
) -> None:
    """Test entity presentation shows total and unique counts."""
    # Mock Rich console
    mock_console = mocker.patch("gdpr_pseudonymizer.cli.validation_stub.console")

    entities: list[tuple[str, str, int, int, str]] = [
        ("Marie Dubois", "PERSON", 0, 12, "Leia Organa"),
        ("Marie Dubois", "PERSON", 30, 42, "Leia Organa"),
        ("Paris", "LOCATION", 50, 55, "Coruscant"),
    ]

    present_entities_for_validation(entities)

    # Should print total (3) and unique (2) counts
    assert mock_console.print.called
    # Verify count information is printed
    call_args_list = [str(call) for call in mock_console.print.call_args_list]
    call_args_str = " ".join(call_args_list)
    assert "3" in call_args_str  # Total entities
    assert "2" in call_args_str  # Unique entities


def test_confirm_processing_user_accepts(mocker: MockerFixture) -> None:
    """Test confirmation when user accepts (presses 'y')."""
    # Mock Rich Confirm.ask to simulate user pressing 'y'
    mock_confirm = mocker.patch("gdpr_pseudonymizer.cli.validation_stub.Confirm.ask")
    mock_confirm.return_value = True

    result = confirm_processing()

    assert result is True
    mock_confirm.assert_called_once_with("Confirm pseudonymization?")


def test_confirm_processing_user_rejects(mocker: MockerFixture) -> None:
    """Test confirmation when user rejects (presses 'n')."""
    # Mock Rich Confirm.ask to simulate user pressing 'n'
    mock_confirm = mocker.patch("gdpr_pseudonymizer.cli.validation_stub.Confirm.ask")
    mock_confirm.return_value = False

    result = confirm_processing()

    assert result is False
    mock_confirm.assert_called_once_with("Confirm pseudonymization?")


def test_present_entities_for_validation_with_all_entity_types(
    mocker: MockerFixture,
) -> None:
    """Test entity presentation with PERSON, LOCATION, and ORG entities."""
    # Mock Rich console and Table
    mocker.patch("gdpr_pseudonymizer.cli.validation_stub.console")
    mock_table_class = mocker.patch("gdpr_pseudonymizer.cli.validation_stub.Table")
    mock_table = mock_table_class.return_value

    entities: list[tuple[str, str, int, int, str]] = [
        ("Marie Dubois", "PERSON", 0, 12, "Leia Organa"),
        ("Paris", "LOCATION", 20, 25, "Coruscant"),
        ("Acme SA", "ORG", 30, 37, "Rebel Alliance"),
    ]

    present_entities_for_validation(entities)

    # Should add all 3 entities to table
    assert mock_table.add_row.call_count == 3

    # Verify entity information is passed to add_row
    calls = mock_table.add_row.call_args_list
    assert calls[0][0] == ("Marie Dubois", "PERSON", "Leia Organa")
    assert calls[1][0] == ("Paris", "LOCATION", "Coruscant")
    assert calls[2][0] == ("Acme SA", "ORG", "Rebel Alliance")


def test_present_entities_for_validation_table_configuration(
    mocker: MockerFixture,
) -> None:
    """Test entity presentation creates table with correct configuration."""
    # Mock Rich Table class
    mock_table_class = mocker.patch("gdpr_pseudonymizer.cli.validation_stub.Table")
    mocker.patch("gdpr_pseudonymizer.cli.validation_stub.console")

    entities: list[tuple[str, str, int, int, str]] = [
        ("Marie Dubois", "PERSON", 0, 12, "Leia Organa"),
    ]

    present_entities_for_validation(entities)

    # Verify Table was created with correct title
    mock_table_class.assert_called_once()
    call_kwargs = mock_table_class.call_args[1]
    assert call_kwargs["title"] == "Detected Entities"
    assert call_kwargs["show_header"] is True

    # Verify columns were added
    mock_table = mock_table_class.return_value
    assert mock_table.add_column.call_count == 3  # Entity, Type, Pseudonym


def test_validation_workflow_integration(mocker: MockerFixture) -> None:
    """Test complete validation workflow (present + confirm)."""
    # Mock Rich components
    mock_console = mocker.patch("gdpr_pseudonymizer.cli.validation_stub.console")
    mock_confirm = mocker.patch("gdpr_pseudonymizer.cli.validation_stub.Confirm.ask")
    mock_confirm.return_value = True

    entities: list[tuple[str, str, int, int, str]] = [
        ("Marie Dubois", "PERSON", 0, 12, "Leia Organa"),
        ("Paris", "LOCATION", 20, 25, "Coruscant"),
    ]

    # Present entities
    present_entities_for_validation(entities)
    assert mock_console.print.called

    # Confirm processing
    confirmed = confirm_processing()
    assert confirmed is True
    assert mock_confirm.called
