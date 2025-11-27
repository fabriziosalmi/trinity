# Trinity - Migration Guide to v0.6.0

## Overview

This guide helps you migrate from Trinity v0.5.0 to v0.6.0, which includes significant architectural improvements for production readiness.

## What's Changed

### Major Changes
1. **Immutable Configuration** - `TrinityConfig` → `ImmutableTrinityConfig` with dependency injection
2. **Custom Exceptions** - Specific exceptions instead of generic `Exception`
3. **Externalized Prompts** - LLM prompts moved to `config/prompts.yaml`
4. **MLOps Support** - Models tracked with DVC instead of Git
5. **Circuit Breakers** - Resilience for external service calls
6. **Idempotency** - Safe retries without duplicates
7. **Secrets Management** - System keyring integration

### Backward Compatibility
✅ Old code continues to work (deprecated)  
⚠️  Gradual migration recommended  
📅 Old patterns will be removed in v1.0.0

## Step-by-Step Migration

### Step 1: Update Dependencies

```bash
# Update requirements
pip install -r requirements.txt

# New dependencies:
# - PyYAML (prompts)
# - keyring (secrets)
# - dvc (models)
# - mlflow (experiments)
# - hypothesis (testing)
```

### Step 2: Migrate Configuration

#### Before (v0.5.0)
```python
from trinity.config import TrinityConfig

# Global mutable config
config = TrinityConfig()
engine = TrinityEngine()  # Uses global config
```

#### After (v0.6.0)
```python
from trinity.config_v2 import create_config

# Immutable config with explicit injection
config = create_config(
    max_retries=5,
    llm_timeout=120
)
engine = TrinityEngine(config=config)
```

### Step 3: Update Exception Handling

#### Before (v0.5.0)
```python
try:
    content = engine.generate_content(theme, raw_content)
except Exception as e:
    logger.error(f"Failed: {e}")
    return None
```

#### After (v0.6.0)
```python
from trinity.exceptions import (
    LLMConnectionError,
    LLMTimeoutError,
    ContentGenerationError
)

try:
    content = engine.generate_content(theme, raw_content)
except LLMConnectionError as e:
    # Handle connection failures
    logger.error(f"LLM unreachable: {e.details}")
    return use_fallback_content()
except LLMTimeoutError as e:
    # Handle timeouts specifically
    logger.error(f"LLM timeout: {e.details}")
    return cached_content
except ContentGenerationError as e:
    # Handle other content errors
    logger.error(f"Generation failed: {e.message}")
    raise
```

### Step 4: Add Circuit Breakers

#### New Pattern (v0.6.0)
```python
from trinity.utils.circuit_breaker import CircuitBreaker
from trinity.exceptions import LLMConnectionError, CircuitOpenError

# Create circuit breaker for LLM
llm_breaker = CircuitBreaker(
    name="llm-api",
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=LLMConnectionError
)

# Wrap LLM calls
try:
    content = llm_breaker.call(
        lambda: engine.generate_content(theme, raw_content)
    )
except CircuitOpenError:
    # Circuit is open, use fallback
    logger.warning("LLM circuit open, using cache")
    content = get_cached_content()
```

### Step 5: Implement Idempotency

#### New Pattern (v0.6.0)
```python
from trinity.utils.idempotency import idempotent, get_global_manager

manager = get_global_manager()

@idempotent(
    manager,
    key_params=['theme', 'raw_content'],
    ttl=3600  # 1 hour cache
)
def generate_content(theme: str, raw_content: str):
    """This function is now idempotent - safe to retry."""
    return engine.content_engine.generate_content(
        raw_content=raw_content,
        theme=theme
    )

# First call executes
result1 = generate_content("brutalist", content)

# Second call returns cached (no LLM call, no cost)
result2 = generate_content("brutalist", content)
```

### Step 6: Setup Secrets Management

#### Before (v0.5.0)
```python
import os
api_key = os.getenv("OPENAI_API_KEY")
```

#### After (v0.6.0)
```python
from trinity.utils.secrets import secrets_manager

# Store API key in system keyring (one-time)
secrets_manager.set_secret("openai_api_key", "sk-...")

# Retrieve securely
api_key = secrets_manager.get_secret("openai_api_key", required=True)

# Or let config handle it
config = create_config()  # Automatically loads from keyring
```

### Step 7: Externalize Prompts

#### Before (v0.5.0)
Prompts hardcoded in `brain.py`:
```python
vibes = {
    "enterprise": {
        "role": "CTO at Fortune 500",
        "tone": "Professional, reliable",
        # ...
    }
}
```

#### After (v0.6.0)
Prompts in `config/prompts.yaml`:
```yaml
content_generation:
  vibes:
    enterprise:
      role: "Chief Technology Officer at a Fortune 500 company"
      tone: "Professional, reliable, scalable"
      instructions: "..."
```

Load in code:
```python
import yaml

with open(config.prompts_config_path) as f:
    prompts = yaml.safe_load(f)

vibe = prompts['content_generation']['vibes']['enterprise']
```

### Step 8: Setup MLOps (Models & Data)

