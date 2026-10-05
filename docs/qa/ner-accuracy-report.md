# NER Accuracy Report — Story 4.4

**Generated:** 2026-02-08
**Pipeline:** HybridDetector (spaCy fr_core_news_lg + regex patterns)
**Corpus:** 25-document annotated test corpus (1,855 ground-truth entities)
**Matching:** Case-insensitive text + entity type

---

## Executive Summary

| NFR | Metric | Target | Actual | Status |
|-----|--------|--------|--------|--------|
| NFR8 | False Negative Rate | <10% | **63.83%** | FAIL (aspirational) |
| NFR9 | False Positive Rate | <15% | **74.75%** | FAIL (aspirational) |

**Verdict:** NFR8/NFR9 targets are **not met** with current NLP accuracy. This was anticipated from Epic 1 benchmarking (F1=29.54%). **Mandatory validation mode** is the mitigation strategy — users review and correct NER results before pseudonymization.

---

## Overall Metrics

| Metric | Value |
|--------|-------|
| **Precision** | 0.2525 (25.25%) |
| **Recall** | 0.3617 (36.17%) |
| **F1 Score** | 0.2974 (29.74%) |
| **True Positives** | 671 |
| **False Positives** | 1,986 |
| **False Negatives** | 1,184 |
| **FN Rate (NFR8)** | 63.83% |
| **FP Rate (NFR9)** | 74.75% |

---

## Per-Entity-Type Metrics

| Entity Type | Precision | Recall | F1 | TP | FP | FN |
|------------|-----------|--------|-----|-----|------|------|
| **PERSON** | 0.3319 | 0.3423 | 0.3371 | 557 | 1,121 | 1,070 |
| **LOCATION** | 0.2617 | 0.6341 | 0.3705 | 78 | 220 | 45 |
| **ORG** | 0.0529 | 0.3429 | 0.0916 | 36 | 645 | 69 |

**Key observations:**
- LOCATION has the highest recall (63.41%) but low precision due to many false positives
- PERSON has balanced precision/recall around 34%
- ORG has very low precision (5.29%) — many non-ORG entities are incorrectly classified as ORG

---

## Per-Detection-Source Metrics

| Source | TP | FP | Precision |
|--------|-----|------|-----------|
| **spaCy** | 630 | 1,598 | 0.2828 |
| **regex** | 41 | 388 | 0.0956 |

- spaCy contributes 94% of true positives
- Regex patterns have low precision (9.56%) but contribute additional recall for entities spaCy misses

---

## Edge Case Analysis

| Category | Recall | TP | FN | Total |
|----------|--------|-----|------|-------|
| **Title with name** (Dr., M., Mme) | 0.1670 | 77 | 384 | 461 |
| **French diacritics** (é, è, ç) | 0.2214 | 60 | 211 | 271 |
| **Multi-word ORG** | 0.3077 | 28 | 63 | 91 |
| **Last, First order** | 0.0000 | 0 | 90 | 90 |
| **Compound/hyphenated** | 0.5000 | 1 | 1 | 2 |
| **Abbreviation** (J-M.) | 0.3333 | 1 | 2 | 3 |

**Lowest accuracy categories:**
1. **Last, First order** (0% recall) — spaCy does not handle reversed name formats (e.g., "Dubois, Jean-Marc")
2. **Title with name** (16.7% recall) — titles like "Mme", "M." confuse the detector. The annotation ground truth includes the title as part of the entity text, but detection often captures only the name portion
3. **French diacritics** (22.1% recall) — characters like é, è, ç contribute to mismatches

**Recommendations per category:**
- **Last, First order:** Add regex patterns for "LastName, FirstName" format
- **Title with name:** Improve title normalization in matching or in annotations
- **French diacritics:** Ensure NLP model handles accented characters consistently
- **Multi-word ORG:** Expand organization suffix patterns (SA, SAS, SARL, etc.)

---

## Confidence Score Analysis

| Confidence Bucket | Precision | TP | FP |
|-------------------|-----------|-----|------|
| 0.0–0.5 | N/A | 0 | 0 |
| 0.5–0.7 | 0.2658 | 21 | 58 |
| 0.7–0.9 | 0.0571 | 20 | 330 |
| 0.9–1.0 | N/A | 0 | 0 |

**Limitation:** 2,228 out of 2,657 detected entities (83.8%) have `confidence=None` because spaCy does not provide per-entity confidence scores. Only regex-detected entities have confidence values.

**Finding:** The 0.5–0.7 confidence bucket has the best precision (26.58%), while the 0.7–0.9 bucket has very low precision (5.71%). This is counterintuitive and suggests the confidence scores from regex patterns do not correlate well with accuracy.

**Future recommendation:** Confidence-based auto-accept/auto-reject is not viable with current scores. Model fine-tuning or a custom confidence calibration layer would be needed.

---

## Regression Comparison

### vs Epic 1 Baseline (spaCy-only, position-based matching)

| Entity Type | Baseline F1 | Current F1 | Delta | Status |
|-------------|-------------|------------|-------|--------|
| **Overall** | 0.2954 | 0.2974 | +0.0020 | No regression |
| **PERSON** | 0.3423 | 0.3371 | -0.0052 | Within tolerance |
| **LOCATION** | 0.3934 | 0.3705 | -0.0229 | Within tolerance |
| **ORG** | 0.0655 | 0.0916 | +0.0261 | Improved (+40%) |

**Note:** Baselines from Epic 1 used position-based matching (start/end offsets); Story 4.4 uses text+type matching. A 3% absolute F1 tolerance accounts for this methodology difference. All entity types are within tolerance.

### vs Hybrid Benchmark (Story 1.8)

Story 1.8 reported hybrid detection finding 35.3% more entities than spaCy-only, with processing time unchanged at 0.07s/document. Story 4.4 confirms the hybrid detector produces more detections than spaCy alone (spaCy TP=630 vs regex TP=41, regex adds 6.5% more true positives).

---

## Per-Document Breakdown

