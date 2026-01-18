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


class FileProcessingError(PseudonymizerError):
    """Raised when file I/O operations fail.

    Examples:
        - File not found
        - Permission denied
        - Invalid file type
        - File read/write error
    """

    pass
