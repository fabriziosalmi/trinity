"""
Trinity ML Predictor - Phase 3: The Pre-Cognition Layer

Loads trained Random Forest model and predicts layout breakage risk
BEFORE rendering, enabling pre-emptive healing strategies.

Architecture:
    Input: (content, theme, css_signature) → Feature Engineering
    Model: Trained Random Forest Classifier (.pkl from trainer.py)
    Output: Probability of failure (0.0 - 1.0)
    
    If risk > 0.7 (70% chance of breakage):
        → Skip NONE strategy
        → Apply CSS_BREAK_WORD immediately
        → Save 1-2 seconds per risky build

⚠️  SECURITY WARNING (Rule #6):
    This module loads pickle-serialized models (.pkl files).
    NEVER load models from untrusted sources - pickle can execute arbitrary code.
    Verify model integrity and source before loading in production.

Rule #7: Graceful degradation if model unavailable (fallback to heuristics).
Rule #66: Load model once per execution (Singleton pattern).
"""
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import json
import numpy as np
import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier

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
                    encoder.classes_ = np.array(classes)  # Convert list back to numpy array
                    self.label_encoders[feature] = encoder
                    self.label_encoders[feature] = encoder
        
        self.is_loaded = True
        logger.info(f"✅ Model loaded successfully")
        logger.info(f"   F1-Score: {self.metadata.get('f1_score', 'N/A'):.3f}")
    
    def _prepare_features(
        self, 
        content: Dict[str, Any], 
        theme: str,
        css_signature: str = "NONE"
    ) -> Optional[list]:
        """
        Prepare features for prediction (MUST match Trainer preprocessing).
        
        Args:
            content: Content dictionary
            theme: Theme name
            css_signature: Current CSS healing strategy
            
        Returns:
            Feature list [char_len, word_count, theme_encoded, strategy_encoded]
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
                strategy_encoded = self.label_encoders["active_strategy"].transform([css_signature])[0]
            else:
                strategy_encoded = hash(css_signature) % 100
                logger.warning(f"⚠️  Strategy encoder not found, using hash fallback")
        except ValueError:
            logger.warning(f"⚠️  Unseen strategy '{css_signature}', using fallback encoding")
            strategy_encoded = -1
        
        return [char_len, word_count, theme_encoded, strategy_encoded]
    
    def predict_risk(
        self, 
        content: Dict[str, Any], 
        theme: str,
        css_signature: str = "NONE"
    ) -> Tuple[float, bool]:
        """
        Predict layout breakage risk.
        
        Args:
            content: Content dictionary
            theme: Theme name
            css_signature: Current CSS healing strategy
            
        Returns:
            Tuple of (risk_score, prediction_available)
            - risk_score: 0.0 - 1.0 (probability of failure)
            - prediction_available: True if model loaded, False if fallback
        """
        # Rule #7: Graceful degradation if model not loaded
        if not self.is_loaded or self.model is None:
            logger.debug("Predictor in fallback mode (no model)")
            return (0.5, False)  # Neutral prediction
        
        try:
            # Prepare features
            features = self._prepare_features(content, theme, css_signature)
            
            if features is None:
                logger.error("Feature preparation failed")
                return (0.5, False)
            
            # Predict probability of class 0 (Failure)
            # Model.predict_proba returns [[prob_class_0, prob_class_1]]
            proba = self.model.predict_proba([features])[0]
            
            # Risk = probability of failure (class 0)
            risk_score = proba[0]
            
            logger.debug(f"🔮 Predicted risk: {risk_score:.2%} (theme={theme}, char_len={features[0]})")
            
            return (risk_score, True)
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            return (0.5, False)  # Fallback to neutral
    
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
                "confidence": risk_score
            }
        elif risk_score >= 0.5:
            return {
                "skip_none_strategy": False,
                "reason": f"Moderate risk ({risk_score:.0%}). Attempting normal build with Guardian enabled.",
                "confidence": risk_score
            }
        else:
            return {
                "skip_none_strategy": False,
                "reason": f"Low risk ({risk_score:.0%}). Proceeding with standard build.",
                "confidence": 1 - risk_score
            }
