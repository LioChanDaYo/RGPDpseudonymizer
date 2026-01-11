# Project Brief: GDPR Pseudonymizer

## Executive Summary

**GDPR Pseudonymizer** is a local Python application designed to pseudonymize sensitive documents and interview transcripts in compliance with GDPR regulations. Currently in early development, the solution starts as a CLI tool for rapid MVP validation and technical users, with a GUI planned for Phase 2 (estimated 2-4 months post-MVP) to make privacy-preserving pseudonymization accessible to non-technical users.

The tool addresses two equally critical use cases: **(1) Protecting confidential documents before processing with external LLMs** (ChatGPT, Claude, etc.), unlocking AI capabilities while maintaining privacy, and **(2) Pseudonymizing interview transcripts** for analysis, research publication, or sharing with third parties. Unlike cloud-based alternatives, GDPR Pseudonymizer guarantees that confidential data never leaves the user's infrastructure.

**Target users** span multiple domains: organizations wanting to leverage LLMs on proprietary documents, researchers conducting qualitative studies, HR professionals handling employee interviews, and consultants managing sensitive client data. The CLI serves technically-comfortable early adopters and enables automation/scripting, while the planned GUI (Phase 2, Q2-Q3 2026) will expand accessibility to all user profiles.

**Key value proposition:** A trustworthy, locally-run pseudonymization solution that maintains document readability and narrative coherence through optional fictional universe theming, while providing complete control over sensitive data and GDPR compliance. The phased approach delivers immediate value to technical users while ensuring enterprise-grade privacy protection becomes accessible to everyone.

---

## Problem Statement

**Current State & Pain Points:**

Professionals across multiple domains face a critical dilemma when handling sensitive personal data: they need to analyze, share, or process confidential information, but doing so risks privacy violations and GDPR non-compliance. This problem manifests in several painful scenarios:

1. **LLM Adoption Blocked by Privacy Concerns:** Organizations possess valuable proprietary documents (contracts, reports, meeting notes, client communications) that could benefit enormously from LLM analysis, but cannot safely send them to cloud-based AI services due to embedded personal data. This effectively locks them out of the AI revolution for their most sensitive—and often most valuable—content.

2. **Research Bottlenecks & Ethical Obligations:** Researchers conducting qualitative studies with interview transcripts face a dual challenge: they have both **legal obligations under GDPR** to protect participant data and **ethical commitments** to honor the trust placed in them by interviewees. This creates severe limitations—they cannot share raw transcripts with colleagues, publish supporting materials, or use modern AI tools for analysis without risking participant confidentiality breaches and violating their research ethics protocols. The consent forms they provide to participants promise anonymity, making proper pseudonymization not just a legal requirement but an ethical imperative.

3. **Manual Redaction is Inefficient and Error-Prone:** Current alternatives involve manually searching for and redacting names, which is time-consuming (hours per document), inconsistent across team members, and prone to human error. A single missed name can constitute a GDPR violation.

4. **Cloud Solutions Require Trusting Third Parties:** Existing cloud-based pseudonymization services require uploading sensitive data to external servers, creating a fundamental trust problem and additional legal complexity (data processor agreements, cross-border transfers). For highly confidential data, this is simply unacceptable.

**Impact & Scale:**

- **Business Impact:** Companies are leaving significant value on the table by not leveraging LLMs on proprietary documents, limiting competitive advantage and innovation.
- **Research Impact:** Academic and market researchers face delays of weeks in preparing data for publication or collaboration, directly impacting research output and velocity.
- **Compliance Risk:** Manual processes create audit trail gaps and increase the risk of costly GDPR violations (fines up to 4% of global revenue or €20M).
- **Operational Burden:** Manual redaction is labor-intensive and doesn't scale—batch processing of dozens or hundreds of documents is effectively impractical without automation.

**Why Existing Solutions Fall Short:**

- **Cloud services** require trusting third parties with your most sensitive data—a non-starter for many organizations
- **Manual redaction** doesn't scale, is error-prone, and destroys narrative coherence (lots of █████ blocks)
- **Simple find-replace scripts** miss contextual variations and don't maintain consistency across documents
- **Enterprise DLP tools** are designed for prevention, not transformation—they block but don't enable
- **Generic NLP libraries** require significant technical expertise to configure and integrate

**Urgency & Importance:**

The explosion of LLM capabilities in 2024-2025 has made this problem urgent. Every day, organizations choose between:
- **Staying compliant but falling behind** (not using LLMs on sensitive data), or
- **Innovating but taking risks** (using LLMs unsafely)

Neither option is acceptable. The need for a trustworthy, local pseudonymization solution is immediate and growing as AI adoption accelerates. GDPR enforcement is also intensifying, with regulatory scrutiny on AI and data processing increasing quarter over quarter.

---

## Proposed Solution

