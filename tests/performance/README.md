# Performance Benchmarks

## Overview

Performance tests validate NFR1 (single-document <30s) and NFR2 (batch 50 docs <30min) using `pytest-benchmark`.

## Running Locally

```bash
# Run all benchmarks (requires spaCy model)
poetry run pytest tests/performance/ -v --benchmark-json=benchmark-results.json

# Run only benchmark tests (skip timing breakdown)
poetry run pytest tests/performance/ -v -m benchmark

# Limit benchmark duration
poetry run pytest tests/performance/ -v --benchmark-max-time=60

# Skip benchmarks (run other tests only)
poetry run pytest tests/ -v -p no:benchmark
```

## Benchmark Groups

| Group | File | What it measures |
|-------|------|------------------|
| `single-document` | `test_single_document_benchmark.py` | Full pipeline (NLP + DB + file I/O) for 2K/3.5K/5K word docs |
| `entity-detection` | `test_single_document_benchmark.py` | Hybrid NLP+regex detection only (isolates NLP regressions) |
| `batch` | `test_batch_performance.py` | 50-document batch processing throughput |

## Thresholds

- **NFR1**: Single document processing < 30 seconds
- **NFR2**: 50-document batch < 30 minutes (1800s)

## CI Integration

The Ubuntu 3.11 (primary) CI job runs benchmarks with `--benchmark-json=benchmark-results.json` and uploads the JSON as a build artifact for tracking.

Benchmarks are **not** run on Windows (spaCy segfault) or as separate CI jobs — they run alongside the test suite.

## Test Fixtures

- `tests/fixtures/performance/sample_2000_words.txt` — ~2K word French document
- `tests/fixtures/performance/sample_3500_words.txt` — ~3.5K word French document
- `tests/fixtures/performance/sample_5000_words.txt` — ~5K word French document
- Batch documents are generated at runtime (50 docs, deterministic seed)
