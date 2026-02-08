# Frequently Asked Questions

**GDPR Pseudonymizer** - Common questions and answers

---

## Accuracy and Detection

### What accuracy should I expect from the automatic detection?

The hybrid detection pipeline (NLP + regex) automatically identifies approximately 40-50% of entities in French text. This is a pre-filtering step -- **you review and confirm every entity** during the mandatory validation workflow.

After human validation, accuracy is **100%** because you control the final decision for every entity.

### Why is the NER accuracy so low?

The spaCy `fr_core_news_lg` model was trained primarily on news text, not interview transcripts or business documents. Domain-specific language patterns (conversational registers, mixed formality) reduce out-of-the-box accuracy. A benchmark on 25 French documents with 1,855 entities measured 29.5% F1 for spaCy alone, improving to ~40-50% with the hybrid approach.

Fine-tuning with real-world validation data is planned for v3.0 (targeting 70-85% F1).

### Why is validation mandatory?

Because the AI detection misses entities. With ~40-50% recall, roughly half of entities would go undetected without human review. For GDPR compliance, missing even one personal data entity could constitute a data breach. Mandatory validation ensures **zero false negatives**.

---

## Document Formats and Languages

### What document formats are supported?

v1.0 supports:
- **Plain text** (`.txt`)
- **Markdown** (`.md`)

PDF, DOCX, HTML, and other formats are not supported in v1.0. Convert files to plain text before processing.

### Can I use this for non-French documents?

No. v1.0 is designed exclusively for French-language text. The NLP model (`fr_core_news_lg`), regex patterns, and pseudonym libraries are all French-specific.

Multi-language support (English, Spanish, German) is planned for v3.0.

### What languages are supported?

French only in v1.0. The tool uses spaCy's `fr_core_news_lg` model trained specifically on French text.

---

## GDPR Compliance

### Is this tool GDPR compliant?

GDPR Pseudonymizer **supports** GDPR compliance but does not guarantee it by itself. The tool implements:

- **Article 4(5):** Pseudonymization with separate encrypted mapping storage
- **Article 25:** Data protection by design (100% local processing, encrypted storage)
- **Article 32:** Security measures (AES-256-SIV encryption, PBKDF2 key derivation)
- **Article 30:** Processing records (comprehensive audit logging with export)

**Important:** Pseudonymized data is still personal data under GDPR (Recital 26). You remain the data controller and should consult your Data Protection Officer for specific compliance guidance.

See [Methodology](methodology.md) for the full GDPR compliance mapping.

### Is pseudonymization the same as anonymization?

No. **Pseudonymization** replaces identifying information with pseudonyms but remains reversible (with the mapping table and passphrase). Pseudonymized data is still personal data under GDPR.

**Anonymization** irreversibly removes all identifying information so re-identification is impossible. GDPR does not apply to truly anonymous data.

GDPR Pseudonymizer performs pseudonymization, not anonymization. This is by design -- many use cases require reversibility (academic research follow-ups, legal proceedings, audit requirements).

### Does my data leave my machine?

No. All processing happens locally. There are no cloud dependencies, API calls, telemetry, or network communication. After initial installation (downloading the spaCy model), the tool works completely offline.

---

## Comparison with Alternatives

### How does this compare to manual redaction?

| Aspect | Manual Redaction | GDPR Pseudonymizer |
|--------|-----------------|---------------------|
| **Time per document** | 15-30 minutes | 2-5 minutes (AI pre-detection + validation) |
| **Accuracy** | Human error prone | 100% (mandatory validation) |
| **Consistency** | Difficult across documents | Guaranteed (same entity = same pseudonym) |
| **Reversibility** | Not possible | Yes (encrypted mapping table) |
| **Audit trail** | Manual logging | Automatic (operation logging, JSON/CSV export) |
| **Cost for 50 documents** | 16-25 hours | 2-3 hours |

