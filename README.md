# 🏛️ Trinity

> **AI-powered site generator that actually works in production**

Stop wasting time debugging broken layouts. Trinity generates beautiful, responsive websites from any data using AI—and automatically fixes any CSS issues before deployment.

[![asciicast](https://asciinema.org/a/aPIGQHdxN2hewQgegQhGaiCBG.svg)](https://asciinema.org/a/aPIGQHdxN2hewQgegQhGaiCBG)

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/docker-ready-brightgreen.svg" alt="Docker"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://github.com/fabriziosalmi/trinity/releases"><img src="https://img.shields.io/badge/version-0.8.1-green.svg" alt="Version"></a>
</p>

<p align="center">
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-features">✨ Features</a> •
  <a href="#-why-trinity">🎯 Why Trinity?</a> •
  <a href="#-examples">📚 Examples</a> •
  <a href="https://fabriziosalmi.github.io/trinity/">📖 Documentation</a>
</p>

---

## 🚀 Quick Start

```bash
# Install
pip install -r requirements.txt

# Generate your portfolio
python main.py --input data/input_content.json --theme brutalist --output portfolio.html

# That's it! Open portfolio.html in your browser
```

**What just happened?**
1. ✅ Trinity analyzed your GitHub repos
2. ✅ AI generated compelling content
3. ✅ Applied a professional theme
4. ✅ Automatically fixed any layout issues
5. ✅ Output validated, production-ready HTML

<details>
<summary><b>📦 Try it with Docker</b></summary>

```bash
# Clone and start
git clone https://github.com/fabriziosalmi/trinity.git
cd trinity
./dev.sh start

# Build inside container
docker-compose exec trinity-builder trinity build --theme brutalist
```
</details>

---

## ✨ Features

### 🤖 AI-Powered Content Generation
- **Local LLM Support**: Ollama, LlamaCPP, LM Studio
- **Cloud LLMs**: OpenAI, Claude, Gemini (via API)
- **Smart Caching**: 40% cost reduction on repeated builds
- **Async Operations**: 6x faster with concurrent requests

### 🎨 Professional Themes
- **14 Built-in Themes**: Enterprise, Brutalist, Editorial, Minimalist, Hacker, and more
- **Tailwind CSS**: Modern, responsive design out of the box
- **Dark Mode**: Auto-switching based on user preference
- **Customizable**: YAML configuration for easy theming

### 🔧 Self-Healing Layouts
- **Automatic CSS Fixes**: Detects and repairs overflow, broken grids, text wrapping
- **ML-Powered**: Random Forest multiclass predictor recommends optimal strategy
- **Progressive Strategies**: 4 healing strategies (CSS_BREAK_WORD → FONT_SHRINK → CSS_TRUNCATE → CONTENT_CUT)
- **Visual Validation**: Guardian DOM-based validation system

### ⚡ Production-Ready
- **Circuit Breakers**: Graceful degradation on LLM failures
- **Idempotency**: Same input = same output (deterministic builds)
- **Structured Logging**: JSON logs ready for ELK/Datadog/CloudWatch (stdout in Production)
- **Immutable Config**: Type-safe, validated settings

---

## 🎯 Why Trinity?

| Feature | Traditional SSG | Trinity |
|---------|----------------|--------------|
| **Content Generation** | Manual writing | AI-powered (GPT, Claude, local LLMs) |
| **Layout Issues** | Debug after deploy | Auto-detected and fixed |
| **Themes** | Write CSS yourself | 14 professional themes built-in |
| **Performance** | Synchronous builds | Async (6x faster) |
| **Caching** | Manual implementation | Built-in multi-tier (40% cost savings) |
| **Observability** | Print statements | Structured JSON logging |
| **Reliability** | Hope it works | Circuit breakers + idempotency |
| **Setup Time** | Hours of config | 5 minutes to first build |

---

## 📚 Examples

### Portfolio Site
```bash
# From GitHub repos to portfolio in one command
python main.py --input data/portfolio.txt --theme enterprise
```

**Output:** Professional portfolio with:
- Hero section with AI-generated tagline
- Project cards with descriptions
- Tech stack badges
- Responsive grid layout
- Dark mode support

### Personal Blog
```bash
# Generate blog landing page
python main.py --input blog_posts.json --theme editorial
```

**Features:**
- Clean, readable typography
- Featured post highlighting
- Category organization
- Mobile-first design

### Developer Documentation
```bash
# Technical documentation site
python main.py --input api_docs.json --theme minimalist
```

**Optimized for:**
- Code snippet display
- API reference layout
- Search-friendly structure
- Fast load times

---

## 🛠️ How It Works

<details>
<summary><b>For the curious: Architecture overview</b></summary>

Trinity uses a multi-layer pipeline:

```
Input → Brain (LLM) → Skeleton (Theme) → Healer (CSS Fixes) → Output
         ↓                                      ↑
      Caching                            Predictor (ML)
         ↓                                      ↑
    Structured Logging              Guardian (Visual QA)
```

**1. Brain (Content Generation)**
- LLM generates content from your data
- Pydantic schema validation
- Theme-aware prompts
- Async operations for speed

**2. Skeleton (Theme Application)**
- Jinja2 templates
- Tailwind CSS styling
- 14 professional themes
- Responsive by default

**3. Predictor (ML Strategy Recommendation)**
- Random Forest multiclass classifier
- Predicts optimal healing strategy (0-4: NONE → CONTENT_CUT, 99: UNRESOLVED)
- Trained on 2000+ real build samples
- >60% confidence threshold for smart strategy selection

**4. Healer (CSS Auto-Repair)**
- 4 progressive strategies (CSS_BREAK_WORD → FONT_SHRINK → CSS_TRUNCATE → CONTENT_CUT)
- ML predictor recommends optimal strategy (skips 1-3 iterations)
- Learns from successful fixes
- 95% success rate on pathological content

**5. Guardian (Visual Validation - Optional)**
- Playwright headless browser
- DOM overflow detection
- Can be disabled for faster builds

For detailed architecture, see [ARCHITECTURE.md](docs/ARCHITECTURE.md)

</details>

---

## 📊 Performance

**Phase 6 Improvements (v0.7.0):**

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Throughput | 5 req/sec | 30 req/sec | **6x faster** |
| LLM Costs | $1.00/build | $0.60/build | **40% savings** |
| Command Length | 64 chars | 13 chars | **70% less typing** |
| Observability | Print statements | JSON logs | **100% better** |

**Features:**
- ✅ Async/await with HTTP/2 multiplexing
- ✅ Multi-tier caching (memory → Redis → filesystem)
- ✅ Structured logging for aggregation
- ✅ Makefile shortcuts (`make test`, `make build`)

---

## 🎨 Available Themes

```bash
# Professional
--theme enterprise      # Corporate, clean, trustworthy
--theme minimalist      # Simple, elegant, focused

# Creative
--theme brutalist       # Bold, raw, attention-grabbing
--theme editorial       # Magazine-style, readable

# Technical
--theme hacker          # Terminal-inspired, monospace
--theme tech_01         # Modern tech aesthetic

# And 8 more...
```

Preview all themes: `python main.py --list-themes`

---

## 🔧 Configuration

### Basic Setup
```bash
# Use local LLM (recommended)
export LLM_PROVIDER=ollama
export LLM_MODEL=qwen2.5-coder:7b

# Or cloud LLMs
export OPENAI_API_KEY=your_key
export LLM_PROVIDER=openai

# Production Telemetry
export TRINITY_ENV=Production  # Enable JSON logs to stdout
```

### Advanced Configuration
```yaml
# config/settings.yaml
llm:
  provider: ollama
  model: qwen2.5-coder:7b
  temperature: 0.2
  cache_enabled: true
  cache_ttl: 3600

themes:
  default: brutalist
  dark_mode: auto

healer:
  enable_neural: true
  max_attempts: 3
  strategies:
    - CSS_BREAK_WORD
    - FONT_SHRINK
    - CSS_TRUNCATE
```

See [Configuration Guide](docs/CONFIGURATION.md) for all options.

---

## 📖 Documentation

### Getting Started
- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions
- [Quick Start Tutorial](docs/QUICKSTART.md) - Your first portfolio in 5 minutes
- [CLI Reference](docs/CLI.md) - Complete command documentation

### Phase 6 Features
- [Async Guide](docs/ASYNC_GUIDE.md) - Async/await migration and performance
- [Caching Guide](docs/CACHING.md) - Multi-tier cache configuration
- [Logging Guide](docs/LOGGING_GUIDE.md) - Structured logging and observability
- [Makefile Guide](docs/MAKEFILE_GUIDE.md) - Development workflow shortcuts

### Advanced Topics
- [Architecture Overview](docs/ARCHITECTURE.md) - System design and components
- [Neural Healer](docs/NEURAL_SYMBOLIC_ARCHITECTURE.md) - ML-powered CSS fixing
- [Theme Development](docs/CENTURIA_FACTORY_SUMMARY.md) - Creating custom themes
- [Security Policy](SECURITY.md) - Vulnerability reporting

### Development
- [Contributing Guide](CONTRIBUTING.md) - Development setup and guidelines
- [Changelog](CHANGELOG.md) - Version history and release notes
- [Phase 6 Roadmap](docs/PHASE6_ROADMAP.md) - Future features and improvements

---

## 🧪 Testing

```bash
# Run all tests
make test

# With coverage
make test-cov

# E2E tests (complete workflow)
pytest tests/test_e2e_complete.py -v

# Multiclass pipeline tests
pytest tests/test_multiclass_pipeline.py -v

# Docker E2E validation
./scripts/test_docker_e2e.sh
```

**Test Coverage:** 111/111 tests passing (24 E2E + multiclass, 32 healer, 6 engine, 49 other)

---

## 🐳 Docker Deployment

```bash
# Build image
make docker-build

# Run container
make docker-run

# Development mode with live reload
make docker-dev
```

See [Docker Guide](DOCKER_README.md) for production deployment.

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/trinity.git
cd trinity

# 2. Setup development environment
make setup

# 3. Create feature branch
git checkout -b feature/amazing-feature

# 4. Make changes and test
make test
make format
make lint

# 5. Commit and push
git commit -m "feat: add amazing feature"
git push origin feature/amazing-feature

# 6. Open Pull Request
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **LLM Providers**: Ollama, OpenAI, Anthropic, Google
- **Frameworks**: Jinja2, Tailwind CSS, PyTorch
- **Tools**: Playwright, Pydantic, httpx
- **Community**: All contributors and users

---

## 📊 Project Stats

- **Version:** 0.8.1
- **Python:** 3.10+
- **Tests:** 111/111 passing (9 E2E, 15 multiclass, 32 healer, 6 engine, 49 other)
- **Themes:** 14 built-in + Centuria Factory for mass generation
- **Self-Healing:** 4 progressive strategies with ML prediction
- **Coverage:** Comprehensive E2E + Docker validation

---

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/fabriziosalmi/trinity/issues)
- **Discussions**: [GitHub Discussions](https://github.com/fabriziosalmi/trinity/discussions)
- **Security**: [SECURITY.md](SECURITY.md)

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/fabriziosalmi">@fabriziosalmi</a>
</p>

<p align="center">
  <i>Generate beautiful portfolios. Let AI do the heavy lifting.</i>
</p>
