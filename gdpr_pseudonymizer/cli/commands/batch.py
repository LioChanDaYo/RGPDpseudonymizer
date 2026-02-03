"""Batch command for processing multiple documents.

This command processes multiple documents sequentially with progress indicators.
Parallel processing will be added in Story 3.3.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console, Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from gdpr_pseudonymizer.cli.formatters import format_error_message
from gdpr_pseudonymizer.cli.passphrase import resolve_passphrase
from gdpr_pseudonymizer.cli.progress import ETAColumn, ProgressTracker
from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database
from gdpr_pseudonymizer.utils.logger import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Rich console for output
console = Console()

# Supported file extensions
SUPPORTED_EXTENSIONS = [".txt", ".md"]


@dataclass
class BatchResult:
    """Result of batch processing."""

    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    total_entities: int = 0
    new_entities: int = 0
    reused_entities: int = 0
    total_time_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


def collect_files(input_path: Path, recursive: bool = False) -> list[Path]:
    """Collect files to process from directory or file list.

    Args:
        input_path: Directory path or file path
        recursive: Whether to search subdirectories

    Returns:
        List of file paths to process (excludes *_pseudonymized.* output files)
    """
    files: list[Path] = []

    if input_path.is_file():
        # Single file - exclude if it's already a pseudonymized output
        if (
            input_path.suffix.lower() in SUPPORTED_EXTENSIONS
            and "_pseudonymized" not in input_path.stem
        ):
            files.append(input_path)
    elif input_path.is_dir():
        # Directory - collect all supported files, excluding pseudonymized outputs
        pattern = "**/*" if recursive else "*"
        for ext in SUPPORTED_EXTENSIONS:
            for file_path in input_path.glob(f"{pattern}{ext}"):
                if "_pseudonymized" not in file_path.stem:
                    files.append(file_path)

    return sorted(files)


def batch_command(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
        help="Input directory or file path",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (defaults to same directory as input with _pseudonymized suffix)",
    ),
    theme: str = typer.Option(
        "neutral",
        "--theme",
        "-t",
        help="Pseudonym library theme (neutral/star_wars/lotr)",
    ),
    model: str = typer.Option(
        "spacy",
        "--model",
        "-m",
        help="NLP model name (spacy)",
    ),
    db_path: str = typer.Option(
        "mappings.db",
        "--db",
        help="Database file path",
    ),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help="Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="Process subdirectories recursively",
    ),
    continue_on_error: bool = typer.Option(
        True,
        "--continue-on-error/--stop-on-error",
        help="Continue processing on individual file errors (default: continue)",
    ),
) -> None:
    """Process multiple documents with pseudonymization.

    Processes all .txt and .md files in the specified directory or file list.
    Each file is processed sequentially with progress indicators.

    Output files are saved with '_pseudonymized' suffix in the output directory.

    Examples:
        # Process all files in a directory
        gdpr-pseudo batch ./documents/

        # Process recursively with custom output
        gdpr-pseudo batch ./documents/ -o ./output/ --recursive

        # Process with specific theme
        gdpr-pseudo batch ./documents/ --theme star_wars

        # Stop on first error
        gdpr-pseudo batch ./documents/ --stop-on-error
    """
    try:
        # Collect files to process
        files = collect_files(input_path, recursive)

        if not files:
            console.print(f"[yellow]No supported files found in {input_path}[/yellow]")
            console.print(
                f"[dim]Supported extensions: {', '.join(SUPPORTED_EXTENSIONS)}[/dim]"
            )
            sys.exit(1)

        console.print(f"\n[bold]Found {len(files)} file(s) to process[/bold]\n")

        # Validate theme
        valid_themes = ["neutral", "star_wars", "lotr"]
        if theme not in valid_themes:
            format_error_message(
                "Invalid Theme",
                f"Theme '{theme}' is not recognized.",
                f"Valid themes: {', '.join(valid_themes)}",
            )
            sys.exit(1)

        # Get passphrase
        resolved_passphrase = resolve_passphrase(
            cli_passphrase=passphrase,
            prompt_message="Enter passphrase for mapping database",
            confirm=False,
        )

        # Initialize database if needed
        db_file = Path(db_path)
        if not db_file.exists():
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Initializing database...", total=None)
                try:
                    init_database(db_path, resolved_passphrase)
                    progress.update(task, description="✓ Database initialized")
                except ValueError as e:
                    console.print(
                        f"\n[bold red]Database initialization failed:[/bold red] {e}"
                    )
                    sys.exit(1)
            console.print()

        # Initialize processor
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing processor...", total=None)
            try:
                processor = DocumentProcessor(
                    db_path=db_path,
                    passphrase=resolved_passphrase,
                    theme=theme,
                    model_name=model,
                )
                progress.update(task, description="✓ Processor initialized")
            except ValueError as e:
                console.print(f"\n[bold red]Error:[/bold red] {e}")
                if "passphrase" in str(e).lower():
                    console.print(
                        "[yellow]Hint:[/yellow] Check passphrase or delete database to reinitialize"
                    )
                sys.exit(1)

        console.print()

        # Process files with progress bar
        batch_result = BatchResult(total_files=len(files))
        progress_tracker = ProgressTracker(total_files=len(files))
        start_time = time.time()

        # Create progress bar with ETA display
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("["),
            TimeElapsedColumn(),
            ETAColumn(),
            TextColumn("]"),
            expand=False,
        )
        task = progress.add_task(
            "Processing Batch...",
            total=len(files),
            eta="calculating...",
        )

        # Current file and stats displays
        current_file_text = Text("Current: ", style="dim")
        stats_text = Text("Entities: 0 | New: 0 | Reused: 0", style="dim")

        def make_progress_group() -> Group:
            """Create grouped display with progress bar and stats."""
            return Group(
                progress,
                current_file_text,
                stats_text,
            )

        with Live(
            make_progress_group(), console=console, refresh_per_second=10
        ) as live:
            for file_path in files:
                file_start_time = time.time()

                # Update current file being processed
                progress_tracker.set_current_file(file_path.name)

                # Truncate long filenames
                display_name = file_path.name
                if len(display_name) > 40:
                    display_name = "..." + display_name[-37:]
                current_file_text = Text(f"Current: {display_name}", style="cyan")

                live.update(make_progress_group())

                # Generate output path
                if output_dir:
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_file = (
                        output_dir / f"{file_path.stem}_pseudonymized{file_path.suffix}"
                    )
                else:
                    output_file = (
                        file_path.parent
                        / f"{file_path.stem}_pseudonymized{file_path.suffix}"
                    )

                try:
                    # Stop live display during document processing
                    # This allows the validation workflow UI to display properly
                    live.stop()

                    # Process document (includes interactive validation)
                    result = processor.process_document(
                        input_path=str(file_path),
                        output_path=str(output_file),
                    )

                    # Restart live display for progress updates
                    live.start()

                    file_processing_time = time.time() - file_start_time

                    if result.success:
                        batch_result.successful_files += 1
                        batch_result.total_entities += result.entities_detected
                        batch_result.new_entities += result.entities_new
                        batch_result.reused_entities += result.entities_reused

                        # Update progress tracker
                        progress_tracker.update_file_complete(
                            file_name=file_path.name,
                            processing_time=file_processing_time,
                            entities_detected=result.entities_detected,
                            pseudonyms_new=result.entities_new,
                            pseudonyms_reused=result.entities_reused,
                        )
                    else:
                        batch_result.failed_files += 1
                        batch_result.errors.append(
                            f"{file_path.name}: {result.error_message}"
                        )
                        # Still track time for failed files for ETA accuracy
                        progress_tracker.update_file_complete(
                            file_name=file_path.name,
                            processing_time=file_processing_time,
                            entities_detected=0,
                            pseudonyms_new=0,
                            pseudonyms_reused=0,
                        )

                        if not continue_on_error:
                            progress.update(task, description="✗ Processing stopped")
                            break

                except Exception as e:
                    # Ensure live display is restarted even on error
                    if not live.is_started:
                        live.start()

                    file_processing_time = time.time() - file_start_time
                    batch_result.failed_files += 1
                    batch_result.errors.append(f"{file_path.name}: {str(e)}")
                    logger.error(
                        "batch_file_error",
                        file=str(file_path),
                        error=str(e),
                    )
                    # Track time for failed files
                    progress_tracker.update_file_complete(
                        file_name=file_path.name,
                        processing_time=file_processing_time,
                        entities_detected=0,
                        pseudonyms_new=0,
                        pseudonyms_reused=0,
                    )

                    if not continue_on_error:
                        progress.update(task, description="✗ Processing stopped")
                        break

                # Update progress display with live stats
                entities = progress_tracker.entities_detected
                new_p = progress_tracker.pseudonyms_new
                reused_p = progress_tracker.pseudonyms_reused
                stats_text = Text(
                    f"Entities: {entities:,} | New: {new_p:,} | Reused: {reused_p:,}"
                )

                progress.update(task, eta=progress_tracker.calculate_eta())
                progress.advance(task)
                live.update(make_progress_group())

            # Completion state
            progress.update(task, description="✓ Processing complete")
            current_file_text = Text("")
            live.update(make_progress_group())

        batch_result.total_time_seconds = time.time() - start_time

        # Display summary report
        _display_batch_summary(batch_result)

        logger.info(
            "batch_complete",
            total_files=batch_result.total_files,
            successful=batch_result.successful_files,
            failed=batch_result.failed_files,
            total_entities=batch_result.total_entities,
            processing_time=batch_result.total_time_seconds,
        )

        # Exit with error code if any files failed
        if batch_result.failed_files > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Batch processing cancelled by user[/yellow]")
        logger.info("batch_cancelled", reason="keyboard_interrupt")
        sys.exit(0)

    except Exception as e:
        logger.error("batch_error", error=str(e), error_type=type(e).__name__)
        format_error_message(
            "Batch Processing Error",
            str(e),
            "Check file permissions and try again.",
        )
        sys.exit(2)


def _display_batch_summary(result: BatchResult) -> None:
    """Display batch processing summary report.

    Args:
        result: BatchResult with processing statistics
    """
    console.print("\n[bold]Batch Processing Summary[/bold]\n")

    # Create summary table
    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total files", str(result.total_files))
    table.add_row("Successful", f"[green]{result.successful_files}[/green]")
    if result.failed_files > 0:
        table.add_row("Failed", f"[red]{result.failed_files}[/red]")
    table.add_row("", "")
    table.add_row("Total entities", str(result.total_entities))
    table.add_row("New entities", str(result.new_entities))
    table.add_row("Reused entities", str(result.reused_entities))
    table.add_row("", "")
    table.add_row("Processing time", f"{result.total_time_seconds:.2f}s")

    if result.total_files > 0:
        avg_time = result.total_time_seconds / result.total_files
        table.add_row("Avg time/file", f"{avg_time:.2f}s")

    console.print(table)

    # Display errors if any
    if result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for error in result.errors[:10]:  # Show first 10 errors
            console.print(f"  • {error}")
        if len(result.errors) > 10:
            console.print(f"  ... and {len(result.errors) - 10} more errors")

    # Final status
    console.print()
    if result.failed_files == 0:
        console.print("[bold green]✓ All files processed successfully[/bold green]")
    elif result.successful_files > 0:
        console.print(
            f"[bold yellow]⚠ {result.successful_files}/{result.total_files} files processed successfully[/bold yellow]"
        )
    else:
        console.print("[bold red]✗ All files failed to process[/bold red]")
