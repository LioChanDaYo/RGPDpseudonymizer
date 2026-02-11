"""Batch command for processing multiple documents.

This command processes multiple documents with progress indicators.
Supports both sequential processing (with interactive validation) and
parallel processing (auto-accept mode) using multiprocessing.Pool.

Story 3.3: Added --workers parameter and parallel batch processing.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any, Optional

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

from gdpr_pseudonymizer.cli.config import load_config
from gdpr_pseudonymizer.cli.formatters import format_error_message, rich_notifier
from gdpr_pseudonymizer.cli.passphrase import resolve_passphrase
from gdpr_pseudonymizer.cli.progress import ETAColumn, ProgressTracker
from gdpr_pseudonymizer.cli.validators import (
    ensure_database,
    parse_entity_type_filter,
    validate_theme_or_exit,
)
from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
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


def _process_single_document_worker(
    args: tuple[str, str, str, str, str, str, Optional[str]],
) -> dict[str, Any]:
    """Worker function for parallel batch processing.

    Each worker initializes its own DocumentProcessor with separate
    SQLite connection, spaCy model, and encryption service.

    Args:
        args: Tuple of (input_path, output_path, db_path, passphrase, theme, model,
              entity_types_csv). entity_types_csv is a comma-separated string of
              entity types to filter, or None for all types.

    Returns:
        Dictionary with processing results:
        - success: bool
        - file: input document path
        - entities_detected: int (if success)
        - entities_new: int (if success)
        - entities_reused: int (if success)
        - processing_time: float (if success)
        - error: str (if failure)
    """
    input_path, output_path, db_path, passphrase, theme, model, entity_types_csv = args

    # Reconstruct entity_type_filter from CSV string (sets aren't picklable for multiprocessing)
    entity_type_filter: set[str] | None = None
    if entity_types_csv is not None:
        entity_type_filter = set(entity_types_csv.split(","))

    try:
        # Each worker initializes its own DocumentProcessor
        processor = DocumentProcessor(
            db_path=db_path,
            passphrase=passphrase,
            theme=theme,
            model_name=model,
            notifier=rich_notifier,
        )

        # Process document with validation SKIPPED (parallel mode has no stdin)
        result = processor.process_document(
            input_path,
            output_path,
            skip_validation=True,
            entity_type_filter=entity_type_filter,
        )

        return {
            "success": result.success,
            "file": input_path,
            "entities_detected": result.entities_detected,
            "entities_new": result.entities_new,
            "entities_reused": result.entities_reused,
            "processing_time": result.processing_time_seconds,
            "error": result.error_message if not result.success else None,
        }
    except Exception as e:
        return {
            "success": False,
            "file": input_path,
            "entities_detected": 0,
            "entities_new": 0,
            "entities_reused": 0,
            "processing_time": 0.0,
            "error": str(e),
        }


def _process_batch_parallel(
    files: list[Path],
    output_dir: Optional[Path],
    db_path: str,
    passphrase: str,
    theme: str,
    model: str,
    num_workers: int,
    entity_type_filter: Optional[set[str]] = None,
) -> BatchResult:
    """Process documents in parallel using multiprocessing pool.

    Args:
        files: List of input file paths
        output_dir: Output directory (None = same as input)
        db_path: Database file path
        passphrase: Encryption passphrase
        theme: Pseudonym library theme
        model: NLP model name
        num_workers: Number of worker processes
        entity_type_filter: Optional set of entity types to keep

    Returns:
        BatchResult with processing statistics
    """
    # Cap workers at cpu_count and 8
    effective_workers = min(cpu_count(), num_workers, 8)

    # Ensure at least 1 worker
    effective_workers = max(1, effective_workers)

    logger.info(
        "batch_parallel_start",
        total_files=len(files),
        requested_workers=num_workers,
        effective_workers=effective_workers,
        cpu_count=cpu_count(),
    )

    # Prepare arguments for each file
    # Convert set to CSV string for pickling across process boundaries
    entity_types_csv: Optional[str] = None
    if entity_type_filter is not None:
        entity_types_csv = ",".join(sorted(entity_type_filter))

    args_list: list[tuple[str, str, str, str, str, str, Optional[str]]] = []
    for file_path in files:
        if output_dir:
            out_file = output_dir / f"{file_path.stem}_pseudonymized{file_path.suffix}"
        else:
            out_file = (
                file_path.parent / f"{file_path.stem}_pseudonymized{file_path.suffix}"
            )
        args_list.append(
            (
                str(file_path),
                str(out_file),
                db_path,
                passphrase,
                theme,
                model,
                entity_types_csv,
            )
        )

    batch_result = BatchResult(total_files=len(files))
    start_time = time.time()

    # Create progress bar
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("["),
        TimeElapsedColumn(),
        TextColumn("]"),
        expand=False,
    )

    task = progress.add_task(
        f"Processing ({effective_workers} workers)...",
        total=len(files),
    )

    # Stats text for live display
    stats_text = Text(
        f"Entities: 0 | New: 0 | Reused: 0 | Workers: {effective_workers}",
        style="dim",
    )

    def make_progress_group() -> Group:
        return Group(progress, stats_text)

    with Live(make_progress_group(), console=console, refresh_per_second=4) as live:
        # Process in parallel using imap_unordered for real-time progress
        with Pool(processes=effective_workers) as pool:
            for result in pool.imap_unordered(
                _process_single_document_worker, args_list
            ):
                if result["success"]:
                    batch_result.successful_files += 1
                    batch_result.total_entities += result["entities_detected"]
                    batch_result.new_entities += result["entities_new"]
                    batch_result.reused_entities += result["entities_reused"]
                else:
                    batch_result.failed_files += 1
                    error_msg = result.get("error", "Unknown error")
                    file_name = Path(result["file"]).name
                    batch_result.errors.append(f"{file_name}: {error_msg}")

                # Update progress display
                stats_text = Text(
                    f"Entities: {batch_result.total_entities:,} | "
                    f"New: {batch_result.new_entities:,} | "
                    f"Reused: {batch_result.reused_entities:,} | "
                    f"Workers: {effective_workers}",
                    style="dim",
                )
                progress.advance(task)
                live.update(make_progress_group())

        # Completion state
        progress.update(task, description="✓ Processing complete")
        live.update(make_progress_group())

    batch_result.total_time_seconds = time.time() - start_time

    logger.info(
        "batch_parallel_complete",
        total_files=batch_result.total_files,
        successful=batch_result.successful_files,
        failed=batch_result.failed_files,
        total_entities=batch_result.total_entities,
        processing_time=batch_result.total_time_seconds,
        workers=effective_workers,
    )

    return batch_result


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
    theme: Optional[str] = typer.Option(
        None,
        "--theme",
        "-t",
        help="Pseudonym library theme (neutral/star_wars/lotr). Default from config.",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="NLP model name (spacy). Default from config.",
    ),
    db_path: Optional[str] = typer.Option(
        None,
        "--db",
        help="Database file path. Default from config.",
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
        "--continue-on-error/--no-continue-on-error",
        help="Continue processing on individual file errors (default: continue)",
    ),
    workers: Optional[int] = typer.Option(
        None,
        "--workers",
        "-w",
        min=1,
        max=8,
        help="Number of parallel workers (1=sequential with validation, 2-8=parallel without validation). Default from config.",
    ),
    entity_types: Optional[str] = typer.Option(
        None,
        "--entity-types",
        help="Filter entity types to process (comma-separated). Options: PERSON, LOCATION, ORG. Default: all types.",
    ),
) -> None:
    """Process multiple documents with pseudonymization.

    Processes all .txt and .md files in the specified directory or file list.

    With --workers 1 (sequential mode): Files are processed one at a time with
    interactive validation prompts for each entity detected.

    With --workers 2-8 (parallel mode): Files are processed in parallel using
    multiple worker processes. Interactive validation is SKIPPED in this mode
    (all entities are auto-accepted). Use this for large batches where manual
    review is not feasible.

    Output files are saved with '_pseudonymized' suffix in the output directory.

    Configuration support: Default values for theme, model, db, workers, and
    output_dir can be set in ~/.gdpr-pseudo.yaml or ./.gdpr-pseudo.yaml.
    Use 'gdpr-pseudo config' to view effective configuration.

    Examples:
        # Sequential processing with validation (explicit)
        gdpr-pseudo batch ./documents/ --workers 1

        # Parallel processing with 4 workers (default)
        gdpr-pseudo batch ./documents/

        # Parallel processing with 8 workers
        gdpr-pseudo batch ./documents/ --workers 8

        # Process recursively with custom output
        gdpr-pseudo batch ./documents/ -o ./output/ --recursive

        # Process with specific theme
        gdpr-pseudo batch ./documents/ --theme star_wars
    """
    try:
        # Load configuration (project > home > defaults)
        config = load_config()

        # Apply config defaults where CLI flags not specified
        effective_theme = theme if theme is not None else config.pseudonymization.theme
        effective_model = model if model is not None else config.pseudonymization.model
        effective_db_path = db_path if db_path is not None else config.database.path
        effective_workers = workers if workers is not None else config.batch.workers
        effective_output_dir = (
            output_dir
            if output_dir is not None
            else (Path(config.batch.output_dir) if config.batch.output_dir else None)
        )

        # Parse entity type filter
        entity_type_filter = parse_entity_type_filter(entity_types, console)

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
        validate_theme_or_exit(effective_theme)

        # Get passphrase
        resolved_passphrase = resolve_passphrase(
            cli_passphrase=passphrase,
            prompt_message="Enter passphrase for mapping database",
            confirm=False,
        )

        # Initialize database if needed
        ensure_database(effective_db_path, resolved_passphrase, console)

        # Determine processing mode based on workers parameter
        actual_workers = min(cpu_count(), effective_workers, 8)
        actual_workers = max(1, actual_workers)

        if actual_workers > 1:
            # PARALLEL MODE: Skip interactive validation
            console.print(
                "[yellow]Parallel mode:[/yellow] Skipping interactive validation "
                "(use --workers 1 for manual review)"
            )
            console.print(
                f"[dim]Using {actual_workers} worker processes "
                f"(requested: {effective_workers}, CPU count: {cpu_count()})[/dim]"
            )
            console.print()

            # Create output directory if specified
            if effective_output_dir:
                effective_output_dir.mkdir(parents=True, exist_ok=True)

            # Process in parallel
            batch_result = _process_batch_parallel(
                files=files,
                output_dir=effective_output_dir,
                db_path=effective_db_path,
                passphrase=resolved_passphrase,
                theme=effective_theme,
                model=effective_model,
                num_workers=effective_workers,
                entity_type_filter=entity_type_filter,
            )
        else:
            # SEQUENTIAL MODE: With interactive validation
            console.print("[dim]Sequential mode: Interactive validation enabled[/dim]")

            # Initialize processor for sequential mode only
            # (parallel mode workers create their own processors)
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as init_progress:
                init_task = init_progress.add_task(
                    "Initializing processor...", total=None
                )
                try:
                    processor = DocumentProcessor(
                        db_path=effective_db_path,
                        passphrase=resolved_passphrase,
                        theme=effective_theme,
                        model_name=effective_model,
                        notifier=rich_notifier,
                    )
                    init_progress.update(
                        init_task, description="✓ Processor initialized"
                    )
                except ValueError as e:
                    console.print(f"\n[bold red]Error:[/bold red] {e}")
                    if "passphrase" in str(e).lower():
                        console.print(
                            "[yellow]Hint:[/yellow] Check passphrase or "
                            "delete database to reinitialize"
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
                    if effective_output_dir:
                        effective_output_dir.mkdir(parents=True, exist_ok=True)
                        output_file = (
                            effective_output_dir
                            / f"{file_path.stem}_pseudonymized{file_path.suffix}"
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
                            entity_type_filter=entity_type_filter,
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
                                progress.update(
                                    task, description="✗ Processing stopped"
                                )
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
