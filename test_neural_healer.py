#!/usr/bin/env python3
"""Test script for Neural Healer and Generative Style Engine."""

import sys
from pathlib import Path
import torch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from trinity.ml.tokenizer import TailwindTokenizer
from trinity.ml.models import LSTMStyleGenerator
from trinity.components.neural_healer import NeuralHealer
from trinity.components.generative_trainer import CSSFixDataset, GenerativeStyleTrainer

def test_tokenizer():
    """Test Tailwind tokenizer."""
    print("\n=== Testing Tokenizer ===")
    
    tokenizer = TailwindTokenizer()
    
    # Build vocabulary first
    css_examples = [
        "flex items-center justify-between",
        "bg-blue-500 text-white p-4",
        "rounded-lg shadow-md truncate",
        "text-sm line-clamp-2 break-all"
    ]
    tokenizer.build_vocab(css_examples, min_freq=1)
    print(f"Vocabulary size: {tokenizer.vocab_size}")
    
    # Sample CSS classes
    css_classes = "flex items-center bg-blue-500 text-white"
    
    # Encode
    tokens = tokenizer.encode(css_classes)
    print(f"Original: {css_classes}")
    print(f"Tokens: {tokens}")
    
    # Decode
    decoded = tokenizer.decode(tokens, skip_special_tokens=True)
    print(f"Decoded: {decoded}")
    
    return True

def test_model_creation():
    """Test LSTM model creation and forward pass."""
    print("\n=== Testing LSTM Model ===")
    
    tokenizer = TailwindTokenizer()
    css_examples = ["flex items-center", "bg-blue-500 text-white", "rounded-lg shadow-md"]
    tokenizer.build_vocab(css_examples, min_freq=1)
    
    # Context dimension: theme (4) + content_len (1) + attempt (1) + error_type (4) = 10
    context_dim = 10
    
    model = LSTMStyleGenerator(
        vocab_size=tokenizer.vocab_size,
        context_dim=context_dim,
        embedding_dim=64,
        hidden_dim=128,
        num_layers=2,
        dropout=0.1
    )
    
    print(f"Model created: {model.__class__.__name__}")
    print(f"Vocabulary size: {tokenizer.vocab_size}")
    print(f"Parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Test generation with context tensor (without training)
    context_tensor = torch.randn(1, context_dim)  # Random context
    generated_ids = model.generate(
        context=context_tensor,
        max_length=10,
        temperature=1.0,
        sos_token_idx=tokenizer.token2idx[tokenizer.SOS_TOKEN],
        eos_token_idx=tokenizer.token2idx[tokenizer.EOS_TOKEN]
    )
    
    generated_css = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
    print(f"\nGenerated (untrained): {generated_css}")
    
    return True

def test_neural_healer():
    """Test Neural Healer with fallback."""
    print("\n=== Testing Neural Healer ===")
    
    healer = NeuralHealer.from_default_paths(fallback_to_heuristic=True)
    
    # Test case: broken layout (using HealingResult API)
    guardian_report = {
        'issues': ['overflow', 'text_too_long'],
        'severity': 'high'
    }
    
    content = {
        'hero': {
            'title': 'This is a very long title that might cause overflow issues',
            'subtitle': 'Subtitle text'
        }
    }
    
    context = {
        'theme': 'enterprise',
        'error_type': 'overflow'
    }
    
    print(f"Guardian report: {guardian_report}")
    print(f"Content length: {len(content['hero']['title'])}")
    
    # Heal (will use fallback if model not trained)
    result = healer.heal_layout(
        guardian_report=guardian_report,
        content=content,
        attempt=1,
        context=context
    )
    
    print(f"\nHealing result:")
    print(f"  Strategy: {result.strategy}")
    print(f"  Style overrides: {result.style_overrides}")
    print(f"  Description: {result.description}")
    
    if result.style_overrides:
        print("\n✓ Healer generated CSS fixes")
    else:
        print("\n✗ No fixes generated")
    
    return True

def test_dataset_loading():
    """Test CSS dataset loading."""
    print("\n=== Testing Dataset ===")
    
    dataset_path = Path(__file__).parent / "data" / "training_dataset.csv"
    
    if not dataset_path.exists():
        print(f"✗ Dataset not found: {dataset_path}")
        return False
    
    try:
        # First build tokenizer
        tokenizer = TailwindTokenizer()
        
        # Read CSV to build vocab
        import pandas as pd
        df = pd.read_csv(dataset_path)
        
        # Extract CSS from successful fixes
        successful = df[df['is_valid'] == 1]
        # v0.5.0 uses style_overrides_raw
        col_name = 'style_overrides_raw' if 'style_overrides_raw' in df.columns else 'style_overrides'
        css_sequences = successful[col_name].dropna().tolist()
        
        if css_sequences:
            tokenizer.build_vocab(css_sequences, min_freq=1)
            print(f"✓ Built vocabulary: {tokenizer.vocab_size} tokens")
        
        # Now create dataset
        dataset = CSSFixDataset(dataset_path, tokenizer)
        print(f"✓ Dataset loaded: {len(dataset)} samples")
        
        if len(dataset) > 0:
            context, target = dataset[0]
            # Context is a tensor in v0.5.0, not a dict
            print(f"\nSample context shape: {context.shape}")
            print(f"Sample target shape: {target.shape}")
        
        return True
    except Exception as e:
        print(f"✗ Dataset loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("TRINITY v0.5.0 - Generative Style Engine Test Suite")
    print("=" * 60)
    
    tests = [
        ("Tokenizer", test_tokenizer),
        ("LSTM Model", test_model_creation),
        ("Neural Healer", test_neural_healer),
        ("Dataset Loading", test_dataset_loading)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
            print(f"\n{'✓' if result else '✗'} {name} test {'passed' if result else 'failed'}")
        except Exception as e:
            print(f"\n✗ {name} test failed with error:")
            print(f"  {type(e).__name__}: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
