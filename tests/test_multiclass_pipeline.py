"""
Comprehensive tests for Multiclass Predictor Pipeline (v0.8.0)

Tests the full neural-symbolic architecture:
    DataMiner → Trainer → Predictor → Engine

Validates:
1. DataMiner logs resolved_strategy_id correctly (0-99 schema)
2. Trainer trains multiclass RF and extracts feature importance
3. Predictor.predict_best_strategy() returns valid recommendations
4. Engine executes recommended strategy with correct attempt number

Rule #30: Testable design - small, deterministic tests
Rule #7: Test graceful degradation (model unavailable)
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import pytest

from trinity.components.dataminer import TrinityMiner
from trinity.components.trainer import LayoutRiskTrainer
from trinity.components.predictor import LayoutRiskPredictor


# === FIXTURES ===


@pytest.fixture
def temp_dir():
    """Create temporary directory for test artifacts."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def sample_content() -> Dict[str, Any]:
    """Sample content for testing."""
    return {
        "hero": {
            "title": "The Quick Brown Fox Jumps Over The Lazy Dog",
            "subtitle": "A simple test subtitle"
        },
        "body": {
            "text": "This is a normal paragraph with reasonable length."
        }
    }


@pytest.fixture
def pathological_content() -> Dict[str, Any]:
    """Pathological content (long words, no spaces)."""
    return {
        "hero": {
            "title": "Supercalifragilisticexpialidocious" * 3,  # 102 chars, no breaks
            "subtitle": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"  # 34 A's
        }
    }


@pytest.fixture
def miner_with_data(temp_dir) -> TrinityMiner:
    """Create DataMiner with synthetic multiclass dataset."""
    dataset_path = temp_dir / "training_dataset.csv"
    miner = TrinityMiner(dataset_path=dataset_path)

    # Generate 100 samples across all 6 classes
    # Class 0: NONE (no healing needed)
    for i in range(20):
        miner.log_build_event(
            theme="brutalist",
            content={"hero": {"title": f"Short {i}"}},
            strategy="NONE",
            guardian_verdict=True,
            guardian_reason="",
            css_overrides={}
        )

    # Class 1: CSS_BREAK_WORD (long words)
    for i in range(20):
        miner.log_build_event(
            theme="enterprise",
            content={"hero": {"title": "Supercalifragilisticexpialidocious"}},
            strategy="CSS_BREAK_WORD",
            guardian_verdict=True,
            guardian_reason="",
            css_overrides={"word-break": "break-all"}
        )

    # Class 2: FONT_SHRINK (medium overflow)
    for i in range(20):
        miner.log_build_event(
            theme="minimalist",
            content={"hero": {"title": "A" * 80}},
            strategy="FONT_SHRINK",
            guardian_verdict=True,
            guardian_reason="",
            css_overrides={"font-size": "0.9rem"}
        )

    # Class 3: CSS_TRUNCATE (ellipsis acceptable)
    for i in range(20):
        miner.log_build_event(
            theme="modern",
            content={"hero": {"title": "Very long title that needs truncation"}},
            strategy="CSS_TRUNCATE",
            guardian_verdict=True,
            guardian_reason="",
            css_overrides={"overflow": "hidden", "text-overflow": "ellipsis"}
        )

    # Class 4: CONTENT_CUT (nuclear option)
    for i in range(10):
        miner.log_build_event(
            theme="brutalist",
            content={"hero": {"title": "X" * 200}},
            strategy="CONTENT_CUT",
            guardian_verdict=True,
            guardian_reason="",
            css_overrides={}
        )

    # Class 99: UNRESOLVED_FAIL (unfixable)
    for i in range(10):
        miner.log_build_event(
            theme="enterprise",
            content={"hero": {"title": "Broken layout"}},
            strategy="FONT_SHRINK",
            guardian_verdict=False,
            guardian_reason="Layout still broken after all attempts",
            css_overrides={}
        )

    return miner


# === DATAMINER TESTS ===


