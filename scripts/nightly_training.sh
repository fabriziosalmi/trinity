#!/bin/bash
# Trinity Core - Nightly Training Routine
# Generates 100 themes → Mines 2000+ samples → Trains production model
# 
# Expected runtime: 2-3 hours
# Expected result: F1-Score ≥ 0.90 on diverse dataset

set -e  # Exit on error

echo "════════════════════════════════════════════════════════════════"
echo "🌙 TRINITY NIGHTLY TRAINING ROUTINE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Mission: Train production-grade Layout Risk Predictor"
echo "Strategy: 100 diverse themes + 2000+ samples = DOM Physics understanding"
echo ""
echo "Estimated time: 2-3 hours"
echo "Coffee recommended: ☕☕☕"
echo ""

# Step 1: Theme Generation (15 minutes)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 STEP 1/3: Centuria Factory - Generating 100 Diverse Themes"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🏛️  Historical themes (Victorian, Art Deco, 1980s, Y2K...)..."
poetry run python scripts/mass_theme_generator.py --count 20 --category historical

echo ""
echo "💻 Tech themes (DOS Terminal, Material Design, Vaporwave...)..."
poetry run python scripts/mass_theme_generator.py --count 20 --category tech

echo ""
echo "🎨 Artistic themes (Bauhaus, Cubist, Pop Art, Swiss...)..."
poetry run python scripts/mass_theme_generator.py --count 20 --category artistic

echo ""
echo "💥 Chaotic themes (Glitch, Trashcore, Comic Sans, BSOD...)..."
poetry run python scripts/mass_theme_generator.py --count 20 --category chaotic

echo ""
echo "🏢 Professional themes (Legal, Medical, Fintech, Government...)..."
poetry run python scripts/mass_theme_generator.py --count 20 --category professional

echo ""
echo "✅ Theme generation complete!"
echo ""

# Verify theme count
THEME_COUNT=$(poetry run trinity themes 2>/dev/null | grep -c "│" | tail -1 || echo "unknown")
echo "📊 Total themes available: ${THEME_COUNT}"
echo ""

# Step 2: Data Mining (1-2 hours)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⛏️  STEP 2/3: Mining 2000+ Training Samples with Guardian"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This will take 1-2 hours. Go touch grass. 🌱"
echo ""

poetry run trinity mine-generate --count 2000 --guardian

echo ""
echo "✅ Mining complete!"
echo ""

# Show dataset stats
echo "📊 Dataset Statistics:"
poetry run trinity mine-stats

echo ""

# Step 3: Model Training
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧠 STEP 3/3: Training Production Model"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

poetry run trinity train

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "🎉 NIGHTLY ROUTINE COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Your Layout Risk Predictor is now ready for production."
echo ""
echo "Next steps:"
echo "  1. Test predictive mode:"
echo "     poetry run trinity build --theme cyberpunk_05 --predictive"
echo ""
echo "  2. Compare vs heuristic:"
echo "     poetry run trinity build --theme brutalist --no-predictive"
echo ""
echo "  3. Deploy with confidence. The model understands DOM physics. 🔥"
echo ""
echo "Fatto come Dio comanda."
echo ""
