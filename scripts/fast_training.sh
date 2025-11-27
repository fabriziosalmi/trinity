#!/bin/bash
# Trinity - Fast Training Routine (for testing)
# 10 themes + 100 samples = Quick validation

set -e

echo "🚀 TRINITY FAST TRAINING (Test Mode)"
echo ""
echo "Generating 10 themes + 100 samples for quick validation..."
echo ""

# Step 1: Generate 10 themes
echo "📝 Generating 10 themes (2 per category)..."
poetry run python scripts/mass_theme_generator.py --count 2 --category tech
poetry run python scripts/mass_theme_generator.py --count 2 --category artistic
poetry run python scripts/mass_theme_generator.py --count 2 --category chaotic
poetry run python scripts/mass_theme_generator.py --count 2 --category historical
poetry run python scripts/mass_theme_generator.py --count 2 --category professional

echo ""

# Step 2: Mine 100 samples
echo "⛏️  Mining 100 samples..."
poetry run trinity mine-generate --count 100 --guardian

echo ""

# Step 3: Stats
echo "📊 Dataset Statistics:"
poetry run trinity mine-stats

echo ""

# Step 4: Train
echo "🧠 Training model..."
poetry run trinity train

echo ""
echo "✅ Fast training complete!"
echo ""
echo "This is for testing only. For production, run:"
echo "  ./scripts/nightly_training.sh"
echo ""
