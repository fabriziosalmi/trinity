"""
Trinity ML Predictor - Phase 3: The Pre-Cognition Layer (v0.8.0 Multiclass)

Loads trained Random Forest model and predicts WHICH healing strategy to use
BEFORE rendering, enabling smart pre-emptive healing.

Architecture (v0.8.0):
    Input: (content, theme, css_density, pathological_score) → Feature Engineering
    Model: Trained Random Forest Multiclass Classifier (.pkl from trainer.py)
    Output: Best strategy recommendation (0=NONE, 1=BREAK_WORD, 2=FONT_SHRINK,
                                          3=TRUNCATE, 4=CONTENT_CUT)

    Multiclass Output:
        - Strategy ID with highest probability
        - Confidence scores for all strategies
        - Actionable recommendation for Engine

    If model recommends FONT_SHRINK (ID=2):
        → Skip NONE and CSS_BREAK_WORD
        → Start directly with FONT_SHRINK
        → Save 2-3 healing iterations

⚠️  SECURITY WARNING (Rule #6):
    This module loads pickle-serialized models (.pkl files).
    NEVER load models from untrusted sources - pickle can execute arbitrary code.
    Verify model integrity and source before loading in production.

Rule #7: Graceful degradation if model unavailable (fallback to heuristics).
Rule #66: Load model once per execution (Singleton pattern).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib  # type: ignore
import numpy as np
import pandas as pd  # type: ignore
from sklearn.ensemble import RandomForestClassifier  # type: ignore
from sklearn.preprocessing import LabelEncoder  # type: ignore

from trinity.utils.logger import get_logger

logger = get_logger(__name__)


class LayoutRiskPredictor:
    """
    Predicts layout breakage risk using trained ML model.

    Implements Rule #7 (Graceful Degradation) and Rule #66 (Load Once).
    """

    def __init__(self, model_dir: str = "models/"):
        """
        Initialize predictor.

        Args:
            model_dir: Directory containing trained models
        """
        self.model_dir = Path(model_dir)
        self.model: Optional[RandomForestClassifier] = None
        self.metadata: Optional[Dict[str, Any]] = None
        self.label_encoders: Dict[str, LabelEncoder] = {}
        self.is_loaded = False

        # Try to load model automatically
        try:
            self._load_latest_model()
        except Exception as e:
            logger.warning(f"⚠️  No trained model available: {e}")
            logger.info("   Predictor will operate in fallback mode (heuristic-only)")

    def _load_latest_model(self) -> None:
        """
        Find and load the most recent .pkl model.

        Raises:
            FileNotFoundError: If no models found
            Exception: If model loading fails
        """
        if not self.model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {self.model_dir}")

        # Find all .pkl files
        model_files = sorted(self.model_dir.glob("layout_risk_predictor_*.pkl"))

        if not model_files:
            raise FileNotFoundError(f"No trained models found in {self.model_dir}")

        # Get latest (sorted by filename timestamp)
        latest_model = model_files[-1]
        metadata_file = latest_model.with_suffix(".json").with_name(
            latest_model.stem + "_metadata.json"
        )

        logger.info(f"🔮 Loading ML model: {latest_model.name}")

        # ⚠️  SECURITY WARNING: Pickle files can execute arbitrary code
        # Only load models from trusted sources. Verify model integrity before loading.
        logger.warning("⚠️  SECURITY: Loading pickle model. Only load from trusted sources.")

        # Load model
        self.model = joblib.load(latest_model)

        # Load metadata (contains LabelEncoders)
        if not metadata_file.exists():
            logger.warning(f"⚠️  Metadata file not found: {metadata_file}")
            logger.warning("   Proceeding without label encoder mapping (may cause errors)")
            self.metadata = {}
        else:
            with open(metadata_file, "r") as f:
                self.metadata = json.load(f)

            # Reconstruct LabelEncoders from metadata
            if "label_encoders" in self.metadata:
                for feature, classes in self.metadata["label_encoders"].items():
                    encoder = LabelEncoder()
                    encoder.classes_ = np.array(
                        classes, dtype=object
                    )  # Convert list to numpy array
                    self.label_encoders[feature] = encoder

        self.is_loaded = True
        logger.info("✅ Model loaded successfully")

        # Safe F1-Score logging
        metrics = self.metadata.get("metrics", {})
        f1_score = metrics.get("f1_score", "N/A") if isinstance(metrics, dict) else "N/A"
        if isinstance(f1_score, (int, float)):
            logger.info(f"   F1-Score: {f1_score:.3f}")
        else:
            logger.info(f"   F1-Score: {f1_score}")

    def _prepare_features(
        self,
        content: Dict[str, Any],
        theme: str,
        css_signature: str = "NONE",
        css_density_spacing: int = 0,
        css_density_layout: int = 0,
        pathological_score: float = 0.0,
    ) -> Optional[List[Any]]:
        """
        Prepare features for prediction (v0.8.0: MUST match Trainer preprocessing).

        Args:
            content: Content dictionary
            theme: Theme name
            css_signature: Current CSS healing strategy
            css_density_spacing: Count of spacing classes (NEW v0.8.0)
            css_density_layout: Count of layout classes (NEW v0.8.0)
            pathological_score: Risk score for pathological strings (NEW v0.8.0)

        Returns:
            Feature list matching trainer's feature_columns:
            [char_len, word_count, css_density_spacing, css_density_layout,
             pathological_score, theme_encoded, strategy_encoded]
            or None if encoding fails
        """
        # Calculate char_len and word_count (same as TrinityMiner)
        char_len = sum(len(str(v)) for v in content.values() if isinstance(v, str))

        # Word count approximation
        text_blob = " ".join(str(v) for v in content.values() if isinstance(v, str))
        word_count = len(text_blob.split())

        # Encode theme (Rule #7: Handle unseen labels gracefully)
        try:
            if "theme" in self.label_encoders:
                theme_encoded = self.label_encoders["theme"].transform([theme])[0]
            else:
                # Fallback: Use hash (consistent but not ideal)
                theme_encoded = hash(theme) % 100
                logger.warning(f"⚠️  Theme '{theme}' encoder not found, using hash fallback")
        except ValueError:
            # Theme not seen during training (unseen label)
            logger.warning(f"⚠️  Unseen theme '{theme}', using fallback encoding")
            theme_encoded = -1  # Special "unknown" encoding

        # Encode strategy
        try:
            if "active_strategy" in self.label_encoders:
                strategy_encoded = self.label_encoders["active_strategy"].transform(
                    [css_signature]
                )[0]
            else:
                strategy_encoded = hash(css_signature) % 100
                logger.warning("⚠️  Strategy encoder not found, using hash fallback")
        except ValueError:
            logger.warning(f"⚠️  Unseen strategy '{css_signature}', using fallback encoding")
            strategy_encoded = -1

        # v0.8.0: Return features in same order as trainer
        # [input_char_len, input_word_count, css_density_spacing, css_density_layout,
        #  pathological_score, theme_encoded, strategy_encoded]
        return [
            char_len,
            word_count,
            css_density_spacing,
            css_density_layout,
            pathological_score,
            theme_encoded,
            strategy_encoded,
        ]

    def predict_risk(
        self, content: Dict[str, Any], theme: str, css_signature: str = "NONE"
    ) -> Tuple[float, bool]:
        """
        Predict layout breakage risk (DEPRECATED: use predict_best_strategy for v0.8.0).

        Args:
            content: Content dictionary
            theme: Theme name
            css_signature: Current CSS healing strategy

        Returns:
            Tuple of (risk_score, prediction_available)
            - risk_score: 0.0 - 1.0 (probability of failure)
            - prediction_available: True if model loaded, False if fallback
        """
        logger.warning(
            "⚠️  predict_risk() is DEPRECATED. Use predict_best_strategy() for multiclass."
        )

        # Rule #7: Graceful degradation if model not loaded
        if not self.is_loaded or self.model is None:
            logger.debug("Predictor in fallback mode (no model)")
            return (0.5, False)  # Neutral prediction

        try:
            # Prepare features (v0.8.0: use defaults for new features)
            features = self._prepare_features(content, theme, css_signature)

            if features is None:
                logger.error("Feature preparation failed")
                return (0.5, False)

            # Predict probability with DataFrame (eliminates sklearn warnings)
            feature_names = [
                "input_char_len",
                "input_word_count",
                "css_density_spacing",
                "css_density_layout",
                "pathological_score",
                "theme_encoded",
                "active_strategy_encoded",
            ]
            X = pd.DataFrame([features], columns=feature_names)
            proba = self.model.predict_proba(X)[0]

            # For binary compatibility: return prob of failure (first class or max prob)
            risk_score = max(proba) if len(proba) > 2 else proba[0]

            logger.debug(
                f"🔮 Predicted risk: {risk_score:.2%} (theme={theme}, char_len={features[0]})"
            )

            return (risk_score, True)

        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            return (0.5, False)  # Fallback to neutral

    def predict_best_strategy(
        self,
        content: Dict[str, Any],
        theme: str,
        css_density_spacing: int = 0,
        css_density_layout: int = 0,
        pathological_score: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Predict best healing strategy using multiclass model (v0.8.0).

        Args:
            content: Content dictionary
            theme: Theme name
            css_density_spacing: Count of spacing classes
            css_density_layout: Count of layout classes
            pathological_score: Pathological string risk score

        Returns:
            Dict with:
                - strategy_id: Recommended strategy ID (0-4, 99)
                - strategy_name: Human-readable name (NONE, CSS_BREAK_WORD, etc.)
                - confidence: Confidence score (0.0-1.0)
                - probabilities: Dict of all strategy probabilities
                - prediction_available: Whether model was available
        """
        # Strategy ID to name mapping
        STRATEGY_MAP = {
            0: "NONE",
            1: "CSS_BREAK_WORD",
            2: "FONT_SHRINK",
            3: "CSS_TRUNCATE",
            4: "CONTENT_CUT",
            99: "UNRESOLVED_FAIL",
        }

        # Rule #7: Graceful degradation if model not loaded
        if not self.is_loaded or self.model is None:
            logger.debug("Predictor in fallback mode (no model)")
            return {
                "strategy_id": 1,  # Default to CSS_BREAK_WORD
                "strategy_name": "CSS_BREAK_WORD",
                "confidence": 0.5,
                "probabilities": {},
                "prediction_available": False,
            }

        try:
            # Prepare features
            features = self._prepare_features(
                content, theme, "NONE", css_density_spacing, css_density_layout, pathological_score
            )

            if features is None:
                logger.error("Feature preparation failed")
                return {
                    "strategy_id": 1,
                    "strategy_name": "CSS_BREAK_WORD",
                    "confidence": 0.5,
                    "probabilities": {},
                    "prediction_available": False,
                }

            # Multiclass prediction with DataFrame (eliminates sklearn warnings)
            feature_names = [
                "input_char_len",
                "input_word_count",
                "css_density_spacing",
                "css_density_layout",
                "pathological_score",
                "theme_encoded",
                "active_strategy_encoded",
            ]
            X = pd.DataFrame([features], columns=feature_names)

            proba = self.model.predict_proba(X)[0]
            predicted_class = self.model.predict(X)[0]

            # Build probability dict using model.classes_ (handles non-contiguous labels like 0,99)
            probabilities = {
                STRATEGY_MAP.get(int(class_id), f"UNKNOWN_{class_id}"): float(prob)
                for class_id, prob in zip(self.model.classes_, proba)
            }

            strategy_id = int(predicted_class)
            strategy_name = STRATEGY_MAP.get(strategy_id, "UNKNOWN")

            # Get confidence from correct position in proba array
            class_index = list(self.model.classes_).index(predicted_class)
            confidence = float(proba[class_index]) if class_index < len(proba) else 0.5

            logger.info(f"🔮 Recommended strategy: {strategy_name} (confidence: {confidence:.2%})")
            logger.debug(f"   All probabilities: {probabilities}")

            return {
                "strategy_id": strategy_id,
                "strategy_name": strategy_name,
                "confidence": confidence,
                "probabilities": probabilities,
                "prediction_available": True,
            }

        except Exception as e:
            logger.error(f"Multiclass prediction failed: {e}", exc_info=True)
            return {
                "strategy_id": 1,
                "strategy_name": "CSS_BREAK_WORD",
                "confidence": 0.5,
                "probabilities": {},
                "prediction_available": False,
            }

    def get_recommendation(self, risk_score: float) -> Dict[str, Any]:
        """
        Convert risk score to actionable recommendation.

        Args:
            risk_score: Risk probability (0.0 - 1.0)

        Returns:
            Dict with: {"skip_none_strategy": bool, "reason": str, "confidence": float}
        """
        if risk_score >= 0.7:
            return {
                "skip_none_strategy": True,
                "reason": f"High breakage risk detected ({risk_score:.0%}). Applying pre-emptive healing.",
                "confidence": risk_score,
            }
        elif risk_score >= 0.5:
            return {
                "skip_none_strategy": False,
                "reason": f"Moderate risk ({risk_score:.0%}). Attempting normal build with Guardian enabled.",
                "confidence": risk_score,
            }
        else:
            return {
                "skip_none_strategy": False,
                "reason": f"Low risk ({risk_score:.0%}). Proceeding with standard build.",
                "confidence": 1 - risk_score,
            }
