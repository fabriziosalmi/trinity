#!/bin/bash
# Trinity v0.5.0 - Neural Healer Activation Script
# This script automates the "Final Cut" workflow

set -e  # Exit on error

echo "============================================================"
echo "🧠 TRINITY v0.5.0 - NEURAL HEALER ACTIVATION"
echo "============================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Tabula Rasa
echo -e "${YELLOW}[1/4] Tabula Rasa (Reset Dataset)${NC}"
if [ -f "data/training_dataset.csv" ]; then
    echo "📦 Backing up old dataset..."
    mv data/training_dataset.csv data/training_dataset_old_$(date +%Y%m%d_%H%M%S).csv
    echo -e "${GREEN}✅ Old dataset backed up${NC}"
else
    echo "ℹ️  No existing dataset found (starting fresh)"
fi
echo ""

# Step 2: Feed the Beast
echo -e "${YELLOW}[2/4] Feed the Beast (Generate Training Data)${NC}"
echo "⏳ Generating 300 training samples with Guardian enabled..."
echo "   This will take ~15-20 minutes (300 builds × 3-4 sec each)"
echo ""

# Check if poetry is available
if command -v poetry &> /dev/null; then
    poetry run trinity mine-generate --count 300 --guardian
else
    echo -e "${RED}❌ Poetry not found. Please install: curl -sSL https://install.python-poetry.org | python3 -${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Training data generated${NC}"
echo ""

# Step 3: Train the Brain
echo -e "${YELLOW}[3/4] Train the Brain (LSTM Training)${NC}"
echo "🧠 Training LSTM Style Generator..."
echo "   Expected time: 5-10 minutes on CPU, 1-2 minutes on GPU"
echo ""

python -m trinity.components.generative_trainer

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Model trained successfully${NC}"
else
    echo -e "${RED}❌ Training failed. Check logs above.${NC}"
    exit 1
fi
echo ""

# Step 4: Neural Chaos Test
echo -e "${YELLOW}[4/4] The Neural Chaos Test (Grand Finale)${NC}"
echo "🎬 Testing Neural Healer with chaos content..."
echo ""

if command -v poetry &> /dev/null; then
    poetry run trinity chaos --neural
else
    python -m trinity.cli chaos --neural
fi

echo ""
echo "============================================================"
echo -e "${GREEN}🎉 NEURAL HEALER ACTIVATION COMPLETE!${NC}"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  • Check model: ls -lh models/generative/"
echo "  • Build with neural: poetry run trinity build --neural"
echo "  • View logs: tail -f logs/trinity.log"
echo ""
echo "Fallback behavior:"
echo "  If neural healer fails, SmartHealer automatically takes over."
echo ""