**GDPR Pseudonymizer** is a local, Python-based pseudonymization tool that solves the trust and scalability problems of handling sensitive data. By keeping all processing on the user's own infrastructure and automating entity detection and replacement, it enables safe use of AI tools and data sharing while maintaining full GDPR compliance.

**Core Concept & Approach:**

The solution uses advanced Named Entity Recognition (NER) technology to automatically detect personal identifiers (names, locations, organizations) in documents and transcripts, then systematically replaces them with consistent pseudonyms throughout the text. Unlike simple redaction that creates █████ blocks, GDPR Pseudonymizer maintains narrative coherence and readability—"Jean Dupont" becomes "Luke Skywalker" everywhere it appears, preserving context for analysis.

The tool operates entirely locally, with three core components:
1. **NER Engine** - Detects entities using proven NLP libraries (spaCy, Stanza, or similar)
2. **Pseudonymization Logic** - Maps detected entities to consistent, readable pseudonyms with optional thematic naming (Star Wars, Lord of the Rings, etc.) to enhance document readability while maintaining coherence
3. **Secure Mapping Table** - Encrypted SQLite database storing the correspondence between original and pseudonymized identities, enabling reversibility for GDPR rights exercise and providing full audit trail capabilities

**Input Format Support:**
- **MVP (Phase 1):** Plain text (.txt) and Markdown (.md) files
- **Phase 2+:** PDF, DOCX, and other document formats

**Key Differentiators:**

- **100% Local Processing** - No data ever leaves your infrastructure; complete trust and control
- **Maintains Narrative Coherence** - Pseudonymized documents remain readable and analyzable, unlike redaction blocks
- **Batch Processing with Consistency** - Handle dozens or hundreds of documents efficiently with consistent pseudonymization across the entire corpus
- **Quality Controls & Validation** - Built-in mechanisms for reviewing detected entities before final pseudonymization, with logging of all transformations for quality assurance
- **Audit Trail** - Complete tracking of all pseudonymization operations for regulatory compliance and accountability
- **Optional Thematic Naming** - Transform generic pseudonyms into coherent fictional identities to maintain readability (fully optional for professional contexts)
- **Reversibility for GDPR Rights** - Secure mapping table enables exercising data subject rights (access, rectification, deletion)
- **CLI-first with GUI roadmap** - Immediate value for technical users and automation; accessibility for all users in Phase 2

**Why This Solution Succeeds:**

Unlike cloud services, GDPR Pseudonymizer eliminates the trust problem entirely—your data never touches third-party servers. Unlike manual redaction, it scales to batch processing and maintains consistency. Unlike generic NLP libraries, it provides a complete, ready-to-use solution with GDPR-specific features (audit trails, reversibility, quality controls) built in.

The phased approach (CLI → GUI) allows rapid validation with early adopters while ensuring long-term accessibility. The optional thematic naming feature addresses a real problem (maintaining readability) in a creative way that differentiates GDPR Pseudonymizer in the market, while remaining professional through its optional nature.

**High-Level Vision:**

A tool that empowers professionals to safely leverage modern AI capabilities on their most sensitive data, while honoring both legal obligations and ethical commitments to data subjects. GDPR Pseudonymizer should become the de facto standard for local pseudonymization, trusted by researchers, enterprises, and compliance officers alike for its transparency, auditability, and reliability.

---

## Target Users

GDPR Pseudonymizer serves professionals across multiple domains who share a common need: processing sensitive personal data while maintaining privacy, compliance, and data quality.

### Primary User Segment: AI-Forward Organizations & Knowledge Workers

**Profile:**
- Organizations and individuals seeking to leverage LLM capabilities (ChatGPT, Claude, etc.) on proprietary or confidential documents
- Includes: Legal departments, consultancies, financial services, healthcare administration, business analysts, knowledge management teams
- Technical comfort level: Medium to high (comfortable with CLI tools, Python installation)
- Organization size: SMEs to enterprises, plus individual professionals

**Current Behaviors & Workflows:**
- Currently avoid sending sensitive documents to LLMs due to privacy concerns, or manually redact before processing (time-consuming and error-prone)
- Use LLMs extensively for public/non-sensitive content but feel limited in their most valuable use cases
- May have experimented with corporate LLM instances but still concerned about internal data exposure

**Specific Needs & Pain Points:**
- Need to unlock AI analysis on contracts, client communications, internal reports, meeting notes
- Require batch processing capability for document repositories
- Need confidence that no sensitive data leaks to external services
- Want to maintain document coherence so LLMs can provide useful analysis
- **Critical requirement:** Detection accuracy must be high enough to trust—manual verification alone defeats the purpose

**Goals:**
- Safely use LLMs on 100% of their document corpus, not just public-safe content
- Maintain competitive advantage by leveraging AI without compromising confidentiality
- Establish repeatable, compliant workflows for AI-assisted analysis

