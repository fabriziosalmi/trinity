# Trinity Core

**Deterministic Layouts. AI-Powered Content.**

Trinity Core is an industrial-strength static site generator that separates concerns:
- **Golden Skeletons:** Human-crafted, accessible HTML/Tailwind templates (immutable)
- **Python Builder:** Fast Jinja2-based assembler (deterministic)
- **LLM Painter:** AI generates content only, not structure (zero hallucinations)

## Philosophy

Instead of asking LLMs to write entire HTML pages (slow, error-prone), we:
1. Maintain a library of **validated** component templates
2. Use **Python** to assemble pages at blazing speed
3. Let **LLMs** handle only content generation (text, copy, tone)

**Result:** Predictable output, no broken layouts, WCAG-compliant by design.

## Project Structure

```
trinity-core/
├── config/              # Configuration files
│   ├── settings.py      # Pydantic settings models
│   └── themes.json      # Theme definitions (CSS class mappings)
├── data/                # Raw input data
│   └── input_content.json
├── library/             # Golden Skeleton Templates
│   ├── atoms/           # Buttons, badges, inputs
│   ├── molecules/       # Search bars, cards
│   ├── organisms/       # Hero, navbar, grids
│   └── templates/       # Base layouts
├── logs/                # Structured logs
├── output/              # Generated HTML files
├── src/                 # Core Python modules
│   ├── builder.py       # Site assembler
│   ├── llm_client.py    # LLM API wrapper
│   └── validator.py     # Schema & HTML validation
├── main.py              # CLI entry point
└── requirements.txt     # Pinned dependencies
```

## Installation

```bash
# Clone repository
git clone <repo-url>
cd trinity-core

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

## Quick Start

### 1. Build Demo Pages (No LLM Required)

Generate demo pages using mock data:

```bash
# Build all themes
python main.py --demo-all

# Build single theme
python main.py --demo --theme brutalist

# Output: output/index_brutalist.html
```

### 2. Validate Configuration

```bash
# Check themes.json integrity
python main.py --validate-only
```

### 3. Test Individual Components

```bash
# Run builder demo
python src/builder.py

# Test LLM client (requires Ollama running)
python src/llm_client.py

# Test validator
python src/validator.py
```

## Available Themes

| Theme | Description | Use Case |
|-------|-------------|----------|
| **enterprise** | Clean, professional, SaaS-ready | Corporate sites, dashboards |
| **brutalist** | Bold, high-contrast, monospace | Creative portfolios, experimental |
| **editorial** | Serif typography, classic layout | Blogs, documentation |

Themes are defined in `config/themes.json` with strict CSS class mappings.

## Usage Examples

### Build with Mock Data

```python
from src.builder import SiteBuilder
from src.validator import ContentValidator

content = {
    "brand_name": "My Portfolio",
    "hero": {
        "title": "Hello World",
        "subtitle": "Developer & Designer"
    },
    "repos": [...]
}

# Validate content structure
validator = ContentValidator()
validator.validate_content_schema(content)

# Build page
builder = SiteBuilder()
output = builder.build_page(content, theme="editorial")
print(f"Generated: {output}")
```

### LLM Content Generation (Coming Soon)

```python
from src.llm_client import LLMClient

with LLMClient(model_name="llama3.2:3b") as llm:
    prompt = "Generate portfolio content for a Python developer"
    content_json = llm.generate_content(prompt, expect_json=True)
```

## Architecture Principles

### The 400 Rules (Highlights)

- **Rule #5:** Check file existence before operations
- **Rule #7:** Catch specific exceptions, don't swallow errors
- **Rule #8:** No magic numbers/strings (use constants)
- **Rule #13:** No hardcoded paths (use config)
- **Rule #14:** Avoid God Objects (single responsibility)
- **Rule #27:** Separation of concerns (logic vs presentation)
- **Rule #28:** Structured logging (JSON for production)
- **Rule #64:** Autoescape templates (prevent XSS)
- **Rule #71:** Mobile-first responsive design
- **Rule #94:** Semantic HTML5 (`<nav>`, `<section>`, `<article>`)
- **Rule #95:** WCAG Level A accessibility (ARIA, focus states)
- **Rule #96:** No clever one-liners (explicit > implicit)

## Component Library

### Organisms (Full Sections)

- **`navbar_v1.html`** - Responsive navigation with mobile menu
- **`hero_v1.html`** - Above-the-fold hero section
- **`repo_grid_v1.html`** - Repository/project grid

All components:
- ✅ ARIA labels and semantic HTML
- ✅ Keyboard navigation support
- ✅ Responsive (mobile-first)
- ✅ Theme-agnostic (CSS classes injected)

## Configuration

### Themes (`config/themes.json`)

Add new themes by defining CSS class mappings:

```json
{
  "my_theme": {
    "nav_bg": "bg-purple-900",
    "text_primary": "text-white",
    "btn_primary": "bg-yellow-400 text-black",
    ...
  }
}
```

Required keys:
- `nav_bg`, `text_primary`, `text_secondary`, `nav_link`
- `btn_primary`, `btn_secondary`
- `hero_bg`, `card_bg`
- `heading_primary`, `heading_secondary`, `body_text`

### Settings (`config/settings.py`)

Pydantic models with validation:
- `LLMConfig` - LLM client settings
- `BuildConfig` - Build paths and options
- `ContentSchema` - Expected content structure

## Roadmap

- [ ] LLM content generation pipeline
- [ ] A/B testing framework for themes
- [ ] Atom/Molecule component library expansion
- [ ] HTML minification option
- [ ] GitHub Actions CI/CD
- [ ] VS Code extension for theme preview

## Development

```bash
# Run tests (when implemented)
pytest

# Type checking
mypy src/

# Code formatting
black src/ main.py

# Linting
ruff check src/
```

## License

MIT

## Credits

Built following the **400 Rules of SOTA Engineering**:
- Type safety (Pydantic)
- Error handling (explicit exceptions)
- Accessibility (WCAG Level A)
- Separation of concerns (templates ≠ logic)

No vibecoding. Only engineering.
