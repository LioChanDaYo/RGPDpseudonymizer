# 6. Components

Based on the architectural patterns, tech stack, and module interfaces defined above, this section identifies the major logical components across the application with clear boundaries and responsibilities.

### 6.1 CLI Layer

**Responsibility:** User interaction, command parsing, input validation, and output formatting. Translates user commands into orchestrator calls.

**Key Interfaces:**
- `gdpr-pseudo process <file>` - Single document pseudonymization
- `gdpr-pseudo batch <directory>` - Multi-document batch processing
- `gdpr-pseudo init` - Initialize encrypted mapping table
- `gdpr-pseudo list-mappings` - View entity↔pseudonym correspondences
- `gdpr-pseudo stats` - Show usage statistics
- `gdpr-pseudo export` - Export audit log
- `gdpr-pseudo destroy-table` - Secure deletion with confirmation

**Dependencies:**
- Core Orchestrator (delegates workflow execution)
- Configuration loader (reads `.gdpr-pseudo.yaml`)
- Rich library (progress bars, formatted tables)

**Technology Stack:**
- Typer (CLI framework with auto-generated help)
- Rich (enhanced terminal UI)
- PyYAML (configuration parsing)

**Key Design Decisions:**
- **Stateless commands:** Each CLI invocation creates fresh orchestrator instance (no daemon process)
- **Input validation at boundary:** File existence, passphrase strength, format checks before passing to Core
- **User-friendly errors:** All exceptions caught and formatted with actionable guidance (NFR7)
- **Progress indicators:** Batch mode shows real-time progress via Rich progress bars

---

### 6.2 Core Orchestrator

**Responsibility:** Workflow coordination for single-document and batch processing. Orchestrates entity detection → mapping lookup → pseudonym assignment → replacement → audit logging sequence.

**Key Interfaces:**
- `process_document(input_path, output_path, validation_mode) -> ProcessingResult`
- `process_batch(input_paths, output_dir, validation_mode, workers) -> BatchResult`
- `validate_entities(entities) -> List[Entity]` - Interactive validation mode

**Dependencies:**
- EntityDetector (NLP engine)
- MappingRepository (persistence)
- AuditRepository (audit logs)
- PseudonymManager (pseudonym assignment)
- FileHandler (I/O operations)

