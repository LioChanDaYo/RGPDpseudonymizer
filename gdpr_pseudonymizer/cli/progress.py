"""Progress tracking for batch processing.

This module provides progress tracking and ETA calculation for batch operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.progress import ProgressColumn, Task
from rich.text import Text


@dataclass
class ProgressState:
    """State container for batch progress tracking.

    Attributes:
        current_file: Name of file currently being processed
        files_completed: Number of files successfully processed
        files_total: Total number of files to process
        entities_detected: Cumulative count of entities detected
        pseudonyms_new: Cumulative count of new pseudonyms created
        pseudonyms_reused: Cumulative count of pseudonyms reused
        start_time: Processing start timestamp (not stored, tracked externally)
        file_times: List of processing times per file (seconds)
    """

    current_file: str = ""
    files_completed: int = 0
    files_total: int = 0
    entities_detected: int = 0
    pseudonyms_new: int = 0
    pseudonyms_reused: int = 0
    file_times: list[float] = field(default_factory=list)


@dataclass
class DisplayState:
    """Formatted state for progress display.

    Attributes:
        current_file: Truncated file name for display
        files_completed: Files completed count
        files_total: Total files count
        entities_detected: Total entities detected
        pseudonyms_new: New pseudonyms created
        pseudonyms_reused: Pseudonyms reused
        eta: Formatted ETA string
        elapsed: Total elapsed time in seconds
    """

    current_file: str
    files_completed: int
    files_total: int
    entities_detected: int
    pseudonyms_new: int
    pseudonyms_reused: int
    eta: str
    elapsed: float


class ProgressTracker:
    """Tracks progress state and calculates ETA for batch processing.

    Usage:
        tracker = ProgressTracker(total_files=10)
        for file in files:
            tracker.set_current_file(file.name)
            # process file...
            tracker.update_file_complete(
                file_name=file.name,
                processing_time=1.5,
                entities_detected=10,
                pseudonyms_new=5,
                pseudonyms_reused=5,
            )
        display = tracker.get_display_state(elapsed=30.0)
    """

    # Number of recent files to use for rolling average ETA
    ROLLING_WINDOW_SIZE = 5

    # Maximum file name length for display
    MAX_FILENAME_LENGTH = 30

    def __init__(self, total_files: int) -> None:
        """Initialize progress tracker.

        Args:
            total_files: Total number of files to process
        """
        self._state = ProgressState(files_total=total_files)

    @property
    def state(self) -> ProgressState:
        """Access current progress state."""
        return self._state

    @property
    def files_completed(self) -> int:
        """Number of files completed."""
        return self._state.files_completed

    @property
    def files_total(self) -> int:
        """Total number of files."""
        return self._state.files_total

    @property
    def entities_detected(self) -> int:
        """Total entities detected."""
        return self._state.entities_detected

    @property
    def pseudonyms_new(self) -> int:
        """Total new pseudonyms."""
        return self._state.pseudonyms_new

    @property
    def pseudonyms_reused(self) -> int:
        """Total reused pseudonyms."""
        return self._state.pseudonyms_reused

    def set_current_file(self, file_name: str) -> None:
        """Set the file currently being processed.

        Args:
            file_name: Name of file being processed
        """
        self._state.current_file = file_name

    def update_file_complete(
        self,
        file_name: str,
        processing_time: float,
        entities_detected: int,
        pseudonyms_new: int,
        pseudonyms_reused: int,
    ) -> None:
        """Update state after completing a file.

        Args:
            file_name: Name of completed file
            processing_time: Time taken to process file (seconds)
            entities_detected: Number of entities detected in file
            pseudonyms_new: Number of new pseudonyms created
            pseudonyms_reused: Number of pseudonyms reused
        """
        self._state.files_completed += 1
        self._state.entities_detected += entities_detected
        self._state.pseudonyms_new += pseudonyms_new
        self._state.pseudonyms_reused += pseudonyms_reused
        self._state.file_times.append(processing_time)
        self._state.current_file = file_name

    def calculate_eta(self) -> str:
        """Calculate estimated time remaining.

        Uses rolling average of last N files for stability.
        Returns 'calculating...' if no files have been completed yet.

        Returns:
            Formatted ETA string (e.g., '2m 30s', '< 1m', 'calculating...')
        """
        if self._state.files_completed == 0:
            return "calculating..."

        # Use rolling average of recent files for stability
        recent_times = self._state.file_times[-self.ROLLING_WINDOW_SIZE :]
        avg_time = sum(recent_times) / len(recent_times)

        files_remaining = self._state.files_total - self._state.files_completed
        eta_seconds = avg_time * files_remaining

        return self._format_duration(eta_seconds)

    def _format_duration(self, seconds: float) -> str:
        """Format duration as human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., '2m 30s', '< 1m')
        """
        if seconds < 60:
            return "< 1m"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"

    def get_display_state(self, elapsed: float) -> DisplayState:
        """Get formatted state for progress display.

        Args:
            elapsed: Total elapsed time in seconds

        Returns:
            DisplayState with formatted values for display
        """
        current_file = self._state.current_file
        if len(current_file) > self.MAX_FILENAME_LENGTH:
            current_file = "..." + current_file[-(self.MAX_FILENAME_LENGTH - 3) :]

        return DisplayState(
            current_file=current_file,
            files_completed=self._state.files_completed,
            files_total=self._state.files_total,
            entities_detected=self._state.entities_detected,
            pseudonyms_new=self._state.pseudonyms_new,
            pseudonyms_reused=self._state.pseudonyms_reused,
            eta=self.calculate_eta(),
            elapsed=elapsed,
        )

    def format_elapsed(self, seconds: float) -> str:
        """Format elapsed time for display.

        Args:
            seconds: Elapsed time in seconds

        Returns:
            Formatted string (e.g., '2m 30s')
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"


