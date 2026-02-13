# Test Corpus Annotations

## Overview

This directory contains ground truth annotations for the GDPR Pseudonymizer test corpus.

## Statistics

- **Total Documents**: 25 (15 interview transcripts + 10 business documents)
- **Total Entities**: 1,737
- **Entity Distribution**:
  - PERSON: 1,482 entities
  - LOCATION: 124 entities
  - ORG: 131 entities

## Acceptance Criteria Verification

| Entity Type | Required | Actual | Status |
|-------------|----------|--------|--------|
| PERSON      | 100      | 1,482  | ✓ PASS |
| LOCATION    | 50       | 124    | ✓ PASS |
| ORG         | 30       | 131    | ✓ PASS |

## Annotation Schema

Each annotation file follows this JSON schema:

```json
{
  "document_name": "document.txt",
  "entities": [
    {
      "entity_text": "Marie Dubois",
      "entity_type": "PERSON",
      "start_pos": 15,
      "end_pos": 27
    }
  ]
}
```

### Fields

- `document_name`: Name of the source document
- `entity_text`: The actual text of the entity
- `entity_type`: One of PERSON, LOCATION, or ORG
- `start_pos`: Character position where entity starts (0-indexed)
- `end_pos`: Character position where entity ends (exclusive)

## Annotation Policy: Titles

**Policy (Story 5.3):** French honorific titles are **excluded** from PERSON entity text.

Annotate only the person's name, not the title prefix:
- **Correct:** `"entity_text": "Marie Dubois"` (the source text may read "Dr. Marie Dubois")
- **Incorrect:** `"entity_text": "Dr. Marie Dubois"`

**Excluded title prefixes:** M., Mme, Dr., Me, Pr., Maître, Monsieur, Madame, Professeur, Mmes

**Rationale:** The hybrid detector (`strip_french_titles()` in `hybrid_detector.py`) strips
titles before entity matching. If annotations include titles but detection strips them,
entity matching always fails for titled entities, inflating false negative counts. Excluding
titles from annotations aligns ground truth with how the detector actually works.

## Edge Cases Covered

The corpus includes comprehensive edge cases:

1. **Titles**: Titles appear in source text but are excluded from entity_text per policy above
2. **Name Order Variations**: Dubois, Jean-Marc (Last, First format)
3. **Abbreviations**: J-M. Martin
4. **Nested Entities**: Organizations within locations, titles with names
5. **Hyphenated Names**: Jean-Pierre, Marie-Anne
6. **Multi-word Organizations**: TechCorp France SAS, McKinsey France
7. **French Diacritics**: François, Élisabeth, Stéphane

## Files

- `interview_01.json` through `interview_15.json`: Annotations for interview transcripts
- `audit_summary.json`, `board_minutes.json`, etc.: Annotations for business documents

## Generation

Annotations were generated using:
- Automated pattern matching (`auto_annotate_corpus.py`)
- Manual review and validation
- Entity counting verification (`count_entities.py`)

## Usage

These annotations serve as ground truth for:
1. NLP library benchmarking (Story 1.2)
2. Precision/recall/F1 score calculation
3. Quality validation throughout development