**Key Design Decisions:**
- **Single Responsibility:** Orchestrates workflow but doesn't implement domain logic
- **Dependency Injection:** All dependencies passed as interfaces (enables testing with mocks)
- **Write Coordinator Pattern:** In batch mode, workers send detected entities via Queue, only main process writes to database (Risk #2 mitigation)
- **Transaction boundaries:** Each document is a transaction (commit per document, not per entity)

---

### 6.3 NLP Engine

**Responsibility:** Entity detection using French NER models. Detects PERSON, LOCATION, ORG entities with optional confidence scores and gender classification.

**Key Interfaces:**
- `EntityDetector.detect_entities(text) -> List[DetectedEntity]` (abstract interface)
- Concrete implementations: `SpaCyDetector`, `StanzaDetector`

**Dependencies:**
- spaCy/Stanza libraries (external NLP frameworks)
- French language models (downloaded post-install)

**Technology Stack:**
- **spaCy 3.7+** with `fr_core_news_lg` model (preferred - pending Epic 1 benchmark)
- **Alternative: Stanza 1.7+** with French models (fallback if spaCy <85% accuracy)

**Key Design Decisions:**
- **Lazy Model Loading:** Models loaded on first `detect_entities()` call, not during CLI startup (improves NFR5: <5s startup time)
- **Interface Abstraction:** `EntityDetector` interface allows swapping libraries without changing Core logic
- **Compound Name Handling:** Special detection for French hyphenated names (Jean-Pierre, Marie-Claire) via regex patterns if NER doesn't capture them (FR20)
- **Confidence Thresholds:** Low-confidence entities (<0.6) flagged as ambiguous for validation mode review (Risk #3 mitigation)

**Performance Characteristics:**
- Model size: ~500MB (fr_core_news_lg)
- Memory footprint: ~1.5GB when loaded
- Processing speed: ~2-5K words/second on consumer hardware
- Thread safety: **NOT thread-safe** (requires process-based parallelism)

---

### 6.4 Pseudonym Manager

**Responsibility:** Load themed pseudonym libraries, assign pseudonyms with compositional logic (FR4-5), track library exhaustion (FR11), prevent duplicate assignments (Risk #7).

**Key Interfaces:**
- `PseudonymManager.assign_pseudonym(...) -> PseudonymAssignment`
- `PseudonymManager.check_exhaustion() -> float`
- `PseudonymManager.mark_as_used(pseudonym)`

**Dependencies:**
- Pseudonym library JSON files (`data/pseudonyms/*.json`)
- MappingRepository (query existing component mappings)

**Key Design Decisions:**
- **Compositional Logic:** When assigning "Marie Dupont" pseudonym, first check if "Marie" already mapped (e.g., to "Leia"), reuse it and assign new last name ("Skywalker")
- **Gender-Preserving:** If NER provides gender, select pseudonym from matching gender pool (male/female/neutral)
- **Exhaustion Tracking:** Maintain used pseudonym set, warn at 80% exhaustion, fallback to "Person-001" systematic naming when library depleted (FR11)
- **Collision Prevention:** Never assign same full pseudonym to different entities (Risk #7 mitigation via `mark_as_used()`)

**Library Structure:**
```json
{
  "theme": "star_wars",
  "first_names": {
    "male": ["Luke", "Han", "Anakin", ...],
    "female": ["Leia", "Padmé", "Rey", ...],
    "neutral": ["Yoda", "Chewbacca", ...]
  },
  "last_names": ["Skywalker", "Organa", "Solo", "Kenobi", ...]
}
```

**MVP Libraries:**
1. **Neutral** - French INSEE common names (500+ first, 500+ last)
2. **Star Wars** - Curated character names (500+ first, 500+ last)
3. **LOTR** - Tolkien universe names (500+ first, 500+ last)

---

### 6.5 Data Layer

**Responsibility:** Persist entity mappings and audit logs with encryption, provide repository interfaces for data access, manage database lifecycle (initialization, migration, secure deletion).

**Key Interfaces:**
- `MappingRepository` (entity↔pseudonym mappings)
- `AuditRepository` (operation audit logs)
- `MetadataRepository` (system configuration)
- `EncryptionService` (Fernet encryption/decryption)

**Dependencies:**
- SQLite database (local file)
- SQLAlchemy ORM (abstraction layer)
- cryptography library (Fernet encryption)

**Technology Stack:**
- **SQLite 3.35+** (embedded database)
- **SQLAlchemy 2.0+** (ORM with modern API)
- **cryptography 41.0+** (Fernet symmetric encryption)

**Key Design Decisions:**
- **Column-Level Encryption:** Encrypt sensitive fields (names, pseudonyms) individually before INSERT, decrypt on SELECT (application-level, not database-level)
- **Passphrase Canary:** Store encrypted verification string to validate passphrase on database open (Risk #1 mitigation)
- **WAL Mode:** SQLite Write-Ahead Logging enables concurrent reads by worker processes while main process writes
- **No Connection Pooling:** Single writer (main process) negates need for pool
- **Schema Versioning:** `Metadata.schema_version` checked on open, enables future Alembic migrations (Risk #4 mitigation)

---

### 6.6 File I/O Handler

**Responsibility:** Read input documents, write pseudonymized output, detect file format, identify exclusion zones for Markdown (FR21), apply entity replacements while respecting exclusion zones.

**Key Interfaces:**
- `FileHandler.read_document(path) -> str`
- `FileHandler.write_document(path, content)`
- `FileHandler.get_exclusion_zones(content, format) -> List[ExclusionZone]`
- `FileHandler.apply_replacements(content, replacements, exclusions) -> str`

**Dependencies:**
- pathlib (cross-platform file paths)
- markdown-it-py (Markdown AST parsing for exclusion zones)

**Key Design Decisions:**
- **Format Detection:** File extension-based (`.txt` → plain text, `.md` → Markdown)
- **Markdown Exclusion Zones:** Parse AST to identify code blocks (```), inline code (`), URLs in links, image references (FR21)
- **Replacement Strategy:** Apply replacements in reverse position order to maintain character offsets
- **Overlap Detection:** Skip replacements that overlap with exclusion zones

---

### 6.7 Batch Processor

**Responsibility:** Parallel processing of multiple documents using worker pool, aggregate results, coordinate database writes (write coordinator pattern), provide progress indicators.

**Key Interfaces:**
- `BatchProcessor.process_batch(file_paths, output_dir, workers) -> BatchResult`
- Internal: Worker process executes `process_single_document()` workflow

**Dependencies:**
- Core Orchestrator (`process_single_document()` function)
- Python multiprocessing (process pool)
- Queue (worker → main process communication)

**Key Design Decisions:**
- **Write Coordinator Pattern:** Workers detect entities, send to main process via Queue, main process is sole database writer (Risk #2 mitigation - eliminates SQLite concurrency issues)
- **Worker Pool Size:** `min(cpu_count, 4)` to balance parallelism with memory constraints (4 workers × 1.5GB model = 6GB)
- **Isolated Workers:** Each worker loads own NLP model copy (process memory isolation, no shared state)
- **Error Handling:** Individual document failures don't stop batch, errors logged and reported at end

**Architecture:**
```
Main Process:
  ├─ Spawn 4 Worker Processes
  ├─ Distribute documents via input queue
  ├─ Receive detected entities via output queue
  ├─ Write all entities to database (sole writer)
  └─ Aggregate results and generate summary

Worker Process (×4):
  ├─ Load NLP model (isolated copy)
  ├─ Read document from input queue
  ├─ Detect entities
  ├─ Send entities to output queue
  └─ Wait for next document
```

**Performance Characteristics:**
- **Target:** Process 50 documents in <30min (NFR2)
- **Expected Speedup:** 3-4x vs sequential (4 workers, accounting for coordination overhead)
- **Memory Usage:** 4 workers × 1.5GB model + 1GB main process ≈ 7GB total

---

### 6.8 Validation Mode Handler

**Responsibility:** Interactive entity review when `--validate` flag enabled (FR7, FR18), present detected entities to user, allow corrections/additions/removals, apply user modifications before final pseudonymization.

**Key Interfaces:**
- `ValidationHandler.present_entities(entities) -> List[Entity]` (user interaction)
- `ValidationHandler.allow_corrections(entity) -> Entity`

**Dependencies:**
- Rich library (formatted tables, interactive prompts)
- Core Orchestrator (receives modified entity list)

**Key Design Decisions:**
- **Default OFF:** Validation mode disabled by default for fast processing (FR18)
- **Batch vs Single:** In batch mode with validation, review all entities from all documents before processing begins (one review session, not per-document)
- **Ambiguity Highlighting:** Entities with `is_ambiguous=True` shown in different color, user prompted to confirm or correct
- **Modification Logging:** All user changes logged in `Operation.user_modifications` field for audit trail (FR12)

---
