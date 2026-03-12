# Epic 9: v3.0 — NLP Accuracy & Intelligence

**Epic Goal:** Transform the pseudonymization engine from "good enough with mandatory validation" to "trustworthy with optional validation" by fine-tuning a French NER model to 70-85% F1, implementing confidence-based auto-validation, and adding coreference resolution — enabling a new optional no-validation mode for high-confidence documents.

**Target Release:** v3.0.0
**Duration:** Estimated 8-12 weeks
**Predecessor:** Epic 8 (v2.2.0)

---

## Existing System Context

- **v2.2:** Full-featured CLI + GUI, standalone executables, format preservation (DOCX/PDF), Excel/CSV support, auto-update, WCAG AA, French/English i18n
- **NER Accuracy Baseline (v2.1):**
  - Hybrid detection (spaCy + regex): F1 ~60% (Story 4.4 baseline)
  - spaCy alone: F1 ~30% on domain-specific text
  - PERSON recall ~80%, LOCATION recall ~63-75%, ORG recall ~34-50%
  - 83.8% of entities have no meaningful confidence score (spaCy limitation)
- **Current Constraint:** Validation is mandatory because ~20% of entities are missed (1 in 5). Users cannot trust automated output without review.
- **Key Dependency:** Ground-truth corpus quality (FE-012 cleanup in v2.1) is a prerequisite for model training.

---

## Strategic Context

### Why NLP Accuracy Now?

v1.0-v2.2 focused on building the product surface — CLI, GUI, formats, distribution, accessibility. The core NLP engine has remained essentially unchanged since Epic 1 (spaCy `fr_core_news_lg` + regex hybrid). With the product mature, the highest-leverage investment is now **accuracy** — the quality of the pseudonymization itself.

### The Accuracy Gap

| Metric | Current (v2.1) | Target (v3.0) | Impact |
|--------|----------------|---------------|--------|
| Overall F1 | ~60% | 70-85% | Fewer missed entities, fewer false positives |
| PERSON recall | ~80% | 90%+ | Near-complete person detection |
| LOCATION recall | ~63-75% | 80%+ | Significantly fewer missed locations |
| ORG recall | ~34-50% | 60%+ | Major improvement for organization detection |
| Confidence reliability | None (83.8%) | 100% calibrated | Enables auto-validation |
| Validation required | Always | Optional | Unlocks "trust the tool" mode for routine work |

### Why v3.0 (Major Version)?

The major version bump reflects a **paradigm shift**, not a breaking API change. v1.x-v2.x required mandatory validation — the tool's output was always "human-reviewed." v3.0 introduces optional validation, meaning the tool can produce "machine-only" output for the first time. This changes the trust model and user workflow fundamentally. The CLI/GUI API remains fully backward compatible — `--no-validate` is additive.

### What Changes

| Component | Changes | Impact |
|-----------|---------|--------|
| NLP model | Fine-tuned `fr_core_news_lg` on domain corpus | Higher base accuracy |
| Confidence scores | Calibration layer added | Meaningful 0.0-1.0 scores |
| Coreference | Pronoun + context resolution added | Better entity grouping |
| Validation mode | Optional `--no-validate` flag | New workflow option |
| CLI/GUI | Confidence display, auto-accept threshold | UI enhancements |

---

## Epic 9 Story List

| Story | Priority | Est. Duration | Source | Status |
|-------|----------|---------------|--------|--------|
| 9.1: Ground-Truth Corpus Expansion | HIGH | 2-3 weeks | FE-012 prerequisite | Draft |
| 9.2: Fine-Tuned French NER Model | HIGH | 2-3 weeks | Epic 6 deferred | Draft |
| 9.3: Confidence Score Calibration | HIGH | 1-2 weeks | FE-013 | Draft |
| 9.4: Extended Coreference Resolution (Beta) | MED | 1-2 weeks | FE-014 | Draft |
| 9.5: Optional Validation Mode | MED | 1 week | Epic 6 deferred | Draft |
| 9.6: v3.0 Release Preparation | HIGH | 1-2 days | — | Draft |

**Total Estimated Duration:** 8-12 weeks

---

## Story 9.1: Ground-Truth Corpus Expansion

**As a** data scientist training a fine-tuned NER model,
**I want** a large, high-quality annotated French corpus of domain-specific documents,
**so that** the fine-tuned model learns from representative, accurately labeled data.

