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

Dataset Structure:
    data/training_dataset.csv with columns:
    - timestamp: ISO-8601 build time
    - theme: Theme name (e.g., 'brutalist')
    - input_char_len: Total character count of content
    - input_word_count: Total word count
    - css_signature: Hash of applied CSS overrides
    - active_strategy: Healing strategy applied (or 'NONE')
    - is_valid: Guardian verdict (0=Fail, 1=Pass)
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
from datetime import datetime
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
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                header = f.readline().strip()
                if 'style_overrides_raw' not in header:
                    needs_migration = True
                    logger.warning("⚠️  Dataset schema outdated - migration needed")

        if needs_migration:
            # Backup old file
            backup_path = self.dataset_path.with_suffix('.csv.backup')
            import shutil
            shutil.copy(self.dataset_path, backup_path)
            logger.info(f"📦 Backed up old dataset: {backup_path}")

            # Migrate: add new column with empty values
            self._migrate_schema()

        if not self.dataset_path.exists():
            with open(self.dataset_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write header row (v0.5.0 schema with style_overrides_raw)
                writer.writerow([
                    'timestamp',
                    'theme',
                    'input_char_len',
                    'input_word_count',
                    'css_signature',
                    'active_strategy',
                    'is_valid',
                    'failure_reason',
                    'style_overrides_raw'  # NEW: Actual CSS strings for LSTM training
                ])
            logger.info(f"✅ Created new training dataset: {self.dataset_path}")

    def log_build_event(
        self,
        theme: str,
        content: Dict[str, Any],
        strategy: str,
        guardian_verdict: bool,
        guardian_reason: str = "",
        css_overrides: Optional[Dict[str, str]] = None
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
            timestamp = datetime.utcnow().isoformat()
            char_len = self._calculate_char_count(content)
            word_count = self._calculate_word_count(content)
            css_sig = self._generate_css_signature(css_overrides)
            is_valid = 1 if guardian_verdict else 0

            # v0.5.0: Serialize actual CSS overrides for LSTM training
            style_overrides_raw = self._serialize_css_overrides(css_overrides)

            # Write to CSV (thread-safe append)
            # Use QUOTE_ALL to properly escape JSON strings
            with open(self.dataset_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                writer.writerow([
                    timestamp,
                    theme,
                    char_len,
                    word_count,
                    css_sig,
                    strategy,
                    is_valid,
                    guardian_reason,
                    style_overrides_raw  # NEW: Raw CSS string for training
                ])

            # Log summary
            verdict_emoji = "✅" if guardian_verdict else "❌"
            logger.debug(
                f"📊 Mined: {verdict_emoji} theme={theme}, chars={char_len}, "
                f"strategy={strategy}, valid={is_valid}"
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
        hash_obj = hashlib.md5(css_string.encode('utf-8'))
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

    def _migrate_schema(self):
        """Migrate old CSV schema to v0.5.0 (add style_overrides_raw column)."""
        import pandas as pd

        try:
            # Read old data
            df = pd.read_csv(self.dataset_path)

            # Add new column with empty values
            if 'style_overrides_raw' not in df.columns:
                df['style_overrides_raw'] = ''

            # Save migrated data
            df.to_csv(self.dataset_path, index=False)
            logger.info("✅ Schema migrated to v0.5.0")

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
                "strategies": []
            }

        total = 0
        positive = 0
        themes = set()
        strategies = set()

        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total += 1
                if int(row['is_valid']) == 1:
                    positive += 1
                themes.add(row['theme'])
                strategies.add(row['active_strategy'])

        negative = total - positive
        success_rate = (positive / total * 100) if total > 0 else 0.0

        return {
            "total_samples": total,
            "positive_samples": positive,
            "negative_samples": negative,
            "success_rate": round(success_rate, 2),
            "themes": sorted(list(themes)),
            "strategies": sorted(list(strategies))
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
