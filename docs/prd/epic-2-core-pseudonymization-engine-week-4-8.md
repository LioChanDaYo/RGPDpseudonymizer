# Epic 2: Core Pseudonymization Engine (Week 4-8)

**Epic Goal:** Implement production-quality compositional pseudonymization logic with encrypted mapping tables and audit trails, enabling consistent entity replacement across documents while validating architectural scalability for batch processing.

---

### Story 2.1: Pseudonym Library System

**As a** user,
**I want** themed pseudonym libraries with sufficient name combinations,
**so that** pseudonymized documents maintain readability and avoid repetitive fallback naming.

#### Acceptance Criteria

1. **AC1:** JSON-based pseudonym library structure implemented per Technical Assumptions: separate `first_names` (by gender) and `last_names` arrays.
2. **AC2:** Three themed libraries created with ≥500 first names and ≥500 last names each:
   - Neutral/Generic (French common names from INSEE public data)
   - Star Wars (curated from fan wikis)
   - LOTR (curated from Tolkien Gateway)
3. **AC3:** Gender metadata included where applicable (male/female/neutral tags).
4. **AC4:** Library manager implemented: load themes, select pseudonyms with gender-matching logic (when NER provides gender data).
5. **AC5:** Pseudonym exhaustion detection: warn when library usage exceeds 80%, provide systematic fallback naming ("Person-001", "Location-001") when exhausted.
6. **AC6:** Unit tests: library loading, pseudonym selection (with/without gender), exhaustion handling.
7. **AC7:** Library sourcing documented for legal compliance (public domain, fair use considerations).

---

### Story 2.2: Compositional Pseudonymization Logic (FR4-5)

**As a** user,
**I want** consistent pseudonym application using compositional strict matching,
**so that** "Marie Dubois" → "Leia Organa" everywhere, with "Marie" → "Leia" and "Dubois" → "Organa" when they appear alone.

#### Acceptance Criteria

1. **AC1:** Full name entity detection: identify complete person names (first + last) from NER results.
2. **AC2:** Composite pseudonym assignment: Map full name to full pseudonym (e.g., "Marie Dubois" → "Leia Organa").
3. **AC3:** Component mapping: Extract and store first name → pseudonym first name, last name → pseudonym last name mappings.
4. **AC4:** Standalone component replacement: When "Marie" appears alone, replace with "Leia" (using first name mapping).
5. **AC5:** Shared component handling (FR5): "Marie Dubois" → "Leia Organa", "Marie Dupont" → "Leia Skywalker" (preserves "Marie" → "Leia" consistency).
6. **AC6:** Ambiguous component flagging: Log standalone components without full name context as potentially ambiguous for validation mode review.
7. **AC7:** Unit tests: full name composition, component extraction, standalone replacement, shared component scenarios.
8. **AC8:** Integration test: Process documents with complex name patterns, verify compositional logic correctness.

---

### Story 2.3: Compound Name Handling (FR20)

**As a** user,
**I want** French compound first names like "Jean-Pierre" and "Marie-Claire" handled correctly,
**so that** pseudonymization maintains name structure integrity.

#### Acceptance Criteria

1. **AC1:** Compound first name detection: Identify hyphenated first names in NER results.
2. **AC2:** Compound pseudonym assignment: Map compound names to compound pseudonyms (e.g., "Jean-Pierre" → "Luke-Han").
3. **AC3:** Component awareness: If "Jean" or "Pierre" appear separately, handle based on context (log as ambiguous if unclear).
4. **AC4:** Regex pattern support: Fallback regex for detecting common French compound patterns if NER doesn't identify them.
5. **AC5:** Unit tests: compound name detection, pseudonym assignment, edge cases (triple compounds, non-standard separators).
6. **AC6:** Test corpus validation: Verify compound names in test corpus processed correctly (from Story 1.1 edge cases).

---

### Story 2.4: Encrypted Mapping Table with Python-Native Encryption

**As a** user,
**I want** a secure encrypted mapping table storing original↔pseudonym correspondences,
**so that** I can exercise GDPR rights (reversibility) while protecting sensitive data.

#### Acceptance Criteria

1. **AC1:** SQLite database schema implemented per Technical Assumptions:
   - `entities` table: id, entity_type, first_name, last_name, full_name, pseudonym_first, pseudonym_last, pseudonym_full, first_seen_timestamp, gender, confidence_score
   - `operations` table: id, timestamp, operation_type, files_processed, model_name, model_version, theme_selected, user_modifications, entity_count
   - `metadata` table: key, value (stores encryption params, schema version)