**Priority:** HIGH — Blocks Story 9.2 (model training). Garbage in, garbage out.

### Context

The current test corpus has ~1,855 annotated entities across ~30 documents. For effective fine-tuning, we need 5,000-10,000+ annotated entities across diverse document types. Quality matters more than quantity — Story 4.4 and FE-012 identified annotation inconsistencies that must be resolved before training.

### Acceptance Criteria

1. **AC1:** Existing corpus cleaned (FE-012 items if not completed in v2.1):
   - Annotation count discrepancy resolved
   - board_minutes.json garbage entries removed
   - Consistent title inclusion policy applied
2. **AC2:** Corpus expanded to 50-100 documents covering:
   - Interview transcripts (primary use case)
   - HR documents (employee records, evaluations)
   - Legal/compliance documents (contracts, policies)
   - Academic texts (research reports, meeting minutes)
   - Business correspondence (emails, memos)
3. **AC3:** Minimum 5,000 annotated entities across all documents
4. **AC4:** Entity type distribution: PERSON (50%+), LOCATION (25%+), ORG (20%+)
5. **AC5:** Annotation guidelines document created:
   - Clear rules for title inclusion/exclusion
   - Compound name boundary policy
   - Organization abbreviation handling
   - Location granularity (city vs region vs country)
6. **AC6:** Inter-annotator agreement measured (if multiple annotators): Cohen's kappa >= 0.8
7. **AC7:** Train/dev/test split defined: 70/15/15 or 80/10/10
8. **AC8:** Corpus stored in spaCy-compatible format (DocBin or JSON-lines)
9. **AC9:** Annotation tooling documented (prodigy, doccano, or manual process)

### Deliverables

- `data/training/` — annotated corpus in spaCy format
- `data/training/README.md` — corpus statistics, annotation guidelines, split info
- `data/training/guidelines.md` — detailed annotation guidelines

### Resourcing Note

**This story requires dedicated annotation labor — it cannot be done "on the side."** Expanding from ~1,855 to 5,000+ entities means ~3,000+ new annotations. At ~100 annotations/hour (realistic for careful NER annotation with review), that's 30+ hours of pure annotation work, plus document sourcing, quality review, and format conversion.

**Annotator options:**
- **Primary:** Use spaCy's `ner.correct` recipe with the existing model to pre-annotate, then manually correct (2-3x faster than manual annotation from scratch)
- **Secondary:** Leverage v1.x/v2.x user validation data (accepted/rejected entities) as semi-automated annotations — requires user consent and data pipeline
- **Seed:** Existing test corpus as starting point

**Who annotates?** This must be assigned before the epic starts. Options: (a) dedicated annotation sprint by the team, (b) external annotator with French NER experience, (c) crowdsourced via Prolific/MTurk with French speakers. Budget and availability must be confirmed.

### Estimated Effort: 2-3 weeks (annotation-labor-bound, not engineering-bound)

---

## Story 9.2: Fine-Tuned French NER Model

**As a** user processing French documents,
**I want** the NER engine to detect entities with 70-85% F1 accuracy,
**so that** fewer entities are missed and I spend less time adding entities manually during validation.

**Priority:** HIGH — The core deliverable of this epic

### Context

spaCy supports fine-tuning pre-trained models on custom data via `spacy train`. The approach:
1. Start from `fr_core_news_lg` (pre-trained French model)
2. Fine-tune the NER component on the domain-specific corpus (Story 9.1)
3. Evaluate on held-out test set
4. Package as a custom model that replaces or supplements `fr_core_news_lg`

### Acceptance Criteria

1. **AC1:** Fine-tuning pipeline configured:
   - `spacy train` config file with NER component
   - Training from `fr_core_news_lg` base model
   - Hyperparameter tuning (learning rate, dropout, batch size)
2. **AC2:** Model achieves target accuracy on held-out test set:
   - **Hard gate:** Overall F1 >= 70% (combined hybrid: fine-tuned model + regex). If this is not met, the model is not shipped — expand corpus and retrain.
   - **Stretch goal:** Overall F1 >= 85%
   - PERSON F1 >= 85%
   - LOCATION F1 >= 70%
   - ORG F1 >= 55%
   - **Measurement note:** Report both standalone model F1 and hybrid (model + regex) F1. The hybrid number is what users experience; the standalone number measures model improvement in isolation.
