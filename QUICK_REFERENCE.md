# 🚀 Trinity Quick Reference

## Fast Commands (Copy-Paste Ready)

### Test Single Theme Generation
```bash
poetry run trinity theme-gen "Cyberpunk neon pink cyan" --name test_cyber
```

### Test Build with Generated Theme
```bash
poetry run trinity build --theme test_cyber --predictive
```

### Fast Training Pipeline (10-15 min)
```bash
./scripts/fast_training.sh
```

### Production Training Pipeline (2-3 hours)
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
curl http://192.168.100.12:1234/v1/models

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

### With 3 Themes (Current)
- F1-Score: 0.918
- Precision: 0.867
- Recall: 0.975

### With 100 Themes (After nightly_training.sh)
- F1-Score: **0.95+**
- Precision: **0.90+**
- Recall: **0.98+**

---

## File Locations

- Themes: `config/themes.json`
- Training data: `data/training_dataset.csv`
- Trained models: `models/*.pkl`
- Model metadata: `models/*_metadata.json`

---

**Remember:** The goal is not perfect code. The goal is a model that understands DOM physics. 🔥