class CurrentFileColumn(ProgressColumn):
    """Display current file being processed.

    Shows the file name with truncation for long names.
    Reads from task.fields['current_file'].
    """

    max_length: int = 30

    def __init__(self, max_length: int = 30) -> None:
        """Initialize column.

        Args:
            max_length: Maximum file name length for display
        """
        super().__init__()
        self.max_length = max_length

    def render(self, task: Task) -> Text:
        """Render current file name.

        Args:
            task: Rich Task with fields

        Returns:
            Styled Text with file name
        """
        current_file = task.fields.get("current_file", "")
        if len(current_file) > self.max_length:
            current_file = "..." + current_file[-(self.max_length - 3) :]
        return Text(current_file, style="cyan")


class EntityStatsColumn(ProgressColumn):
    """Display entity statistics.

    Shows: 'Entities: X | New: Y | Reused: Z'
    Reads from task.fields['entities', 'new_pseudonyms', 'reused_pseudonyms'].
    """

    def render(self, task: Task) -> Text:
        """Render entity statistics.

        Args:
            task: Rich Task with fields

        Returns:
            Styled Text with entity stats
        """
        entities = task.fields.get("entities", 0)
        new_pseudonyms = task.fields.get("new_pseudonyms", 0)
        reused = task.fields.get("reused_pseudonyms", 0)

        # Format with thousands separators
        entities_str = f"{entities:,}"
        new_str = f"{new_pseudonyms:,}"
        reused_str = f"{reused:,}"

        return Text(f"Entities: {entities_str} | New: {new_str} | Reused: {reused_str}")


class ETAColumn(ProgressColumn):
    """Display estimated time remaining.

    Shows: '< Xm Ys' format.
    Reads from task.fields['eta'].
    """

    def render(self, task: Task) -> Text:
        """Render ETA.

        Args:
            task: Rich Task with fields

        Returns:
            Styled Text with ETA
        """
        eta = task.fields.get("eta", "calculating...")
        return Text(f"< {eta}", style="green")
