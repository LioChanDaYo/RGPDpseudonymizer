# Batch Processing Spike - Test Corpus

Test corpus for Story 2.7 batch processing scalability validation.

## Corpus Overview

- **Total documents:** 10
- **Language:** French
- **Entity types:** PERSON (names)
- **Entity density:** Low (5-6), Medium (8-10), High (12-15 entities per document)

## Entity Overlap Strategy

Key entities appear across multiple documents to test mapping table consistency:

### Cross-Document Entities

| Entity | Appears in Documents | Purpose |
|--------|---------------------|----------|
| **Marie Dubois** | doc_001, doc_003, doc_007 | Primary overlap test - same person in 3 docs |
| **Pierre Lefebvre** | doc_001, doc_009 | Secondary overlap - consultant in 2 projects |
| **Dr. Marie Dubois** | doc_001, doc_003, doc_007 | Title handling test - same person with title |

### Expected Behavior

- "Marie Dubois" and "Dr. Marie Dubois" should map to **same pseudonym** (title stripping)
- "Dubois" (standalone) should map to **component of Marie Dubois** (compositional logic)
- Cross-document consistency: First occurrence assigns pseudonym, subsequent reuse it

## Document Complexity

| Document | Entity Count | Complexity | Key Features |
|----------|--------------|------------|--------------|
| doc_001.txt | 6 entities | Low | Marie Dubois (3x), Jean Martin (2x), Pierre Lefebvre, Sophie Bernard |
| doc_002.txt | 9 entities | Medium | Luc Fournier, Isabelle Petit, Thomas Rousseau (with standalone "Rousseau", "Petit", "Fournier") |
| doc_003.txt | 10 entities | Medium | Marie Dubois (5x), Claire Fontaine, Antoine Girard, Dr. Dubois |
| doc_004.txt | 9 entities | Medium | Nicolas Blanchard, Véronique Mercier, Émilie Durand (with standalone names) |
| doc_005.txt | 0 entities | Low | No names - tests zero-entity handling |
| doc_006.txt | 8 entities | Medium | Philippe Moreau, Céline Garnier (with standalone "Moreau", "Garnier") |
| doc_007.txt | 12 entities | High | Marie Dubois (4x), François Lambert, Sarah Morel, Alexandre Roux, Dr. Marie Dubois |
| doc_008.txt | 10 entities | Medium | Olivier Dumas, Nathalie Chevalier (with standalone "Chevalier", "Dumas") |
| doc_009.txt | 11 entities | High | Marc Bertrand, Julie Renard, Pierre Lefebvre (with standalone names) |
| doc_010.txt | 10 entities | Medium | Sylvie Lemoine, Bernard Fabre (with standalone names + email addresses) |

## Testing Objectives

### AC3: Mapping Table Consistency

After batch processing, verify:

1. **Marie Dubois appears in 3 documents** → Should have exactly **1 database entry**
2. **Pierre Lefebvre appears in 2 documents** → Should have exactly **1 database entry**
3. **All other entities** → Each should have exactly **1 database entry** (no duplicates)

### Database Query for Verification

```python
# Expected: 1 entry for "Marie Dubois"
SELECT * FROM entities WHERE full_name_encrypted = encrypt("Marie Dubois");

# Expected: 1 entry for "Pierre Lefebvre"
SELECT * FROM entities WHERE full_name_encrypted = encrypt("Pierre Lefebvre");

# Expected: No duplicate pseudonyms assigned
SELECT pseudonym_full, COUNT(*) as count
FROM entities
GROUP BY pseudonym_full
HAVING count > 1;
```

### AC4: Performance Expectations

- **Total entities:** ~85 unique entities across 10 documents (~150 total occurrences)
- **Sequential time:** ~5-8 minutes (10 docs × 30-50s per doc)
- **Parallel time:** ~2-3 minutes (4 workers, 2-3x speedup)
- **Bottleneck:** SQLite write serialization (new entities), spaCy NLP (CPU-bound)

## Entity Details

### Unique Entities by Document

- **doc_001:** Marie Dubois, Jean Martin, Pierre Lefebvre, Sophie Bernard
- **doc_002:** Luc Fournier, Isabelle Petit, Thomas Rousseau
- **doc_003:** Marie Dubois (overlap), Claire Fontaine, Antoine Girard
- **doc_004:** Nicolas Blanchard, Véronique Mercier, Émilie Durand
- **doc_005:** (none)
- **doc_006:** Philippe Moreau, Céline Garnier
- **doc_007:** Marie Dubois (overlap), François Lambert, Sarah Morel, Alexandre Roux
- **doc_008:** Olivier Dumas, Nathalie Chevalier
- **doc_009:** Marc Bertrand, Julie Renard, Pierre Lefebvre (overlap)
- **doc_010:** Sylvie Lemoine, Bernard Fabre

### Total Unique Entities: ~27

(Accounting for overlaps: Marie Dubois, Pierre Lefebvre)

## Test Execution

```bash
# Run spike
poetry run python scripts/batch_processing_spike.py

# Check database consistency (after running spike)
sqlite3 tests/fixtures/batch_spike/spike_test.db "SELECT COUNT(*) FROM entities;"
# Expected: ~27 unique entities

sqlite3 tests/fixtures/batch_spike/spike_test.db "SELECT COUNT(*) FROM operations;"
# Expected: 20 operations (10 sequential + 10 parallel)
```

## Notes

- Documents contain realistic French business content (reports, meeting notes, proposals)
- Entity names use common French surnames (Dubois, Martin, Lefebvre, Bernard, etc.)
- Title variations test preprocessing (Dr., Mme., M.)
- Standalone names test compositional logic (Dubois, Moreau, etc.)
- Email addresses in doc_010 test exclusion zones (should NOT be pseudonymized)
