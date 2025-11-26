# Trinity Core - Terminal Recording Guide

## Quick Start

### 1. Install Recording Tool

**Option A: asciinema (Recommended)**
```bash
# macOS
brew install asciinema

# Linux
sudo apt-get install asciinema
# or
pip install asciinema
```

**Option B: terminalizer**
```bash
npm install -g terminalizer
```

**Option C: ttygif (for GIF)**
```bash
# macOS
brew install ttygif

# Linux
git clone https://github.com/icholy/ttygif.git
cd ttygif && make
```

### 2. Record Demo

**Using asciinema:**
```bash
# Make demo executable
chmod +x scripts/demo.sh

# Record the demo
asciinema rec trinity-demo.cast -c "./scripts/demo.sh"

# Upload and get shareable link
asciinema upload trinity-demo.cast
```

**Using terminalizer:**
```bash
# Initialize config
terminalizer init trinity-demo

# Record
terminalizer record trinity-demo -c "./scripts/demo.sh"

# Render to GIF
terminalizer render trinity-demo -o docs/assets/demo.gif
```

### 3. Convert to GIF (if needed)

**From asciinema:**
```bash
# Install svg-term-cli
npm install -g svg-term-cli

# Convert to SVG
cat trinity-demo.cast | svg-term --out docs/assets/demo.svg

# Or use asciicast2gif
docker run --rm -v $PWD:/data asciinema/asciicast2gif trinity-demo.cast docs/assets/demo.gif
```

**Optimize GIF:**
```bash
# Install gifsicle
brew install gifsicle  # macOS
sudo apt-get install gifsicle  # Linux

# Optimize
gifsicle -O3 --colors 256 docs/assets/demo.gif -o docs/assets/demo-optimized.gif
```

## Recording Tips

### Terminal Settings
```bash
# Set terminal size for consistency
export COLUMNS=100
export LINES=30

# Clear before recording
clear
```

### Timing
- Total duration: ~60-90 seconds
- Pause between steps: 2 seconds
- Text display speed: Natural typing speed

### What to Show

1. **Configuration** (10s)
   - Create immutable config
   - Show dependency injection

2. **Exception Handling** (10s)
   - List custom exceptions
   - Show type safety

3. **Circuit Breaker** (10s)
   - Initialize breaker
   - Demonstrate resilience

4. **Idempotency** (10s)
   - Generate key
   - Show caching

5. **Secrets** (10s)
   - Show backend info
   - Keyring status

6. **Build Demo** (15s)
   - Create content
   - Run build
   - Show output

7. **Summary** (10s)
   - Feature checklist
   - Documentation links

## Manual Recording Steps

If automated script doesn't work:

### 1. Prepare
```bash
cd /Users/fab/GitHub/trinity
source venv/bin/activate  # if using venv
clear
```

### 2. Start Recording
```bash
asciinema rec trinity-demo.cast
```

### 3. Execute Commands

```bash
# Header
echo "🏛️  Trinity Core v0.6.0 - Production-Ready Architecture"
echo ""

# 1. Configuration
python3 -c "
from trinity.config_v2 import create_config
config = create_config(max_retries=5, default_theme='brutalist')
print(f'Config: max_retries={config.max_retries}, theme={config.default_theme}')
"

# 2. Exceptions
python3 -c "
from trinity.exceptions import LLMConnectionError, CircuitOpenError
print('Custom exceptions: LLMConnectionError, CircuitOpenError, +13 more')
"

# 3. Circuit Breaker
python3 -c "
from trinity.utils.circuit_breaker import CircuitBreaker
breaker = CircuitBreaker(name='demo', failure_threshold=3)
print(f'Circuit Breaker: {breaker.state.value}, threshold={breaker.failure_threshold}')
"

# 4. Idempotency
python3 -c "
from trinity.utils.idempotency import IdempotencyKeyManager
manager = IdempotencyKeyManager(enable_persistence=False)
key = manager.generate_key(theme='brutalist', content='demo')
print(f'Idempotency key: {key[:32]}...')
"

# 5. Summary
echo ""
echo "✅ Production-ready features:"
echo "   • Immutable Configuration"
echo "   • Circuit Breakers"
echo "   • Idempotency"
echo "   • Secrets Management"
echo ""
echo "📚 Docs: REFACTORING_SUMMARY.md"
```

### 4. Stop Recording
Press `Ctrl+D` or type `exit`

## Embedding in README

### As SVG (Recommended)
```markdown
![Trinity Demo](https://asciinema.org/a/YOUR_RECORDING_ID.svg)
```

### As GIF
```markdown
![Trinity Demo](docs/assets/demo.gif)
```

### As Link
```markdown
[![asciicast](https://asciinema.org/a/YOUR_RECORDING_ID.png)](https://asciinema.org/a/YOUR_RECORDING_ID)
```

## Alternative: Screenshot Sequence

If recording doesn't work, create screenshots:

```bash
# macOS
screencapture -x demo-1.png

# Linux
scrot demo-1.png
```

Then create a collage:

```bash
# Using ImageMagick
montage demo-*.png -tile 2x3 -geometry +5+5 docs/assets/demo-collage.png
```

## Hosting Options

1. **asciinema.org** (free, recommended)
   - Upload: `asciinema upload trinity-demo.cast`
   - Embed directly in README

2. **GitHub Assets**
   - Upload GIF to `docs/assets/`
   - Reference in README

3. **CloudFlare R2 / S3**
   - For larger files
   - CDN distribution

## Example README Section

```markdown
# 🏛️ Trinity Core

<p align="center">
  <img src="https://asciinema.org/a/YOUR_RECORDING_ID.svg" alt="Trinity Demo" width="800">
</p>

> **AI-Powered Static Site Generator with Production-Ready Architecture**

Trinity Core v0.6.0 introduces enterprise-grade features:
- 🔒 Immutable Configuration
- 🔌 Circuit Breakers
- 🔑 Idempotency
- 🔐 Secrets Management

[📚 Documentation](docs/) | [🚀 Quick Start](#quick-start) | [🔧 Migration Guide](docs/MIGRATION_GUIDE.md)
```

## Troubleshooting

### Recording Too Fast
Add delays in script:
```bash
sleep 2  # between steps
```

### Recording Too Slow
Use `--speed` flag:
```bash
terminalizer render trinity-demo --speed 1.5
```

### GIF Too Large
Optimize:
```bash
gifsicle -O3 --colors 128 --lossy=80 input.gif -o output.gif
```

### Python Commands Fail
Ensure environment is activated:
```bash
source venv/bin/activate
export PYTHONPATH=$PWD/src:$PYTHONPATH
```

## Final Steps

1. Record demo: `./scripts/demo.sh`
2. Upload to asciinema: `asciinema upload trinity-demo.cast`
3. Update README with embed code
4. Commit changes:
   ```bash
   git add README.md docs/assets/ scripts/demo.sh
   git commit -m "Add terminal demo recording"
   ```
