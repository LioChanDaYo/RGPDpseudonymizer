# 1. Introduction

This document outlines the complete system architecture for the **GDPR Pseudonymizer**, a local Python CLI tool that enables GDPR-compliant pseudonymization of French text documents. The tool automatically detects and replaces personal identifiers (names, locations, organizations) with consistent, readable pseudonyms—entirely on the user's infrastructure.

While this is not a traditional fullstack web application, this architecture document covers the complete technology stack from the CLI interface layer through the core processing engine, NLP pipeline, data persistence layer, and infrastructure concerns. It serves as the single source of truth for AI-driven development of a modular monolithic Python application.

**Architecture Philosophy:** This design prioritizes **local-first processing**, **cross-platform compatibility**, **security by design**, and **clear modular boundaries** that enable future evolution (potential GUI in Phase 2, alternative NLP engines, extended language support).

---

### 1.1 Primary Use Case: LLM Enablement

This architecture enables the core workflow:

**User has sensitive French documents → Pseudonymize locally → Safely send to ChatGPT/Claude → Analyze results → Reverse pseudonyms if needed**

Every architectural decision prioritizes this workflow's **reliability**, **security**, and **document utility preservation**. The system must maintain ≥80% LLM analysis quality while protecting personal data through local-only processing with encrypted reversible mappings.

---

### 1.2 Starter Template or Existing Project

**Status:** N/A - Greenfield project

This is a new Python CLI application built from scratch without starter templates. The project uses:
- **Poetry** for modern Python dependency management and packaging
- **Typer** as the CLI framework foundation (chosen for excellent type hints support)
- **spaCy/Stanza** NLP framework (selection determined in Epic 0-1 benchmarking via decision tree below)
- Standard Python project structure with clear module boundaries

**NLP Library Selection (Week 0 Decision Tree):**
- **IF** spaCy achieves ≥85% F1 score: Choose spaCy (faster, better documentation, larger community)
- **ELSE IF** Stanza achieves ≥85% F1 score: Choose Stanza (Stanford NLP quality)
- **ELSE IF** best score ≥80% F1: Proceed with mandatory `--validate` mode enabled by default (user reviews all entities)
- **ELSE**: Execute contingency plan:
  - **Option A:** Hybrid NER + French name dictionary rules
  - **Option B:** Pivot to English language market (higher NER accuracy available)

**Rationale for Greenfield Approach:**
- No existing Python CLI templates provide the specific combination of NLP, encryption, and batch processing needed
- Clean slate allows optimal architecture for local-first, security-focused design
- Modular structure from day one enables future feature expansion without technical debt

**NLP Abstraction Layer:** The architecture defines an `EntityDetector` interface to isolate spaCy/Stanza implementation details. This enables Epic 1 benchmarking (testing both libraries) and future library swaps without core logic changes. Minimal overhead (~50 lines of code), high flexibility value.

---

### 1.3 Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-01-12 | v1.0 | Initial architecture document creation | Winston (Architect) |

---

### 1.4 Rationale & Key Architectural Decisions

**Trade-offs Made:**

1. **Monolithic vs Microservices:** Chose modular monolith for MVP simplicity while maintaining clear internal boundaries (CLI → Core → NLP → Data layers). This reduces deployment complexity and avoids network overhead while preserving future decomposition options.

2. **Process-based Parallelism:** Required by spaCy's thread-safety limitations (global model state). Increases memory footprint but enables batch processing scalability. Alternative would be sequential processing (unacceptable for 50+ document batches).

3. **Python-native Encryption vs SQLCipher:** Switched from SQLCipher to Python's `cryptography` library to eliminate platform-specific compilation issues. Using **`cryptography.fernet`** (symmetric AES-128 in CBC mode with HMAC authentication) via PBKDF2 key derivation from user passphrase. Column-level encryption for names/pseudonyms provides equivalent security with 85%+ installation success rate target (NFR3).

4. **CLI-only MVP:** Defers GUI to Phase 2 to validate core value proposition with technical early adopters first. Reduces scope risk and accelerates time-to-market for primary use case (LLM enablement).

**Architectural Constraint:** Process-based parallelism with shared SQLite creates database locking that limits future service decomposition. This is acceptable for MVP (single-user, local-only tool) but Phase 3+ distributed architecture would require migration to client-server database (PostgreSQL) or message queue pattern. **We are optimizing for MVP success, not hypothetical enterprise scale.**

**Key Assumptions:**
- Users have Python 3.9+ installed or can install it (target platforms: Windows 10/11, macOS 11+, Linux)
- NLP library (spaCy or Stanza) achieves ≥85% F1 score on French NER (validated in Epic 0-1 benchmark)
- Consumer hardware sufficient (8GB RAM, dual-core 2.0GHz+ CPU)
- Users accept CLI interaction for MVP; GUI demanded for broader adoption in Phase 2

**Hard Quality Gates:**
- **Week 0:** NLP benchmark achieves ≥85.0% F1 score (not 84.9%) OR execute contingency plan
- **Epic 2:** Single-document processing completes in ≤30s for 95th percentile of test corpus
- **Epic 3:** Batch of 50 documents completes in ≤30min with zero crashes
- **Epic 4:** Installation succeeds on ≥85% of platform test matrix (minimum 17/20 clean installs across Windows/macOS/Linux variants)

---
