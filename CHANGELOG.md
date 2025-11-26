# Changelog

All notable changes to Trinity Core will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- ONNX model export for safer serialization
- Unit test coverage >80%
- Theme preview server (live reload)

---

## [0.5.0] - 2025-11-26 (Phase 5: Generative Style Engine)

### Added
- **Neural Healer:** LSTM-based generative CSS fix generator
  - `src/trinity/ml/tokenizer.py` - Tailwind CSS vocabulary and tokenization
  - `src/trinity/ml/models.py` - Seq2Seq LSTM Style Generator (2 layers, 128 hidden)
  - `src/trinity/components/generative_trainer.py` - PyTorch training pipeline
  - `src/trinity/components/neural_healer.py` - Generative replacement for SmartHealer
- **Transfer Learning:** Model learns fixes across 100+ themes (Centuria Factory)
  - CSS solutions learned on Brutalist apply to Editorial, Medical, etc.
  - Generalizes patterns: "overflow-x-hidden fixes horizontal scroll" regardless of theme
- **Anti-Hallucination:** Token validation and Top-K sampling
  - Whitelist of valid Tailwind classes
  - Temperature-controlled generation (0.8 default)
  - Fallback to heuristic SmartHealer if model unavailable

### Changed
- **Dependencies:** Added PyTorch >= 2.0.0 and tqdm for deep learning
- **Training Data:** Utilizes `css_overrides` from successful fixes in `training_dataset.csv`
- **Healing Strategy:** Transitions from fixed heuristics to learned generation

### Technical Details
- **Model Architecture:**
  - Encoder: Context (theme + content_length + error_type) → Hidden state
  - Decoder: 2-layer LSTM generates CSS token sequences
  - Vocabulary: ~200 Tailwind utility classes
- **Training:**
  - Batch size: 32
  - Learning rate: 0.001 (Adam optimizer)
  - Early stopping: 5 epochs patience
  - CrossEntropyLoss with <PAD> ignore
- **Inference:**
  - Temperature sampling for creativity vs precision
  - Top-K filtering (K=20) prevents rare token hallucinations
  - Output validation against Tailwind whitelist

### Migration Guide
```python
# Old (v0.4.0): Heuristic Healer
from trinity.components.healer import SmartHealer
healer = SmartHealer()

# New (v0.5.0): Neural Healer with fallback
from trinity.components.neural_healer import NeuralHealer
healer = NeuralHealer.from_default_paths(fallback_to_heuristic=True)

# Usage remains identical
result = healer.heal_layout(guardian_report, content, attempt=1)
```

### Training the Model
```bash
# Generate training data (if not already done)
trinity mine-generate --count 1000 --themes all

# Train generative model
python -m trinity.components.generative_trainer \
    --dataset data/training_dataset.csv \
    --output models/generative \
    --epochs 50 \
    --batch-size 32

# Model outputs:
# - models/generative/style_generator_best.pth (trained LSTM)
# - models/generative/tailwind_vocab.json (tokenizer vocabulary)
```

### Performance
- **Before (Heuristic):** 4 fixed strategies, theme-agnostic
- **After (Generative):** ∞ learned strategies, theme-aware
- **F1-Score:** TBD (requires production deployment for evaluation)
- **Inference Speed:** ~10ms per fix (CPU), ~2ms (GPU)

---

---

## [0.4.0] - 2025-11-26

### Added
- **Centuria Factory:** Text-to-Theme generation system using local LLM
  - `trinity theme-gen` CLI command for single theme generation
  - `scripts/mass_theme_generator.py` for batch generation (100 themes)
  - 5 theme categories: Historical, Tech, Artistic, Chaotic, Professional
- **Production automation scripts:**
  - `scripts/fast_training.sh` - Quick ML pipeline validation (10-15 min)
  - `scripts/nightly_training.sh` - Full production training (2-3 hours)
- **CONTRIBUTING.md** - Development setup and contribution guidelines
- **SECURITY.md** - Vulnerability reporting policy and security considerations
- **CHANGELOG.md** - Version history in Keep a Changelog format

