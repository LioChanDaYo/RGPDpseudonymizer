# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for GDPR Pseudonymizer (--onedir mode).

Produces a directory-based bundle that includes:
- Python runtime
- All Python dependencies (SQLAlchemy, cryptography, structlog, etc.)
- PySide6-Essentials Qt libraries
- spaCy fr_core_news_lg model (~541MB)
- Pseudonym libraries and resource files
- GUI resources (icons, themes, i18n)

Usage:
    poetry run pyinstaller gdpr-pseudo-gui.spec
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate spaCy model directory
# ---------------------------------------------------------------------------
def _find_spacy_model() -> str:
    """Locate fr_core_news_lg model installed in the virtualenv."""
    try:
        import spacy.util

        model_path = spacy.util.get_package_path("fr_core_news_lg")
        if model_path.exists():
            return str(model_path)
    except Exception:
        pass

    # Fallback: search site-packages
    for path in sys.path:
        candidate = Path(path) / "fr_core_news_lg"
        if candidate.exists() and (candidate / "meta.json").exists():
            return str(candidate)

    raise FileNotFoundError(
        "spaCy model 'fr_core_news_lg' not found. "
        "Install with: poetry run python -m spacy download fr_core_news_lg"
    )


spacy_model_path = _find_spacy_model()
project_root = Path(SPECPATH)

# ---------------------------------------------------------------------------
# Read version from pyproject.toml
# ---------------------------------------------------------------------------
_version = "0.0.0"
_pyproject = project_root / "pyproject.toml"
if _pyproject.exists():
    import re

    _match = re.search(r'^version\s*=\s*"([^"]+)"', _pyproject.read_text(), re.MULTILINE)
    if _match:
        _version = _match.group(1)

# ---------------------------------------------------------------------------
# Platform-specific settings
# ---------------------------------------------------------------------------
_is_windows = sys.platform == "win32"
_is_macos = sys.platform == "darwin"
_sep = ";" if _is_windows else ":"

# ---------------------------------------------------------------------------
# Data files to bundle
# ---------------------------------------------------------------------------
datas = [
    # Pseudonym libraries and resource JSON/YAML files
    (
        str(project_root / "gdpr_pseudonymizer" / "resources" / "*.json"),
        os.path.join("gdpr_pseudonymizer", "resources"),
    ),
    (
        str(project_root / "gdpr_pseudonymizer" / "resources" / "*.yaml"),
        os.path.join("gdpr_pseudonymizer", "resources"),
    ),
    (
        str(project_root / "gdpr_pseudonymizer" / "resources" / "pseudonyms" / "*.json"),
        os.path.join("gdpr_pseudonymizer", "resources", "pseudonyms"),
    ),
    # GUI icons
    (
        str(project_root / "gdpr_pseudonymizer" / "gui" / "resources" / "icons" / "*"),
        os.path.join("gdpr_pseudonymizer", "gui", "resources", "icons"),
    ),
    # GUI themes (QSS stylesheets)
    (
        str(project_root / "gdpr_pseudonymizer" / "gui" / "resources" / "themes" / "*.qss"),
        os.path.join("gdpr_pseudonymizer", "gui", "resources", "themes"),
    ),
    # i18n compiled translation files
    (
        str(project_root / "gdpr_pseudonymizer" / "gui" / "i18n" / "*.qm"),
        os.path.join("gdpr_pseudonymizer", "gui", "i18n"),
    ),
    # spaCy model (entire directory tree)
    (spacy_model_path, os.path.join("fr_core_news_lg")),
]

# ---------------------------------------------------------------------------
# Hidden imports — dynamically loaded modules PyInstaller cannot detect
# ---------------------------------------------------------------------------
hiddenimports = [
    # spaCy submodules (many are loaded dynamically via registry)
    "spacy.lang.fr",
    # SQLAlchemy dialect
    "sqlalchemy.dialects.sqlite",
    # structlog processors
    "structlog",
    "structlog.stdlib",
    # cryptography backends
    "cryptography.hazmat.primitives.ciphers.aead",
    # PySide6 plugins
    "PySide6.QtSvg",
    # YAML support
    "yaml",
    # markdown-it-py
    "markdown_it",
]

# ---------------------------------------------------------------------------
# Modules to exclude (reduce bundle size)
# ---------------------------------------------------------------------------
excludes = [
    "tkinter",
    "matplotlib",
    "numpy.testing",
    "scipy",
    "pandas",
    "notebook",
    "IPython",
    "PIL",
    "cv2",
    "torch",
    "tensorflow",
    "stanza",
    "pytest",
    "pytest_cov",
    "pytest_mock",
    "pytest_benchmark",
    "pytest_qt",
    "black",
    "ruff",
    "mypy",
    "mkdocs",
]

# ---------------------------------------------------------------------------
# Collect all spaCy submodules (recommended by story for dynamic loading)
# ---------------------------------------------------------------------------
from PyInstaller.utils.hooks import (
    collect_all,
    collect_submodules,
    copy_metadata,
)

spacy_datas, spacy_binaries, spacy_hiddenimports = collect_all("spacy")
datas += spacy_datas
hiddenimports += spacy_hiddenimports

# Also collect thinc (spaCy's ML backend)
thinc_datas, thinc_binaries, thinc_hiddenimports = collect_all("thinc")
datas += thinc_datas
hiddenimports += thinc_hiddenimports

# readchar uses importlib.metadata.version() at import time — bundle its metadata
datas += copy_metadata("readchar")

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [str(project_root / "scripts" / "standalone_entry.py")],
    pathex=[str(project_root)],
    binaries=spacy_binaries + thinc_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# ---------------------------------------------------------------------------
# GUI Executable (windowed — no console window)
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="gdpr-pseudonymizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI application — no console window
    disable_windowed_traceback=False,
    argv_emulation=_is_macos,  # macOS: support file open via Finder
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=(
        str(project_root / "gdpr_pseudonymizer" / "gui" / "resources" / "icons" / "app.ico")
        if _is_windows
        else str(project_root / "gdpr_pseudonymizer" / "gui" / "resources" / "icons" / "icon_512.png")
    ),
)

# ---------------------------------------------------------------------------
# CLI Executable (console — attaches to calling terminal for stdout/stderr)
# ---------------------------------------------------------------------------
cli_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="gdpr-pseudo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Console mode — stdout/stderr visible in terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=(
        str(project_root / "gdpr_pseudonymizer" / "gui" / "resources" / "icons" / "app.ico")
        if _is_windows
        else str(project_root / "gdpr_pseudonymizer" / "gui" / "resources" / "icons" / "icon_512.png")
    ),
)

# ---------------------------------------------------------------------------
# Collect into directory (--onedir mode)
# ---------------------------------------------------------------------------
coll = COLLECT(
    exe,
    cli_exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="gdpr-pseudonymizer",
)

# ---------------------------------------------------------------------------
# macOS .app bundle
# ---------------------------------------------------------------------------
if _is_macos:
    app = BUNDLE(
        coll,
        name="GDPR Pseudonymizer.app",
        icon=str(
            project_root / "gdpr_pseudonymizer" / "gui" / "resources" / "icons" / "icon_512.png"
        ),
        bundle_identifier="com.gdpr-pseudonymizer.app",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": _version,
            "CFBundleName": "GDPR Pseudonymizer",
        },
    )
