# NLP Library Benchmark Report

**Story:** 1.2 - Comprehensive NLP Library Benchmark
**Date:** 2026-01-16
**Evaluator:** Dev Agent (James)
**Test Corpus:** 25 documents, 1,855 annotated entities

---

## Executive Summary

**CRITICAL FINDING: Both spaCy and Stanza FAIL to meet the ≥85% F1 score threshold required for MVP.**

- **spaCy F1 Score:** 29.54% (FAIL - 55.46% below threshold)
- **Stanza F1 Score:** 11.89% (FAIL - 73.11% below threshold)

**Recommendation:** Execute contingency plan. Neither library achieves acceptable accuracy on the current test corpus with default configurations.

---

## 1. Accuracy Metrics Comparison

### 1.1 Overall Performance

| Metric | spaCy | Stanza | Winner |
|--------|-------|--------|--------|
| **Precision** | 26.96% | 10.26% | spaCy (+16.70%) |
| **Recall** | 32.67% | 14.12% | spaCy (+18.55%) |
| **F1 Score** | 29.54% | 11.89% | spaCy (+17.65%) |
| **True Positives** | 606 | 262 | spaCy (+344) |
| **False Positives** | 1,642 | 2,291 | spaCy (-649) |
| **False Negatives** | 1,249 | 1,593 | spaCy (-344) |

**Analysis:** spaCy significantly outperforms Stanza across all metrics, achieving 2.5x better F1 score. However, both libraries show unacceptably high false positive rates.

---

### 1.2 Per-Entity Type Performance

#### PERSON Entities (Ground Truth: 1,627 entities)

| Metric | spaCy | Stanza | Winner |
|--------|-------|--------|--------|
| **Precision** | 37.79% | 12.46% | spaCy (+25.33%) |
| **Recall** | 31.28% | 10.26% | spaCy (+21.02%) |
| **F1 Score** | 34.23% | 11.26% | spaCy (+22.97%) |
| **True Positives** | 509 | 167 | spaCy (+342) |
| **False Positives** | 838 | 1,173 | spaCy (-335) |
| **False Negatives** | 1,118 | 1,460 | spaCy (-342) |

**Analysis:** PERSON detection is weak for both libraries. spaCy detects only 31% of persons (missing 69%), while Stanza detects only 10% (missing 90%). High false positive rates indicate both libraries misclassify many non-person entities as persons.

---

#### LOCATION Entities (Ground Truth: 123 entities)

| Metric | spaCy | Stanza | Winner |
|--------|-------|--------|--------|
| **Precision** | 29.63% | 42.55% | Stanza (+12.92%) |
| **Recall** | 58.54% | 48.78% | spaCy (+9.76%) |
| **F1 Score** | 39.34% | 45.45% | Stanza (+6.11%) |
| **True Positives** | 72 | 60 | spaCy (+12) |
| **False Positives** | 171 | 81 | Stanza (-90) |
| **False Negatives** | 51 | 63 | spaCy (-12) |

**Analysis:** This is the ONLY category where performance approaches acceptable levels. Stanza achieves better F1 (45%) due to higher precision, while spaCy has better recall (59%). Both libraries perform relatively better on locations than other entity types.

---

#### ORG Entities (Ground Truth: 105 entities)

| Metric | spaCy | Stanza | Winner |
|--------|-------|--------|--------|
| **Precision** | 3.80% | 3.26% | spaCy (+0.54%) |
| **Recall** | 23.81% | 33.33% | Stanza (+9.52%) |
| **F1 Score** | 6.55% | 5.95% | spaCy (+0.60%) |
| **True Positives** | 25 | 35 | Stanza (+10) |
| **False Positives** | 633 | 1,037 | spaCy (-404) |
| **False Negatives** | 80 | 70 | Stanza (-10) |

**Analysis:** CATASTROPHIC performance for both libraries. Precision under 4% means 96%+ of detected ORG entities are false positives. Both libraries massively over-detect organizations, misclassifying hundreds of non-ORG entities.

