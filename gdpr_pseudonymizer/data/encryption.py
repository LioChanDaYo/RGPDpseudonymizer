"""Encryption service for sensitive database fields using AES-256-SIV.

This module provides deterministic authenticated encryption for sensitive entity data,
enabling encrypted field queries while maintaining NIST-approved security standards.

Security Properties:
- Algorithm: AES-256-SIV (RFC 5297) - deterministic authenticated encryption
- Key Derivation: PBKDF2-HMAC-SHA256 with 100,000 iterations
- Deterministic: Same plaintext + key → same ciphertext (enables DB queries)
- Authenticated: SIV mode prevents tampering (like HMAC)
- GDPR Compliant: Meets Article 32 "appropriate technical measures" requirement
"""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESSIV
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionService:
    """AES-256-SIV deterministic authenticated encryption for sensitive database fields.

    Provides column-level encryption for Entity sensitive fields (names, pseudonyms).
    Uses PBKDF2 key derivation from user passphrase for key generation.

    Security Trade-offs:
    - Pattern leakage: Duplicate plaintexts produce identical ciphertexts
    - Mitigation: Local-only database (NFR11) + strong passphrase (NFR12) = LOW RISK
    - Benefit: Enables encrypted field queries for compositional pseudonymization (Story 2.2)

    Example:
        >>> salt = EncryptionService.generate_salt()
        >>> service = EncryptionService("my_secure_passphrase_123!", salt)
        >>> encrypted = service.encrypt("Marie Dubois")
        >>> decrypted = service.decrypt(encrypted)
        >>> assert decrypted == "Marie Dubois"
    """

    # NIST SP 800-132 recommendations
    PBKDF2_ITERATIONS = 100000  # Minimum recommended for PBKDF2-HMAC-SHA256
    SALT_LENGTH = 32  # 256 bits
    KEY_LENGTH = 64  # 512 bits (AES-256-SIV requires 256 bits encryption + 256 bits authentication)

    # Passphrase validation canary
    CANARY_VALUE = "GDPR_PSEUDO_CANARY_V1"

    def __init__(
        self, passphrase: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS
    ) -> None:
        """Initialize encryption service with passphrase-derived key.

        Args:
            passphrase: User passphrase for key derivation (min 12 chars recommended)
            salt: Cryptographically random salt (32 bytes)
            iterations: PBKDF2 iteration count (default 100,000)

        Raises:
            ValueError: If passphrase or salt invalid
        """
        if not passphrase:
            raise ValueError("Passphrase cannot be empty")
        if not salt or len(salt) != self.SALT_LENGTH:
            raise ValueError(f"Salt must be {self.SALT_LENGTH} bytes")
        if iterations < 1000:
            raise ValueError("Iterations must be at least 1000")

        # Derive 512-bit key from passphrase using PBKDF2-HMAC-SHA256
        kdf = PBKDF2HMAC(
            algorithm=SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=iterations,
        )
        key = kdf.derive(passphrase.encode("utf-8"))

        # Initialize AES-256-SIV cipher
        self._cipher = AESSIV(key)

    def encrypt(self, plaintext: str | None) -> str | None:
        """Encrypt plaintext string using AES-256-SIV.

        Deterministic encryption: same plaintext always produces same ciphertext.
        This enables database queries on encrypted fields.

        Args:
            plaintext: String to encrypt (None returns None unchanged)

        Returns:
            Base64-encoded ciphertext, or None if plaintext was None

        Example:
            >>> encrypted = service.encrypt("Marie Dubois")
            >>> assert "Marie" not in encrypted  # Verify no plaintext leakage
        """
        if plaintext is None:
            return None

        # AES-SIV doesn't allow empty strings, handle specially
        if plaintext == "":
            # Return a special marker for empty strings (still deterministic)
            return base64.b64encode(b"__EMPTY__").decode("ascii")

        # Encrypt with SIV (no additional data)
        ciphertext = self._cipher.encrypt(plaintext.encode("utf-8"), None)

        # Return base64-encoded for safe string storage
        return base64.b64encode(ciphertext).decode("ascii")

    def decrypt(self, ciphertext: str | None) -> str | None:
        """Decrypt ciphertext string using AES-256-SIV.

        SIV mode provides authentication - decryption fails if ciphertext tampered.

        Args:
            ciphertext: Base64-encoded ciphertext (None returns None unchanged)

        Returns:
            Original plaintext string, or None if ciphertext was None

        Raises:
            Exception: If ciphertext tampered or encrypted with different key

        Example:
            >>> decrypted = service.decrypt(encrypted)
            >>> assert decrypted == "Marie Dubois"
        """
        if ciphertext is None:
            return None

        # Decode base64
        ciphertext_bytes = base64.b64decode(ciphertext.encode("ascii"))

        # Check for empty string marker
        if ciphertext_bytes == b"__EMPTY__":
            return ""

        # Decrypt with SIV authentication verification
        plaintext_bytes = self._cipher.decrypt(ciphertext_bytes, None)

        return plaintext_bytes.decode("utf-8")

    def encrypt_canary(self) -> str:
        """Encrypt canary value for passphrase validation.

        Returns:
            Encrypted canary value (base64-encoded)
        """
        return self.encrypt(self.CANARY_VALUE)  # type: ignore

    def verify_canary(self, encrypted_canary: str) -> bool:
        """Verify passphrase by decrypting canary value.

        Args:
            encrypted_canary: Encrypted canary from database

        Returns:
            True if passphrase correct (decrypts to expected value), False otherwise
        """
        try:
            decrypted = self.decrypt(encrypted_canary)
            return decrypted == self.CANARY_VALUE
        except Exception:
            return False

    @staticmethod
    def generate_salt() -> bytes:
        """Generate cryptographically random salt for PBKDF2.

        Returns:
            32 bytes (256 bits) of random data suitable for salt

        Example:
            >>> salt = EncryptionService.generate_salt()
            >>> assert len(salt) == 32
        """
        return os.urandom(EncryptionService.SALT_LENGTH)

    @staticmethod
    def validate_passphrase(passphrase: str) -> tuple[bool, str]:
        """Validate passphrase strength and provide feedback.

        Enforces minimum 12 character requirement (NFR12).
        Provides entropy feedback based on length and character diversity.

        Args:
            passphrase: User passphrase to validate

        Returns:
            Tuple of (is_valid, feedback_message)
            - is_valid: True if passphrase meets minimum requirements
            - feedback_message: "weak", "medium", or "strong" with guidance

        Example:
            >>> valid, feedback = EncryptionService.validate_passphrase("short")
            >>> assert not valid
            >>> assert "12" in feedback

            >>> valid, feedback = EncryptionService.validate_passphrase("strong_pass_123!")
            >>> assert valid
            >>> assert "medium" in feedback or "strong" in feedback
        """
        if not passphrase:
            return False, "Passphrase cannot be empty"

        length = len(passphrase)

        # Minimum length requirement (NFR12)
        if length < 12:
            return (
                False,
                f"Passphrase must be at least 12 characters (current: {length})",
            )

        # Character diversity analysis
        has_lower = any(c.islower() for c in passphrase)
        has_upper = any(c.isupper() for c in passphrase)
        has_digit = any(c.isdigit() for c in passphrase)
        has_special = any(not c.isalnum() for c in passphrase)

        diversity_count = sum([has_lower, has_upper, has_digit, has_special])

        # Strength feedback
        if length >= 30 and diversity_count >= 3:
            return True, "strong - Excellent passphrase!"
        elif length >= 20 and diversity_count >= 2:
            return (
                True,
                "medium - Good passphrase. Consider adding more character types for stronger security.",
            )
        elif length >= 12:
            return (
                True,
                "weak - Passphrase meets minimum requirements. Consider using 20+ characters with mixed case, numbers, and special characters.",
            )
        else:
            # Should not reach here due to earlier check, but included for completeness
            return (
                False,
                f"Passphrase must be at least 12 characters (current: {length})",
            )
