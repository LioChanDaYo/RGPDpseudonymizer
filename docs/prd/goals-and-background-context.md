# Goals and Background Context

### Goals

- Achieve ≥90% NER detection accuracy (precision and recall) on French text benchmark corpus
- Achieve ≥85% installation success rate for first-time users on target platforms
- Validate LLM utility preservation: pseudonymized documents maintain ≥80% usefulness for AI analysis
- Automate entity detection and pseudonymization with 50%+ time savings vs manual redaction for batch processing
- Provide GDPR-compliant pseudonymization with encrypted mapping tables, audit trails, and reversibility
- Enable consistent pseudonymization across document batches (10-100+ files) for corpus-level analysis
- Deliver transparent, cite-able methodology suitable for research ethics board evaluation

### Background Context

The explosion of LLM capabilities in 2024-2025 has created an urgent dilemma: organizations and researchers possess valuable documents that could benefit enormously from AI analysis, but cannot safely send them to cloud-based services due to embedded personal data and GDPR obligations. Every day, they choose between staying compliant but falling behind, or innovating but taking unacceptable privacy risks. Manual redaction doesn't scale and destroys document coherence, while cloud-based pseudonymization services require trusting third parties with confidential data.

GDPR Pseudonymizer solves this by providing a local Python CLI tool that automatically detects and replaces personal identifiers (names, locations, organizations) with consistent, readable pseudonyms—entirely on the user's infrastructure. The MVP targets **AI-forward organizations and technically-comfortable researchers** as primary users, focusing on French-language text files (.txt, .md) to validate core value propositions: trustworthy local processing, batch efficiency, and maintained document utility for LLM analysis and qualitative research. Phase 2 will expand to GUI for broader adoption. The tool prioritizes the LLM enablement use case for MVP validation while ensuring methodology meets academic rigor standards for research applications.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-01-11 | v1.0 | Initial PRD creation from Project Brief | John (PM) |

---