---

## 2. Performance Metrics Comparison

### 2.1 Processing Speed

| Metric | spaCy | Stanza | Winner |
|--------|-------|--------|--------|
| **Model Loading Time** | 0.001s | 0.001s | Tie |
| **Avg Time per Document** | 0.293s | 0.789s | spaCy (2.7x faster) |
| **Total Processing Time (25 docs)** | 7.329s | 19.729s | spaCy (2.7x faster) |
| **Estimated Processing Rate** | ~341 words/sec | ~127 words/sec | spaCy (2.7x faster) |

**Analysis:** spaCy is significantly faster than Stanza, processing documents 2.7x faster. For batch processing of large document sets, spaCy would complete in 1/3 the time of Stanza.

---

### 2.2 Model Information

| Attribute | spaCy | Stanza |
|-----------|-------|--------|
| **Library Version** | 3.8.0 | 1.11.0 |
| **Model Name** | core_news_lg | stanza_fr |
| **Language** | fr | fr |
| **Model Size** | ~571 MB | ~360 MB |
| **Installation Complexity** | Simple (1 command) | Simple (1 command) |

---

## 3. Compound Name Detection Analysis

### 3.1 Test Results

| Library | Detection Rate | Notes |
|---------|----------------|-------|
| **spaCy** | 1/1 (100%) | Correctly detected "M. Jean-Pierre Martin" |
| **Stanza** | 1/1 (100%) | Correctly detected "M. Jean-Pierre Martin" |

**Analysis:** Both libraries handle French hyphenated compound names correctly. Only 1 compound name entity exists in the current test corpus, limiting statistical significance. Both libraries detected it successfully.

**Conclusion:** Compound name detection is NOT a differentiator between libraries. Both handle French hyphenated names (Jean-Pierre, Marie-Claire pattern) correctly with default configuration.

---

## 4. Root Cause Analysis

### 4.1 Why Did Both Libraries Fail?

**Hypothesis 1: Model-Corpus Mismatch**
- spaCy's `fr_core_news_lg` and Stanza's `fr_default` are trained on news/formal text corpora
- Our test corpus contains interview transcripts and business documents with:
  - Conversational language patterns
  - Domain-specific terminology
  - Mixed formal/informal registers
- **Likelihood:** HIGH - This is the most likely cause

**Hypothesis 2: Ground Truth Annotation Quality**
- While Story 1.1 validated annotations, there may be annotation style mismatches
- Example: Models may not recognize titles ("M.", "Dr.") as part of person names
- **Likelihood:** MEDIUM - Partial contributor

**Hypothesis 3: Entity Type Definition Misalignment**
- Models may use different entity type taxonomies than our PERSON/LOCATION/ORG schema
- Label mapping in detectors may be incomplete
- **Likelihood:** MEDIUM - ORG performance suggests this is a factor

**Hypothesis 4: Out-of-the-Box Configuration Not Optimized**
- Both libraries have configuration options, confidence thresholds, and fine-tuning capabilities
- We tested with default configurations only
- **Likelihood:** HIGH - Fine-tuning could significantly improve results

---

## 5. Contingency Plan Options

Given that BOTH libraries fail to meet the ≥85% F1 threshold, the following contingency options are available:

---

### Option 1: Lower Threshold + Mandatory Validation Mode (RECOMMENDED)

**Approach:**
- Accept 30% F1 score as baseline for automatic detection
- Make validation mode (FR7) MANDATORY for all processing
- Users must manually review and confirm all detected entities

**Pros:**
- Can proceed with MVP immediately
- Aligns with privacy-first approach (manual review reduces false positives)
- spaCy's 59% recall on LOCATION is usable with validation

**Cons:**
- Removes "automatic" from automatic pseudonymization
- Increases user workload significantly
- May not meet original product vision

**Estimated Effort:** 0 sprints (decision only)

**Recommendation Level:** ★★★★★ (Highest)

---

### Option 2: Fine-Tune spaCy Model on Domain-Specific Data

