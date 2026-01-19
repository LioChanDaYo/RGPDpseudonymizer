# GDPR Pseudonymizer

**AI-Assisted Pseudonymization for French Documents with Human Verification**

Transform sensitive French documents for safe AI analysis with local processing, mandatory human review, and GDPR compliance.

---

## 🎯 Overview

GDPR Pseudonymizer is a **privacy-first CLI tool** that combines AI efficiency with human accuracy to pseudonymize French text documents. Unlike fully automatic tools or cloud services, we prioritize **zero false negatives** and **legal defensibility** through mandatory validation workflows.

**Perfect for:**
- 🏛️ **Privacy-conscious organizations** needing GDPR-compliant AI analysis
- 🎓 **Academic researchers** with ethics board requirements
- ⚖️ **Legal/HR teams** requiring defensible pseudonymization
- 🤖 **LLM users** who want to analyze confidential documents safely

---

## ✨ Key Features

### 🔒 **Privacy-First Architecture**
- ✅ **100% local processing** - Your data never leaves your machine
- ✅ **No cloud dependencies** - Works completely offline after installation
- ✅ **Encrypted mapping tables** - Reversible pseudonymization with passphrase protection
- ✅ **Zero telemetry** - No analytics, crash reporting, or external communication

### 🤝 **AI + Human Verification**
- ✅ **Hybrid detection** - AI pre-detects 40-50% of entities (NLP + regex patterns)
- ✅ **Mandatory validation** - You review and confirm all entities (ensures 100% accuracy)
- ✅ **Fast validation UI** - Keyboard-driven interface, <2 min per document
- ✅ **Batch actions** - Confirm/reject multiple entities efficiently

### 📊 **Batch Processing**
- ✅ **Consistent pseudonyms** - Same entity = same pseudonym across 10-100+ documents
- ✅ **Compositional matching** - "Marie Dubois" → "Leia Organa", "Marie" alone → "Leia"
- ✅ **50%+ time savings** vs manual redaction (AI pre-detection + validation)

### 🎭 **Themed Pseudonyms**
- ✅ **Readable output** - Star Wars, LOTR, or generic French names
- ✅ **Maintains context** - LLM analysis preserves ≥80% document utility
- ✅ **Gender-preserving** - When NER provides gender classification

---

## 🚀 Quick Start

**Status:** 🚧 **Pre-MVP Development** (Week 1/14 - Epic 1 in progress)

### Current Development Stage

We're actively developing v1.0 MVP with an **AI-assisted approach**:
- ✅ **Story 1.2 Complete:** NLP library benchmark (spaCy selected: 29.5% F1)
- 🔄 **Week 1-5 (Current):** Epic 1 - Foundation & Validation UI
- 📅 **Week 6-14:** Core engine, CLI polish, launch prep
- 🎯 **MVP Launch:** Week 14 (estimated Q2 2026)

### Realistic Expectations for v1.0

**What v1.0 delivers:**
- 🤖 **AI-assisted detection** - Hybrid NLP + regex detects ~40-50% of entities automatically
- ✅ **Mandatory human verification** - You review and confirm all entities (2-3 min per document)
- 🔒 **100% accuracy guarantee** - Human validation ensures zero false negatives
- ⚡ **50%+ faster than manual** - Pre-detection saves time vs pure manual redaction

**What v1.0 does NOT deliver:**
- ❌ Fully automatic "set and forget" processing
- ❌ 85%+ AI accuracy (current: 40-50% with hybrid approach)
- ❌ Optional validation mode (validation is mandatory)

### Roadmap

**v1.0 (MVP - Week 14):** AI-assisted with mandatory validation
- Target: Privacy-conscious early adopters who value human oversight

**v1.1 (Q2 2026):** Semi-automatic with optional validation
- Fine-tuned model: 70-85% F1 accuracy
- Optional `--no-validate` flag for high-confidence workflows

**v2.0 (Future):** Fully automatic with confidence thresholds
- 85%+ F1 accuracy
- Confidence-based auto-processing

