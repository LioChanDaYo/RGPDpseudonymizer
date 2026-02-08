# 19. Coding Standards

### 19.0 Build & Test Commands (CRITICAL)

**This project uses Poetry. ALL commands must use `poetry run`:**

```bash
# Install dependencies
poetry install

# CI Quality Checks - ALL FOUR MUST PASS before PR
poetry run black --check gdpr_pseudonymizer/ tests/  # Formatting
poetry run ruff check gdpr_pseudonymizer/            # Linting
poetry run mypy gdpr_pseudonymizer/                  # Type checking
poetry run pytest tests/                             # Tests
```

**BAD - DO NOT use system Python or pip:**
```bash
pip install -e .          # ❌ NO
pytest tests/             # ❌ NO (use 'poetry run pytest')
python -m pytest tests/   # ❌ NO (use 'poetry run pytest')
```

**Why?** Poetry ensures:
- Correct Python version (3.10-3.12)
- Locked dependency versions
- Isolated virtual environment

**Supported Python:** 3.10 - 3.12 (3.9 EOL October 2025, 3.13+ not yet tested)

---

### 19.1 Critical Rules

1. **Module Imports:** Always use absolute imports
   ```python
   # GOOD
   from gdpr_pseudonymizer.data.repositories import MappingRepository

   # BAD
   from ..data.repositories import MappingRepository
   ```

2. **Interface Usage:** Core layer must use interfaces
   ```python
   # GOOD
   def __init__(self, mapping_repo: MappingRepository):

   # BAD
   def __init__(self, mapping_repo: SQLiteMappingRepository):
   ```

3. **Logging:** NEVER log sensitive data
   ```python
   # GOOD
   logger.info("entity_detected", entity_type="PERSON", confidence=0.92)

   # BAD
   logger.info(f"Detected: {entity.full_name}")  # Logs sensitive data!
   ```

4. **Type Hints:** All public functions must have type hints

---

### 19.2 Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| **Modules** | snake_case | `entity_detector.py` |
| **Classes** | PascalCase | `EntityDetector` |
| **Functions** | snake_case | `detect_entities()` |
| **Constants** | UPPER_SNAKE_CASE | `PBKDF2_ITERATIONS` |

---