**Adoption Barriers:**
- CLI may be a barrier for some; ease of installation critical
- Performance expectations: must handle typical document batches (10-50 docs) in reasonable time
- Need confidence that pseudonymized documents remain useful for LLM analysis

---

### Primary User Segment: Academic & Market Researchers

**Profile:**
- Researchers conducting qualitative studies with interview transcripts (PhD students, postdocs, faculty, market research firms)
- Includes: Social scientists, anthropologists, user researchers, marketing analysts, policy researchers
- Technical comfort level: Low to medium (varies widely; some CLI-comfortable, many prefer GUI)
- Organization: Universities, research institutes, consulting firms, independent researchers

**Current Behaviors & Workflows:**
- Manually pseudonymize transcripts for publication, collaboration, or ethics compliance (extremely time-consuming)
- Limit data sharing due to confidentiality concerns, restricting collaboration opportunities
- Must satisfy institutional ethics boards (IRB/HREC) and honor consent form promises to participants
- Often work with dozens of interview transcripts per study (10-50+ documents)

**Specific Needs & Pain Points:**
- **Ethical imperative:** Must honor the trust of research participants who shared personal stories
- **Legal obligation:** GDPR compliance is non-negotiable for participant protection
- Need to maintain narrative coherence for qualitative analysis (coding, thematic analysis)
- **Must be able to cite and defend the methodology** in publications and to ethics committees
- Require consistency across large transcript corpora for cross-case analysis
- **Critical concern:** Pseudonymization must not destroy qualitative data integrity (narrative patterns, contextual meaning)

**Goals:**
- Protect participant confidentiality while enabling collaboration and publication
- Accelerate research timelines by automating tedious manual pseudonymization
- Maintain research quality through readable, analyzable pseudonymized transcripts
- Satisfy ethics boards and regulatory requirements with transparent, auditable methods

**Adoption Barriers:**
- Need methodological transparency and cite-able approach for academic rigor
- Ethics committees may require validation before approval
- CLI is a significant barrier for less technical researchers (GUI critical for broader adoption)
- Concerns about "black box" processing—need to understand and explain what the tool does

---

### Secondary User Segment: HR & Internal Communications Professionals

**Profile:**
- HR professionals, internal investigators, employee relations specialists, organizational development consultants
- Handle sensitive employee interviews (exit interviews, investigation transcripts, performance discussions, climate surveys)
- Technical comfort level: Low (typically not technical; **GUI is essential** for this segment)
- Organization: Medium to large enterprises, HR consulting firms

**Current Behaviors & Workflows:**
- Manually redact employee names before sharing interview data with leadership or external consultants
- Struggle to aggregate insights across multiple interview transcripts due to confidentiality constraints
- Face GDPR obligations to protect employee personal data
- Limited ability to use modern analytics or AI tools on sensitive HR data

**Specific Needs & Pain Points:**
- Need simple, reliable tools (**GUI essential**—CLI is a non-starter)
- Must protect employee identities while extracting actionable organizational insights
- Compliance requirements but limited technical resources
- Desire to use AI for sentiment analysis, trend detection, but blocked by privacy concerns

**Goals:**
- Extract strategic HR insights from sensitive interview data safely
- Enable data-driven decision-making without compromising employee trust
- Maintain legal compliance with minimal technical overhead

**Adoption Barriers:**
- **CLI is a complete blocker** for this segment
- May require enterprise support contracts and legal guarantees
- Integration with existing HR systems may be expected

**Note:** This segment will become accessible primarily in Phase 2 (GUI), though technically-savvy HR teams may adopt in Phase 1.

---

### Cross-Segment Insights

**Common characteristics across all segments:**
- High trust requirements—will not use cloud-based solutions for most sensitive data
- Need for batch processing and consistency across multiple documents
- Regulatory/ethical obligations (GDPR, research ethics, employment law)
- Desire to leverage modern tools (LLMs, analytics) currently blocked by privacy concerns
- **Quality threshold:** Detection accuracy must be high enough to trust automated results

**Common adoption barriers:**
- Concerns about NER detection accuracy and false positives/negatives
- Need for methodological transparency (especially researchers and compliance)
- Technical barriers vary widely by segment (CLI vs GUI requirements)
- Performance expectations (speed, resource requirements)

**Segment prioritization for MVP:**
- **Phase 1 (CLI):** AI-forward organizations and technically-comfortable researchers (primary focus)
- **Phase 2 (GUI):** Expands to all researchers and HR professionals (broader adoption)

**Critical success factors identified:**
- Detection quality must exceed manual methods in accuracy or time-to-completion
- Installation and setup must be smooth (broken installs = immediate abandonment)
- For researchers: must be academically defensible and ethics-board approved
- For enterprises: audit trail and compliance features are non-negotiable

---

## Goals & Success Metrics

Clear, measurable objectives ensure we can evaluate GDPR Pseudonymizer's success and guide development priorities. **Underlying all metrics is a central theme: building and maintaining user trust**—trust that the tool works accurately, trust that data remains secure, and trust that the solution delivers on its promises.

