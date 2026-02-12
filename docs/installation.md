# Installation Guide

**GDPR Pseudonymizer** - AI-Assisted Pseudonymization for French Documents

This guide covers installation on Windows, macOS, and Linux.

---

## Prerequisites

| Requirement | Version | How to Check |
|-------------|---------|--------------|
| **Python** | 3.10, 3.11, or 3.12 | `python --version` |
| **Disk Space** | ~1GB free | For spaCy French model (auto-downloaded on first use) |
| **Internet** | Required for installation | Model auto-download ~571MB |

**Important:** Python 3.10-3.12 are validated in CI/CD. Python 3.9 is no longer supported (EOL October 2025). Python 3.13+ is not yet tested.

---

## Install from PyPI (Recommended)

The simplest way to install for end-users:

```bash
pip install gdpr-pseudonymizer

# Verify installation
gdpr-pseudo --help
```

> **Note:** The spaCy French model (~571MB) downloads automatically on first use. To pre-download it:
> ```bash
> python -m spacy download fr_core_news_lg
> ```

---

## Install from Source (Contributors)

For development and contributing, you'll also need [Poetry](https://python-poetry.org/) 1.7+.

### Quick Install (All Platforms)

```bash
# 1. Clone repository
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer

# 2. Install dependencies
poetry install

# 3. Verify installation
poetry run gdpr-pseudo --help
```

> **Note:** The spaCy French model (~571MB) downloads automatically on first use. To pre-download it:
> ```bash
> poetry run python scripts/install_spacy_model.py
> ```

---

## Platform-Specific Instructions

### Windows 11

#### Step 1: Install Python

