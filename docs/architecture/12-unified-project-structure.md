# 12. Unified Project Structure

Complete directory tree with explanations:

```
gdpr-pseudonymizer/
├── .github/
│   ├── workflows/
│   │   ├── ci.yaml                    # CI/CD: test matrix
│   │   └── release.yaml               # PyPI publishing
│   └── ISSUE_TEMPLATE/
├── gdpr_pseudonymizer/                # Main package
│   ├── cli/                           # CLI interface layer
│   │   ├── commands/                  # Command implementations
│   │   ├── validators.py
│   │   └── formatters.py
│   ├── core/                          # Core orchestration
│   │   ├── orchestrator.py
│   │   ├── document_processor.py
│   │   ├── batch_processor.py
│   │   └── validation_handler.py
│   ├── nlp/                           # NLP engine
│   │   ├── entity_detector.py         # Interface
│   │   ├── spacy_detector.py
│   │   └── stanza_detector.py
│   ├── data/                          # Data layer
│   │   ├── models.py                  # SQLAlchemy models
│   │   ├── repositories/
│   │   │   ├── mapping_repository.py
│   │   │   └── audit_repository.py
│   │   ├── encryption.py
│   │   └── migrations/                # Alembic
│   ├── pseudonym/                     # Pseudonym manager
│   │   ├── library_manager.py
│   │   ├── assignment_engine.py
│   │   └── validators.py
│   ├── utils/                         # Utilities
│   │   ├── file_handler.py
│   │   ├── markdown_parser.py
│   │   └── logger.py
│   └── exceptions.py
├── data/pseudonyms/                   # Pseudonym libraries
│   ├── neutral.json
│   ├── star_wars.json
│   └── lotr.json
├── tests/                             # Test suite
│   ├── unit/
│   ├── integration/
│   ├── performance/
│   └── test_corpus/                   # 25-document benchmark
├── docs/                              # Documentation
│   ├── prd.md
│   ├── architecture.md
│   ├── installation.md
│   └── usage.md
├── scripts/                           # Dev scripts
│   ├── benchmark_nlp.py
│   └── install_models.py
├── pyproject.toml                     # Poetry config
├── pytest.ini
├── mypy.ini
├── README.md
└── LICENSE
```

---
