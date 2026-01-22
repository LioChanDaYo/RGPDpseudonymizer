# Hybrid Detection Strategy

## Overview

The hybrid detection strategy combines spaCy NLP-based entity recognition with regex pattern matching to improve entity detection accuracy for French documents.

**Goal:** Improve detection from 29.5% F1 (spaCy baseline) to 40-50% F1 by detecting entities that spaCy misses.

---

## Architecture

### Detection Pipeline

```
Input Text
    ↓
┌─────────────────────────┐
│ 1. spaCy NER Detection  │ ← Baseline NLP detection
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│ 2. Regex Pattern Match  │ ← Pattern-based detection
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│ 3. Merge & Deduplicate  │ ← Combine results
└─────────────────────────┘
    ↓
Combined Entity List
```

### Components

1. **SpaCyDetector**: Baseline NLP-based entity detection
   - Uses `fr_core_news_lg` model (spaCy 3.8.0)
   - Detects PERSON, LOCATION, ORG entities
   - Provides confidence scores when available

2. **RegexMatcher**: Pattern-based entity detection
   - Loads patterns from `config/detection_patterns.yaml`
   - Uses French name dictionary (`data/french_names.json`)
   - Assigns confidence scores based on pattern type

3. **HybridDetector**: Orchestrates both approaches
   - Implements `EntityDetector` interface
   - Merges results with deduplication logic
   - Returns combined entity list

---

## Regex Pattern Categories

### 1. Title Patterns (High Confidence: 0.85)

**Purpose:** Detect titles followed by names
**Confidence:** 0.85 (high - titles strongly indicate person names)

**Examples:**
- `M. Dupont` → PERSON
- `Mme Laurent` → PERSON
- `Dr. Marie Dubois` → PERSON
- `Pr. François Martin` → PERSON

**Pattern:**
```regex
\b(M\.|Mme|Mlle|Dr\.|Pr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)
```

---

### 2. Compound Name Patterns (High Confidence: 0.80)

**Purpose:** Detect hyphenated French first names
**Confidence:** 0.80 (high - very common in French naming conventions)

**Examples:**
- `Jean-Pierre` → PERSON
- `Marie-Claire` → PERSON
- `Anne-Sophie` → PERSON

**Pattern:**
```regex
\b([A-Z][a-z]+-[A-Z][a-z]+)\b
```

---

### 3. Location Indicator Patterns (Medium Confidence: 0.65)

**Purpose:** Detect location prepositions + place names
**Confidence:** 0.65 (medium - strong indicator but some ambiguity)

**Examples:**
- `à Paris` → LOCATION
- `en France` → LOCATION
- `près de Lyon` → LOCATION
- `ville de Marseille` → LOCATION

**Pattern:**
```regex
\b(à|en|dans|près de|ville de)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)
```

---

### 4. Organization Patterns (Medium Confidence: 0.70)

**Purpose:** Detect French organization legal suffixes and prefixes
**Confidence:** 0.70 (medium - strong indicator for French companies)

**Examples:**
- `TechCorp SA` → ORG
- `Solutions SARL` → ORG
- `Société TechCorp` → ORG
- `Cabinet Martin` → ORG

**Patterns:**
```regex
# Suffix pattern
\b([A-Z][A-Za-z\s]+?)\s+(SA|SARL|SAS|EURL|SNC|SCM|SCI)\b

# Prefix pattern
\b(Société|Entreprise|Cabinet|Groupe|Compagnie)\s+([A-Z][A-Za-z\s]+)
```

---

### 5. Full Name Patterns (Medium Confidence: 0.65)

**Purpose:** Detect firstname + lastname combinations using name dictionary
**Confidence:** 0.65 (medium - dictionary match provides validation)

**Examples:**
- `Marie Dubois` → PERSON (if both in dictionary)
- `Jean Martin` → PERSON (if both in dictionary)
- `François Bernard` → PERSON (if both in dictionary)

**Implementation:**
```python
# Pattern: Capitalized word + Capitalized word
# Validated against data/french_names.json
if first_name in FRENCH_FIRST_NAMES and last_name in FRENCH_LAST_NAMES:
    match as PERSON entity
```

---

## French Name Dictionary

**Source:** INSEE (Institut national de la statistique et des études économiques)
**Location:** `data/french_names.json`

**Contents:**
- **First names:** 451 most common French first names
- **Last names:** 316 most common French last names

**Format:**
```json
{
  "first_names": ["Marie", "Jean", "Pierre", ...],
  "last_names": ["Martin", "Bernard", "Dubois", ...]
}
```

**Usage:**
- Loaded by `NameDictionary` class
- Used by `RegexMatcher` for full name pattern validation
- Case-insensitive matching with capitalization normalization

---

## Deduplication Logic

When both spaCy and regex detect overlapping entities, the hybrid detector applies these rules:

### Exact Overlap (Same Span)
**Rule:** Keep spaCy entity (prefer NLP confidence)
**Example:**
```
spaCy:  "Paris" (10-15)
Regex:  "Paris" (10-15)
Result: Keep spaCy entity only
```

