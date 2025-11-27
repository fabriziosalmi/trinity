# Trinity Secrets Management Guide

## Overview

Trinity uses a layered approach to secrets management for maximum security and flexibility:

1. **System Keyring** (Most Secure) - macOS Keychain, Windows Credential Manager, Linux Secret Service
2. **Environment Variables** (Fallback)
3. **.env File** (Development Only)

## Installation

Install the optional `keyring` dependency:

```bash
pip install keyring
```

## Usage

### Storing Secrets

#### Option 1: Python API (Recommended)

```python
from trinity.utils.secrets import secrets_manager

# Store OpenAI API key
secrets_manager.set_secret("openai_api_key", "sk-...")

# Store custom LLM endpoint credentials
secrets_manager.set_secret("llm_api_key", "your-key-here")
```

#### Option 2: CLI (Coming Soon)

```bash
# Store secret via CLI
trinity secrets set openai_api_key

# You'll be prompted to enter the secret securely
```

#### Option 3: Environment Variables

```bash
# For development/testing
export TRINITY_OPENAI_API_KEY="sk-..."
export TRINITY_LLM_API_KEY="your-key-here"
```

#### Option 4: .env File (Development Only)

```bash
# .env file (DO NOT COMMIT TO GIT)
TRINITY_OPENAI_API_KEY=sk-...
TRINITY_LLM_API_KEY=your-key-here
```

### Retrieving Secrets

```python
from trinity.utils.secrets import secrets_manager

# Get API key (returns None if not found)
api_key = secrets_manager.get_secret("openai_api_key")

# Get with default value
api_key = secrets_manager.get_secret("openai_api_key", default="fallback-key")

# Require secret (raises error if not found)
api_key = secrets_manager.get_secret("openai_api_key", required=True)
```

### Deleting Secrets

```python
# Delete from keyring
secrets_manager.delete_secret("openai_api_key")
```

### Backend Information

```python
# Check which backend is being used
info = secrets_manager.get_backend_info()
print(info)
# {
#   "active_backend": "keyring",
#   "keyring_available": True,
#   "keyring_backend": "macOS Keychain",
#   "dotenv_exists": False
# }
```

## Integration with Configuration

Update `config_v2.py` to use secrets manager:

```python
from trinity.utils.secrets import secrets_manager

class ImmutableTrinityConfig(BaseSettings):
    openai_api_key: Optional[str] = Field(
        default_factory=lambda: secrets_manager.get_secret("openai_api_key"),
        description="OpenAI API key from secrets manager"
    )
```

## Platform-Specific Details

### macOS
- Uses **Keychain Access**
- Secrets stored in `login` keychain
- View with: `open "/Applications/Utilities/Keychain Access.app"`
- Search for service: `trinity-core`

### Windows
- Uses **Credential Manager**
- View with: Control Panel → Credential Manager → Windows Credentials
- Search for: `trinity-core`

### Linux
- Uses **Secret Service API** (GNOME Keyring, KWallet)
- May require `dbus` and `gnome-keyring` packages
- Install: `sudo apt install gnome-keyring python3-dbus`

## Security Best Practices

### ✅ DO:
- Use system keyring for production API keys
- Use environment variables for CI/CD pipelines
- Rotate API keys regularly
- Use different keys for dev/staging/prod
- Audit secret access logs

### ❌ DON'T:
- Commit `.env` files to Git
- Hardcode API keys in source code
- Share API keys in chat/email
- Use production keys in development
- Store secrets in config files

## CI/CD Integration

### GitHub Actions

```yaml
name: Trinity Build

on: push

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set secrets
        env:
          TRINITY_OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          TRINITY_LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
        run: |
          echo "Secrets configured from GitHub Secrets"
      
      - name: Run Trinity
        run: trinity build
```

### Docker

```dockerfile
# Use build args (not recommended for production)
ARG TRINITY_OPENAI_API_KEY
ENV TRINITY_OPENAI_API_KEY=$TRINITY_OPENAI_API_KEY

# Or mount secrets (recommended)
# docker run --secret=openai_key,src=./openai.key trinity
```

```bash
# Docker secrets mounting
docker run \
  -e TRINITY_OPENAI_API_KEY="$(cat openai.key)" \
  trinity-builder
```

## Troubleshooting

### Keyring Not Available

```
WARNING: keyring package not available
```

**Solution:**
```bash
pip install keyring
```

### Secret Not Found

```
ConfigurationError: Required secret 'openai_api_key' not found
```

**Solution:**
1. Check keyring: `python -c "import keyring; print(keyring.get_password('trinity-core', 'OPENAI_API_KEY'))"`
2. Check environment: `echo $TRINITY_OPENAI_API_KEY`
3. Set secret: `secrets_manager.set_secret("openai_api_key", "sk-...")`

### Permission Denied (Linux)

```
GDBus.Error:org.freedesktop.DBus.Error.AccessDenied
```

**Solution:**
```bash
# Start gnome-keyring daemon
gnome-keyring-daemon --start --components=secrets

# Or use environment variables as fallback
export TRINITY_OPENAI_API_KEY="sk-..."
```

## Migration Guide

### From Hardcoded Keys

**Before:**
```python
client = OpenAI(api_key="sk-hardcoded-key-bad")
```

**After:**
```python
from trinity.utils.secrets import secrets_manager

api_key = secrets_manager.get_secret("openai_api_key", required=True)
client = OpenAI(api_key=api_key)
```

### From .env Only

**Before:**
```python
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
```

**After:**
```python
from trinity.utils.secrets import secrets_manager

# Automatically checks .env as fallback
api_key = secrets_manager.get_secret("openai_api_key")
```

## Secret Rotation

```python
# Rotate API key
old_key = secrets_manager.get_secret("openai_api_key")
new_key = generate_new_api_key()  # From your API provider

# Update keyring
secrets_manager.set_secret("openai_api_key", new_key)

# Verify
assert secrets_manager.get_secret("openai_api_key") == new_key
```

## Supported Secret Keys

| Key | Description | Required |
|-----|-------------|----------|
| `openai_api_key` | OpenAI API key | No |
| `llm_api_key` | Custom LLM endpoint key | No |
| `github_token` | GitHub API token | No |
| `aws_access_key` | AWS S3 credentials | No (for DVC) |
| `aws_secret_key` | AWS S3 credentials | No (for DVC) |

## Resources

- [Python Keyring Documentation](https://pypi.org/project/keyring/)
- [OWASP Secrets Management](https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password)
- [12-Factor App: Config](https://12factor.net/config)
