# GDPR Pseudonymizer v1.1.0 Released

We're pleased to announce **GDPR Pseudonymizer v1.1.0**, completing Epic 5 (Quick Wins & GDPR Compliance) with 7 new stories bringing significant improvements to privacy compliance, accuracy, format support, and documentation.

## What's New

### GDPR Article 17 — Right to Erasure (Story 5.1)
New `delete-mapping` and `list-entities` commands enable selective deletion of entity mappings with full audit trail, fulfilling GDPR Article 17 compliance requirements. Includes passphrase verification, confirmation prompts, and optional `--reason` flag for documenting erasure rationale.

### Gender-Aware Pseudonym Assignment (Story 5.2)
Automatically detects French first name gender from a 945-name dictionary (470 male, 457 female, 18 ambiguous) and assigns gender-matched pseudonyms. Female names get female pseudonyms, male names get male pseudonyms — preserving document coherence for downstream analysis.

### NER Accuracy Doubled (Story 5.3)
F1 score improved from **29.74% to 59.97%** (+30.23pp) through:
- Ground-truth annotation cleanup (1,855 to 1,737 entities)
- Expanded regex patterns (LastName/FirstName format, 18 ORG suffixes, 10 ORG prefixes)
- French geography dictionary (100 cities, 18 regions, 101 departments)
- PERSON recall: 34.23% to 82.93% (+48.70pp)

### French Documentation (Story 5.4)
Full French translation of README and user guides (`installation.fr.md`, `tutorial.fr.md`, `faq.fr.md`, `troubleshooting.fr.md`). MkDocs documentation site now features FR/EN toggle via `mkdocs-static-i18n`.

### PDF/DOCX Input Support (Story 5.5)
Process PDF and DOCX documents directly without manual text conversion. Install optional extras:
```bash
pip install gdpr-pseudonymizer[formats]    # Both PDF + DOCX
pip install gdpr-pseudonymizer[pdf]        # PDF only
pip install gdpr-pseudonymizer[docx]       # DOCX only
```

### CLI Polish & Benchmarks (Story 5.6)
- Context cycling dot indicator in validation UI
- Batch operations feedback with entity counts
- CI benchmark regression gate with `pytest-benchmark`

## Upgrade

```bash
pip install --upgrade gdpr-pseudonymizer
```

For PDF/DOCX support:
```bash
pip install --upgrade gdpr-pseudonymizer[formats]
```

## Breaking Changes

**None.** v1.1.0 is fully backwards compatible with v1.0.x. Existing mapping databases, configuration files, and workflows continue to work without modification.

## By the Numbers

- **40 stories** completed across 5 epics
- **1,267+ tests** passing
- **86%+ code coverage**
- All quality gates green (Black, Ruff, mypy, pytest)
- Tested on Python 3.10-3.12 across Windows, macOS, and Linux

## Links

- **PyPI:** https://pypi.org/project/gdpr-pseudonymizer/1.1.0/
- **Documentation:** https://liochandayo.github.io/RGPDpseudonymizer/
- **Documentation (FR):** https://liochandayo.github.io/RGPDpseudonymizer/fr/
- **Changelog:** [CHANGELOG.md](https://github.com/LioChanDaYo/RGPDpseudonymizer/blob/main/CHANGELOG.md)
- **Source:** https://github.com/LioChanDaYo/RGPDpseudonymizer

## Thank You

Thanks to everyone who tested v1.0.x and provided feedback. Your bug reports and feature requests directly shaped this release.

---

**Questions?** Open a [GitHub Discussion](https://github.com/LioChanDaYo/RGPDpseudonymizer/discussions) or file an [Issue](https://github.com/LioChanDaYo/RGPDpseudonymizer/issues).
