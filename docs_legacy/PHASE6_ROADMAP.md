# Trinity - Phase 6 Roadmap (v0.6.x → v0.8.0)

> **Status:** Planning  
> **Current Version:** v0.6.0  
> **Target Version:** v0.8.0  
> **Timeline:** Q1-Q2 2026

## Overview

Phase 6 focuses on **performance, scalability, and developer experience**. Building on the solid architectural foundation from v0.6.0 (immutable config, circuit breakers, idempotency), we now optimize for scale and maintainability.

---

## 🎯 Goals

1. **Improve Performance** - Handle high throughput with async operations
2. **Reduce Costs** - Cache LLM responses, avoid duplicate work
3. **Improve DX** - Simplify workflows, better tooling
4. **Enhance Testing** - Deterministic, fast CI/CD
5. **Optimize Dependencies** - Make heavy deps optional

---

## 📋 Tasks

### 1. PERFORMANCE: Async/Await for ContentEngine ⚡

**Priority:** HIGH  
**Impact:** Enables horizontal scaling  
**Estimated Effort:** 3-5 days

**Problem:**
```python
# Current: Blocking synchronous calls
response = llm_client.generate(prompt)  # Blocks entire thread
```

At scale (100+ concurrent requests), synchronous calls will:
- Block the event loop
- Limit throughput to ~5-10 req/sec
- Cause cascading timeouts

**Solution:**
```python
# Target: Async/await pattern
async def generate_content(self, theme: str, content: str) -> str:
    async with self.llm_client as client:
        response = await client.generate(prompt)
    return response
```

**Implementation:**
- [ ] Convert `ContentEngine` to async class
- [ ] Use `httpx.AsyncClient` for LLM calls
- [ ] Add `asyncio` support to circuit breaker
- [ ] Update idempotency manager for async context
- [ ] Add async tests with `pytest-asyncio`

**Files to Modify:**
- `src/trinity/components/brain.py` - Make async
- `src/content_engine.py` - Make async
- `src/llm_client.py` - Add async client
- `src/trinity/utils/circuit_breaker.py` - Async support
- `tests/test_async_performance.py` - New benchmarks

**Success Metrics:**
- ✅ Handle 50+ concurrent requests
- ✅ Throughput > 30 req/sec (6x improvement)
- ✅ All tests pass in async mode

**Migration Path:**
```python
# Compatibility layer for v0.7.0
class ContentEngine:
    # Sync version (deprecated)
    def generate_content(self, theme, content):
        warnings.warn("Use async version", DeprecationWarning)
        return asyncio.run(self.generate_content_async(theme, content))
    
    # Async version (recommended)
    async def generate_content_async(self, theme, content):
        # New implementation
```

---

### 2. RESILIENCE: LLM Response Caching 💾

**Priority:** HIGH  
**Impact:** Reduces costs by 40-60%  
**Estimated Effort:** 3-4 days

**Problem:**
Same prompts generate same responses, but we pay every time:
```python
# Same content + theme = Same LLM output = Wasted $$
generate("brutalist", "About Me")  # $0.002
generate("brutalist", "About Me")  # $0.002 again (duplicate!)
```

**Solution:**
Multi-tier caching with TTL:

```python
# L1: In-memory (fast, ephemeral)
# L2: Redis (distributed, persistent)
# L3: Filesystem (backup)

cache_key = hash(theme, content, model)
if cached := cache.get(cache_key):
    return cached

response = await llm_client.generate(prompt)
cache.set(cache_key, response, ttl=3600)
```

**Implementation:**
- [ ] Create `LLMCache` class with multi-tier support
- [ ] Add Redis client (optional dependency)
- [ ] Filesystem cache fallback
- [ ] Cache invalidation strategies
- [ ] Cache hit/miss metrics
- [ ] Integration with existing idempotency manager

**Files to Create/Modify:**
- `src/trinity/utils/llm_cache.py` - New cache layer
- `src/trinity/components/brain.py` - Integrate cache
- `config/cache_config.yaml` - Cache settings
- `requirements.txt` - Add `redis>=5.0.0` (optional)

