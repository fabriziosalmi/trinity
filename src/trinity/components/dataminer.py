"""
Trinity Data Miner - ML Dataset Collection Module

This module implements the Neural-Symbolic Learning Pipeline's data collection phase.
Every build event (success or failure) is logged with rich features to train predictive models.

Architecture:
    Traditional Trinity: Heuristic Self-Healing (CSS strategies)
    Future Trinity: ML-Predicted Self-Healing (LSTM/Random Forest)

The miner creates the training dataset that will power:
    - Model A (Risk Assessor): Predicts layout breakage BEFORE rendering
    - Model B (Style Generator): Generates infinite CSS themes from latent space

Dataset Structure (v0.8.0 Multiclass):
    data/training_dataset.csv with columns:
    - timestamp: ISO-8601 build time
    - theme: Theme name (e.g., 'brutalist')
    - input_char_len: Total character count of content
    - input_word_count: Total word count
    - css_signature: Hash of applied CSS overrides
    - css_density_spacing: Count of spacing classes (p-*, m-*, gap-*)
    - css_density_layout: Count of layout classes (flex, grid, w-*, h-*)
    - pathological_score: Risk score for pathological strings (long words, no spaces)
    - active_strategy: Healing strategy applied (or 'NONE')
    - resolved_strategy_id: Multiclass target (0=NONE_SUCCESS, 1=CSS_BREAK_WORD, 2=FONT_SHRINK, 3=CSS_TRUNCATE, 4=CONTENT_CUT, 99=UNRESOLVED_FAIL)
    - is_valid: Guardian verdict (0=Fail, 1=Pass) - DEPRECATED, use resolved_strategy_id
    - failure_reason: Guardian error message (empty if passed)

Usage:
    from trinity.components.dataminer import TrinityMiner

    miner = TrinityMiner()
    miner.log_build_event(
        theme="brutalist",
        content={"hero": {"title": "Test"}},
        strategy="CSS_BREAK_WORD",
        guardian_verdict=True,
        guardian_reason=""
    )
"""

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from trinity.utils.logger import get_logger

logger = get_logger(__name__)


