"""Unit tests for progress tracking module.

Tests ProgressTracker, ProgressState, DisplayState, and custom rich columns.
"""

from __future__ import annotations

from rich.progress import Task
from rich.text import Text

from gdpr_pseudonymizer.cli.progress import (
    CurrentFileColumn,
    DisplayState,
    EntityStatsColumn,
    ETAColumn,
    ProgressState,
    ProgressTracker,
)


class TestProgressState:
    """Tests for ProgressState dataclass."""

    def test_default_initialization(self) -> None:
        """Test ProgressState initializes with default values."""
        state = ProgressState()

        assert state.current_file == ""
        assert state.files_completed == 0
        assert state.files_total == 0
        assert state.entities_detected == 0
        assert state.pseudonyms_new == 0
        assert state.pseudonyms_reused == 0
        assert state.file_times == []

    def test_custom_initialization(self) -> None:
        """Test ProgressState with custom values."""
        state = ProgressState(
            current_file="test.txt",
            files_completed=5,
            files_total=10,
            entities_detected=100,
            pseudonyms_new=50,
            pseudonyms_reused=50,
            file_times=[1.0, 2.0, 3.0],
        )

        assert state.current_file == "test.txt"
        assert state.files_completed == 5
        assert state.files_total == 10
        assert state.entities_detected == 100
        assert state.pseudonyms_new == 50
        assert state.pseudonyms_reused == 50
        assert state.file_times == [1.0, 2.0, 3.0]


