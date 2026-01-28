# 9. Database Schema

This section consolidates the data models from Section 4, providing concrete database schema definitions for SQLite implementation with SQLAlchemy ORM.

### 9.1 Schema Overview

**Database Technology:** SQLite 3.35+ with Write-Ahead Logging (WAL mode)

**ORM:** SQLAlchemy 2.0+ (modern async-ready API)

**Encryption:** Application-level column encryption using Fernet (AES-128-CBC + HMAC)

**Schema Version:** 1.0.0 (tracked in `metadata` table)

---

### 9.2 SQL DDL (Data Definition Language)

```sql
-- ============================================
-- GDPR Pseudonymizer Database Schema v1.0.0
-- ============================================

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Enable Write-Ahead Logging for concurrent reads
PRAGMA journal_mode = WAL;

-- ============================================
-- Table: entities
-- ============================================
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,

    -- Original entity (encrypted)
    first_name TEXT,
    last_name TEXT,
    full_name TEXT NOT NULL,

    -- Assigned pseudonym (encrypted)
    pseudonym_first TEXT,
    pseudonym_last TEXT,
    pseudonym_full TEXT NOT NULL,

    -- Metadata
    first_seen_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    gender TEXT,
    confidence_score REAL,
    theme TEXT NOT NULL,
    is_ambiguous BOOLEAN NOT NULL DEFAULT 0,
    ambiguity_reason TEXT,

    CHECK (entity_type IN ('PERSON', 'LOCATION', 'ORG'))
);

-- Indexes for performance
CREATE INDEX idx_entities_full_name ON entities(full_name);
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_first_name ON entities(first_name);
CREATE INDEX idx_entities_last_name ON entities(last_name);
CREATE INDEX idx_entities_ambiguous ON entities(is_ambiguous) WHERE is_ambiguous = 1;

-- ============================================
-- Table: operations
-- ============================================
CREATE TABLE operations (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    operation_type TEXT NOT NULL,
    files_processed TEXT NOT NULL,        -- JSON array
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    theme_selected TEXT NOT NULL,
    user_modifications TEXT,              -- JSON object
    entity_count INTEGER NOT NULL,
    processing_time_seconds REAL NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,

    CHECK (operation_type IN ('PROCESS', 'BATCH', 'VALIDATE', 'IMPORT', 'EXPORT', 'DESTROY'))
);

CREATE INDEX idx_operations_timestamp ON operations(timestamp);
CREATE INDEX idx_operations_type ON operations(operation_type);

-- ============================================
-- Table: metadata
-- ============================================
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Critical metadata keys:
-- - 'passphrase_canary': Encrypted verification string
-- - 'encryption_salt': Salt for PBKDF2
-- - 'kdf_iterations': PBKDF2 iteration count
-- - 'schema_version': Database schema version
-- - 'file:{path}:hash': File hash for idempotency
```

---

### 9.3 Encryption Implementation

**Encryption Service:**

```python
from cryptography.hazmat.primitives.ciphers.aead import AESSIV
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64
import os

class EncryptionService:
    """AES-256-SIV deterministic authenticated encryption for sensitive database fields.

    Uses AES-SIV (Synthetic IV mode, RFC 5297) which provides:
    - Deterministic encryption: same plaintext + key → same ciphertext
    - Authenticated encryption: prevents tampering via SIV authentication
    - Searchable: enables database queries on encrypted fields

    Security Trade-Off: Pattern leakage (duplicate plaintexts produce identical
    ciphertexts). Acceptable for this use case due to local-only database +
    passphrase protection.
    """

    PBKDF2_ITERATIONS = 100000  # NIST minimum
    SALT_LENGTH = 32             # 256 bits

    def __init__(self, passphrase: str, salt: bytes):
        # Derive 64-byte key (512 bits) for AES-256-SIV
        # 256 bits for encryption + 256 bits for authentication
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=64,  # AES-256-SIV requires 512-bit key
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS
        )
        key = kdf.derive(passphrase.encode('utf-8'))
        self.aessiv = AESSIV(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt with AES-256-SIV deterministic authenticated encryption.

        Returns base64-encoded ciphertext. Same plaintext always produces
        same ciphertext (deterministic), enabling database queries.
        """
        if plaintext is None:
            return None
        ciphertext_bytes = self.aessiv.encrypt(plaintext.encode('utf-8'), None)
        return base64.urlsafe_b64encode(ciphertext_bytes).decode('ascii')

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt and verify SIV authentication (prevents tampering)."""
        if ciphertext is None:
            return None
        ciphertext_bytes = base64.urlsafe_b64decode(ciphertext.encode('ascii'))
        plaintext_bytes = self.aessiv.decrypt(ciphertext_bytes, None)
        return plaintext_bytes.decode('utf-8')
```

**Why AES-SIV (Deterministic Encryption)?**

- **Required for compositional logic:** Story 2.2 needs `find_by_component("Marie")` queries on encrypted fields
- **Performance:** Enables database indexes for <30s processing (NFR1)
- **Industry standard:** AWS DynamoDB, Google Tink, MongoDB use deterministic encryption for searchable databases
- **GDPR compliant:** Meets Article 32 "appropriate technical measures" requirement

**Security Assessment:**

| Property | Status | Notes |
|----------|--------|-------|
| **Confidentiality** | ✅ Strong | Names encrypted, attacker without passphrase cannot read plaintext |
| **Integrity** | ✅ Strong | SIV authentication prevents tampering |
| **Pattern Leakage** | ⚠️ Low Risk | Duplicate names produce identical ciphertexts, but local-only + passphrase mitigates risk |
| **GDPR Article 32** | ✅ Compliant | Deterministic encryption is industry-standard "appropriate measure" |

---

### 9.4 Database Initialization

```python
def init_database(db_path: str, passphrase: str) -> None:
    """Initialize new mapping table database with AES-256-SIV encryption."""

    # Validate passphrase
    is_valid, message = EncryptionService.validate_passphrase(passphrase)
    if not is_valid:
        raise ValueError(message)

    # Generate salt
    salt = EncryptionService.generate_salt()

    # Create encryption service (AES-256-SIV)
    encryption = EncryptionService(passphrase, salt)

    # Create database
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)

    # Enable WAL mode (concurrent reads for batch processing)
    with engine.connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.commit()

    # Initialize metadata
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        session.add(Metadata(key='schema_version', value=json.dumps('1.0.0')))
        session.add(Metadata(key='encryption_salt', value=base64.b64encode(salt).decode('ascii')))
        session.add(Metadata(key='kdf_iterations', value=json.dumps(100000)))
        session.add(Metadata(key='encryption_algorithm', value=json.dumps('AES-256-SIV')))

        # Passphrase canary (validates correct passphrase on database open)
        # Encrypted with AES-SIV deterministic encryption
        canary_encrypted = encryption.encrypt('GDPR_PSEUDO_CANARY_V1')
        session.add(Metadata(key='passphrase_canary', value=canary_encrypted))

        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
```

---