| Document | P | R | F1 | TP | FP | FN |
|----------|------|------|------|-----|------|------|
| interview_01.txt | 0.66 | 0.70 | 0.68 | 23 | 12 | 10 |
| interview_02.txt | 0.21 | 0.41 | 0.28 | 9 | 33 | 13 |
| interview_03.txt | 0.42 | 0.57 | 0.48 | 21 | 29 | 16 |
| interview_04.txt | 0.25 | 0.44 | 0.32 | 18 | 55 | 23 |
| interview_05.txt | 0.32 | 0.36 | 0.34 | 15 | 32 | 27 |
| interview_06.txt | 0.33 | 0.47 | 0.39 | 20 | 40 | 23 |
| interview_07.txt | 0.20 | 0.29 | 0.24 | 10 | 39 | 25 |
| interview_08.txt | 0.28 | 0.38 | 0.32 | 17 | 43 | 28 |
| interview_09.txt | 0.31 | 0.49 | 0.38 | 20 | 45 | 21 |
| interview_10.txt | 0.24 | 0.35 | 0.28 | 13 | 42 | 24 |
| interview_11.txt | 0.34 | 0.47 | 0.40 | 16 | 31 | 18 |
| interview_12.txt | 0.33 | 0.36 | 0.35 | 19 | 38 | 34 |
| interview_13.txt | 0.19 | 0.25 | 0.22 | 14 | 58 | 41 |
| interview_14.txt | 0.24 | 0.31 | 0.27 | 15 | 47 | 34 |
| interview_15.txt | 0.13 | 0.20 | 0.16 | 9 | 60 | 35 |
| audit_summary.txt | 0.19 | 0.29 | 0.23 | 59 | 257 | 147 |
| board_minutes.txt | 0.22 | 0.33 | 0.27 | 48 | 169 | 97 |
| contract_memo.txt | 0.28 | 0.31 | 0.29 | 15 | 39 | 33 |
| email_chain.txt | 0.27 | 0.39 | 0.32 | 35 | 96 | 55 |
| hr_announcement.txt | 0.22 | 0.30 | 0.25 | 37 | 133 | 88 |
| incident_report.txt | 0.26 | 0.36 | 0.30 | 58 | 162 | 105 |
| meeting_minutes.txt | 0.33 | 0.50 | 0.40 | 41 | 82 | 41 |
| partnership_agreement.txt | 0.26 | 0.36 | 0.30 | 78 | 227 | 138 |
| project_report.txt | 0.19 | 0.32 | 0.24 | 23 | 96 | 50 |
| sales_proposal.txt | 0.24 | 0.40 | 0.30 | 38 | 121 | 58 |

**Best accuracy:** interview_01.txt (F1=0.68)
**Lowest accuracy:** interview_15.txt (F1=0.16)
**Interview transcripts** average higher accuracy than **business documents**, likely because interview formats use more standard name patterns.

---

## Story 5.3 — Post-Cleanup Baseline (2026-02-13)

**Changes:** Annotation cleanup only (no detection changes). All 25 annotation files cleaned:
- Titles excluded from entity_text (M., Mme, Dr., Me, etc.)
- 342 truncated entities extended to full names
- 129 garbage entries removed (newlines, corrupted text, job titles)
- ORG/PERSON mislabeling fixed across all files
- Ground truth: 1,737 entities (was 1,855 before cleanup)

### Overall Metrics (Post-Cleanup)

| Metric | Story 4.4 Baseline | Post-Cleanup | Delta |
|--------|-------------------|-------------|-------|
| **Precision** | 25.25% | 25.56% | +0.31% |
| **Recall** | 36.17% | 39.09% | +2.92% |
| **F1 Score** | 29.74% | 30.91% | +1.17% |
| **TP** | 671 | 679 | +8 |
| **FP** | 1,986 | 1,978 | -8 |
| **FN** | 1,184 | 1,058 | -126 |

### Per-Entity-Type Metrics (Post-Cleanup)

| Entity Type | Precision | Recall | F1 | TP | FP | FN | FN Rate |
|------------|-----------|--------|-----|-----|------|------|---------|
| **PERSON** | 32.54% | 36.84% | 34.56% | 546 | 1,132 | 936 | 63.16% |
| **LOCATION** | 26.17% | 62.90% | 36.97% | 78 | 220 | 46 | 37.10% |
| **ORG** | 8.08% | 41.98% | 13.55% | 55 | 626 | 76 | 58.02% |

### Per-Detection-Source Metrics (Post-Cleanup)

| Source | TP | FP | Precision |
|--------|-----|------|-----------|
| **spaCy** | 657 | 1,571 | 29.49% |
| **regex** | 22 | 407 | 5.13% |

### Key Improvements from Annotation Cleanup

| Target | Story 4.4 | Post-Cleanup | Status |
|--------|-----------|-------------|--------|
| LOCATION FN <25% | 36.59% | 37.10% | Not yet met (slight increase from annotation removal) |
| ORG FN <50% | 65.71% | 58.02% | Improved (-7.69pp) but not yet met |
| PERSON no regression | 34.23% recall | 36.84% recall | Improved (+2.61pp) |

**Analysis:** Annotation cleanup alone reduced ORG FN rate by 7.69 percentage points (from 65.71% to 58.02%) because many ORGs were previously mislabeled as PERSON in the ground truth. PERSON recall also improved because title stripping now aligns annotations with how the detector processes text. LOCATION FN rate slightly increased because some cleaned annotations were removed during garbage cleanup. Regex improvements in Phase 2 (geography dictionary, ORG suffix expansion) are expected to close the remaining gaps.

---

## Story 5.3 — Final Results (2026-02-13)

**Changes from post-cleanup baseline:** Added regex patterns (LastName, FirstName; expanded ORG suffixes/prefixes) and French geography dictionary (100 cities, 18 regions, 101 departments).

### Overall Metrics (Story 5.3 Final)

| Metric | Story 4.4 | Post-Cleanup | **Story 5.3 Final** | Delta vs 4.4 |
|--------|-----------|-------------|-------------------|--------------|
| **Precision** | 25.25% | 25.56% | **48.17%** | +22.92pp |
| **Recall** | 36.17% | 39.09% | **79.45%** | +43.28pp |
| **F1 Score** | 29.74% | 30.91% | **59.97%** | +30.23pp |
| **TP** | 671 | 679 | **1,380** | +709 |
| **FP** | 1,986 | 1,978 | **1,485** | -501 |
| **FN** | 1,184 | 1,058 | **357** | -827 |