2. **AC2:** Python-native encryption implemented using `cryptography` library (Fernet symmetric encryption).
3. **AC3:** Passphrase-based key derivation: PBKDF2 with salt stored in `metadata` table.
4. **AC4:** Column-level encryption: Sensitive columns (names, pseudonyms) encrypted individually.
5. **AC5:** Passphrase validation on database open: verify passphrase before allowing access.
6. **AC6:** Passphrase strength validation: minimum 12 characters (NFR12), provide entropy feedback ("weak/medium/strong").
7. **AC7:** Database operations: create, open (with passphrase), query mappings, insert new entities, close.
8. **AC8:** Unit tests: encryption/decryption, passphrase validation, CRUD operations, error handling (wrong passphrase, corrupted database).
9. **AC9:** Security review: No plaintext sensitive data in logs, no temp file leakage.

---

### Story 2.5: Audit Logging (FR12)

**As a** compliance officer,
**I want** comprehensive audit logs of all pseudonymization operations,
**so that** I can demonstrate GDPR Article 30 compliance and troubleshoot issues.

#### Acceptance Criteria

1. **AC1:** Audit log implemented in `operations` table (from Story 2.4 schema).
2. **AC2:** Log entry created for each pseudonymization operation with required fields (FR12): timestamp, operation type, files processed, model version, theme selected, entity count.
3. **AC3:** User modifications logged when validation mode used (deferred to Epic 3, placeholder in schema).
4. **AC4:** Export functionality: Query audit log and export to JSON or CSV format.
5. **AC5:** Log rotation not required for MVP (SQLite database handles growth).
6. **AC6:** Unit tests: log entry creation, query operations, export functionality.
7. **AC7:** Documentation: audit log schema, query examples, GDPR Article 30 mapping.

---

### Story 2.6: Single-Document Pseudonymization Workflow

**As a** user,
**I want** to pseudonymize a single document with all compositional logic applied,
**so that** I can validate the core value proposition on real documents.

#### Acceptance Criteria

1. **AC1:** Integrate all Epic 2 components: NER detection (Epic 1) → compositional logic (2.2) → compound handling (2.3) → mapping table (2.4) → audit log (2.5).
2. **AC2:** `process` command updated from Epic 1 skeleton to production implementation.
3. **AC3:** Workflow: Load document → detect entities → assign pseudonyms (compositional) → store mappings → apply replacements → write output → log operation.
4. **AC4:** Idempotent behavior (FR19): Re-processing same document reuses existing mappings.
5. **AC5:** Performance validation (NFR1): Process 2-5K word document in <30 seconds on standard hardware.
6. **AC6:** Accuracy validation: False negative rate <10% (NFR8), false positive rate <15% (NFR9) on test corpus.
7. **AC7:** Integration tests: End-to-end workflow, idempotency, error scenarios (file not found, encryption errors).
8. **AC8:** Can demo to alpha testers: Fully functional single-document pseudonymization.

---

### Story 2.7: Architectural Spike - Batch Processing Scalability

**As a** developer,
**I want** to validate that our architecture can handle batch processing efficiently,
**so that** Epic 3 batch implementation doesn't require major refactoring.

#### Acceptance Criteria

1. **AC1:** Prototype batch processing with process-based parallelism (multiprocessing module).
2. **AC2:** Test with 10-document batch: process in parallel using worker pool (min(cpu_count, 4) workers).
3. **AC3:** Validate mapping table consistency: Cross-document entity mapping works correctly (same entity gets same pseudonym across batch).
4. **AC4:** Performance measurement: Estimate batch processing time vs sequential processing (should show speedup).
5. **AC5:** Identify architectural issues: memory leaks, mapping table contention, worker process overhead.
6. **AC6:** Document findings: Recommendations for Epic 3 implementation, known limitations, optimization opportunities.
7. **AC7:** If major issues found, adjust architecture before proceeding to Epic 3.

---

### Story 2.8: Alpha Release Preparation

**As a** product manager,
**I want** to release an alpha version to 3-5 friendly users after Epic 2,
**so that** I can validate core value proposition and gather early feedback before investing in CLI polish and batch features.

#### Acceptance Criteria

1. **AC1:** Basic installation package created: PyPI-style package installable via `pip install -e .`.
2. **AC2:** Minimal documentation: README with installation instructions, basic usage example, known limitations.
3. **AC3:** Alpha testers identified and onboarded (3-5 users: 2 researchers, 2-3 LLM users).
4. **AC4:** Alpha testing protocol created: specific tasks for testers, feedback survey questions.
5. **AC5:** Feedback collection mechanism: Google Form or GitHub issues for structured feedback.
6. **AC6:** Alpha release tagged in Git: `v0.1.0-alpha`.
7. **AC7:** Alpha feedback review session scheduled (end of week 6-7) to inform Epic 3 priorities.

---
