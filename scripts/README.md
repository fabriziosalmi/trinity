# Trinity Scripts

Automation scripts for Trinity Core development and ML training.

## 📁 Available Scripts

### `nightly_training.sh` - Production Training Routine ⭐

**Purpose:** Fully automated pipeline to train production-grade model.

**What it does:**
1. Generates 100 diverse themes (5 categories × 20)
2. Mines 2000+ training samples with Guardian validation
3. Trains Random Forest model with quality gates
4. Validates F1-Score ≥ 0.90

**Runtime:** 2-3 hours (run overnight)

**Usage:**
```bash
# Run the full pipeline
./scripts/nightly_training.sh

# Or with poetry
poetry run ./scripts/nightly_training.sh
```

**Expected Output:**
```
🌙 TRINITY NIGHTLY TRAINING ROUTINE

STEP 1/3: Generating 100 themes... ✅
STEP 2/3: Mining 2000 samples... ✅ (1-2 hours)
STEP 3/3: Training model... ✅

Model Performance:
  F1-Score: 0.95+
  Precision: 0.90+
  Recall: 0.98+

🎉 Production model ready!
```

---

### `fast_training.sh` - Quick Validation

**Purpose:** Fast pipeline for testing (10 themes, 100 samples).

**Runtime:** 10-15 minutes

**Usage:**
```bash
./scripts/fast_training.sh
```

**Use case:** Testing changes to training pipeline.

---

### `mass_theme_generator.py` - The Centuria Factory

**Purpose:** Generate 100 diverse themes for robust ML training.

**Why:** Training on 3 themes = memorization. Training on 100 themes = generalization.

#### Quick Start

```bash
# Generate all 100 themes (takes ~15 minutes)
poetry run python scripts/mass_theme_generator.py

# Preview themes without generating
poetry run python scripts/mass_theme_generator.py --dry-run

# Generate specific category
poetry run python scripts/mass_theme_generator.py --category tech --count 20
```

#### Categories

The script generates themes across 5 diverse categories:

1. **Historical** (20 themes)
   - Victorian steampunk, Art Deco, 1980s neon, Y2K futuristic, etc.
   
2. **Tech** (20 themes)
   - DOS terminal, Material Design, Vaporwave, Cyberpunk, Matrix, etc.
   
3. **Artistic** (20 themes)
   - Bauhaus, Cubist, Pop Art, Minimalist, Graffiti, Pixel art, etc.
   
4. **Chaotic** (20 themes)
   - Glitch art, Trashcore, Comic Sans, BSOD, Geocities, etc.
   
5. **Professional** (20 themes)
   - Legal, Medical, Financial, Government, Academic, etc.

#### Full Pipeline

```bash
# Step 1: Generate themes
poetry run python scripts/mass_theme_generator.py

# Step 2: Collect training data with all themes
poetry run trinity mine-generate --count 5000

# Step 3: Verify dataset
poetry run trinity mine-stats

# Step 4: Train model
poetry run trinity train

# Step 5: Use predictive model
poetry run trinity build --theme cyberpunk_01 --predictive
```

#### Command-Line Options

```bash
# Show help
python scripts/mass_theme_generator.py --help

# Generate all categories
python scripts/mass_theme_generator.py

# Preview only (no generation)
python scripts/mass_theme_generator.py --dry-run

# Generate specific category
python scripts/mass_theme_generator.py --category historical

# Limit count per category
python scripts/mass_theme_generator.py --category tech --count 10

# Custom output path
python scripts/mass_theme_generator.py --output my_themes.json
```

#### Expected Output

```
🏭 Trinity Centuria Factory

Generating 100 themes...

✓ historical_01: Victorian steampunk with brass and dark wood...
✓ historical_02: Art Deco 1920s with gold geometric patterns...
...
✓ tech_01: DOS terminal green on black monospace...
...
✓ professional_20: Nonprofit compassionate soft pastels...

✅ Generation complete!

Success: 100 themes
Failed: 0 themes

Saved to: config/themes.json
Total themes: 103
```

#### Requirements

- LM Studio running with Qwen 2.5 Coder (or compatible model)
- `TRINITY_LM_STUDIO_URL` environment variable set (default: http://localhost:1234/v1)

#### Troubleshooting

**Error: "Cannot connect to LM Studio"**
```bash
# Check LM Studio is running
curl http://localhost:1234/v1/models

# Set correct URL
export TRINITY_LM_STUDIO_URL="http://localhost:1234/v1"
```

**Error: "Theme generation failed"**
- Increase timeout in `src/trinity/components/brain.py`
- Try with fewer themes first (`--count 5`)
- Check LM Studio model is loaded

---

## 🎯 The Math Behind 100 Themes

### Problem: Overfitting to Theme Names

With 3 themes:
```python
# Model learns patterns like:
if theme == "brutalist":
    risk = 0.8  # Brutalist is always risky
elif theme == "enterprise":
    risk = 0.2  # Enterprise is always safe
```

### Solution: Learning DOM Physics

With 100 themes:
```python
# Model forced to learn geometric constraints:
risk = (text_length * avg_char_width) / container_width
if risk > 1.0:
    return HIGH_RISK  # Text overflows container
```

### Impact

| Dataset | What Model Learns | F1-Score |
|---------|-------------------|----------|
| 3 themes | Theme-specific patterns | 0.918 |
| 100 themes | **DOM physics** | **0.95+** |

**Bottom line:** More theme diversity = better generalization = production-ready ML.

---

## 📊 Data Augmentation Strategy

```
┌─────────────────────────────────────────────────────────┐
│                   THEME DIVERSITY                       │
└─────────────────────────────────────────────────────────┘

Font Sizes:     text-xs, sm, base, lg, xl ... 9xl
Padding:        p-0, p-1, p-2 ... p-24
Borders:        none, border, border-2, border-4, border-8
Colors:         Pastels, Neons, Monochromes, Gradients
Spacing:        tight, normal, relaxed, loose
Shadows:        none, sm, md, lg, xl, 2xl
Rounded:        none, sm, md, lg, full
```

**Result:** 100 themes = 100 different "physics experiments" for the model to learn from.

---

## 🚀 Next Steps

After generating themes:

1. **Collect Data:**
   ```bash
   poetry run trinity mine-generate --count 5000
   ```

2. **Verify Quality:**
   ```bash
   poetry run trinity mine-stats
   # Look for: 103 themes, 40-60% success rate
   ```

3. **Train Model:**
   ```bash
   poetry run trinity train
   # Expected: F1 ≥ 0.95, Precision ≥ 0.90
   ```

4. **Deploy:**
   ```bash
   poetry run trinity build --theme vaporwave_03 --predictive
   ```

---

**Made with 🔥 by developers who understand that data diversity = model robustness.**