### Business Objectives

- **Achieve MVP validation within 3 months:** Release functional CLI tool (Phase 1) with core features (NER detection, batch processing, secure mapping table) to 10-20 early adopters by Q2 2026
- **Establish technical credibility:** Achieve ≥90% entity detection accuracy (precision and recall) on French language test corpus (100+ documents) to validate core value proposition and build user confidence
- **Build early adopter community:** Onboard 50+ active users (primarily AI-forward organizations and technical researchers) by end of Phase 1
- **Validate use case viability:** Demonstrate successful LLM integration workflow—users can pseudonymize documents and successfully use them with ChatGPT/Claude with maintained utility
- **Secure pathway to Phase 2:** Validate CLI adoption and user feedback to justify GUI development investment (target: 70%+ user satisfaction, clear demand for GUI from non-technical users)

### User Success Metrics

- **Time savings vs manual redaction:** Users report 50%+ time reduction for batch pseudonymization tasks (compared to manual methods)
- **Trust and confidence:** 80%+ of users report feeling confident using the tool on their most sensitive documents (post-usage survey)—this is the critical trust threshold
- **Willingness to rely on tool:** 75%+ of users willing to use pseudonymized documents for critical purposes (LLM processing, publication, compliance) without additional manual verification
- **Batch processing usage:** Average user processes 10+ documents per session (validates batch use case)
- **Quality perception:** <5% of detected entities flagged as errors by users during validation step (indicates acceptable detection quality and builds trust)
- **Repeat usage:** 60%+ of early adopters use the tool for a second project/batch within first 3 months (indicates value delivery and sustained trust)
- **Recommendation rate:** Net Promoter Score (NPS) of 40+ among early adopters (indicates product-market fit potential)

### Key Performance Indicators (KPIs)

**Technical Quality (Foundation of Trust):**
- **Detection Accuracy:** ≥90% precision and recall on entity detection (names, locations, organizations) in French text, measured on standardized test corpus—this is the minimum threshold for ethical defensibility
- **False Negative Rate:** <10% of sensitive entities missed (critical for trust—missing entities = GDPR violations)
- **False Positive Rate:** <15% of flagged entities are false positives (impacts user effort in validation)
- **Performance:** Process typical document (2000-5000 words) in <30 seconds on standard laptop (8GB RAM, mid-range CPU)

**User Experience (Trust Enablers):**
- **Installation Success Rate:** >85% of users successfully install and run first pseudonymization within 30 minutes (measures friction and builds initial confidence)
- **First-Run Success:** >80% of users complete their first document pseudonymization without errors or support requests
- **Documentation Effectiveness:** <20% of users require support beyond documentation to complete first successful run

**Adoption & Retention (Trust Indicators):**
- **User Retention:** 50%+ of users who complete first successful run return for second use within 30 days
- **Error Rate:** <10% of pseudonymization sessions encounter technical errors (crashes, failed processing)
- **User Confidence Score:** Average 4.0/5.0 on post-session confidence survey ("How confident are you in the pseudonymization quality?")

**Validation & Credibility (Trust Builders):**
- **Academic Validation:** Secure approval from at least 2 university ethics boards (IRB/HREC) for use in research projects by end of Phase 1
- **LLM Utility Preservation:** Pseudonymized documents maintain ≥80% of original LLM analysis quality (measured via user-reported satisfaction with LLM outputs)—validates that the core value proposition is delivered
- **Methodological Transparency:** Publish comprehensive methodology documentation citable in academic papers and defensible to ethics committees (completion target: before Phase 1 end)

---

## MVP Scope

Defining clear boundaries for the Minimum Viable Product ensures rapid delivery while validating core value propositions.

### Core Features (Must Have)

- **NER-based Entity Detection:** Automatically detect names (persons), locations (cities, countries), and organizations in French text using proven NLP libraries (spaCy or Stanza with French models). Must achieve ≥90% accuracy on test corpus.

- **Consistent Pseudonymization:** Replace detected entities with consistent pseudonyms throughout single documents and across document batches. "Marie Dubois" becomes "Leia Organa" everywhere it appears, maintaining narrative coherence.

- **Batch Processing:** Process multiple documents (10-100+) in a single operation with consistent pseudonym mapping across the entire batch. Critical for research and enterprise workflows.

- **Secure Mapping Table:** Encrypted SQLite database storing original↔pseudonym correspondences, enabling reversibility for GDPR rights exercise. Basic encryption with user-provided passphrase.

- **Interactive Validation Mode:** Before finalizing pseudonymization, present detected entities to user for review/correction. Allows manual additions/removals to ensure quality and build trust.

- **Basic Thematic Pseudonym Libraries:** Provide 2-3 themed name sets (e.g., Star Wars, neutral/generic) with 100+ names each to maintain readability while allowing professional contexts.

