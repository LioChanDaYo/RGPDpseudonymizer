# Alpha Installation Guide

**Version:** v0.1.0-alpha
**Status:** Early Alpha - Not Production Ready
**Target Users:** 3-5 friendly testers for feedback collection

---

## Prerequisites

Before installing the GDPR Pseudonymizer, ensure you have:

- **Python:** 3.9, 3.10, 3.11, or 3.12 (NOT 3.13+)
  - Check version: `python --version`
  - Download from: https://www.python.org/downloads/
- **Poetry:** 1.7+ (dependency management)
  - Check version: `poetry --version`
  - Installation instructions below
- **Disk Space:** ~1GB free (for spaCy French model)
- **Internet Connection:** Required for initial installation

---

## Installation Steps

### Step 1: Install Poetry

Poetry is required to manage dependencies and run the tool.

**Windows:**
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

**macOS/Linux:**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

**Verify Installation:**
```bash
poetry --version
# Expected output: Poetry (version 1.7.0 or higher)
```

If `poetry` command not found, add to PATH:
- Windows: `%APPDATA%\Python\Scripts`
- macOS/Linux: `$HOME/.local/bin`

---

### Step 2: Clone Repository

```bash
git clone https://github.com/your-org/gdpr-pseudonymizer.git
cd gdpr-pseudonymizer
```

**Note:** Replace `your-org` with the actual GitHub organization/username provided in your onboarding email.

---

### Step 3: Install Dependencies

```bash
poetry install
```

**Expected output:**
- Downloads and installs Python packages
- Creates isolated virtual environment
- Installs `gdpr-pseudonymizer` package

**Installation time:** 2-5 minutes (depending on network speed)

---

### Step 4: Install spaCy French Language Model

The tool requires a large French NLP model (~571MB download):

```bash
poetry run python scripts/install_spacy_model.py
```

**Expected output:**
```
======================================================================
spaCy French Language Model Installer
======================================================================

Installing spaCy model: fr_core_news_lg
This may take a few minutes (model size: ~571MB)...

[SUCCESS] Model 'fr_core_news_lg' installed successfully!
```

**Installation time:** 5-10 minutes (depending on network speed)

---

### Step 5: Verify Installation

Test that the CLI works correctly:

```bash
poetry run gdpr-pseudo --help
```

**Expected output:**
```
Usage: gdpr-pseudo [OPTIONS] COMMAND [ARGS]...

GDPR-compliant pseudonymization tool for French text documents

Options:
  --version  -v        Show version and exit
  --help               Show this message and exit.

Commands:
  process  Process a single document with complete pseudonymization workflow.
```

**Success!** You're ready to pseudonymize documents.

---

## Platform-Specific Notes

### Windows

- CLI command appears as `gdpr-pseudo.cmd` (this is normal Poetry behavior)
- Use PowerShell or Command Prompt for best compatibility
- If you encounter spaCy installation issues, consider using WSL (Windows Subsystem for Linux)

### macOS

- Ensure Xcode Command Line Tools installed: `xcode-select --install`
- Apple Silicon (M1/M2) users: Python 3.9+ has native ARM support

### Linux

- Ensure `python3-dev` package installed (Debian/Ubuntu: `sudo apt install python3-dev`)
- Some distributions may require `gcc` and `build-essential` packages

---

## Troubleshooting

### Problem: `poetry: command not found`

**Solution:**
1. Verify Poetry installed: Check `%APPDATA%\Python\Scripts` (Windows) or `~/.local/bin` (macOS/Linux)
2. Add Poetry to PATH (see Step 1 instructions)
3. Restart terminal/command prompt
4. Try `python -m poetry` instead of `poetry`

### Problem: Python version not supported (3.13+ detected)

**Solution:**
1. Install Python 3.9-3.12 from https://www.python.org/downloads/
2. Use `py -3.11` (Windows) or `python3.11` (macOS/Linux) to specify version
3. Configure Poetry to use specific Python: `poetry env use python3.11`

### Problem: spaCy model download fails

**Possible causes:**
- Network connectivity issues
- Insufficient disk space (~1GB required)
- Firewall blocking download

**Solutions:**
1. Check internet connection and retry
2. Free up disk space (check with `df -h` on macOS/Linux or `dir` on Windows)
3. Manual installation:
   ```bash
   poetry run python -m spacy download fr_core_news_lg
   ```
4. If behind corporate firewall, contact IT for proxy configuration

### Problem: `poetry install` fails with dependency conflicts

**Solution:**
1. Ensure Python version is 3.9-3.12 (check with `python --version`)
2. Delete existing virtual environment:
   ```bash
   poetry env remove python
   poetry install
   ```
3. Update Poetry: `poetry self update`

### Problem: CLI command not working after installation

**Solution:**
1. Always prefix commands with `poetry run`:
   ```bash
   # CORRECT
   poetry run gdpr-pseudo --help

   # INCORRECT (won't work)
   gdpr-pseudo --help
   ```
2. Alternative: Activate virtual environment manually:
   ```bash
   poetry shell
   gdpr-pseudo --help
   ```

---

## Next Steps

Once installation is complete:
1. Read [ALPHA-QUICKSTART.md](ALPHA-QUICKSTART.md) for your first pseudonymization
2. Review [ALPHA-TESTING-PROTOCOL.md](ALPHA-TESTING-PROTOCOL.md) for test scenarios
3. Report any installation issues via email or GitHub Issues

---

## Getting Help

**Installation Issues:**
- Email: [your-email@example.com] (replace with actual contact)
- GitHub Issues: https://github.com/your-org/gdpr-pseudonymizer/issues
- Include: OS version, Python version, error messages

**Expected Response Time:** Within 24 hours during alpha testing period

---

**Alpha Version Note:** This installation guide is for early testing. Some rough edges are expected. Your feedback will help improve the installation experience for the official release.
