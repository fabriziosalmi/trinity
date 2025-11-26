#!/bin/bash
# Trinity v0.5.0 - Production Training Pipeline
# Executes complete training with 2611 samples dataset

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Activate virtual environment
source .venv/bin/activate

# Suppress Python warnings for clean output
export PYTHONWARNINGS=ignore

echo "============================================================"
echo "🧠 TRINITY v0.5.0 - PRODUCTION TRAINING SESSION"
echo "============================================================"
echo ""
echo "Dataset: data/training_dataset.csv"
echo "Expected samples: 2611"
echo ""

# Step 1: Dataset Statistics
echo "============================================================"
echo "📊 STEP 1: Dataset Statistics"
echo "============================================================"
poetry run trinity mine-stats
echo ""

# Step 2: Train Neural Healer (LSTM)
echo "============================================================"
echo "🧠 STEP 2: Training Neural Healer (LSTM Style Generator)"
echo "============================================================"
echo "Configuration:"
echo "  - Epochs: 100"
echo "  - Batch Size: 32"
echo "  - Early Stopping: Enabled"
echo ""
python -m trinity.components.generative_trainer \
  --dataset data/training_dataset.csv \
  --output models/generative \
  --epochs 100 \
  --batch-size 32
echo ""

# Step 3: Train Layout Risk Predictor (Random Forest)
echo "============================================================"
echo "🎯 STEP 3: Training Layout Risk Predictor (Random Forest)"
echo "============================================================"
poetry run trinity train \
  --dataset-path data/training_dataset.csv \
  --output-dir models/
echo ""

# Step 4: Validation Tests
echo "============================================================"
echo "🧪 STEP 4: Validation Tests"
echo "============================================================"

echo ""
echo "Test 1: Normal content with Neural Healer + Guardian"
echo "------------------------------------------------------------"
poetry run trinity build --theme brutalist --neural --guardian | tail -20
echo ""

echo "Test 2: Neural Chaos Mode"
echo "------------------------------------------------------------"
poetry run trinity chaos --neural --theme brutalist | tail -30
echo ""

# Summary
echo "============================================================"
echo "✅ TRAINING SESSION COMPLETE!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Review training metrics above"
echo "  2. Check models in models/ directory"
echo "  3. Run additional validation: poetry run pytest tests/"
echo "  4. Commit changes: git add -A && git commit -m 'feat: production training'"
echo ""
