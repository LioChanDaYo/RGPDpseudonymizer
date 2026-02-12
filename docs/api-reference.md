# API Reference

**GDPR Pseudonymizer** - Module documentation for developers

---

## Overview

The `gdpr_pseudonymizer` package is organized into the following subpackages:

| Package | Purpose |
|---------|---------|
| `core` | Document processing orchestration |
| `nlp` | Named Entity Recognition (NER) pipeline |
| `pseudonym` | Pseudonym assignment and library management |
| `data` | Database, models, encryption, and repositories |
| `validation` | Interactive human-in-the-loop validation workflow |
| `cli` | Command-line interface (Typer-based) |
| `utils` | File handling, configuration, and logging |

---

## Core Module (`gdpr_pseudonymizer.core`)

### DocumentProcessor

Orchestrates the single-document pseudonymization workflow: entity detection, validation, pseudonym assignment, and file output.

```python
from gdpr_pseudonymizer.core.document_processor import DocumentProcessor

processor = DocumentProcessor(
    db_path="mappings.db",
    passphrase="your-secure-passphrase",
    theme="neutral",        # neutral | star_wars | lotr
    model_name="spacy"
)

result = processor.process_document(
    input_path="input.txt",
    output_path="output.txt",
    skip_validation=False,    # Set True for programmatic use (no UI)
    entity_type_filter=None   # Optional: set of types e.g. {"PERSON", "LOCATION"}
)
```

### ProcessingResult

Dataclass returned by `DocumentProcessor.process_document()`:

| Attribute | Type | Description |
|-----------|------|-------------|
| `success` | `bool` | Whether processing completed successfully |
| `input_file` | `str` | Input file path |
| `output_file` | `str` | Output file path |
| `entities_detected` | `int` | Total entities detected |
| `entities_new` | `int` | Newly assigned pseudonyms |
| `entities_reused` | `int` | Reused pseudonyms (idempotency) |
| `processing_time_seconds` | `float` | Total processing time |
| `error_message` | `str | None` | Error description if failed |

---

## NLP Module (`gdpr_pseudonymizer.nlp`)

### DetectedEntity

Dataclass representing a detected named entity:

| Attribute | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Original entity text |
| `entity_type` | `str` | Classification: `PERSON`, `LOCATION`, `ORG` |
| `start_pos` | `int` | Character offset start position |
| `end_pos` | `int` | Character offset end position |
| `confidence` | `float | None` | NER confidence score (0.0-1.0) |
| `gender` | `str | None` | Gender: `male`, `female`, `neutral`, `unknown` |
| `is_ambiguous` | `bool` | Whether flagged as ambiguous |
| `source` | `str` | Detection source: `spacy`, `regex`, or `hybrid` |

### EntityDetector (Abstract Base Class)

Interface for NER implementations. All detectors must implement:

```python
class EntityDetector(ABC):
    @abstractmethod
    def load_model(self, model_name: str) -> None: ...

    @abstractmethod
    def detect_entities(self, text: str) -> list[DetectedEntity]: ...

    @abstractmethod
    def get_model_info(self) -> dict[str, str]: ...

    @property
    @abstractmethod
    def supports_gender_classification(self) -> bool: ...
```

### HybridDetector

Default detector combining spaCy NER with regex pattern matching. This is the detector used by `DocumentProcessor`.

```python
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector

detector = HybridDetector()
detector.load_model("fr_core_news_lg")
entities = detector.detect_entities("Marie Dubois travaille a Paris.")
```

### SpaCyDetector

Pure spaCy NER implementation:

```python
from gdpr_pseudonymizer.nlp.spacy_detector import SpaCyDetector

detector = SpaCyDetector()
detector.load_model("fr_core_news_lg")
entities = detector.detect_entities(text)
```

### RegexMatcher

Pattern-based entity matcher using French title patterns, compound names, name dictionaries, and organization suffixes:

```python
from gdpr_pseudonymizer.nlp.regex_matcher import RegexMatcher

matcher = RegexMatcher()
matcher.load_patterns()  # Loads from config/detection_patterns.yaml
entities = matcher.match_entities(text)
stats = matcher.get_pattern_stats()
```

### NameDictionary

French name dictionary for pattern-based detection:

```python
from gdpr_pseudonymizer.nlp.name_dictionary import NameDictionary

names = NameDictionary()
names.load()
names.is_first_name("Marie")  # True
names.is_last_name("Dubois")  # True
```

### EntityGrouping (`entity_grouping` module)

