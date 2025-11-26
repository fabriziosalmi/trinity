"""
Trinity ML Module - Neural Style Generation

This module implements generative models for CSS style healing.
Unlike heuristic strategies, these models learn from data to generate fixes.

Components:
- tokenizer.py: Tailwind CSS vocabulary and tokenization
- models.py: LSTM-based Seq2Seq style generator
- training.py: PyTorch training pipeline

Phase: v0.5.0 (Generative Style Engine)
"""

from trinity.ml.tokenizer import TailwindTokenizer
from trinity.ml.models import LSTMStyleGenerator

__all__ = ["TailwindTokenizer", "LSTMStyleGenerator"]
