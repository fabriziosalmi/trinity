# Trinity - Architectural Refactoring Guide

## Overview

This document outlines the major architectural improvements implemented to address code quality, maintainability, and production readiness concerns.

## Summary of Changes

### 1. ✅ Strict Error Handling

**Problem:** Generic `except Exception` blocks throughout codebase made debugging difficult and masked real issues.

**Solution:** Implemented comprehensive custom exception hierarchy.

**Files Created:**
- `src/trinity/exceptions.py` - 15+ domain-specific exception types

**Benefits:**
- Specific exception types for different failure modes
- Better error messages with context
- Easier debugging and monitoring
- Type-safe error handling

**Migration Example:**
```python
# Before ❌
try:
    result = llm.generate()
except Exception as e:
    logger.error(f"Failed: {e}")

# After ✅
try:
    result = llm.generate()
except LLMConnectionError as e:
    # Handle connection failures specifically
    logger.error(f"LLM connection failed: {e.details}")
except LLMTimeoutError as e:
    # Handle timeouts differently
    logger.error(f"LLM timeout: {e.details}")
```

### 2. ✅ Immutable Configuration with Dependency Injection

**Problem:** Mutable global `TrinityConfig()` instances scattered across modules created unpredictable state.

**Solution:** Implemented immutable, frozen Pydantic configuration with explicit dependency injection.

**Files Created:**
- `src/trinity/config_v2.py` - Immutable configuration system

**Key Features:**
- Frozen Pydantic models (no mutation after creation)
- Factory pattern (`create_config()`)
- Validation at initialization
- Explicit dependency injection

**Migration Example:**
```python
# Before ❌
class MyComponent:
    def __init__(self):
        self.config = TrinityConfig()  # Global mutable instance

# After ✅
class MyComponent:
    def __init__(self, config: ImmutableTrinityConfig):
        self.config = config  # Injected, immutable

# Usage
config = create_config(max_retries=5)
component = MyComponent(config=config)
```

### 3. ✅ Externalized LLM Prompts

**Problem:** All LLM prompts and "vibe" definitions hardcoded in `brain.py` made them difficult to modify and version.

**Solution:** Extracted all prompts to YAML configuration file.

**Files Created:**
- `config/prompts.yaml` - All LLM prompt templates

**Benefits:**
- Prompts editable without code changes
- Version control for prompt engineering
- A/B testing different prompts
- Non-developers can modify content

**Structure:**
```yaml
content_generation:
  vibes:
    enterprise:
      role: "Chief Technology Officer"
      tone: "Professional, reliable"
      instructions: "..."
    brutalist:
      role: "Elite DevOps Engineer"
      tone: "Raw, direct, technical"
      instructions: "..."
```

### 4. ✅ MLOps Infrastructure

**Problem:** Trained models (`.pkl`) and datasets (`.csv`) committed to Git, bloating repository.

**Solution:** Implemented DVC (Data Version Control) and MLflow for artifact management.

**Files Modified:**
- `.gitignore` - Ignore models and data files
- `docs/MLOPS_SETUP.md` - Complete setup guide

**Workflow:**
```bash
# Train model
trinity train

# Track with DVC (not Git)
dvc add models/layout_risk_predictor.pkl
dvc push

# Commit only metadata
git add models/*.dvc
git commit -m "Update model v1.2.0"
```

**Benefits:**
- Lightweight Git repository
- Proper model versioning
- Experiment tracking
- Cloud storage for artifacts
- Reproducible pipelines

### 5. ✅ Circuit Breaker Pattern

**Problem:** External service failures (LLM API, Playwright) caused cascading failures without graceful degradation.

**Solution:** Implemented circuit breaker pattern for resilient external calls.

**Files Created:**
- `src/trinity/utils/circuit_breaker.py` - Circuit breaker implementation

**Features:**
- Three states: CLOSED, OPEN, HALF_OPEN
- Configurable failure threshold
- Automatic recovery testing
- Statistics and monitoring

**Usage:**
```python
from trinity.utils.circuit_breaker import CircuitBreaker
from trinity.exceptions import LLMConnectionError

# Create circuit breaker
llm_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=LLMConnectionError
)

# Use as decorator
@llm_breaker
def call_llm_api():
    return llm.generate_content()

# Or explicit call
try:
    result = llm_breaker.call(llm.generate_content)
except CircuitOpenError:
    # Use fallback
    result = cached_response
```

### 6. ✅ Idempotency Support

**Problem:** Retry operations could create duplicate content or waste resources.

**Solution:** Implemented idempotency key manager for safe retries.

**Files Created:**
- `src/trinity/utils/idempotency.py` - Idempotency manager

**Features:**
- Hash-based key generation
- In-memory + persistent storage
- Automatic expiration (TTL)
- Thread-safe operations

**Usage:**
```python
from trinity.utils.idempotency import idempotent, get_global_manager

manager = get_global_manager()

@idempotent(manager, key_params=['theme', 'content'], ttl=3600)
def generate_content(theme: str, content: str):
    return expensive_llm_call(theme, content)

# First call executes
result1 = generate_content("brutalist", "My portfolio")

# Second call returns cached result (idempotent)
result2 = generate_content("brutalist", "My portfolio")
```

