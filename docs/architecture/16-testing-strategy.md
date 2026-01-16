# 16. Testing Strategy

### 16.1 Testing Pyramid

```
        E2E Tests (5%)
        ┌───────────┐
        │  ~15 tests │
        └───────────┘
       /             \
   Integration Tests (20%)
   ┌─────────────────────┐
   │    ~60 tests        │
   └─────────────────────┘
  /                       \
Unit Tests (75%)
┌───────────────────────────┐
│      ~225 tests           │
└───────────────────────────┘
```

**Total Test Count Target:** ~300 tests by Epic 4

---

### 16.2 Test Categories

#### Unit Tests (75%)

**Examples:**

```python
def test_encrypt_decrypt_roundtrip():
    service = EncryptionService("password", os.urandom(32))
    plaintext = "Sensitive Data"

    encrypted = service.encrypt(plaintext)
    assert encrypted != plaintext

    decrypted = service.decrypt(encrypted)
    assert decrypted == plaintext
```

**Coverage Target:** 90-100% for core business logic

#### Integration Tests (20%)

**Examples:**

```python
def test_reprocess_document_reuses_mappings(test_db, tmp_path):
    """Test FR19: Idempotent processing."""
    orchestrator = create_orchestrator(test_db)

    # First processing
    result1 = orchestrator.process_document("input.txt", "output1.txt")
    assert result1.entities_detected == 2

    # Second processing (same document)
    result2 = orchestrator.process_document("input.txt", "output2.txt")
    assert result2.entities_reused == 2
    assert result2.entities_new == 0
```

**Coverage Target:** 80% of integration paths

#### Performance Tests

```python
@pytest.mark.benchmark
def test_single_document_processing_speed(benchmark, test_db):
    """NFR1: Process 2-5K word document in <30 seconds."""
    result = benchmark(orchestrator.process_document, "doc.txt", "out.txt")
    assert benchmark.stats['mean'] < 30.0
```

---

### 16.3 Test Coverage Targets

| Epic | Coverage Target |
|------|-----------------|
| Epic 1 | 70% |
| Epic 2 | 80% |
| Epic 3 | 85% |
| Epic 4 | 85% (maintain) |

---
