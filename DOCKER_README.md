# 🐋 Trinity Core - Docker Quick Start

Complete Docker development environment for Trinity Core static site generator.

## Prerequisites

- **Docker Desktop >= 24.0** (latest stable recommended)
- **Docker Compose >= 2.20** (included with Docker Desktop)
- **LM Studio >= 0.2.0** with Qwen 2.5 Coder model (optional for LLM content generation)
  - Default endpoint: `http://localhost:1234`
  - Alternative: Any OpenAI-compatible API
- **Disk Space:** ~500MB for Docker images + models

## Verify Setup
```bash
./verify-docker.sh
```

## Start Development Environment

### macOS/Linux
```bash
# Start all services (builder + web server)
./dev.sh start

# Build demo site
./dev.sh build brutalist

# View at http://localhost:8080
```

### Windows
```batch
REM Start services
dev.bat start

REM Build demo site
dev.bat build brutalist

REM View at http://localhost:8080
```

## Quick Commands

| Command | Description |
|---------|-------------|
| `./dev.sh start` | Start Docker services |
| `./dev.sh build [theme]` | Build with demo data |
| `./dev.sh build-llm [theme]` | Build with LLM generation |
| `./dev.sh guardian [theme]` | Run Guardian QA inspection |
| `./dev.sh chaos` | Test with broken layout (should REJECT) |
| `./dev.sh logs` | View build logs |
| `./dev.sh shell` | Open shell in container |
| `./dev.sh stop` | Stop services |

## Architecture

```
┌─────────────────────────────────────┐
│ Host Machine                        │
│  - LM Studio (localhost:1234)       │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Docker: trinity-builder      │  │
│  │  - Python 3.14               │  │
│  │  - Playwright/Chromium       │  │
│  │  - Connects via              │  │
│  │    host.docker.internal      │  │
│  └──────────────────────────────┘  │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ Docker: trinity-web          │  │
│  │  - Nginx                     │  │
│  │  - Serves ./output           │  │
│  │  - http://localhost:8080     │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Why Docker?

1. **Playwright Pre-installed**: Microsoft's official image includes Chromium for Guardian screenshots
2. **LM Studio Bridge**: `host.docker.internal` allows container to reach LM Studio on host
3. **Isolated Environment**: No conflicts with system Python/packages
4. **Instant Refresh**: Nginx auto-serves new builds from `./output`

## Example Workflows

### Build Demo Site (No LLM Required)
```bash
./dev.sh build brutalist
# Open http://localhost:8080
```

### Build with LLM Content
```bash
./dev.sh build-llm editorial
# Generates AI-powered content using LM Studio
```

### Run Guardian QA Test
```bash
./dev.sh guardian brutalist
# Expected: ✅ Guardian Approved
```

### Test Chaos Detection
```bash
./dev.sh chaos
# Expected: ❌ Guardian REJECTED (overflow detected)
```

## Files Created

- `Dockerfile.dev` - Development image with Python + Playwright
- `docker-compose.yml` - Multi-service orchestration
- `.dockerignore` - Exclude unnecessary files from build
- `dev.sh` - macOS/Linux helper script
- `dev.bat` - Windows helper script
- `verify-docker.sh` - Pre-flight checks
- `docs/DOCKER.md` - Complete documentation

## Troubleshooting

### LM Studio Not Reachable
```bash
# Check connection from container
docker-compose exec trinity-builder curl http://host.docker.internal:1234/v1/models
```

### Port 8080 in Use
Edit `docker-compose.yml`:
```yaml
trinity-web:
  ports:
    - "8081:80"  # Change to 8081
```

### Permission Issues
```bash
sudo chown -R $USER:$USER output/ logs/
```

## Full Documentation
See `docs/DOCKER.md` for:
- Advanced configuration
- Production deployment
- CI/CD integration
- Performance tuning

---

**Ready to Deploy?** The Docker setup is production-ready. Change `LM_STUDIO_URL` to your hosted LLM API endpoint.