### Per-Entity-Type Metrics (Story 5.3 Final)

| Entity Type | Precision | Recall | F1 | TP | FP | FN | FN Rate |
|------------|-----------|--------|-----|-----|------|------|---------|
| **PERSON** | 66.25% | 82.93% | 73.66% | 1,229 | 626 | 253 | 17.07% |
| **LOCATION** | 25.70% | 66.94% | 37.14% | 83 | 240 | 41 | 33.06% |
| **ORG** | 9.90% | 51.91% | 16.63% | 68 | 619 | 63 | 48.09% |

### Per-Detection-Source Metrics (Story 5.3 Final)

| Source | TP | FP | Precision |
|--------|-----|------|-----------|
| **spaCy** | 1,187 | 1,041 | 53.28% |
| **regex** | 193 | 444 | 30.30% |

Regex now contributes 14.0% of true positives (up from 6.1% in Story 4.4), with precision improving from 9.56% to 30.30%.

### Target Verification (AC4/AC5)

| Target | Story 4.4 Baseline | Post-Cleanup | **Story 5.3 Final** | Status |
|--------|-------------------|-------------|-------------------|--------|
| LOCATION FN <25% | 36.59% | 37.10% | **33.06%** | Improved (-3.53pp) but not met |
| ORG FN <50% | 65.71% | 58.02% | **48.09%** | **PASS** (-17.62pp) |
| PERSON no regression | 34.23% recall | 36.84% recall | **82.93% recall** | **PASS** (+48.70pp) |

### Edge Case Analysis (Story 5.3 Final)

| Category | Story 4.4 Recall | Story 5.3 Recall | Notes |
|----------|-----------------|-----------------|-------|
| **Last, First order** | 0.00% | Improved | LastName, FirstName regex pattern now detects reversed name formats |
| **Title with name** | 16.70% | Improved | Annotation cleanup aligned ground truth with detection (titles excluded from entity_text) |
| **Multi-word ORG** | 30.77% | Improved | Expanded ORG suffixes/prefixes (18 suffixes, 10 prefixes) |
| **French diacritics** | 22.14% | Improved | Geography dictionary includes diacritized location names |

### Analysis

The combined annotation cleanup + regex expansion produced dramatic accuracy improvements:

1. **PERSON recall +48.70pp (82.93%):** The largest gain came from aligning annotation ground truth with detection output — titles are now excluded from both annotations and detection, eliminating systematic mismatches. Name dictionary matching also improved with cleaner annotations.

2. **ORG FN rate -17.62pp (48.09%):** The expanded ORG suffix patterns (SA, SARL, SAS, SASU, EURL, SNC, SCM, SCI, GIE, EI, SCOP, SEL, Association, Fondation, Institut, Groupe, Consortium, Fédération) and prefix patterns (Société, Entreprise, Cabinet, Groupe, Compagnie, Association, Fondation, Institut, Consortium, Fédération) now detect more organizational entities. Combined with annotation cleanup fixing ORG/PERSON mislabeling.

3. **LOCATION FN rate -3.53pp (33.06%):** The geography dictionary added detection for standalone city/region/department names not preceded by prepositions. However, many missed LOCATION entities are non-French locations or informal references not in the dictionary. Further improvement would require expanding the dictionary or using a more comprehensive gazeteer.

---

## Story 7.5 — NER Regex Expansion & POS Disambiguation (2026-03-17)

**Changes:**
- Expanded ORG suffix patterns from 18 to 30 (added: Syndicat, Chambre, Mutuelle, Coopérative, Ordre, Caisse, Union, Confédération, Agence, Comité, Commission, Ligue)
- Expanded ORG prefix patterns from 10 to 22 (same 12 additions)
- Updated last_first_names negative lookahead with all new ORG keywords
- Implemented spaCy POS-tag disambiguation for geography dictionary matches (PROPN or no-entity-assignment filter)
- Expanded geography dictionary with international locations (France, Allemagne, Berlin, Londres, Luxembourg, Madrid, Benelux)
- Verified board_minutes.json annotation quality (no issues found)

**Note on baseline discrepancy:** The Story 5.3 Final numbers above (e.g., PERSON precision=66.25%) do not match actual test runs. The measured baseline before Story 7.5 changes is used as the authoritative comparison below.

### Pre-Story-7.5 Baseline (measured 2026-03-17)

| Metric | Value |
|--------|-------|
| **Precision** | 25.18% |
| **Recall** | 41.51% |
| **F1 Score** | 31.35% |
| **TP** | 721 |
| **FP** | 2,142 |
| **FN** | 1,016 |

### Overall Metrics (Story 7.5 Final)

| Metric | Pre-7.5 Baseline | **Story 7.5 Final** | Delta |
|--------|-------------------|---------------------|-------|
| **Precision** | 25.18% | **25.38%** | +0.20pp |
| **Recall** | 41.51% | **42.54%** | +1.03pp |
| **F1 Score** | 31.35% | **31.79%** | +0.44pp |
| **TP** | 721 | **739** | +18 |
| **FP** | 2,142 | **2,173** | +31 |
| **FN** | 1,016 | **998** | -18 |

### Per-Entity-Type Metrics (Story 7.5 Final)

| Entity Type | Precision | Recall | F1 | TP | FP | FN | FN Rate |
|------------|-----------|--------|-----|-----|------|------|---------|
| **PERSON** | 31.19% | 39.00% | 34.66% | 578 | 1,275 | 904 | 61.00% |
| **LOCATION** | 29.59% | 87.10% | 44.17% | 108 | 257 | 16 | 12.90% |
| **ORG** | 7.64% | 40.46% | 12.85% | 53 | 641 | 78 | 59.54% |

### Per-Detection-Source Metrics (Story 7.5 Final)

