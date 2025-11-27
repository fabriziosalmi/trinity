# Multiclass Trainer Modifications (v0.8.0)

## Changes Summary

### 1. Target Column
- **Old**: `is_valid` (binary: 0/1)
- **New**: `resolved_strategy_id` (multiclass: 0-4, 99)

### 2. New Features
Add to feature extraction:
- `css_density_spacing`
- `css_density_layout`
- `pathological_score`

### 3. Classification Metrics
- Switch from binary metrics to multiclass
- Use `classification_report` with multiclass support
- Calculate per-class precision/recall/f1

### 4. Feature Importance (XAI)
After training:
```python
# Extract feature importances
importances = model.feature_importances_
feature_importance_dict = dict(zip(feature_names, importances))

# Sort and take top 10
sorted_features = sorted(
    feature_importance_dict.items(), 
    key=lambda x: x[1], 
    reverse=True
)[:10]

# Save to metadata JSON
metadata["feature_importance_top10"] = [
    {"feature": name, "importance": float(importance)}
    for name, importance in sorted_features
]
```

### 5. Model Validation
- Update thresholds for multiclass
- Check weighted F1 score (not binary F1)
- Log per-class performance

## Implementation Notes

1. Keep `is_valid` for backward compatibility during migration
2. Primary target is now `resolved_strategy_id`
3. Feature importance enables XAI (explainability)
4. Top 10 features help understand model decisions