### How does this compare to cloud pseudonymization services?

| Aspect | Cloud Services | GDPR Pseudonymizer |
|--------|---------------|---------------------|
| **Data location** | Third-party servers | 100% local |
| **Privacy risk** | Data exposure to provider | Zero (no network) |
| **Cost** | Per-document or subscription | Free (open source) |
| **Accuracy** | Varies (often no validation) | 100% (mandatory validation) |
| **Customization** | Limited | Full (themed pseudonyms, config files) |
| **Internet required** | Always | Only for installation |

### How does this compare to fully automatic tools?

| Aspect | Automatic Tools | GDPR Pseudonymizer |
|--------|----------------|---------------------|
| **Human oversight** | None | Mandatory |
| **Accuracy** | Depends on NLP (often 70-90%) | 100% (human validated) |
| **Speed** | Faster (no validation) | Slower but more accurate |
| **GDPR defensibility** | Weaker (no human audit trail) | Stronger (documented human review) |
| **False negatives** | Possible | Zero (by design) |

---

## Roadmap

### What's planned for future versions?

**v1.0 (Current - Q2 2026):** AI-assisted CLI with mandatory validation
- 100% local processing, encrypted mapping tables, audit trails
- French language, .txt/.md formats

**v1.1 (Q2-Q3 2026):** Quick wins and GDPR compliance
- GDPR Right to Erasure: selective entity deletion (`delete-mapping` command, Article 17)
- Gender-aware pseudonym assignment for French names
- Beta feedback bug fixes and UX improvements

**v2.0 (Q3-Q4 2026):** Desktop GUI
- Graphical interface wrapping CLI core (drag-and-drop, visual entity review)
- Standalone executables (.exe, .app) -- no Python required
- French-first UI with internationalization architecture

**v3.0 (2027+):** NLP accuracy and automation
- Fine-tuned French NER model (70-85% F1 target)
- Optional `--no-validate` flag for high-confidence workflows
- Multi-language support (English, Spanish, German)

### Will there be a GUI version?

Yes. v2.0 (planned Q3-Q4 2026) will include a desktop GUI with drag-and-drop document processing, visual entity review, and standalone executables that don't require Python installation. The target audience is non-technical users (HR, legal, compliance teams).

### Can I contribute?

Not yet. The project is in pre-release development. After v1.0 MVP launch, contributions will be welcome for bug reports, documentation improvements, translations, and feature suggestions.

GitHub: https://github.com/LioChanDaYo/RGPDpseudonymizer

---

## Technical Questions

### What NLP model is used?

spaCy `fr_core_news_lg` (version 3.8.0), a large French language model (~571MB). It was selected after benchmarking against Stanza, achieving 2.5x better F1 score on the test corpus.

### How is the mapping database encrypted?

AES-256-SIV (deterministic authenticated encryption per RFC 5297) with PBKDF2-HMAC-SHA256 key derivation (210,000 iterations). Each database has a unique cryptographically random 32-byte salt. The passphrase is never stored on disk.

### What happens if I forget my passphrase?

The mapping database cannot be decrypted without the correct passphrase. This means:
- Existing pseudonym mappings are permanently inaccessible
- You cannot reverse pseudonymization on previously processed documents
- You must create a new database (`poetry run gdpr-pseudo init --force`)

**Recommendation:** Store your passphrase in a secure password manager.

### Can I use different themes for the same project?

Technically yes, but it's not recommended. Different themes produce different pseudonyms for the same entity, creating inconsistencies. If you must switch themes, use a separate database for each theme.

---

## Related Documentation

- [Installation Guide](installation.md) - Setup instructions
- [Usage Tutorial](tutorial.md) - Step-by-step tutorials
- [CLI Reference](CLI-REFERENCE.md) - Complete command documentation
- [Methodology](methodology.md) - Technical approach and GDPR compliance
- [Troubleshooting](troubleshooting.md) - Error reference and solutions