---

## 📖 Documentation

**For Users:**
- 📘 [Installation Guide](docs/installation.md) *(Coming in Epic 3)*
- 📗 [Usage Tutorial](docs/tutorial.md) *(Coming in Epic 3)*
- 📕 [Methodology & Academic Citation](docs/methodology.md) *(Coming in Epic 4)*
- ❓ [FAQ](docs/faq.md) *(Coming in Epic 4)*

**For Developers:**
- 🏗️ [Architecture Documentation](docs/architecture/) *(In progress)*
- 📊 [NLP Benchmark Report](docs/nlp-benchmark-report.md) *(Complete)*
- 🎯 [Product Requirements (PRD)](docs/.ignore/prd.md) *(v2.0 - Updated 2026-01-16)*

**For Stakeholders:**
- 🎨 [Positioning & Messaging](docs/positioning-messaging-v2-assisted.md)
- 📋 [Deliverables Summary](docs/DELIVERABLES-SUMMARY-2026-01-16.md)

---

## 🔬 Technical Details

### NLP Library Selection (Story 1.2 - Completed)

After comprehensive benchmarking on 25 French interview/business documents (1,855 entities):

| Library | F1 Score | Precision | Recall | Decision |
|---------|----------|-----------|--------|----------|
| **spaCy** `fr_core_news_lg` | **29.5%** | 27.0% | 32.7% | ✅ **Selected** |
| **Stanza** `fr_default` | 11.9% | 10.3% | 14.1% | ❌ Rejected |

**Why both failed 85% target:**
- Pre-trained models optimized for news text (not interview/business docs)
- Domain-specific language patterns (conversational, mixed registers)
- ORG detection catastrophic (3.8% precision = 96% false positives)

**Approved Solution:**
- ✅ **Hybrid approach** (NLP + regex) targets 40-50% F1
- ✅ **Mandatory validation** ensures 100% final accuracy
- 📅 **Fine-tuning** deferred to v1.1 (70-85% F1 target)

See full analysis: [docs/nlp-benchmark-report.md](docs/nlp-benchmark-report.md)

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Runtime** | Python | 3.9+ | Cross-platform compatibility |
| **NLP Library** | spaCy | 3.8.0 | French entity detection (fr_core_news_lg) |
| **CLI Framework** | Typer | 0.9+ | Command-line interface |
| **Database** | SQLite | 3.35+ | Local mapping table storage |
| **Encryption** | cryptography (Fernet) | 41.0+ | Symmetric encryption for mappings |
| **Validation UI** | rich | 13.7+ | Interactive CLI entity review |
| **Testing** | pytest | 7.4+ | Unit & integration testing |
| **CI/CD** | GitHub Actions | N/A | Automated testing (Windows/Mac/Linux) |

---

## 🤔 Why AI-Assisted Instead of Automatic?

**Short answer:** Privacy and compliance require human oversight.

**Long answer:**
1. **GDPR defensibility** - Human verification provides legal audit trail
2. **Zero false negatives** - AI misses entities, humans catch them (100% coverage)
3. **Current NLP limitations** - French models on interview/business docs: 29.5% F1 out-of-box
4. **Better than alternatives:**
   - ✅ **vs Manual redaction:** 50%+ faster (AI pre-detection)
   - ✅ **vs Cloud services:** 100% local processing (no data leakage)
   - ✅ **vs Fully automatic tools:** 100% accuracy (human verification)

**User Perspective:**
> "I WANT human review for compliance reasons. The AI saves me time by pre-flagging entities, but I control the final decision." - Compliance Officer

---

## 🎯 Use Cases

### 1. **Research Ethics Compliance**
**Scenario:** Academic researcher with 50 interview transcripts needing IRB approval

**Without GDPR Pseudonymizer:**
- ❌ Manual redaction: 16-25 hours
- ❌ Destroys document coherence for analysis
- ❌ Error-prone (human fatigue)