Groups variant forms of the same real-world entity into single validation items, reducing user validation fatigue. For example, "Marie Dubois", "Pr. Dubois", and "Dubois" are grouped as one item.

```python
from gdpr_pseudonymizer.nlp.entity_grouping import group_entity_variants

groups = group_entity_variants(detected_entities)
for canonical, occurrences, variant_texts in groups:
    print(f"{canonical.text} (appears as: {variant_texts})")
```

**Return type:** `list[tuple[DetectedEntity, list[DetectedEntity], set[str]]]`

Each tuple contains:

| Element | Type | Description |
|---------|------|-------------|
| `canonical` | `DetectedEntity` | Representative entity (longest text form) |
| `occurrences` | `list[DetectedEntity]` | All entity instances in the group |
| `variant_texts` | `set[str]` | Unique text forms in the group |

**Grouping rules by entity type:**

| Type | Rule |
|------|------|
| `PERSON` | Title stripping + surname matching. "Marie Dubois" and "Dubois" group together. Different first names stay separate ("Marie Dubois" vs "Jean Dubois"). Ambiguous single-word surnames matching multiple people are isolated. |
| `LOCATION` | French preposition stripping. "a Lyon" and "Lyon" group together. |
| `ORG` | Case-insensitive matching. "ACME Corp" and "acme corp" group together. |

---

## Pseudonym Module (`gdpr_pseudonymizer.pseudonym`)

### LibraryBasedPseudonymManager

Loads pseudonym libraries from JSON files and assigns pseudonyms with gender matching:

```python
from gdpr_pseudonymizer.pseudonym.library_manager import LibraryBasedPseudonymManager

manager = LibraryBasedPseudonymManager()
manager.load_library("star_wars")

assignment = manager.assign_pseudonym(
    entity_type="PERSON",
    first_name="Marie",
    last_name="Dubois",
    gender="female"
)
print(assignment.pseudonym_full)  # e.g., "Leia Organa"
```

### PseudonymAssignment

Dataclass returned by pseudonym assignment:

| Attribute | Type | Description |
|-----------|------|-------------|
| `pseudonym_full` | `str` | Complete pseudonym string |
| `pseudonym_first` | `str | None` | First name component (PERSON only) |
| `pseudonym_last` | `str | None` | Last name component (PERSON only) |
| `theme` | `str` | Library theme used |
| `exhaustion_percentage` | `float` | Library usage (0.0-1.0) |
| `is_ambiguous` | `bool` | Ambiguity flag |
| `ambiguity_reason` | `str | None` | Reason for ambiguity |

### GenderDetector

Auto-detects French first name gender from a bundled 945-name INSEE-sourced dictionary. Used by `CompositionalPseudonymEngine` to assign gender-matched pseudonyms automatically.

```python
from gdpr_pseudonymizer.pseudonym.gender_detector import GenderDetector

detector = GenderDetector()
detector.load()

detector.detect_gender("Marie")          # "female"
detector.detect_gender("Jean")           # "male"
detector.detect_gender("Camille")        # None (ambiguous)
detector.detect_gender("Xyzabc")         # None (unknown)

# Full name detection (extracts first name, checks entity type)
detector.detect_gender_from_full_name("Marie Dupont", "PERSON")    # "female"
detector.detect_gender_from_full_name("Jean-Pierre Martin", "PERSON")  # "male" (compound: uses first component)
detector.detect_gender_from_full_name("Paris", "LOCATION")         # None (non-PERSON)
```

Key methods:

| Method | Description |
|--------|-------------|
| `load()` | Load gender lookup dictionary from JSON (lazy-loaded on first detect call) |
| `detect_gender(first_name)` | Detect gender from a single first name. Returns `"male"`, `"female"`, or `None` |
| `detect_gender_from_full_name(full_name, entity_type)` | Extract first name from full name and detect gender. Non-PERSON entities always return `None` |

Dictionary stats: 470 male, 457 female, 18 ambiguous names. Case-insensitive matching.

### CompositionalPseudonymEngine

Handles compositional logic: "Marie Dubois" maps to "Leia Organa", and "Marie" alone maps to "Leia" for consistency. Optionally integrates `GenderDetector` for automatic gender-matched pseudonym assignment.

```python
from gdpr_pseudonymizer.pseudonym.assignment_engine import CompositionalPseudonymEngine

engine = CompositionalPseudonymEngine(
    pseudonym_manager=manager,
    mapping_repository=repo,
    gender_detector=detector  # Optional: enables auto gender detection
)

result = engine.assign_compositional_pseudonym(
    entity_text="Marie Dubois",
    entity_type="PERSON",
    gender="female"
)
```

