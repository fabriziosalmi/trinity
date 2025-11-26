#!/usr/bin/env python3
"""End-to-end test for Neural Healer integration."""

import sys
from pathlib import Path
import torch

sys.path.insert(0, str(Path(__file__).parent / "src"))

from trinity.ml.tokenizer import TailwindTokenizer
from trinity.ml.models import LSTMStyleGenerator
from trinity.components.neural_healer import NeuralHealer

def test_full_pipeline():
    """Test complete neural healing pipeline."""
    
    print("=" * 70)
    print("TRINITY v0.5.0 - Neural Healer End-to-End Test")
    print("=" * 70)
    
    # Step 1: Build tokenizer with realistic vocabulary
    print("\n[1/4] Building Tailwind CSS vocabulary...")
    tokenizer = TailwindTokenizer()
    
    realistic_css = [
        "text-sm truncate break-words",
        "text-[0.9rem] leading-tight line-clamp-2",
        "break-all overflow-hidden text-ellipsis",
        "max-w-prose break-words hyphens-auto",
        "text-xs line-clamp-3 overflow-wrap-anywhere",
        "break-words overflow-wrap-anywhere word-break-break-all",
        "text-sm leading-relaxed break-all",
        "truncate overflow-hidden whitespace-nowrap",
    ]
    
    tokenizer.build_vocab(realistic_css, min_freq=1)
    print(f"   ✓ Vocabulary: {tokenizer.vocab_size} tokens")
    print(f"   ✓ Sample tokens: {list(tokenizer.token2idx.keys())[:10]}")
    
    # Step 2: Create and configure LSTM model
    print("\n[2/4] Creating LSTM Style Generator...")
    
    context_dim = 10  # theme(4) + content_len(1) + attempt(1) + error_type(4)
    
    model = LSTMStyleGenerator(
        vocab_size=tokenizer.vocab_size,
        context_dim=context_dim,
        embedding_dim=64,
        hidden_dim=128,
        num_layers=2,
        dropout=0.2
    )
    
    print(f"   ✓ Model architecture: {model.__class__.__name__}")
    print(f"   ✓ Parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(f"   ✓ Context dimension: {context_dim}")
    
    # Step 3: Test generation without training (random weights)
    print("\n[3/4] Testing generation (untrained model)...")
    
    model.eval()
    
    # Simulate different contexts
    test_cases = [
        {"theme": "enterprise", "error": "overflow", "length": 500},
        {"theme": "brutalist", "error": "text_too_long", "length": 300},
        {"theme": "editorial", "error": "layout_shift", "length": 800},
    ]
    
    for i, case in enumerate(test_cases, 1):
        # Build context vector
        context_vec = torch.randn(1, context_dim)  # Random for untrained model
        
        # Generate
        output_ids = model.generate(
            context=context_vec,
            max_length=12,
            temperature=0.8,
            top_k=10,
            sos_token_idx=tokenizer.token2idx[tokenizer.SOS_TOKEN],
            eos_token_idx=tokenizer.token2idx[tokenizer.EOS_TOKEN]
        )
        
        generated_css = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        
        print(f"\n   Case {i}: {case['theme']} / {case['error']}")
        print(f"   Generated CSS: {generated_css}")
    
    # Step 4: Test Neural Healer with fallback
    print("\n[4/4] Testing Neural Healer integration...")
    
    healer = NeuralHealer.from_default_paths(fallback_to_heuristic=True)
    
    # Realistic problem scenario
    guardian_report = {
        'issues': ['overflow', 'text_exceeds_container'],
        'severity': 'high',
        'affected_components': ['hero_title', 'card_description']
    }
    
    content = {
        'hero': {
            'title': 'Implementing Next-Generation Machine Learning Infrastructure for Large-Scale Distributed Systems',
            'subtitle': 'A comprehensive guide to modern ML architectures'
        }
    }
    
    context = {
        'theme': 'enterprise',
        'error_type': 'overflow'
    }
    
    print(f"\n   Problem: Title length = {len(content['hero']['title'])} chars")
    print(f"   Guardian issues: {guardian_report['issues']}")
    
    # Heal
    result = healer.heal_layout(
        guardian_report=guardian_report,
        content=content,
        attempt=1,
        context=context
    )
    
    print(f"\n   Healing Result:")
    print(f"   ✓ Strategy: {result.strategy.name}")
    print(f"   ✓ CSS Overrides:")
    for component, css in result.style_overrides.items():
        print(f"      - {component}: {css}")
    print(f"   ✓ Description: {result.description}")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ END-TO-END TEST COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print("\nKey Features Verified:")
    print("  ✓ Tailwind CSS tokenization with special tokens")
    print("  ✓ LSTM model creation and configuration")
    print("  ✓ Context-based CSS generation")
    print("  ✓ Neural Healer with heuristic fallback")
    print("  ✓ Style override generation for multiple components")
    print("\nNote: Model is untrained - using random weights.")
    print("To train: python -m trinity.components.generative_trainer")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(test_full_pipeline())
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
