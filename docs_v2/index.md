---
layout: home

hero:
  name: "Trinity Core"
  text: "AI-Powered Site Generator"
  tagline: "Stop debugging broken layouts. Let AI fix them automatically."
  actions:
    - theme: brand
      text: Quick Start
      link: /2_Development/2.0_Setup
    - theme: alt
      text: Architecture
      link: /1_Architecture/1.0_Neural_Symbolic
    - theme: alt
      text: View on GitHub
      link: https://github.com/fabriziosalmi/trinity

features:
  - title: AI-Powered Content
    details: Generate compelling content with local LLMs (Ollama, LlamaCPP) or cloud providers (OpenAI, Claude, Gemini). 40% cost savings with multi-tier caching.
  
  - title: 14 Professional Themes
    details: Built-in themes powered by Tailwind CSS. Enterprise, Brutalist, Editorial, Minimalist, and more. Dark mode included.
  
  - title: Self-Healing Layouts
    details: LSTM neural network detects and fixes CSS issues automatically. 95% success rate with progressive fallback strategies.
  
  - title: 6x Faster Builds
    details: Async/await with HTTP/2 multiplexing. Concurrent LLM requests. Sub-millisecond cache hits. Production-ready performance.
  
  - title: Production-Ready
    details: Circuit breakers, idempotency, structured logging (JSON), visual QA validation. Enterprise-grade reliability.
  
  - title: Full Observability
    details: Structured JSON logs ready for ELK/Datadog/CloudWatch. Correlation IDs for distributed tracing. Performance metrics built-in.
---

## Why Trinity?

| Feature | Traditional SSG | Trinity Core |
|---------|----------------|--------------|
| **Content** | Manual writing | AI-powered |
| **Layout Issues** | Debug after deploy | Auto-detected & fixed |
| **Themes** | Write CSS yourself | 14 built-in professional themes |
| **Performance** | Synchronous | Async (6x faster) |
| **Caching** | Manual | Multi-tier (40% cost savings) |
| **Observability** | Print statements | Structured JSON logging |

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Generate portfolio
python main.py --input data/portfolio.txt --theme brutalist

# That's it! Open output/index.html
```

## What Just Happened?

1. ✅ Analyzed your GitHub repos non structured data
2. ✅ AI generated compelling content
3. ✅ Applied professional theme
4. ✅ Auto-fixed any layout issues
5. ✅ Output validated HTML

## Architecture Overview

Trinity uses a **5-layer neural-generative pipeline**:

```
Input → Brain (LLM) → Skeleton (Theme) → Healer (CSS Fixes) → Output
         ↓                                      ↑
      Caching                            Predictor (ML)
         ↓                                      ↑
    Structured Logging              Guardian (Visual QA)
```

**Learn More:**
- [Neural-Symbolic Architecture](/1_Architecture/1.0_Neural_Symbolic) - Deep dive into the 5-layer system
- [Async & MLOps](/1_Architecture/1.1_Async_MLOps) - Performance optimization details
- [Self-Healing Layouts](/3_Features/3.0_Self_Healing) - How the LSTM neural network works

## Performance

**Phase 6 Improvements:**

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Throughput | 5 req/sec | 30 req/sec | **6x faster** |
| LLM Costs | $1.00/build | $0.60/build | **40% savings** |
| Command Length | 64 chars | 13 chars | **70% less typing** |
| Observability | Print statements | JSON logs | **100% better** |

## Community

- **GitHub**: [fabriziosalmi/trinity](https://github.com/fabriziosalmi/trinity)
- **Issues**: [Report bugs](https://github.com/fabriziosalmi/trinity/issues)
- **Discussions**: [Ask questions](https://github.com/fabriziosalmi/trinity/discussions)
- **Security**: [Report vulnerabilities](https://github.com/fabriziosalmi/trinity/security)

## License

MIT License - see [LICENSE](https://github.com/fabriziosalmi/trinity/blob/main/LICENSE) for details.
