"""
Tailwind CSS Tokenizer for Neural Style Generation

This tokenizer converts CSS class strings into numerical sequences
for LSTM training, with special handling for Tailwind utility classes.

Anti-Vibecoding Rules Applied:
- Rule #1: Explicit unknown token handling with <UNK>
- Rule #43: Keep vocabulary small and focused (Tailwind utilities only)
- Rule #28: Comprehensive token validation
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set


class TailwindTokenizer:
    """
    Tokenizer for Tailwind CSS utility classes.

    Converts strings like "text-sm truncate break-all" into:
    - Token sequences: [<SOS>, text-sm, truncate, break-all, <EOS>]
    - Integer sequences: [1, 45, 89, 12, 2]

    Special Tokens:
        <PAD>: Padding for batch processing (index 0)
        <SOS>: Start of sequence (index 1)
        <EOS>: End of sequence (index 2)
        <UNK>: Unknown token fallback (index 3)
    """

    # Special token constants
    PAD_TOKEN = "<PAD>"
    SOS_TOKEN = "<SOS>"
    EOS_TOKEN = "<EOS>"
    UNK_TOKEN = "<UNK>"

    def __init__(self, vocab_path: Optional[Path] = None):
        """
        Initialize tokenizer with vocabulary.

        Args:
            vocab_path: Path to saved vocabulary JSON. If None, builds from scratch.
        """
        # Initialize special tokens first (indices 0-3)
        self.token2idx: Dict[str, int] = {
            self.PAD_TOKEN: 0,
            self.SOS_TOKEN: 1,
            self.EOS_TOKEN: 2,
            self.UNK_TOKEN: 3,
        }
        self.idx2token: Dict[int, str] = {v: k for k, v in self.token2idx.items()}
        self.next_idx = 4

        if vocab_path and vocab_path.exists():
            self.load_vocab(vocab_path)

    def build_vocab(self, css_sequences: List[str], min_freq: int = 2) -> None:
        """
        Build vocabulary from training CSS sequences.

        Args:
            css_sequences: List of CSS class strings from successful fixes
            min_freq: Minimum frequency to include token (avoid rare hallucinations)

        Example:
            >>> tokenizer = TailwindTokenizer()
            >>> css_examples = [
            ...     "text-sm truncate",
            ...     "break-all overflow-hidden",
            ...     "text-sm line-clamp-2"
            ... ]
            >>> tokenizer.build_vocab(css_examples, min_freq=1)
        """
        # Count token frequencies
        token_freq: Dict[str, int] = {}

        for sequence in css_sequences:
            tokens = self._split_css_string(sequence)
            for token in tokens:
                token_freq[token] = token_freq.get(token, 0) + 1

        # Add tokens that meet frequency threshold
        for token, freq in sorted(token_freq.items(), key=lambda x: -x[1]):
            if freq >= min_freq and token not in self.token2idx:
                self.token2idx[token] = self.next_idx
                self.idx2token[self.next_idx] = token
                self.next_idx += 1

        print(f"✅ Vocabulary built: {len(self.token2idx)} tokens (min_freq={min_freq})")

    def _split_css_string(self, css_string: str) -> List[str]:
        """
        Split CSS string into individual class tokens.

        Handles edge cases:
        - Multiple spaces
        - Leading/trailing whitespace
        - Arbitrary values: text-[0.9rem]
        - Negative values: -mt-4

        Args:
            css_string: Raw CSS class string

        Returns:
            List of normalized tokens
        """
        if not css_string or css_string.isspace():
            return []

        # Split by whitespace and filter empty strings
        tokens = [t.strip() for t in css_string.split() if t.strip()]

        # Validate Tailwind-like patterns (allow alphanumeric, hyphens, brackets, dots)
        valid_tokens = []
        for token in tokens:
            # Allow: text-sm, text-[0.9rem], -mt-4, hover:text-blue-500
            if re.match(r'^-?[\w\-\[\].:]+$', token):
                valid_tokens.append(token)
            # else: silently skip invalid tokens (anti-injection)

        return valid_tokens

    def encode(self, css_string: str, add_special_tokens: bool = True) -> List[int]:
        """
        Convert CSS string to integer sequence.

        Args:
            css_string: CSS class string to encode
            add_special_tokens: Whether to add <SOS> and <EOS>

        Returns:
            List of token indices

        Example:
            >>> tokenizer.encode("text-sm truncate")
            [1, 45, 89, 2]  # [<SOS>, text-sm, truncate, <EOS>]
        """
        tokens = self._split_css_string(css_string)

        # Convert to indices (use <UNK> for unknown tokens)
        indices = [
            self.token2idx.get(token, self.token2idx[self.UNK_TOKEN])
            for token in tokens
        ]

        if add_special_tokens:
            indices = [self.token2idx[self.SOS_TOKEN]] + indices + [self.token2idx[self.EOS_TOKEN]]

        return indices

    def decode(self, indices: List[int], skip_special_tokens: bool = True) -> str:
        """
        Convert integer sequence back to CSS string.

        Args:
            indices: Token indices from model output
            skip_special_tokens: Whether to remove <SOS>, <EOS>, <PAD>

        Returns:
            Reconstructed CSS class string

        Example:
            >>> tokenizer.decode([1, 45, 89, 2])
            "text-sm truncate"
        """
        special_indices = {
            self.token2idx[self.PAD_TOKEN],
            self.token2idx[self.SOS_TOKEN],
            self.token2idx[self.EOS_TOKEN],
        }

        tokens = []
        for idx in indices:
            if skip_special_tokens and idx in special_indices:
                continue

            token = self.idx2token.get(idx, self.UNK_TOKEN)

            # Stop at <EOS> if not skipping special tokens
            if not skip_special_tokens and token == self.EOS_TOKEN:
                break

            if token != self.UNK_TOKEN or not skip_special_tokens:
                tokens.append(token)

        return " ".join(tokens)

    def validate_tokens(self, tokens: List[str]) -> Set[str]:
        """
        Validate that tokens exist in vocabulary.

        This prevents the LSTM from hallucinating invalid Tailwind classes.

        Args:
            tokens: List of token strings to validate

        Returns:
            Set of valid tokens (unknowns filtered out)
        """
        valid = set()
        for token in tokens:
            if token in self.token2idx and token not in {
                self.PAD_TOKEN, self.SOS_TOKEN, self.EOS_TOKEN, self.UNK_TOKEN
            }:
                valid.add(token)
        return valid

    def save_vocab(self, vocab_path: Path) -> None:
        """Save vocabulary to JSON file."""
        vocab_data = {
            "token2idx": self.token2idx,
            "vocab_size": len(self.token2idx),
        }

        vocab_path.parent.mkdir(parents=True, exist_ok=True)
        with open(vocab_path, 'w') as f:
            json.dump(vocab_data, f, indent=2)

        print(f"💾 Vocabulary saved: {vocab_path} ({len(self.token2idx)} tokens)")

    def load_vocab(self, vocab_path: Path) -> None:
        """Load vocabulary from JSON file."""
        with open(vocab_path, 'r') as f:
            vocab_data = json.load(f)

        self.token2idx = vocab_data["token2idx"]
        self.idx2token = {int(v): k for k, v in self.token2idx.items()}
        self.next_idx = max(self.idx2token.keys()) + 1

        print(f"📂 Vocabulary loaded: {vocab_path} ({len(self.token2idx)} tokens)")

    @property
    def vocab_size(self) -> int:
        """Get total vocabulary size."""
        return len(self.token2idx)

    def __len__(self) -> int:
        """Enable len(tokenizer)."""
        return self.vocab_size


# Example usage for documentation
if __name__ == "__main__":
    # Build vocabulary from training data
    tokenizer = TailwindTokenizer()

    training_examples = [
        "text-sm truncate",
        "break-all overflow-hidden",
        "text-3xl font-bold",
        "line-clamp-2 text-ellipsis",
        "overflow-x-hidden overflow-y-auto",
    ]

    tokenizer.build_vocab(training_examples, min_freq=1)

    # Encode/decode example
    css = "text-sm truncate"
    encoded = tokenizer.encode(css)
    decoded = tokenizer.decode(encoded)

    print(f"\nOriginal: {css}")
    print(f"Encoded:  {encoded}")
    print(f"Decoded:  {decoded}")

    # Save for model training
    tokenizer.save_vocab(Path("models/tailwind_vocab.json"))