**Configuration:**
```yaml
# config/cache_config.yaml
cache:
  enabled: true
  backend: redis  # redis, filesystem, memory
  ttl: 3600  # 1 hour default
  max_size: 1000  # Max cached items
  redis:
    host: localhost
    port: 6379
    db: 0
  filesystem:
    path: .cache/llm_responses
```

**Success Metrics:**
- ✅ 60% cache hit rate in production
- ✅ 40% cost reduction
- ✅ <10ms cache lookup time

---

### 3. ARCH: Move Vibe Engine to YAML 📄

**Priority:** MEDIUM  
**Impact:** Easier prompt engineering without code changes  
**Estimated Effort:** 1-2 days

**Problem:**
```python
# src/trinity/components/brain.py (lines 45-180)
VIBES = {
    "enterprise": "Professional corporate...",
    "brutalist": "Raw, bold, technical...",
    "editorial": "Magazine-inspired..."
}
# ☝️ Hardcoded in Python = Need to redeploy to change prompts
```

**Solution:**
Already partially done in v0.6.0 with `config/prompts.yaml`, but needs completion:

```yaml
# config/prompts.yaml (expand existing)
content_generation:
  vibes:
    enterprise:
      system_prompt: |
        You are a professional corporate content writer.
        Style: Clean, corporate, trustworthy.
      temperature: 0.3
      max_tokens: 2000
    
    brutalist:
      system_prompt: |
        You are a bold, technical content writer.
        Style: Raw, minimal, direct.
      temperature: 0.5
      max_tokens: 1500
```

**Implementation:**
- [x] `config/prompts.yaml` already exists (v0.6.0)
- [ ] Remove hardcoded `VIBES` dict from `brain.py`
- [ ] Load prompts from YAML at runtime
- [ ] Add prompt hot-reloading (optional)
- [ ] Validate prompt schema with Pydantic

**Files to Modify:**
- `src/trinity/components/brain.py` - Remove VIBES dict, load from YAML
- `config/prompts.yaml` - Expand with all vibe definitions
- `src/trinity/config_v2.py` - Add prompt loading

**Success Metrics:**
- ✅ Zero hardcoded prompts in Python code
- ✅ Prompt changes don't require code deployment
- ✅ Schema validation prevents broken prompts

---

### 4. TESTING: Mock LLM in CI/CD 🧪

**Priority:** MEDIUM  
**Impact:** Deterministic tests, faster CI  
**Estimated Effort:** 2-3 days

**Problem:**
```python
# tests/test_chaos.py
def test_chaos_mode():
    result = engine.generate(theme="chaos")  # Calls real LLM!
    assert "AAAAAAA" in result  # ❌ Non-deterministic
```

Current issues:
- Tests depend on LLM availability
- Non-deterministic outputs
- Slow (3-5 sec per test)
- Costs money in CI

**Solution:**
Mock LLM responses with fixtures:

```python
# tests/fixtures/llm_responses.yaml
chaos_mode:
  prompt_hash: "abc123"
  response: |
    AAAAAAAAAAAAAAAA This is intentionally broken CSS
    with overflow text and chaos patterns.
  metadata:
    model: qwen2.5-coder-3b
    tokens: 150

# tests/test_chaos.py
@pytest.fixture
def mock_llm(mocker):
    responses = load_yaml("fixtures/llm_responses.yaml")
    mocker.patch("trinity.components.brain.ContentEngine.generate",
                 return_value=responses["chaos_mode"]["response"])

def test_chaos_mode(mock_llm):
    result = engine.generate(theme="chaos")
    assert "AAAAAAA" in result  # ✅ Deterministic
```

**Implementation:**
- [ ] Create `tests/fixtures/llm_responses.yaml`
- [ ] Add `pytest` fixtures for mocking
- [ ] Mock all LLM calls in unit tests
- [ ] Keep 1-2 integration tests with real LLM (manual)
- [ ] Add environment var to toggle mocking

**Files to Create/Modify:**
- `tests/fixtures/llm_responses.yaml` - Canned responses
- `tests/conftest.py` - Mock fixtures
- `tests/test_content_engine.py` - Use mocks
- `tests/test_chaos.py` - Use mocks
- `.github/workflows/ci.yml` - Set `MOCK_LLM=true`

