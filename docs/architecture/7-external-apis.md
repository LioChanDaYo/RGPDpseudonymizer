# 7. External APIs

**Condition Check:** Does the project require external API integrations?

**Answer:** **NO** - The GDPR Pseudonymizer is designed as a **local-first, offline-capable tool** with **zero network dependencies** after initial installation (NFR11, NFR16).

### 7.1 No External APIs Required

**Statement:** This project **does not integrate with external APIs** during normal operation. All processing occurs entirely on the user's local machine without network communication.

**Rationale:**
- **GDPR Compliance:** Primary requirement is to process sensitive documents locally to avoid data transfer risks
- **Privacy by Design:** No telemetry, crash reporting, or external service dependencies
- **Offline Operation:** Users can work in air-gapped environments after installation (NFR11)
- **Data Minimization:** No external services have access to original documents or pseudonymized mappings

### 7.2 Installation-Time Dependencies (Not Runtime APIs)

While the application has no runtime API dependencies, there are **one-time installation dependencies**:

#### 7.2.1 PyPI (Python Package Index)

- **Purpose:** Package distribution and installation
- **URL:** https://pypi.org/
- **Authentication:** None (public package repository)
- **Usage:** User runs `pip install gdpr-pseudonymizer` once during installation

#### 7.2.2 spaCy Model Download

- **Purpose:** Download French NER model post-installation
- **Documentation:** https://spacy.io/usage/models
- **Base URL:** https://github.com/explosion/spacy-models/releases/
- **Usage:** Downloaded once after package installation (~500MB model cached locally)

### 7.3 Optional Testing Dependencies (Epic 4 - LLM Utility Validation)

For **NFR10 validation** (LLM utility preservation testing), the development team requires API access to LLM services. **These are testing-only, not user-facing runtime dependencies.**

#### 7.3.1 OpenAI API (Testing Only)

- **Purpose:** Validate pseudonymized document utility with ChatGPT (NFR10)
- **Usage:** **Development/testing only** - NOT used in production application
- **Integration Notes:** Users never need OpenAI API access

#### 7.3.2 Anthropic API (Testing Only)

- **Purpose:** Validate pseudonymized document utility with Claude (NFR10)
- **Usage:** **Development/testing only** - NOT used in production application

---