3. **AC3:** No regression on general French NER tasks (evaluate on standard benchmarks)
4. **AC4:** Model packaged as installable Python package (`gdpr-pseudonymizer-model-fr`)
5. **AC5:** Model loading integrated into existing pipeline:
   - Auto-detect custom model if installed; fall back to `fr_core_news_lg`
   - CLI flag: `--model custom` / `--model default`
   - GUI setting: model selection dropdown
6. **AC6:** Model size acceptable: < 600MB (same order as `fr_core_news_lg`)
7. **AC7:** Training reproducible: random seed, config file, and corpus version documented
8. **AC8:** Performance: inference time within 2x of base model (no major slowdown)
9. **AC9:** Accuracy report updated with fine-tuned model results
10. **AC10:** CI pipeline includes model evaluation step (accuracy regression detection)

### Integration Points

- `gdpr_pseudonymizer/nlp/detector.py` — model loading logic
- `gdpr_pseudonymizer/nlp/` — training scripts and config
- `pyproject.toml` — optional dependency for custom model
- CI — model evaluation workflow

### Risk Note

Fine-tuning success depends heavily on corpus quality (Story 9.1) and domain match. If the corpus is too small or unrepresentative, accuracy gains may be marginal. Mitigation: evaluate on dev set frequently during training; abort and expand corpus if gains plateau below 65% F1.

### Estimated Effort: 2-3 weeks

---

## Story 9.3: Confidence Score Calibration

**As a** user reviewing detected entities,
**I want** each entity to have a meaningful confidence score (0.0-1.0) where higher scores reliably indicate higher precision,
**so that** I can auto-accept high-confidence entities and focus validation effort on uncertain detections.

**Priority:** HIGH — Enables Story 9.5 (optional validation mode)

### Context

Story 4.4 found that 83.8% of entities have `confidence=None` (spaCy entities lack meaningful scores) and the remaining 16.2% (regex detections) have counterintuitive precision distributions. A dedicated calibration layer is needed to produce reliable confidence scores for all entities regardless of detection source.

### Acceptance Criteria

1. **AC1:** All detected entities receive a calibrated confidence score (0.0-1.0)
2. **AC2:** Confidence is monotonically correlated with precision (validated on held-out test set):
   - Entities with confidence >= 0.9 have precision >= 95%
   - Entities with confidence >= 0.7 have precision >= 80%
   - Entities with confidence < 0.3 have precision < 50%
   - **Statistical note:** With a 15% test split of 5,000 entities (~750 test entities), per-bucket sample sizes may be small. Report 95% confidence intervals alongside point estimates. If intervals are too wide to verify the thresholds above, either (a) expand the test set or (b) relax to "directionally monotonic" (rank correlation >= 0.8) rather than hard precision thresholds per bucket.
3. **AC3:** Calibration model trained on ground-truth corpus:
   - Features: entity text, entity type, detection source (spaCy/regex/both), surrounding context, entity length, capitalization pattern
   - Method: logistic regression or gradient boosted classifier
4. **AC4:** Calibration model integrated into detection pipeline:
   - Runs after entity detection, before validation
   - Adds `calibrated_confidence` field to `DetectedEntity`
5. **AC5:** GUI displays confidence:
   - Color intensity or icon in entity panel indicates confidence level
   - Tooltip shows exact confidence value
   - Sortable by confidence in entity list
6. **AC6:** CLI displays confidence in validation UI (Rich-based)
7. **AC7:** Auto-accept threshold configurable:
   - CLI: `--auto-accept-threshold 0.9`
   - GUI: Settings slider for auto-accept threshold
   - Default: disabled (0.0 — no auto-accept)
8. **AC8:** Auto-accepted entities clearly marked as "auto-accepted" (distinguishable from user-accepted)
9. **AC9:** Calibration model size < 5MB (lightweight)
10. **AC10:** Unit tests for calibration accuracy, threshold logic, and UI display

### Integration Points

- `gdpr_pseudonymizer/nlp/confidence.py` — new calibration module
- `gdpr_pseudonymizer/nlp/detector.py` — calibration step after detection
- `gdpr_pseudonymizer/nlp/models.py` — `calibrated_confidence` field on `DetectedEntity`
- `gdpr_pseudonymizer/gui/widgets/entity_panel.py` — confidence display
- `gdpr_pseudonymizer/validation/` — auto-accept logic

### Estimated Effort: 1-2 weeks

---

## Story 9.4: Extended Coreference Resolution (Beta/Experimental)

