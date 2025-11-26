"""
Generative Style Trainer

PyTorch training pipeline for LSTM Style Generator.
Learns to generate CSS fixes from successful healing attempts.

Anti-Vibecoding Rules Applied:
- Rule #28: Comprehensive logging and metrics
- Rule #43: Efficient training (batch processing, early stopping)
- Rule #1: Data validation before training

Training Flow:
    1. Load training_dataset.csv
    2. Filter for successful fixes (is_valid=1)
    3. Build vocabulary from CSS overrides
    4. Train LSTM to predict CSS sequences
    5. Save model + vocabulary
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from trinity.ml.models import LSTMStyleGenerator
from trinity.ml.tokenizer import TailwindTokenizer
from trinity.utils.logger import get_logger

logger = get_logger(__name__)


class CSSFixDataset(Dataset):
    """
    Dataset for CSS fix generation training.

    Loads successful fixes from training_dataset.csv and prepares
    context-target pairs for LSTM training.
    """

    def __init__(self, csv_path: Path, tokenizer: TailwindTokenizer, max_seq_length: int = 20):
        """
        Initialize dataset.

        Args:
            csv_path: Path to training_dataset.csv
            tokenizer: Trained Tailwind tokenizer
            max_seq_length: Maximum CSS sequence length (for padding)
        """
        self.tokenizer = tokenizer
        self.max_seq_length = max_seq_length

        # Load and filter data
        df = pd.read_csv(csv_path)

        # Only use successful fixes
        df = df[df["is_valid"] == 1].copy()

        logger.info(f"📊 Loaded {len(df)} successful fixes from {csv_path.name}")

        # Extract features
        self.contexts = self._extract_contexts(df)
        self.targets = self._extract_targets(df)

        assert len(self.contexts) == len(self.targets), "Context-target mismatch"

    def _extract_contexts(self, df: pd.DataFrame) -> List[Dict]:
        """
        Extract context features from dataframe.

        Context includes:
        - theme (one-hot encoded)
        - content_length (normalized)
        - error_type (one-hot encoded)
        - attempt_number
        """
        contexts = []

        # Get unique themes for one-hot encoding
        themes = df["theme"].unique().tolist()
        theme_to_idx = {theme: idx for idx, theme in enumerate(themes)}

        # Get unique error types
        error_types = ["overflow", "text_too_long", "layout_shift", "unknown"]
        error_to_idx = {err: idx for idx, err in enumerate(error_types)}

        for _, row in df.iterrows():
            # Theme one-hot
            theme_vec = [0] * len(themes)
            theme_vec[theme_to_idx[row["theme"]]] = 1

            # Content length (normalized to [0, 1])
            content_len = min(row.get("content_length", 100), 1000) / 1000.0

            # Error type one-hot
            error_vec = [0] * len(error_types)
            error_type = row.get("error_type", "unknown")
            if error_type in error_to_idx:
                error_vec[error_to_idx[error_type]] = 1
            else:
                error_vec[error_to_idx["unknown"]] = 1

            # Attempt number (normalized)
            attempt = min(row.get("attempt_number", 1), 5) / 5.0

            # Combine into context vector
            context = {
                "vector": theme_vec + [content_len, attempt] + error_vec,
                "metadata": {
                    "theme": row["theme"],
                    "content_length": row.get("content_length", 0),
                    "error_type": error_type,
                },
            }

            contexts.append(context)

        logger.info(f"✅ Context dimension: {len(contexts[0]['vector'])}")

        return contexts

    def _extract_targets(self, df: pd.DataFrame) -> List[str]:
        """
        Extract target CSS sequences from dataframe.

        v0.5.0: Uses 'style_overrides_raw' column (JSON serialized CSS overrides).
        Falls back to legacy behavior if column doesn't exist.
        """
        targets = []

        # Check if v0.5.0 schema exists
        if "style_overrides_raw" in df.columns:
            for _, row in df.iterrows():
                css_raw = row.get("style_overrides_raw", "")

                if pd.isna(css_raw) or not css_raw.strip():
                    # No CSS override (probably failed build)
                    targets.append("text-sm truncate")  # Fallback
                else:
                    # Parse JSON: {"hero_title": "break-all", "card": "truncate"}
                    try:
                        import json

                        css_dict = json.loads(css_raw)
                        # Combine all CSS classes from overrides
                        all_classes = []
                        for component, classes in css_dict.items():
                            if classes.strip():
                                all_classes.extend(classes.split())

                        # Deduplicate and join
                        unique_classes = list(dict.fromkeys(all_classes))  # Preserve order
                        css_string = " ".join(unique_classes)

                        targets.append(css_string if css_string else "text-sm truncate")

                    except json.JSONDecodeError:
                        # Invalid JSON, use as-is
                        targets.append(css_raw if css_raw.strip() else "text-sm truncate")
        else:
            # Legacy: try 'css_overrides' column (old schema)
            logger.warning("⚠️  Using legacy CSS extraction (upgrade dataset to v0.5.0)")
            for _, row in df.iterrows():
                css_override = row.get("css_overrides", "")

                if pd.isna(css_override) or not css_override.strip():
                    css_override = "text-sm truncate"

                targets.append(css_override)

        logger.info(f"✅ Extracted {len(targets)} CSS target sequences")
        return targets

    def __len__(self) -> int:
        return len(self.contexts)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Get a single training example.

        Returns:
            context: [context_dim] float tensor
            target: [seq_len] long tensor (padded)
        """
        # Context vector
        context = torch.FloatTensor(self.contexts[idx]["vector"])

        # Target CSS tokens
        css_string = self.targets[idx]
        token_ids = self.tokenizer.encode(css_string, add_special_tokens=True)

        # Pad to max length
        if len(token_ids) < self.max_seq_length:
            token_ids += [self.tokenizer.token2idx[self.tokenizer.PAD_TOKEN]] * (
                self.max_seq_length - len(token_ids)
            )
        else:
            token_ids = token_ids[: self.max_seq_length]

        target = torch.LongTensor(token_ids)

        return context, target


