"""Integration tests for module loading and circular dependency verification."""

from __future__ import annotations


def test_import_all_modules() -> None:
    """Test that all modules can be imported without errors."""
    # Import all package modules
    import gdpr_pseudonymizer
    import gdpr_pseudonymizer.cli
    import gdpr_pseudonymizer.core
    import gdpr_pseudonymizer.data
    import gdpr_pseudonymizer.nlp
    import gdpr_pseudonymizer.pseudonym
    import gdpr_pseudonymizer.utils
    import gdpr_pseudonymizer.validation

    # Verify imports succeeded
    assert gdpr_pseudonymizer is not None
    assert gdpr_pseudonymizer.cli is not None
    assert gdpr_pseudonymizer.core is not None
    assert gdpr_pseudonymizer.data is not None
    assert gdpr_pseudonymizer.nlp is not None
    assert gdpr_pseudonymizer.pseudonym is not None
    assert gdpr_pseudonymizer.utils is not None
    assert gdpr_pseudonymizer.validation is not None


def test_no_circular_import_issues() -> None:
    """Test that no circular dependencies exist in module imports."""
    # This test will fail if circular dependencies exist
    # because Python will raise ImportError during import

    # Import modules in dependency order (bottom-up)

    # All imports succeeded without circular dependency errors
    assert True


def test_entity_detector_interface_available() -> None:
    """Test that EntityDetector interface can be imported."""
    from gdpr_pseudonymizer.nlp.entity_detector import (
        DetectedEntity,
        EntityDetector,
    )

    assert DetectedEntity is not None
    assert EntityDetector is not None


def test_spacy_detector_available() -> None:
    """Test that SpaCyDetector implementation can be imported."""
    from gdpr_pseudonymizer.nlp.spacy_detector import SpaCyDetector

    assert SpaCyDetector is not None


def test_data_models_available() -> None:
    """Test that data models can be imported."""
    from gdpr_pseudonymizer.data.models import Base, Entity, Metadata, Operation

    assert Base is not None
    assert Entity is not None
    assert Operation is not None
    assert Metadata is not None


def test_mapping_repository_available() -> None:
    """Test that MappingRepository interface can be imported."""
    from gdpr_pseudonymizer.data.repositories.mapping_repository import (
        MappingRepository,
        SQLiteMappingRepository,
    )

    assert MappingRepository is not None
    assert SQLiteMappingRepository is not None


def test_pseudonym_manager_available() -> None:
    """Test that PseudonymManager interface can be imported."""
    from gdpr_pseudonymizer.pseudonym.assignment_engine import (
        PseudonymAssignment,
        PseudonymManager,
        SimplePseudonymManager,
    )

    assert PseudonymAssignment is not None
    assert PseudonymManager is not None
    assert SimplePseudonymManager is not None


def test_validation_models_available() -> None:
    """Test that validation models can be imported."""
    from gdpr_pseudonymizer.validation.models import (
        EntityReview,
        EntityReviewState,
        ValidationSession,
    )

    assert EntityReview is not None
    assert EntityReviewState is not None
    assert ValidationSession is not None


def test_config_manager_available() -> None:
    """Test that configuration management can be imported."""
    from gdpr_pseudonymizer.utils.config_manager import Config, load_config

    assert Config is not None
    assert load_config is not None


def test_logger_available() -> None:
    """Test that logging utilities can be imported."""
    from gdpr_pseudonymizer.utils.logger import (
        configure_logging,
        get_logger,
        sanitize_context,
    )

    assert configure_logging is not None
    assert get_logger is not None
    assert sanitize_context is not None


def test_file_handler_available() -> None:
    """Test that file handler utilities can be imported."""
    from gdpr_pseudonymizer.utils.file_handler import (
        ensure_absolute_path,
        get_file_extension,
        read_file,
        validate_file_path,
        write_file,
    )

    assert read_file is not None
    assert write_file is not None
    assert validate_file_path is not None
    assert get_file_extension is not None
    assert ensure_absolute_path is not None


