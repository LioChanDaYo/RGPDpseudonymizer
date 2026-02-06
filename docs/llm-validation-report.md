# LLM Utility Preservation Validation Report

**Story 4.1 - NFR10 Validation**
**Date:** 2026-02-06
**Status:** PASS

---

## Executive Summary

This report validates NFR10 (LLM Utility Preservation) for the GDPR Pseudonymizer tool. Testing confirms that pseudonymized documents maintain sufficient utility for LLM analysis, meeting the 80% threshold required for launch.

**Key Results:**
- **Overall Utility Score:** 4.27/5.0 (85.4%)
- **Pass Threshold:** 4.0/5.0 (80%)
- **Result:** PASS

---

## 1. Methodology

### 1.1 Test Design

The validation follows an A/B comparison methodology:
1. Select representative documents from the test corpus
2. Process documents through the GDPR Pseudonymizer (neutral theme)
3. Run identical LLM prompts on both original and pseudonymized versions
4. Use LLM-as-judge to compare response quality
5. Calculate aggregate statistics and determine pass/fail

### 1.2 LLM Configuration

| Parameter | Value |
|-----------|-------|
| Provider | Anthropic |
| Model | claude-sonnet-4-20250514 |
| Max Tokens | 1024 (responses), 512 (evaluation) |
| Temperature | Default |
| Rate Limiting | 1.5s between calls |

### 1.3 Evaluation Framework

Responses were evaluated on four dimensions using a 1-5 scale:

| Dimension | Description |
|-----------|-------------|
| **Thematic Accuracy** | Does the response capture the same main themes? |
| **Relationship Coherence** | Are entity relationships correctly preserved? |
| **Factual Preservation** | Are facts/details accurately extracted? |
| **Overall Utility** | Would a researcher find this equally useful? |

**Scoring Scale:**
- 5 = Excellent - No degradation, identical or equivalent quality
- 4 = Good - Minor differences, still highly useful
- 3 = Acceptable - Some information loss, but core meaning preserved
- 2 = Poor - Significant degradation, limited utility
- 1 = Unacceptable - Major errors or missing information

---

## 2. Test Documents

### 2.1 Selection Criteria

Documents were selected to represent:
- Variety of entity types (PERSON, LOCATION, ORG)
- Different document lengths and complexity
- Mix of interview transcripts and business documents
- Real-world use cases for LLM analysis

### 2.2 Document Set (n=10)

**Interview Transcripts (5):**

| Document | Description | Entity Density |
|----------|-------------|----------------|
| interview_01 | TechCorp innovation director interview | High (PERSON, ORG, LOC) |
| interview_03 | Public sector digital transformation | High (PERSON, ORG, LOC) |
| interview_05 | Legal/commercial case discussion | Medium (PERSON, ORG) |
| interview_07 | Energy transition in industry | High (PERSON, ORG, LOC) |
| interview_10 | AgriTech innovation | High (PERSON, ORG, LOC) |

**Business Documents (5):**

| Document | Description | Entity Density |
|----------|-------------|----------------|
| meeting_minutes | Board meeting minutes | Very High |
| email_chain | Project Phoenix coordination | Very High |
| incident_report | Security incident report | Very High |
| hr_announcement | HR nominations and changes | Very High |
| contract_memo | Contract notification | Medium |

---

## 3. Standardized Prompts

Three prompts were executed on each document version:

### Prompt 1: Theme Summary
```
Summarize the main themes in this document. Provide a concise overview
of the key topics discussed.
```

### Prompt 2: Relationship Identification
```
Identify key relationships between individuals mentioned in this document.
Describe who interacts with whom and in what context.
```

### Prompt 3: Action Items
```
Extract action items and decisions made in this document. List specific
tasks, deadlines, or resolutions if mentioned.
```

**Total API Calls:** 60 (10 docs × 2 versions × 3 prompts) + 30 evaluations = 90

---

## 4. Results

### 4.1 Overall Statistics

| Metric | Value |
|--------|-------|
| Overall Utility Mean | **4.27/5.0** |
| Overall Utility Median | 5.0 |
| Standard Deviation | 0.93 |
| Min Score | 2 |
| Max Score | 5 |
| Pass Threshold | 4.0 |
| **Result** | **PASS** |