- **Audit Logging:** Record all pseudonymization operations (timestamp, files processed, entities detected, user modifications) for compliance and debugging.

- **CLI Interface:** Command-line tool with clear commands: `init`, `process`, `batch`, `list-mappings`, `export`, `destroy-table`. Must be intuitive for technically-comfortable users.

- **Documentation Package:** Installation guide, usage tutorial, FAQ, methodology description (for academic citation), troubleshooting guide.

### Out of Scope for MVP

- **GUI Interface** - Deferred to Phase 2 (Q2-Q3 2026)
- **PDF/DOCX Input** - Phase 1 supports only .txt and .md files
- **Multi-language Support** - MVP focuses on French only; other languages in Phase 2+
- **Audio Transcription Integration** - Moonshot feature, not MVP
- **Advanced Entity Types** - MVP covers names, locations, organizations; ages/professions/dates deferred
- **Cloud Deployment** - Local-only for MVP; no web service or API
- **Advanced Encryption** - Basic SQLCipher sufficient for MVP; hardware security modules deferred
- **Intelligent Pseudonym Generation** - MVP uses predefined lists; AI-generated names are Phase 3 moonshot
- **Integration Plugins** - No IDE/Office/LLM platform integrations in MVP
- **Automatic Table Destruction** - Scheduled deletion deferred; manual destruction only in MVP
- **De-pseudonymization UI** - Reversibility possible via CLI only in MVP
- **Multi-user/Team Features** - Single-user tool in MVP; collaboration features deferred

### MVP Success Criteria

**Technical:**
- Successfully processes 100-document test corpus in <1 hour on standard laptop
- Achieves ≥90% precision and recall on French NER detection
- Zero data leakage (all processing confirmed local via network monitoring)
- <5% crash rate across 1000+ test runs

**User Validation:**
- 10-20 early adopters successfully complete end-to-end workflow (install → process → use pseudonymized docs)
- 70%+ report they would continue using the tool
- At least 5 users successfully use pseudonymized documents with LLMs and report maintained utility
- At least 2 researchers obtain ethics board approval for methodology

**Confidence that Phase 2 is warranted:**
- Clear demand expressed for GUI from non-technical potential users
- No fundamental blockers discovered (e.g., NER accuracy unachievable, LLM utility degraded too much)
- Early adopters willing to recommend to colleagues

---

## Post-MVP Vision

### Phase 2 Features (Q2-Q3 2026, 3-6 months post-MVP)

**GUI Development (Primary Phase 2 Goal):**
- Cross-platform desktop application (Electron or native) with intuitive drag-and-drop interface
- Visual entity review/editing with highlighting in document preview
- Progress indicators for batch processing
- Configuration wizard for first-time setup

**Expanded Format Support:**
- PDF input with text extraction
- DOCX/ODT document processing
- CSV/Excel for tabular data pseudonymization

**Enhanced Pseudonymization:**
- Interactive pseudonym selection (user chooses from suggestions)
- Scheduled automatic table destruction with configurable retention periods
- Extended entity types: ages (with age-appropriate pseudonym matching), professions, dates

**Usability Improvements:**
- Installation packages (installers for Windows/Mac, .deb/.rpm for Linux)
- In-app tutorials and onboarding
- Improved error messages and recovery

### Long-term Vision (12-24 months)

**Become the trusted standard for local pseudonymization** - recognized by ethics boards, compliance officers, and enterprises as the go-to solution for GDPR-compliant data transformation.

**Expand language coverage** - Support major European languages (Spanish, German, Italian) plus English, making tool globally applicable while maintaining local-first principle.

**Enable research at scale** - Researchers routinely pseudonymize large transcript corpora (100s of documents) confidently, accelerating qualitative research timelines and enabling new forms of data sharing and collaboration.

**Unlock LLM value for sensitive data** - Organizations safely leverage AI capabilities on their most valuable confidential documents, eliminating the current trust/innovation trade-off.

### Expansion Opportunities

**Academic Ecosystem Integration:**
- Plugins for qualitative analysis software (NVivo, MAXQDA, Atlas.ti)
- Integration with institutional data management systems
- Certification/endorsement from research ethics associations

**Enterprise Features:**
- Team collaboration with shared pseudonym dictionaries
- Role-based access control for mapping tables
- Integration with document management systems (SharePoint, Confluence)
- Compliance reporting dashboards

**AI/LLM Platform Integrations:**
- Browser extensions for ChatGPT/Claude with automatic pre-pseudonymization
- API for programmatic access (with strong authentication)
- Direct integration with private LLM deployments

**Specialized Verticals:**
- Healthcare-specific compliance (HIPAA in addition to GDPR)
- Legal sector (attorney-client privilege protection)
- HR/recruiting (candidate data protection)

---

## Technical Considerations

### Platform Requirements

