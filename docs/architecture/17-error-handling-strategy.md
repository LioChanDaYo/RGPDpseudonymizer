# 17. Error Handling Strategy

### 17.1 Error Categories

#### User Input Errors (Recoverable)

**Example:**
```
[ERROR] Input file not found: '/path/to/nonexistent.txt'
| Check the file path and ensure the file exists
| Reference: docs/usage.md#file-paths
```

#### Configuration Errors (Recoverable)

**Example:**
```
[ERROR] NLP model 'fr_core_news_lg' not found
| Run: python -m spacy download fr_core_news_lg
| Reference: docs/installation.md#nlp-models
```

#### Data Integrity Errors (Fatal)

**Example:**
```
[ERROR] Incorrect passphrase
| The passphrase does not match initialization
| WARNING: Passphrase loss means permanent data loss
| Reference: docs/troubleshooting.md#passphrase-issues
```

---

### 17.2 Exit Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success |
| 1 | User Error (invalid input) |
| 2 | System Error (fatal) |
| 3 | Data Error (corruption) |
| 4 | Permission Error |

---

### 17.3 Logging Strategy

**Structured Logging (structlog):**

```python
logger.info("document_processed", file_path=path, entities=15)
logger.warning("low_confidence", entity=entity.text, confidence=0.55)
logger.error("database_error", error=str(e), operation="commit")
```

**What Gets Logged:**
- ✅ Operation metadata (file paths, entity counts)
- ✅ Performance metrics
- ✅ Error details
- ❌ **Sensitive data** (entity names, pseudonyms, passphrases)

---