### 4.2 By Dimension

| Dimension | Mean | Median | Std Dev |
|-----------|------|--------|---------|
| Thematic Accuracy | 4.90 | 5.0 | 0.30 |
| Relationship Coherence | 4.13 | 4.0 | 0.88 |
| Factual Preservation | 4.00 | 4.0 | 1.00 |
| Overall Utility | 4.27 | 5.0 | 0.93 |

### 4.3 By Document Type

| Type | Mean Utility | Median | Notes |
|------|--------------|--------|-------|
| Interview | 4.47 | 5 | Higher consistency |
| Business | 4.07 | 4 | More complex entity networks |

### 4.4 By Prompt Type

| Prompt | Mean Utility | Notes |
|--------|--------------|-------|
| Themes | 3.90 | Slightly impacted by org-code placeholders |
| Relationships | 4.50 | Relationships well preserved |
| Actions | 4.40 | Action items reliably extracted |

---

## 5. Edge Cases Analysis

### 5.1 Low-Scoring Evaluations (Utility < 4)

Six evaluations scored below the 4.0 threshold:

| Document | Prompt | Score | Root Cause |
|----------|--------|-------|------------|
| interview_10 | themes | 2/5 | Org-XXX codes questioned document integrity |
| contract_memo | relationships | 2/5 | Inconsistent name mapping across entities |
| meeting_minutes | relationships | 3/5 | Lost specific company/partner identifications |
| email_chain | themes | 3/5 | Incorrect entity names introduced |
| hr_announcement | actions | 3/5 | Missing personnel moves, incomplete info |
| contract_memo | themes | 3/5 | Entity mapping confusion |

### 5.2 Root Cause Analysis

**Issue 1: Organization Code Placeholders (Org-XXX)**
- Impact: Medium
- Cause: When organizations are pseudonymized with generic codes (Org-058, Org-092), LLMs may question document authenticity or miss organizational context
- Frequency: Occasional (2/30 evaluations significantly affected)

**Issue 2: Inconsistent Name Mapping**
- Impact: Low-Medium
- Cause: In complex documents with many entities, name consistency can break across sections
- Frequency: Rare (1/30 evaluations significantly affected)

**Issue 3: Context Loss for External Organizations**
- Impact: Low
- Cause: Well-known organizations (Google, Microsoft, INRIA) become anonymous codes, reducing context
- Frequency: Occasional but impact minimal

### 5.3 Recommendations for Users

1. **Validation Mode for Critical Documents**: Use `--validate` mode for documents where accuracy is critical
2. **Named Themes for Organizations**: Consider using themed pseudonym libraries that provide more natural-sounding organization names
3. **Document Complexity**: Very complex documents with 50+ entities may require manual review
4. **Context Preservation**: For research where organizational context matters, consider using `--preserve-org` option (if available) or manual review

---

## 6. Example Comparisons

### 6.1 High-Quality Preservation (interview_05)

**Original Response (Themes):**
> The document covers a commercial litigation case, mediation processes, expert witness testimony, and legal representation across multiple jurisdictions.

**Pseudonymized Response (Themes):**
> The document covers a commercial litigation case, mediation processes, expert witness testimony, and legal representation across multiple jurisdictions.

**Score:** 5/5 - Identical thematic extraction

### 6.2 Moderate Impact (hr_announcement - actions)

**Original Response (Actions):**
> - M. Kevin Zhang promoted to VP Engineering, reporting to Dr. Marie Dubois
> - Mme Nadia Amrani moving from DevOps to Product Management

**Pseudonymized Response (Actions):**
> - M. Jasmine Torres promoted to VP Engineering, reporting to Dr. Lucie Guillory
> - Personnel moves in DevOps and Product Management departments

**Score:** 3/5 - Core actions preserved but some specific details less clear

---

## 7. NFR10 Compliance Determination

### 7.1 Pass/Fail Criteria

| Criterion | Threshold | Actual | Status |
|-----------|-----------|--------|--------|
| Overall Utility Mean | ≥ 4.0/5.0 | 4.27/5.0 | PASS |
| Valid Evaluations | 30/30 | 30/30 | PASS |
| Critical Failures (score = 1) | 0 | 0 | PASS |

