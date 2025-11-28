"""
Neural Healer - Generative CSS Fix Generator

Replaces heuristic healing strategies with LSTM-generated fixes.
Learns optimal CSS solutions from training data instead of using predefined rules.

Anti-Vibecoding Rules Applied:
- Rule #1: Validate generated CSS against whitelist
- Rule #43: Fallback to heuristic if model unavailable
- Rule #28: Comprehensive error handling

Phase: v0.5.0 (Generative Style Engine)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, cast

import torch

from trinity.components.healer import HealingResult, HealingStrategy
from trinity.ml.models import LSTMStyleGenerator
from trinity.ml.tokenizer import TailwindTokenizer
from trinity.utils.logger import get_logger

logger = get_logger(__name__)


class NeuralHealer:
    """
    Neural network-based CSS fix generator.

    Uses trained LSTM to generate CSS fixes instead of predefined strategies.
    Implements Transfer Learning: fixes learned on Brutalist theme apply to Editorial.

    Example:
        >>> healer = NeuralHealer(model_path="models/generative/style_generator_best.pth")
        >>> context = {
        ...     "theme": "brutalist",
        ...     "content_length": 500,
        ...     "error_type": "overflow"
        ... }
        >>> result = healer.heal_layout(guardian_report, content, attempt=1, context=context)
        >>> print(result.style_overrides)
        {'hero_title': 'text-[0.9rem] leading-tight break-words overflow-hidden'}
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        vocab_path: Optional[Path] = None,
        device: str = "cpu",
        fallback_to_heuristic: bool = True,
    ):
        """
        Initialize Neural Healer.

        Args:
            model_path: Path to trained LSTM model (*.pth)
            vocab_path: Path to Tailwind vocabulary (*.json)
            device: Device for inference ('cpu' or 'cuda')
            fallback_to_heuristic: Use SmartHealer if model unavailable
        """
        self.device = device
        self.fallback_to_heuristic = fallback_to_heuristic

        # Try to load model and tokenizer
        self.model: Optional[LSTMStyleGenerator] = None
        self.tokenizer: Optional[TailwindTokenizer] = None

        if model_path and model_path.exists():
            try:
                self.model = LSTMStyleGenerator.load(model_path, device=device)
                logger.info(f"🧠 Neural Healer loaded: {model_path.name}")
            except Exception as e:
                logger.warning(f"Failed to load model: {e}")

        if vocab_path and vocab_path.exists():
            try:
                self.tokenizer = TailwindTokenizer(vocab_path)
            except Exception as e:
                logger.warning(f"Failed to load vocabulary: {e}")

        # Fallback to heuristic healer if model not available
        self.heuristic_healer: Optional[Any] = None
        if not self.model or not self.tokenizer:
            if fallback_to_heuristic:
                from trinity.components.healer import SmartHealer

                self.heuristic_healer = SmartHealer()
                logger.info("⚠️  Neural model unavailable, using heuristic fallback")
            else:
                raise RuntimeError("Neural model not loaded and fallback disabled")

        # Whitelist of valid Tailwind CSS classes (anti-hallucination)
        self.valid_tailwind_classes = self._build_class_whitelist()

    def _build_class_whitelist(self) -> Set[str]:
        """
        Build whitelist of valid Tailwind classes.

        Prevents the LSTM from hallucinating invalid CSS.
        In production, this should be the full Tailwind vocabulary.
        """
        # Common Tailwind utilities (subset for safety)
        whitelist = {
            # Text sizing
            "text-xs",
            "text-sm",
            "text-base",
            "text-lg",
            "text-xl",
            "text-2xl",
            "text-3xl",
            "text-4xl",
            "text-5xl",
            # Line height
            "leading-none",
            "leading-tight",
            "leading-snug",
            "leading-normal",
            # Word breaking
            "break-normal",
            "break-words",
            "break-all",
            # Overflow
            "overflow-hidden",
            "overflow-x-hidden",
            "overflow-y-hidden",
            "overflow-auto",
            "overflow-scroll",
            # Truncation
            "truncate",
            "text-ellipsis",
            "line-clamp-1",
            "line-clamp-2",
            "line-clamp-3",
            "line-clamp-4",
            # Whitespace
            "whitespace-normal",
            "whitespace-nowrap",
            "whitespace-pre",
            # Font weight
            "font-normal",
            "font-medium",
            "font-semibold",
            "font-bold",
        }

        # If tokenizer available, use its vocabulary
        if self.tokenizer:
            vocab_classes = set(self.tokenizer.token2idx.keys()) - {
                self.tokenizer.PAD_TOKEN,
                self.tokenizer.SOS_TOKEN,
                self.tokenizer.EOS_TOKEN,
                self.tokenizer.UNK_TOKEN,
            }
            whitelist.update(vocab_classes)

        return whitelist

    def _extract_context_vector(
        self, theme: str, content_length: int, error_type: str, attempt: int
    ) -> torch.Tensor:
        """
        Convert context into feature vector for LSTM.

        Must match the format used during training.
        CRITICAL: Use same theme list as training (brutalist, editorial, enterprise).
        """
        # Theme one-hot - MUST match training data exactly!
        # Training uses: brutalist, editorial, enterprise (alphabetical order from dataset)
        themes = ["brutalist", "editorial", "enterprise"]
        theme_vec = [0] * len(themes)
        if theme in themes:
            theme_vec[themes.index(theme)] = 1
        else:
            # Fallback to enterprise if unknown theme
            theme_vec[themes.index("enterprise")] = 1

        # Content length normalized
        content_len_norm = min(content_length, 1000) / 1000.0

        # Error type one-hot
        error_types = ["overflow", "text_too_long", "layout_shift", "unknown"]
        error_vec = [0] * len(error_types)
        if error_type in error_types:
            error_vec[error_types.index(error_type)] = 1
        else:
            error_vec[-1] = 1  # "unknown"

        # Attempt normalized
        attempt_norm = min(attempt, 5) / 5.0

        # Combine: 3 (themes) + 1 (content) + 1 (attempt) + 4 (errors) = 9 dimensions
        context_vector = theme_vec + [content_len_norm, attempt_norm] + error_vec

        return torch.FloatTensor(context_vector).unsqueeze(0)  # [1, 9]

    def _validate_generated_css(self, css_classes: List[str]) -> List[str]:
        """
        Validate generated CSS classes against whitelist.

        Filters out hallucinated or invalid classes.

        Args:
            css_classes: List of CSS class tokens from model

        Returns:
            Filtered list of valid classes
        """
        valid = []
        for cls in css_classes:
            # Check against whitelist
            if cls in self.valid_tailwind_classes:
                valid.append(cls)
            # Allow arbitrary values: text-[0.9rem]
            elif "[" in cls and "]" in cls:
                valid.append(cls)
            else:
                logger.debug(f"⚠️  Filtered invalid class: {cls}")

        return valid

    def heal_layout(
        self,
        guardian_report: Dict[str, Any],
        content: Dict[str, Any],
        attempt: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> HealingResult:
        """
        Generate CSS fix using neural model.

        Args:
            guardian_report: Guardian audit results (unused but kept for compatibility)
            content: Content dict (for length calculation)
            attempt: Healing attempt number
            context: Additional context (theme, error_type, etc.)

        Returns:
            HealingResult with generated CSS overrides
        """
        # Fallback to heuristic if model unavailable
        if not self.model or not self.tokenizer:
            if self.heuristic_healer:
                logger.debug("🔄 Using heuristic fallback")
                return cast(HealingResult, self.heuristic_healer.heal_layout(guardian_report, content, attempt))
            else:
                raise RuntimeError("Neural model and heuristic fallback unavailable")

        # Extract context
        context = context or {}
        theme = context.get("theme", "enterprise")
        error_type = context.get("error_type", "overflow")

        # Calculate content length
        content_str = str(content.get("hero", {}).get("title", ""))
        content_length = len(content_str)

        # Build context vector
        context_tensor = self._extract_context_vector(
            theme=theme, content_length=content_length, error_type=error_type, attempt=attempt
        ).to(self.device)

        # Generate CSS fix
        self.model.eval()
        with torch.no_grad():
            # Clamp top_k to vocab size (avoid index out of range)
            effective_top_k = min(20, self.tokenizer.vocab_size - 1)  # -1 to exclude PAD

            generated_sequences = self.model.generate(
                context=context_tensor,
                max_length=15,
                temperature=0.8,  # Balanced creativity
                top_k=effective_top_k,  # Anti-hallucination (clamped to vocab size)
                sos_token_idx=self.tokenizer.token2idx[self.tokenizer.SOS_TOKEN],
                eos_token_idx=self.tokenizer.token2idx[self.tokenizer.EOS_TOKEN],
            )

        # Decode to CSS string
        token_ids = generated_sequences[0]
        css_string = self.tokenizer.decode(token_ids, skip_special_tokens=True)

        # Validate generated classes
        css_classes = css_string.split()
        valid_classes = self._validate_generated_css(css_classes)

        if not valid_classes:
            logger.warning("⚠️  No valid classes generated, using fallback")
            if self.heuristic_healer:
                return cast(HealingResult, self.heuristic_healer.heal_layout(guardian_report, content, attempt))
            valid_classes = ["text-sm", "truncate"]  # Safe default

        final_css = " ".join(valid_classes)

        # Build style overrides (apply to problematic elements)
        style_overrides = {
            "hero_title": final_css,
            "hero_subtitle": final_css,
            "card_description": final_css,
        }

        logger.info(f"🧠 Neural fix (attempt {attempt}): {final_css}")

        return HealingResult(
            strategy=HealingStrategy.CSS_BREAK_WORD,  # Generic label
            style_overrides=style_overrides,
            content_modified=False,
            modified_content=None,
            description=f"Neural-generated CSS: {final_css}",
        )

    @classmethod
    def from_default_paths(cls, fallback_to_heuristic: bool = True) -> "NeuralHealer":
        """
        Create Neural Healer with default model paths.

        Args:
            fallback_to_heuristic: Use SmartHealer if model not found

        Returns:
            Configured NeuralHealer instance
        """
        model_path = Path("models/generative/style_generator_best.pth")
        vocab_path = Path("models/generative/tailwind_vocab.json")

        return cls(
            model_path=model_path if model_path.exists() else None,
            vocab_path=vocab_path if vocab_path.exists() else None,
            fallback_to_heuristic=fallback_to_heuristic,
        )


# Example usage
if __name__ == "__main__":
    # Create healer (will fallback to heuristic if model unavailable)
    healer = NeuralHealer.from_default_paths()

    # Simulate Guardian report
    guardian_report = {
        "approved": False,
        "reason": "Text overflow detected",
        "issues": ["hero_title overflow"],
        "fix_suggestion": "Reduce font size or add truncation",
    }

    # Content
    content = {
        "hero": {
            "title": "A" * 100,  # Pathological content
            "subtitle": "This is a test",
        }
    }

    # Generate fix
    result = healer.heal_layout(
        guardian_report=guardian_report,
        content=content,
        attempt=1,
        context={"theme": "brutalist", "error_type": "overflow"},
    )

    print(f"\n🧠 Generated fix: {result.style_overrides}")
    print(f"📝 Description: {result.description}")