**With GDPR Pseudonymizer:**
- ✅ AI pre-detection: ~30 min processing
- ✅ Human validation: ~90 min review (50 docs × ~2 min each)
- ✅ Total: **2-3 hours** (85%+ time savings)
- ✅ Audit trail for ethics board

---

### 2. **HR Document Analysis**
**Scenario:** HR team analyzing employee feedback with ChatGPT

**Without GDPR Pseudonymizer:**
- ❌ Can't use ChatGPT (GDPR violation - employee names exposed)
- ❌ Manual analysis only (slow, limited insights)

**With GDPR Pseudonymizer:**
- ✅ Pseudonymize locally (employee names → pseudonyms)
- ✅ Send to ChatGPT safely (no personal data exposed)
- ✅ Get AI insights while staying GDPR-compliant

---

### 3. **Legal Document Preparation**
**Scenario:** Law firm preparing case materials for AI legal research

**Without GDPR Pseudonymizer:**
- ❌ Cloud pseudonymization service (third-party risk)
- ❌ Manual redaction (expensive billable hours)

**With GDPR Pseudonymizer:**
- ✅ 100% local processing (client confidentiality)
- ✅ Human-verified accuracy (legal defensibility)
- ✅ Reversible mappings (can de-pseudonymize if needed)

---

## ⚖️ GDPR Compliance

### How GDPR Pseudonymizer Supports Compliance

| GDPR Requirement | Implementation |
|------------------|----------------|
| **Art. 25 - Data Protection by Design** | Local processing, no cloud dependencies, encrypted storage |
| **Art. 30 - Processing Records** | Audit logs capture all operations, timestamps, model versions |
| **Art. 32 - Security Measures** | AES-128-CBC encryption (Fernet), passphrase-protected, secure deletion |
| **Art. 35 - Privacy Impact Assessment** | Transparent methodology, cite-able approach for DPIA documentation |
| **Recital 26 - Pseudonymization** | Consistent pseudonym mapping, reversibility with passphrase |

### What Pseudonymization Means (Legally)

**According to GDPR Article 4(5):**
> "Pseudonymization means the processing of personal data in such a manner that the personal data can no longer be attributed to a specific data subject **without the use of additional information**, provided that such additional information is kept separately."

**GDPR Pseudonymizer approach:**
- ✅ **Personal data replaced:** Names, locations, organizations → pseudonyms
- ✅ **Separate storage:** Mapping table encrypted with passphrase (separate from documents)
- ✅ **Reversibility:** Authorized users can de-pseudonymize with passphrase
- ⚠️ **Note:** Pseudonymization reduces risk but **does NOT make data anonymous**

**Recommendation:** Consult your Data Protection Officer (DPO) for specific compliance guidance.

---

## 🛠️ Development Status

**Current Epic:** Epic 1 - Foundation & NLP Validation (Week 1-5/14)

### Completed ✅
- ✅ **Story 0.1-0.2:** Test corpus (25 docs, 1,855 entities) + dev environment
- ✅ **Story 1.1:** Expanded test corpus with ground truth annotations
- ✅ **Story 1.2:** NLP benchmark (spaCy selected, contingency plan approved)
- ✅ **Story 1.3:** CI/CD pipeline setup (GitHub Actions)
- ✅ **Story 1.4:** Project foundation & module structure
- ✅ **Story 1.5:** Walking skeleton - basic process command (48 tests passing)

### In Progress 🔄
- 📅 **Story 1.6:** NLP integration (spaCy `fr_core_news_lg`)
- 📅 **Story 1.7:** Validation UI implementation *(NEW - Critical path)*
- 📅 **Story 1.8:** Hybrid detection strategy *(NEW - NLP + regex)*

### Upcoming 📅
- **Epic 2 (Week 6-10):** Core pseudonymization engine
- **Epic 3 (Week 11-13):** CLI polish & batch processing
- **Epic 4 (Week 14):** Launch readiness & LLM validation

---

## 🤝 Contributing

**Status:** 🚧 Pre-release development - Not yet accepting contributions