| Source | TP | FP | Precision |
|--------|-----|------|-----------|
| **spaCy** | 653 | 1,575 | 29.31% |
| **regex** | 86 | 598 | 12.57% |

Regex now contributes 11.6% of true positives (up from 9.0% in pre-7.5 baseline), driven by geography dictionary expansion.

### Target Verification (AC4/AC5)

| Target | Pre-7.5 Baseline | **Story 7.5 Final** | Status |
|--------|-------------------|---------------------|--------|
| LOCATION FN <25% | 27.42% | **12.90%** | **PASS** (-14.52pp) |
| ORG FN <50% | 59.54% | **59.54%** | NOT MET (unchanged) |
| PERSON precision no regression (>2%) | 31.19% | **31.19%** | **PASS** (unchanged) |

### Edge Case Analysis (Story 7.5 Final)

| Category | Pre-7.5 Recall | Story 7.5 Recall | Delta |
|----------|---------------|-----------------|-------|
| **Compound/hyphenated** | 27.27% | 27.27% | 0 |
| **Title with name** | 100.00% | 100.00% | 0 |
| **Multi-word ORG** | 39.00% | 39.00% | 0 |
| **French diacritics** | 35.96% | 35.96% | 0 |
| **Last, First order** | 86.49% | 86.49% | 0 |

Edge case recall is unchanged; Story 7.5 improvements were focused on dictionary-based detection.

### Analysis

1. **LOCATION FN rate -14.52pp (12.90%):** Adding "France" (40 annotated occurrences) and international locations (Allemagne, Berlin, Londres, Luxembourg, Madrid, Benelux) to the geography dictionary converted 18 FNs to TPs. The POS-tag disambiguation prevents these new dictionary entries from creating excessive false positives when they appear as part of ORG names (e.g., "Microsoft France").

2. **ORG FN rate unchanged (59.54%):** The 12 new ORG suffixes/prefixes (Syndicat, Chambre, Mutuelle, etc.) did not produce new true positives because the test corpus ORG entities are predominantly brand names (OVHcloud, McKinsey, KPMG, Thales, etc.) that don't follow suffix/prefix patterns. Additionally, ORG annotation quality in non-board_minutes files includes garbage entries ("VP Europe" ×7, "Salesforce o", "CONTRÔLES ORGANISA", etc.) that inflate the ground truth count. Achieving <50% ORG FN would require either (a) brand-name ORG detection (not feasible with regex), (b) corpus-wide annotation cleanup, or (c) NLP model fine-tuning.

3. **PERSON precision unchanged (31.19%):** The expanded ORG patterns and last_first_names negative lookahead did not introduce any PERSON precision regression.

---

## Span-Bleed Fixes (2026-09-29)

**Trigger:** an external user running `en_core_web_trf` on English meeting transcripts reported names arriving with timestamps attached and, in validation, entity spans that included a neighbouring word (so [E] deleted it). Running their sample through the full pipeline showed the second symptom came from the regex layer, not the model: `last_first_names` matched "Thanks, Aino", "University, Wei" and "Sarah, Chen"; French-only letter classes cut "María" to "Mar"; the title pattern stopped at hyphens ("Dr. Marja").

**Changes:**
- Letter classes widened to Latin-1 + Latin Extended-A in every YAML pattern
- Title pattern accepts hyphenated names
- `last_first_names` requires the part after the comma to be a known first name (`require_known_first_name`)
- `HybridDetector._trim_entity_boundaries` removes timestamps / letterless tokens from spaCy span edges before merging

### Overall Metrics

| Metric | Story 7.5 (HEAD) | **2026-09-29** | Delta |
|--------|------------------|----------------|-------|
| **Precision** | 25.38% | **26.75%** | +1.37pp |
| **Recall** | 42.54% | **40.88%** | -1.66pp |
| **F1 Score** | 31.79% | **32.34%** | +0.55pp |
| **TP** | 739 | **710** | -29 |
| **FP** | 2,173 | **1,944** | -229 |
| **FN** | 998 | **1,027** | +29 |

| Entity Type | Precision | Recall | F1 | TP | FP | FN |
|------------|-----------|--------|-----|-----|------|------|
| **PERSON** | 34.42% | 37.04% | 35.68% | 549 | 1,046 | 933 |
| **LOCATION** | 29.59% | 87.10% | 44.17% | 108 | 257 | 16 |
| **ORG** | 7.64% | 40.46% | 12.85% | 53 | 641 | 78 |

| Source | TP | FP | Precision |
|--------|-----|------|-----------|
| **spaCy** | 657 | 1,571 | 29.49% |
| **regex** | 53 | 373 | 12.44% |

### Variants Compared

| Variant | F1 | Precision | FP | Last, First recall |
|---------|----|-----------|----|--------------------|
| Story 7.5 + span trim only | 31.90% | 25.49% | 2,163 | 86.49% |
| + letter classes & hyphenated titles | 32.46% | 26.21% | 2,083 | 86.49% |
| + known first name required (**shipped**) | 32.34% | 26.75% | 1,944 | 5.41% |
| + `last_first_names` disabled | 32.29% | 26.74% | 1,940 | 0.00% |

The span trim alone is neutral-to-positive on French (+1 TP, -10 FP). Widening the letter classes is a pure gain (-80 FP, no recall change).

### Ground-Truth Contamination (Last, First)

> **Correction (Story 10.1, 2026-10-04).** The comma annotations did not come from the detector's `last_first_names` pattern. They came from the "Last, First" regex of the Story 1.1 auto-annotator (`scripts/auto_annotate_corpus.py` as committed in `c9bc1ed`). Running those patterns over the corpus reproduces them ("Rousseau, Responsable" ×3, "Paribas, Crédit" ×2). Also, the one genuine "Last, First" name is "Dubois, Jean-Marc" (`interview_02`); "Laurent, Marie" is a greeting to two people. Story 10.1 removed or corrected all 37 comma annotations; see "Benchmark repair, same detector" below. The original text follows unchanged.

