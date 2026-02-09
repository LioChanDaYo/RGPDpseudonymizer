# Alpha Feedback Summary

**Collection Date:** 2026-02-09
**Testers:** 1
**Testing Context:** Free-form usage feedback (not structured protocol)
**Story Target:** Story 4.6 (Beta Feedback Integration & Bug Fixes)

---

## Feedback Items

### FB-001: Entity Variant Grouping in Validation UI

**Category:** UX / NER
**Priority:** HIGH
**Source Quote:** _"C'est confusant qu'on me propose plusieurs fois le meme nom ou le meme lieu sous toutes ses formes. Exemple : Marie Dubois, Pr. Dubois, Dubois. Aussi : a Lyon, Lyon."_

**Analysis:**
Story 1.9 implemented deduplication for **exact-match** entities (same text + same type). This feedback surfaces a **different problem**: variant forms of the same real-world entity are presented as separate validation items.

**Examples reported:**
- PERSON: "Marie Dubois" / "Pr. Dubois" / "Dubois" (same person, 3 validation prompts)
- LOCATION: "a Lyon" / "Lyon" (same place, 2 validation prompts)

**Potential Approaches:**
1. Entity co-reference clustering (group variants of the same entity)
2. Strip titles/prepositions before dedup comparison
3. Substring matching heuristic (if "Dubois" is a suffix of "Marie Dubois", suggest grouping)

**Backlog Mapping:** NEW — no existing backlog item covers this. Needs new FE-xxx entry.

---

### FB-002: French Documentation

**Category:** Documentation
**Priority:** MEDIUM
**Source Quote:** _"On veut de la doc en francais."_

**Analysis:**
Primary user base is French-speaking. All current documentation is in English.

**Backlog Mapping:** **FE-010** (French Documentation Translation) — already planned for v1.1.
**Recommendation:** Consider pulling FE-010 forward into Epic 4 scope, or at minimum provide a French README and installation guide before launch.

---

### FB-003: Selective Entity Type Processing

**Category:** Feature Request
**Priority:** MEDIUM
**Source Quote:** _"J'aimerais qu'il soit possible de choisir ce qu'on processe : uniquement les personnes, par exemple."_

**Analysis:**
User wants a CLI flag to filter which entity types are processed/pseudonymized (e.g., `--entity-types PERSON` to skip LOCATION and ORG). Use case: when only person names are sensitive in a given context.

**Backlog Mapping:** NEW — no existing backlog item. Needs new FE-xxx entry.

---

### FB-004: Additional Format Support (DOCX, etc.)

**Category:** Feature Request
**Priority:** LOW (for MVP)
**Source Quote:** _"A quand le traitement d'autres formats ? docx etc."_

**Analysis:**
Currently only plain text (.txt) is supported. Users expect DOCX support at minimum. PDF also mentioned in backlog.

**Backlog Mapping:** Already in v1.1 roadmap ("PDF/DOCX format support"). Confirms user demand.

---

### FB-005: GUI Highly Anticipated

**Category:** Feature Request
**Priority:** LOW (for MVP) / HIGH (for adoption)
**Source Quote:** _"L'interface graphique est tres attendue."_

**Analysis:**
CLI-only interface is a barrier for non-technical users. GUI is on the v2.0 roadmap per PRD.

**Backlog Mapping:** v2.0 roadmap item. Feedback confirms strong demand — reinforces priority for v2.0 planning.

---

### FB-006: Newer Python Version Support

**Category:** Compatibility
**Priority:** MEDIUM
**Source Quote:** _"Versions suivantes de Python ?"_

**Analysis:**
User wants support for Python 3.12+. Currently CI tests 3.10-3.11 only.

**Backlog Mapping:** **TD-004** (Python Version Support Inconsistency) + **MON-005** (spaCy compatibility monitoring). Both already tracked. Story 4.5 AC9 investigated MON-005 findings.

---

### FB-007: Slow `--help` Display

**Category:** Bug / Performance
**Priority:** HIGH
**Source Quote:** _"L'affichage du help est lente, est-ce que le projet est trop volumineux ?"_

**Analysis:**
The `--help` flag is slow, likely because Typer eagerly imports the full module tree (spaCy, torch, stanza, SQLAlchemy, cryptography) just to render help text. This is a known pattern with heavy NLP dependencies.

**Potential Fixes:**
1. Lazy imports: defer heavy imports (spaCy, stanza, torch) until actually needed by a command
2. Typer lazy loading: use `typer.Typer(invoke_without_command=True)` patterns to avoid importing command implementations at app construction time

**Backlog Mapping:** NEW — no existing backlog item. Needs new item (likely TD-005 or FE-xxx). Related to Story 4.5 AC3 (startup time NFR).

---

## Summary Matrix

| ID | Item | Category | Backlog Match | Priority | MVP Scope? |
|----|------|----------|---------------|----------|------------|
| FB-001 | Entity variant grouping | UX/NER | NEW | HIGH | Story 4.6 |
| FB-002 | French documentation | Docs | FE-010 | MEDIUM | Partial |
| FB-003 | Selective entity types | Feature | NEW | MEDIUM | Story 4.6 |
| FB-004 | DOCX/PDF support | Feature | v1.1 roadmap | LOW | No (v1.1) |
| FB-005 | GUI | Feature | v2.0 roadmap | LOW | No (v2.0) |
| FB-006 | Python 3.12+ | Compat | TD-004/MON-005 | MEDIUM | Story 4.6 |
| FB-007 | Slow --help | Perf/Bug | NEW | HIGH | Story 4.6 |

## Recommendations for Story 4.6

**Must address (HIGH):**
- FB-001: Entity variant grouping — biggest UX pain point reported
- FB-007: Slow --help — first impression issue, erodes confidence in the tool

**Should address (MEDIUM):**
- FB-003: Selective entity types — quick CLI flag addition, high user value
- FB-006: Python 3.12+ — depends on Story 4.5 MON-005 findings

**Acknowledge in release notes / roadmap (LOW for MVP):**
- FB-002: French docs — commit to v1.1 timeline, possibly ship French README with MVP
- FB-004: DOCX/PDF — confirm v1.1 target
- FB-005: GUI — confirm v2.0 target

---

## Story 4.6 Task Mappings

| ID | Priority | Story 4.6 Task | AC |
|----|----------|----------------|-----|
| FB-001 | HIGH | Task 4.6.3 (Entity Variant Grouping) | AC3, AC6 |
| FB-002 | MEDIUM | Deferred to v1.1 (FE-010) | AC5 |
| FB-003 | MEDIUM | Task 4.6.4 (Selective Entity Type Processing) | AC4, AC6 |
| FB-004 | LOW | Deferred to v1.1 | AC5 |
| FB-005 | LOW | Deferred to v2.0 | AC5 |
| FB-006 | MEDIUM | Task 4.6.5 (Python 3.13 CI Evaluation) | AC4, AC6 |
| FB-007 | HIGH | Task 4.6.2 (Lazy Imports Fix) | AC3, AC6 |

**No critical bugs (AC2):** Alpha testing revealed no data loss, crashes, incorrect pseudonymization, or security issues. AC2 is satisfied by confirmed absence of critical bugs.

---

**Next Step:** Story 4.6 implementation in progress.
