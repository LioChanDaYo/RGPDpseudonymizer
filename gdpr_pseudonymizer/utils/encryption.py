"""Encryption service interface for data-at-rest protection.

This module defines the encryption interface for protecting sensitive
entity mappings in the database. Full implementation in Epic 2.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EncryptionService(ABC):
    """Abstract interface for encryption operations.

    Implementations must use Fernet (AES-128-CBC with HMAC) from
    the cryptography library for symmetric encryption.
    """

    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string.

        Args:
            plaintext: Data to encrypt

        Returns:
            Encrypted data as base64-encoded string

        Raises:
            EncryptionError: If encryption fails
        """
        pass

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext string.

        Args:
            ciphertext: Base64-encoded encrypted data

        Returns:
            Decrypted plaintext

        Raises:
            EncryptionError: If decryption fails (invalid key, corrupted data)
        """
        pass


class FernetEncryptionService(EncryptionService):
    """Stub implementation of encryption service using Fernet.

    Full implementation will be completed in Epic 2 with:
    - PBKDF2 key derivation from passphrase
    - Passphrase verification (canary)
    - Secure key storage
    """

    def __init__(self, passphrase: str, salt: bytes) -> None:
        """Initialize encryption service (stub).

        Args:
            passphrase: User-provided passphrase for key derivation
            salt: Salt for PBKDF2 (stored in metadata table)
        """
        # Stub: Full implementation in Epic 2
        self.passphrase = passphrase
        self.salt = salt

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext (stub implementation).

        Args:
            plaintext: Data to encrypt

        Returns:
            Stub encrypted value
        """
        # Stub: Full implementation in Epic 2
        return f"ENCRYPTED:{plaintext}"

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext (stub implementation).

        Args:
            ciphertext: Encrypted data

        Returns:
            Stub decrypted value
        """
        # Stub: Full implementation in Epic 2
        if ciphertext.startswith("ENCRYPTED:"):
            return ciphertext[10:]
        return ciphertext