### 7. ✅ Enhanced Secrets Management

**Problem:** API keys in environment variables only, no secure storage option.

**Solution:** Integrated system keyring with fallback to environment variables.

**Files Created:**
- `src/trinity/utils/secrets.py` - Secrets manager
- `docs/SECRETS_MANAGEMENT.md` - Usage guide

**Backends:**
1. **System Keyring** (macOS Keychain, Windows Credential Manager, Linux Secret Service)
2. **Environment Variables** (fallback)
3. **.env File** (development only)

**Usage:**
```python
from trinity.utils.secrets import secrets_manager

# Store API key in keyring
secrets_manager.set_secret("openai_api_key", "sk-...")

# Retrieve securely
api_key = secrets_manager.get_secret("openai_api_key", required=True)
```

### 8. 🔄 Module Boundary Cleanup (In Progress)

**Problem:** Duplicate code in `src/` root and `src/trinity/components/`:
- `src/builder.py` vs `src/trinity/components/builder.py`
- `src/guardian.py` vs `src/trinity/components/guardian.py`
- etc.

**Solution:** Consolidate all modules into `src/trinity/components/`, remove duplicates.

**Status:** Documentation created, implementation pending.

### 9. 📋 Test Coverage Improvements (Planned)

**Problem:** Limited test coverage, no property-based testing.

**Solution:** 
- Add `pytest-cov` for coverage metrics
- Add `hypothesis` for property-based testing
- Target 80%+ coverage

**Planned Files:**
- `tests/test_circuit_breaker.py`
- `tests/test_idempotency.py`
- `tests/test_secrets.py`
- `tests/property_tests.py` (hypothesis)

### 10. 📋 Versioning Documentation (Planned)

**Problem:** README shows features as "COMPLETED" but implementation status unclear.

**Solution:** Update README with proper semantic versioning and feature status.

## Migration Checklist

For existing Trinity projects:

- [ ] Update to `config_v2.py` with dependency injection
- [ ] Replace generic `except Exception` with specific exceptions
- [ ] Migrate prompts to `config/prompts.yaml`
- [ ] Setup DVC for model/data versioning
- [ ] Remove `.pkl` and `.csv` from Git history
- [ ] Add circuit breakers to LLM calls
- [ ] Implement idempotency for content generation
- [ ] Configure keyring for API keys
- [ ] Update `requirements.txt` with new dependencies
- [ ] Run tests and verify functionality

## Compatibility

### Backward Compatibility

The refactoring maintains backward compatibility where possible:

- Old `TrinityConfig` still works (deprecated)
- Existing code continues to function
- Gradual migration path provided

### Breaking Changes

Minimal breaking changes:

1. Circuit breaker may fail fast (by design)
2. Idempotency prevents duplicate work (feature)
3. Secrets manager requires keyring or env vars

## Performance Impact

**Positive:**
- Idempotency reduces redundant LLM calls
- Circuit breaker prevents wasted requests
- DVC reduces Git clone time

**Negligible:**
- Immutable config has no runtime overhead
- Exception hierarchy adds no overhead
- Secrets manager caches results

## Testing Strategy

1. **Unit Tests** - Each component tested in isolation
2. **Integration Tests** - Components work together
3. **Property-Based Tests** - Verify invariants with hypothesis
4. **Load Tests** - Circuit breaker under stress
5. **Security Tests** - Secrets manager security

## Monitoring & Observability

### Circuit Breaker Monitoring

```python
from trinity.utils.circuit_breaker import circuit_breaker_registry

# Get all circuit breaker statuses
status = circuit_breaker_registry.get_all_status()
print(status)
```

### Idempotency Monitoring

```python
from trinity.utils.idempotency import get_global_manager

manager = get_global_manager()
stats = manager.get_stats()
print(f"Cache hit rate: {stats['active_entries']}/{stats['total_entries']}")
```

### Secrets Audit

```python
from trinity.utils.secrets import secrets_manager

info = secrets_manager.get_backend_info()
print(f"Backend: {info['active_backend']}")
```

## Future Improvements

1. **Service Mesh** - Integrate with Istio/Linkerd for distributed circuit breakers
2. **Distributed Tracing** - OpenTelemetry integration
3. **Metrics** - Prometheus/Grafana dashboards
4. **Rate Limiting** - Token bucket for LLM calls
5. **Caching Layer** - Redis for distributed idempotency

## Resources

- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [DVC Documentation](https://dvc.org/doc)
- [MLflow Documentation](https://mlflow.org/docs/latest/)
- [Python Keyring](https://pypi.org/project/keyring/)

## Questions?

See individual documentation files:
- `docs/MLOPS_SETUP.md` - Model versioning
- `docs/SECRETS_MANAGEMENT.md` - API key security
- `docs/TESTING.md` - Test strategy (TBD)
