<!-- Powered by BMAD™ Core -->

# User-Defined Preferred Patterns and Preferences

## Build & Dependency Management

**Package Manager: Poetry**

This project uses **Poetry** for dependency management. All agents MUST use Poetry commands:

- ✅ **Install dependencies**: `poetry install`
- ✅ **Run tests**: `poetry run pytest [args]`
- ✅ **Run linting**: `poetry run ruff check [files]`
- ✅ **Run type checking**: `poetry run mypy [files]`
- ✅ **Add dependencies**: `poetry add <package>`
- ✅ **Run any command**: `poetry run <command>`

**❌ DO NOT use**:
- `pip install -e .` (use `poetry install` instead)
- Direct `pytest`, `ruff`, `mypy` commands (use `poetry run` prefix)
- System Python directly (Poetry manages virtual environment)

**Why Poetry?**
- Ensures correct Python version (3.9-3.11 per pyproject.toml)
- Dependency version locking via poetry.lock
- Isolated virtual environment
- Consistent across all development environments

## Python Version

**Supported**: Python 3.9 - 3.11
**Excluded**: Python 3.12, 3.13, 3.14+ (dependency compatibility)

When running commands, Poetry automatically uses the correct Python version from its managed virtual environment.