**Target Platforms:**
- Windows 10/11 (64-bit)
- macOS 11+ (Intel and Apple Silicon)
- Linux (Ubuntu 20.04+, Debian 11+, Fedora 35+)

**Minimum Hardware:**
- 8GB RAM (NLP models are memory-intensive)
- 2GB free disk space (for models and dependencies)
- Dual-core CPU (2.0GHz+)

**Performance Requirements:**
- Process 2000-5000 word document in <30 seconds
- Batch of 50 documents in <30 minutes
- Startup time <5 seconds

### Technology Preferences

**Language & Runtime:**
- **Python 3.9+** - Mature NLP ecosystem, cross-platform, wide developer familiarity

**NLP/NER Libraries:**
- **Primary: spaCy** with `fr_core_news_lg` French model (proven, well-documented, good accuracy)
- **Alternative: Stanza** as fallback if spaCy accuracy insufficient
- Evaluation criteria: Precision/recall on test corpus, speed, memory footprint

**Data Storage:**
- **SQLite with SQLCipher** for encrypted mapping table (lightweight, zero-config, good encryption)
- Simple schema: `entities` table (original, pseudonym, entity_type, first_seen), `operations` table (audit log)

**CLI Framework:**
- **Click** or **Typer** - Both mature, well-documented Python CLI frameworks

**Pseudonym Data:**
- JSON files with themed name lists (easy to extend, human-readable)
- Structured by entity type (persons, locations, organizations) and theme

**Testing:**
- pytest for unit/integration tests
- Test corpus with ground-truth annotations for NER accuracy measurement

### Architecture Considerations

**Repository Structure:**
- Monorepo for MVP (single Python package)
- Clear separation: CLI layer, core processing logic, NLP engine, data layer

**Service Architecture:**
- Single-process application for MVP (no microservices complexity)
- Modular design to allow future extraction of components

**Integration Requirements:**
- No external service dependencies (fully offline-capable)
- File system only (reads input files, writes output files)

**Security/Compliance:**
- All processing in-memory (no temp file leakage)
- Secure deletion of mapping table (overwrite before delete)
- No telemetry or analytics (zero data exfiltration)
- Clear documentation of data flows for GDPR Article 30 compliance

**Packaging & Distribution:**
- PyPI package for Python users
- Consider standalone executables (PyInstaller) for non-Python users in Phase 2

---

## Constraints & Assumptions

### Constraints

**Budget:**
- Bootstrapped development (no external funding initially)
- Minimal cloud costs (local-first = no server infrastructure)
- Development time limited by single developer availability

**Timeline:**
- 3-month MVP target (Q2 2026)
- 4-month buffer to Phase 2 GUI (accounts for iteration based on feedback)

**Resources:**
- Single developer (you) for MVP
- No dedicated QA team (early adopters as testers)
- No marketing budget (organic growth via GitHub, word-of-mouth)

**Technical:**
- Must run on consumer hardware (8GB RAM constraint)
- French language focus (limited by NLP model availability/quality)
- Text-only input for MVP (PDF/DOCX parsing adds complexity)
- No GPU required (CPU-only NLP models for accessibility)

**Legal/Compliance:**
- Must comply with GDPR requirements (no legal budget for formal audit)
- Cannot provide legal guarantees without formal entity structure

### Key Assumptions

**Technical Assumptions:**
- spaCy/Stanza can achieve ≥90% accuracy on French NER with off-the-shelf models
- SQLCipher encryption is sufficient for mapping table security
- Consumer laptops (8GB RAM) can handle NLP models and batch processing
- Text extraction from PDF/DOCX can be added later without architecture redesign

**Market Assumptions:**
- There is real demand for local pseudonymization (validated by brainstorming session insights)
- Users are willing to try CLI tools if value proposition is strong (Phase 1 focuses on technical early adopters)
- LLM adoption continues to accelerate, increasing urgency of privacy solutions
- Ethics boards will accept automated pseudonymization if methodology is transparent

**User Assumptions:**
- Early adopters can handle Python installation and basic CLI usage
- Users will invest time in validation mode (reviewing detected entities) to build trust
- Researchers need citable methodology more than proprietary algorithms
- Batch processing is more important than real-time processing for target users

**Competitive Assumptions:**
- No dominant local pseudonymization tool exists currently (market gap)
- Cloud providers won't solve the trust problem (local-first remains differentiator)
- Open-source approach builds more trust than proprietary alternatives for this use case

**Adoption Assumptions:**
- 10-20 early adopters is achievable via GitHub, LinkedIn, academic networks
- Word-of-mouth can drive Phase 1 growth without marketing spend
- Academic validation (ethics board approvals) is obtainable within 3-6 months

---

## Risks & Open Questions

### Key Risks

**Critical Risks (Could Kill MVP):**