### Changed
- **main.py** replaced with 20-line clean wrapper delegating to `trinity.cli`
  - Old version backed up as `main_legacy.py`
- **Recursion protection:** Added depth guard (max 50 levels) to prevent stack overflow
- **Duplicate detection:** Warning when merging themes with overlapping keys

### Removed
- **sys.path hacking** from all scripts (now uses proper Poetry package structure)
- **TODO comments** from active codebase (moved to GitHub Issues)
- **Hardcoded build dates** (replaced with `datetime.utcnow()`)

### Security
- **Pickle warnings:** Added security notices to all model load/save operations
  - Module docstrings in `trainer.py` and `predictor.py`
  - Runtime logging warnings when loading `.pkl` files
- **Documentation:** Security policy documented in SECURITY.md

### Fixed
- Import errors when running scripts outside Poetry environment
- Missing datetime imports in builder modules
- Obsolete TODOs referencing unimplemented features

---

## [0.3.0] - 2025-11-25

### Added
- **Neural-Symbolic Architecture (Phase 2 & 3):**
  - `LayoutRiskTrainer` - Random Forest classifier training pipeline
  - `LayoutRiskPredictor` - Pre-emptive ML-based healing
  - Quality gates: F1 ≥ 0.60, Precision ≥ 0.50, Recall ≥ 0.50
- **CLI commands:**
  - `trinity train` - Train layout risk prediction model
  - `trinity mine-stats` - Show dataset statistics
  - `trinity mine-generate` - Automated data collection
- **Model versioning:** Timestamped `.pkl` files with JSON metadata sidecars
- **Production model:** Trained on 1,355 samples, F1-Score: 0.918

### Changed
- **Self-healing logic:** Now ML-guided instead of purely heuristic
  - Predictor estimates breakage probability before rendering
  - High-risk content (>70%) triggers pre-emptive strategies
- **Training dataset format:** Added features for ML (theme, strategy, content metrics)

### Dependencies
- Added `scikit-learn>=1.3.0` for Random Forest classifier
- Added `pandas>=2.0.0` for data manipulation
- Added `joblib>=1.3.0` for model serialization

---

## [0.2.0] - 2025-11-24

### Added
- **Guardian QA system:** Playwright-based visual validation
  - DOM overflow detection via JavaScript
  - Optional Vision AI analysis (Qwen VL)
- **Self-healing engine:** Progressive CSS strategies
  - `CSS_BREAK_WORD` - Inject break-all and overflow-wrap
  - `FONT_SHRINK` - Reduce font sizes (text-5xl → text-3xl)
  - `CSS_TRUNCATE` - Add ellipsis and line-clamp
  - `CONTENT_CUT` - Truncate strings (nuclear option)
- **Data mining:** Automated training data collection
  - `TrinityMiner` class collects build events
  - CSV export: `data/training_dataset.csv`
- **Chaos mode:** Intentional broken content testing

### Changed
- **README:** Complete rewrite explaining Neural-Symbolic approach
- **Docker setup:** Production-ready containerization
- **Error handling:** Custom exceptions with actionable messages

---

## [0.1.0] - 2025-11-20

### Added
- **Core static site generator:**
  - Jinja2 templates (Skeleton layer)
  - Tailwind CSS themes (Brutalist, Enterprise, Editorial)
  - LLM content generation via LM Studio (Brain layer)
- **CLI interface:** Typer-based modern CLI
  - `trinity build` - Basic site generation
  - `trinity list-themes` - Show available themes
- **Docker development environment:**
  - `dev.sh` / `dev.bat` scripts for cross-platform use
  - `docker-compose.yml` with builder + web server

### Dependencies
- Python 3.10+
- Poetry for dependency management
- Docker Desktop (optional)
- LM Studio with Qwen 2.5 Coder (optional)

---

**Legend:**
- `Added` - New features
- `Changed` - Changes to existing functionality
- `Deprecated` - Features marked for removal
- `Removed` - Deleted features
- `Fixed` - Bug fixes
- `Security` - Vulnerability fixes or security improvements
