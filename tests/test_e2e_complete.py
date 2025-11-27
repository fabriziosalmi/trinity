"""
End-to-End Integration Tests

Tests the complete Trinity pipeline from data mining to HTML generation,
including model training, prediction, and Guardian validation.
"""

import json
import tempfile
from pathlib import Path

import pytest

from trinity.components.dataminer import TrinityMiner
from trinity.components.predictor import LayoutRiskPredictor
from trinity.components.trainer import LayoutRiskTrainer
from trinity.engine import TrinityEngine


class TestE2ECompleteWorkflow:
    """Test complete end-to-end workflow"""

    @pytest.fixture
    def temp_output_dir(self, tmp_path):
        """Create temporary output directory"""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        return output_dir

    @pytest.fixture
    def temp_model_dir(self, tmp_path):
        """Create temporary models directory"""
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        return model_dir

    @pytest.fixture
    def sample_content(self):
        """Generate sample content for testing"""
        return {
            "brand_name": "Test Portfolio",
            "hero": {
                "title": "Test Portfolio",
                "subtitle": "Software Engineer"
            },
            "body": {
                "sections": [
                    {"title": "About", "content": "Software engineer with 5 years experience."},
                    {"title": "Skills", "content": "Python, JavaScript, Docker, Kubernetes"},
                    {"title": "Projects", "content": "Built scalable microservices"}
                ]
            }
        }

    @pytest.fixture
    def pathological_content(self):
        """Generate pathological content that requires healing"""
        long_text = "very long content " * 500  # 10,000+ chars
        return {
            "brand_name": "Pathological Test",
            "hero": {
                "title": "Pathological Test",
                "subtitle": "Long content test"
            },
            "body": {
                "sections": [
                    {"title": "Section 1", "content": long_text},
                    {"title": "Section 2", "content": long_text},
                    {"title": "Section 3", "content": long_text}
                ]
            }
        }

    def test_data_mining_workflow(self, temp_output_dir, sample_content):
        """Test data mining can log events correctly"""
        dataset_path = Path(__file__).parent.parent / "data" / "training_dataset.csv"
        if not dataset_path.exists():
            pytest.skip("Training dataset not found")

        miner = TrinityMiner(dataset_path=dataset_path)
        
        # Test logging a build event
        miner.log_build_event(
            theme="brutalist",
            content=sample_content,
            strategy="NONE",
            guardian_verdict=True,
            guardian_reason="Test passed",
            css_overrides={}
        )
        
        # Validate event was logged
        import pandas as pd
        df = pd.read_csv(dataset_path)
        assert len(df) > 0
        assert df.iloc[-1]["theme"] == "brutalist"

    def test_model_training_workflow(self, temp_model_dir):
        """Test model training pipeline"""
        dataset_path = Path(__file__).parent.parent / "data" / "training_dataset.csv"
        if not dataset_path.exists():
            pytest.skip("Training dataset not found")

        trainer = LayoutRiskTrainer()
        
        # Train model
        model, metrics = trainer.train_from_csv(
            csv_path=str(dataset_path),
            output_dir=str(temp_model_dir)
        )
        
        # Validate model and metrics
        assert model is not None
        assert metrics is not None
        assert "accuracy" in metrics
        assert "f1_score" in metrics
        assert metrics["accuracy"] >= 0.0
        assert metrics["f1_score"] >= 0.0

    def test_prediction_workflow(self, sample_content, pathological_content):
        """Test prediction on normal and pathological content"""
        model_path = Path(__file__).parent.parent / "models"
        predictor = LayoutRiskPredictor(model_dir=str(model_path))
        
        if not predictor.model:
            pytest.skip("No trained model available")

        # Test normal content
        normal_result = predictor.predict_best_strategy(sample_content, theme="brutalist")
        assert "strategy_id" in normal_result
        assert "confidence" in normal_result
        assert normal_result["confidence"] >= 0.0

        # Test pathological content
        patho_result = predictor.predict_best_strategy(pathological_content, theme="enterprise")
        assert "strategy_id" in patho_result
        assert patho_result["strategy_id"] in [0, 1, 2, 3, 4, 99]

    def test_build_workflow(self, temp_output_dir, sample_content):
        """Test complete build workflow"""
        output_file = "test_build.html"

        # Build site
        engine = TrinityEngine()
        result = engine.build_with_self_healing(
            content=sample_content,
            theme="brutalist",
            output_filename=output_file,
            enable_guardian=False
        )

        # Validate result
        assert result.status.name == "SUCCESS"
        output_path = Path(__file__).parent.parent / "output" / output_file
        assert output_path.exists()
        assert output_path.stat().st_size > 1000

    def test_multiple_themes(self, temp_output_dir, sample_content):
        """Test build with multiple themes"""
        themes = ["brutalist", "enterprise"]
        
        for theme in themes:
            output_file = f"test_{theme}.html"
            
            engine = TrinityEngine()
            result = engine.build_with_self_healing(
                content=sample_content,
                theme=theme,
                output_filename=output_file,
                enable_guardian=False
            )

            assert result.status.name == "SUCCESS", f"Build failed for theme: {theme}"
            output_path = Path(__file__).parent.parent / "output" / output_file
            assert output_path.exists(), f"Output not created for theme: {theme}"