- **NER Accuracy Insufficient:** spaCy/Stanza French models may not reach 90% accuracy threshold on real-world transcripts (informal language, typos, domain-specific terminology). **Impact:** Tool unusable if users can't trust detection; entire value proposition fails. **Mitigation:** Benchmark multiple models on representative corpus in first 2 weeks; if accuracy insufficient, lower threshold but make user validation mandatory and prominent; consider hybrid approach with rule-based enhancements.

- **LLM Utility Degradation:** Pseudonymized documents lose too much context for useful LLM analysis (e.g., names carry semantic meaning that affects interpretation). **Impact:** Primary use case (#1: LLM enablement) fails completely. **Mitigation:** Test with real LLMs early (week 3-4); user study with 5-10 LLM users comparing original vs pseudonymized outputs; may need "smart" pseudonymization preserving gender/role context.

- **Installation Complexity Blocks Adoption:** Python dependency hell, model downloads failing, platform-specific issues discourage early adopters before they evaluate tool. **Impact:** Poor first impressions kill word-of-mouth growth; nobody recommends tool. **Mitigation:** Invest heavily in packaging (Docker container as backup); create installation videos; excellent troubleshooting docs; beta test installation on 10+ different machines.

**High Risks (Significant Impact):**

- **Performance Unacceptable on Consumer Hardware:** NLP models + batch processing exceed 8GB RAM or take excessively long (>2min per document). **Impact:** Users abandon due to poor experience; "too slow to be useful" reputation. **Mitigation:** Profile early with realistic document sizes; optimize or set clear expectations; consider lightweight model option; implement progress indicators.

- **Ethics Board Rejection:** Academic institutions refuse to approve methodology due to automation concerns or lack of precedent. **Impact:** Researcher segment blocked entirely; half of target market inaccessible. **Mitigation:** Engage 2-3 ethics boards early (month 1) for input on methodology; emphasize transparency, validation steps, and user control; publish methodology paper for citation.

**Medium Risks (Manageable but Important):**

- **Encrypted Database Complexity:** SQLCipher integration issues, key management UX problems, cross-platform incompatibilities. **Impact:** Core security feature unreliable; compliance claims undermined. **Mitigation:** Research SQLCipher alternatives; prototype encryption early; consider plain SQLite with OS-level encryption as backup.

- **Pseudonym Library Exhaustion:** Finite name lists run out during large batches; users frustrated by repetition or random fallbacks. **Impact:** User experience degraded; professionalism concerns if names repeat. **Mitigation:** Large initial libraries (500+ names per theme); clear warnings when approaching exhaustion; graceful degradation to systematic naming (Person-001, etc.).

- **Scope Creep Pressure:** Early adopters request PDF support, multi-language, GUI immediately. **Impact:** MVP delayed; focus diluted; 3-month timeline fails. **Mitigation:** Clear communication of roadmap; firm boundaries; redirect feature requests to Phase 2; build trust that feedback is valued but prioritized.

### Open Questions

**Technical Unknowns:**

- **Which NLP library delivers best French accuracy: spaCy or Stanza?** Need empirical testing on representative corpus with ground truth annotations.

- **What is acceptable pseudonymization time per document?** User tolerance unknown—is 30 seconds OK? 1 minute? 5 minutes for long documents?

- **Can off-the-shelf French NER models handle informal interview language?** Transcripts may have colloquialisms, incomplete sentences, filler words that trained models struggle with.

- **Does SQLCipher performance degrade with large mapping tables (10,000+ entries)?** Need to test at scale.

**User Experience Unknowns:**

- **Do users prefer automated detection + validation workflow, or manual entity marking mode?** Workflow preference unclear; may need both options.

- **Will users accept passphrase-based encryption or demand certificate/key file management?** Security expectations vary by user sophistication.

- **How much error tolerance do users have?** If tool achieves 85% accuracy instead of 90%, is validation workflow sufficient to compensate?

**Market/Adoption Unknowns:**

- **Is French-only sufficient for MVP, or do multilingual transcripts (French/English code-switching) block adoption?** Common in business contexts; may need at least bilingual support.

- **Can we obtain ethics board approval within 3-month MVP timeline?** Bureaucratic processes may take 4-6 months; could delay user validation.

- **What is realistic early adopter acquisition number?** Is 10-20 achievable via organic outreach, or do we need 50+ for statistically meaningful feedback?

- **Will researchers trust open-source tool, or do they expect commercial entity with support contracts?** Trust dynamics for academic vs enterprise users may differ.

**Competitive Landscape:**

- **Are we aware of all existing solutions?** Need thorough competitive analysis—Microsoft Presidio, AWS Comprehend, academic tools, etc.

- **Could a well-funded startup or big tech enter this space rapidly during our MVP phase?** Market timing risk.

### Areas Needing Further Research

**Before Development Starts (Week 0-2):**

1. **Benchmark existing NER models on French interview transcripts** - Create or obtain representative test corpus (20-30 docs) with ground truth; test spaCy, Stanza, others; document precision/recall by entity type.

2. **Competitive deep dive** - Systematically evaluate Microsoft Presidio, AWS Comprehend, Google DLP API, academic tools; document gaps and positioning strategy.

3. **Initial user interviews** - 5-10 conversations with potential users (mix of researchers and LLM users) about workflows, pain points, must-haves; validate assumptions.

**During Early Development (Week 2-6):**

4. **LLM utility testing** - Pseudonymize sample documents; run through ChatGPT/Claude with realistic prompts; measure output quality degradation; iterate pseudonymization approach if needed.

5. **Ethics board consultation** - Contact 3-5 university IRBs; understand approval requirements, timelines, documentation needs; incorporate feedback into methodology.

6. **Installation dry runs** - Test installation procedure on diverse platforms (Windows 10/11, macOS Intel/Silicon, Ubuntu, Debian); document pain points; refine packaging.

**Post-MVP (Continuous):**

7. **GDPR legal review** - Consult with data protection expert to validate compliance claims, methodology soundness, documentation completeness.

8. **Usability studies** - Observe 5-10 users completing full workflow; identify friction points, confusing terminology, workflow gaps.

---

## Next Steps

### Immediate Actions (This Week)

1. **Finalize Project Brief** - Review this document with stakeholders; incorporate final feedback; publish as [docs/brief.md](docs/brief.md).

2. **Set up development environment** - Initialize Git repository; create basic Python project structure; set up testing framework.

3. **Create NER benchmark corpus** - Gather or create 20-30 French interview transcript samples; manually annotate entities for ground truth.

### Week 1-2: Research & Validation Sprint

1. **NLP Library Benchmarking**
   - Test spaCy `fr_core_news_lg` on benchmark corpus
   - Test Stanza French model on same corpus
   - Document precision, recall, speed, memory usage
   - **Decision point:** Select primary NLP library

2. **Competitive Analysis**
   - Deep dive into Microsoft Presidio, AWS Comprehend, Google DLP
   - Document feature comparison, pricing, trust model
   - Identify clear differentiation opportunities

3. **Early User Outreach**
   - Reach out to 10 potential early adopters (5 researchers, 5 LLM users)
   - Conduct informal interviews about workflows and pain points
   - Gauge interest in CLI-first approach

### Week 3-6: Core MVP Development

1. **Implement NER detection** using selected library
2. **Build pseudonymization engine** with basic name libraries
3. **Create secure mapping table** with SQLCipher
4. **Develop CLI interface** with core commands
5. **Add interactive validation mode**
6. **Weekly testing** on benchmark corpus

**Milestone (Week 6):** Functional prototype - can process single document end-to-end

### Week 7-10: Batch Processing & Polish

1. **Implement batch processing** with consistency
2. **Add audit logging**
3. **Create documentation package** (installation, usage, methodology)
4. **LLM utility testing** - validate pseudonymized docs work with ChatGPT/Claude
5. **Polish error handling and messages**

**Milestone (Week 10):** MVP feature-complete - ready for friendly alpha testers

### Week 11-12: Alpha Testing & Iteration

1. **Recruit 5-10 alpha testers** from early outreach
2. **Support alpha testing** - hands-on assistance, troubleshooting
3. **Gather feedback** - surveys, interviews, usage data
4. **Fix critical bugs** and usability issues
5. **Refine documentation** based on real user confusion

**Milestone (Week 12):** MVP validated - ready for broader early adopter release

### Post-MVP (Month 4+)

1. **Expand early adopter community** to 50+ users
2. **Pursue ethics board approvals** (2+ institutions)
3. **Collect success metrics** against KPIs defined in this brief
4. **Evaluate Phase 2 decision** - proceed with GUI if validation successful
5. **Plan Phase 2 development** if warranted

---

## PM Handoff

This Project Brief provides comprehensive context for **GDPR Pseudonymizer**. The next step is to work with the Product Manager or development team to:

1. **Review and validate** all sections of this brief, especially MVP Scope and Success Criteria
2. **Create detailed PRD** (Product Requirements Document) from this brief, specifying exact user stories, acceptance criteria, and technical specifications
3. **Establish development process** - sprint planning, review cadence, decision-making framework
4. **Set up project tracking** - task board, milestone tracking, risk register

**Key handoff artifacts:**
- This Project Brief ([docs/brief.md](docs/brief.md))
- Brainstorming session results ([docs/brainstorming-session-results.md](docs/brainstorming-session-results.md))
- NER benchmark corpus (to be created Week 1)
- Competitive analysis (to be created Week 1-2)

**Critical success factors to monitor:**
- Detection quality (90% threshold)
- Installation success rate (85% threshold)
- User confidence score (4.0/5.0 threshold)
- Academic validation (2+ ethics boards)

---

*This Project Brief was created collaboratively using the BMAD-METHOD™ framework, incorporating strategic analysis, user research, and systematic risk assessment to establish a solid foundation for GDPR Pseudonymizer development.*