class TestProgressTracker:
    """Tests for ProgressTracker class."""

    def test_initialization(self) -> None:
        """Test ProgressTracker initializes with correct total."""
        tracker = ProgressTracker(total_files=10)

        assert tracker.files_total == 10
        assert tracker.files_completed == 0
        assert tracker.entities_detected == 0
        assert tracker.pseudonyms_new == 0
        assert tracker.pseudonyms_reused == 0

    def test_set_current_file(self) -> None:
        """Test setting current file."""
        tracker = ProgressTracker(total_files=5)
        tracker.set_current_file("test_file.txt")

        assert tracker.state.current_file == "test_file.txt"

    def test_update_file_complete(self) -> None:
        """Test updating state after file completion."""
        tracker = ProgressTracker(total_files=10)

        tracker.update_file_complete(
            file_name="file1.txt",
            processing_time=2.5,
            entities_detected=10,
            pseudonyms_new=5,
            pseudonyms_reused=5,
        )

        assert tracker.files_completed == 1
        assert tracker.entities_detected == 10
        assert tracker.pseudonyms_new == 5
        assert tracker.pseudonyms_reused == 5
        assert tracker.state.file_times == [2.5]
        assert tracker.state.current_file == "file1.txt"

    def test_update_file_complete_accumulates(self) -> None:
        """Test that multiple file completions accumulate correctly."""
        tracker = ProgressTracker(total_files=10)

        tracker.update_file_complete(
            file_name="file1.txt",
            processing_time=2.0,
            entities_detected=10,
            pseudonyms_new=5,
            pseudonyms_reused=5,
        )
        tracker.update_file_complete(
            file_name="file2.txt",
            processing_time=3.0,
            entities_detected=15,
            pseudonyms_new=8,
            pseudonyms_reused=7,
        )

        assert tracker.files_completed == 2
        assert tracker.entities_detected == 25
        assert tracker.pseudonyms_new == 13
        assert tracker.pseudonyms_reused == 12
        assert tracker.state.file_times == [2.0, 3.0]

    def test_eta_calculation_first_file(self) -> None:
        """Test ETA returns 'calculating...' before first file completes."""
        tracker = ProgressTracker(total_files=10)

        eta = tracker.calculate_eta()

        assert eta == "calculating..."

    def test_eta_calculation_multiple_files(self) -> None:
        """Test ETA calculation with multiple completed files."""
        tracker = ProgressTracker(total_files=10)

        # Simulate 5 files completed, each taking ~2 seconds
        for i in range(5):
            tracker.update_file_complete(
                file_name=f"file_{i}.txt",
                processing_time=2.0,
                entities_detected=10,
                pseudonyms_new=5,
                pseudonyms_reused=5,
            )

        eta = tracker.calculate_eta()

        # 5 files remaining * 2 seconds avg = 10 seconds = "< 1m"
        assert eta == "< 1m"

    def test_eta_calculation_longer_estimate(self) -> None:
        """Test ETA returns minutes format for longer estimates."""
        tracker = ProgressTracker(total_files=10)

        # Simulate 2 files completed, each taking 60 seconds
        for i in range(2):
            tracker.update_file_complete(
                file_name=f"file_{i}.txt",
                processing_time=60.0,
                entities_detected=10,
                pseudonyms_new=5,
                pseudonyms_reused=5,
            )

        eta = tracker.calculate_eta()

        # 8 files remaining * 60 seconds avg = 480 seconds = 8m 0s
        assert eta == "8m 0s"

    def test_eta_calculation_variance_uses_rolling_average(self) -> None:
        """Test ETA uses rolling average of last 5 files for stability."""
        tracker = ProgressTracker(total_files=20)

        # First 5 files: slow (10 seconds each)
        for i in range(5):
            tracker.update_file_complete(
                file_name=f"slow_file_{i}.txt",
                processing_time=10.0,
                entities_detected=10,
                pseudonyms_new=5,
                pseudonyms_reused=5,
            )

        # Next 5 files: fast (2 seconds each)
        for i in range(5):
            tracker.update_file_complete(
                file_name=f"fast_file_{i}.txt",
                processing_time=2.0,
                entities_detected=10,
                pseudonyms_new=5,
                pseudonyms_reused=5,
            )

        eta = tracker.calculate_eta()

        # Rolling average uses last 5 files (2.0 seconds each)
        # 10 files remaining * 2 seconds = 20 seconds = "< 1m"
        assert eta == "< 1m"

    def test_format_duration_under_minute(self) -> None:
        """Test duration formatting for times under 1 minute."""
        tracker = ProgressTracker(total_files=10)

        assert tracker._format_duration(30) == "< 1m"
        assert tracker._format_duration(59) == "< 1m"

    def test_format_duration_minutes_and_seconds(self) -> None:
        """Test duration formatting for times over 1 minute."""
        tracker = ProgressTracker(total_files=10)

        assert tracker._format_duration(60) == "1m 0s"
        assert tracker._format_duration(90) == "1m 30s"
        assert tracker._format_duration(150) == "2m 30s"

    def test_format_elapsed_under_minute(self) -> None:
        """Test elapsed time formatting for times under 1 minute."""
        tracker = ProgressTracker(total_files=10)

        assert tracker.format_elapsed(30) == "30s"
        assert tracker.format_elapsed(59) == "59s"

    def test_format_elapsed_over_minute(self) -> None:
        """Test elapsed time formatting for times over 1 minute."""
        tracker = ProgressTracker(total_files=10)

        assert tracker.format_elapsed(60) == "1m 0s"
        assert tracker.format_elapsed(90) == "1m 30s"

    def test_get_display_state(self) -> None:
        """Test get_display_state returns formatted DisplayState."""
        tracker = ProgressTracker(total_files=10)

        # Complete some files
        tracker.update_file_complete(
            file_name="test_file.txt",
            processing_time=2.0,
            entities_detected=25,
            pseudonyms_new=15,
            pseudonyms_reused=10,
        )

        display = tracker.get_display_state(elapsed=30.0)

        assert isinstance(display, DisplayState)
        assert display.files_completed == 1
        assert display.files_total == 10
        assert display.entities_detected == 25
        assert display.pseudonyms_new == 15
        assert display.pseudonyms_reused == 10
        assert display.elapsed == 30.0
        assert display.eta == "< 1m"

    def test_get_display_state_truncates_long_filename(self) -> None:
        """Test display state truncates long filenames."""
        tracker = ProgressTracker(total_files=10)

        long_filename = (
            "this_is_a_very_long_filename_that_exceeds_thirty_characters.txt"
        )
        tracker.update_file_complete(
            file_name=long_filename,
            processing_time=2.0,
            entities_detected=10,
            pseudonyms_new=5,
            pseudonyms_reused=5,
        )

        display = tracker.get_display_state(elapsed=5.0)

        assert len(display.current_file) <= 30
        assert display.current_file.startswith("...")

    def test_progress_tracker_empty_batch(self) -> None:
        """Test edge case with zero total files."""
        tracker = ProgressTracker(total_files=0)

        assert tracker.files_total == 0
        assert tracker.files_completed == 0
        eta = tracker.calculate_eta()
        assert eta == "calculating..."


