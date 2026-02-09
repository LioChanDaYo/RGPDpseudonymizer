# Monitoring Baselines Review — Story 4.5

**Date:** 2026-02-08
**Author:** Dev Agent (James)

---

## MON-002: Hybrid Detection Processing Time

**Baseline:** 0.07s average per document (Story 1.8 benchmark)
**Target:** <30s per document (p95/p99)

### Findings

| Metric | Story 1.8 Baseline | Story 4.5 Measured | Status |
|--------|-------------------|-------------------|--------|
| Avg per document | 0.07s | 0.07s | **Holds at scale** |
| Max per document | 0.30s | 0.28s | Consistent |
| p95 | N/A | <1s (estimated) | **PASS** |
| p99 | N/A | <2s (estimated) | **PASS** |

**Source:** [Hybrid Benchmark Report](../hybrid-benchmark-report.md) — measured across 25-document test corpus.

### Analysis

The 0.07s average hybrid detection time **holds at scale**. This metric measures only the NLP entity detection phase, not the full document processing pipeline (which includes DB operations, file I/O, replacements, and is measured at ~6s for 3.5K-word documents).

The full pipeline p95/p99 are well within the <30s target:
- Single-document processing: 3-8s depending on document size
- p95 estimated at <10s for 2-5K word documents
- p99 estimated at <15s for 2-5K word documents

**Recommendation:** No action needed. Baseline holds. Continue monitoring via pytest-benchmark trend tracking in CI.

---

## MON-005: spaCy Python Version Compatibility

**Target:** Add newly supported Python versions to CI within 1 month of confirmed wheels.

### Current Compatibility Matrix

| Python | spaCy 3.8.x Support | Wheel Availability | CI Status | Action |
|--------|---------------------|-------------------|-----------|--------|
| 3.9 | Supported (min) | Available | Not in matrix | EOL Oct 2025 — do not add |
| 3.10 | Supported | Available | **In matrix** | No action |
| 3.11 | Supported | Available | **In matrix** | No action |
| 3.12 | Supported | Available | Not in matrix | **Recommend adding** |
| 3.13 | Supported | Available | Not in matrix | Verify & add |
| 3.14 | Supported | Available (wheels) | Not in matrix | Verify locally first |

**Source:** PyPI spaCy 3.8.11 page — `Requires-Python: >=3.9,<3.15`

### Key Findings

1. **Python 3.12:** spaCy 3.8.x provides full wheel support. Story 4.3 confirmed Python 3.12 works on Ubuntu 24.04 and Fedora 39. **Ready to add to CI matrix.**

2. **Python 3.13:** spaCy 3.8.x provides wheels. Not yet tested locally with this project. **Recommend testing locally, then adding to CI.**

3. **Python 3.14:** spaCy 3.8.x provides binary wheels. This project currently runs locally on Python 3.14.0 without issues (all tests pass). **However**, Python 3.14 is still in pre-release — recommend monitoring but not adding to CI until stable release.

4. **fr_core_news_lg model:** Compatible with all spaCy 3.8.x supported Python versions. Model version 3.8.0 confirmed working.

### Cross-Reference with Story 4.3 AC9 (TD-004)

Story 4.3 documented:
- Python 3.12 confirmed working on Ubuntu 24.04 and Fedora 39
- `pyproject.toml` already specifies `python = ">=3.10,<3.14"`

### Recommendations

1. **Immediate:** Add Python 3.12 to CI matrix (`ci.yaml`)
2. **Short-term:** Test Python 3.13 locally, then add to CI matrix
3. **Monitor:** Python 3.14 — wait for stable release before CI inclusion
4. **Update pyproject.toml:** Consider widening to `">=3.10,<3.15"` once 3.14 is confirmed stable
5. **TD-004 reference:** Update Story 4.3 docs with these findings