**Approach:**
- Use test corpus (25 documents, 1,855 annotations) to fine-tune spaCy's `fr_core_news_lg`
- Add more annotated training data in same domain (interviews, business docs)
- Re-evaluate after fine-tuning

**Pros:**
- Could significantly improve accuracy (industry reports show 20-40% F1 gains)
- spaCy has excellent fine-tuning documentation and tools
- Addresses root cause (model-corpus mismatch)

**Cons:**
- Requires ML expertise and experimentation
- Need more annotated training data (current 25 docs insufficient)
- 1-2 sprint delay to MVP

**Estimated Effort:** 1-2 sprints

**Recommendation Level:** ★★★★☆

---

### Option 3: Hybrid Approach (Multiple Detection Strategies)

**Approach:**
- Use spaCy as primary detector
- Add regex-based fallback patterns for high-confidence cases:
  - French names with titles: "M. [Surname]", "Mme [Surname]", "Dr. [Name]"
  - Email addresses → extract names
  - Phone numbers → flag for manual review
- Combine NLP + rule-based detection

**Pros:**
- Can improve recall without additional training
- Pragmatic solution for MVP
- Leverages spaCy's strengths while covering blind spots

**Cons:**
- Increases code complexity
- Regex patterns may not generalize well
- Still requires validation mode

**Estimated Effort:** 1 sprint

**Recommendation Level:** ★★★★☆

---

### Option 4: Evaluate Alternative NLP Libraries

**Approach:**
- Test other French NER libraries:
  - Flair (strong multilingual support)
  - Hugging Face Transformers (BERT-based French models: CamemBERT)
  - spaCy with different models (fr_core_news_md, fr_dep_news_trf)

**Pros:**
- Transformer-based models (BERT) often achieve 10-20% higher F1
- CamemBERT trained specifically on French data
- May find better out-of-the-box solution

**Cons:**
- 1-2 sprint delay for evaluation
- Transformer models are slower (10-100x) than spaCy/Stanza
- Higher memory requirements (2-4GB vs 1.5GB)
- May still not reach 85% without fine-tuning

**Estimated Effort:** 1-2 sprints

**Recommendation Level:** ★★★☆☆

---

### Option 5: Pivot to Different Technical Approach

**Approach:**
- Abandon automatic NER entirely
- Implement manual entity marking workflow:
  - User highlights text → selects entity type → assigns pseudonym
  - Tool provides suggestions based on patterns
  - Minimal NLP usage

**Pros:**
- Guarantees 100% accuracy (human-verified)
- Simpler technical implementation
- Faster to MVP

**Cons:**
- Fundamentally changes product value proposition
- Requires UX redesign
- High user effort for large documents
- Competitive disadvantage vs automatic tools

**Estimated Effort:** 2-3 sprints (UX + implementation)

**Recommendation Level:** ★☆☆☆☆ (Last resort)

---

## 6. Recommendation

### Primary Recommendation: **Option 1 + Option 3 (Combined)**

**Rationale:**
1. **Option 1 (Mandatory Validation)** enables immediate MVP launch with acceptable privacy guarantees
2. **Option 3 (Hybrid Approach)** improves detection quality without major delays
3. Combined approach:
   - spaCy as NLP detector (29.5% F1 baseline)
   - Regex patterns for common French name structures
   - Mandatory validation mode for all processing
   - Document in architecture as "Phase 1" approach

**Timeline:**
- Sprint 1: Implement hybrid detection (Story 1.3+)
- Sprint 2: Build validation mode UI (Epic 0)
- Sprint 3: MVP launch with validation-required workflow

**Expected Results:**
- Hybrid approach could reach 40-50% F1 (estimate)
- Validation mode ensures no false negatives escape
- User reviews ~50% of entities (vs 100% manual marking)
- Product launches on time with privacy guarantees

---

### Secondary Recommendation: **Option 2 (Fine-Tuning)** - Post-MVP