**Success Metrics:**
- ✅ All CI tests run in <30 seconds
- ✅ 100% test determinism
- ✅ Zero LLM API calls in CI

---

### 5. DX: Add Makefile 🛠️

**Priority:** LOW  
**Impact:** Developer experience improvement  
**Estimated Effort:** 1 day

**Problem:**
```bash
# Current: Verbose docker-compose commands
docker-compose -f docker-compose.yml up --build
docker-compose -f docker-compose.yml exec trinity python main.py
docker-compose down -v
```

**Solution:**
Simple Makefile:

```makefile
.PHONY: help build up down test lint clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build:  ## Build Docker images
	docker-compose build

up:  ## Start services
	docker-compose up -d

down:  ## Stop services
	docker-compose down

test:  ## Run tests
	pytest --cov=src/trinity --cov-report=html

lint:  ## Run linters
	ruff check src/
	black --check src/
	mypy src/

clean:  ## Clean caches and temp files
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov
```

**Implementation:**
- [ ] Create `Makefile` in project root
- [ ] Add common tasks (build, test, lint, deploy)
- [ ] Document in README
- [ ] Add to getting started guide

**Success Metrics:**
- ✅ One command to start: `make up`
- ✅ One command to test: `make test`
- ✅ 50% reduction in command length

---

### 6. LOGGING: Structured Logging for Mining 📊

**Priority:** MEDIUM  
**Impact:** Better observability  
**Estimated Effort:** 2 days

**Problem:**
```python
# Current: print statements
print(f"Mining {file}...")
print("Found 5 repositories")
# ❌ Not structured, hard to parse, no log levels
```

**Solution:**
Structured logging with context:

```python
# Use existing logger with structured fields
logger.info("mining_started", extra={
    "file": file,
    "file_size": os.path.getsize(file),
    "timestamp": datetime.now().isoformat()
})

logger.info("repositories_found", extra={
    "count": 5,
    "languages": ["Python", "JavaScript"],
    "avg_stars": 150
})
```

**Implementation:**
- [ ] Replace all `print()` in mining pipeline with `logger`
- [ ] Add structured context to log calls
- [ ] Configure JSON log output for production
- [ ] Add log aggregation guide (ELK, Datadog)

**Files to Modify:**
- `src/trinity/components/dataminer.py` - Replace prints
- `src/trinity/utils/logger.py` - Add JSON formatter
- `config/logging.yaml` - Structured config

**Success Metrics:**
- ✅ Zero print statements in mining code
- ✅ All logs parseable as JSON
- ✅ Log aggregation ready

---

### 7. DEPS: Make Playwright Optional 🎭

**Priority:** MEDIUM  
**Impact:** Faster installs, smaller Docker images  
**Estimated Effort:** 1-2 days

**Problem:**
```txt
# requirements.txt
playwright==1.55.0  # 500MB+ download, always installed
# ☝️ Only needed for Guardian visual QA, but mandatory
```

**Solution:**
Optional dependency groups:

```toml
# pyproject.toml
[project]
dependencies = [
    "jinja2==3.1.4",
    "pydantic>=2.10.0",
    # ... core deps only
]

[project.optional-dependencies]
guardian = [
    "playwright==1.55.0",
    "pillow>=10.0.0"
]

all = [
    "trinity[guardian]",
]
```

```bash
# Install without Guardian
pip install trinity-core

# Install with Guardian
pip install trinity-core[guardian]

# Install everything
pip install trinity-core[all]
```

**Implementation:**
- [ ] Move to `pyproject.toml` (modern packaging)
- [ ] Define optional dependency groups
- [ ] Make Guardian imports conditional
- [ ] Update Docker images (separate for Guardian)
- [ ] Update documentation

**Files to Create/Modify:**
- `pyproject.toml` - Add optional deps (expand existing)
- `src/trinity/components/guardian.py` - Conditional import
- `Dockerfile` - Base image without playwright
- `Dockerfile.guardian` - Extended with playwright
- `docs/INSTALLATION.md` - Document options

**Success Metrics:**
- ✅ Base install < 100MB (was 600MB)
- ✅ Install time < 30s (was 2min)
- ✅ Guardian still works when opted-in