**As a** user validating entities in interview transcripts,
**I want** pronoun references ("il", "elle") and contextual mentions to be linked to their referenced entities,
**so that** all references to a person are pseudonymized consistently — even indirect ones.

**Priority:** MEDIUM — Improves quality for interview/narrative documents
**Feature Status:** Beta/Experimental — French coreference is a hard NLP problem. Ship as opt-in with clear "experimental" labeling in UI.

### Context

Story 4.6 implemented basic variant grouping (suffix matching, title stripping, preposition stripping). This story extends grouping to full coreference resolution — linking pronouns and contextual references to their antecedent entities. This is particularly important for interview transcripts where subjects are frequently referred to by pronoun after initial mention.

### Acceptance Criteria

1. **AC1:** French pronoun resolution: "il"/"elle"/"lui"/"leur" linked to nearest compatible PERSON entity (gender/number agreement). **Precision caveat:** "nearest compatible" is a heuristic — in complex text with multiple characters, precision will degrade. Accept ~70% precision as v3.0 target; do not block release on coreference accuracy.
2. **AC2:** Possessive resolution: "son bureau"/"sa collegue" linked to antecedent PERSON
3. **AC3:** Cross-sentence entity linking: "Le directeur" linked to previously named director entity
4. **AC4:** Coreference chains visible in validation UI:
   - Entity panel shows linked references under parent entity
   - Accepting parent entity auto-accepts all coreference links
5. **AC5:** Coreference resolution is optional and **off by default** (opt-in via `--coreference` CLI flag or GUI settings toggle labeled "Experimental: Coreference Resolution")
6. **AC6:** Performance: coreference adds < 5s to processing time per document
7. **AC7:** No regression in existing variant grouping behavior
8. **AC8:** Accuracy: coreference precision >= 70% (acceptable false link rate)
9. **AC9:** Unit and integration tests for pronoun resolution, possessive linking, and cross-sentence chaining

### Implementation Notes

Two approaches to evaluate:
- **spaCy-based:** Use `coreferee` or `crosslingual-coreference` spaCy components
- **Rule-based:** Gender/number agreement rules for French pronouns + proximity heuristics

Recommend starting with rule-based approach for French-specific accuracy, with spaCy component as enhancement.

### Integration Points

- `gdpr_pseudonymizer/nlp/coreference.py` — new coreference resolution module
- `gdpr_pseudonymizer/nlp/entity_grouping.py` — extended grouping with coreference chains
- `gdpr_pseudonymizer/gui/widgets/entity_panel.py` — coreference chain display
- `gdpr_pseudonymizer/core/processor.py` — coreference step in pipeline

### Estimated Effort: 1-2 weeks

---

## Story 9.5: Optional Validation Mode

**As a** user who processes routine documents with high-confidence entity detection,
**I want** to skip the validation step entirely and trust the automated pseudonymization,
**so that** I can process documents in seconds instead of minutes when accuracy is sufficient.

**Priority:** MEDIUM — Gated on accuracy improvements from Stories 9.2-9.3

### Context

Currently validation is mandatory (`--validate` is the only mode). This story adds `--no-validate` as an option, but ONLY when the fine-tuned model (Story 9.2) and confidence calibration (Story 9.3) provide sufficient accuracy. The threshold for enabling no-validation mode is F1 >= 70% with calibrated confidence.

### Acceptance Criteria

1. **AC1:** CLI flag: `--no-validate` / `--skip-validation` skips the validation step entirely
2. **AC2:** GUI toggle: "Mode automatique (sans validation)" in processing options
3. **AC3:** Guard rail: `--no-validate` emits a warning if the custom fine-tuned model is NOT installed:
   - "Warning: Skipping validation with the default model (F1 ~60%) may result in missed entities. Consider installing the fine-tuned model for better accuracy."
4. **AC4:** Guard rail: `--no-validate` logs all auto-decisions to audit trail:
   - Entity text, type, confidence, decision (auto-accepted), timestamp
5. **AC5:** Summary report after no-validate processing:
   - "Processed X entities automatically. Y entities had confidence < 0.5 (review recommended)."
   - List of low-confidence entities for optional review
6. **AC6:** Batch mode integration: `--no-validate` works with batch processing
7. **AC7:** GUI shows post-processing summary with option to "Review low-confidence entities" (opens validation screen with only low-confidence entities)
8. **AC8:** No regression in existing validated processing mode
9. **AC9:** Documentation clearly explains when to use no-validate vs validated mode
10. **AC10:** Unit and integration tests for no-validate pipeline, guard rails, and summary report

