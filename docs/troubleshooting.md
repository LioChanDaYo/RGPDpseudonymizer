# Troubleshooting Guide

**GDPR Pseudonymizer** - Error reference and solutions

---

## Installation Issues

### `poetry: command not found`

**Cause:** Poetry is not in your system PATH.

**Solution:**
1. Check installation location:
   - Windows: `%APPDATA%\Python\Scripts`
   - macOS/Linux: `~/.local/bin`
2. Add to PATH:
   - **Windows (PowerShell):** `$env:PATH += ";$env:APPDATA\Python\Scripts"`
   - **macOS/Linux:** `export PATH="$HOME/.local/bin:$PATH"` (add to `~/.bashrc` or `~/.zshrc`)
3. Restart your terminal
4. Alternative: use `python -m poetry` instead of `poetry`

### Python version not supported

**Error:** `The currently activated Python version X.Y.Z is not supported`

**Solution:**
1. Install Python 3.10, 3.11, or 3.12
2. Configure Poetry to use correct version:
   ```bash
   poetry env use python3.11
   poetry install
   ```
3. Verify with `poetry env info` (look for "Python: 3.10.x" or "3.11.x" or "3.12.x")

**Note:** Python 3.9 is no longer supported (EOL October 2025). Python 3.13+ is not yet tested.

### spaCy model download fails

**Possible causes:** Network issues, insufficient disk space (~1GB needed), firewall blocking.

**Solutions:**

1. **Check disk space:**
   ```bash
   # macOS/Linux
   df -h
   # Windows PowerShell
   Get-PSDrive C
   ```

2. **Manual installation:**
   ```bash
   poetry run python -m spacy download fr_core_news_lg
   ```

3. **Retry with verbose output:**
   ```bash
   poetry run python -m spacy download fr_core_news_lg --verbose
   ```

4. **Behind corporate firewall:** Contact IT for proxy configuration or download the model package manually from https://github.com/explosion/spacy-models

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

### `gdpr-pseudo: command not found`

**Cause:** The CLI requires the `poetry run` prefix during development.

**Solution:** Always use `poetry run`:
```bash
# CORRECT
poetry run gdpr-pseudo --help

# INCORRECT
gdpr-pseudo --help
```

**Alternative:** Activate Poetry shell:
```bash
poetry shell
gdpr-pseudo --help
exit
```

---

## Passphrase Issues

### `Passphrase must be at least 12 characters`

**Cause:** Security requirement -- passphrases must be 12+ characters.

**Solution:**
1. Use a passphrase with at least 12 characters
2. Or set via environment variable:
   ```bash
   # macOS/Linux
   export GDPR_PSEUDO_PASSPHRASE="your-secure-passphrase-here"

   # Windows PowerShell
   $env:GDPR_PSEUDO_PASSPHRASE = "your-secure-passphrase-here"
   ```

### `Incorrect passphrase`

**Error:** `Incorrect passphrase. Please check your passphrase and try again.`

**Solution:**
- Verify you are using the exact passphrase used when creating the database
- Check for trailing spaces or invisible characters
- If using environment variable, verify: `echo $GDPR_PSEUDO_PASSPHRASE` (Linux/macOS) or `echo $env:GDPR_PSEUDO_PASSPHRASE` (PowerShell)

### Forgot passphrase

**Consequence:** The mapping database cannot be decrypted. Existing mappings are permanently inaccessible and pseudonymization cannot be reversed.

**Recovery:** Create a new database (previous mappings are lost):
```bash
poetry run gdpr-pseudo init --force
```

**Prevention:** Store passphrases in a secure password manager.

### `Passphrase in config file is forbidden`

**Cause:** A `passphrase` field was found in `.gdpr-pseudo.yaml`. Plaintext credential storage is blocked for security.

**Solution:** Remove the `passphrase` field from your config file. Use one of:
- **Environment variable:** `GDPR_PSEUDO_PASSPHRASE` (recommended for automation)
- **Interactive prompt** (most secure -- default behavior)
- **CLI flag:** `--passphrase` (not recommended -- visible in shell history)

---

## Database Errors

### `Database file not found: mappings.db`

**Cause:** No database has been created yet.

**Solution:** Initialize a database:
```bash
poetry run gdpr-pseudo init
```

### `Database may be corrupted`

**Solution:**
1. If you have a backup, restore it
2. Try exporting data: `poetry run gdpr-pseudo export backup.json`
3. Create a new database: `poetry run gdpr-pseudo init --force`

### Inconsistent pseudonyms across documents