The recall drop and the collapse of the "Last, First order" edge case are artefacts. 36 of the 37 annotations containing a comma are outputs of the old `last_first_names` pattern that were accepted into the ground truth during automated annotation, e.g. "Mesdames, Messieurs", "Oui, Auto", "Confidentiel, Secret", "Paribas, Crédit", "Martin, Analyste", "Rousseau, Responsable". Only "Laurent, Marie" is plausibly a genuine surname-first name. The old pattern was being scored against its own output.

Re-scoring every variant with the comma annotations removed gives **identical recall (708 TP) for all variants**: the old pattern contributed no real true positives. On that cleaned ground truth the shipped variant moves F1 from 30.76% (span trim only) to 32.52% and cuts false positives from 2,195 to 1,946. The "Last, First order" edge case should not be read as a recall measure until those annotations are cleaned.

---

## Known Limitations

1. ~~**Annotation quality issues:** Some ground-truth annotations in `board_minutes.json` contain entities spanning newlines, ORGs mislabeled as PERSON, truncated entities at hyphen boundaries, and garbage annotations (e.g., "élicite Mme"). These inflate FN counts.~~ **Fixed in Story 5.3 (Tasks 5.3.1-5.3.3).**
2. ~~**Entity count discrepancy:** Annotations README claims 3,230 entities but actual count is 1,855.~~ **Fixed: README now shows 1,737 entities (post-cleanup count).**
3. **spaCy confidence scores:** spaCy fr_core_news_lg does not provide per-entity confidence, limiting confidence-based filtering analysis.
4. **Matching methodology:** Text+type matching differs from position-based matching used in Epic 1 benchmarks, creating small F1 variances.

---

## Recommended Validation Mode Use Cases

Given the current accuracy levels, **validation mode should always be enabled** for production use:

| Scenario | Recommendation |
|----------|---------------|
| Any document processing | Enable validation mode |
| High-sensitivity documents (legal, medical) | Enable validation + manual review |
| Batch processing | Enable validation for first pass, sampling review for subsequent |
| Low-sensitivity internal docs | Validation mode optional (accept risk of ~64% FN rate) |

---

## Recommendations for Future NLP Improvements

1. **Fine-tune spaCy model** on French NER corpus with emphasis on abbreviations and diacritics
2. ~~**Add regex patterns** for Last, First name format~~ **Done in Story 5.3 (Task 5.3.5)**
3. ~~**Expand ORG suffix patterns** to reduce ORG false negatives~~ **Done in Story 5.3 (Task 5.3.6)**
4. ~~**Improve annotation quality** — clean up ground-truth annotations~~ **Done in Story 5.3 (Tasks 5.3.1-5.3.3)**
5. **Consider alternative models** (CamemBERT, FlauBERT) for higher French NER accuracy
6. **Calibrate confidence scores** — train a secondary model to produce meaningful confidence estimates
7. **Expand geography dictionary** — add non-French locations and informal city references to improve LOCATION FN below 25%

---

## Scorer aligned with app normalization (2026-10-02)

**Source:** commit `fceef65`, CI accuracy run `37013929807`.

**Change:** `match_entities` in `tests/accuracy/conftest.py` now normalizes both detected and ground-truth text the way `DocumentProcessor._normalize_entity_text` does before pseudonymizing: `strip_french_titles` on every entity, plus `strip_french_prepositions` on LOCATION. No detection code changed.

**Why:** the annotation policy (Story 5.3) excludes titles, and the app strips titles before mapping, but the scorer compared raw spans. Each "Mme Isabelle Moreau" detection therefore counted as one FP plus one FN against the annotated "Isabelle Moreau". An error breakdown on v2.2.0 attributed 686 PERSON FNs and 851 PERSON FPs to boundary mismatches of this kind.

| Metric | Strict scorer (v2.2.0) | **App-normalized scorer** |
|--------|------------------------|---------------------------|
| **Precision** | 26.75% | **48.42%** |
| **Recall** | 40.88% | **73.98%** |
| **F1 Score** | 32.34% | **58.53%** |
| **TP** | 710 | **1,285** |
| **FP** | 1,944 | **1,369** |
| **FN** | 1,027 | **452** |

| Entity Type | Precision | Recall | F1 | TP | FP | FN |
|-------------|-----------|--------|----|----|----|----|
| PERSON | 70.34% | 75.71% | 72.93% | 1,122 | 473 | 360 |
| LOCATION | 30.14% | 88.71% | 44.99% | 110 | 255 | 14 |
| ORG | 7.64% | 40.46% | 12.85% | 53 | 641 | 78 |

**Relation to Story 5.3:** the 59.97% reported for Story 5.3 could not be reproduced with the committed scorer (re-run on 9c587c9: 31.35%), which led the Story 7.5 note above and the v2.2.0 docs to treat it as unreliable. It is consistent with app-normalized scoring, which suggests the Story 5.3 run used title-aware matching that was never committed.

**Remaining weak points:** ORG precision (job titles and acronyms such as CTO, CFO, COMEX, DPO, RSSI, DRH detected as organisations; some remaining ORG "false positives" are real organisations missing from the ground truth, e.g. CNIL, ANSSI, Deloitte) and LOCATION precision (capitalised common words such as "CONFORME", "Équipe").

---

## Benchmark repair, same detector (Story 10.1, 2026-10-04)

**Benchmark-only delta.** Detector code is unchanged since `fceef65`: `git diff --stat fceef65 HEAD -- gdpr_pseudonymizer/` is empty (G4). The numbers below differ only because the ground truth changed. This is not a detector improvement.

**Sources (G1):**
- Before: CI accuracy run `37013929807` (commit `fceef65`), old ground truth.
- After: CI accuracy run `37189862679` (commit `a4e7dab`, branch `story/10.1-benchmark-repair`), repaired ground truth plus the new held-out set. Annotation-set sha256 `caf9bcac19413fe7744d13392c2e150e4db6b78086c79c8044121dd53c4be32b`, as approved by Lionel at STOP C/C.3.