class TestCurrentFileColumn:
    """Tests for CurrentFileColumn rich progress column."""

    def test_render_short_filename(self) -> None:
        """Test rendering short filename."""
        column = CurrentFileColumn()

        # Create a mock task with fields
        task = _create_mock_task(current_file="test.txt")
        result = column.render(task)

        assert isinstance(result, Text)
        assert str(result) == "test.txt"

    def test_render_long_filename_truncated(self) -> None:
        """Test rendering truncates long filename."""
        column = CurrentFileColumn(max_length=20)

        long_name = "this_is_a_very_long_filename.txt"
        task = _create_mock_task(current_file=long_name)
        result = column.render(task)

        assert len(str(result)) <= 20
        assert str(result).startswith("...")

    def test_render_empty_filename(self) -> None:
        """Test rendering with no current file."""
        column = CurrentFileColumn()

        task = _create_mock_task(current_file="")
        result = column.render(task)

        assert str(result) == ""

    def test_render_missing_field(self) -> None:
        """Test rendering when field is missing."""
        column = CurrentFileColumn()

        task = _create_mock_task()  # No current_file field
        result = column.render(task)

        assert str(result) == ""


class TestEntityStatsColumn:
    """Tests for EntityStatsColumn rich progress column."""

    def test_render_stats(self) -> None:
        """Test rendering entity stats."""
        column = EntityStatsColumn()

        task = _create_mock_task(
            entities=1234,
            new_pseudonyms=567,
            reused_pseudonyms=678,
        )
        result = column.render(task)

        assert isinstance(result, Text)
        # Check for formatted numbers with thousands separators
        assert "1,234" in str(result)
        assert "567" in str(result)
        assert "678" in str(result)

    def test_render_zero_stats(self) -> None:
        """Test rendering with zero values."""
        column = EntityStatsColumn()

        task = _create_mock_task(
            entities=0,
            new_pseudonyms=0,
            reused_pseudonyms=0,
        )
        result = column.render(task)

        assert "Entities: 0" in str(result)
        assert "New: 0" in str(result)
        assert "Reused: 0" in str(result)

    def test_render_missing_fields(self) -> None:
        """Test rendering with missing fields defaults to zero."""
        column = EntityStatsColumn()

        task = _create_mock_task()  # No fields
        result = column.render(task)

        assert "Entities: 0" in str(result)


class TestETAColumn:
    """Tests for ETAColumn rich progress column."""

    def test_render_eta(self) -> None:
        """Test rendering ETA."""
        column = ETAColumn()

        task = _create_mock_task(eta="2m 30s")
        result = column.render(task)

        assert isinstance(result, Text)
        assert "2m 30s" in str(result)

    def test_render_calculating(self) -> None:
        """Test rendering 'calculating...' state."""
        column = ETAColumn()

        task = _create_mock_task(eta="calculating...")
        result = column.render(task)

        assert "calculating..." in str(result)

    def test_render_missing_field(self) -> None:
        """Test rendering with missing eta field."""
        column = ETAColumn()

        task = _create_mock_task()  # No eta field
        result = column.render(task)

        assert "calculating..." in str(result)


class TestColumnWidthConstraints:
    """Tests for column width constraints (80-char terminal)."""

    def test_current_file_column_max_width(self) -> None:
        """Test CurrentFileColumn respects max width."""
        column = CurrentFileColumn(max_length=30)

        # Very long filename
        long_name = "a" * 100
        task = _create_mock_task(current_file=long_name)
        result = column.render(task)

        assert len(str(result)) <= 30

    def test_entity_stats_column_format(self) -> None:
        """Test EntityStatsColumn format is consistent."""
        column = EntityStatsColumn()

        # Large numbers
        task = _create_mock_task(
            entities=999999,
            new_pseudonyms=888888,
            reused_pseudonyms=777777,
        )
        result = column.render(task)

        # Should contain formatted output (with separators)
        text = str(result)
        assert "Entities:" in text
        assert "New:" in text
        assert "Reused:" in text


def _create_mock_task(**fields: object) -> Task:
    """Create a mock Task with specified fields.

    Args:
        **fields: Field values to set on the task

    Returns:
        Mock Task object with fields attribute
    """

    class MockTask:
        """Mock Task for testing."""

        def __init__(self, task_fields: dict[str, object]) -> None:
            self.fields = task_fields

    return MockTask(fields)  # type: ignore[return-value]
