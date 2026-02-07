"""Destroy-table command for secure database deletion.

This command implements secure deletion with 3-pass overwrite before deletion.

Security Hardening (Story 3.4):
- SQLite magic number verification (AC4)
- Symlink protection (AC4)
- Passphrase verification before destruction (AC4)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from gdpr_pseudonymizer.cli.formatters import (
    ErrorCode,
    format_error_message,
    format_styled_error,
)
from gdpr_pseudonymizer.utils.logger import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Rich console for output
console = Console()

# SQLite file format magic number (first 16 bytes)
SQLITE_MAGIC = b"SQLite format 3\x00"


def _verify_sqlite_file(file_path: Path) -> bool:
    """Verify file is a SQLite database by checking magic number (AC4).

    Args:
        file_path: Path to file to verify

    Returns:
        True if file has SQLite magic number, False otherwise
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(16)
        return header == SQLITE_MAGIC
    except Exception:
        return False


def _verify_not_symlink(file_path: Path) -> bool:
    """Check if file is a symbolic link (AC4).

    Args:
        file_path: Path to check

    Returns:
        True if file is NOT a symlink (safe to proceed), False if it IS a symlink
    """
    return not file_path.is_symlink()


def _verify_passphrase(db_path: Path, passphrase: str) -> bool:
    """Verify passphrase can decrypt the database (AC4).

    Attempts to open the database and verify the encryption canary.

    Args:
        db_path: Path to the encrypted database
        passphrase: Passphrase to verify

    Returns:
        True if passphrase is correct, False otherwise
    """
    try:
        from gdpr_pseudonymizer.data.database import open_database

        with open_database(str(db_path), passphrase) as session:
            # If we can open the database and the session is valid,
            # the passphrase is correct
            return session is not None
    except Exception:
        return False