---

### 8. DOCS: Simplify README 📝

**Priority:** LOW  
**Impact:** Better first impressions  
**Estimated Effort:** 1 day

**Problem:**
Current README says:
> "Neural-Generative 5-layer system"
> "LSTM neural networks that learn CSS fixing strategies"

This scares away pragmatic engineers who just want:
- Fast static site generation
- AI-powered content
- Broken layout detection

**Solution:**
Lead with value, not architecture:

```markdown
# Trinity Core

> **AI-powered static site generator that fixes broken layouts automatically**

**What it does:**
1. Generate content with LLMs (GPT, Claude, local models)
2. Apply responsive themes (enterprise, brutalist, editorial)
3. Detect and fix layout issues (overflow, broken grids)
4. Output validated HTML

**Why it's different:**
- 🔧 Self-healing: Automatically fixes CSS issues
- 🎨 Theme-aware: Built-in design systems
- ⚡ Fast: Caches responses, async operations
- 🔒 Reliable: Circuit breakers, idempotency

## Quick Start

```bash
pip install trinity-core
trinity build --content data/portfolio.txt --theme brutalist
```

<details>
<summary>How it works (for the curious)</summary>

Trinity uses a multi-layer architecture:
- **Brain**: LLM content generation
- **Skeleton**: Theme application
- **Healer**: CSS fixing (rule-based + ML)
- **Guardian**: Visual QA (optional)
- **Predictor**: Pre-emptive issue detection
</details>
```

**Changes:**
- [ ] Rewrite README hero section
- [ ] Lead with practical use cases
- [ ] Move architecture to separate doc
- [ ] Add "Why Trinity?" comparison table
- [ ] More code examples, fewer diagrams

**Success Metrics:**
- ✅ <5 min to understand value proposition
- ✅ Clear getting started path
- ✅ Architecture details opt-in

---

### 9. CODE: Refactor God Object in engine.py ⚙️

**Priority:** HIGH  
**Impact:** Better maintainability  
**Estimated Effort:** 4-5 days

**Problem:**
`src/trinity/engine.py` is becoming a God Object:
- 500+ lines
- Handles content generation, healing, validation, building
- Tight coupling between components
- Hard to test in isolation

**Solution:**
Extract responsibilities into focused classes:

```python
# Before: God Object
class TrinityEngine:
    def generate_content(self): ...
    def apply_theme(self): ...
    def heal_css(self): ...
    def validate(self): ...
    def build(self): ...
    def deploy(self): ...
    # 500+ lines of mixed concerns

# After: Single Responsibility
class TrinityPipeline:
    def __init__(self, config):
        self.content_gen = ContentGenerator(config)
        self.theme_engine = ThemeEngine(config)
        self.healer = CSSHealer(config)
        self.validator = LayoutValidator(config)
        self.builder = StaticSiteBuilder(config)
    
    async def run(self, input_data):
        content = await self.content_gen.generate(input_data)
        themed = self.theme_engine.apply(content)
        healed = await self.healer.fix(themed)
        validated = self.validator.check(healed)
        return self.builder.build(validated)
```

**Implementation:**
- [ ] Extract `ContentGenerator` from engine
- [ ] Extract `ThemeEngine` from engine
- [ ] Extract `CSSHealer` from engine (already partially done)
- [ ] Create `TrinityPipeline` orchestrator
- [ ] Update all imports and tests
- [ ] Add integration tests for pipeline

**Files to Create/Modify:**
- `src/trinity/pipeline.py` - New orchestrator
- `src/trinity/components/content_generator.py` - Extracted
- `src/trinity/components/theme_engine.py` - Extracted
- `src/trinity/engine.py` - Slim down to ~100 lines
- `tests/test_pipeline.py` - Integration tests

**Success Metrics:**
- ✅ Each class < 200 lines
- ✅ Single Responsibility Principle
- ✅ Unit tests for each component

---

## 📅 Release Plan

### v0.7.0 - Performance & Caching (Weeks 1-3)
**Focus:** Scale and cost reduction