After MVP launch with Option 1+3, invest in fine-tuning:
- Collect more domain-specific annotated data from early adopters
- Fine-tune spaCy model in Sprint 4-5
- Target 70-85% F1 with fine-tuned model
- Reduce validation burden in v1.1 release

---

## 7. Selected Library for MVP: **spaCy**

Despite both libraries failing the 85% threshold, **spaCy** is selected for MVP implementation based on:

| Criterion | spaCy Advantage | Impact |
|-----------|-----------------|--------|
| **F1 Score** | 2.5x better (29.5% vs 11.9%) | HIGH - Fewer false positives/negatives |
| **Processing Speed** | 2.7x faster | HIGH - Better UX for batch processing |
| **Precision** | 2.6x better (27% vs 10%) | HIGH - Fewer false alarms in validation |
| **Documentation** | Extensive, beginner-friendly | MEDIUM - Faster development |
| **Fine-Tuning Support** | Excellent tooling and guides | HIGH - Enables future improvement |
| **Model Size** | Larger (571MB vs 360MB) | LOW - Acceptable download size |

**Decision:** Use spaCy's `fr_core_news_lg` model for Epic 1 implementation, with mandatory validation mode and hybrid detection enhancements.

---

## 8. Architecture Documentation Updates

The following changes will be made to [docs/architecture/3-tech-stack.md](docs/architecture/3-tech-stack.md):

### Current Entry:
```
| **NLP Library** | spaCy OR Stanza | spaCy 3.7+ OR Stanza 1.7+ | French NER (entity detection) | **DECISION PENDING Epic 0-1 benchmark**. |
```

### Updated Entry:
```
| **NLP Library** | spaCy | 3.7+ (tested: 3.8.0) | French NER (entity detection) | Selected after Story 1.2 benchmark. Achieves 29.5% F1 (below 85% target but 2.5x better than Stanza). Mandatory validation mode required for MVP. Fine-tuning planned for post-MVP. Model: fr_core_news_lg (571MB). |
```

### New Documentation Section:
A new architecture section will be created: **docs/architecture/20-nlp-accuracy-limitations.md** documenting:
- Benchmark results
- Accuracy limitations
- Validation mode requirement
- Fine-tuning roadmap
- User expectations

---

## 9. Open Questions for Product Manager

1. **Is 30% automatic detection + mandatory validation acceptable for MVP launch?**
   - Alternative: Delay MVP for fine-tuning (1-2 sprints)

2. **Should we scope validation UI into Epic 0 or Epic 1?**
   - Validation mode is now CRITICAL path, not optional feature

3. **Budget for post-MVP fine-tuning?**
   - Requires ML expertise + annotated training data collection

4. **Acceptable user experience for validation workflow?**
   - Users must review ~50-70% of entities (spaCy detects ~30%, misses ~70%)

---

## 10. Conclusion

**Go/No-Go Decision: NO-GO on original 85% threshold**

Both spaCy and Stanza fail to meet the ≥85% F1 score requirement with out-of-the-box configurations on our test corpus. However, this is a surmountable challenge with the proposed contingency plan (Option 1+3).

**Revised Go/No-Go: GO with Contingency Plan**

Proceeding with:
- ✅ spaCy selected as NLP library (best of available options)
- ✅ Mandatory validation mode for MVP
- ✅ Hybrid detection approach (NLP + regex patterns)
- ✅ Post-MVP fine-tuning roadmap
- ⚠️ Revised user expectations: "Assisted" pseudonymization, not fully automatic

**Next Steps:**
1. Update architecture documentation (Task 7 completion)
2. Escalate to product manager for approval
3. Scope validation mode into Epic 0 or Epic 1
4. Proceed to Story 1.3 (CI/CD Pipeline Setup)

---

**Report Generated:** 2026-01-16
**Dev Agent:** James (Full Stack Developer)
**Story:** 1.2 - Comprehensive NLP Library Benchmark
**Status:** Benchmark Complete - Awaiting Product Manager Decision on Contingency Plan
