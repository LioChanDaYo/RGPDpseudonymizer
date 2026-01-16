# Requirements

### Functional Requirements

**FR1:** The system shall detect personal names (persons) in French text using NER technology with ≥90% precision and recall for both entity detection and entity type classification, treating full names as composite entities (first name + last name).

**FR2:** The system shall detect location entities (cities, countries, regions) in French text using NER technology.

**FR3:** The system shall detect organization entities (companies, institutions) in French text using NER technology.

**FR4:** The system shall replace each detected entity with a consistent pseudonym throughout single documents and across document batches using compositional strict matching: when "Marie Dubois" is pseudonymized to "Leia Organa", all subsequent occurrences of "Marie Dubois" become "Leia Organa", isolated "Marie" becomes "Leia", and isolated "Dubois" becomes "Organa". Standalone name components without full name context shall be flagged for user validation when validation mode is enabled, or logged as ambiguous entities when validation is disabled.

**FR5:** The system shall handle multiple entities sharing name components by maintaining unique pseudonym assignments per complete entity: if both "Marie Dubois" and "Marie Dupont" are detected, they shall be pseudonymized to distinct full pseudonyms (e.g., "Leia Organa" and "Leia Skywalker" respectively), preserving shared first name consistency ("Marie" → "Leia") while distinguishing last names.

**FR6:** The system shall support batch processing of multiple documents (10-100+) with consistent pseudonym mapping across the entire corpus, with mapping table updates applied incrementally to ensure cross-document consistency within the batch.

**FR7:** The system shall provide an optional interactive validation mode (activated via `--validate` flag) that presents detected entities and classification results for review before pseudonymization is applied. Users may correct, add, or remove entities. Validation mode is recommended for highly sensitive documents but not required.

**FR8:** The system shall maintain a secure encrypted mapping table (SQLite with SQLCipher) storing original↔pseudonym correspondences with user-provided passphrase protection.

**FR9:** The system shall support pseudonymization reversibility by allowing authorized users to retrieve original entities from the encrypted mapping table.

**FR10:** The system shall provide themed pseudonym libraries (minimum 2-3 themes) with separate pools of ≥500 first names and ≥500 last names per theme to support compositional pseudonymization with sufficient combinations. Libraries shall include neutral/generic and optional thematic sets (e.g., Star Wars). Gender-preserving pseudonymization is recommended where NER provides gender classification.

**FR11:** The system shall gracefully handle pseudonym library exhaustion by providing clear warnings and systematic fallback naming (e.g., Person-001, Location-001).

**FR12:** The system shall log all pseudonymization operations including timestamp, files processed, entities detected, NLP model name and version, pseudonym theme selected, detection confidence scores (if available), entities modified by user (if validation mode used), and pseudonyms applied.

**FR13:** The system shall accept plain text (.txt) and Markdown (.md) file formats as input for MVP.

**FR14:** The system shall output pseudonymized documents in the same format as input files.

**FR15:** The system shall provide CLI commands: `init` (initialize mapping table), `process` (single document), `batch` (multiple documents), `list-mappings` (view correspondences), `validate-mappings` (review existing mappings without processing), `stats` (show statistics), `import-mappings` (load mappings from previous project), `export` (audit log), `destroy-table` (secure deletion).

**FR16:** The system shall perform all processing locally without network communication or external service dependencies.

**FR17:** The system shall securely delete mapping tables by overwriting data before file deletion when user executes `destroy-table` command, with mandatory user confirmation prompt (yes/no) before destruction to prevent accidental data loss.

**FR18:** The system shall disable validation mode by default (fast processing) and require explicit `--validate` flag to enable interactive review. In batch mode without validation, the system shall provide a summary report of detected entities after processing all documents.

**FR19:** The system shall implement idempotent processing: re-processing the same document shall reuse existing pseudonym mappings from the mapping table, ensuring consistency. If new entities are detected in subsequent runs, only those shall be added to the mapping table.

**FR20:** The system shall detect and handle French compound first names (e.g., "Jean-Pierre", "Marie-Claire") as single first name entities for compositional pseudonymization.

**FR21:** The system shall implement format-aware processing for Markdown files, excluding pseudonymization within URLs, code blocks (```), inline code (`), and image references.

### Non-Functional Requirements

**NFR1:** The system shall process typical documents (2000-5000 words) in <30 seconds on standard consumer hardware (8GB RAM, dual-core 2.0GHz+ CPU). Processing time excludes user interaction time when `--validate` flag is used.

**NFR2:** The system shall process batches of 50 documents in <30 minutes on standard consumer hardware. Processing time excludes user interaction time when `--validate` flag is used.

**NFR3:** The system shall achieve ≥85% installation success rate for first-time users across Windows 10/11, macOS 11+, and Linux (Ubuntu 20.04+, Debian 11+, Fedora 35+).

**NFR4:** The system shall require maximum 8GB RAM and 2GB free disk space (including NLP models and dependencies).

**NFR5:** The system shall start up in <5 seconds after initial installation and model loading.

**NFR6:** The system shall maintain <10% crash/error rate during pseudonymization sessions.

**NFR7:** The system shall provide clear, actionable error messages that enable users to resolve issues without external support in ≥80% of error scenarios.

**NFR8:** The system shall maintain false negative rate <10% (missed sensitive entities) to ensure GDPR compliance safety.

**NFR9:** The system shall maintain false positive rate <15% (incorrectly flagged entities) to minimize user validation burden.

**NFR10:** The system shall preserve pseudonymized document utility such that LLM analysis maintains ≥80% quality compared to original documents (measured via user satisfaction surveys).

**NFR11:** The system shall operate entirely offline with zero network dependencies after initial installation and model download.

**NFR12:** The system shall implement encryption for mapping tables using industry-standard SQLCipher with user-provided passphrase (minimum 12 characters).

**NFR13:** The system shall provide comprehensive documentation including installation guide, usage tutorial, methodology description (for academic citation), FAQ, and troubleshooting guide.

**NFR14:** The system shall enable ≥80% of users to complete their first successful pseudonymization within 30 minutes including installation.

**NFR15:** The system shall support Python 3.9+ runtime environment across all target platforms.

---