### No Overlap
**Rule:** Keep both entities
**Example:**
```
spaCy:  "Paris" (10-15)
Regex:  "M. Dupont" (20-29)
Result: Keep both entities
```

### Partial Overlap
**Rule:** Keep both, flag regex entity as ambiguous
**Example:**
```
spaCy:  "Dubois" (10-16)
Regex:  "M. Dubois" (7-16)
Result: Keep both, mark "M. Dubois" as ambiguous
```

**Rationale:** User validation will resolve ambiguous entities.

---

## Configuration

### Pattern Configuration File

**Location:** `config/detection_patterns.yaml`

**Structure:**
```yaml
patterns:
  titles:
    enabled: true           # Enable/disable pattern category
    confidence: 0.85       # Confidence score for matches
    entity_type: PERSON    # Entity type to assign
    patterns:
      - pattern: '\b(M\.|Mme|...'
        description: "..."
        examples: [...]
```

**Customization:**
- Enable/disable pattern categories by setting `enabled: true/false`
- Adjust confidence scores for pattern categories
- Add custom patterns for domain-specific entities

---

## Performance Characteristics

### Expected Improvements

| Metric | spaCy Baseline | Hybrid Target | Improvement |
|--------|----------------|---------------|-------------|
| **Recall (PERSON)** | 31.28% | 45-55% | +14-24% |
| **Recall (LOCATION)** | 58.54% | 65-75% | +7-17% |
| **Recall (ORG)** | 23.81% | 30-40% | +6-16% |
| **Overall F1** | 29.54% | 40-50% | +10-20% |

### Processing Time

- **Target:** <30s per document (2-5K words)
- **Overhead:** Regex matching adds ~1-2s per document
- **Acceptable:** Performance remains within target

### Validation Burden

- **Improved recall:** Fewer missed entities to add manually
- **Expected reduction:** ~40-50% less time adding entities
- **Trade-off:** Some regex false positives (caught during validation)

---

## Usage

### In Process Command

The `process` command automatically uses hybrid detection:

```bash
gdpr-pseudo process interview.txt
```

**Pipeline:**
1. Load hybrid detector (spaCy + regex)
2. Detect entities using both methods
3. Present merged entities for validation
4. Apply pseudonymization

### Programmatic Usage

```python
from gdpr_pseudonymizer.nlp.hybrid_detector import HybridDetector

# Initialize detector
detector = HybridDetector()
detector.load_model("fr_core_news_lg")

# Detect entities
text = "M. Dupont travaille à Paris pour TechCorp SA."
entities = detector.detect_entities(text)

# Entities have source attribution
for entity in entities:
    print(f"{entity.text} ({entity.entity_type}) - source: {entity.source}")

# Output:
# M. Dupont (PERSON) - source: regex
# Paris (LOCATION) - source: spacy
# TechCorp SA (ORG) - source: regex
```

---

## Limitations

### 1. Regex Pattern Coverage

- Patterns cover common French structures
- Domain-specific entities may be missed
- Custom patterns may be needed for specialized domains

### 2. Name Dictionary Coverage

- Limited to top 500 first/last names
- Rare or regional names may not be in dictionary
- Immigrant names may require expansion

### 3. False Positives

- Regex patterns may over-match (e.g., "Paris" could be a name)
- Validation workflow catches and corrects false positives
- Trade-off: Better recall at cost of some false positives

### 4. Language-Specific

- Patterns designed for French documents
- Would require adaptation for other languages
- English/multilingual documents not supported

---

## Testing

### Unit Tests

- **RegexMatcher:** `tests/unit/test_regex_matcher.py`
- **HybridDetector:** `tests/unit/test_hybrid_detector.py`
- **NameDictionary:** `tests/unit/test_name_dictionary.py`

### Integration Tests

- **Full pipeline:** `tests/integration/test_hybrid_detection_integration.py`
- **Process command:** `tests/integration/test_process_command.py`

### Benchmarking

- **Script:** `scripts/benchmark_hybrid.py`
- **Output:** `docs/hybrid-benchmark-report.md`
- **Metrics:** Precision, recall, F1, processing time

---

## Future Enhancements

### 1. Pattern Expansion

- Add more organization patterns (associations, foundations)
- Expand location patterns (regions, departments)
- Add date/address patterns

### 2. Dictionary Expansion

- Expand to top 1000 names
- Add regional name variations
- Include common immigrant names

### 3. Machine Learning Hybrid

- Train custom NER model on French legal documents
- Use regex patterns as features for ML model
- Active learning from validation corrections

### 4. Adaptive Patterns

- Learn patterns from user validation corrections
- Adjust confidence scores based on validation feedback
- Domain-specific pattern tuning

---

## References

- **Story 1.8:** [docs/stories/1.8.hybrid-detection-strategy.story.md](stories/1.8.hybrid-detection-strategy.story.md)
- **NLP Benchmark:** [docs/nlp-benchmark-report.md](nlp-benchmark-report.md)
- **Architecture:** [docs/architecture/8-nlp-engine.md](architecture/8-nlp-engine.md)
- **Tech Stack:** [docs/architecture/3-tech-stack.md](architecture/3-tech-stack.md)