def destroy_table_command(
    db_path: str = typer.Option(
        "mappings.db",
        "--db",
        help="Database file path to destroy",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt (use with caution)",
    ),
    passphrase: Optional[str] = typer.Option(
        None,
        "--passphrase",
        "-p",
        help="Passphrase to verify database ownership (recommended for safety)",
    ),
    skip_passphrase_check: bool = typer.Option(
        False,
        "--skip-passphrase-check",
        help="Skip passphrase verification (not recommended)",
    ),
) -> None:
    """Securely delete the mapping database.

    ⚠️  WARNING: This operation is IRREVERSIBLE!

    This command performs secure deletion with 3-pass overwrite:
    1. Overwrite with zeros
    2. Overwrite with ones
    3. Overwrite with random data
    4. Delete the file

    This ensures data cannot be recovered with standard recovery tools.

    Security Checks:
    - Verifies file is a valid SQLite database (prevents accidental deletion)
    - Rejects symbolic links (prevents following links to critical files)
    - Optionally verifies passphrase (ensures you're deleting the right database)

    Examples:
        # Delete with confirmation
        gdpr-pseudo destroy-table

        # Delete specific database
        gdpr-pseudo destroy-table --db project.db

        # Skip confirmation (dangerous!)
        gdpr-pseudo destroy-table --force

        # Verify passphrase before deletion (recommended)
        gdpr-pseudo destroy-table --passphrase
    """
    try:
        # Validate database exists
        db_file = Path(db_path)
        if not db_file.exists():
            format_styled_error(
                ErrorCode.DATABASE_NOT_FOUND,
                f"Database file not found: {db_file.absolute()}",
            )
            sys.exit(1)

        # Security check: Reject symbolic links (AC4)
        if not _verify_not_symlink(db_file):
            format_styled_error(
                ErrorCode.SYMLINK_REJECTED,
                f"Target is a symbolic link: {db_file.absolute()}",
            )
            logger.warning(
                "destroy_rejected_symlink",
                path=str(db_file.absolute()),
            )
            sys.exit(1)

        # Security check: Verify SQLite magic number (AC4)
        if not _verify_sqlite_file(db_file):
            format_styled_error(
                ErrorCode.NOT_SQLITE_FILE,
                f"File does not appear to be a SQLite database: {db_file.absolute()}",
            )
            logger.warning(
                "destroy_rejected_not_sqlite",
                path=str(db_file.absolute()),
            )
            sys.exit(1)

        # Get database size for display
        db_size = db_file.stat().st_size

        # Display warning
        console.print("\n[bold red]⚠️  WARNING: PERMANENT DATA LOSS[/bold red]\n")
        console.print("You are about to permanently destroy:")
        console.print(f"  [bold]Database:[/bold] {db_file.absolute()}")
        console.print(f"  [bold]Size:[/bold] {_format_size(db_size)}")
        console.print()
        console.print("[yellow]This action CANNOT be undone![/yellow]")
        console.print("All entity mappings and audit logs will be permanently deleted.")
        console.print()

        # Passphrase verification (AC4)
        if not skip_passphrase_check:
            # Prompt for passphrase if not provided
            if passphrase is None:
                passphrase = Prompt.ask(
                    "Enter passphrase to verify database ownership",
                    password=True,
                )

            if not _verify_passphrase(db_file, passphrase):
                format_styled_error(
                    ErrorCode.PASSPHRASE_VERIFICATION_FAILED,
                    "Could not verify database with provided passphrase. Destruction aborted.",
                )
                logger.warning(
                    "destroy_passphrase_verification_failed",
                    path=str(db_file.absolute()),
                )
                sys.exit(1)

            console.print("[green]Passphrase verified successfully.[/green]\n")
        else:
            console.print(
                "[yellow]Warning: Skipping passphrase verification as requested.[/yellow]\n"
            )

        # Confirmation
        if not force:
            confirmation = Prompt.ask(
                "Type 'yes' to confirm destruction",
                default="",
            )

            if confirmation.lower() != "yes":
                console.print(
                    "\n[green]Destruction cancelled. Database is safe.[/green]"
                )
                sys.exit(0)

        # Perform secure deletion
        console.print()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Performing secure deletion...", total=None)

            try:
                _secure_delete(db_file)
                progress.update(task, description="✓ Secure deletion complete")
            except Exception as e:
                progress.update(task, description="✗ Secure deletion failed")
                raise e

        # Also delete WAL and SHM files if they exist (SQLite journal files)
        wal_file = db_file.with_suffix(db_file.suffix + "-wal")
        shm_file = db_file.with_suffix(db_file.suffix + "-shm")

        if wal_file.exists():
            _secure_delete(wal_file)
            console.print(f"[dim]  Deleted WAL file: {wal_file.name}[/dim]")

        if shm_file.exists():
            _secure_delete(shm_file)
            console.print(f"[dim]  Deleted SHM file: {shm_file.name}[/dim]")

        console.print("\n[bold green]✓ Database Destroyed Successfully[/bold green]")
        console.print(
            f"\nThe database at {db_file.absolute()} has been securely deleted."
        )
        console.print(
            "Data has been overwritten with 3-pass secure wipe and cannot be recovered."
        )

        logger.info(
            "database_destroyed",
            path=str(db_file.absolute()),
            size=db_size,
        )

    except PermissionError:
        format_error_message(
            "Permission Denied",
            f"Cannot delete database file: {db_path}",
            "Check file permissions or close any applications using the database.",
        )
        sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n\n[green]Destruction cancelled. Database is safe.[/green]")
        logger.info("destroy_cancelled", reason="keyboard_interrupt")
        sys.exit(0)

    except Exception as e:
        logger.error("destroy_error", error=str(e), error_type=type(e).__name__)
        format_error_message(
            "Deletion Error",
            str(e),
            "Check file permissions and try again.",
        )
        sys.exit(2)


def _secure_delete(file_path: Path) -> None:
    """Securely delete file with 3-pass overwrite.

    Args:
        file_path: Path to file to delete

    Raises:
        OSError: If file operations fail
    """
    file_size = file_path.stat().st_size

    # Skip if file is empty
    if file_size == 0:
        file_path.unlink()
        return

    with open(file_path, "r+b") as f:
        # Pass 1: Overwrite with zeros
        f.seek(0)
        f.write(b"\x00" * file_size)
        f.flush()
        os.fsync(f.fileno())

        # Pass 2: Overwrite with ones
        f.seek(0)
        f.write(b"\xff" * file_size)
        f.flush()
        os.fsync(f.fileno())

        # Pass 3: Overwrite with random data
        f.seek(0)
        f.write(os.urandom(file_size))
        f.flush()
        os.fsync(f.fileno())

    # Delete file after overwrite
    file_path.unlink()


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string
    """
    size: float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
