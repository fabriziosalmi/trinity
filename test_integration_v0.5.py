#!/usr/bin/env python3
"""
Test script for v0.5.0 integration: DataMiner → Trainer → Neural Healer
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from trinity.components.dataminer import TrinityMiner

def test_dataminer_schema():
    """Test DataMiner creates v0.5.0 schema with style_overrides_raw column."""
    
    print("=" * 70)
    print("TEST 1: DataMiner Schema Upgrade (v0.5.0)")
    print("=" * 70)
    
    # Use test dataset
    test_csv = Path(__file__).parent / "test_dataset_v0.5.csv"
    if test_csv.exists():
        test_csv.unlink()
    
    miner = TrinityMiner(dataset_path=test_csv)
    
    # Log a successful build with CSS overrides
    print("\n[1] Logging successful build with CSS overrides...")
    miner.log_build_event(
        theme="enterprise",
        content={"hero": {"title": "Test " * 50}},
        strategy="CSS_BREAK_WORD",
        guardian_verdict=True,
        guardian_reason="",
        css_overrides={
            "hero_title": "text-sm break-all overflow-hidden",
            "card_description": "truncate text-ellipsis"
        }
    )
    
    # Verify CSV has new column
    print("\n[2] Verifying CSV schema...")
    with open(test_csv, 'r') as f:
        header = f.readline().strip()
        data = f.readline().strip()
    
    print(f"Header: {header}")
    
    if 'style_overrides_raw' in header:
        print("✅ Column 'style_overrides_raw' exists")
    else:
        print("❌ Column 'style_overrides_raw' missing!")
        return False
    
    # Parse data row
    print(f"\nData row preview: {data[:150]}...")
    
    # Read CSV with pandas to properly handle quoted JSON
    print("\n[3] Reading CSV with pandas...")
    import pandas as pd
    df = pd.read_csv(test_csv)
    
    if len(df) == 0:
        print("❌ No data rows")
        return False
    
    style_col = df.iloc[0]['style_overrides_raw']
    print(f"\nstyle_overrides_raw value: {style_col}")
    
    if pd.isna(style_col) or not style_col.strip():
        print("❌ style_overrides_raw is empty")
        return False
    
    try:
        css_dict = json.loads(style_col)
        print(f"✅ Parsed CSS dict: {css_dict}")
        
        # Verify content
        if "hero_title" in css_dict and "break-all" in css_dict["hero_title"]:
            print("✅ CSS overrides correctly serialized")
            return True
        else:
            print("❌ CSS content incorrect")
            return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False


def test_trainer_reads_column():
    """Test GenerativeTrainer can read style_overrides_raw column."""
    
    print("\n" + "=" * 70)
    print("TEST 2: GenerativeTrainer Reads v0.5.0 Schema")
    print("=" * 70)
    
    from trinity.ml.tokenizer import TailwindTokenizer
    from trinity.components.generative_trainer import CSSFixDataset
    
    test_csv = Path(__file__).parent / "test_dataset_v0.5.csv"
    
    if not test_csv.exists():
        print("❌ Test CSV not found (run test 1 first)")
        return False
    
    print("\n[1] Building tokenizer vocabulary...")
    tokenizer = TailwindTokenizer()
    
    # Minimal vocab for testing
    css_samples = [
        "text-sm break-all overflow-hidden",
        "truncate text-ellipsis",
        "break-words line-clamp-2"
    ]
    tokenizer.build_vocab(css_samples, min_freq=1)
    print(f"✅ Vocabulary: {tokenizer.vocab_size} tokens")
    
    print("\n[2] Loading dataset...")
    try:
        dataset = CSSFixDataset(test_csv, tokenizer, max_seq_length=20)
        
        print(f"✅ Dataset loaded: {len(dataset)} samples")
        
        if len(dataset) > 0:
            # Dataset returns (context, target) tuple
            context, target = dataset[0]
            print(f"\nContext vector shape: {context.shape}")
            print(f"Target sequence shape: {target.shape}")
            
            # Decode target
            target_ids = target.tolist()
            decoded_css = tokenizer.decode(target_ids, skip_special_tokens=True)
            print(f"\nDecoded target CSS: {decoded_css}")
            
            if decoded_css:
                print("✅ Trainer successfully reads and decodes CSS targets")
                return True
            else:
                print("❌ Decoded CSS is empty")
                return False
        else:
            print("❌ No samples in dataset")
            return False
    
    except Exception as e:
        print(f"❌ Dataset loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cli_flag():
    """Test --neural flag is available in CLI."""
    
    print("\n" + "=" * 70)
    print("TEST 3: CLI --neural Flag")
    print("=" * 70)
    
    print("\n[1] Checking --neural flag in build command...")
    import subprocess
    
    result = subprocess.run(
        ["python", "-m", "trinity.cli", "build", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    if "--neural" in result.stdout:
        print("✅ --neural flag exists in build command")
        flag_found = True
    else:
        print("❌ --neural flag not found in build command")
        flag_found = False
    
    print("\n[2] Checking --neural flag in chaos command...")
    result = subprocess.run(
        ["python", "-m", "trinity.cli", "chaos", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    if "--neural" in result.stdout:
        print("✅ --neural flag exists in chaos command")
        return flag_found and True
    else:
        print("❌ --neural flag not found in chaos command")
        return False


def main():
    """Run all integration tests."""
    
    print("\n" + "=" * 70)
    print("TRINITY v0.5.0 - INTEGRATION TEST SUITE")
    print("DataMiner Schema → Trainer → Neural Healer → CLI")
    print("=" * 70)
    
    results = []
    
    # Test 1: DataMiner schema
    try:
        result = test_dataminer_schema()
        results.append(("DataMiner Schema v0.5.0", result))
    except Exception as e:
        print(f"\n❌ Test 1 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("DataMiner Schema v0.5.0", False))
    
    # Test 2: Trainer reads new column
    try:
        result = test_trainer_reads_column()
        results.append(("GenerativeTrainer Reads v0.5.0", result))
    except Exception as e:
        print(f"\n❌ Test 2 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("GenerativeTrainer Reads v0.5.0", False))
    
    # Test 3: CLI flag
    try:
        result = test_cli_flag()
        results.append(("CLI --neural Flag", result))
    except Exception as e:
        print(f"\n❌ Test 3 failed with exception: {e}")
        results.append(("CLI --neural Flag", False))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    total_passed = sum(1 for _, p in results if p)
    total = len(results)
    
    print(f"\nTotal: {total_passed}/{total} tests passed")
    
    if total_passed == total:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("\nNext steps:")
        print("  1. Rename old dataset: mv data/training_dataset.csv data/training_dataset_old.csv")
        print("  2. Generate new data: poetry run trinity mine-generate --count 50 --guardian")
        print("  3. Train model: python -m trinity.components.generative_trainer")
        print("  4. Test neural inference: poetry run trinity chaos --neural")
        return 0
    else:
        print(f"\n⚠️  {total - total_passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
