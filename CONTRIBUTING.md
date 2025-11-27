# Contributing to Trinity

Thank you for considering contributing to Trinity! This document provides guidelines for development setup, code standards, and contribution workflow.

## Development Setup

### Prerequisites

- **Python >= 3.10** (3.12 recommended)
- **Poetry >= 1.6** for dependency management
- **Node.js >= 18** (for documentation site only)
- **Docker Desktop >= 24.0** (optional, for containerized development)
- **LM Studio >= 0.2.0** with Qwen 2.5 Coder model (optional, for LLM features)

### Dependency Management

Trinity uses **two separate dependency systems**:

1. **Python (Poetry)** - Core application and ML models
   - `pyproject.toml` - Source of truth for Python dependencies
   - `requirements.txt` - Generated from Poetry for Docker/CI compatibility
   
2. **Node.js (npm)** - Documentation site only (VitePress)
   - `package.json` - Documentation tooling (build/preview docs_v2/)
   - **Not** used for the core Trinity application

**Why both?** The Python app is the product. Node.js is only for building/previewing the VitePress documentation site.

### Local Installation

```bash
# Clone repository
git clone https://github.com/fabriziosalmi/trinity.git
cd trinity

# Install Python dependencies with Poetry
poetry install

# Activate virtual environment
poetry shell

# Verify installation
trinity --version

# (Optional) Install npm deps only if working on docs_v2/
npm install  # Only needed for VitePress documentation
```

### Environment Configuration

Create `.env` file in project root:

```bash
# LLM Configuration (optional)
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=qwen2.5-coder-7b-instruct

# Logging
LOG_LEVEL=INFO

# Output paths (defaults shown)
OUTPUT_DIR=output
DATA_DIR=data
MODELS_DIR=models
```

## Code Quality Standards

This project enforces **Anti-Vibecoding Rules** - a strict engineering discipline documented in the codebase. Key principles:

### Rule Compliance

- **Rule #6:** Security-first design (never load untrusted pickle files)
- **Rule #7:** Explicit error handling (no silent failures)
- **Rule #8:** No magic numbers (all constants named and documented)
- **Rule #13:** Don't hack `sys.path` (use proper package structure)
- **Rule #18:** Use proper package imports
- **Rule #28:** Structured logging (JSON-compatible metadata)
- **Rule #30:** Testable design (small, pure functions)

### Code Style

```bash
# Format code with Black (line length 100)
poetry run black src/ scripts/ --line-length 100

# Sort imports
poetry run isort src/ scripts/

# Type checking (optional but recommended)
poetry run mypy src/
```

### Documentation Standards

- **Docstrings:** Google style for all public functions/classes
- **Type Hints:** Required for all function signatures
- **Comments:** Explain "why", not "what" (code should be self-documenting)
- **No TODO comments:** Move tasks to GitHub Issues instead

Example:

```python
def predict_layout_risk(
    content_len: int,
    theme: str,
    active_strategy: str
) -> float:
    """
    Predict probability of layout breakage before rendering.
    
    Uses trained Random Forest classifier to estimate failure risk
    based on content metrics and CSS configuration. Risk > 0.7
    triggers pre-emptive healing strategies.
    
    Args:
        content_len: Character count of input content
        theme: Tailwind theme name (e.g., "brutalist", "enterprise")
        active_strategy: Current healing strategy being applied
        
    Returns:
        Probability of layout failure (0.0-1.0)
        
    Raises:
        ModelNotFoundError: If no trained model exists in models/
        
    Example:
        >>> risk = predict_layout_risk(500, "brutalist", "NONE")
        >>> if risk > 0.7:
        ...     apply_preventive_healing()
    """
```

## Testing

### Run Tests

```bash
# Run full test suite (when implemented)
poetry run pytest

# Run specific test file
poetry run pytest tests/test_engine.py

# Run with coverage
poetry run pytest --cov=src --cov-report=html
```

### Manual Testing

```bash
# Test ML pipeline end-to-end
bash scripts/fast_training.sh

# Test theme generation
poetry run trinity theme-gen "Cyberpunk neon city" --name cyberpunk

# Test chaos mode (intentional failures)
poetry run trinity chaos --theme brutalist
```

## Contribution Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make Changes

- Follow code quality standards above
- Add tests for new features
- Update documentation if changing behavior

### 3. Commit Standards

Use [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat: Add ONNX export for ML models
fix: Resolve pickle security warning in trainer
docs: Update CLI reference for theme-gen command
refactor: Extract theme validation to separate module
test: Add unit tests for LayoutRiskPredictor
```

**Commit message format:**

```
<type>: <subject>

<body (optional)>

<footer (optional)>
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`

### 4. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Open PR on GitHub with:
- Clear description of changes
- Link to related issue (if applicable)
- Screenshots/logs for visual changes
- Checklist of completed items

### 5. Code Review

All PRs require:
- Passing CI checks (when implemented)
- Code review from maintainer
- No merge conflicts with `main`
- Updated documentation

## Project Structure

```
trinity/
├── src/trinity/              # Core package
│   ├── components/           # ML models, builders, healers
│   ├── cli.py               # CLI entry point
│   ├── config.py            # Configuration management
│   └── engine.py            # Main orchestration logic
├── scripts/                  # Automation scripts
│   ├── mass_theme_generator.py
│   ├── fast_training.sh
│   └── nightly_training.sh
├── data/                     # Training datasets
├── models/                   # Trained ML models (.pkl)
├── output/                   # Generated HTML files
├── config/                   # Theme definitions (JSON/YAML)
├── library/                  # Jinja2 templates
│   ├── atoms/
│   ├── molecules/
│   ├── organisms/
│   └── templates/
├── docs/                     # Architecture documentation
├── tests/                    # Unit and integration tests
└── main.py                   # Legacy entry point (use CLI instead)
```

## Release Process

Releases are managed by project maintainers:

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` (Keep a Changelog format)
3. Create git tag: `git tag -a v0.5.0 -m "Release v0.5.0: Feature description"`
4. Push tag: `git push origin v0.5.0`
5. GitHub Actions automatically builds and publishes (when configured)

## Support and Communication

- **Bug Reports:** [GitHub Issues](https://github.com/fabriziosalmi/trinity/issues)
- **Feature Requests:** [GitHub Discussions](https://github.com/fabriziosalmi/trinity/discussions)
- **Security Vulnerabilities:** See [SECURITY.md](SECURITY.md)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Bus Factor:** Currently 1 (primary maintainer). Deployment and release knowledge is documented in this file to reduce risk.