### 7.2 Decision

**NFR10 STATUS: PASS**

The GDPR Pseudonymizer meets the LLM Utility Preservation requirement with an overall score of 4.27/5.0 (85.4%), exceeding the 80% threshold.

---

## 8. Go/No-Go Recommendation

### 8.1 Recommendation: GO

Based on the validation results:

1. **Overall utility is preserved** - 85.4% utility retention exceeds 80% target
2. **Core use cases work well** - Relationship and action extraction score 4.4-4.5/5.0
3. **Edge cases are documented** - Known limitations identified with mitigation strategies
4. **No critical failures** - No evaluation scored 1/5

### 8.2 Caveats for Launch

1. **Document Complexity**: Users should be advised that very complex documents (50+ entities) may have slightly reduced utility
2. **Organization Context**: When organizational context is critical, validation mode is recommended
3. **Thematic Analysis**: Theme extraction shows slightly lower scores (3.9) - acceptable but users should be aware

### 8.3 Post-Launch Monitoring

Recommend collecting user feedback on:
- Document types that work best/worst
- Specific use cases where utility is insufficient
- Requests for enhanced pseudonymization options

---

## Appendix A: Test Artifacts

| Artifact | Location |
|----------|----------|
| LLM Responses | `docs/qa/llm-test-responses.json` |
| Evaluation Scores | `docs/qa/llm-evaluation-scores.json` |
| Test Script | `scripts/llm_utility_test.py` |
| Original Documents | `tests/test_corpus/llm_test/originals/` |
| Pseudonymized Documents | `tests/test_corpus/llm_test/pseudonymized/` |

---

## Appendix B: Full Evaluation Results

| Document | Prompt | Thematic | Coherence | Factual | Utility |
|----------|--------|----------|-----------|---------|---------|
| interview_01 | themes | 5 | 4 | 4 | 4 |
| interview_01 | relationships | 5 | 5 | 5 | 5 |
| interview_01 | actions | 5 | 4 | 4 | 5 |
| interview_03 | themes | 5 | 4 | 3 | 4 |
| interview_03 | relationships | 5 | 5 | 5 | 5 |
| interview_03 | actions | 5 | 3 | 3 | 4 |
| interview_05 | themes | 5 | 5 | 5 | 5 |
| interview_05 | relationships | 5 | 5 | 5 | 5 |
| interview_05 | actions | 5 | 4 | 4 | 4 |
| interview_07 | themes | 5 | 4 | 4 | 4 |
| interview_07 | relationships | 5 | 5 | 5 | 5 |
| interview_07 | actions | 5 | 4 | 4 | 5 |
| interview_10 | themes | 5 | 4 | 3 | 2 |
| interview_10 | relationships | 5 | 5 | 5 | 5 |
| interview_10 | actions | 5 | 4 | 4 | 5 |
| meeting_minutes | themes | 5 | 4 | 4 | 5 |
| meeting_minutes | relationships | 4 | 3 | 2 | 3 |
| meeting_minutes | actions | 5 | 4 | 5 | 4 |
| email_chain | themes | 5 | 2 | 3 | 3 |
| email_chain | relationships | 5 | 5 | 5 | 5 |
| email_chain | actions | 5 | 5 | 5 | 5 |
| incident_report | themes | 5 | 5 | 5 | 5 |
| incident_report | relationships | 5 | 5 | 5 | 5 |
| incident_report | actions | 5 | 5 | 4 | 5 |
| hr_announcement | themes | 5 | 4 | 4 | 4 |
| hr_announcement | relationships | 5 | 5 | 5 | 5 |
| hr_announcement | actions | 4 | 3 | 2 | 3 |
| contract_memo | themes | 5 | 3 | 3 | 3 |
| contract_memo | relationships | 4 | 2 | 2 | 2 |
| contract_memo | actions | 5 | 4 | 3 | 4 |

---

*Report generated by automated LLM utility testing (Story 4.1)*
*Model: Claude claude-sonnet-4-20250514 via Anthropic API*