class TestE2EPerformance:
    """Test performance characteristics"""

    def test_build_performance(self, tmp_path):
        """Test build completes in reasonable time"""
        import time

        content = {
            "brand_name": "Performance Test",
            "hero": {"title": "Performance Test", "subtitle": "Speed check"},
            "body": {
                "sections": [
                    {"title": f"Section {i}", "content": f"Content {i}" * 50}
                    for i in range(10)
                ]
            }
        }

        output_file = "perf_test.html"

        start = time.time()
        engine = TrinityEngine()
        result = engine.build_with_self_healing(
            content=content,
            theme="brutalist",
            output_filename=output_file,
            enable_guardian=False
        )
        duration = time.time() - start

        assert result.status.name == "SUCCESS"
        assert duration < 10.0, f"Build took too long: {duration:.2f}s"

    def test_prediction_performance(self):
        """Test prediction is fast"""
        import time

        content = {
            "brand_name": "Perf Test",
            "hero": {"title": "Test", "subtitle": "Perf"},
            "body": {"sections": [{"title": "Test", "content": "Test content"}]}
        }

        model_path = Path(__file__).parent.parent / "models"
        predictor = LayoutRiskPredictor(model_dir=str(model_path))
        
        if not predictor.model:
            pytest.skip("No trained model available")

        start = time.time()
        result = predictor.predict_best_strategy(content, theme="brutalist")
        duration = time.time() - start

        assert duration < 1.0, f"Prediction took too long: {duration:.2f}s"
        assert "strategy_id" in result


class TestE2ERobustness:
    """Test robustness and error handling"""

    def test_empty_content_handling(self, tmp_path):
        """Test handling of empty content"""
        content = {
            "brand_name": "Empty Test",
            "hero": {"title": "Empty", "subtitle": "Test"},
            "body": {"sections": []}
        }
        
        output_file = "empty_test.html"

        engine = TrinityEngine()
        result = engine.build_with_self_healing(
            content=content,
            theme="brutalist",
            output_filename=output_file,
            enable_guardian=False
        )

        # Should handle gracefully
        assert result.status.name in ["SUCCESS", "FAILED"]

    def test_corrupted_model_handling(self):
        """Test handling when model is unavailable"""
        predictor = LayoutRiskPredictor(model_dir="/nonexistent/path")
        
        content = {
            "brand_name": "Corrupted Model Test",
            "hero": {"title": "Test", "subtitle": "Test"},
            "body": {"sections": [{"title": "Test", "content": "Content"}]}
        }

        # Should handle gracefully without crashing
        result = predictor.predict_best_strategy(content, theme="brutalist")
        
        # Should return fallback strategy
        assert "strategy_id" in result
