# God Object Refactoring Plan

## Overview
Rename dramatic "God Complex" naming to descriptive functional names for engineering clarity.

## Renaming Map

| Old Name | New Name | Rationale |
|----------|----------|-----------|
| `ContentEngine` (brain.py) | `ContentGenerator` | Describes what it does: generates content via LLM |
| `SmartHealer` (healer.py) | `LayoutValidator` | Validates and fixes layout issues |
| `NeuralHealer` (neural_healer.py) | `MLLayoutOptimizer` | Uses ML to optimize layouts |
| `TrinityEngine` (engine.py) | `SiteBuilder` | Builds the complete site |
| `TrinityGuardian` (guardian.py) | `QualityChecker` | Checks quality/validates output |
| `TrinityMiner` (dataminer.py) | `DataExtractor` | Extracts data from sources |

## Files to Update

### 1. Core Components (src/trinity/components/)
- [ ] `brain.py` → `content_generator.py`
  - Class: `ContentEngine` → `ContentGenerator`
  - Exception: `ContentEngineError` → `ContentGeneratorError`
  
- [ ] `healer.py` → `layout_validator.py`
  - Class: `SmartHealer` → `LayoutValidator`
  
- [ ] `neural_healer.py` → `ml_layout_optimizer.py`
  - Class: `NeuralHealer` → `MLLayoutOptimizer`
  
- [ ] `guardian.py` → `quality_checker.py`
  - Class: `TrinityGuardian` → `QualityChecker`
  - Exception: `GuardianError` → `QualityCheckError`
  
- [ ] `dataminer.py` → `data_extractor.py`
  - Class: `TrinityMiner` → `DataExtractor`

### 2. Main Engine
- [ ] `engine.py`
  - Class: `TrinityEngine` → `SiteBuilder`
  - Update all imports

### 3. Public API
- [ ] `src/trinity/__init__.py` - Update exports
- [ ] `src/trinity/components/__init__.py` - Update exports
- [ ] `src/trinity/cli.py` - Update imports

### 4. Tests
- [ ] `tests/test_healer.py` → `tests/test_layout_validator.py`
- [ ] `tests/test_engine.py` - Update imports
- [ ] `tests/test_async_performance.py` - Update imports

### 5. Documentation
- [ ] All `docs/*.md` files
- [ ] All `docs_v2/**/*.md` files
- [ ] `README.md`
- [ ] `CHANGELOG.md`
- [ ] `examples/refactored_usage.py`

### 6. Configuration
- [ ] Exception classes in `src/trinity/exceptions.py`

## Migration Strategy

### Phase 1: Create Aliases (Backward Compatibility)
```python
# brain.py
class ContentGenerator:
    """Generates content via LLM."""
    pass

# Deprecated alias for backward compatibility
ContentEngine = ContentGenerator
```

### Phase 2: Update Internal Code
- Update all imports in src/
- Update all instantiations
- Update all type hints

### Phase 3: Update Public API
- Update __init__.py exports
- Update CLI
- Update examples

### Phase 4: Update Documentation
- Update all docs
- Add deprecation warnings to old names

### Phase 5: Remove Aliases (Breaking Change - v0.8.0)
- Remove deprecated aliases
- Update CHANGELOG with breaking changes

## Implementation Order

1. ✅ Create this migration plan
2. ⏳ Rename files and classes with aliases
3. ⏳ Update all imports
4. ⏳ Update tests
5. ⏳ Update documentation
6. ⏳ Add deprecation warnings
7. ⏳ (Future) Remove aliases in v0.8.0

## Notes

- Keep backward compatibility during transition
- Add deprecation warnings to guide users
- Document breaking changes in CHANGELOG
- Update type hints and docstrings
- Run full test suite after each phase
