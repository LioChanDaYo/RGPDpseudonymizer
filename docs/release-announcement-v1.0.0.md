# GDPR Pseudonymizer v1.0.0 — Public Release

**Pseudonymize French documents for safe AI analysis. Local processing. Human verification. GDPR compliance.**

---

## The Problem

Organizations across Europe face a dilemma: they need AI-powered analysis of sensitive documents (interviews, HR records, legal texts), but GDPR prohibits sending personal data to cloud services like ChatGPT without proper safeguards. Manual redaction is slow, error-prone, and destroys document coherence.

## The Solution

**GDPR Pseudonymizer** is a privacy-first CLI tool that replaces real names, locations, and organizations with themed pseudonyms — locally, with mandatory human review, producing documents that remain readable and analyzable by LLMs.

Unlike cloud-based redaction tools or fully automatic approaches, GDPR Pseudonymizer keeps all data on your machine and ensures 100% accuracy through human-in-the-loop validation.

## Key Features

- **100% local processing** — No cloud dependencies, no telemetry, no data leaves your machine
- **AI-assisted detection** — Hybrid NLP + regex pre-identifies ~40-50% of entities, saving time vs manual redaction
- **Mandatory human validation** — Rich CLI interface with keyboard shortcuts ensures zero false negatives
- **Themed pseudonyms** — Choose Neutral (French names), Star Wars, or Lord of the Rings themes for readable output
- **Batch processing** — Process 50+ documents with consistent pseudonyms across the entire set

## Getting Started

```bash
# Install from PyPI
pip install gdpr-pseudonymizer

# Download French language model
python -m spacy download fr_core_news_lg

# Pseudonymize a document
gdpr-pseudo process interview.txt
```

Full documentation: [https://liochandayo.github.io/RGPDpseudonymizer/](https://liochandayo.github.io/RGPDpseudonymizer/)

## Use Cases

### 1. Academic Research
Researchers with ethics board requirements can pseudonymize interview transcripts before AI analysis. The audit trail provides evidence of GDPR-compliant processing.

### 2. HR & Legal Teams
Pseudonymize employee feedback or legal documents before sending to LLM services. Reversible mappings allow authorized de-pseudonymization when needed.

### 3. Privacy-Conscious Organizations
Any team handling French-language personal data can use GDPR Pseudonymizer as part of their data protection workflow.

## What's Next

**v1.1 (Q2-Q3 2026):** GDPR Right to Erasure support, gender-aware pseudonym assignment, community feedback integration.

**v2.0 (Q3-Q4 2026):** Desktop GUI with drag-and-drop, standalone executables (no Python required), French-first UI.

**v3.0 (2027+):** Fine-tuned French NER model (70-85% F1 target), optional auto-processing mode, multi-language support.

## Get Involved

- **Try it:** `pip install gdpr-pseudonymizer`
- **Star the repo:** [https://github.com/LioChanDaYo/RGPDpseudonymizer](https://github.com/LioChanDaYo/RGPDpseudonymizer)
- **Report issues:** [GitHub Issues](https://github.com/LioChanDaYo/RGPDpseudonymizer/issues)
- **Ask questions:** [GitHub Discussions](https://github.com/LioChanDaYo/RGPDpseudonymizer/discussions)
- **Read the docs:** [https://liochandayo.github.io/RGPDpseudonymizer/](https://liochandayo.github.io/RGPDpseudonymizer/)

---

**License:** MIT | **Python:** 3.10-3.12 | **Platforms:** Windows, macOS, Linux | **Language:** French
