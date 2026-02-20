# Trinity

A static site generator that uses LLMs to produce content and applies CSS self-healing strategies to fix layout issues.

[![asciicast](https://asciinema.org/a/aPIGQHdxN2hewQgegQhGaiCBG.svg)](https://asciinema.org/a/aPIGQHdxN2hewQgegQhGaiCBG)

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/docker-ready-brightgreen.svg" alt="Docker"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://github.com/fabriziosalmi/trinity/releases"><img src="https://img.shields.io/badge/version-0.8.1-green.svg" alt="Version"></a>
</p>

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Build with static JSON content
trinity build --input data/input_content.json --theme brutalist --output portfolio.html

# Build with LLM-generated content (requires a running LLM endpoint)
trinity build --input data/raw_portfolio.txt --llm --theme enterprise

# Enable Guardian layout validation and self-healing
trinity build --input data/input_content.json --theme brutalist --guardian
```

Open the output HTML file in a browser. If `--guardian` is not specified, builds complete without visual validation.

<details>
<summary>Docker</summary>

```bash
git clone https://github.com/fabriziosalmi/trinity.git
cd trinity
docker-compose up -d
```
</details>

---

## Features

### Content Generation
- Reads structured JSON input or raw text files
- Optionally generates content via a local or cloud LLM (Ollama, LM Studio, OpenAI)
- Validates generated content with Pydantic schemas before rendering
- Filesystem-based LLM response caching (memory and filesystem tiers; Redis is optional)

### Themes
- 14 built-in themes defined in `config/themes.yaml`: `artistic_01`, `artistic_02`, `brutalist`, `chaotic_01`, `chaotic_02`, `editorial`, `enterprise`, `historical_01`, `historical_02`, `professional_01`, `professional_02`, `retro_arcade`, `tech_01`, `tech_02`
- All themes use Tailwind CSS classes rendered via Jinja2 templates
- New themes can be generated from a text description using the `trinity theme-gen` command (requires a running LLM)

### Self-Healing Layouts (optional, requires `--guardian`)
- Guardian uses Playwright to load the rendered page and detect DOM overflow
- When overflow is detected, the SmartHealer applies one of four progressive CSS strategies: `CSS_BREAK_WORD`, `FONT_SHRINK`, `CSS_TRUNCATE`, `CONTENT_CUT`
- An optional ML predictor (Random Forest, trained on local build data) can suggest which strategy to apply before Guardian runs; the model must be trained locally with `trinity train`
- An LSTM-based Neural Healer (`--neural`) is available as an alternative to the rule-based SmartHealer
- Guardian requires Playwright and its browser dependencies; it is disabled by default

### Reliability
- Circuit breaker on LLM requests (fails fast after repeated errors)
- Structured logging (JSON format when `TRINITY_ENV=Production`)
- Pydantic-based type-safe configuration

---

## Available Themes

```bash
# List available themes
trinity themes
```

Themes are defined in `config/themes.yaml`. The default set includes:

| Theme | Description |
|-------|-------------|
| enterprise | Corporate, clean design |
| brutalist | Bold, raw aesthetic |
| editorial | Magazine-style layout |
| artistic_01 | Creative gradient design |
| tech_01 | Modern tech aesthetic |
| retro_arcade | Retro gaming style |
| ... | (14 themes total) |

---

## Configuration

### Environment Variables

```bash
# LLM endpoint (LM Studio default)
export TRINITY_LM_STUDIO_URL=http://localhost:1234/v1

# OpenAI API key (if using OpenAI)
export TRINITY_OPENAI_API_KEY=your_key

# Enable JSON logging
export TRINITY_ENV=Production
```

### Settings

Key settings in `config/settings.yaml` or via `TRINITY_*` environment variables:

| Setting | Default | Description |
|---------|---------|-------------|
| `lm_studio_url` | `http://localhost:1234/v1` | LLM API endpoint |
| `guardian_enabled` | `false` | Enable Guardian layout validation |
| `predictive_enabled` | `true` | Enable ML-based strategy prediction |
| `max_retries` | `3` | Max self-healing attempts |
| `default_theme` | `enterprise` | Default theme name |

---

## CLI Reference

```bash
# Build a site page
trinity build --input <file> --theme <name> [--llm] [--guardian] [--neural]

# Run chaos test with intentionally broken content
trinity chaos --theme <name>

# List available themes
trinity themes

# Show current configuration
trinity config-info

# Collect ML training data via random builds
trinity mine-generate --count 100

# Train layout risk predictor from collected data
trinity train

# Generate a new theme from a style description (requires LLM)
trinity theme-gen "description" --name <name>
```

---

## Documentation

- [Architecture: Retry Logic and Heuristics](docs/1_Architecture/1.0_Retry_Logic_Heuristics.md)
- [Architecture: Async and MLOps](docs/1_Architecture/1.1_Async_MLOps.md)
- [Setup Guide](docs/2_Development/2.0_Setup.md)
- [Code Quality](docs/2_Development/2.1_Code_Quality.md)
- [Self-Healing Layouts](docs/3_Features/3.0_Self_Healing.md)
- [Centuria Theme Factory](docs/3_Features/3.1_Centuria_Factory.md)
- [LLM Response Caching](docs/4_LLM_Agents/4.0_LLM_Caching.md)
- [Docker Guide](DOCKER_README.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [Security Policy](SECURITY.md)

---

## Testing

```bash
# Run all tests
make test

# With coverage report
make test-cov

# E2E tests
pytest tests/test_e2e_complete.py -v

# Multiclass pipeline tests
pytest tests/test_multiclass_pipeline.py -v
```

---

## Docker

```bash
make docker-build
make docker-run
```

See [DOCKER_README.md](DOCKER_README.md) for details.

---

## Contributing

```bash
git clone https://github.com/fabriziosalmi/trinity.git
cd trinity
make setup
git checkout -b feature/your-feature
make test
make format
make lint
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- LLM integration: Ollama, OpenAI, LM Studio
- Templating: Jinja2, Tailwind CSS
- ML: scikit-learn, PyTorch
- Validation: Playwright, Pydantic, httpx

---

## Support

- [GitHub Issues](https://github.com/fabriziosalmi/trinity/issues)
- [GitHub Discussions](https://github.com/fabriziosalmi/trinity/discussions)
- [Security Policy](SECURITY.md)
