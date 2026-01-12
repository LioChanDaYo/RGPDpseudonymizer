# 15. Security and Performance

### 15.1 Security Requirements

#### 15.1.1 Encryption Security

| Security Property | Implementation | Standard |
|-------------------|----------------|----------|
| **Algorithm** | Fernet (AES-128-CBC + HMAC-SHA256) | NIST approved |
| **Key Derivation** | PBKDF2-HMAC-SHA256, 100K iterations | NIST SP 800-132 |
| **Salt** | 32 bytes, cryptographically random | NIST recommendation |
| **Authentication** | HMAC prevents tampering | Authenticated encryption |

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
| **A02: Cryptographic Failures** | High | NIST-approved Fernet encryption, PBKDF2 key derivation |
| **A03: Injection** | Medium | SQLAlchemy ORM prevents SQL injection |
| **A07: Authentication Failures** | Medium | Strong passphrase requirements, canary validation |

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
