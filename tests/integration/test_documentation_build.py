"""Tests for documentation tooling (MkDocs build and internal links).

Story 4.3 - Task 4.3.12: Verify MkDocs builds without errors
and all navigation pages exist.
"""

import subprocess
import sys
from pathlib import Path

import pytest

# Project root (two levels up from tests/integration/)
PROJECT_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def mkdocs_build() -> subprocess.CompletedProcess[str]:
    """Run MkDocs build once for the entire test session."""
    result = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result


class TestDocumentationBuild:
    """Test that MkDocs documentation builds successfully."""

    def test_mkdocs_config_exists(self) -> None:
        """Verify mkdocs.yml configuration file exists."""
        config_path = PROJECT_ROOT / "mkdocs.yml"
        assert config_path.exists(), f"mkdocs.yml not found at {config_path}"

    def test_mkdocs_build_succeeds(
        self, mkdocs_build: subprocess.CompletedProcess[str]
    ) -> None:
        """Verify MkDocs build completes without errors (strict mode)."""
        assert (
            mkdocs_build.returncode == 0
        ), f"MkDocs build failed:\nstdout: {mkdocs_build.stdout}\nstderr: {mkdocs_build.stderr}"

    @pytest.mark.parametrize(
        "doc_file",
        [
            "docs/index.md",
            "docs/installation.md",
            "docs/tutorial.md",
            "docs/CLI-REFERENCE.md",
            "docs/methodology.md",
            "docs/faq.md",
            "docs/troubleshooting.md",
            "docs/api-reference.md",
        ],
    )
    def test_nav_pages_exist(self, doc_file: str) -> None:
        """Verify all pages listed in MkDocs nav actually exist."""
        file_path = PROJECT_ROOT / doc_file
        assert file_path.exists(), f"Navigation page missing: {doc_file}"

    @pytest.mark.parametrize(
        "doc_file",
        [
            "docs/index.md",
            "docs/installation.md",
            "docs/tutorial.md",
            "docs/CLI-REFERENCE.md",
            "docs/methodology.md",
            "docs/faq.md",
            "docs/troubleshooting.md",
            "docs/api-reference.md",
        ],
    )
    def test_nav_pages_not_empty(self, doc_file: str) -> None:
        """Verify navigation pages have content (not empty)."""
        file_path = PROJECT_ROOT / doc_file
        content = file_path.read_text(encoding="utf-8")
        assert len(content) > 100, f"Page appears empty or too short: {doc_file}"

    def test_site_directory_created(
        self, mkdocs_build: subprocess.CompletedProcess[str]
    ) -> None:
        """Verify the build produces a site/ directory with index.html."""
        assert mkdocs_build.returncode == 0, "Build must succeed first"
        site_dir = PROJECT_ROOT / "site"
        assert site_dir.exists(), "site/ directory not created by build"
        index_html = site_dir / "index.html"
        assert index_html.exists(), "site/index.html not created by build"

    def test_search_index_generated(
        self, mkdocs_build: subprocess.CompletedProcess[str]
    ) -> None:
        """Verify search index is generated for search functionality."""
        assert mkdocs_build.returncode == 0, "Build must succeed first"
        search_index = PROJECT_ROOT / "site" / "search" / "search_index.json"
        assert search_index.exists(), "Search index not generated"
        content = search_index.read_text(encoding="utf-8")
        assert len(content) > 100, "Search index appears empty"

    def test_internal_links_no_warnings(
        self, mkdocs_build: subprocess.CompletedProcess[str]
    ) -> None:
        """Verify MkDocs build produces no link warnings in stderr."""
        assert mkdocs_build.returncode == 0, "Build must succeed first"
        stderr = mkdocs_build.stderr.lower()
        assert (
            "warning" not in stderr
        ), f"MkDocs build produced warnings:\n{mkdocs_build.stderr}"
