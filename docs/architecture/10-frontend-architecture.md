# 10. Frontend Architecture

**Condition Check:** Does this project have a frontend (web UI, mobile app, desktop GUI)?

**Answer:** **NO** - The MVP is a **CLI-only application** with no graphical frontend (FR15, Technical Assumptions).

### 10.1 No Frontend in MVP

**Statement:** This project **does not include a frontend** in the MVP scope. All user interaction occurs through command-line interface (CLI) commands.

**Rationale:**
- **Target Users:** Technical early adopters (AI-forward organizations, researchers) comfortable with CLI tools
- **Rapid Validation:** CLI-only reduces development time, enables faster PRD validation
- **Scope Management:** Defers GUI complexity to Phase 2 after core value proposition validated

### 10.2 CLI as "Frontend"

The **CLI Layer** serves as the user interface for MVP:

**User Interaction Patterns:**

1. **Command Execution:**
   ```bash
   $ gdpr-pseudo process input.txt output.txt
   $ gdpr-pseudo batch documents/ output/ --workers 4
   ```

2. **Interactive Prompts:**
   - Passphrase entry (secure, hidden input)
   - Validation mode entity review (Rich library formatted tables)
   - Confirmation dialogs (`destroy-table` requires yes/no)

3. **Progress Indicators:**
   - Real-time progress bars for batch processing
   - Status messages (colored output: green=success, red=error, yellow=warning)

**Technology Stack:**
- **Typer:** CLI framework (command routing, argument parsing)
- **Rich:** Terminal UI enhancements (progress bars, tables, colored output)

---
