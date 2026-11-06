"""
Unit tests for CI/CD configuration validation.

Tests verify project configuration files are valid and dependencies are correctly specified.
"""

import ast
import configparser
import sys
import tomllib
from pathlib import Path

import pytest
import yaml


def test_pyproject_toml_is_valid():
    """Test that pyproject.toml is valid TOML format."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml not found"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    assert "tool" in config
    assert "poetry" in config["tool"]


def test_pyproject_has_required_metadata():
    """Test that pyproject.toml has all required metadata fields."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    poetry_config = config["tool"]["poetry"]

    # Check required fields
    assert "name" in poetry_config
    assert poetry_config["name"] == "gdpr-pseudonymizer"
    assert "version" in poetry_config
    assert "description" in poetry_config
    assert "authors" in poetry_config
    assert "license" in poetry_config


def test_pyproject_has_runtime_dependencies():
    """Test that all required runtime dependencies are listed in pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    dependencies = config["tool"]["poetry"]["dependencies"]

    # Check runtime dependencies from tech stack
    required_deps = [
        "spacy",
        "typer",
        "rich",
        "PyYAML",
        "cryptography",
        "SQLAlchemy",
        "structlog",
        "markdown-it-py",
    ]

    for dep in required_deps:
        assert dep in dependencies, f"Missing required dependency: {dep}"


def test_pyproject_has_dev_dependencies():
    """Test that all required dev dependencies are listed in pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    dev_dependencies = config["tool"]["poetry"]["group"]["dev"]["dependencies"]

    # Check dev dependencies from tech stack
    required_dev_deps = [
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "pytest-benchmark",
        "black",
        "ruff",
        "mypy",
    ]

    for dep in required_dev_deps:
        assert dep in dev_dependencies, f"Missing required dev dependency: {dep}"


def test_python_version_compatibility():
    """Test that the project's floor is Python 3.11 (Story 11.1)."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    python_version = config["tool"]["poetry"]["dependencies"]["python"]

    assert python_version == ">=3.11,<3.14", "Project floor must be Python 3.11"

    # Verify current Python version is supported
    current_version = sys.version_info
    assert current_version >= (3, 11), f"Python 3.11+ required, got {current_version}"


def test_python_classifiers():
    """Test that the classifiers list 3.11, 3.12 and 3.13, and no longer 3.10."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    classifiers = config["tool"]["poetry"]["classifiers"]

    assert "Programming Language :: Python :: 3.10" not in classifiers
    assert "Programming Language :: Python :: 3.13" in classifiers
    assert "Programming Language :: Python :: 3.11" in classifiers
    assert "Programming Language :: Python :: 3.12" in classifiers


def test_no_python_310_backport():
    """Test that the Python 3.10 tomli backport is gone from the dev group."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    dev_dependencies = config["tool"]["poetry"]["group"]["dev"]["dependencies"]

    assert "tomli" not in dev_dependencies


def test_pyside6_python_marker():
    """Test the PySide6 metadata in pyproject.toml (Story 11.3).

    The PySide6-Essentials dependency entry is 6.8.3, optional, for Python
    3.11 to 3.13, and the ``gui`` and ``all`` extras list it.
    """
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    dependencies = config["tool"]["poetry"]["dependencies"]
    extras = config["tool"]["poetry"]["extras"]

    assert dependencies["PySide6-Essentials"] == {
        "version": "~6.8.3",
        "optional": True,
        "python": ">=3.11,<3.14",
    }
    assert "PySide6-Essentials" in extras["gui"]
    assert "PySide6-Essentials" in extras["all"]


def test_macos_bundle_minimum_version():
    """Test that the macOS bundle's Info.plist declares macOS 12 (Story 11.3).

    Reads gdpr-pseudo-gui.spec with ``ast`` and checks the ``info_plist``
    dict passed to ``BUNDLE(...)``.
    """
    spec_path = Path(__file__).parent.parent.parent / "gdpr-pseudo-gui.spec"
    tree = ast.parse(spec_path.read_text(encoding="utf-8"))

    bundles = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "BUNDLE"
    ]
    assert len(bundles) == 1, "expected exactly one BUNDLE(...) call"
    info_plists = [kw.value for kw in bundles[0].keywords if kw.arg == "info_plist"]
    assert len(info_plists) == 1, "BUNDLE(...) has no info_plist"
    info_plist = info_plists[0]
    assert isinstance(info_plist, ast.Dict)

    entries = {
        key.value: value
        for key, value in zip(info_plist.keys, info_plist.values, strict=True)
        if isinstance(key, ast.Constant)
    }
    minimum = entries.get("LSMinimumSystemVersion")
    assert isinstance(minimum, ast.Constant)
    assert minimum.value == "12.0.0"


def test_defusedxml_with_openpyxl():
    """Test that every extra with openpyxl also installs defusedxml.

    openpyxl uses defusedxml, when it is installed, to block XML entity
    expansion in Excel files.
    """
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    dependencies = config["tool"]["poetry"]["dependencies"]
    extras = config["tool"]["poetry"]["extras"]

    assert "defusedxml" in dependencies
    assert dependencies["defusedxml"]["optional"] is True
    openpyxl_extras = sorted(
        name for name, packages in extras.items() if "openpyxl" in packages
    )
    assert openpyxl_extras == ["all", "excel", "formats"]
    for name in openpyxl_extras:
        assert "defusedxml" in extras[name], f"extra {name!r} lacks defusedxml"


def test_black_configuration():
    """Test that Black is configured correctly."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    black_config = config["tool"]["black"]

    assert black_config["line-length"] == 88
    assert black_config["target-version"] == ["py311"]


