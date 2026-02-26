"""Background worker for database operations (list, search, delete, export).

Runs database queries and file I/O on a QThreadPool thread, emitting progress
signals for each stage. Supports cancellation via threading.Event.
"""

from __future__ import annotations

import csv
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PySide6.QtCore import QRunnable

from gdpr_pseudonymizer.gui.workers.signals import WorkerSignals
from gdpr_pseudonymizer.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ListEntitiesResult:
    """Result payload for the 'list' operation."""

    entities: list[Any] = field(default_factory=list)
    db_created_str: str = ""
    entity_count: int = 0
    last_op_str: str = ""


class DatabaseWorker(QRunnable):
    """Background worker for database screen operations.

    Supports four operation types: list, search, delete, export.
    Each operation opens its own database session (no shared state).

    On success: emits ``finished`` with operation-specific result.
    On failure: emits ``error`` with a user-friendly French message.
    """

    def __init__(
        self,
        operation: str,
        db_path: str = "",
        passphrase: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self._operation = operation
        self._db_path = db_path
        self._passphrase = passphrase
        self._kwargs = kwargs
        self._cancelled = threading.Event()
        self.is_passphrase_error = False
        self.setAutoDelete(True)

    def cancel(self) -> None:
        """Request cancellation. Thread-safe (threading.Event)."""
        self._cancelled.set()

    def run(self) -> None:
        """Execute the requested operation in a background thread."""
        try:
            if self._cancelled.is_set():
                return

            if self._operation == "list":
                self._list_entities()
            elif self._operation == "search":
                self._search_entities()
            elif self._operation == "delete":
                self._delete_entities()
            elif self._operation == "export":
                self._export_csv()
            else:
                logger.error("database_worker_unknown_op", operation=self._operation)
                self.signals.error.emit("Opération inconnue.")
        except Exception as e:
            if self._cancelled.is_set():
                return
            logger.error(
                "database_worker_unexpected",
                error=repr(e),
                error_type=type(e).__name__,
            )
            self.signals.error.emit("Une erreur inattendue s'est produite.")

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def _list_entities(self) -> None:
        """Load all entities + DB info from the database."""
        from gdpr_pseudonymizer.data.database import open_database
        from gdpr_pseudonymizer.data.repositories.audit_repository import (
            AuditRepository,
        )
        from gdpr_pseudonymizer.data.repositories.mapping_repository import (
            SQLiteMappingRepository,
        )
        from gdpr_pseudonymizer.exceptions import (
            CorruptedDatabaseError,
            DatabaseError,
            EncryptionError,
        )

        self.signals.progress.emit(10, "Ouverture de la base de données...")

        if self._cancelled.is_set():
            return

        try:
            with open_database(self._db_path, self._passphrase) as db_session:
                if self._cancelled.is_set():
                    return

                self.signals.progress.emit(30, "Chargement des entités...")

                repo = SQLiteMappingRepository(db_session)
                entities = repo.find_all()

                if self._cancelled.is_set():
                    return

                self.signals.progress.emit(70, "Lecture des métadonnées...")

                # DB file creation date
                db_file = Path(self._db_path)
                created = datetime.fromtimestamp(db_file.stat().st_ctime)
                db_created_str = created.strftime("%d/%m/%Y")

                # Last audit operation
                audit_repo = AuditRepository(db_session.session)
                last_ops = audit_repo.find_operations(limit=1)
                if last_ops:
                    last_op_time = last_ops[0].timestamp
                    if last_op_time.tzinfo is None:
                        last_op_time = last_op_time.replace(tzinfo=timezone.utc)
                    delta = datetime.now(timezone.utc) - last_op_time
                    if delta.days == 0:
                        last_op_str = "aujourd'hui"
                    elif delta.days == 1:
                        last_op_str = "hier"
                    else:
                        last_op_str = f"il y a {delta.days} jours"
                else:
                    last_op_str = "aucune"

            if self._cancelled.is_set():
                return

            self.signals.progress.emit(100, "Terminé")
            self.signals.finished.emit(
                ListEntitiesResult(
                    entities=entities,
                    db_created_str=db_created_str,
                    entity_count=len(entities),
                    last_op_str=last_op_str,
                )
            )

        except ValueError:
            if self._cancelled.is_set():
                return
            self.is_passphrase_error = True
            self.signals.error.emit("Phrase secrète incorrecte.")

        except EncryptionError:
            if self._cancelled.is_set():
                return
            self.signals.error.emit(
                "Erreur de déchiffrement. Les données sont peut-être corrompues."
            )

        except CorruptedDatabaseError:
            if self._cancelled.is_set():
                return
            self.signals.error.emit("La base de données est corrompue ou invalide.")

        except DatabaseError as e:
            if self._cancelled.is_set():
                return
            logger.error("db_list_failed", error=str(e))
            self.signals.error.emit("Erreur lors de l'accès à la base de données.")

        except OSError as e:
            if self._cancelled.is_set():
                return
            logger.error("db_list_io_error", error=str(e))
            self.signals.error.emit(
                "Impossible d'accéder au fichier de base de données."
            )

        except Exception as e:
            if self._cancelled.is_set():
                return
            logger.error(
                "db_list_unexpected",
                error=repr(e),
                error_type=type(e).__name__,
            )
            self.signals.error.emit(
                "Erreur lors du chargement : données chiffrées corrompues "
                "ou base de données incompatible."
            )

    def _search_entities(self) -> None:
        """Filter an in-memory entity list on the worker thread."""
        entities: list[Any] = self._kwargs.get("entities", [])
        search_text: str = self._kwargs.get("search_text", "")
        type_filter: str = self._kwargs.get("type_filter", "")

        self.signals.progress.emit(10, "Filtrage en cours...")

        if self._cancelled.is_set():
            return

        filtered = entities
        if type_filter:
            filtered = [e for e in filtered if e.entity_type == type_filter]

        if self._cancelled.is_set():
            return

        if search_text:
            search_lower = search_text.lower()
            filtered = [
                e
                for e in filtered
                if search_lower in e.full_name.lower()
                or search_lower in e.pseudonym_full.lower()
            ]

        if self._cancelled.is_set():
            return

        self.signals.progress.emit(100, "Terminé")
        self.signals.finished.emit(filtered)

    def _delete_entities(self) -> None:
        """Delete entities by ID and log ERASURE audit operation."""
        from gdpr_pseudonymizer.data.database import open_database
        from gdpr_pseudonymizer.data.models import Operation
        from gdpr_pseudonymizer.data.repositories.audit_repository import (
            AuditRepository,
        )
        from gdpr_pseudonymizer.data.repositories.mapping_repository import (
            SQLiteMappingRepository,
        )
        from gdpr_pseudonymizer.exceptions import (
            CorruptedDatabaseError,
            DatabaseError,
            EncryptionError,
        )

        entity_ids: list[str] = self._kwargs.get("entity_ids", [])
        total = len(entity_ids)
        if total == 0:
            self.signals.finished.emit(0)
            return

        self.signals.progress.emit(5, "Ouverture de la base de données...")

        if self._cancelled.is_set():
            return

        try:
            deleted_count = 0
            with open_database(self._db_path, self._passphrase) as db_session:
                repo = SQLiteMappingRepository(db_session)
                audit_repo = AuditRepository(db_session.session)

                for i, entity_id in enumerate(entity_ids):
                    if self._cancelled.is_set():
                        return

                    deleted = repo.delete_entity_by_id(entity_id)
                    if deleted:
                        deleted_count += 1

                    percent = int(5 + (85 * (i + 1) / total))
                    self.signals.progress.emit(
                        percent,
                        f"Suppression {i + 1}/{total}...",
                    )

                if self._cancelled.is_set():
                    return

                self.signals.progress.emit(95, "Journalisation de l'opération...")

                audit_repo.log_operation(
                    Operation(
                        operation_type="ERASURE",
                        files_processed=[],
                        model_name="gui",
                        model_version="1.0",
                        theme_selected="",
                        entity_count=deleted_count,
                        processing_time_seconds=0.0,
                        success=True,
                    )
                )

            if self._cancelled.is_set():
                return

            self.signals.progress.emit(100, "Terminé")
            self.signals.finished.emit(deleted_count)

        except ValueError:
            if self._cancelled.is_set():
                return
            self.is_passphrase_error = True
            self.signals.error.emit("Phrase secrète incorrecte.")

        except EncryptionError:
            if self._cancelled.is_set():
                return
            self.signals.error.emit(
                "Erreur de déchiffrement. Les données sont peut-être corrompues."
            )

        except CorruptedDatabaseError:
            if self._cancelled.is_set():
                return
            self.signals.error.emit("La base de données est corrompue ou invalide.")

        except DatabaseError as e:
            if self._cancelled.is_set():
                return
            logger.error("db_delete_failed", error=str(e))
            self.signals.error.emit("Erreur lors de la suppression des entités.")

        except OSError as e:
            if self._cancelled.is_set():
                return
            logger.error("db_delete_io_error", error=str(e))
            self.signals.error.emit(
                "Impossible d'accéder au fichier de base de données."
            )

        except Exception as e:
            if self._cancelled.is_set():
                return
            logger.error(
                "db_delete_unexpected",
                error=repr(e),
                error_type=type(e).__name__,
            )
            self.signals.error.emit(
                "Erreur inattendue lors de la suppression des entités."
            )

    def _export_csv(self) -> None:
        """Write entities to a CSV file."""
        filepath: str = self._kwargs.get("filepath", "")
        entities: list[Any] = self._kwargs.get("entities", [])
        total = len(entities)

        self.signals.progress.emit(5, "Préparation de l'export...")

        if self._cancelled.is_set():
            return

        try:
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "entity_id",
                        "entity_type",
                        "full_name",
                        "pseudonym_full",
                        "first_seen",
                    ]
                )

                for i, entity in enumerate(entities):
                    if self._cancelled.is_set():
                        return

                    ts = ""
                    if entity.first_seen_timestamp:
                        ts = entity.first_seen_timestamp.isoformat()
                    writer.writerow(
                        [
                            entity.id[:8] if entity.id else "",
                            entity.entity_type,
                            entity.full_name,
                            entity.pseudonym_full,
                            ts,
                        ]
                    )

                    if total > 0:
                        percent = int(5 + (90 * (i + 1) / total))
                        self.signals.progress.emit(
                            percent,
                            f"Export {i + 1}/{total}...",
                        )

            if self._cancelled.is_set():
                return

            self.signals.progress.emit(100, "Terminé")
            self.signals.finished.emit(True)

        except OSError as e:
            if self._cancelled.is_set():
                return
            logger.error("csv_export_failed", error=str(e))
            self.signals.error.emit("Erreur lors de l'écriture du fichier CSV.")