Key methods:

| Method | Description |
|--------|-------------|
| `assign_compositional_pseudonym(entity_text, entity_type, gender)` | Assign pseudonym with component reuse |
| `strip_titles(text)` | Remove French honorifics (Dr., Mme, Maitre) |
| `strip_prepositions(text)` | Remove French prepositions from locations |
| `parse_full_name(entity_text)` | Split into (first, last, is_compound) |
| `find_standalone_components(component, component_type)` | Look up existing component mapping |

---

## Data Module (`gdpr_pseudonymizer.data`)

### Database Functions

```python
from gdpr_pseudonymizer.data.database import init_database, open_database

# Initialize a new encrypted database
init_database("mappings.db", "your-passphrase")

# Open existing database (context manager)
with open_database("mappings.db", "your-passphrase") as db_session:
    # Use repositories with db_session
    pass
```

### SQLAlchemy Models

#### Entity (`entities` table)

| Column | Type | Description |
|--------|------|-------------|
| `id` | `str` (UUID) | Primary key |
| `entity_type` | `str` | PERSON, LOCATION, ORG |
| `first_name` | `str | None` | Original first name (encrypted) |
| `last_name` | `str | None` | Original last name (encrypted) |
| `full_name` | `str` | Original entity text (encrypted, unique) |
| `pseudonym_first` | `str | None` | Assigned first name pseudonym |
| `pseudonym_last` | `str | None` | Assigned last name pseudonym |
| `pseudonym_full` | `str` | Complete pseudonym |
| `gender` | `str | None` | Gender classification |
| `confidence_score` | `float | None` | NER confidence |
| `theme` | `str` | Library theme used |
| `first_seen_timestamp` | `datetime` | First detection time |

#### Operation (`operations` table)

| Column | Type | Description |
|--------|------|-------------|
| `id` | `str` (UUID) | Primary key |
| `timestamp` | `datetime` | Operation timestamp |
| `operation_type` | `str` | PROCESS, BATCH, VALIDATE, etc. |
| `files_processed` | `list[str]` | JSON array of file paths |
| `entity_count` | `int` | Entities processed |
| `processing_time_seconds` | `float` | Duration |
| `success` | `bool` | Outcome |

### Repositories

#### MappingRepository (Abstract)

```python
class MappingRepository(ABC):
    def find_by_full_name(self, full_name: str) -> Entity | None: ...
    def find_by_component(self, component: str, component_type: str) -> list[Entity]: ...
    def save(self, entity: Entity) -> Entity: ...
    def save_batch(self, entities: list[Entity]) -> list[Entity]: ...
    def find_all(self, entity_type=None, is_ambiguous=None) -> list[Entity]: ...
```

#### AuditRepository

```python
from gdpr_pseudonymizer.data.repositories.audit_repository import AuditRepository

repo = AuditRepository(session)
repo.log_operation(operation)
operations = repo.find_operations(operation_type="PROCESS", success=True)
repo.export_to_csv("audit_log.csv")
```

### EncryptionService

AES-256-SIV deterministic authenticated encryption:

```python
from gdpr_pseudonymizer.data.encryption import EncryptionService

salt = EncryptionService.generate_salt()
valid, msg = EncryptionService.validate_passphrase("my-passphrase")

service = EncryptionService(passphrase="...", salt=salt)
ciphertext = service.encrypt("Marie Dubois")
plaintext = service.decrypt(ciphertext)
```

---

## Validation Module (`gdpr_pseudonymizer.validation`)

### Validation Workflow

```python
from gdpr_pseudonymizer.validation.workflow import run_validation_workflow

validated_entities = run_validation_workflow(
    entities=detected_entities,
    document_text=text,
    document_path="input.txt",
    pseudonym_assigner=my_assigner_fn  # Optional callback
)
```

### Review States

| State | Description |
|-------|-------------|
| `PENDING` | Awaiting user review |
| `CONFIRMED` | Confirmed as correct entity |
| `REJECTED` | Rejected as false positive |
| `MODIFIED` | Entity text modified by user |
| `ADDED` | Manually added by user |

### User Actions

| Action Class | Description |
|-------------|-------------|
| `ConfirmAction(entity)` | Accept entity and pseudonym |
| `RejectAction(entity)` | Mark as false positive |
| `ModifyAction(entity, new_text)` | Change entity text |
| `AddAction(text, entity_type, start_pos, end_pos)` | Add missed entity |
| `ChangePseudonymAction(entity, new_pseudonym)` | Override pseudonym |

