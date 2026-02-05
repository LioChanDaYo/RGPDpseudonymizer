"""Process command for single document pseudonymization (Production Implementation).

This module implements the production `process` command that performs complete
pseudonymization workflow with:
- Compositional pseudonymization logic (Epic 2.2)
- Encrypted mapping storage (Epic 2.4)
- Audit logging (Epic 2.5)
- Idempotent processing (FR19)
- Progress indicators (rich library)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from gdpr_pseudonymizer.cli.config import load_config
from gdpr_pseudonymizer.cli.formatters import format_error_message
from gdpr_pseudonymizer.cli.passphrase import resolve_passphrase
from gdpr_pseudonymizer.core.document_processor import DocumentProcessor
from gdpr_pseudonymizer.data.database import init_database
from gdpr_pseudonymizer.exceptions import FileProcessingError
from gdpr_pseudonymizer.utils.logger import configure_logging, get_logger

# Configure Windows console to handle Unicode encoding errors gracefully
# Skip reconfiguration when running under pytest to avoid interfering with capture
if sys.platform == "win32" and "pytest" not in sys.modules:
    import io

    # Reconfigure stdout to use UTF-8 with error replacement (instead of charmap)
    # This allows Unicode characters (spinners, Braille) to be replaced with '?' instead of crashing
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer,
            encoding="utf-8",
            errors="replace",  # Replace unsupported characters with '?'
            line_buffering=True,
        )
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Rich console for progress indicators
console = Console()


def process_command(
    input_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Input file path (.txt or .md)",
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (defaults to <input>_pseudonymized.ext)",
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
) -> None:
    """Process a single document with complete pseudonymization workflow.

    This command integrates all Epic 2 components:
    - Compositional pseudonymization logic (Story 2.2)
    - Encrypted mapping storage with idempotency (Story 2.4)
    - Comprehensive audit logging (Story 2.5)

    Features:
    - Idempotent processing: reprocessing same document reuses existing mappings
    - Encrypted storage: all entity mappings encrypted at rest
    - Audit trail: all operations logged for GDPR Article 30 compliance
    - Configuration support: defaults can be set in ~/.gdpr-pseudo.yaml or ./.gdpr-pseudo.yaml

    Args:
        input_file: Path to input document (.txt or .md)
        output_file: Path to output document (optional, defaults to <input>_pseudonymized.ext)
        theme: Pseudonym library theme (neutral/star_wars/lotr)
        model: NLP model name (spacy)
        db_path: Database file path (default: mappings.db)
        passphrase: Database passphrase (or use GDPR_PSEUDO_PASSPHRASE env var)

    Examples:
        gdpr-pseudo process input.txt
        gdpr-pseudo process input.txt -o output.txt
        gdpr-pseudo process input.txt -o output.txt --theme star_wars
        gdpr-pseudo process input.txt --db custom.db
    """
    try:
        # Load configuration (project > home > defaults)
        config = load_config()

        # Apply config defaults where CLI flags not specified
        effective_theme = theme if theme is not None else config.pseudonymization.theme
        effective_model = model if model is not None else config.pseudonymization.model
        effective_db_path = db_path if db_path is not None else config.database.path
        # Validate file extension
        allowed_extensions = [".txt", ".md"]
        if input_file.suffix.lower() not in allowed_extensions:
            format_error_message(
                "Invalid File Format",
                f"File extension '{input_file.suffix}' is not supported.",
                f"Supported formats: {', '.join(allowed_extensions)}",
            )
            sys.exit(1)

        # Generate default output filename if not provided
        if output_file is None:
            output_file = (
                input_file.parent
                / f"{input_file.stem}_pseudonymized{input_file.suffix}"
            )
            logger.info("using_default_output", output_file=str(output_file))

        # Validate theme
        valid_themes = ["neutral", "star_wars", "lotr"]
        if effective_theme not in valid_themes:
            format_error_message(
                "Invalid Theme",
                f"Theme '{effective_theme}' is not recognized.",
                f"Valid themes: {', '.join(valid_themes)}",
            )
            sys.exit(1)

        # Get passphrase (with warning if --passphrase flag used)
        passphrase = resolve_passphrase(cli_passphrase=passphrase)

        # Initialize database if it doesn't exist
        db_file = Path(effective_db_path)
        if not db_file.exists():
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "Initializing encrypted database...", total=None
                )
                try:
                    init_database(effective_db_path, passphrase)
                    progress.update(task, description="✓ Database initialized")
                except ValueError as e:
                    console.print(
                        f"[bold red]Database initialization failed:[/bold red] {e}"
                    )
                    sys.exit(1)
            console.print("[green]✓ New database created successfully[/green]\n")

        # Log processing start
        logger.info(
            "processing_started",
            input_file=str(input_file),
            output_file=str(output_file),
            theme=effective_theme,
            model=effective_model,
        )

        # Initialize processor with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing processor...", total=None)
            try:
                processor = DocumentProcessor(
                    db_path=effective_db_path,
                    passphrase=passphrase,
                    theme=effective_theme,
                    model_name=effective_model,
                )
                progress.update(task, description="✓ Processor initialized")
            except ValueError as e:
                console.print(f"\n[bold red]Error:[/bold red] {e}")
                if "passphrase" in str(e).lower():
                    console.print(
                        "[yellow]Hint:[/yellow] Check passphrase or delete database to reinitialize"
                    )
                sys.exit(1)

        # Process document (without progress bar to avoid interfering with interactive validation UI)
        console.print("\n[bold]Processing document...[/bold]")
        result = processor.process_document(
            input_path=str(input_file),
            output_path=str(output_file),
        )

        # Display results
        if result.success:
            console.print("\n[bold green]✓ Processing Successful[/bold green]\n")
            console.print(f"[bold]Input:[/bold]  {input_file}")
            console.print(f"[bold]Output:[/bold] {output_file}\n")

            # Processing statistics
            console.print("[bold]Processing Statistics:[/bold]")
            console.print(f"  • Entities detected: {result.entities_detected}")
            console.print(f"  • New entities:      {result.entities_new}")
            console.print(f"  • Reused entities:   {result.entities_reused}")
            console.print(
                f"  • Processing time:   {result.processing_time_seconds:.2f}s\n"
            )

            # Idempotency hint
            if result.entities_reused > 0:
                console.print(
                    f"[cyan]ℹ  {result.entities_reused} entity mapping(s) reused from database (idempotent processing)[/cyan]\n"
                )

            logger.info(
                "processing_complete",
                entities_detected=result.entities_detected,
                entities_new=result.entities_new,
                entities_reused=result.entities_reused,
            )

        else:
            # Processing failed
            console.print("\n[bold red]✗ Processing Failed[/bold red]\n")
            console.print(f"[bold]Error:[/bold] {result.error_message}\n")

            logger.error("processing_failed", error=result.error_message)
            sys.exit(1)

    except FileProcessingError as e:
        # Handle file I/O errors
        logger.error("file_processing_error", error=str(e))
        format_error_message(
            "File Processing Error",
            str(e),
            "Check file path and permissions.",
        )
        sys.exit(1)

    except KeyboardInterrupt:
        # User cancelled
        console.print("\n\n[yellow]Processing cancelled by user[/yellow]")
        logger.info("processing_cancelled", reason="keyboard_interrupt")
        sys.exit(0)

    except Exception as e:
        # Handle unexpected errors
        logger.error("unexpected_error", error=str(e), error_type=type(e).__name__)
        format_error_message(
            "Unexpected Error",
            str(e),
            "Please report this issue if it persists.",
        )
        sys.exit(2)
