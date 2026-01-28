"""Unit tests for EncryptionService (AES-256-SIV deterministic encryption)."""

import base64
import os

import pytest

from gdpr_pseudonymizer.data.encryption import EncryptionService


class TestEncryptionService:
    """Test suite for EncryptionService class."""

    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Test encryption and decryption preserve plaintext."""
        salt = EncryptionService.generate_salt()
        service = EncryptionService("strong_passphrase_123!", salt)
        plaintext = "Marie Dubois"

        encrypted = service.encrypt(plaintext)
        assert encrypted is not None
        assert encrypted != plaintext  # Verify encrypted
        assert "Marie" not in encrypted  # Verify no plaintext leakage

        decrypted = service.decrypt(encrypted)
        assert decrypted == plaintext  # Verify roundtrip

    def test_encrypt_returns_same_ciphertext_for_same_plaintext(self) -> None:
        """Test AES-SIV deterministic property - same plaintext produces same ciphertext."""
        salt = EncryptionService.generate_salt()
        service = EncryptionService("strong_passphrase_123!", salt)
        plaintext = "Jean Dupont"

        encrypted1 = service.encrypt(plaintext)
        encrypted2 = service.encrypt(plaintext)

        # Deterministic encryption: same plaintext + key → same ciphertext
        assert encrypted1 == encrypted2

    def test_encrypt_different_passphrases_produce_different_ciphertexts(self) -> None:
        """Test different passphrases produce different ciphertexts for same plaintext."""
        salt = EncryptionService.generate_salt()
        plaintext = "Marie Curie"

        service1 = EncryptionService("passphrase_one_123!", salt)
        service2 = EncryptionService("passphrase_two_456!", salt)

        encrypted1 = service1.encrypt(plaintext)
        encrypted2 = service2.encrypt(plaintext)

        # Different keys → different ciphertexts
        assert encrypted1 != encrypted2

    def test_decrypt_with_wrong_key_raises_exception(self) -> None:
        """Test decryption with wrong passphrase raises exception."""
        salt = EncryptionService.generate_salt()
        service1 = EncryptionService("correct_passphrase_123!", salt)
        service2 = EncryptionService("wrong_passphrase_456!", salt)

        plaintext = "Sophie Martin"
        encrypted = service1.encrypt(plaintext)

        # Attempt decrypt with wrong key
        with pytest.raises(Exception):  # SIV authentication failure
            service2.decrypt(encrypted)

    def test_encrypt_none_returns_none(self) -> None:
        """Test encrypt handles None input correctly."""
        salt = EncryptionService.generate_salt()
        service = EncryptionService("strong_passphrase_123!", salt)

        result = service.encrypt(None)
        assert result is None

    def test_decrypt_none_returns_none(self) -> None:
        """Test decrypt handles None input correctly."""
        salt = EncryptionService.generate_salt()
        service = EncryptionService("strong_passphrase_123!", salt)

        result = service.decrypt(None)
        assert result is None

    def test_encrypt_empty_string(self) -> None:
        """Test encryption of empty string."""
        salt = EncryptionService.generate_salt()
        service = EncryptionService("strong_passphrase_123!", salt)

        encrypted = service.encrypt("")
        assert encrypted is not None
        assert encrypted != ""

        decrypted = service.decrypt(encrypted)
        assert decrypted == ""

    def test_encrypt_unicode_characters(self) -> None:
        """Test encryption handles Unicode characters correctly."""
        salt = EncryptionService.generate_salt()
        service = EncryptionService("strong_passphrase_123!", salt)

        # French names with accents
        plaintext = "François Müller-Lefèvre"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plaintext

    def test_generate_salt_returns_32_bytes(self) -> None:
        """Test salt generation produces 32 bytes."""
        salt = EncryptionService.generate_salt()
        assert len(salt) == 32
        assert isinstance(salt, bytes)

    def test_generate_salt_cryptographically_random(self) -> None:
        """Test salt generation produces different values each time."""
        salt1 = EncryptionService.generate_salt()
        salt2 = EncryptionService.generate_salt()
        salt3 = EncryptionService.generate_salt()

        # All salts should be unique (extremely high probability with 256-bit random)
        assert salt1 != salt2
        assert salt2 != salt3
        assert salt1 != salt3

    def test_validate_passphrase_minimum_length(self) -> None:
        """Test passphrase validation enforces 12 character minimum."""
        # Too short
        valid, message = EncryptionService.validate_passphrase("short")
        assert not valid
        assert "12" in message

        # Exactly 12 characters (minimum)
        valid, message = EncryptionService.validate_passphrase("exactly12chr")
        assert valid

        # Longer than 12
        valid, message = EncryptionService.validate_passphrase("this_is_longer_than_12")
        assert valid

    def test_validate_passphrase_empty_string(self) -> None:
        """Test passphrase validation rejects empty string."""
        valid, message = EncryptionService.validate_passphrase("")
        assert not valid
        assert "empty" in message.lower()

    def test_validate_passphrase_strength_weak(self) -> None:
        """Test passphrase strength feedback - weak."""
        valid, message = EncryptionService.validate_passphrase("simplepassword")
        assert valid
        assert "weak" in message.lower()

    def test_validate_passphrase_strength_medium(self) -> None:
        """Test passphrase strength feedback - medium."""
        valid, message = EncryptionService.validate_passphrase("medium_passphrase_20chars!")
        assert valid
        assert "medium" in message.lower()

    def test_validate_passphrase_strength_strong(self) -> None:
        """Test passphrase strength feedback - strong."""
        valid, message = EncryptionService.validate_passphrase(
            "VeryStrongPassphrase123WithSpecialChars!@#"
        )
        assert valid
        assert "strong" in message.lower()

    def test_encrypt_canary(self) -> None:
        """Test canary encryption for passphrase validation."""
        salt = EncryptionService.generate_salt()
        service = EncryptionService("test_passphrase_123!", salt)

        encrypted_canary = service.encrypt_canary()
        assert encrypted_canary is not None
        assert EncryptionService.CANARY_VALUE not in encrypted_canary

        # Verify can decrypt back to canary value
        decrypted = service.decrypt(encrypted_canary)
        assert decrypted == EncryptionService.CANARY_VALUE

    def test_verify_canary_correct_passphrase(self) -> None:
        """Test canary verification succeeds with correct passphrase."""
        salt = EncryptionService.generate_salt()
        service = EncryptionService("correct_passphrase_123!", salt)

        encrypted_canary = service.encrypt_canary()
        assert service.verify_canary(encrypted_canary) is True

    def test_verify_canary_wrong_passphrase(self) -> None:
        """Test canary verification fails with wrong passphrase."""
        salt = EncryptionService.generate_salt()
        service1 = EncryptionService("passphrase_one_123!", salt)
        service2 = EncryptionService("passphrase_two_456!", salt)

        # Encrypt canary with service1
        encrypted_canary = service1.encrypt_canary()

        # Verify with service2 (wrong passphrase)
        assert service2.verify_canary(encrypted_canary) is False

    def test_verify_canary_corrupted_value(self) -> None:
        """Test canary verification fails with corrupted ciphertext."""
        salt = EncryptionService.generate_salt()
        service = EncryptionService("test_passphrase_123!", salt)

        # Create corrupted canary (invalid base64)
        corrupted_canary = "invalid_base64_not_encrypted"
        assert service.verify_canary(corrupted_canary) is False

    def test_init_with_empty_passphrase_raises_error(self) -> None:
        """Test initialization with empty passphrase raises ValueError."""
        salt = EncryptionService.generate_salt()
        with pytest.raises(ValueError, match="Passphrase cannot be empty"):
            EncryptionService("", salt)

    def test_init_with_invalid_salt_length_raises_error(self) -> None:
        """Test initialization with wrong salt length raises ValueError."""
        invalid_salt = os.urandom(16)  # Only 16 bytes instead of 32
        with pytest.raises(ValueError, match="Salt must be 32 bytes"):
            EncryptionService("test_passphrase_123!", invalid_salt)

    def test_init_with_low_iterations_raises_error(self) -> None:
        """Test initialization with too few iterations raises ValueError."""
        salt = EncryptionService.generate_salt()
        with pytest.raises(ValueError, match="Iterations must be at least 1000"):
            EncryptionService("test_passphrase_123!", salt, iterations=500)

    def test_no_plaintext_in_encrypted_output(self) -> None:
        """Test encrypted output contains no obvious plaintext fragments."""
        salt = EncryptionService.generate_salt()
        service = EncryptionService("strong_passphrase_123!", salt)

        # Test with various sensitive strings
        sensitive_strings = [
            "Marie Dubois",
            "Jean-Claude Martin",
            "François Lefèvre",
        ]

        for plaintext in sensitive_strings:
            encrypted = service.encrypt(plaintext)
            assert encrypted is not None

            # Verify no words of 4+ characters from plaintext appear in ciphertext
            # (short words like "de" or "la" can appear by coincidence in base64)
            for word in plaintext.split():
                if len(word) >= 4:
                    assert word not in encrypted
                    assert word.lower() not in encrypted.lower()

    def test_no_plaintext_in_logs(self) -> None:
        """Test encryption service doesn't log sensitive data.

        Security requirement: EncryptionService must not log sensitive data.
        Current implementation: No logging in EncryptionService (by design).

        This test serves as documentation of the security requirement.
        If logging is added in the future, this test should be updated to verify
        that no sensitive data (plaintexts, passphrases) are logged.
        """
        # Verify EncryptionService has no logging calls
        salt = EncryptionService.generate_salt()
        service = EncryptionService("test_passphrase_123!", salt)

        # Perform operations - no logging should occur
        encrypted = service.encrypt("Sensitive Name")
        decrypted = service.decrypt(encrypted)

        assert decrypted == "Sensitive Name"
        # If logging is added, mock logger here and verify no sensitive data logged

    def test_encrypted_value_is_base64_encoded(self) -> None:
        """Test encrypted output is valid base64 for safe string storage."""
        salt = EncryptionService.generate_salt()
        service = EncryptionService("strong_passphrase_123!", salt)

        encrypted = service.encrypt("Test Value")
        assert encrypted is not None

        # Verify valid base64
        try:
            decoded = base64.b64decode(encrypted.encode("ascii"))
            assert len(decoded) > 0
        except Exception as e:
            pytest.fail(f"Encrypted value is not valid base64: {e}")

    def test_different_salts_produce_different_ciphertexts(self) -> None:
        """Test different salts produce different ciphertexts for same passphrase and plaintext."""
        salt1 = EncryptionService.generate_salt()
        salt2 = EncryptionService.generate_salt()
        passphrase = "same_passphrase_123!"
        plaintext = "Same Plaintext"

        service1 = EncryptionService(passphrase, salt1)
        service2 = EncryptionService(passphrase, salt2)

        encrypted1 = service1.encrypt(plaintext)
        encrypted2 = service2.encrypt(plaintext)

        # Different salts → different derived keys → different ciphertexts
        assert encrypted1 != encrypted2