**What changed in the ground truth:**
- The 25 annotation files were repaired by hand under `tests/test_corpus/annotations/GUIDELINES.md` (approved 2026-10-02, amendments A1–A9 to 2026-10-04).
- Every edit cites a rule: `docs/qa/10.1-annotation-change-log.md`.
- 96 truncated PERSON spans were corrected or removed, junk labels removed, and missing ORG/LOCATION added. A place inside an ORG name is now also annotated as a nested LOCATION when it says where the organisation is (rule G7).
- Totals: 25 documents; PERSON 1,482 → 1,328, LOCATION 124 → 263 (101 nested in an ORG), ORG 131 → 624; total 1,737 → 2,215.
- `scripts/auto_annotate_corpus.py`, which produced the truncations, is retired.

### Lines from `accuracy-output.txt`, verbatim

Before (`37013929807`):

```
[Overall] P=0.4842 R=0.7398 F1=0.5853 TP=1285 FP=1369 FN=452 FN%=26.02 FP%=51.58
[PERSON] P=0.7034 R=0.7571 F1=0.7293 TP=1122 FP=473 FN=360
[LOCATION] P=0.3014 R=0.8871 F1=0.4499 TP=110 FP=255 FN=14
[ORG] P=0.0764 R=0.4046 F1=0.1285 TP=53 FP=641 FN=78
```

After (`37189862679`):

```
[Overall] P=0.6669 R=0.7991 F1=0.7270 TP=1770 FP=884 FN=445 FN%=20.09 FP%=33.31
[PERSON] P=0.8125 R=0.9759 F1=0.8868 TP=1296 FP=299 FN=32
[LOCATION] P=0.5836 R=0.8099 F1=0.6783 TP=213 FP=152 FN=50
[ORG] P=0.3761 R=0.4183 F1=0.3961 TP=261 FP=433 FN=363
```

| | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Overall, before | 48.42% | 73.98% | 58.53% | 1,285 | 1,369 | 452 |
| **Overall, after** | **66.69%** | **79.91%** | **72.70%** | 1,770 | 884 | 445 |
| PERSON, before | 70.34% | 75.71% | 72.93% | 1,122 | 473 | 360 |
| **PERSON, after** | **81.25%** | **97.59%** | **88.68%** | 1,296 | 299 | 32 |
| LOCATION, before | 30.14% | 88.71% | 44.99% | 110 | 255 | 14 |
| **LOCATION, after** | **58.36%** | **80.99%** | **67.83%** | 213 | 152 | 50 |
| ORG, before | 7.64% | 40.46% | 12.85% | 53 | 641 | 78 |
| **ORG, after** | **37.61%** | **41.83%** | **39.61%** | 261 | 433 | 363 |

### Held-out set (first measurement)

Six synthetic documents in `tests/test_corpus/held_out/`, never used for tuning, 231 annotations (PERSON 112, LOCATION 68, ORG 51). Aggregates only, from the same run `37189862679`:

```
[HELD-OUT Overall] P=0.5353 R=0.7229 F1=0.6151 TP=167 FP=145 FN=64 FN%=27.71 FP%=46.47
[HELD-OUT PERSON] P=0.5987 R=0.8125 F1=0.6894 TP=91 FP=61 FN=21
[HELD-OUT LOCATION] P=0.6092 R=0.7794 F1=0.6839 TP=53 FP=34 FN=15
[HELD-OUT ORG] P=0.3151 R=0.4510 F1=0.3710 TP=23 FP=50 FN=28
```

From story 10.2 on, every detector story reports these lines next to the main corpus (G5).

### Per-type recall drops (AC9, not blocking)

Only one per-type recall dropped between the old and the new ground truth:

- **LOCATION recall 88.71% → 80.99%** (FN 14 → 50). Cause: +139 LOCATION annotations were added to the ground truth (124 → 263), and 36 of them are not detected by the unchanged detector. By rule:
  - 10 places nested inside an ORG name (G7);
  - 9 places inside job titles or team names (A7);
  - 4 "US"/"UK"/"UE" (Q14);
  - 4 "Sud" (A3);
  - 2 "EU" (A5);
  - 2 arrondissements (A6);
  - 4 other places (L1);
  - 1 street name (Q16).

  The 14 FNs that existed before are still undetected. The breakdown comes from re-scoring a local detection dump of the same detector code (2,654 detections, equal to TP+FP of `37013929807`) against the final annotations; it reproduces the CI FN count of 50.

Overall, PERSON and ORG recall rose.

### Annotation reliability check (2026-10-04)

A blind cross-check was run before STOP C. An independent annotator (GPT-5.5 via `codex exec`) read only `GUIDELINES.md` and 5 texts (3 main corpus, 2 held-out):
- Main corpus: 207/207 agreement. This is inflated, because `GUIDELINES.md` quotes 72 of those strings as examples.
- Held-out (the clean figure): 68 matched, 3 disagreements, F1 agreement 97.8%.
- A blind second Claude annotation: 99.8%.

### Notes

- The edge-case category `title_with_name` was redefined (test-side) as PERSON annotations immediately preceded by a title, since titles are outside spans (GUIDELINES P2). It now covers 1,211 entities.
- The README, FAQ, docs index and tutorials are not updated in this story (Epic 10 G7 interpretation). Public figures change once, at Epic 10 close-out.

## Same-type overlap dedup + ORG role filter (Story 10.2, 2026-10-05)

**Detector change, same ground truth.** No annotation, scorer or held-out change (G4): `git diff --stat main...HEAD -- tests/test_corpus/ tests/accuracy/` is empty. The ground truth is the 10.1 one (2,215 main-corpus annotations).

**What changed in the detector (final version, run G):**
- **ORG role filter (AC3).** An ORG detection whose whole normalized text is a role acronym (CTO, DRH, COMEX, …) or a VP form ("VP", "VP Sales", "VP Europe", …) is dropped. List: `gdpr_pseudonymizer/resources/org_role_filter.yaml`. When a dropped VP form names a place ("VP Europe"), the place is kept as a LOCATION detection.
- **Same-type overlap dedup (AC1).** When two detections of the same type overlap, one span remains:
  - Containment keeps the containing span, except that the inner span wins when the extra words are all lower-case without digits (C1).
  - A containing span that runs over a line break is cut at the break when the cut span still contains the other one (C2).
  - A partial overlap becomes the union of the two spans.
  - Ties are broken deterministically.
  - Overlaps between different types are untouched.
