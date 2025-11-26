# Trinity Core - Docker Development Guide

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- LM Studio running on host machine (http://localhost:1234)
- 4GB+ RAM available for Docker

### Start the Stack

```bash
# macOS/Linux
./dev.sh start

# Windows
dev.bat start
```

This starts:
1. **trinity-builder**: Python + Playwright + LLM client
2. **trinity-web**: Nginx server at http://localhost:8080

---

## Common Workflows

### 1. Build Demo Site
```bash
# macOS/Linux
./dev.sh build brutalist

# Windows
dev.bat build brutalist
```

View at: http://localhost:8080

### 2. Build with LLM Content Generation
```bash
# macOS/Linux
./dev.sh build-llm editorial

# Windows
dev.bat build-llm editorial
```

### 3. Run Guardian QA Test
```bash
# macOS/Linux
./dev.sh guardian brutalist

# Windows
dev.bat guardian brutalist
```

### 4. Run Chaos Test (Intentionally Broken Layout)
```bash
# macOS/Linux
./dev.sh chaos

# Windows
dev.bat chaos
```

Expected output: `❌ STATUS: REJECTED` (Guardian catches overflow bugs)

### 5. Watch Logs
```bash
# macOS/Linux
./dev.sh logs trinity-builder

# Windows
dev.bat logs trinity-builder
```

### 6. Open Shell (for debugging)
```bash
# macOS/Linux
./dev.sh shell

# Windows
dev.bat shell
```

Inside container:
```bash
python main.py --demo --theme brutalist
ls -la output/
cat logs/trinity.log
```

---

## Architecture

### Docker Networking
```
┌─────────────────────────────────────────────┐
│ Host Machine (macOS/Windows/Linux)         │
│                                             │
│  LM Studio:  http://localhost:1234         │
│                                             │
│  ┌────────────────────────────────────┐    │
│  │ Docker Network: trinity-net        │    │
│  │                                    │    │
│  │  ┌──────────────────────────┐     │    │
│  │  │ trinity-builder          │     │    │
│  │  │ - Python 3.14            │     │    │
│  │  │ - Playwright/Chromium    │     │    │
│  │  │ - Connects to LM Studio  │     │    │
│  │  │   via host.docker.internal    │    │
│  │  └──────────────────────────┘     │    │
│  │                                    │    │
│  │  ┌──────────────────────────┐     │    │
│  │  │ trinity-web              │     │    │
│  │  │ - Nginx Alpine           │     │    │
│  │  │ - Serves ./output folder │     │    │
│  │  │ - Port 8080:80           │     │    │
│  │  └──────────────────────────┘     │    │
│  └────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

### LM Studio Connection
Docker containers cannot use `localhost` to reach the host. Trinity Core uses:

**Environment Variable**: `LM_STUDIO_URL=http://host.docker.internal:1234/v1`

This magic hostname (`host.docker.internal`) resolves to the host machine's network interface, allowing the container to access LM Studio.

**Code Implementation**:
```python
# src/content_engine.py & src/guardian.py
DEFAULT_LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
```

- **In Docker**: Uses `host.docker.internal:1234`
- **On Host**: Uses `localhost:1234` (fallback)

---

## Volume Mounts

### Development Mode (Live Code Sync)
```yaml
volumes:
  - .:/app  # Entire project directory synced
```

Changes to Python files are immediately available inside the container. No rebuild required.

### Output Directory (Shared with Nginx)
```yaml
trinity-builder:
  volumes:
    - .:/app

trinity-web:
  volumes:
    - ./output:/usr/share/nginx/html:ro  # Read-only
```

When builder generates HTML, Nginx serves it immediately.

---

## Commands Reference

### Dev Script Commands

| Command | Description |
|---------|-------------|
| `./dev.sh start` | Start all services |
| `./dev.sh stop` | Stop all services |
| `./dev.sh restart` | Restart services |
| `./dev.sh status` | Health check + LM Studio connection test |
| `./dev.sh build [theme]` | Build with demo data |
| `./dev.sh build-llm [theme]` | Build with LLM generation |
| `./dev.sh guardian [theme]` | Run Guardian QA |
| `./dev.sh chaos` | Run chaos test (broken layout) |
| `./dev.sh logs [service]` | Tail service logs |
| `./dev.sh shell` | Open bash shell in builder |
| `./dev.sh clean` | Remove generated files |
| `./dev.sh rebuild` | Rebuild Docker images |

### Raw Docker Compose Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f trinity-builder

# Execute command in builder
docker-compose exec trinity-builder python main.py --demo --theme brutalist

# Rebuild images
docker-compose build --no-cache

# Check service status
docker-compose ps
```

---

## Troubleshooting

### Issue: LM Studio Not Reachable

**Symptoms**:
```
[WARNING] LM Studio: Not reachable
APIConnectionError: Connection refused
```

**Solutions**:
1. Verify LM Studio is running on host: http://localhost:1234
2. Check Docker can reach host:
   ```bash
   docker-compose exec trinity-builder curl http://host.docker.internal:1234/v1/models
   ```
3. On Linux, use `host-gateway` instead:
   ```yaml
   extra_hosts:
     - "host.docker.internal:host-gateway"
   ```

### Issue: Playwright Browser Not Found

**Symptoms**:
```
playwright._impl._api_types.Error: Executable doesn't exist
```

**Solution**:
The official `mcr.microsoft.com/playwright/python` image has browsers pre-installed. If you see this error:
1. Rebuild the image: `./dev.sh rebuild`
2. Verify image: `docker-compose exec trinity-builder playwright --version`

### Issue: Permission Denied on Output Files

**Symptoms**:
```
PermissionError: [Errno 13] Permission denied: 'output/index.html'
```

**Solution**:
Docker writes files as root. Fix ownership:
```bash
sudo chown -R $USER:$USER output/ logs/
```

Or add to `docker-compose.yml`:
```yaml
user: "${UID}:${GID}"
```

### Issue: Port 8080 Already in Use

**Symptoms**:
```
Error: bind: address already in use
```

**Solution**:
Change port in `docker-compose.yml`:
```yaml
trinity-web:
  ports:
    - "8081:80"  # Use 8081 instead
```

---

## Production Deployment

### Build Optimized Image

Create `Dockerfile.prod`:
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs output

CMD ["python", "main.py", "--demo-all"]
```

### Build and Run
```bash
docker build -f Dockerfile.prod -t trinity-core:latest .
docker run -p 8080:80 \
  -e LM_STUDIO_URL=http://your-llm-api.com/v1 \
  trinity-core:latest
```

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Trinity Core CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker-compose build
      
      - name: Run tests
        run: |
          docker-compose up -d
          docker-compose exec -T trinity-builder python -m pytest tests/
          docker-compose down
      
      - name: Run Guardian chaos test
        run: |
          docker-compose up -d
          docker-compose exec -T trinity-builder \
            python main.py --static-json --input data/chaos_content.json \
            --theme brutalist --guardian --guardian-only-dom
```

---

## Performance Tips

### 1. Use BuildKit for Faster Builds
```bash
DOCKER_BUILDKIT=1 docker-compose build
```

### 2. Mount Python Cache
Already configured in `docker-compose.yml`:
```yaml
volumes:
  - python-cache:/root/.cache/pip
```

### 3. Prune Unused Images
```bash
docker system prune -a
```

---

## Next Steps

1. **Add Watchers**: Use `watchdog` to auto-rebuild on file changes
2. **Multi-Stage Builds**: Separate build and runtime images
3. **Health Checks**: Already included in `docker-compose.yml`
4. **Secrets Management**: Use Docker secrets for API keys
5. **Kubernetes**: Deploy with Helm charts for scaling

---

**Need Help?**
- Check logs: `./dev.sh logs trinity-builder`
- Open shell: `./dev.sh shell`
- Run status check: `./dev.sh status`