---

## Utils Module (`gdpr_pseudonymizer.utils`)

### File Handling

```python
from gdpr_pseudonymizer.utils.file_handler import read_file, write_file, validate_file_path

text = read_file("input.txt")
write_file("output.txt", pseudonymized_text)
validate_file_path("doc.txt", allowed_extensions=[".txt", ".md"])
```

### Configuration

```python
from gdpr_pseudonymizer.utils.config_manager import load_config, Config

config = load_config("config.yaml")  # Or None for defaults
# config.theme, config.model_name, config.db_path, etc.
```

### Logging

```python
from gdpr_pseudonymizer.utils.logger import configure_logging, get_logger

configure_logging("INFO")
logger = get_logger("my_module")
logger.info("entity_detected", entity_type="PERSON", confidence=0.92)
```

---

## Exceptions

All exceptions inherit from `PseudonymizerError`:

| Exception | When Raised |
|-----------|-------------|
| `ConfigurationError` | Invalid or missing configuration |
| `ModelNotFoundError` | NLP model cannot be loaded |
| `EncryptionError` | Encryption or decryption fails |
| `ValidationError` | Validation workflow error |
| `FileProcessingError` | File I/O operation fails |

```python
from gdpr_pseudonymizer.exceptions import (
    PseudonymizerError,
    ConfigurationError,
    ModelNotFoundError,
    EncryptionError,
    ValidationError,
    FileProcessingError,
)
```

---

## Extension Points

### Custom Pseudonym Libraries

Create a JSON file in `data/pseudonyms/` following this schema:

```json
{
  "theme": "my_theme",
  "data_sources": [
    {
      "source_name": "Description",
      "url": "https://...",
      "license": "License type",
      "usage_justification": "Why this source",
      "extraction_date": "2026-01-01",
      "extraction_method": "How data was collected"
    }
  ],
  "first_names": {
    "male": ["Name1", "Name2"],
    "female": ["Name3", "Name4"],
    "neutral": ["Name5", "Name6"]
  },
  "last_names": ["LastName1", "LastName2"],
  "locations": {
    "cities": ["City1", "City2"],
    "regions": ["Region1", "Region2"]
  },
  "organizations": {
    "companies": ["Company1", "Company2"],
    "agencies": ["Agency1"],
    "institutions": ["Institute1"]
  }
}
```

**Minimum requirements:** 500+ first names, 500+ last names, 80+ locations, 35+ organizations.

**Usage:**
```python
manager = LibraryBasedPseudonymManager()
manager.load_library("my_theme")
```

Or via CLI:
```bash
poetry run gdpr-pseudo process doc.txt --theme my_theme
```

### Custom NLP Detector

Extend the `EntityDetector` abstract base class:

```python
from gdpr_pseudonymizer.nlp.entity_detector import EntityDetector, DetectedEntity

class MyDetector(EntityDetector):
    def load_model(self, model_name: str) -> None:
        # Load your model
        pass

    def detect_entities(self, text: str) -> list[DetectedEntity]:
        # Return detected entities
        pass

    def get_model_info(self) -> dict[str, str]:
        return {"name": "my_model", "version": "1.0"}

    @property
    def supports_gender_classification(self) -> bool:
        return False
```

---

## Programmatic Usage Example

Complete example of pseudonymizing a document programmatically:

```python
from gdpr_pseudonymizer.core.document_processor import DocumentProcessor

# Initialize processor
processor = DocumentProcessor(
    db_path="project.db",
    passphrase="MySecurePassphrase123",
    theme="neutral",
    model_name="spacy"
)

# Process document (skip_validation=True for non-interactive use)
result = processor.process_document(
    input_path="interview.txt",
    output_path="interview_pseudonymized.txt",
    skip_validation=True,
    entity_type_filter={"PERSON", "LOCATION"}  # Optional: only process these types
)

if result.success:
    print(f"Processed {result.entities_detected} entities")
    print(f"New: {result.entities_new}, Reused: {result.entities_reused}")
    print(f"Time: {result.processing_time_seconds:.2f}s")
else:
    print(f"Error: {result.error_message}")
```

---

## Related Documentation

- [CLI Reference](CLI-REFERENCE.md) - Command-line interface documentation
- [Methodology](methodology.md) - Technical approach and GDPR compliance
- [Installation Guide](installation.md) - Setup instructions
- [Tutorial](tutorial.md) - Usage tutorials