def test_ruff_configuration():
    """Test that Ruff is configured correctly."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    ruff_config = config["tool"]["ruff"]
    ruff_lint_config = ruff_config["lint"]

    assert ruff_config["line-length"] == 88
    assert ruff_config["target-version"] == "py311"
    assert "F" in ruff_lint_config["select"]  # Pyflakes
    assert "E" in ruff_lint_config["select"]  # pycodestyle errors


def test_pytest_configuration():
    """Test that pytest is configured correctly."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    pytest_config = config["tool"]["pytest"]["ini_options"]

    assert "tests/unit" in pytest_config["testpaths"]
    assert "test_*.py" in pytest_config["python_files"]


def test_mypy_configuration():
    """Test that mypy is configured correctly."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    mypy_config = config["tool"]["mypy"]

    assert mypy_config["python_version"] == "3.11"
    assert mypy_config["strict"] is True


def test_mypy_ini_python_version():
    """Test that mypy.ini, which overrides [tool.mypy], targets the 3.11 floor."""
    mypy_ini_path = Path(__file__).parent.parent.parent / "mypy.ini"

    cfg = configparser.ConfigParser()
    cfg.read(mypy_ini_path, encoding="utf-8")

    assert cfg["mypy"]["python_version"] == "3.11"


def test_coverage_configuration():
    """Test that coverage is configured correctly."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        config = tomllib.load(f)

    coverage_config = config["tool"]["coverage"]["run"]

    assert "gdpr_pseudonymizer" in coverage_config["source"]
    assert coverage_config["branch"] is True


def test_can_import_main_package():
    """Smoke test: verify main package can be imported."""
    try:
        import gdpr_pseudonymizer

        assert gdpr_pseudonymizer is not None
    except ImportError as e:
        pytest.fail(f"Failed to import main package: {e}")


def test_can_import_nlp_module():
    """Smoke test: verify NLP module can be imported."""
    try:
        import gdpr_pseudonymizer.nlp

        assert gdpr_pseudonymizer.nlp is not None
    except ImportError as e:
        pytest.fail(f"Failed to import NLP module: {e}")


def test_codecov_yaml_exists():
    """Test that .codecov.yml configuration file exists."""
    codecov_path = Path(__file__).parent.parent.parent / ".codecov.yml"
    assert codecov_path.exists(), ".codecov.yml not found"


def test_github_workflows_exist():
    """Test that GitHub Actions workflow files exist."""
    workflows_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
    assert workflows_dir.exists(), ".github/workflows directory not found"

    ci_workflow = workflows_dir / "ci.yaml"
    assert ci_workflow.exists(), "ci.yaml workflow not found"

    quality_workflow = workflows_dir / "code-quality.yaml"
    assert quality_workflow.exists(), "code-quality.yaml workflow not found"


def test_ci_test_matrix():
    """Test the CI test matrix: 3.11 with coverage, 3.13, macOS and Windows 3.12 (Story 11.3)."""
    ci_path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "ci.yaml"

    with open(ci_path, encoding="utf-8") as f:
        ci_config = yaml.safe_load(f)

    matrix = ci_config["jobs"]["test"]["strategy"]["matrix"]["include"]
    versions = [entry["python-version"] for entry in matrix]

    assert matrix == [
        {"os": "ubuntu-22.04", "python-version": "3.11", "coverage": True},
        {"os": "ubuntu-22.04", "python-version": "3.13", "coverage": False},
        {"os": "macos-latest", "python-version": "3.12", "coverage": False},
        {"os": "windows-latest", "python-version": "3.12", "coverage": False},
    ]
    assert "3.10" not in versions


def test_pytest_ini_exists():
    """Test that pytest.ini configuration file exists."""
    pytest_ini_path = Path(__file__).parent.parent.parent / "pytest.ini"
    assert pytest_ini_path.exists(), "pytest.ini not found"


def test_mypy_ini_exists():
    """Test that mypy.ini configuration file exists."""
    mypy_ini_path = Path(__file__).parent.parent.parent / "mypy.ini"
    assert mypy_ini_path.exists(), "mypy.ini not found"