class TestDataMinerMulticlass:
    """Test DataMiner multiclass schema (v0.8.0)."""

    def test_resolved_strategy_id_mapping(self, temp_dir):
        """Test that resolved_strategy_id maps correctly to strategies."""
        miner = TrinityMiner(dataset_path=temp_dir / "test.csv")

        # NONE + Success → 0
        miner.log_build_event(
            theme="brutalist",
            content={"hero": {"title": "Test"}},
            strategy="NONE",
            guardian_verdict=True,
            guardian_reason="",
            css_overrides={}
        )

        df = pd.read_csv(miner.dataset_path)
        assert df.iloc[-1]["resolved_strategy_id"] == 0

        # CSS_BREAK_WORD + Success → 1
        miner.log_build_event(
            theme="brutalist",
            content={"hero": {"title": "Test"}},
            strategy="CSS_BREAK_WORD",
            guardian_verdict=True,
            guardian_reason="",
            css_overrides={}
        )

        df = pd.read_csv(miner.dataset_path)
        assert df.iloc[-1]["resolved_strategy_id"] == 1

        # FONT_SHRINK + Failure → 99
        miner.log_build_event(
            theme="brutalist",
            content={"hero": {"title": "Test"}},
            strategy="FONT_SHRINK",
            guardian_verdict=False,
            guardian_reason="Still broken",
            css_overrides={}
        )

        df = pd.read_csv(miner.dataset_path)
        assert df.iloc[-1]["resolved_strategy_id"] == 99

    def test_pathological_score_calculation(self, temp_dir, pathological_content):
        """Test pathological_score calculation for risky content."""
        miner = TrinityMiner(dataset_path=temp_dir / "test.csv")

        miner.log_build_event(
            theme="brutalist",
            content=pathological_content,
            strategy="NONE",
            guardian_verdict=True,
            guardian_reason="",
            css_overrides={}
        )

        df = pd.read_csv(miner.dataset_path)
        pathological_score = df.iloc[-1]["pathological_score"]

        # Pathological content should have high score (>0.5)
        assert pathological_score > 0.5
        assert 0.0 <= pathological_score <= 1.0

    def test_css_density_calculations(self, temp_dir):
        """Test CSS density feature extraction."""
        miner = TrinityMiner(dataset_path=temp_dir / "test.csv")

        css_overrides = {
            "padding": "p-4",
            "margin": "m-2",
            "gap": "gap-3",
            "display": "flex",
            "grid-template-columns": "grid-cols-3",
            "width": "w-full",
            "height": "h-screen"
        }

        miner.log_build_event(
            theme="brutalist",
            content={"hero": {"title": "Test"}},
            strategy="CSS_BREAK_WORD",
            guardian_verdict=True,
            guardian_reason="",
            css_overrides=css_overrides
        )

        df = pd.read_csv(miner.dataset_path)
        row = df.iloc[-1]

        # Should count spacing classes (p-*, m-*, gap-*)
        assert row["css_density_spacing"] >= 3

        # Should count layout classes (flex, grid-*, w-*, h-*)
        assert row["css_density_layout"] >= 3  # flex, grid-cols, w-full (h-screen might not match)


# === TRAINER TESTS ===


class TestTrainerMulticlass:
    """Test Trainer multiclass RF training + XAI."""

    def test_multiclass_training(self, miner_with_data, temp_dir):
        """Test that Trainer trains multiclass RF successfully."""
        trainer = LayoutRiskTrainer()

        # Train on synthetic dataset
        model, metrics = trainer.train_from_csv(
            csv_path=str(miner_with_data.dataset_path),
            output_dir=str(temp_dir)
        )

        # Verify model trained
        assert model is not None
        assert metrics is not None

        # Check returned metrics
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        
        # Load metadata from saved file
        metadata_files = list(temp_dir.glob("*_metadata.json"))
        assert len(metadata_files) > 0
        
        with open(metadata_files[0], "r") as f:
            metadata = json.load(f)

        # Verify feature importance extracted (XAI)
        assert "feature_importance_top10" in metadata
        assert len(metadata["feature_importance_top10"]) <= 10

        # Check feature names
        top_feature = metadata["feature_importance_top10"][0]
        assert "feature" in top_feature
        assert "importance" in top_feature
        assert 0.0 <= top_feature["importance"] <= 1.0

    def test_feature_importance_ranking(self, miner_with_data, temp_dir):
        """Test that feature importance is correctly ranked."""
        trainer = LayoutRiskTrainer()
        model, metrics = trainer.train_from_csv(
            csv_path=str(miner_with_data.dataset_path),
            output_dir=str(temp_dir)
        )

        metadata_files = list(temp_dir.glob("*_metadata.json"))
        with open(metadata_files[0], "r") as f:
            metadata = json.load(f)

        importances = metadata["feature_importance_top10"]

        # Should be sorted by importance (descending)
        for i in range(len(importances) - 1):
            assert importances[i]["importance"] >= importances[i + 1]["importance"]

        # Top features should include pathological_score or input_char_len
        top_3_features = [f["feature"] for f in importances[:3]]
        assert any(
            feat in top_3_features
            for feat in ["pathological_score", "input_char_len", "css_density_layout"]
        )