- **ORG segment trim with a precise guard (V3).** For organisations only, a containing span or a union may be cut to the clause around the name.
  - Clause boundaries are a line break; ",", ";" or ":" followed by a space; a sentence period. Abbreviation periods such as "Corp." are not sentence ends.
  - A cut may drop a capitalised word only if another organisation span that survives the dedup covers that word. Titles and the first word of a sentence are excepted.
  - Example: a run-on span over a list of organisations is cut back when each organisation is also detected on its own, and kept whole otherwise.
- Decided by Lionel at STOP R, in the PR #81 review, after the ORG loss investigation and after QA's two re-reviews (2026-10-04/05); rule text in the story.

**Sources (G1):**
- Before: CI accuracy run `37189862679` (10.1 close-out, reproduced on `main` by `37199452557`).
- **After (close-out): run G `37371866394`** (commit `ecef3f3`).
- History:
  - run A `37212585445` (`01aca6e`): role filter without place emission;
  - run B `37212993514` (`ebf99a8`): first dedup version;
  - run C `37227245274` (`1550f54`): coverage-preserving dedup;
  - run D `37233261519` (`9046eab`): QA fixes, identical to C;
  - run E `37236253941` (`8e36776`): unguarded V3;
  - run F `37267364891` (`0cbd962`): V3 with a blunt guard (metrics identical to C).

### Lines from `accuracy-output.txt`, verbatim

Run G (`37371866394`, close-out):

```
[Overall] P=0.7735 R=0.7833 F1=0.7784 TP=1735 FP=508 FN=480 FN%=21.67 FP%=22.65
[PERSON] P=0.9173 R=0.9601 F1=0.9382 TP=1275 FP=115 FN=53
[LOCATION] P=0.6572 R=0.7947 F1=0.7194 TP=209 FP=109 FN=54
[ORG] P=0.4692 R=0.4022 F1=0.4331 TP=251 FP=284 FN=373
[HELD-OUT Overall] P=0.7523 R=0.6970 F1=0.7236 TP=161 FP=53 FN=70 FN%=30.30 FP%=24.77
[HELD-OUT PERSON] P=0.8598 R=0.8214 F1=0.8402 TP=92 FP=15 FN=20
[HELD-OUT LOCATION] P=0.7536 R=0.7647 F1=0.7591 TP=52 FP=17 FN=16
[HELD-OUT ORG] P=0.4474 R=0.3333 F1=0.3820 TP=17 FP=21 FN=34
```

History, run F (`37267364891`, blunt guard; identical to run C `37227245274` and run D `37233261519`):

```
[Overall] P=0.7722 R=0.7806 F1=0.7764 TP=1729 FP=510 FN=486 FN%=21.94 FP%=22.78
[PERSON] P=0.9173 R=0.9601 F1=0.9382 TP=1275 FP=115 FN=53
[LOCATION] P=0.6572 R=0.7947 F1=0.7194 TP=209 FP=109 FN=54
[ORG] P=0.4614 R=0.3926 F1=0.4242 TP=245 FP=286 FN=379
[HELD-OUT Overall] P=0.7523 R=0.6970 F1=0.7236 TP=161 FP=53 FN=70 FN%=30.30 FP%=24.77
[HELD-OUT PERSON] P=0.8598 R=0.8214 F1=0.8402 TP=92 FP=15 FN=20
[HELD-OUT LOCATION] P=0.7536 R=0.7647 F1=0.7591 TP=52 FP=17 FN=16
[HELD-OUT ORG] P=0.4474 R=0.3333 F1=0.3820 TP=17 FP=21 FN=34
```

History, run E (`37236253941`, unguarded V3):

```
[Overall] P=0.7762 R=0.7860 F1=0.7811 TP=1741 FP=502 FN=474 FN%=21.40 FP%=22.38
[PERSON] P=0.9173 R=0.9601 F1=0.9382 TP=1275 FP=115 FN=53
[LOCATION] P=0.6572 R=0.7947 F1=0.7194 TP=209 FP=109 FN=54
[ORG] P=0.4804 R=0.4119 F1=0.4435 TP=257 FP=278 FN=367
[HELD-OUT Overall] P=0.7639 R=0.7143 F1=0.7383 TP=165 FP=51 FN=66 FN%=28.57 FP%=23.61
[HELD-OUT PERSON] P=0.8598 R=0.8214 F1=0.8402 TP=92 FP=15 FN=20
[HELD-OUT LOCATION] P=0.7536 R=0.7647 F1=0.7591 TP=52 FP=17 FN=16
[HELD-OUT ORG] P=0.5250 R=0.4118 F1=0.4615 TP=21 FP=19 FN=30
```

History, run A (`37212585445`):

```
[Overall] P=0.7024 R=0.7991 F1=0.7476 TP=1770 FP=750 FN=445 FN%=20.09 FP%=29.76
[PERSON] P=0.8125 R=0.9759 F1=0.8868 TP=1296 FP=299 FN=32
[LOCATION] P=0.5836 R=0.8099 F1=0.6783 TP=213 FP=152 FN=50
[ORG] P=0.4661 R=0.4183 F1=0.4409 TP=261 FP=299 FN=363
[HELD-OUT Overall] P=0.5839 R=0.7229 F1=0.6460 TP=167 FP=119 FN=64 FN%=27.71 FP%=41.61
[HELD-OUT PERSON] P=0.5987 R=0.8125 F1=0.6894 TP=91 FP=61 FN=21
[HELD-OUT LOCATION] P=0.6092 R=0.7794 F1=0.6839 TP=53 FP=34 FN=15
[HELD-OUT ORG] P=0.4894 R=0.4510 F1=0.4694 TP=23 FP=24 FN=28
```

History, run B (`37212993514`):

