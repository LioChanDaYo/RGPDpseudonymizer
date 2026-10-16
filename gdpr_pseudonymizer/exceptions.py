"""Custom exception classes for GDPR pseudonymizer."""

from __future__ import annotations


class PseudonymizerError(Exception):
    """Base exception for all pseudonymizer errors."""

    pass


class ConfigurationError(PseudonymizerError):
    """Raised when configuration is invalid or missing.

    Examples:
        - Config file has invalid YAML syntax
        - Required configuration fields are missing
        - Config file path is inaccessible
    """

    pass


class ModelNotFoundError(PseudonymizerError):
    """Raised when NLP model cannot be loaded.

    Examples:
        - spaCy model not installed
        - Model name is invalid
        - Model files are corrupted
    """

    pass


class EncryptionError(PseudonymizerError):
    """Raised when encryption or decryption fails.

    Examples:
        - Invalid passphrase
        - Corrupted encrypted data
        - Key derivation failure
    """

    pass


class ValidationError(PseudonymizerError):
    """Raised when validation workflow encounters an error.

    Examples:
        - Invalid user input during entity review
        - Validation session state is inconsistent
        - Entity modification fails validation rules
    """

    pass


class CustomPseudonymError(ValidationError):
    """Raised when a custom pseudonym breaks a rule at finalization (Story 10.11).

    The review refuses such a pseudonym when it is set; this is the last
    check, made before anything is saved or written. Its message names no
    name and no pseudonym.
    """


class FileProcessingError(PseudonymizerError):
    """Raised when file I/O operations fail.

    Examples:
        - File not found
        - Permission denied
        - Invalid file type
        - File read/write error
    """

    pass


class DatabaseError(PseudonymizerError):
    """Raised when database operation fails."""

    pass


class DuplicateEntityError(DatabaseError):
    """Raised when saving an entity whose (full_name, entity_type) is stored."""

    pass


class CorruptedDatabaseError(DatabaseError):
    """Raised when database metadata is missing or invalid."""

    pass


class DatabaseConversionError(DatabaseError):
    """Raised when database conversion or erasure-log cleaning fails.

    The conversion to one row per (name, type) runs once, on open, in one
    transaction: when it fails, the file is left unchanged. Also raised when
    the file's schema version and its table definition disagree, so the
    format is not recognised. Also covers a failed removal of erased names
    from the audit log (Story 10.12); the log is left unchanged.
    """

    pass


class ConfigValidationError(PseudonymizerError):
    """Raised when configuration validation fails."""

    pass


class PassphraseInConfigError(ConfigValidationError):
    """Raised when passphrase is found in config file (security violation)."""

    pass