**Cause:** Using different database files for related documents.

**Solution:** Always specify the same database:
```bash
poetry run gdpr-pseudo process doc1.txt --db shared.db
poetry run gdpr-pseudo process doc2.txt --db shared.db
```

---

## NLP Processing Errors

### No entities detected

**Possible causes:**
- Document does not contain recognizable French text
- File encoding is not UTF-8
- File format not supported

**Solutions:**
1. Ensure text is in French with proper encoding (UTF-8 with accents: é, è, à)
2. Verify the document contains names, locations, or organizations
3. Verify file is `.txt` or `.md` format
4. Test with a known-good sample:
   ```bash
   echo "Marie Dubois travaille a Paris pour Acme SA." > test.txt
   poetry run gdpr-pseudo process test.txt
   ```

### `Invalid theme 'xyz'`

**Solution:** Use one of the valid themes: `neutral`, `star_wars`, `lotr`

```bash
poetry run gdpr-pseudo process doc.txt --theme neutral
```

---

## Validation UI Issues

### Validation UI not responding

**Cause:** Terminal compatibility issue with keyboard input capture.

**Solutions:**
1. Use a standard terminal (PowerShell, Terminal.app, bash)
2. Avoid running in IDE integrated terminals (VS Code, PyCharm -- may have input issues)
3. Try `poetry shell` then run the command directly
4. On Windows, try Windows Terminal instead of legacy cmd.exe

### Keyboard shortcuts not working

**Solution:** Press `H` or `?` during validation to see the full help overlay with all available shortcuts. Some shortcuts (batch operations like `Shift+A`, `Shift+R`) are hidden by default.

---

## Platform-Specific Issues

### Windows: spaCy access violations

**Symptom:** Crash or access violation errors when running spaCy on Windows.

**Solutions:**
1. **Use WSL (recommended):** Install Windows Subsystem for Linux and run the tool there
2. **Limit threads:** Set `OMP_NUM_THREADS=1` in environment:
   ```powershell
   $env:OMP_NUM_THREADS = 1
   ```
3. **Update dependencies:**
   - Update Windows to latest version
   - Update Visual C++ Redistributable

**Note:** This is a known spaCy issue on Windows ([spaCy #12659](https://github.com/explosion/spaCy/issues/12659)). CI skips spaCy-dependent tests on Windows for this reason.

### macOS: Xcode Command Line Tools required

**Error:** Build errors during `poetry install`

**Solution:**
```bash
xcode-select --install
```

### macOS: Apple Silicon (M1/M2/M3)

Python 3.10+ has native ARM support. If using Homebrew:
```bash
brew install python@3.11
```

### Linux: Missing build tools

**Error:** Compilation errors during `poetry install`

**Solution:**

Ubuntu/Debian:
```bash
sudo apt install python3-dev build-essential
```

Fedora:
```bash
sudo dnf install python3-devel gcc
```

### Permission denied errors

**Solutions:**
- **macOS/Linux:** Check file permissions with `ls -la`, ensure write access
- **Windows:** Run PowerShell as Administrator for installation steps
- Ensure write access to the project directory and output paths

---

## Performance Issues

### Processing slows or crashes on large batches

**Solutions:**
- Process files in smaller batches
- Reduce parallel workers: `--workers 1`
- Close other applications to free memory (spaCy model uses ~1.5GB per worker)
- Monitor memory usage -- the tool requires up to 8GB RAM with 4 workers

### spaCy model loading is slow

**Cause:** The `fr_core_news_lg` model is ~571MB and takes a few seconds to load on first use.

**Mitigation:** The model is cached in memory after first load. Subsequent documents in a batch session process faster.

---

## When to File Bug Reports

File a bug report on GitHub if you encounter:

1. **Crashes** that are not explained by the troubleshooting entries above
2. **Incorrect pseudonymization** (entity replaced with wrong type of pseudonym)
3. **Data loss** (database corruption, missing mappings)
4. **Security concerns** (passphrase exposure, encryption issues)

**How to report:**
- GitHub Issues: https://github.com/LioChanDaYo/RGPDpseudonymizer/issues
- Include: OS version, Python version, full error message, steps to reproduce
- **Do NOT include** sensitive data (real names, document content) in bug reports

---

## Related Documentation

- [Installation Guide](installation.md) - Platform-specific setup
- [CLI Reference](CLI-REFERENCE.md) - Complete command documentation
- [FAQ](faq.md) - Common questions
- [Tutorial](tutorial.md) - Step-by-step usage guides
