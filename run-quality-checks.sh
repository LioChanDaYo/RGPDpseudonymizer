#!/bin/bash
# Full CI/CD quality pipeline - run this before pushing code

set -e  # Exit on first error

echo "========================================="
echo "Running Full CI/CD Quality Pipeline"
echo "========================================="
echo ""

echo "1/4 Running Ruff linter..."
poetry run ruff check .
echo "✓ Ruff passed"
echo ""

echo "2/4 Running Black formatter check..."
poetry run black --check .
echo "✓ Black passed"
echo ""

echo "3/4 Running mypy type checker..."
poetry run mypy gdpr_pseudonymizer
echo "✓ mypy passed"
echo ""

echo "4/4 Running pytest..."
poetry run pytest tests/unit/ tests/integration/ -v --tb=short
echo "✓ pytest passed"
echo ""

echo "========================================="
echo "All Quality Checks Passed!"
echo "========================================="