### Integration Points

- `gdpr_pseudonymizer/core/processor.py` — conditional validation step
- `gdpr_pseudonymizer/cli/commands/process.py` — `--no-validate` flag
- `gdpr_pseudonymizer/gui/screens/home.py` — automatic mode toggle
- `gdpr_pseudonymizer/data/audit_logger.py` — auto-decision logging

### Estimated Effort: 1 week

---

## Story 9.6: v3.0 Release Preparation

**As a** product manager,
**I want** v3.0.0 published as a major release with the fine-tuned model, confidence calibration, and optional validation,
**so that** users experience a step-change in pseudonymization quality.

**Priority:** HIGH — Gates the release

### Acceptance Criteria

1. **AC1:** Version bumped to `3.0.0` in `pyproject.toml`
2. **AC2:** CHANGELOG.md updated with v3.0.0 section — major release
3. **AC3:** README updated: accuracy improvements, new model, confidence scores, optional validation
4. **AC4:** README.fr.md mirrored
5. **AC5:** Accuracy report updated with fine-tuned model benchmarks
6. **AC6:** Full regression suite passing
7. **AC7:** Fine-tuned model package published (PyPI or GitHub Releases)
8. **AC8:** Standalone executables built with fine-tuned model bundled
9. **AC9:** Git tag `v3.0.0` triggers release workflow
10. **AC10:** Migration guide: how to install/use the fine-tuned model
11. **AC11:** Release announcement highlights accuracy improvement narrative

### Estimated Effort: 1-2 days

---

## Execution Sequence

```
Story 9.1 (Corpus Expansion)          --- Week 1-3 ---    Blocks model training
Story 9.2 (Fine-Tuned Model)          --- Week 3-6 ---    Depends on 9.1
Story 9.3 (Confidence Calibration)    --- Week 5-7 ---    Can start during 9.2 (uses same corpus)
Story 9.4 (Coreference Resolution)    --- Week 5-7 ---    Independent of 9.2/9.3
Story 9.5 (Optional Validation)       --- Week 7-8 ---    Depends on 9.2 + 9.3
Story 9.6 (Release Prep)              --- Week 8-9 ---    Release gate
```

**Critical Path:** 9.1 -> 9.2 -> 9.5 -> 9.6 (corpus -> model -> optional validation -> release)

**Parallelization:** Stories 9.3 and 9.4 can run in parallel with each other and partially overlap with 9.2.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Corpus too small for meaningful fine-tuning | MEDIUM | HIGH | Set minimum 5,000 entities; use data augmentation; monitor dev set gains early |
| Fine-tuning plateaus below 70% F1 | MEDIUM | HIGH | Evaluate at 65% — if stuck, consider alternative models (CamemBERT, FlauBERT) |
| Confidence calibration overfits to training data | MEDIUM | MEDIUM | Validate on held-out test set; use cross-validation |
| Coreference resolution adds latency | LOW | MEDIUM | Make optional; profile and optimize; set 5s budget |
| No-validate mode used inappropriately | MEDIUM | LOW | Guard rails, warnings, audit logging; default remains validated |
| Custom model distribution complexity | MEDIUM | MEDIUM | Package as pip-installable; bundle in standalone executables |

---

## Definition of Done

- [ ] All 6 stories completed with acceptance criteria met
- [ ] Fine-tuned model achieves F1 >= 70% on held-out test set
- [ ] Confidence scores are calibrated and monotonically correlated with precision
- [ ] Optional validation mode works end-to-end with guard rails
- [ ] All quality gates green: black, ruff, mypy, pytest
- [ ] Test count >= v2.2 baseline, coverage >= 86%
- [ ] No regression in existing CLI and GUI workflows
- [ ] v3.0.0 published on PyPI and GitHub Releases
- [ ] Fine-tuned model package available for installation
- [ ] Documentation updated (EN + FR)

---

## Explicitly Deferred (v3.1+)

| Item | Reason | Target |
|------|--------|--------|
| Multi-language NER (EN, ES, DE) | Requires per-language corpus, model, pseudonym libraries | v3.1 |
| Mobile app | Different platform entirely | v4.0+ |
| Scanned PDF OCR | Requires OCR pipeline integration | v3.1+ |
| Silent auto-update (self-replacing binary) | Code-signing complexity | v3.1+ |
| Active learning pipeline | Requires user consent and data collection infrastructure | v3.1+ |