- ✅ Task 1: Async/await for ContentEngine
- ✅ Task 2: LLM response caching
- ✅ Task 6: Structured logging
- 🎯 **Target:** 6x throughput, 40% cost reduction

### v0.7.5 - DX & Testing (Weeks 4-5)
**Focus:** Developer experience

- ✅ Task 4: Mock LLM in CI/CD
- ✅ Task 5: Makefile
- ✅ Task 7: Optional Playwright
- 🎯 **Target:** <30s CI, better install UX

### v0.8.0 - Architecture & Polish (Weeks 6-8)
**Focus:** Maintainability and docs

- ✅ Task 3: Vibe engine to YAML (finish migration)
- ✅ Task 8: Simplify README
- ✅ Task 9: Refactor engine.py God Object
- 🎯 **Target:** Maintainable, scalable codebase

---

## 🧪 Testing Strategy

### Unit Tests
- All async functions tested with `pytest-asyncio`
- Mock LLM responses in all unit tests
- Property-based tests for cache layer

### Integration Tests
- End-to-end pipeline with mocked LLM
- Real LLM tests (manual, not in CI)
- Performance benchmarks

### Load Tests
- 100 concurrent requests with async engine
- Cache hit rate validation
- Circuit breaker under load

---

## 📊 Success Metrics

### Performance
- ✅ Throughput: >30 req/sec (from 5 req/sec)
- ✅ Latency: p95 < 2s (from 5s)
- ✅ Cache hit rate: >60%

### Cost
- ✅ LLM costs: -40% (via caching)
- ✅ Infrastructure: -30% (async = fewer containers)

### Developer Experience
- ✅ Install time: <30s (from 2min with optional deps)
- ✅ CI time: <30s (from 5min)
- ✅ Command simplicity: 3 words average (from 8)

### Code Quality
- ✅ Test coverage: >80% (from 60%)
- ✅ Avg class size: <200 lines
- ✅ Cyclomatic complexity: <10

---

## 🚀 Migration Guide (v0.6.0 → v0.8.0)

### Breaking Changes

**1. Async API (v0.7.0)**
```python
# Old (v0.6.0)
engine = TrinityEngine(config)
result = engine.generate_content(theme, content)

# New (v0.7.0)
engine = TrinityEngine(config)
result = await engine.generate_content(theme, content)

# Compatibility layer available until v0.9.0
```

**2. Optional Dependencies (v0.7.5)**
```bash
# Old (v0.6.0)
pip install -r requirements.txt  # Installs everything

# New (v0.7.5)
pip install trinity-core              # Base install
pip install trinity-core[guardian]    # With visual QA
pip install trinity-core[all]         # Everything
```

**3. Engine API (v0.8.0)**
```python
# Old (v0.6.0)
from trinity.engine import TrinityEngine

# New (v0.8.0)
from trinity.pipeline import TrinityPipeline
# (TrinityEngine still available as alias)
```

### Non-Breaking Enhancements

- Caching is opt-in via config
- Structured logging backward compatible
- Prompts in YAML (fallback to code)
- Makefile is additive

---

## 📚 Documentation Updates

- [ ] Update README (simplified, value-first)
- [ ] Add ASYNC_GUIDE.md
- [ ] Add CACHING_GUIDE.md
- [ ] Update CONTRIBUTING.md (Makefile commands)
- [ ] Add ARCHITECTURE.md (move from README)
- [ ] Update API_REFERENCE.md

---

## 🎯 Phase 6 Summary

**What we're building:**
A scalable, cost-effective static site generator that's easy to use and maintain.

**Key improvements:**
1. **6x faster** with async operations
2. **40% cheaper** with intelligent caching
3. **Easier to use** with better DX and docs
4. **More maintainable** with cleaner architecture

**Timeline:** 8 weeks  
**Effort:** ~25-30 developer days  
**Risk:** Low (incremental changes, good test coverage)

---

## Next Steps

1. **Review this plan** with team
2. **Create GitHub milestones** for v0.7.0, v0.7.5, v0.8.0
3. **Break into issues** (one per task)
4. **Start with Task 1** (async/await) - highest impact
5. **Ship v0.7.0** in 3 weeks

**Questions? Feedback?** Open an issue or discussion.
