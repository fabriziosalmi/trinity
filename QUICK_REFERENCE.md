# Trinity Quick Reference (v0.8.0)

## Fast Commands (Copy-Paste Ready)

### Testing

```bash
# Run all tests
pytest tests/ -v

# E2E tests only
pytest tests/test_e2e_complete.py -v

# Multiclass pipeline tests
pytest tests/test_multiclass_pipeline.py -v

# Docker E2E validation
./scripts/test_docker_e2e.sh
```

### Build & Generate

### Test Single Theme Generation
```bash
poetry run trinity theme-gen "Cyberpunk neon pink cyan" --name test_cyber
```

### Test Build with Generated Theme
```bash
poetry run trinity build --theme test_cyber --predictive
```

### Build with Self-Healing & Guardian
```bash
poetry run trinity build --theme brutalist --guardian --output test.html
```

### Fast Training Pipeline
```bash
./scripts/fast_training.sh
```

### Production Training Pipeline
```bash
./scripts/nightly_training.sh
```

### Check Dataset Stats
```bash
poetry run trinity mine-stats
```

### Generate More Samples
```bash
poetry run trinity mine-generate --count 500 --guardian
```

### Train Model
```bash
poetry run trinity train
```

---

## Troubleshooting

### "Cannot connect to LM Studio"
```bash
# Check LM Studio is running
curl http://localhost:1234/v1/models

# Or change URL
export TRINITY_LM_STUDIO_URL="http://localhost:1234/v1"
```

### "Insufficient data" error
```bash
# Need more samples
poetry run trinity mine-generate --count 1000 --guardian
```

### "Model performance below threshold"
```bash
# Generate diverse themes first
./scripts/nightly_training.sh
```

---

## Expected Metrics

Model performance depends on the amount and diversity of training data collected. With limited training data (e.g., 3 themes, few samples), the predictor may not meet the quality thresholds required to train.

---

## File Locations

- Themes: `config/themes.yaml`
- Training data: `data/training_dataset.csv`
- Trained models: `models/*.pkl`
- Model metadata: `models/*_metadata.json`