class TrinityMiner:
    """
    Data mining component for ML-ready dataset collection.

    Logs every build event with extracted features suitable for training
    predictive models (Random Forest, LSTM) that can forecast layout stability.
    """

    def __init__(self, dataset_path: Optional[Path] = None):
        """
        Initialize the data miner.

        Args:
            dataset_path: Path to CSV dataset file.
                         Defaults to data/training_dataset.csv
        """
        if dataset_path is None:
            # Default to data/training_dataset.csv
            project_root = Path(__file__).parent.parent.parent.parent
            dataset_path = project_root / "data" / "training_dataset.csv"

        self.dataset_path = dataset_path
        self._ensure_dataset_exists()

        logger.info(f"🗃️  TrinityMiner initialized: {self.dataset_path}")

    def _ensure_dataset_exists(self):
        """Create dataset file with headers if it doesn't exist."""
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if migration needed (v0.5.0: add style_overrides_raw column)
        needs_migration = False
        if self.dataset_path.exists():
            with open(self.dataset_path, "r", encoding="utf-8") as f:
                header = f.readline().strip()
                if "style_overrides_raw" not in header:
                    needs_migration = True
                    logger.warning("⚠️  Dataset schema outdated - migration needed")

        if needs_migration:
            # Backup old file
            backup_path = self.dataset_path.with_suffix(".csv.backup")
            import shutil

            shutil.copy(self.dataset_path, backup_path)
            logger.info(f"📦 Backed up old dataset: {backup_path}")

            # Migrate: add new column with empty values
            self._migrate_schema()

        if not self.dataset_path.exists():
            with open(self.dataset_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Write header row (v0.8.0 multiclass schema)
                writer.writerow(
                    [
                        "timestamp",
                        "theme",
                        "input_char_len",
                        "input_word_count",
                        "css_signature",
                        "css_density_spacing",   # NEW v0.8.0
                        "css_density_layout",    # NEW v0.8.0
                        "pathological_score",    # NEW v0.8.0
                        "active_strategy",
                        "resolved_strategy_id",  # NEW v0.8.0 (multiclass target)
                        "is_valid",             # DEPRECATED (kept for compatibility)
                        "failure_reason",
                        "style_overrides_raw",
                    ]
                )
            logger.info(f"✅ Created new training dataset (v0.8.0 multiclass): {self.dataset_path}")

    def log_build_event(
        self,
        theme: str,
        content: Dict[str, Any],
        strategy: str,
        guardian_verdict: bool,
        guardian_reason: str = "",
        css_overrides: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Log a single build event to the training dataset.

        This is the core data collection method. Called from the engine's
        self-healing loop to record both failures and successes.

        Args:
            theme: Theme name (e.g., 'brutalist', 'enterprise')
            content: Content dictionary passed to builder
            strategy: Healing strategy applied ('NONE', 'CSS_BREAK_WORD', etc.)
            guardian_verdict: True if Guardian approved, False if rejected
            guardian_reason: Error message from Guardian (empty if approved)
            css_overrides: Dictionary of CSS class overrides applied

        Example:
            # Failed build (before healing)
            miner.log_build_event(
                theme="brutalist",
                content=content_dict,
                strategy="NONE",
                guardian_verdict=False,
                guardian_reason="DOM overflow detected"
            )

            # Successful build (after CSS fix)
            miner.log_build_event(
                theme="brutalist",
                content=content_dict,
                strategy="CSS_BREAK_WORD",
                guardian_verdict=True,
                css_overrides={"hero_title": "break-all"}
            )
        """
        try:
            # Extract features
            timestamp = datetime.now(timezone.utc).isoformat()
            char_len = self._calculate_char_count(content)
            word_count = self._calculate_word_count(content)
            css_sig = self._generate_css_signature(css_overrides)
            
            # NEW v0.8.0: CSS density features
            css_density_spacing = self._calculate_css_density_spacing(css_overrides)
            css_density_layout = self._calculate_css_density_layout(css_overrides)
            pathological_score = self._calculate_pathological_score(content)
            
            # NEW v0.8.0: Multiclass target (resolved_strategy_id)
            resolved_strategy_id = self._compute_resolved_strategy_id(
                strategy, guardian_verdict
            )
            
            # DEPRECATED: Keep is_valid for backward compatibility
            is_valid = 1 if guardian_verdict else 0

            # v0.5.0: Serialize actual CSS overrides for LSTM training
            style_overrides_raw = self._serialize_css_overrides(css_overrides)

            # Check for Production environment
            import os
            env = os.environ.get("TRINITY_ENV", "Development")

            if env.lower() == "production":
                # Structured JSON logging to stdout
                log_entry = {
                    "timestamp": timestamp,
                    "event": "build_telemetry",
                    "theme": theme,
                    "input_char_len": char_len,
                    "input_word_count": word_count,
                    "css_signature": css_sig,
                    "css_density_spacing": css_density_spacing,
                    "css_density_layout": css_density_layout,
                    "pathological_score": pathological_score,
                    "active_strategy": strategy,
                    "resolved_strategy_id": resolved_strategy_id,
                    "is_valid": is_valid,
                    "failure_reason": guardian_reason,
                    "style_overrides_raw": style_overrides_raw
                }
                print(json.dumps(log_entry))
            else:
                # Write to CSV (thread-safe append)
                # Use QUOTE_ALL to properly escape JSON strings
                with open(self.dataset_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                    writer.writerow(
                        [
                            timestamp,
                            theme,
                            char_len,
                            word_count,
                            css_sig,
                            css_density_spacing,   # NEW v0.8.0
                            css_density_layout,    # NEW v0.8.0
                            pathological_score,    # NEW v0.8.0
                            strategy,
                            resolved_strategy_id,  # NEW v0.8.0 (multiclass)
                            is_valid,             # DEPRECATED
                            guardian_reason,
                            style_overrides_raw,
                        ]
                    )

            # Log summary
            verdict_emoji = "✅" if guardian_verdict else "❌"
            logger.debug(
                f"📊 Mined: {verdict_emoji} theme={theme}, chars={char_len}, "
                f"strategy={strategy}, resolved_id={resolved_strategy_id}"
            )

        except Exception as e:
            # Don't break the build if mining fails
            logger.error(f"❌ Failed to log build event: {e}")

    def _calculate_char_count(self, content: Dict[str, Any]) -> int:
        """
        Calculate total character count from content dictionary.

        Recursively traverses the content dict and counts all string characters.

        Args:
            content: Content dictionary (e.g., {"hero": {"title": "..."}})

        Returns:
            Total character count
        """
        total = 0

        def count_recursive(obj):
            nonlocal total
            if isinstance(obj, str):
                total += len(obj)
            elif isinstance(obj, dict):
                for value in obj.values():
                    count_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    count_recursive(item)

        count_recursive(content)
        return total

    def _calculate_word_count(self, content: Dict[str, Any]) -> int:
        """
        Calculate total word count from content dictionary.

        Args:
            content: Content dictionary

        Returns:
            Total word count (whitespace-separated tokens)
        """
        total = 0

        def count_recursive(obj):
            nonlocal total
            if isinstance(obj, str):
                total += len(obj.split())
            elif isinstance(obj, dict):
                for value in obj.values():
                    count_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    count_recursive(item)

        count_recursive(content)
        return total

    def _generate_css_signature(self, css_overrides: Optional[Dict[str, str]]) -> str:
        """
        Generate a compact signature of CSS overrides for ML features.

        Creates a deterministic hash of the CSS overrides dictionary.
        This allows the model to learn which CSS patterns are stable vs broken.

        Args:
            css_overrides: Dictionary of CSS class overrides (or None)

        Returns:
            MD5 hash of the sorted CSS overrides (or 'NONE' if no overrides)

        Example:
            {"hero_title": "break-all", "card_bg": "truncate"}
            -> "a3f2c8b9d1e0..."
        """
        if not css_overrides:
            return "NONE"

        # Sort keys for deterministic hashing
        sorted_items = sorted(css_overrides.items())
        css_string = json.dumps(sorted_items, sort_keys=True)

        # Generate MD5 hash (short and fast)
        hash_obj = hashlib.md5(css_string.encode("utf-8"))
        return hash_obj.hexdigest()[:12]  # First 12 chars sufficient

    def _serialize_css_overrides(self, css_overrides: Optional[Dict[str, str]]) -> str:
        """
        Serialize CSS overrides to a string for LSTM training.

        v0.5.0 Feature: This is the Target (y) for neural style generation.
        Extracts the actual CSS class strings from the overrides dictionary.

        Args:
            css_overrides: Dictionary mapping components to CSS classes
                          e.g., {"hero_title": "text-sm break-all", "card": "truncate"}

        Returns:
            JSON string of overrides, or empty string if none

        Example:
            {"hero_title": "break-all overflow-hidden"}
            -> '{"hero_title": "break-all overflow-hidden"}'
        """
        if not css_overrides:
            return ""

        # Store as JSON for easy parsing during training
        return json.dumps(css_overrides, sort_keys=True)

    def _compute_resolved_strategy_id(self, strategy: str, guardian_verdict: bool) -> int:
        """
        Compute multiclass target ID based on which strategy succeeded.
        
        v0.8.0: Maps (strategy, verdict) → resolved_strategy_id for multiclass classification.
        
        Strategy Mapping:
            0: NONE_SUCCESS - No healing needed, passed on first try
            1: CSS_BREAK_WORD - break-all fixed the issue
            2: FONT_SHRINK - Font size reduction fixed the issue  
            3: CSS_TRUNCATE - Truncate/ellipsis fixed the issue
            4: CONTENT_CUT - Nuclear content truncation was needed
            99: UNRESOLVED_FAIL - All strategies failed
        
        Args:
            strategy: Active strategy name (NONE, CSS_BREAK_WORD, etc.)
            guardian_verdict: True if this strategy succeeded
            
        Returns:
            Resolved strategy ID (0-4, 99)
        """
        if not guardian_verdict:
            return 99  # UNRESOLVED_FAIL
        
        # Map successful strategy to ID
        strategy_map = {
            "NONE": 0,              # NONE_SUCCESS
            "CSS_BREAK_WORD": 1,    # break-all worked
            "FONT_SHRINK": 2,       # Font reduction worked
            "CSS_TRUNCATE": 3,      # Truncate worked
            "CONTENT_CUT": 4,       # Nuclear option worked
        }
        
        return strategy_map.get(strategy, 99)  # Default to UNRESOLVED_FAIL

    def _calculate_css_density_spacing(self, css_overrides: Optional[Dict[str, str]]) -> int:
        """
        Count Tailwind spacing classes (p-*, m-*, gap-*, space-*) in CSS overrides.
        
        v0.8.0: Feature for density analysis. High spacing density may indicate
        overcrowded layouts that need more aggressive healing.
        
        Args:
            css_overrides: Dictionary of CSS class strings
            
        Returns:
            Count of spacing-related classes
        """
        if not css_overrides:
            return 0
        
        count = 0
        spacing_prefixes = ['p-', 'm-', 'gap-', 'space-', 'px-', 'py-', 'pt-', 'pb-', 
                           'pl-', 'pr-', 'mx-', 'my-', 'mt-', 'mb-', 'ml-', 'mr-']
        
        for css_string in css_overrides.values():
            if isinstance(css_string, str):
                classes = css_string.split()
                for cls in classes:
                    if any(cls.startswith(prefix) for prefix in spacing_prefixes):
                        count += 1
        
        return count

    def _calculate_css_density_layout(self, css_overrides: Optional[Dict[str, str]]) -> int:
        """
        Count Tailwind layout classes (flex, grid, w-*, h-*, max-*, min-*) in CSS overrides.
        
        v0.8.0: Feature for layout complexity analysis. High layout density suggests
        complex grid/flexbox that may be prone to overflow.
        
        Args:
            css_overrides: Dictionary of CSS class strings
            
        Returns:
            Count of layout-related classes
        """
        if not css_overrides:
            return 0
        
        count = 0
        layout_keywords = ['flex', 'grid', 'block', 'inline', 'absolute', 'relative', 'fixed']
        layout_prefixes = ['w-', 'h-', 'max-w-', 'max-h-', 'min-w-', 'min-h-']
        
        for css_string in css_overrides.values():
            if isinstance(css_string, str):
                classes = css_string.split()
                for cls in classes:
                    # Check keywords
                    if cls in layout_keywords:
                        count += 1
                    # Check prefixes
                    elif any(cls.startswith(prefix) for prefix in layout_prefixes):
                        count += 1
        
        return count

    def _calculate_pathological_score(self, content: Dict[str, Any]) -> float:
        """
        Calculate pathological content score (risk of overflow from problematic strings).
        
        v0.8.0: Detects strings that are likely to cause layout breaks:
        - Very long words (>30 chars) without spaces
        - Repeated characters (AAAAA...)
        - URLs and technical strings
        
        Score ranges:
            0.0-0.3: Normal text, low risk
            0.3-0.7: Some long words, medium risk
            0.7-1.0: Pathological strings detected, high risk
        
        Args:
            content: Content dictionary
            
        Returns:
            Pathological score (0.0 to 1.0)
        """
        long_word_threshold = 30  # Words longer than this are suspicious
        repeat_threshold = 10     # Same char repeated N times is suspicious
        
        total_words = 0
        pathological_words = 0
        max_word_len = 0
        max_repeat = 0
        
        def analyze_recursive(obj):
            nonlocal total_words, pathological_words, max_word_len, max_repeat
            
            if isinstance(obj, str):
                words = obj.split()
                total_words += len(words)
                
                for word in words:
                    word_len = len(word)
                    max_word_len = max(max_word_len, word_len)
                    
                    # Check for pathologically long words
                    if word_len > long_word_threshold:
                        pathological_words += 1
                    
                    # Check for character repetition (AAAA...)
                    if word_len > 0:
                        max_repeat_in_word = max(
                            (len(list(group)) for char, group in __import__('itertools').groupby(word)),
                            default=0
                        )
                        max_repeat = max(max_repeat, max_repeat_in_word)
                        
                        if max_repeat_in_word >= repeat_threshold:
                            pathological_words += 1
            
            elif isinstance(obj, dict):
                for value in obj.values():
                    analyze_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    analyze_recursive(item)
        
        analyze_recursive(content)
        
        if total_words == 0:
            return 0.0
        
        # Normalize score components
        pathological_ratio = pathological_words / total_words
        length_score = min(max_word_len / 100.0, 1.0)  # Cap at 100 chars
        repeat_score = min(max_repeat / 20.0, 1.0)     # Cap at 20 repeats
        
        # Weighted average
        score = (pathological_ratio * 0.5) + (length_score * 0.3) + (repeat_score * 0.2)
        
        return round(min(score, 1.0), 3)  # Cap at 1.0, 3 decimals

    def _migrate_schema(self):
        """Migrate old CSV schema to v0.8.0 (multiclass + density features)."""
        import pandas as pd

        try:
            # Read old data
            df = pd.read_csv(self.dataset_path)

            # Add new v0.8.0 columns with default values
            if "css_density_spacing" not in df.columns:
                df["css_density_spacing"] = 0
            if "css_density_layout" not in df.columns:
                df["css_density_layout"] = 0
            if "pathological_score" not in df.columns:
                df["pathological_score"] = 0.0
            if "resolved_strategy_id" not in df.columns:
                # Compute from existing is_valid and active_strategy
                df["resolved_strategy_id"] = df.apply(
                    lambda row: self._compute_resolved_strategy_id(
                        row.get("active_strategy", "NONE"),
                        bool(row.get("is_valid", 0))
                    ),
                    axis=1
                )
            if "style_overrides_raw" not in df.columns:
                df["style_overrides_raw"] = ""

            # Save migrated data
            df.to_csv(self.dataset_path, index=False)
            logger.info("✅ Schema migrated to v0.8.0 (multiclass)")

        except Exception as e:
            logger.error(f"❌ Schema migration failed: {e}")
            logger.warning("⚠️  Starting fresh dataset instead")
            # Delete corrupted file and recreate
            self.dataset_path.unlink()
            self._ensure_dataset_exists()

    def get_dataset_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collected dataset.

        Returns:
            Dictionary with dataset metrics:
            - total_samples: Total number of logged events
            - positive_samples: Number of successful builds
            - negative_samples: Number of failed builds
            - success_rate: Percentage of successful builds
            - themes: List of unique themes
            - strategies: List of unique strategies used
        """
        if not self.dataset_path.exists():
            return {
                "total_samples": 0,
                "positive_samples": 0,
                "negative_samples": 0,
                "success_rate": 0.0,
                "themes": [],
                "strategies": [],
            }

        total = 0
        positive = 0
        themes = set()
        strategies = set()

        with open(self.dataset_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total += 1
                if int(row["is_valid"]) == 1:
                    positive += 1
                themes.add(row["theme"])
                strategies.add(row["active_strategy"])

        negative = total - positive
        success_rate = (positive / total * 100) if total > 0 else 0.0

        return {
            "total_samples": total,
            "positive_samples": positive,
            "negative_samples": negative,
            "success_rate": round(success_rate, 2),
            "themes": sorted(list(themes)),
            "strategies": sorted(list(strategies)),
        }

    def export_for_training(self, output_path: Optional[Path] = None) -> Path:
        """
        Export dataset in a format optimized for ML training.

        Creates a cleaned version of the dataset with numeric features only,
        ready for feeding into scikit-learn or PyTorch.

        Args:
            output_path: Where to save the training-ready file.
                        Defaults to data/training_dataset_ml.csv

        Returns:
            Path to the exported file
        """
        if output_path is None:
            output_path = self.dataset_path.parent / "training_dataset_ml.csv"

        # Feature extraction implemented via _prepare_features method in trainer.py
        # For now, just copy the raw dataset

        import shutil

        shutil.copy(self.dataset_path, output_path)

        logger.info(f"📦 Exported training dataset: {output_path}")
        return output_path
