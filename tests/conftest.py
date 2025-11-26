"""
Pytest configuration and shared fixtures

This file provides common fixtures and configuration for all tests.
"""

import sys
from pathlib import Path

import pytest

# Add src directory to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def project_root():
    """Get project root directory"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def config_dir(project_root):
    """Get config directory"""
    return project_root / "config"


@pytest.fixture(scope="session")
def output_dir(project_root):
    """Get output directory"""
    return project_root / "data" / "output"


@pytest.fixture
def cleanup_output(output_dir):
    """Cleanup test output files after each test"""
    yield

    # Cleanup any test HTML files
    if output_dir.exists():
        for html_file in output_dir.glob("test_*.html"):
            html_file.unlink()
        for broken_file in output_dir.glob("BROKEN_test_*.html"):
            broken_file.unlink()