---

## Success Criteria

Epic 9 is successful if:

1. Fine-tuned model achieves measurable accuracy improvement (F1 >= 70%)
2. Confidence scores enable meaningful auto-accept (precision >= 95% at threshold 0.9)
3. Users can optionally skip validation for routine documents
4. Coreference resolution reduces missed pronoun references in interview transcripts
5. No regression in existing validated processing mode
6. v3.0.0 published and fine-tuned model available

---

## Architect Feasibility Review

**Reviewed by:** Winston (Architect) — 2026-03-06
**Verdict:** GO WITH PRECONDITIONS — Annotator resourcing (9.1) gates everything; model accuracy is uncertain

### Story-Level Assessment

| Story | Feasibility | Notes |
|-------|------------|-------|
| 9.1 Corpus Expansion | Yellow/Red | Not an engineering problem — it's a resourcing problem. 3,000+ new annotations at ~100/hour = 30+ hours of annotation labor. **Who annotates?** Must be answered before epic start. The `ner.correct` pre-annotation approach (2-3x speedup) is the right call. |
| 9.2 Fine-Tuned Model | Yellow | `spacy train` is well-documented. The architecture already has `EntityDetector` as an ABC with `load_model()` — swapping models is supported by design. Model distribution as a separate pip package is clean. **Risk:** with only 5,000 entities, gains may be modest. The 70% F1 hard gate is appropriate. |
| 9.3 Confidence Calibration | Green/Yellow | `DetectedEntity` already has a `confidence` field (currently `None` for spaCy, ~0.5-0.65 for regex). Adding a calibration layer slots in cleanly after detection. Logistic regression on features (source, type, length, context) is straightforward. Statistical caveats in PRD about per-bucket sample sizes are important. |
| 9.4 Coreference (Beta) | Yellow | French coreference is genuinely hard. `coreferee` has limited French support. Rule-based gender/number agreement is more predictable but labor-intensive. Correctly scoped as opt-in/experimental. 70% precision target is realistic for rule-based. |
| 9.5 Optional Validation | Green | Conditional skip of validation step — straightforward plumbing once 9.2+9.3 deliver. Guard rails and audit logging are good design. |
| 9.6 Release | Green | Bundling a ~500MB custom model in standalone executables will increase build size significantly. CI build workflow (Story 6.10) already handles large builds but budget extra disk/time. |

### Recommendation 1: Validate Fine-Tuning Viability Early

**Before committing to the full epic, run a quick experiment.** Take the current ~1,855 entities, do an 80/10/10 split, fine-tune `fr_core_news_lg`, and measure the delta. If you see meaningful gains even on small data, it validates the approach and gives confidence that corpus expansion will pay off. If gains are flat, you know you need significantly more data (10,000+) and can plan accordingly. This experiment costs 1-2 days and de-risks the entire epic.

### Recommendation 2: Descope Coreference (Story 9.4)

**Limit v3.0 to pronoun-only resolution.** Cross-sentence role-based linking ("le directeur" -> previously named director) is a research-level problem with low precision in practice. Ship pronoun gender/number agreement (il/elle/lui/leur -> nearest compatible PERSON) as the v3.0 beta feature. Defer role-based and cross-sentence linking to v3.1 where it can be evaluated with real user feedback on the pronoun resolution quality.

### Recommendation 3: Confidence Calibration Test Set Size

With a 15% test split of 5,000 entities (~750 test entities), per-bucket precision estimates will have wide confidence intervals. If the experiment from Recommendation 1 shows you need 10,000+ entities for model training, allocate proportionally more to the test set as well. Alternatively, use k-fold cross-validation on the calibration model to get tighter estimates without sacrificing training data.

---

**Document Status:** REVIEWED
**Created:** 2026-03-06
**Author:** Sarah (Product Owner)
**Reviewed by:** John (PM) — 2026-03-06
**Review Notes:** Approved with modifications: annotator resourcing note added to 9.1 (biggest risk), F1 70% set as hard gate in 9.2, confidence calibration statistical caveats added to 9.3, coreference downgraded to beta/experimental and opt-in by default in 9.4, major version rationale documented. **Key blocker:** annotator assignment must be confirmed before epic start.
