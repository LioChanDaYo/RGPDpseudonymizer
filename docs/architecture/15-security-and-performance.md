# 15. Security and Performance

### 15.1 Security Requirements

#### 15.1.1 Encryption Security

| Security Property | Implementation | Standard |
|-------------------|----------------|----------|
| **Algorithm** | AES-256-SIV (deterministic AEAD) | NIST approved, RFC 5297 |
| **Key Derivation** | PBKDF2-HMAC-SHA256, 100K iterations, 64-byte output | NIST SP 800-132 |
| **Salt** | 32 bytes, cryptographically random | NIST recommendation |
| **Authentication** | SIV prevents tampering | Authenticated encryption |
| **Deterministic Property** | Same plaintext → same ciphertext | Enables encrypted field queries |

#### 15.1.2 Input Validation

```python
def validate_file_path(path: str) -> Path:
    """Validate file path to prevent path traversal attacks."""
    file_path = Path(path).resolve()

    # Prevent path traversal
    if not file_path.is_relative_to(Path.cwd()):
        raise ValueError("Invalid file path: path traversal detected")

    return file_path
```

#### 15.1.3 OWASP Top 10 Mitigation

| OWASP Risk | Relevance | Mitigation |
|------------|-----------|------------|
| **A02: Cryptographic Failures** | High | NIST-approved AES-256-SIV encryption, PBKDF2 key derivation |
| **A03: Injection** | Medium | SQLAlchemy ORM prevents SQL injection |
| **A07: Authentication Failures** | Medium | Strong passphrase requirements, canary validation |

#### 15.1.4 Deterministic Encryption & GDPR Compliance

**Why Deterministic Encryption (AES-256-SIV)?**

This project uses **AES-256-SIV** (Synthetic IV mode, RFC 5297) instead of traditional randomized encryption (like AES-CBC or AES-GCM). This is a deliberate architectural decision driven by functional requirements:

| Requirement | Rationale |
|-------------|-----------|
| **Compositional Pseudonymization (Story 2.2)** | Need to query encrypted fields: `find_by_component("Marie")` must work on encrypted database |
| **Performance (NFR1: <30s)** | Database indexes on encrypted fields enable fast lookups |
| **Industry Standard** | AWS DynamoDB, Google Tink, MongoDB all use deterministic encryption for searchable databases |

**Security Trade-Off: Pattern Leakage**

Deterministic encryption reveals patterns that randomized encryption does not:

| Revealed | Not Revealed |
|----------|--------------|
| ✅ Duplicate entries produce identical ciphertexts (frequency analysis possible) | ❌ Actual plaintext names remain encrypted |
| ✅ Correlation patterns visible (Entity X always appears with Entity Y) | ❌ What the actual names are |

**Risk Assessment: LOW**

Pattern leakage is **low risk** for this application due to multiple mitigating factors:

1. **Local-Only Database (NFR11):** No network exposure, attacker needs physical machine access
2. **Passphrase Protection (NFR12):** PBKDF2 100K iterations prevents brute force, attacker without passphrase cannot decrypt
3. **Threat Model:** If attacker has passphrase → pattern leakage irrelevant (they can decrypt everything anyway)
4. **Alternative Analysis:** Hash-based lookup has identical pattern leakage with more implementation complexity

**GDPR Article 32 Compliance**

This implementation satisfies **GDPR Article 32(1)(a)** requirement for "appropriate technical and organizational measures" to ensure security of processing:

| GDPR Requirement | Implementation | Status |
|------------------|----------------|--------|
| **Encryption of personal data** | AES-256-SIV NIST-approved encryption | ✅ Compliant |
| **Confidentiality** | Attacker without passphrase cannot read plaintext | ✅ Compliant |
| **Integrity** | SIV authentication prevents tampering | ✅ Compliant |
| **Availability** | Passphrase-based access control | ✅ Compliant |
| **Reversibility** (Art. 16, 17) | Decryption supports GDPR rights (access, rectification, erasure) | ✅ Compliant |

**Acceptable for GDPR:** YES

- Deterministic encryption is **industry standard** for searchable encryption use cases
- GDPR Article 32 requires "appropriate" measures, not maximum theoretical security
- Risk-based approach: pattern leakage without passphrase is **low impact** for this threat model
- Transparent disclosure: security trade-off will be documented in user-facing documentation

**Precedent & Standards:**

- **RFC 5297 (AES-SIV):** IETF standard for deterministic authenticated encryption
- **AWS DynamoDB Encryption:** Uses deterministic encryption for searchable encrypted fields
- **Google Tink:** Recommends AES-SIV for deterministic encryption use cases
- **MongoDB Client-Side Encryption:** Offers deterministic mode for queryable encrypted fields

---

### 15.2 Performance Optimization

#### 15.2.1 Single Document Processing (NFR1: <30 seconds)

**Optimization Strategies:**

1. **NLP Model Caching:**
   ```python
   class SpaCyDetector:
       _model_cache = {}  # Class-level cache

       def load_model(self, model_name: str):
           if model_name not in self._model_cache:
               self._model_cache[model_name] = spacy.load(model_name)
           self.nlp = self._model_cache[model_name]
   ```

2. **Database Query Optimization:**
   ```python
   # Batch queries instead of N+1
   existing_entities = session.query(Entity).filter(
       Entity.full_name.in_(entity_texts)
   ).all()
   ```

3. **Lazy Decryption:** Only decrypt entities when needed

#### 15.2.2 Batch Processing (NFR2: <30 minutes for 50 documents)

**Parallel Processing:**
```
Sequential: 50 docs × 30s = 25 minutes
Parallel (4 workers): 50 docs ÷ 4 × 30s + overhead ≈ 8 minutes

Target: <30 minutes ✓
```

**Worker Pool Optimization:**
```python
def calculate_optimal_workers() -> int:
    """Calculate worker count based on system resources."""
    cpu_count = multiprocessing.cpu_count()
    available_memory_gb = psutil.virtual_memory().available / (1024**3)
    max_workers_by_memory = int(available_memory_gb / 1.5)

    return min(cpu_count, 4, max_workers_by_memory)
```

#### 15.2.3 Memory Optimization (NFR4: <8GB RAM)

**Memory Budget:**
```
NLP Model (per worker):     1.5 GB × 4 = 6.0 GB
Main Process:               0.5 GB
Entity Cache:               0.3 GB
OS Overhead:                1.0 GB
--------------------------------
Total:                      7.8 GB ✓ (within 8GB)
```

---