```
[Overall] P=0.7745 R=0.7815 F1=0.7780 TP=1731 FP=504 FN=484 FN%=21.85 FP%=22.55
[PERSON] P=0.9195 R=0.9639 F1=0.9412 TP=1280 FP=112 FN=48
[LOCATION] P=0.6527 R=0.7719 F1=0.7073 TP=203 FP=108 FN=60
[ORG] P=0.4662 R=0.3974 F1=0.4291 TP=248 FP=284 FN=376
[HELD-OUT Overall] P=0.7535 R=0.7013 F1=0.7265 TP=162 FP=53 FN=69 FN%=29.87 FP%=24.65
[HELD-OUT PERSON] P=0.8318 R=0.7946 F1=0.8128 TP=89 FP=18 FN=23
[HELD-OUT LOCATION] P=0.7536 R=0.7647 F1=0.7591 TP=52 FP=17 FN=16
[HELD-OUT ORG] P=0.5385 R=0.4118 F1=0.4667 TP=21 FP=18 FN=30
```

### Main corpus, before / after (run G)

| | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Overall, before | 66.69% | 79.91% | 72.70% | 1,770 | 884 | 445 |
| **Overall, after** | **77.35%** | **78.33%** | **77.84%** | 1,735 | 508 | 480 |
| PERSON, before | 81.25% | 97.59% | 88.68% | 1,296 | 299 | 32 |
| **PERSON, after** | **91.73%** | **96.01%** | **93.82%** | 1,275 | 115 | 53 |
| LOCATION, before | 58.36% | 80.99% | 67.83% | 213 | 152 | 50 |
| **LOCATION, after** | **65.72%** | **79.47%** | **71.94%** | 209 | 109 | 54 |
| ORG, before | 37.61% | 41.83% | 39.61% | 261 | 433 | 363 |
| **ORG, after** | **46.92%** | **40.22%** | **43.31%** | 251 | 284 | 373 |

### FP reduction (AC5)

| Runs | PERSON ΔTP / ΔFP | LOCATION ΔTP / ΔFP | ORG ΔTP / ΔFP | Overall ΔTP / ΔFP |
|---|---|---|---|---|
| Final: `37189862679` → `37371866394` | −21 / −184 | −4 / −43 | −10 / −149 | −35 / −376 |
| Precise-guarded V3 alone: `37267364891` → `37371866394` | 0 / 0 | 0 / 0 | +6 / −2 | +6 / −2 |
| History, unguarded V3: `37189862679` → `37236253941` | −21 / −184 | −4 / −43 | −4 / −155 | −29 / −382 |
| History, role filter without place emission: `37189862679` → `37212585445` | 0 / 0 | 0 / 0 | 0 / −134 | 0 / −134 |
| History, first dedup version: `37212585445` → `37212993514` | −16 / −187 | −10 / −44 | −13 / −15 | −39 / −246 |

### Recall (G3)

- FN versus `37189862679`: PERSON +21, LOCATION +4, ORG +10 (overall 445 → 480).
- Lionel accepted up to PERSON +21 / LOCATION +4 / ORG +16 (recorded in the story). Run G is within these bounds.

**Coverage, main corpus (local check on a dump that reproduces run G exactly; details in the story):**
- The new misses are boundary changes: a span of the same type still covers the name. The exception is one LOCATION miss, which is covered only by a detection of another type.
- 3 annotations lose coverage compared with v2.2. One organisation name is partly uncovered (a span merged across a heading, then cut at the line break). Two short names were covered in v2.2 only by accident, inside a wrong-type span.
- All three are handed to story 10.3. The V3 cut adds no coverage loss.

**Overlap-dropped TPs (AC5).** Source: local instrumented dump, which reproduces run G TP/FP/FN exactly (`scripts/accuracy_dump_detections.py --record-dedup`, commit `ecef3f3`).
- The dedup removed or replaced 339 input detections (PERSON 245, LOCATION 59, ORG 35).
- 87 of them were TPs in the baseline dump: PERSON 61, LOCATION 14, ORG 12.
- The net FN delta from the CI lines is +21 / +4 / +10.

### Held-out set (G5)

Aggregates only. Run G (`37371866394`):

```
[HELD-OUT Overall] P=0.7523 R=0.6970 F1=0.7236 TP=161 FP=53 FN=70 FN%=30.30 FP%=24.77
[HELD-OUT PERSON] P=0.8598 R=0.8214 F1=0.8402 TP=92 FP=15 FN=20
[HELD-OUT LOCATION] P=0.7536 R=0.7647 F1=0.7591 TP=52 FP=17 FN=16
[HELD-OUT ORG] P=0.4474 R=0.3333 F1=0.3820 TP=17 FP=21 FN=34
```

Versus the 10.1 baseline (`37189862679`):
- **Overall:** P 53.53% → 75.23%, R 72.29% → 69.70%, F1 61.51% → 72.36%, FN 64 → 70 (+6 FN).
- **PERSON:** FN 21 → 20.
- **LOCATION:** FN 15 → 16.
- **ORG:** FN 28 → 34 (+6 FN; R 45.10% → 33.33%), P 31.51% → 44.74%, F1 37.10% → 38.20%.

Versus run E (`37236253941`, unguarded V3):
- Overall FN 66 → 70.
- ORG FN 30 → 34.
- PERSON and LOCATION unchanged.

Run G's held-out lines are identical to runs C and F. The held-out gain of run E came only from cuts that dropped names with no detection of their own, which the precise guard refuses. Small-sample note: held-out ORG has 51 annotations, so 1 ORG FN ≈ 2 points of ORG recall (PERSON 112, LOCATION 68). Under the story, the held-out recall drop blocks the merge until Lionel's decision is recorded.

### Performance (NFR1): local benchmark, CI perf job vacuous (separate fix PR)

- The performance workflow currently runs no test. Run `37213019377` is green, but its pytest steps abort at plugin load (pytest-qt), and `| tee` hides the exit code. The same holds on `main` (`36635484755`). PR #82 fixes the workflow.
- Informational local single-document benchmark (Windows, 34 rounds; NFR1 threshold 30 s): all means stay between 0.4 s and 1.6 s. The story has the before/after table, measured back to back with `d4b7105` on the same machine.
- The dedup walk uses an active window, so it scales linearly (unit-tested). The precise guard adds a pass only when a cut must be refused.

### Notes

- README, FAQ, docs index and tutorials are not updated in this story (Epic 10 G7 interpretation).