class GenerativeStyleTrainer:
    """
    Trainer for LSTM Style Generator.

    Handles:
    - Data loading and batching
    - Training loop with validation
    - Model checkpointing
    - Metrics logging
    """

    def __init__(
        self,
        dataset_path: Path,
        output_dir: Path,
        vocab_path: Optional[Path] = None,
        device: str = "cpu",
    ):
        """
        Initialize trainer.

        Args:
            dataset_path: Path to training_dataset.csv
            output_dir: Directory to save model and vocab
            vocab_path: Pre-built vocabulary (if None, builds from data)
            device: Training device ('cpu' or 'cuda')
        """
        self.dataset_path = dataset_path
        self.output_dir = output_dir
        self.device = device

        output_dir.mkdir(parents=True, exist_ok=True)

        # Build or load tokenizer
        if vocab_path and vocab_path.exists():
            self.tokenizer = TailwindTokenizer(vocab_path)
        else:
            logger.info("🔨 Building vocabulary from training data...")
            self.tokenizer = TailwindTokenizer()
            self._build_vocabulary()
            vocab_save_path = output_dir / "tailwind_vocab.json"
            self.tokenizer.save_vocab(vocab_save_path)

        # Create dataset
        self.dataset = CSSFixDataset(
            csv_path=dataset_path, tokenizer=self.tokenizer, max_seq_length=20
        )

        # Get context dimension from first sample
        context, _ = self.dataset[0]
        self.context_dim = context.size(0)

        logger.info(f"✅ Dataset ready: {len(self.dataset)} examples")

    def _build_vocabulary(self) -> None:
        """Build tokenizer vocabulary from successful CSS fixes."""
        import json

        df = pd.read_csv(self.dataset_path)
        df = df[df["is_valid"] == 1]

        # Parse JSON CSS overrides and extract all classes
        css_sequences = []
        for css_raw in df["style_overrides_raw"].dropna():
            try:
                css_dict = json.loads(css_raw)
                all_classes = []
                for component, classes in css_dict.items():
                    if classes and classes.strip():
                        all_classes.extend(classes.split())
                unique_classes = list(dict.fromkeys(all_classes))
                css_string = " ".join(unique_classes)
                if css_string:
                    css_sequences.append(css_string)
            except (json.JSONDecodeError, AttributeError):
                # Skip invalid entries
                continue

        self.tokenizer.build_vocab(css_sequences, min_freq=1)  # Lower threshold for small datasets

    def train(
        self,
        epochs: int = 50,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        validation_split: float = 0.2,
        early_stopping_patience: int = 5,
    ) -> LSTMStyleGenerator:
        """
        Train LSTM Style Generator.

        Args:
            epochs: Number of training epochs
            batch_size: Batch size for training
            learning_rate: Adam optimizer learning rate
            validation_split: Fraction of data for validation
            early_stopping_patience: Epochs without improvement before stopping

        Returns:
            Trained model
        """
        # Split dataset
        dataset_size = len(self.dataset)
        val_size = int(dataset_size * validation_split)
        train_size = dataset_size - val_size

        train_dataset, val_dataset = torch.utils.data.random_split(
            self.dataset, [train_size, val_size]
        )

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

        logger.info(f"📊 Training: {train_size} | Validation: {val_size}")

        # Initialize model
        model = LSTMStyleGenerator(
            vocab_size=self.tokenizer.vocab_size,
            context_dim=self.context_dim,
            hidden_dim=128,  # Rule #43: keep small
            num_layers=2,
        ).to(self.device)

        # Optimizer and loss
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        criterion = nn.CrossEntropyLoss(ignore_index=0)  # Ignore <PAD>

        # Training loop
        best_val_loss = float("inf")
        patience_counter = 0

        for epoch in range(epochs):
            # Training phase
            model.train()
            train_loss = 0.0

            for context, target in tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}"):
                context = context.to(self.device)
                target = target.to(self.device)

                optimizer.zero_grad()

                # Forward pass
                logits = model(context, target, teacher_forcing_ratio=0.5)

                # Reshape for loss calculation
                logits = logits.view(-1, self.tokenizer.vocab_size)
                target = target.view(-1)

                loss = criterion(logits, target)

                # Backward pass
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

                train_loss += loss.item()

            train_loss /= len(train_loader)

            # Validation phase
            model.eval()
            val_loss = 0.0

            with torch.no_grad():
                for context, target in val_loader:
                    context = context.to(self.device)
                    target = target.to(self.device)

                    logits = model(context, target, teacher_forcing_ratio=0.0)
                    logits = logits.view(-1, self.tokenizer.vocab_size)
                    target = target.view(-1)

                    loss = criterion(logits, target)
                    val_loss += loss.item()

            val_loss /= len(val_loader)

            logger.info(
                f"Epoch {epoch+1}: " f"Train Loss={train_loss:.4f} | Val Loss={val_loss:.4f}"
            )

            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0

                # Save best model
                model.save(self.output_dir / "style_generator_best.pth")
            else:
                patience_counter += 1
                if patience_counter >= early_stopping_patience:
                    logger.info(f"⏸️  Early stopping at epoch {epoch+1}")
                    break

        logger.info(f"✅ Training complete! Best val loss: {best_val_loss:.4f}")

        # Load best model
        model = LSTMStyleGenerator.load(
            self.output_dir / "style_generator_best.pth", device=self.device
        )

        return model


# CLI for training
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train Generative Style Model")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/training_dataset.csv"),
        help="Path to training dataset",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("models/generative"),
        help="Output directory for model and vocab",
    )
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--device", type=str, default="cpu")

    args = parser.parse_args()

    # Train model
    trainer = GenerativeStyleTrainer(
        dataset_path=args.dataset, output_dir=args.output, device=args.device
    )

    model = trainer.train(epochs=args.epochs, batch_size=args.batch_size, learning_rate=args.lr)

    print("\n🎉 Training complete!")
    print(f"📂 Model saved: {args.output}/style_generator_best.pth")
    print(f"📂 Vocabulary: {args.output}/tailwind_vocab.json")
