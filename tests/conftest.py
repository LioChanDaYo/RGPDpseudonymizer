"""
Pytest configuration and shared fixtures.

This conftest.py file sets up environment variables to prevent
spaCy/Thinc access violations on Windows systems.
"""

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def configure_environment():
    """
    Set environment variables before any tests run.

    OMP_NUM_THREADS=1 helps prevent memory access violations
    in spaCy's underlying Thinc library on Windows systems.
    """
    os.environ["OMP_NUM_THREADS"] = "1"
    yield