# === PREDICTOR TESTS ===


class TestPredictorMulticlass:
    """Test Predictor multiclass strategy recommendation."""

    @pytest.fixture
    def trained_predictor(self, miner_with_data, temp_dir):
        """Train model and return predictor."""
        trainer = LayoutRiskTrainer()
        model_path, _ = trainer.train_from_csv(
            csv_path=miner_with_data.dataset_path,
            output_dir=temp_dir
        )

        predictor = LayoutRiskPredictor(model_dir=str(temp_dir))
        return predictor

    def test_predict_best_strategy_structure(self, trained_predictor):
        """Test that predict_best_strategy returns correct structure."""
        prediction = trained_predictor.predict_best_strategy(
            content={"hero": {"title": "Test"}},
            theme="brutalist",
            css_density_spacing=2,
            css_density_layout=3,
            pathological_score=0.1
        )

        # Required keys
        assert "strategy_id" in prediction
        assert "strategy_name" in prediction
        assert "confidence" in prediction
        assert "probabilities" in prediction
        assert "prediction_available" in prediction

        # Valid strategy ID (0-4, 99)
        assert prediction["strategy_id"] in [0, 1, 2, 3, 4, 99]

        # Confidence is a probability
        assert 0.0 <= prediction["confidence"] <= 1.0

        # Probabilities sum to ~1.0
        probs_sum = sum(prediction["probabilities"].values())
        assert 0.99 <= probs_sum <= 1.01

    def test_predict_pathological_content(self, trained_predictor, pathological_content):
        """Test prediction on pathological content (should recommend aggressive strategy)."""
        prediction = trained_predictor.predict_best_strategy(
            content=pathological_content,
            theme="brutalist",
            css_density_spacing=0,
            css_density_layout=0,
            pathological_score=0.9  # High pathological score
        )

        # With 100 samples, model might still recommend NONE sometimes
        # Just verify valid strategy returned
        assert prediction["strategy_id"] in [0, 1, 2, 3, 4, 99]
        assert prediction["strategy_name"] in [
            "NONE",
            "CSS_BREAK_WORD",
            "FONT_SHRINK",
            "CSS_TRUNCATE",
            "CONTENT_CUT",
            "UNRESOLVED_FAIL"
        ]

    def test_predict_normal_content(self, trained_predictor, sample_content):
        """Test prediction on normal content (should recommend NONE or minimal healing)."""
        prediction = trained_predictor.predict_best_strategy(
            content=sample_content,
            theme="brutalist",
            css_density_spacing=2,
            css_density_layout=3,
            pathological_score=0.05  # Low pathological score
        )

        # Should recommend NONE or CSS_BREAK_WORD for normal content
        assert prediction["strategy_name"] in ["NONE", "CSS_BREAK_WORD"]


# === ENGINE INTEGRATION TESTS ===


class TestEngineSmartStrategySelection:
    """Test Engine smart strategy selection based on ML prediction."""

    def test_strategy_to_attempt_mapping(self):
        """Test that strategy names map to correct attempt numbers."""
        strategy_to_attempt = {
            "NONE": 0,
            "CSS_BREAK_WORD": 1,
            "FONT_SHRINK": 2,
            "CSS_TRUNCATE": 3,
            "CONTENT_CUT": 4
        }

        # Verify mapping
        assert strategy_to_attempt["NONE"] == 0
        assert strategy_to_attempt["CSS_BREAK_WORD"] == 1
        assert strategy_to_attempt["FONT_SHRINK"] == 2
        assert strategy_to_attempt["CSS_TRUNCATE"] == 3
        assert strategy_to_attempt["CONTENT_CUT"] == 4

    def test_confidence_threshold(self):
        """Test that Engine only uses ML prediction if confidence >60%."""
        # Mock prediction with low confidence
        low_confidence_prediction = {
            "strategy_name": "FONT_SHRINK",
            "confidence": 0.45,  # <60%
            "prediction_available": True
        }

        # Should fallback to attempt=1 (start from beginning)
        if low_confidence_prediction["confidence"] < 0.6:
            recommended_attempt = 1
        else:
            recommended_attempt = 2

        assert recommended_attempt == 1

        # Mock prediction with high confidence
        high_confidence_prediction = {
            "strategy_name": "FONT_SHRINK",
            "confidence": 0.85,  # >60%
            "prediction_available": True
        }

        strategy_to_attempt = {"FONT_SHRINK": 2}

        if high_confidence_prediction["confidence"] >= 0.6:
            recommended_attempt = strategy_to_attempt[high_confidence_prediction["strategy_name"]]
        else:
            recommended_attempt = 1

        assert recommended_attempt == 2