Once we reach v1.0 MVP (Week 14), we'll welcome:
- 🐛 Bug reports
- 📝 Documentation improvements
- 🌍 Translations (English, Spanish, German)
- 💡 Feature suggestions

**For now:** Follow development progress via [GitHub Issues](https://github.com/yourusername/RGPDpseudonymizer/issues) and [Discussions](https://github.com/yourusername/RGPDpseudonymizer/discussions).

---

## 📧 Contact & Support

**Project Lead:** Lionel Deveaux - [@LioChanDaYo](https://github.com/LioChanDaYo)

**For questions:**
- 💬 [GitHub Discussions](https://github.com/yourusername/RGPDpseudonymizer/discussions) - General questions, use cases
- 🐛 [GitHub Issues](https://github.com/yourusername/RGPDpseudonymizer/issues) - Bug reports (post-launch)
- 📧 Email: [project-email@example.com](mailto:project-email@example.com) - Private inquiries

---

## 📜 License

**TBD** - Will be announced before v1.0 MVP launch (Week 14)

Likely: MIT or Apache 2.0 (open-source, permissive)

---

## 🙏 Acknowledgments

**Built with:**
- [spaCy](https://spacy.io/) - Industrial-strength NLP library
- [Typer](https://typer.tiangolo.com/) - Modern CLI framework
- [rich](https://rich.readthedocs.io/) - Beautiful CLI formatting

**Inspired by:**
- GDPR privacy-by-design principles
- Academic research ethics requirements
- Real-world need for safe AI document analysis

**Methodology:**
- Developed using [BMAD-METHOD™](https://bmad.ai) framework
- Interactive elicitation and multi-perspective validation

---

## ⚠️ Disclaimer

**GDPR Pseudonymizer is a tool to assist with GDPR compliance. It does NOT provide legal advice.**

**Important notes:**
- ⚠️ Pseudonymization reduces risk but is NOT anonymization
- ⚠️ You remain the data controller under GDPR
- ⚠️ Consult your DPO or legal counsel for compliance guidance
- ⚠️ Human validation is MANDATORY - do not skip review steps
- ⚠️ Test thoroughly before production use

**v1.0 MVP limitations:**
- AI detection: 40-50% baseline (not 85%+)
- Validation required for ALL documents (not optional)
- French language only (English, Spanish, etc. in future versions)
- Text formats only (.txt, .md - no PDF/DOCX in v1.0)

---

## 📊 Project Metrics (As of 2026-01-16)

| Metric | Value | Status |
|--------|-------|--------|
| **Development Progress** | Week 1/14 | 🔄 In Progress |
| **Test Corpus Size** | 25 docs, 1,855 entities | ✅ Complete |
| **NLP Accuracy (Baseline)** | 29.5% F1 (spaCy) | ✅ Measured |
| **Target Accuracy (Hybrid)** | 40-50% F1 | 📅 Epic 1 Story 1.8 |
| **Final Accuracy (AI+Human)** | 100% (validated) | 🎯 By Design |
| **Code Coverage** | TBD | 📅 Epic 1 Story 1.3 |
| **Supported Languages** | French | 🇫🇷 v1.0 only |
| **Supported Formats** | .txt, .md | 📝 v1.0 scope |

---

## 🔗 Quick Links

- 📘 [Full PRD](docs/.ignore/prd.md) - Complete product requirements
- 📊 [Benchmark Report](docs/nlp-benchmark-report.md) - NLP accuracy analysis
- 🎨 [Positioning Strategy](docs/positioning-messaging-v2-assisted.md) - Marketing & messaging
- 🏗️ [Architecture Docs](docs/architecture/) - Technical design
- 📋 [Approval Checklist](docs/PM-APPROVAL-CHECKLIST.md) - PM decision tracker

---

**Last Updated:** 2026-01-19 (Story 1.5 Complete - Walking Skeleton Operational)

**Current Focus:** Epic 1 - NLP Integration (Story 1.6)
