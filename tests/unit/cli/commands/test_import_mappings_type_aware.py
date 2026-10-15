"""Story 10.7, AC4: import-mappings treats a duplicate as same text and same type.

A text stored in the target under another type is imported as its own row; a
pre-10.7 source and target are both converted when opened (AC3). Driven
through the CLI runner on real temporary databases. Invented names only
(AC11).
"""

from __future__ import annotations

from pathlib import Path

import typer
from helpers import strip_ansi
from typer.testing import CliRunner

from gdpr_pseudonymizer.cli.commands.import_mappings import import_mappings_command
from gdpr_pseudonymizer.data.database import init_database, open_database
from gdpr_pseudonymizer.data.models import Entity
from gdpr_pseudonymizer.data.repositories.mapping_repository import (
    SQLiteMappingRepository,
)
from tests.unit.pre_10_7_database import (
    LegacyRow,
    build_pre_10_7_database,
    read_schema_version,
)


def create_test_app() -> typer.Typer:
    app = typer.Typer()

    @app.callback()
    def callback() -> None:
        pass

    app.command(name="import-mappings")(import_mappings_command)
    return app


app = create_test_app()
runner = CliRunner()

SOURCE_PASSPHRASE = "zorbalia_source_pass_123!"
TARGET_PASSPHRASE = "quentrix_target_pass_456!"


def _new_db(path: Path, passphrase: str, *rows: tuple[str, str, str]) -> Path:
    init_database(str(path), passphrase)
    with open_database(str(path), passphrase) as session:
        repo = SQLiteMappingRepository(session)
        for entity_type, name, pseudonym in rows:
            repo.save(
                Entity(
                    entity_type=entity_type,
                    full_name=name,
                    pseudonym_full=pseudonym,
                    theme="neutral",
                )
            )
    return path


def _rows(path: Path, passphrase: str) -> list[tuple[str, str, str]]:
    with open_database(str(path), passphrase) as session:
        return sorted(
            (e.full_name, e.entity_type, e.pseudonym_full)
            for e in SQLiteMappingRepository(session).find_all()
        )


def _import(
    source: Path, target: Path, *flags: str, answer: str | None = None
) -> tuple[int, str]:
    result = runner.invoke(
        app,
        [
            "import-mappings",
            str(source),
            "--db",
            str(target),
            "--passphrase",
            TARGET_PASSPHRASE,
            "--source-passphrase",
            SOURCE_PASSPHRASE,
            *flags,
        ],
        input=answer,
    )
    return result.exit_code, strip_ansi(result.output)


def test_same_text_other_type_is_imported(tmp_path: Path) -> None:
    source = _new_db(
        tmp_path / "source.db", SOURCE_PASSPHRASE, ("ORG", "Zorbaville", "Zorbtech")
    )
    target = _new_db(
        tmp_path / "target.db",
        TARGET_PASSPHRASE,
        ("LOCATION", "Zorbaville", "Quentrel"),
    )

    code, output = _import(source, target, answer="n\n")

    assert code == 0, output
    assert "Duplicate found" not in output
    assert _rows(target, TARGET_PASSPHRASE) == [
        ("Zorbaville", "LOCATION", "Quentrel"),
        ("Zorbaville", "ORG", "Zorbtech"),
    ]


def test_same_text_same_type_is_skipped(tmp_path: Path) -> None:
    source = _new_db(
        tmp_path / "source.db",
        SOURCE_PASSPHRASE,
        ("LOCATION", "Zorbaville", "Zorbtech"),
    )
    target = _new_db(
        tmp_path / "target.db",
        TARGET_PASSPHRASE,
        ("LOCATION", "Zorbaville", "Quentrel"),
    )

    code, output = _import(source, target)

    assert code == 0, output
    assert "Skipped:  1" in output
    assert _rows(target, TARGET_PASSPHRASE) == [("Zorbaville", "LOCATION", "Quentrel")]


def test_same_text_same_type_prompts_when_asked(tmp_path: Path) -> None:
    source = _new_db(
        tmp_path / "source.db",
        SOURCE_PASSPHRASE,
        ("LOCATION", "Zorbaville", "Zorbtech"),
    )
    target = _new_db(
        tmp_path / "target.db",
        TARGET_PASSPHRASE,
        ("LOCATION", "Zorbaville", "Quentrel"),
    )

    code, output = _import(source, target, "--no-skip-duplicates", answer="n\n")

    assert code == 0, output
    assert "Duplicate found" in output
    assert _rows(target, TARGET_PASSPHRASE) == [("Zorbaville", "LOCATION", "Quentrel")]


def test_pre_10_7_source_and_target_are_both_converted(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    build_pre_10_7_database(
        source, SOURCE_PASSPHRASE, [LegacyRow("ORG", "Zorbaville", "Zorbtech")]
    )
    build_pre_10_7_database(
        target, TARGET_PASSPHRASE, [LegacyRow("LOCATION", "Zorbaville", "Quentrel")]
    )

    code, output = _import(source, target, answer="n\n")

    assert code == 0, output
    assert read_schema_version(source) == "1.1.0"
    assert read_schema_version(target) == "1.1.0"
    assert _rows(target, TARGET_PASSPHRASE) == [
        ("Zorbaville", "LOCATION", "Quentrel"),
        ("Zorbaville", "ORG", "Zorbtech"),
    ]