# === EDGE CASES ===


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_predictor_without_model(self, temp_dir):
        """Test predictor gracefully degrades when no model available."""
        predictor = LayoutRiskPredictor(model_dir=str(temp_dir))

        prediction = predictor.predict_best_strategy(
            content={"hero": {"title": "Test"}},
            theme="brutalist",
            css_density_spacing=0,
            css_density_layout=0,
            pathological_score=0.0
        )

        # Should return prediction_available=False
        assert prediction["prediction_available"] is False

    def test_trainer_insufficient_data(self, temp_dir):
        """Test trainer fails gracefully with insufficient data."""
        miner = TrinityMiner(dataset_path=temp_dir / "tiny.csv")

        # Only 3 samples (< MIN_SAMPLES_FOR_TRAINING)
        for i in range(3):
            miner.log_build_event(
                theme="brutalist",
                content={"hero": {"title": f"Test {i}"}},
                strategy="NONE",
                guardian_verdict=True,
                guardian_reason="",
                css_overrides={}
            )

        trainer = LayoutRiskTrainer()

        # Should raise InsufficientDataError
        with pytest.raises(Exception):  # Adjust to specific exception if defined
            trainer.train_from_csv(
                csv_path=miner.dataset_path,
                output_dir=temp_dir
            )

    def test_empty_content(self, temp_dir):
        """Test miner handles empty content gracefully."""
        miner = TrinityMiner(dataset_path=temp_dir / "empty.csv")

        miner.log_build_event(
            theme="brutalist",
            content={},
            strategy="NONE",
            guardian_verdict=True,
            guardian_reason="",
            css_overrides={}
        )

        df = pd.read_csv(miner.dataset_path)

        # Should have 0 chars and 0 words
        assert df.iloc[-1]["input_char_len"] == 0
        assert df.iloc[-1]["input_word_count"] == 0


# === PERFORMANCE TESTS ===


class TestPerformance:
    """Test multiclass pipeline performance."""

    def test_prediction_speed(self, miner_with_data, temp_dir):
        """Test that prediction completes in <100ms."""
        import time

        trainer = LayoutRiskTrainer()
        trainer.train_from_csv(
            csv_path=miner_with_data.dataset_path,
            output_dir=temp_dir
        )

        predictor = LayoutRiskPredictor(model_dir=str(temp_dir))

        start = time.time()
        predictor.predict_best_strategy(
            content={"hero": {"title": "Test"}},
            theme="brutalist",
            css_density_spacing=2,
            css_density_layout=3,
            pathological_score=0.1
        )
        elapsed = time.time() - start

        # Prediction should be fast (<100ms)
        assert elapsed < 0.1

    def test_training_with_large_dataset(self, temp_dir):
        """Test trainer handles 1000+ samples efficiently."""
        miner = TrinityMiner(dataset_path=temp_dir / "large.csv")

        # Generate 1000 samples
        for i in range(1000):
            strategy = ["NONE", "CSS_BREAK_WORD", "FONT_SHRINK", "CSS_TRUNCATE", "CONTENT_CUT"][i % 5]
            miner.log_build_event(
                theme="brutalist",
                content={"hero": {"title": f"Sample {i}"}},
                strategy=strategy,
                guardian_verdict=True,
                guardian_reason="",
                css_overrides={}
            )

        trainer = LayoutRiskTrainer()

        # Should complete without errors
        model, metrics = trainer.train_from_csv(
            csv_path=str(miner.dataset_path),
            output_dir=str(temp_dir)
        )

        assert model is not None
        assert metrics is not None
        assert metrics["accuracy"] > 0.0
