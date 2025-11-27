# Trinity - MLOps Setup Guide

## Overview

Trinity uses **DVC (Data Version Control)** and **MLflow** for model and dataset versioning instead of committing large binary files to Git.

## Why Not Commit Models to Git?

❌ **Problems with Git-committed models:**
- Large file sizes bloat repository
- No proper versioning or comparison
- Difficult to track model lineage
- No metrics/parameters tracking
- Merge conflicts on binary files

✅ **Benefits of DVC + MLflow:**
- Lightweight metadata in Git
- Cloud storage for artifacts
- Experiment tracking
- Model registry
- Reproducible pipelines

## Setup Instructions

### 1. Install DVC

```bash
pip install dvc dvc-s3  # or dvc-gs, dvc-azure depending on storage
```

### 2. Initialize DVC

```bash
cd /path/to/trinity
dvc init
```

This creates `.dvc/` directory and adds `.dvc/config` to Git.

### 3. Configure Remote Storage

Choose your storage backend:

#### Option A: Local Storage (Development)
```bash
dvc remote add -d local /path/to/trinity-artifacts
```

#### Option B: S3 (Production)
```bash
dvc remote add -d s3remote s3://trinity-ml-artifacts/models
dvc remote modify s3remote region us-west-2
```

#### Option C: Google Cloud Storage
```bash
dvc remote add -d gcs gs://trinity-ml-artifacts/models
```

#### Option D: Azure Blob Storage
```bash
dvc remote add -d azure azure://trinity-ml-artifacts/models
```

### 4. Track Models with DVC

Instead of committing `.pkl` files, track them with DVC:

```bash
# Track trained model
dvc add models/layout_risk_predictor.pkl

# This creates models/layout_risk_predictor.pkl.dvc
# Git will only track the .dvc file (a few KB)
```

### 5. Track Training Data

```bash
# Track datasets
dvc add data/training_dataset.csv

# Creates data/training_dataset.csv.dvc
```

### 6. Push to Remote Storage

```bash
# Push models and data to remote storage
dvc push
```

### 7. Commit DVC Metadata

```bash
# Commit .dvc files to Git
git add models/*.pkl.dvc data/*.csv.dvc .dvc/config
git commit -m "Add DVC tracking for models and data"
git push
```

### 8. Pull Models on Another Machine

```bash
# Clone repository
git clone <repo-url>
cd trinity

# Pull models and data from DVC remote
dvc pull
```

## MLflow Setup

### 1. Install MLflow

```bash
pip install mlflow
```

### 2. Start MLflow Tracking Server

```bash
# Local development
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts --host 0.0.0.0 --port 5000
```

### 3. Update Training Scripts

Integrate MLflow tracking in `src/trinity/components/trainer.py`:

```python
import mlflow
import mlflow.sklearn

# Start MLflow run
with mlflow.start_run():
    # Log parameters
    mlflow.log_param("n_estimators", 100)
    mlflow.log_param("max_depth", 10)
    
    # Train model
    model.fit(X_train, y_train)
    
    # Log metrics
    accuracy = model.score(X_test, y_test)
    mlflow.log_metric("accuracy", accuracy)
    
    # Log model
    mlflow.sklearn.log_model(model, "layout_risk_predictor")
```

### 4. View Experiments

```bash
# Open MLflow UI
mlflow ui --port 5000
```

Navigate to `http://localhost:5000` to view experiments, compare runs, and manage models.

## Migration from Git-Committed Models

### Remove Existing Models from Git

```bash
# Remove models from Git tracking (keep local files)
git rm --cached models/*.pkl
git rm --cached data/training_dataset*.csv

# Add to DVC
dvc add models/*.pkl
dvc add data/*.csv

# Commit changes
git add models/*.dvc data/*.dvc .gitignore
git commit -m "Migrate to DVC for model versioning"
```

## Workflow

### Training a New Model

```bash
# 1. Train model (generates .pkl file locally)
trinity train

# 2. Track with DVC
dvc add models/layout_risk_predictor_$(date +%Y%m%d).pkl

# 3. Push to remote storage
dvc push

# 4. Commit metadata to Git
git add models/*.dvc
git commit -m "Train model v1.2.0"
git push
```

### Using a Specific Model Version

```bash
# 1. Check out Git commit with desired model version
git checkout <commit-hash>

# 2. Pull corresponding model
dvc pull
```

## Best Practices

1. **Never commit `.pkl`, `.csv`, `.h5` to Git** - Use DVC
2. **Tag model versions** - Use semantic versioning (`v1.0.0`)
3. **Track experiments** - Use MLflow for every training run
4. **Document models** - Keep metadata JSON files committed
5. **Automate pipelines** - Use `dvc repro` for reproducible training

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Model Training

on:
  workflow_dispatch:

jobs:
  train:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup DVC
        run: |
          pip install dvc dvc-s3
          dvc remote modify s3remote access_key_id ${{ secrets.AWS_ACCESS_KEY }}
          dvc remote modify s3remote secret_access_key ${{ secrets.AWS_SECRET_KEY }}
      
      - name: Pull data
        run: dvc pull data/training_dataset.csv.dvc
      
      - name: Train model
        run: python -m trinity.cli train
      
      - name: Push model
        run: |
          dvc add models/layout_risk_predictor.pkl
          dvc push
          
      - name: Commit metadata
        run: |
          git add models/*.dvc
          git commit -m "Update model $(date +%Y-%m-%d)"
          git push
```

## Troubleshooting

### Large Files Already Committed

If models were already committed to Git:

```bash
# Use BFG Repo Cleaner
java -jar bfg.jar --delete-files '*.pkl' --delete-files '*.csv'
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### DVC Remote Connection Issues

```bash
# Test remote connection
dvc remote list
dvc push --verbose

# Reconfigure credentials
dvc remote modify <remote-name> access_key_id <key>
```

## Resources

- [DVC Documentation](https://dvc.org/doc)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Model Versioning Best Practices](https://dvc.org/doc/use-cases/versioning-data-and-model-files)
