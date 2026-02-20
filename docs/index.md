---
layout: home

hero:
  name: "Trinity"
  text: "Static Site Generator with LLM Content and Self-Healing Layouts"
  tagline: "Generate pages from structured data, apply themes, and auto-fix layout issues."
  actions:
    - theme: brand
      text: Setup Guide
      link: /2_Development/2.0_Setup
    - theme: alt
      text: Architecture
      link: /1_Architecture/1.0_Retry_Logic_Heuristics
    - theme: alt
      text: View on GitHub
      link: https://github.com/fabriziosalmi/trinity

features:
  - title: LLM Content Generation
    details: Read structured JSON input or generate content with local LLMs (Ollama, LM Studio) or cloud providers (OpenAI). Responses are cached to avoid redundant API calls.
  
  - title: 14 Built-in Themes
    details: Themes defined in config/themes.yaml using Tailwind CSS. Includes enterprise, brutalist, editorial, artistic, tech, retro, and more. New themes can be generated with the theme-gen command.
  
  - title: Self-Healing Layouts
    details: Guardian (Playwright) detects DOM overflow and the SmartHealer applies progressive CSS strategies. An optional Random Forest predictor can pre-select the strategy. Guardian is disabled by default.
  
  - title: Async LLM Client
    details: Async/await HTTP client for concurrent LLM requests. Multi-tier caching (memory, optional Redis, filesystem). Circuit breaker for fail-fast error handling.
  
  - title: ML Predictor (optional)
    details: Train a Random Forest classifier on local build data with trinity train. Use it to predict healing strategies before rendering. Requires collecting training data first.
  
  - title: Structured Logging
    details: JSON-formatted logs when TRINITY_ENV=Production. Correlation IDs for request tracing. Human-readable format in development mode.
---

## What Trinity Does

Trinity is a Python CLI tool that:

1. Takes structured JSON input (or raw text for LLM-generated content)
2. Renders HTML using Jinja2 templates and a selected Tailwind CSS theme
3. Optionally validates the rendered layout using Guardian (Playwright DOM inspection)
4. Applies progressive CSS fixes if overflow issues are detected
5. Writes the output HTML file

Guardian and the ML predictor are disabled by default; they require explicit flags and setup.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Build with static JSON content
trinity build --input data/input_content.json --theme brutalist

# Build with LLM content generation (requires running LLM endpoint)
trinity build --input data/raw_portfolio.txt --llm --theme enterprise

# Enable Guardian layout validation
trinity build --input data/input_content.json --guardian --theme brutalist
```

## Architecture

Trinity uses a layered pipeline:

```
Input → Brain (LLM) → Skeleton (Theme) → Healer (CSS Fixes) → Output
         ↓                                      ↑
      Caching                         Predictor (ML, optional)
         ↓                                      ↑
    Structured Logging              Guardian (DOM Validation, optional)
```

**Learn More:**
- [Retry Logic with Heuristics](/1_Architecture/1.0_Retry_Logic_Heuristics) - Pipeline details
- [Async and MLOps](/1_Architecture/1.1_Async_MLOps) - Caching and async client
- [Self-Healing Layouts](/3_Features/3.0_Self_Healing) - Guardian and SmartHealer

## Testing

```bash
make test
make test-cov
pytest tests/test_e2e_complete.py -v
pytest tests/test_multiclass_pipeline.py -v
```

## Limitations

- Guardian requires Playwright and browser binaries to be installed separately
- The ML predictor requires training data collected via `trinity mine-generate` before it has a model to load
- LLM content generation requires a running LLM endpoint (Ollama, LM Studio, or cloud API key)
- Themes in `config/themes.yaml` are available for rendering; the default `available_themes` config lists only `enterprise`, `brutalist`, and `editorial`

## Community

- **GitHub**: [fabriziosalmi/trinity](https://github.com/fabriziosalmi/trinity)
- **Issues**: [Report bugs](https://github.com/fabriziosalmi/trinity/issues)
- **Discussions**: [Ask questions](https://github.com/fabriziosalmi/trinity/discussions)
- **Security**: [Report vulnerabilities](https://github.com/fabriziosalmi/trinity/security)

## License

MIT License - see [LICENSE](https://github.com/fabriziosalmi/trinity/blob/main/LICENSE) for details.