#### Before (v0.5.0)
```bash
# Models committed to Git
git add models/layout_risk_predictor.pkl
git commit -m "Update model"
```

#### After (v0.6.0)
```bash
# Install DVC
pip install dvc dvc-s3

# Initialize DVC
dvc init

# Configure remote storage
dvc remote add -d myremote s3://my-bucket/trinity-models

# Track model with DVC
dvc add models/layout_risk_predictor.pkl

# Push to remote
dvc push

# Commit only metadata to Git
git add models/layout_risk_predictor.pkl.dvc .dvc/config
git commit -m "Update model metadata"
```

See `docs/MLOPS_SETUP.md` for complete guide.

## Migration Checklist

### Required Changes
- [ ] Update `requirements.txt` and reinstall dependencies
- [ ] Replace `from trinity.config import TrinityConfig` with `from trinity.config_v2 import create_config`
- [ ] Update exception handling to use custom exceptions
- [ ] Move API keys to secrets manager

### Recommended Changes
- [ ] Add circuit breakers to LLM calls
- [ ] Implement idempotency for expensive operations
- [ ] Setup DVC for model versioning
- [ ] Externalize custom prompts to `prompts.yaml`

### Optional Improvements
- [ ] Add property-based tests
- [ ] Increase test coverage to 80%+
- [ ] Setup MLflow for experiment tracking
- [ ] Implement monitoring dashboard

## Component-Specific Migrations

### ContentEngine / Brain

**Before:**
```python
brain = ContentEngine(
    base_url=os.getenv("LM_STUDIO_URL"),
    api_key=os.getenv("API_KEY")
)
```

**After:**
```python
from trinity.utils.secrets import secrets_manager

brain = ContentEngine(
    base_url=config.lm_studio_url,
    api_key=secrets_manager.get_secret("llm_api_key")
)
```

### TrinityEngine

**Before:**
```python
engine = TrinityEngine()  # Uses global config
result = engine.build(theme="brutalist", content=raw_content)
```

**After:**
```python
config = create_config(max_retries=5)
engine = TrinityEngine(config=config)
result = engine.build(theme="brutalist", content=raw_content)
```

### Guardian

**Before:**
```python
guardian = TrinityGuardian(enable_vision_ai=True)
```

**After:**
```python
guardian = TrinityGuardian(
    viewport_width=config.guardian_viewport_width,
    viewport_height=config.guardian_viewport_height,
    enable_vision_ai=config.guardian_vision_ai
)
```

## Testing Your Migration

### 1. Run Existing Tests
```bash
pytest tests/ -v
```

### 2. Test New Features
```bash
# Test circuit breaker
pytest tests/test_circuit_breaker.py -v

# Test property-based tests
pytest tests/test_properties.py -v

# Test with coverage
pytest --cov=src/trinity --cov-report=html
```

### 3. Verify Configuration
```python
from trinity.config_v2 import create_config

config = create_config()
print(config.model_dump())  # Verify all settings
```

### 4. Check Secrets
```python
from trinity.utils.secrets import secrets_manager

info = secrets_manager.get_backend_info()
print(info)  # Verify keyring is working
```

## Breaking Changes

### Removed (v0.6.0)
None - full backward compatibility maintained

### Deprecated (v0.6.0)
- `trinity.config.TrinityConfig` - Use `trinity.config_v2.ImmutableTrinityConfig`
- `trinity.config.load_config()` - Use `trinity.config_v2.create_config()`
- Generic `Exception` handling - Use specific exceptions from `trinity.exceptions`

### Will be Removed (v1.0.0)
- Old `TrinityConfig` class
- Duplicate modules in `src/` root
- Environment-only secrets management

## Rollback Plan

If you encounter issues:

### Quick Rollback
```bash
# Revert to v0.5.0
git checkout v0.5.0
pip install -r requirements.txt
```

### Partial Rollback
Keep using old patterns:
```python
# Continue using old config (deprecated but functional)
from trinity.config import TrinityConfig
config = TrinityConfig()
```

## Getting Help

- **Documentation:** See `docs/REFACTORING_GUIDE.md`
- **Examples:** Check `examples/refactored_usage.py`
- **Issues:** Open GitHub issue with `migration` label
- **Questions:** Ask in Discussions

## Timeline

- **v0.6.0 (Current):** New features available, old patterns deprecated
- **v0.7.0 (Q1 2025):** Old patterns warn on usage
- **v0.8.0 (Q2 2025):** Old patterns raise errors
- **v1.0.0 (Q3 2025):** Old patterns removed

## Success Metrics

After migration, you should see:

✅ **Performance**
- Reduced LLM API calls (idempotency)
- Faster failure recovery (circuit breakers)

✅ **Reliability**
- Fewer cascading failures
- Better error messages
- Safer retries

✅ **Security**
- API keys in system keyring
- No secrets in code/config

✅ **Maintainability**
- Externalized prompts
- Immutable configuration
- Higher test coverage

## Example: Full Migration

See `examples/refactored_usage.py` for a complete working example demonstrating all new patterns.

---

**Questions?** Check the documentation or open an issue!