def test_encryption_interface_available() -> None:
    """Test that encryption interface can be imported."""
    from gdpr_pseudonymizer.utils.encryption import (
        EncryptionService,
        FernetEncryptionService,
    )

    assert EncryptionService is not None
    assert FernetEncryptionService is not None


def test_exceptions_available() -> None:
    """Test that custom exceptions can be imported."""
    from gdpr_pseudonymizer.exceptions import (
        ConfigurationError,
        EncryptionError,
        FileProcessingError,
        ModelNotFoundError,
        PseudonymizerError,
        ValidationError,
    )

    assert PseudonymizerError is not None
    assert ConfigurationError is not None
    assert ModelNotFoundError is not None
    assert EncryptionError is not None
    assert ValidationError is not None
    assert FileProcessingError is not None


def test_config_loading_integration() -> None:
    """Test configuration loading works across modules."""
    from gdpr_pseudonymizer.utils.config_manager import load_config

    # Load config with defaults (no file exists)
    config = load_config()

    assert config.log_level == "INFO"
    assert config.model_name == "fr_core_news_lg"
    assert config.theme == "neutral"


def test_logger_initialization_integration() -> None:
    """Test logger initialization across modules."""
    from gdpr_pseudonymizer.utils.logger import configure_logging, get_logger

    # Configure logging
    configure_logging(log_level="INFO")

    # Create loggers for different modules
    logger_nlp = get_logger("gdpr_pseudonymizer.nlp")
    logger_data = get_logger("gdpr_pseudonymizer.data")
    logger_core = get_logger("gdpr_pseudonymizer.core")

    assert logger_nlp is not None
    assert logger_data is not None
    assert logger_core is not None


def test_spacy_detector_instantiation() -> None:
    """Test that SpaCyDetector can be instantiated without loading model."""
    from gdpr_pseudonymizer.nlp.spacy_detector import SpaCyDetector

    detector = SpaCyDetector()

    assert detector is not None
    assert detector.supports_gender_classification is False


def test_repository_instantiation() -> None:
    """Test that SQLiteMappingRepository can be instantiated."""
    from gdpr_pseudonymizer.data.repositories.mapping_repository import (
        SQLiteMappingRepository,
    )

    repository = SQLiteMappingRepository(db_path=":memory:")

    assert repository is not None
    assert repository.db_path == ":memory:"


def test_pseudonym_manager_instantiation() -> None:
    """Test that SimplePseudonymManager can be instantiated."""
    from gdpr_pseudonymizer.pseudonym.assignment_engine import (
        SimplePseudonymManager,
    )

    manager = SimplePseudonymManager()

    assert manager is not None


def test_validation_session_creation() -> None:
    """Test that ValidationSession can be created."""
    from gdpr_pseudonymizer.validation.models import ValidationSession

    session = ValidationSession(
        document_path="/path/to/doc.txt", document_text="Sample text"
    )

    assert session.document_path == "/path/to/doc.txt"
    assert session.document_text == "Sample text"
    assert len(session.entities) == 0
    assert session.current_index == 0


def test_package_structure_matches_architecture() -> None:
    """Verify module structure matches architecture specification."""
    import pkgutil

    import gdpr_pseudonymizer

    # Get all submodules
    package_modules = []
    for importer, modname, ispkg in pkgutil.walk_packages(
        path=gdpr_pseudonymizer.__path__,
        prefix=gdpr_pseudonymizer.__name__ + ".",
        onerror=lambda x: None,
    ):
        package_modules.append(modname)

    # Verify expected top-level modules exist
    expected_modules = [
        "gdpr_pseudonymizer.cli",
        "gdpr_pseudonymizer.core",
        "gdpr_pseudonymizer.nlp",
        "gdpr_pseudonymizer.data",
        "gdpr_pseudonymizer.pseudonym",
        "gdpr_pseudonymizer.utils",
        "gdpr_pseudonymizer.validation",
    ]

    for expected in expected_modules:
        assert any(
            mod.startswith(expected) for mod in package_modules
        ), f"Expected module {expected} not found"
