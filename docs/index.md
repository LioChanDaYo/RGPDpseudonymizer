# GDPR Pseudonymizer

**AI-Assisted Pseudonymization for French Documents with Human Verification**

Transform sensitive French documents for safe AI analysis with local processing, mandatory human review, and GDPR compliance.

---

## What is GDPR Pseudonymizer?

GDPR Pseudonymizer is a **privacy-first CLI tool** that combines AI efficiency with human accuracy to pseudonymize French text documents. Unlike fully automatic tools or cloud services, it prioritizes **zero false negatives** and **legal defensibility** through mandatory validation workflows.

**Perfect for:**

- **Privacy-conscious organizations** needing GDPR-compliant AI analysis
- **Academic researchers** with ethics board requirements
- **Legal/HR teams** requiring defensible pseudonymization
- **LLM users** who want to analyze confidential documents safely

---

## Key Features

### Privacy-First Architecture

- **100% local processing** -- your data never leaves your machine
- **No cloud dependencies** -- works completely offline after installation
- **Encrypted mapping tables** -- AES-256-SIV encryption, passphrase-protected
- **Zero telemetry** -- no analytics or external communication

### AI + Human Verification

- **Hybrid detection** -- AI pre-detects ~60% of entities (NLP + regex + geography dictionary, F1 59.97%)
- **Mandatory validation** -- you review and confirm all entities (ensures 100% accuracy)
- **Fast validation UI** -- keyboard shortcuts, batch operations, <2 min per document
- **Entity variant grouping** -- related forms ("Marie Dubois", "Pr. Dubois", "Dubois") merged into one validation item

### Batch Processing

- **Consistent pseudonyms** -- same entity = same pseudonym across all documents
- **Compositional matching** -- "Marie Dubois" and "Marie" resolve consistently
- **Selective entity processing** -- `--entity-types` flag to filter by type (PERSON, LOCATION, ORG)
- **50%+ time savings** vs manual redaction

### Themed Pseudonyms

Three built-in themes: **Neutral** (French names), **Star Wars**, and **Lord of the Rings**.

---

## Quick Start

```bash
# Install from PyPI
pip install gdpr-pseudonymizer
python -m spacy download fr_core_news_lg

# Process a document
gdpr-pseudo process interview.txt
```

See the [Installation Guide](installation.md) for detailed platform-specific instructions and the [Tutorial](tutorial.md) for step-by-step workflows.

---

## Documentation

| Section | Description |
|---------|-------------|
| [Installation](installation.md) | Platform-specific setup (Windows, macOS, Linux, Docker) |
| [Tutorial](tutorial.md) | Step-by-step usage tutorials and workflows |
| [CLI Reference](CLI-REFERENCE.md) | Complete command documentation |
| [FAQ](faq.md) | Common questions and answers |
| [Troubleshooting](troubleshooting.md) | Error reference and solutions |
| [Methodology](methodology.md) | Technical approach, GDPR compliance, academic citation |
| [API Reference](api-reference.md) | Module documentation for developers |

---

## How It Works

1. **Detect** -- Hybrid NLP + regex identifies candidate entities in French text
2. **Validate** -- You review each entity with surrounding context
3. **Pseudonymize** -- Confirmed entities are replaced with themed pseudonyms
4. **Store** -- Mappings encrypted in local database for consistency and reversibility

---

## GDPR Compliance

GDPR Pseudonymizer supports compliance with Articles 4(5), 25, 30, 32, and 89 of the General Data Protection Regulation. See the [Methodology](methodology.md) document for the full compliance mapping.

**Important:** Pseudonymized data is still personal data under GDPR. Consult your Data Protection Officer for specific compliance guidance.

---

## Status

**Current version:** v1.0.7 (February 2026)

**Supported:** Python 3.10-3.12 | Windows, macOS, Linux | .txt and .md formats | French language

See the [FAQ](faq.md) for the product roadmap.
