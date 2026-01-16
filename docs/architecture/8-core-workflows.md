# 8. Core Workflows

This section illustrates key system workflows using sequence diagrams, showing component interactions including error handling paths and async operations.

### 8.1 Single Document Pseudonymization (Happy Path)

**User Story:** User runs `gdpr-pseudo process input.txt output.txt` to pseudonymize a document.

```mermaid
sequenceDiagram
    actor User
    participant CLI as CLI Layer
    participant Orch as Core Orchestrator
    participant File as File Handler
    participant NLP as NLP Engine
    participant Pseudo as Pseudonym Manager
    participant Mapping as Mapping Repository
    participant Audit as Audit Repository
    participant DB as SQLite Database

    User->>CLI: gdpr-pseudo process input.txt output.txt
    CLI->>CLI: Validate input file exists
    CLI->>CLI: Prompt for passphrase (if needed)
    CLI->>Orch: process_document(input.txt, output.txt)

    Orch->>File: read_document(input.txt)
    File-->>Orch: document_text

    Orch->>NLP: detect_entities(document_text)
    NLP->>NLP: Run spaCy NER pipeline
    NLP-->>Orch: List[DetectedEntity]

    Note over Orch: For each detected entity...

    Orch->>Mapping: find_by_full_name("Marie Dubois")
    Mapping->>DB: SELECT with encrypted name
    DB-->>Mapping: NULL (not found)
    Mapping-->>Orch: None (new entity)

    Orch->>Pseudo: assign_pseudonym(PERSON, "Marie", "Dubois", gender="female")
    Pseudo-->>Orch: PseudonymAssignment("Leia Organa", "Leia", "Organa")

    Orch->>Mapping: save(entity)
    Mapping->>DB: INSERT entity
    DB-->>Mapping: Success

    Orch->>File: apply_replacements(text, replacements, exclusions)
    File-->>Orch: pseudonymized_text

    Orch->>File: write_document(output.txt, pseudonymized_text)
    File-->>Orch: Success

    Orch->>Audit: log_operation(PROCESS, [input.txt], model_info, ...)
    Audit->>DB: INSERT operation log

    Orch-->>CLI: ProcessingResult(success=True, entities_count=15, time=12.3s)
    CLI->>User: ✓ Processed input.txt → output.txt (15 entities, 12.3s)
```

**Key Points:**
- **Idempotency Check:** `find_by_full_name()` checks for existing mappings before assignment
- **Transaction Boundary:** Each entity saved individually (could optimize to batch per document)
- **Performance:** ~12s for typical 3000-word document (well under NFR1: <30s)

---

### 8.2 Batch Processing with Write Coordinator Pattern

**User Story:** User runs `gdpr-pseudo batch documents/ output/ --workers 4` to pseudonymize 50 documents in parallel.

```mermaid
sequenceDiagram
    actor User
    participant CLI as CLI Layer
    participant Batch as Batch Processor
    participant Queue as Entity Queue
    participant W1 as Worker 1
    participant W2 as Worker 2
    participant Orch as Core Orchestrator
    participant Mapping as Mapping Repository
    participant DB as SQLite Database

    User->>CLI: gdpr-pseudo batch documents/ output/ --workers 4
    CLI->>Batch: process_batch(file_list, output_dir, workers=4)

    Batch->>Batch: Create input/output queues
    Batch->>W1: Spawn worker process 1
    Batch->>W2: Spawn worker process 2

    Note over W1,W2: Workers load NLP models independently

    Batch->>W1: doc_001.txt (via input queue)
    Batch->>W2: doc_002.txt (via input queue)

    par Worker 1 Processing
        W1->>W1: Detect entities (NLP)
        W1->>Queue: Send DetectedEntity list
    and Worker 2 Processing
        W2->>W2: Detect entities (NLP)
        W2->>Queue: Send DetectedEntity list
    end

    Note over Batch: Main process is SOLE database writer

    loop For each entity batch from queue
        Queue-->>Batch: List[DetectedEntity] from worker

        Batch->>Orch: Process entity batch

        Orch->>Mapping: find_by_full_name(entity)
        Mapping->>DB: SELECT (read-only, WAL mode)

        alt New entity
            Orch->>Mapping: save(new_entity)
            Mapping->>DB: INSERT (main process only writes)
        end
    end

    Batch-->>CLI: BatchResult(success=True, docs=50, entities=750, time=18.5min)
    CLI->>User: ✓ Processed 50 documents (750 entities, 18.5min)
```

**Key Architectural Decisions:**

1. **Write Coordinator Pattern (Risk #2 Mitigation):**
   - **Only main process writes to database** (eliminates SQLite lock contention)
   - Workers are stateless readers (easier to test, no DB connection management)

2. **Performance:**
   - Target: 50 docs in <30min (NFR2)
   - This example: 18.5min (well under target)
   - ~3-4x speedup vs sequential (4 workers with coordination overhead)

---

### 8.3 Compositional Pseudonymization Logic (Complex Case)

**User Story:** System processes document with overlapping name components: "Marie Dubois", "Marie Dupont", "Jean-Marie Leclerc".

```mermaid
sequenceDiagram
    participant Orch as Core Orchestrator
    participant Mapping as Mapping Repository
    participant Pseudo as Pseudonym Manager

    Note over Orch: Entity 1: "Marie Dubois" detected

    Orch->>Mapping: find_by_component("Marie", "first_name")
    Mapping-->>Orch: [] (no existing "Marie")

    Orch->>Pseudo: assign_pseudonym(PERSON, "Marie", "Dubois")
    Pseudo-->>Orch: "Leia Organa"

    Orch->>Mapping: save(Entity: Marie Dubois → Leia Organa)
    Note over Mapping: Stores: first_name="Marie"→"Leia"

    Note over Orch: Entity 2: "Marie Dupont" detected

    Orch->>Mapping: find_by_component("Marie", "first_name")
    Mapping-->>Orch: [Entity with "Marie" → "Leia"]

    Note over Orch: Compositional Logic: Reuse "Leia"

    Orch->>Pseudo: assign_pseudonym(PERSON, "Marie", "Dupont", existing_first="Leia")
    Pseudo-->>Orch: "Leia Skywalker"

    Note over Orch: Entity 3: "Jean-Marie Leclerc" (compound)

    Orch->>Orch: Detect compound first name
    Orch->>Orch: Mark as ambiguous (Risk #3 mitigation)

    Orch->>Pseudo: assign_pseudonym(PERSON, "Jean-Marie", "Leclerc")
    Pseudo-->>Orch: "Luke-Han Solo"

    Note over Orch: Result: "Marie" → "Leia" consistently,<br/>"Jean-Marie" → "Luke-Han" (separate)
```

**FR4-5 Compliance:** Compositional strict matching:
- "Marie Dubois" → "Leia Organa"
- "Marie Dupont" → "Leia Skywalker" (reuses "Leia" for "Marie")
- "Jean-Marie Leclerc" → "Luke-Han Solo" (compound name treated atomically)

---