1. Download Python 3.11 from [python.org](https://www.python.org/downloads/)
2. Run installer, check **"Add Python to PATH"**
3. Verify: Open PowerShell and run:
   ```powershell
   python --version
   # Expected: Python 3.11.x
   ```

#### Step 2: Install Poetry

Open PowerShell and run:
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

Add Poetry to PATH if not found:
```powershell
# Add to your PowerShell profile or run each session
$env:PATH += ";$env:APPDATA\Python\Scripts"
```

Verify:
```powershell
poetry --version
# Expected: Poetry (version 1.7.0 or higher)
```

#### Step 3: Clone and Install

```powershell
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer
poetry install
```

#### Step 4: Verify Installation

```powershell
poetry run gdpr-pseudo --help
```

> **Note:** The spaCy French model (~571MB) downloads automatically on first use. To pre-download it:
> ```powershell
> poetry run python scripts/install_spacy_model.py
> ```

**Windows Note:** The CLI may appear as `gdpr-pseudo.cmd` - this is normal Poetry behavior.

---

### macOS (Intel & Apple Silicon)

#### Step 1: Install Python

**Option A: Using Homebrew (Recommended)**
```bash
brew install python@3.11
```

**Option B: From python.org**
Download from [python.org](https://www.python.org/downloads/macos/)

Verify:
```bash
python3 --version
# Expected: Python 3.11.x
```

**Apple Silicon (M1/M2/M3):** Python 3.9+ has native ARM support.

#### Step 2: Install Xcode Command Line Tools

Required for compiling some dependencies:
```bash
xcode-select --install
```

#### Step 3: Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Add to PATH (add to `~/.zshrc` for persistence):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Verify:
```bash
poetry --version
```

#### Step 4: Clone and Install

```bash
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer
poetry install
```

#### Step 5: Verify Installation

```bash
poetry run gdpr-pseudo --help
```

> **Note:** The spaCy French model (~571MB) downloads automatically on first use. To pre-download it:
> ```bash
> poetry run python scripts/install_spacy_model.py
> ```

---

### Linux (Ubuntu 22.04 / Debian)

#### Step 1: Install Python and Build Tools

```bash
sudo apt update
sudo apt install python3.11 python3.11-dev python3-pip build-essential
```

Verify:
```bash
python3.11 --version
# Expected: Python 3.11.x
```

#### Step 2: Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Add to PATH (add to `~/.bashrc` for persistence):
```bash
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

Verify:
```bash
poetry --version
```

#### Step 3: Clone and Install

```bash
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer
poetry install
```

#### Step 4: Verify Installation

```bash
poetry run gdpr-pseudo --help
```

> **Note:** The spaCy French model (~571MB) downloads automatically on first use. To pre-download it:
> ```bash
> poetry run python scripts/install_spacy_model.py
> ```

---

### Linux (Fedora 39+)

#### Step 1: Install Python and Build Tools

```bash
sudo dnf install python3.11 python3.11-devel gcc git curl
```

Verify:
```bash
python3.11 --version
# Expected: Python 3.11.x
```

#### Step 2: Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Add to PATH (add to `~/.bashrc` for persistence):
```bash
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

Verify:
```bash
poetry --version
```

#### Step 3: Clone and Install

```bash
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer
poetry install
```

#### Step 4: Verify Installation

```bash
poetry run gdpr-pseudo --help
```

> **Note:** The spaCy French model (~571MB) downloads automatically on first use. To pre-download it:
> ```bash
> poetry run python scripts/install_spacy_model.py
> ```

---

### Docker (Alternative)

Docker provides a platform-independent installation method. A Dockerfile is not yet included in the repository (planned for post-MVP), but you can run the tool in a Docker container manually.

#### Quick Docker Setup

```bash
# Start an interactive Python container
docker run -it --rm -v "$(pwd)/documents:/data" python:3.11 bash

# Inside the container:
pip install poetry
git clone https://github.com/LioChanDaYo/RGPDpseudonymizer.git
cd RGPDpseudonymizer
poetry config virtualenvs.create false
poetry install
python -m spacy download fr_core_news_lg

# Process a document from mounted /data directory
gdpr-pseudo process /data/input.txt -o /data/output.txt
```

#### Notes

- Mount your documents directory with `-v` so output files persist after the container exits
- Use `poetry config virtualenvs.create false` to install directly in the container (no need for a virtual environment inside Docker)
- The `--rm` flag cleans up the container after exit; omit it if you want to reuse the container
- **Tested on:** Docker Desktop 29.2.0 (Windows), Ubuntu 24.04 container, Debian 12 container, Fedora 39 container

#### Planned Improvements

A pre-built Dockerfile and published Docker image are planned for a future release, which will simplify this to:

```bash
# Future (not yet available)
docker run -v "$(pwd):/data" gdpr-pseudonymizer process /data/input.txt
```

---

## Command Usage

### Installed via pip

If you installed with `pip install gdpr-pseudonymizer`, commands work directly:

```bash
gdpr-pseudo --help
gdpr-pseudo process input.txt
gdpr-pseudo batch ./documents/
```

### Installed from source (Poetry)

If you cloned the repository, prefix commands with `poetry run`:

```bash
poetry run gdpr-pseudo --help
poetry run gdpr-pseudo process input.txt
poetry run gdpr-pseudo batch ./documents/
```

**Alternative:** Activate Poetry shell for session:
```bash
poetry shell
gdpr-pseudo --help  # Works within shell
exit                # Return to normal shell
```

---

## Configuration (Optional)

Generate a configuration file template:

```bash
poetry run gdpr-pseudo config --init
```

This creates `.gdpr-pseudo.yaml` in the current directory:

```yaml
database:
  path: mappings.db

pseudonymization:
  theme: neutral    # neutral | star_wars | lotr
  model: spacy

batch:
  workers: 4        # 1-8 (use 1 for interactive validation)
  output_dir: null

logging:
  level: INFO
```

View current effective configuration:
```bash
poetry run gdpr-pseudo config
```

**Security Note:** Passphrase is never stored in config files. Use:
- Environment variable: `GDPR_PSEUDO_PASSPHRASE`
- Interactive prompt (default)

---

## Troubleshooting

### `poetry: command not found`

**Cause:** Poetry not in PATH.

**Solution:**
1. Check installation location:
   - Windows: `%APPDATA%\Python\Scripts`
   - macOS/Linux: `~/.local/bin`
2. Add to PATH (see platform-specific instructions above)
3. Restart terminal
4. Alternative: `python -m poetry` instead of `poetry`

---

### Python version not supported

**Error:** `The currently activated Python version X.Y.Z is not supported`

**Solution:**
1. Install Python 3.10, 3.11, or 3.12
2. Configure Poetry to use correct version:
   ```bash
   poetry env use python3.11
   poetry install
   ```

**Note:** If your system has Python 3.13+ but Poetry uses 3.10-3.12, the tool works correctly. Poetry manages its own virtual environment independently of system Python. Check with:
```bash
poetry env info
# Look for "Virtualenv Python: 3.11.x" (should be 3.10-3.12)
```

---

### Passphrase requirements

**Error:** `Passphrase must be at least 12 characters`

**Cause:** Security requirement - passphrases must be 12+ characters.

**Solution:**
1. Use a passphrase with at least 12 characters
2. Or set via environment variable:
   ```bash
   export GDPR_PSEUDO_PASSPHRASE="your-secure-passphrase-here"
   ```

---

### spaCy model download fails

**Possible causes:**
- Network issues
- Insufficient disk space (~1GB needed)
- Firewall blocking download

**Solutions:**

1. **Check disk space:**
   ```bash
   # macOS/Linux
   df -h

   # Windows
   dir
   ```

2. **Manual installation:**
   ```bash
   poetry run python -m spacy download fr_core_news_lg
   ```

3. **Behind corporate firewall:** Contact IT for proxy configuration

4. **Retry with verbose output:**
   ```bash
   poetry run python -m spacy download fr_core_news_lg --verbose
   ```

---

### `poetry install` fails with dependency conflicts

**Solution:**
1. Verify Python version (must be 3.10-3.12)
2. Clear virtual environment and reinstall:
   ```bash
   poetry env remove python
   poetry install
   ```
3. Update Poetry:
   ```bash
   poetry self update
   ```

---

### CLI command not working

**Error:** `gdpr-pseudo: command not found`

**Solution:** Always use `poetry run` prefix:
```bash
# CORRECT
poetry run gdpr-pseudo --help

# INCORRECT
gdpr-pseudo --help
```

---

### Windows: spaCy access violations

**Symptom:** Crash or access violation errors when running spaCy.

**Solutions:**
1. Use Windows Subsystem for Linux (WSL) instead
2. Limit threads: Set `OMP_NUM_THREADS=1` environment variable
3. Update Windows and Visual C++ Redistributable

---

### Permission denied errors

**Cause:** Insufficient file permissions.

**Solutions:**
- **macOS/Linux:** Check permissions with `ls -la`
- **Windows:** Run PowerShell as Administrator for installation
- Ensure write access to project directory

---

## Verify Complete Installation

Run these commands to verify everything works:

```bash
# 1. Check CLI
poetry run gdpr-pseudo --help

# 2. Check version
poetry run gdpr-pseudo --version

# 3. Test processing (creates test file)
echo "Marie Dubois travaille a Paris." > test_install.txt
poetry run gdpr-pseudo process test_install.txt

# 4. Check output
cat test_install_pseudonymized.txt

# 5. Clean up
rm test_install.txt test_install_pseudonymized.txt mappings.db
```

---

## Next Steps

After installation:

1. **Quick Start Tutorial:** [tutorial.md](tutorial.md) - First pseudonymization in 5 minutes
2. **CLI Reference:** [CLI-REFERENCE.md](CLI-REFERENCE.md) - Complete command documentation
3. **FAQ:** [faq.md](faq.md) - Common questions and answers

---

## Getting Help

**Installation Issues:**
- GitHub Issues: https://github.com/LioChanDaYo/RGPDpseudonymizer/issues
- Include: OS version, Python version, full error message

**Documentation:**
- [CLI Reference](CLI-REFERENCE.md)
- [Tutorial](tutorial.md)
- [FAQ](faq.md)
- [Troubleshooting](troubleshooting.md)
