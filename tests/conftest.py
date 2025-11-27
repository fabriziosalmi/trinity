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


@pytest.fixture
def sample_e2e_content():
    """Sample content for E2E testing"""
    return {
        "hero": {
            "title": "E2E Test Portfolio",
            "subtitle": "Integration Testing"
        },
        "body": {
            "sections": [
                {"title": "About", "content": "Software engineer with expertise in Python and ML."},
                {"title": "Skills", "content": "Python, Docker, Kubernetes, Machine Learning, CI/CD"},
                {"title": "Projects", "content": "Built Trinity: AI-powered site generator"}
            ]
        }
    }


@pytest.fixture
def pathological_e2e_content():
    """Pathological content for E2E testing that requires healing"""
    long_text = "very long content that needs healing " * 500
    return {
        "hero": {
            "title": "Pathological Test",
            "subtitle": "Testing self-healing capabilities"
        },
        "body": {
            "sections": [
                {"title": "Section 1", "content": long_text},
                {"title": "Section 2", "content": long_text},
                {"title": "Section 3", "content": long_text}
            ]
        }
    }


@pytest.fixture
def model_dir(project_root):
    """Get models directory"""
    return project_root / "models"


@pytest.fixture
def dataset_path(project_root):
    """Get training dataset path"""
    return project_root / "data" / "training_dataset.csv"


@pytest.fixture(scope="session")
def trained_model(project_root):
    """Ensure a trained model exists for testing"""
    from trinity.components.trainer import LayoutRiskTrainer
    
    model_dir = project_root / "models"
    dataset_path = project_root / "data" / "training_dataset.csv"
    
    # Check if model exists
    model_files = list(model_dir.glob("layout_risk_predictor_*.joblib"))
    
    if not model_files and dataset_path.exists():
        # Train model if needed
        trainer = LayoutRiskTrainer(dataset_path=str(dataset_path))
        trainer.train()
    
    return model_dir
