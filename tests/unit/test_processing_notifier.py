"""Tests for DocumentProcessor notifier callback decoupling (R1)."""

from __future__ import annotations


def test_document_processor_instantiates_without_cli_dependencies() -> None:
    """DocumentProcessor can be created with no notifier (no CLI dependency)."""
    from gdpr_pseudonymizer.core.document_processor import DocumentProcessor

    processor = DocumentProcessor(
        db_path="test.db",
        passphrase="test_pass",
    )
    assert processor is not None
    assert processor._notifier is not None  # should be the no-op lambda


def test_document_processor_with_custom_notifier() -> None:
    """DocumentProcessor accepts a custom notifier callback."""
    from gdpr_pseudonymizer.core.document_processor import DocumentProcessor

    messages: list[str] = []

    def capture_notifier(msg: str) -> None:
        messages.append(msg)

    processor = DocumentProcessor(
        db_path="test.db",
        passphrase="test_pass",
        notifier=capture_notifier,
    )
    processor._notifier("test message")
    assert messages == ["test message"]


def test_null_notifier_is_noop() -> None:
    """Default notifier (None) produces a no-op that doesn't raise."""
    from gdpr_pseudonymizer.core.document_processor import DocumentProcessor

    processor = DocumentProcessor(
        db_path="test.db",
        passphrase="test_pass",
        notifier=None,
    )
    # Should not raise
    processor._notifier("this message goes nowhere")


def test_core_has_no_cli_imports() -> None:
    """Verify gdpr_pseudonymizer/core/ contains zero imports from cli/."""
    import ast
    from pathlib import Path

    core_dir = Path("gdpr_pseudonymizer/core")
    violations = []

    for py_file in core_dir.glob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "gdpr_pseudonymizer.cli" in node.module:
                    violations.append(f"{py_file.name}:{node.lineno}: {node.module}")

    assert violations == [], f"CLI imports found in core/: {violations}"
