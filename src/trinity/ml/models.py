"""
LSTM-based Generative Style Model

Seq2Seq architecture that learns to generate Tailwind CSS fixes
from layout issue contexts. Implements Transfer Learning across themes.

Anti-Vibecoding Rules Applied:
- Rule #43: Small LSTM (2 layers, 128 hidden) for speed
- Rule #1: Output validation (no blind execution)
- Rule #28: Comprehensive error handling

Architecture:
    Encoder: Context (theme + metrics + error) → Hidden state
    Decoder: Hidden state → CSS token sequence
"""

from pathlib import Path
from typing import List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


class LSTMStyleGenerator(nn.Module):
    """
    Seq2Seq LSTM for CSS style generation.

    Takes layout issue context and generates Tailwind CSS class sequences.
    Trained on successful fixes from training_dataset.csv.

    Architecture:
        Input: Context vector (theme_onehot + content_length + error_type)
        Encoder: Embeds context into hidden state
        Decoder: LSTM generates token sequence
        Output: Probability distribution over vocabulary

    Example:
        >>> model = LSTMStyleGenerator(vocab_size=200, context_dim=50)
        >>> context = torch.randn(1, 50)  # Batch=1, context features
        >>> output_tokens = model.generate(context, max_length=10)
        >>> # output_tokens: [<SOS>, text-sm, truncate, break-all, <EOS>]
    """

    def __init__(
        self,
        vocab_size: int,
        context_dim: int,
        embedding_dim: int = 64,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
    ):
        """
        Initialize LSTM Style Generator.

        Args:
            vocab_size: Size of Tailwind CSS vocabulary
            context_dim: Dimension of context vector (theme + metrics + error)
            embedding_dim: Token embedding dimension
            hidden_dim: LSTM hidden state dimension (Rule #43: keep at 128)
            num_layers: Number of LSTM layers (Rule #43: keep at 2)
            dropout: Dropout rate for regularization
        """
        super().__init__()

        self.vocab_size = vocab_size
        self.context_dim = context_dim
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # Token embedding layer
        self.embedding = nn.Embedding(
            num_embeddings=vocab_size,
            embedding_dim=embedding_dim,
            padding_idx=0,  # <PAD> token
        )

        # Context encoder: maps context to initial hidden state
        self.context_encoder = nn.Sequential(
            nn.Linear(context_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim * num_layers),
            nn.Tanh(),
        )

        # LSTM decoder: generates token sequence
        self.lstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True,
        )

        # Output projection: hidden state → vocabulary logits
        self.output_projection = nn.Linear(hidden_dim, vocab_size)

        # Initialize weights
        self._init_weights()

    def _init_weights(self) -> None:
        """Initialize model weights (Xavier for stability)."""
        for name, param in self.named_parameters():
            if "weight" in name and param.dim() > 1:
                nn.init.xavier_uniform_(param)
            elif "bias" in name:
                nn.init.zeros_(param)

    def _init_hidden(self, context: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Initialize LSTM hidden state from context.

        Args:
            context: [batch_size, context_dim] tensor

        Returns:
            (h0, c0): Initial hidden and cell states
        """
        batch_size = context.size(0)

        # Encode context to hidden state
        h0 = self.context_encoder(context)  # [batch, hidden_dim * num_layers]
        h0 = h0.view(batch_size, self.num_layers, self.hidden_dim)
        h0 = h0.transpose(0, 1).contiguous()  # [num_layers, batch, hidden_dim]

        # Initialize cell state to zeros
        c0 = torch.zeros_like(h0)

        return h0, c0

    def forward(
        self, context: torch.Tensor, target_tokens: torch.Tensor, teacher_forcing_ratio: float = 0.5
    ) -> torch.Tensor:
        """
        Forward pass for training.

        Args:
            context: [batch, context_dim] layout issue context
            target_tokens: [batch, seq_len] target CSS token indices
            teacher_forcing_ratio: Probability of using ground truth vs prediction

        Returns:
            logits: [batch, seq_len, vocab_size] token probabilities
        """
        batch_size, seq_len = target_tokens.size()

        # Initialize hidden state from context
        h0, c0 = self._init_hidden(context)

        # Start with <SOS> token (index 1)
        decoder_input = torch.ones(batch_size, 1, dtype=torch.long, device=context.device)

        # Store outputs
        outputs = []

        # Decode step by step
        hidden = (h0, c0)
        for t in range(seq_len):
            # Embed input token
            embedded = self.embedding(decoder_input)  # [batch, 1, embedding_dim]

            # LSTM step
            lstm_out, hidden = self.lstm(embedded, hidden)

            # Project to vocabulary
            logits = self.output_projection(lstm_out)  # [batch, 1, vocab_size]
            outputs.append(logits)

            # Teacher forcing: use ground truth or prediction?
            use_teacher_forcing = torch.rand(1).item() < teacher_forcing_ratio
            if use_teacher_forcing and t < seq_len - 1:
                decoder_input = target_tokens[:, t + 1].unsqueeze(1)
            else:
                # Use model's own prediction
                decoder_input = logits.argmax(dim=-1)

        # Stack outputs: [batch, seq_len, vocab_size]
        outputs = torch.cat(outputs, dim=1)

        return outputs

    @torch.no_grad()
    def generate(
        self,
        context: torch.Tensor,
        max_length: int = 20,
        temperature: float = 1.0,
        top_k: Optional[int] = None,
        sos_token_idx: int = 1,
        eos_token_idx: int = 2,
    ) -> List[List[int]]:
        """
        Generate CSS token sequences from context (inference mode).

        Supports sampling strategies:
        - Temperature: Controls randomness (0.5=conservative, 1.5=creative)
        - Top-K: Restricts to K most likely tokens (prevents hallucinations)

        Args:
            context: [batch, context_dim] layout issue context
            max_length: Maximum sequence length
            temperature: Sampling temperature (higher = more random)
            top_k: If set, sample from top K tokens only
            sos_token_idx: Start-of-sequence token index
            eos_token_idx: End-of-sequence token index

        Returns:
            List of token sequences (one per batch item)
        """
        self.eval()

        batch_size = context.size(0)
        device = context.device

        # Initialize hidden state
        h0, c0 = self._init_hidden(context)

        # Start with <SOS> token
        decoder_input = torch.full(
            (batch_size, 1), fill_value=sos_token_idx, dtype=torch.long, device=device
        )

        # Track generated sequences
        generated = [[] for _ in range(batch_size)]
        finished = [False] * batch_size

        hidden = (h0, c0)
        for _ in range(max_length):
            # Embed and decode
            embedded = self.embedding(decoder_input)
            lstm_out, hidden = self.lstm(embedded, hidden)
            logits = self.output_projection(lstm_out.squeeze(1))  # [batch, vocab_size]

            # Apply temperature
            logits = logits / temperature

            # Top-K filtering (anti-hallucination)
            if top_k is not None:
                top_k_logits, top_k_indices = torch.topk(logits, top_k, dim=-1)
                logits = torch.full_like(logits, float("-inf"))
                logits.scatter_(1, top_k_indices, top_k_logits)

            # Sample next token
            probs = F.softmax(logits, dim=-1)
            next_tokens = torch.multinomial(probs, num_samples=1)  # [batch, 1]

            # Update sequences
            for i in range(batch_size):
                if not finished[i]:
                    token_id = next_tokens[i].item()

                    if token_id == eos_token_idx:
                        finished[i] = True
                    else:
                        generated[i].append(token_id)

            # Stop if all sequences finished
            if all(finished):
                break

            decoder_input = next_tokens

        return generated

    def save(self, model_path: Path) -> None:
        """
        Save model checkpoint.

        Saves:
        - Model state dict
        - Hyperparameters
        - Optimizer state (if provided separately)
        """
        checkpoint = {
            "model_state_dict": self.state_dict(),
            "vocab_size": self.vocab_size,
            "context_dim": self.context_dim,
            "embedding_dim": self.embedding_dim,
            "hidden_dim": self.hidden_dim,
            "num_layers": self.num_layers,
        }

        model_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(checkpoint, model_path)

        print(f"💾 Model saved: {model_path}")

    @classmethod
    def load(cls, model_path: Path, device: str = "cpu") -> "LSTMStyleGenerator":
        """
        Load model from checkpoint.

        Args:
            model_path: Path to saved checkpoint
            device: Device to load model on

        Returns:
            Loaded model instance
        """
        checkpoint = torch.load(model_path, map_location=device)

        model = cls(
            vocab_size=checkpoint["vocab_size"],
            context_dim=checkpoint["context_dim"],
            embedding_dim=checkpoint["embedding_dim"],
            hidden_dim=checkpoint["hidden_dim"],
            num_layers=checkpoint["num_layers"],
        )

        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)

        print(f"📂 Model loaded: {model_path}")

        return model


# Example usage for documentation
if __name__ == "__main__":
    # Create model
    model = LSTMStyleGenerator(
        vocab_size=200,  # From tokenizer
        context_dim=50,  # Theme (one-hot) + content_length + error_type
        hidden_dim=128,  # Rule #43: keep small
        num_layers=2,
    )

    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Simulate context
    batch_size = 4
    context = torch.randn(batch_size, 50)

    # Generate CSS fixes
    generated_sequences = model.generate(
        context,
        max_length=10,
        temperature=0.8,
        top_k=20,  # Anti-hallucination
    )

    print(f"\nGenerated {len(generated_sequences)} CSS sequences")
    print(f"Example: {generated_sequences[0]}")
