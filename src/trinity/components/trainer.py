"""
Trinity Neural Trainer - ML Model Training Pipeline

Production-grade MLOps pipeline for training layout risk prediction models.
Implements Phase 2 of the Neural-Symbolic Architecture.

Architecture:
    Data Collection (Phase 1) → Training (Phase 2) → Inference (Phase 3)

This module focuses on Phase 2: Training a Random Forest classifier to predict
layout breakage from content metrics and CSS features.

⚠️  SECURITY WARNING (Rule #6):
    This module uses joblib (pickle-based) for model serialization.
    NEVER load models from untrusted sources - pickle can execute arbitrary code.
    In production: Use ONNX format or cryptographically sign models.

Anti-Vibecoding Rules Applied:
    - Rule #6: Security-first design (pickle warning)
    - Rule #8: No magic numbers (all hyperparameters in constants)
    - Rule #7: Explicit error handling (no silent failures)
    - Rule #28: Structured logging (JSON-compatible metadata)
    - Rule #30: Testable design (small, pure functions)
    - Rule #43: Simple models first (Random Forest before Neural Networks)
    - Rule #49: Data cleaning with validation

Usage:
    from trinity.components.trainer import LayoutRiskTrainer

    trainer = LayoutRiskTrainer()
    trainer.train_from_csv("data/training_dataset.csv", "models/")
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, cast

import joblib  # type: ignore
import pandas as pd  # type: ignore
from sklearn.ensemble import RandomForestClassifier  # type: ignore
from sklearn.metrics import (  # type: ignore
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split  # type: ignore
from sklearn.preprocessing import LabelEncoder  # type: ignore

from trinity.utils.logger import get_logger

logger = get_logger(__name__)


# === CONSTANTS (Rule #8: No Magic Numbers) ===

# Training hyperparameters
RANDOM_SEED = 42
TEST_SIZE = 0.2
MIN_SAMPLES_FOR_TRAINING = 10

# Random Forest hyperparameters
RF_N_ESTIMATORS = 100
RF_MAX_DEPTH = 10
RF_MIN_SAMPLES_SPLIT = 5
RF_MIN_SAMPLES_LEAF = 2

# Model validation thresholds
MIN_F1_SCORE = 0.6  # Reject models with F1 < 60%
MIN_PRECISION = 0.5
MIN_RECALL = 0.5


# === CUSTOM EXCEPTIONS ===


class InsufficientDataError(Exception):
    """Raised when dataset has too few samples for reliable training."""

    pass


class ModelPerformanceError(Exception):
    """Raised when trained model fails to meet minimum quality thresholds."""

    pass


class DataValidationError(Exception):
    """Raised when dataset has invalid or missing critical features."""

    pass


# === MAIN TRAINER CLASS ===


class LayoutRiskTrainer:
    """
    ML training pipeline for layout risk prediction.

    Trains a Random Forest classifier to predict whether a given
    (content + CSS) combination will break the layout.

    Pipeline:
        1. Load CSV dataset (from DataMiner)
        2. Clean and validate data
        3. Encode categorical features
        4. Train/test split
        5. Train Random Forest
        6. Evaluate performance
        7. Save model + metadata
    """

    def __init__(
        self,
        random_seed: int = RANDOM_SEED,
        test_size: float = TEST_SIZE,
        min_samples: int = MIN_SAMPLES_FOR_TRAINING,
    ):
        """
        Initialize trainer with hyperparameters.

        Args:
            random_seed: Random seed for reproducibility
            test_size: Fraction of data for testing (0.0 - 1.0)
            min_samples: Minimum samples required for training
        """
        self.random_seed = random_seed
        self.test_size = test_size
        self.min_samples = min_samples

        # Will be populated during training
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.feature_columns: list[str] = []

        logger.info(f"🧠 LayoutRiskTrainer initialized (seed={random_seed}, test_size={test_size})")

    def load_and_prep_data(self, csv_path: str) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Load dataset and prepare features/labels.

        Implements Rule #49 (Data Cleaning) and Rule #7 (Error Handling).

        Args:
            csv_path: Path to training_dataset.csv

        Returns:
            Tuple of (X features DataFrame, y labels Series)

        Raises:
            FileNotFoundError: If CSV doesn't exist
            InsufficientDataError: If dataset has < min_samples
            DataValidationError: If critical columns are missing
        """
        from pathlib import Path

        logger.info(f"📂 Loading dataset: {csv_path}")

        # Check file exists
        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"Dataset not found: {csv_path}")

        # Load CSV
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            raise

        logger.info(f"   Loaded {len(df)} samples")

        # Validate minimum samples (Rule #7)
        if len(df) < self.min_samples:
            raise InsufficientDataError(
                f"Dataset has only {len(df)} samples. "
                f"Minimum required: {self.min_samples}. "
                f"Run 'trinity mine-generate --count 1000' to collect more data."
            )

        # Validate critical columns exist (v0.8.0: resolved_strategy_id preferred)
        required_columns = [
            "theme",
            "input_char_len",
            "input_word_count",
            "active_strategy",
        ]
        # Check for multiclass target (preferred) or fallback to binary
        has_multiclass = "resolved_strategy_id" in df.columns
        has_binary = "is_valid" in df.columns

        if not has_multiclass and not has_binary:
            raise DataValidationError(
                "Missing target column: need 'resolved_strategy_id' (multiclass) "
                "or 'is_valid' (binary fallback)"
            )

        missing = set(required_columns) - set(df.columns)
        if missing:
            raise DataValidationError(f"Missing required columns: {missing}")

        # Clean data (Rule #49)
        df = self._clean_data(df)

        # Prepare features and labels
        X, y = self._prepare_features_and_labels(df)

        logger.info(f"✅ Data prepared: X shape={X.shape}, y shape={y.shape}")
        return X, y

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean dataset: handle missing values, remove duplicates, validate types.

        Implements Rule #49 (Data Cleaning with Validation).

        Args:
            df: Raw DataFrame from CSV

        Returns:
            Cleaned DataFrame
        """
        logger.info("🧹 Cleaning data...")

        # Remove rows with missing critical values (v0.8.0: flexible target)
        before_count = len(df)
        critical_cols = ["theme", "input_char_len"]
        # Add target column (multiclass preferred, binary fallback)
        if "resolved_strategy_id" in df.columns:
            critical_cols.append("resolved_strategy_id")
        elif "is_valid" in df.columns:
            critical_cols.append("is_valid")

        df = df.dropna(subset=critical_cols)
        after_count = len(df)

        if before_count > after_count:
            logger.warning(f"   Dropped {before_count - after_count} rows with missing values")

        # Convert numeric columns (v0.8.0: include new density features)
        df["input_char_len"] = pd.to_numeric(df["input_char_len"], errors="coerce")
        df["input_word_count"] = pd.to_numeric(df["input_word_count"], errors="coerce")

        # Handle new v0.8.0 features (fill missing with 0)
        for col in ["css_density_spacing", "css_density_layout", "pathological_score"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Convert target column (multiclass or binary)
        if "resolved_strategy_id" in df.columns:
            df["resolved_strategy_id"] = pd.to_numeric(
                df["resolved_strategy_id"], errors="coerce"
            ).astype(int)
        if "is_valid" in df.columns:
            df["is_valid"] = pd.to_numeric(df["is_valid"], errors="coerce").astype(int)

        # Remove duplicates
        before_count = len(df)
        df = df.drop_duplicates()
        after_count = len(df)

        if before_count > after_count:
            logger.info(f"   Removed {before_count - after_count} duplicate rows")

        # Validate label values (v0.8.0: multiclass 0-4,99 or binary 0-1)
        if "resolved_strategy_id" in df.columns:
            valid_ids = [0, 1, 2, 3, 4, 99]
            invalid_labels = df[~df["resolved_strategy_id"].isin(valid_ids)]
            if len(invalid_labels) > 0:
                logger.warning(
                    f"   Found {len(invalid_labels)} rows with invalid multiclass labels, removing..."
                )
                df = df[df["resolved_strategy_id"].isin(valid_ids)]
        elif "is_valid" in df.columns:
            # Binary validation
            invalid_labels = df[~df["is_valid"].isin([0, 1])]
            if len(invalid_labels) > 0:
                logger.warning(
                    f"   Found {len(invalid_labels)} rows with invalid binary labels, removing..."
                )
                df = df[df["is_valid"].isin([0, 1])]

        logger.info(f"   Clean dataset: {len(df)} samples")
        return df

    def _prepare_features_and_labels(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Extract features (X) and labels (y) from cleaned DataFrame.

        Features (v0.8.0):
            - input_char_len (numeric)
            - input_word_count (numeric)
            - css_density_spacing (numeric) - NEW v0.8.0
            - css_density_layout (numeric) - NEW v0.8.0
            - pathological_score (numeric) - NEW v0.8.0
            - theme (categorical → encoded)
            - active_strategy (categorical → encoded)

        Label (v0.8.0 MULTICLASS):
            - resolved_strategy_id (0=NONE_SUCCESS, 1=CSS_BREAK_WORD, 2=FONT_SHRINK,
                                    3=CSS_TRUNCATE, 4=CONTENT_CUT, 99=UNRESOLVED_FAIL)

        Args:
            df: Cleaned DataFrame

        Returns:
            Tuple of (X features, y labels)
        """
        logger.info("🔧 Preparing features and labels (v0.8.0 multiclass)...")

        # Define feature columns (v0.8.0: add density features)
        numeric_features = [
            "input_char_len",
            "input_word_count",
            "css_density_spacing",  # NEW v0.8.0
            "css_density_layout",  # NEW v0.8.0
            "pathological_score",  # NEW v0.8.0
        ]
        categorical_features = ["theme", "active_strategy"]

        # Handle missing new columns (backward compatibility)
        for col in numeric_features:
            if col not in df.columns:
                logger.warning(f"   Missing column '{col}', filling with 0")
                df[col] = 0

        # Encode categorical features
        df_encoded = df.copy()

        for col in categorical_features:
            if col in df_encoded.columns:
                encoder = LabelEncoder()
                df_encoded[f"{col}_encoded"] = encoder.fit_transform(df_encoded[col].astype(str))
                self.label_encoders[col] = encoder
                logger.debug(f"   Encoded '{col}': {len(encoder.classes_)} unique values")

        # Select feature columns
        self.feature_columns = numeric_features + [f"{col}_encoded" for col in categorical_features]

        X = df_encoded[self.feature_columns]

        # NEW v0.8.0: Use resolved_strategy_id as target (multiclass)
        if "resolved_strategy_id" in df_encoded.columns:
            y = df_encoded["resolved_strategy_id"]
            logger.info("   Using MULTICLASS target: resolved_strategy_id")
        else:
            # Fallback to binary for backward compatibility
            y = df_encoded["is_valid"]
            logger.warning("   Falling back to BINARY target: is_valid (consider re-mining data)")

        logger.info(f"   Features: {self.feature_columns}")
        logger.info(f"   Label distribution: {y.value_counts().to_dict()}")

        return X, y

    def train_model(self, X: pd.DataFrame, y: pd.Series) -> RandomForestClassifier:
        """
        Train Random Forest classifier.

        Implements Rule #43 (Simple Models First) and Rule #8 (No Magic Numbers).

        Args:
            X: Feature matrix
            y: Labels

        Returns:
            Trained RandomForestClassifier
        """
        logger.info("🌲 Training Random Forest classifier...")

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=self.test_size,
            random_state=self.random_seed,
            stratify=y,  # Preserve label distribution
        )

        logger.info(f"   Train samples: {len(X_train)}")
        logger.info(f"   Test samples: {len(X_test)}")

        # Initialize Random Forest with explicit hyperparameters (Rule #8)
        model = RandomForestClassifier(
            n_estimators=RF_N_ESTIMATORS,
            max_depth=RF_MAX_DEPTH,
            min_samples_split=RF_MIN_SAMPLES_SPLIT,
            min_samples_leaf=RF_MIN_SAMPLES_LEAF,
            random_state=self.random_seed,
            n_jobs=-1,  # Use all CPU cores
            verbose=0,
        )

        # Train
        logger.info("   Fitting model...")
        model.fit(X_train, y_train)

        # Evaluate
        logger.info("   Evaluating performance...")
        self._evaluate_model(model, X_test, y_test)

        # Store test sets for later reference
        self._X_test = X_test
        self._y_test = y_test

        return model

    def _evaluate_model(
        self, model: RandomForestClassifier, X_test: pd.DataFrame, y_test: pd.Series
    ) -> Dict[str, float]:
        """
        Evaluate model performance and validate against thresholds.

        v0.8.0: Supports both binary and multiclass evaluation.

        Implements quality gates to prevent deploying garbage models.

        Args:
            model: Trained model
            X_test: Test features
            y_test: Test labels

        Returns:
            Dictionary of metrics

        Raises:
            ModelPerformanceError: If model fails to meet minimum thresholds
        """
        y_pred = model.predict(X_test)

        # Detect if multiclass (more than 2 unique labels OR non-binary labels like 0,99)
        unique_labels = sorted(y_test.unique())
        is_binary = len(unique_labels) == 2 and set(unique_labels) == {0, 1}
        is_multiclass = not is_binary

        # Calculate metrics (use weighted average for multiclass or non-standard binary)
        average_method = "binary" if is_binary else "weighted"

        precision = precision_score(y_test, y_pred, average=average_method, zero_division=0)
        recall = recall_score(y_test, y_pred, average=average_method, zero_division=0)
        f1 = f1_score(y_test, y_pred, average=average_method, zero_division=0)
        accuracy = accuracy_score(y_test, y_pred)

        metrics = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "accuracy": round(accuracy, 4),
            "train_samples": len(self._X_train) if hasattr(self, "_X_train") else 0,
            "test_samples": len(y_test),
        }

        # Log metrics
        logger.info(f"   📊 Metrics ({'multiclass' if is_multiclass else 'binary'}):")
        logger.info(f"      Precision: {metrics['precision']:.4f}")
        logger.info(f"      Recall:    {metrics['recall']:.4f}")
        logger.info(f"      F1-Score:  {metrics['f1_score']:.4f}")
        logger.info(f"      Accuracy:  {metrics['accuracy']:.4f}")

        # Detailed classification report (v0.8.0: per-class metrics for multiclass)
        if is_multiclass:
            logger.info("   📋 Per-Class Performance:")
            # Map strategy IDs to names for readability
            num_classes = len(unique_labels)
            target_names = [
                "NONE",
                "BREAK_WORD",
                "FONT_SHRINK",
                "TRUNCATE",
                "CONTENT_CUT",
                "UNRESOLVED",
            ]
            report = classification_report(
                y_test, y_pred, zero_division=0, target_names=target_names[:num_classes]
            )
            logger.info("\n" + report)
        else:
            logger.debug("\n" + classification_report(y_test, y_pred, zero_division=0))

        # Quality gates (Rule #7: Don't silently accept bad models)
        failures = []
        if metrics["f1_score"] < MIN_F1_SCORE:
            failures.append(f"F1-Score {metrics['f1_score']:.4f} < {MIN_F1_SCORE}")
        if metrics["precision"] < MIN_PRECISION:
            failures.append(f"Precision {metrics['precision']:.4f} < {MIN_PRECISION}")
        if metrics["recall"] < MIN_RECALL:
            failures.append(f"Recall {metrics['recall']:.4f} < {MIN_RECALL}")

        if failures:
            error_msg = "Model quality below minimum thresholds:\n  - " + "\n  - ".join(failures)
            logger.error(f"❌ {error_msg}")
            raise ModelPerformanceError(error_msg)

        logger.info("   ✅ Model passed quality gates")
        return metrics

    def save_model(
        self,
        model: RandomForestClassifier,
        output_dir: Path,
        metrics: Optional[Dict[str, float]] = None,
    ) -> Path:
        """
        Save trained model with versioning and metadata.

        Implements Rule #28 (Structured Metadata) and avoids overwriting.

        Args:
            model: Trained model
            output_dir: Directory to save model
            metrics: Optional metrics to include in metadata

        Returns:
            Path to saved model file
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamped filename (avoid overwriting)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        model_filename = f"layout_risk_predictor_{timestamp}.pkl"
        model_path = output_dir / model_filename

        # ⚠️  SECURITY WARNING: Pickle files can execute arbitrary code
        # Only load models from trusted sources. For production, consider ONNX format.
        logger.info(f"💾 Saving model: {model_path}")
        logger.warning("⚠️  SECURITY: Model uses pickle format. Only load from trusted sources.")
        joblib.dump(model, model_path)

        # Save metadata (Rule #28: Structured Logging)
        metadata: Dict[str, Any] = {
            "model_type": "RandomForestClassifier",
            "model_file": model_filename,
            "timestamp": timestamp,
            "hyperparameters": {
                "n_estimators": RF_N_ESTIMATORS,
                "max_depth": RF_MAX_DEPTH,
                "min_samples_split": RF_MIN_SAMPLES_SPLIT,
                "min_samples_leaf": RF_MIN_SAMPLES_LEAF,
                "random_seed": self.random_seed,
            },
            "feature_columns": self.feature_columns,
            "label_encoders": {
                col: encoder.classes_.tolist() for col, encoder in self.label_encoders.items()
            },
        }

        # NEW v0.8.0: XAI - Feature Importance (Explainability)
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            feature_importance_dict = dict(zip(self.feature_columns, importances))

            # Sort by importance (descending) and take top 10
            sorted_features = sorted(
                feature_importance_dict.items(), key=lambda x: x[1], reverse=True
            )[:10]

            metadata["feature_importance_top10"] = [
                {"feature": name, "importance": round(float(importance), 4)}
                for name, importance in sorted_features
            ]

            logger.info("📊 Top 3 Important Features (XAI):")
            for name, importance in sorted_features[:3]:
                logger.info(f"   {name}: {importance:.4f}")

        if metrics:
            metadata["metrics"] = metrics

        metadata_path = output_dir / f"layout_risk_predictor_{timestamp}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"   Metadata saved: {metadata_path}")
        logger.info("✅ Model training complete!")

        return model_path

    def train_from_csv(
        self, csv_path: str, output_dir: str
    ) -> Tuple[RandomForestClassifier, Dict[str, Any]]:
        """
        End-to-end training pipeline from CSV to saved model.

        This is the main entry point for training.

        Args:
            csv_path: Path to training_dataset.csv (string)
            output_dir: Directory to save trained model (string)

        Returns:
            Tuple of (trained model, metrics dictionary)

        Raises:
            InsufficientDataError: Too few samples
            DataValidationError: Invalid data
            ModelPerformanceError: Model quality below threshold
        """
        from pathlib import Path

        logger.info("🚀 Starting training pipeline...")

        # Convert strings to Path objects
        csv_file = Path(csv_path)
        out_dir = Path(output_dir)

        # Load and prepare data
        X, y = self.load_and_prep_data(str(csv_file))

        # Train model
        model = self.train_model(X, y)

        # Compute final metrics
        metrics: Dict[str, Any] = self._evaluate_model(model, self._X_test, self._y_test)

        # Save model
        model_path = self.save_model(model, out_dir, cast(Dict[str, float], metrics))

        # Add model_path to metrics for CLI display
        metrics["model_path"] = str(model_path)

        return model, metrics
