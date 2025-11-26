# Security Policy

## Supported Versions

| Version | Supported          | End of Life    |
|---------|--------------------|----------------|
| 0.4.x   | ✅ Active support  | TBD            |
| 0.3.x   | ⚠️ Security fixes only | 2026-06-01 |
| 0.2.x   | ❌ Unsupported     | 2025-11-26     |
| < 0.2   | ❌ Unsupported     | 2025-11-26     |

## Reporting a Vulnerability

**DO NOT open a public GitHub issue for security vulnerabilities.**

### Private Disclosure Process

1. **Email:** Send vulnerability details to `security@yourdomain.com` (replace with actual contact)
   - Subject: `[SECURITY] Trinity Core Vulnerability Report`
   - Include: Description, affected versions, reproduction steps, potential impact

2. **Expected Response Time:**
   - Initial acknowledgment: Within 48 hours
   - Status update: Within 7 days
   - Fix timeline: Depends on severity (see below)

3. **Severity Levels:**
   - **Critical:** Remote Code Execution (RCE), arbitrary file access
     - Fix target: 24-48 hours
   - **High:** Privilege escalation, authentication bypass
     - Fix target: 7 days
   - **Medium:** XSS, CSRF, information disclosure
     - Fix target: 30 days
   - **Low:** Minor information leaks, configuration issues
     - Fix target: Next release

### Known Security Considerations

#### Pickle Model Loading (CRITICAL)

Trinity Core uses `joblib` (pickle-based) for ML model serialization. **NEVER load models from untrusted sources.**

- **Risk:** Pickle can execute arbitrary Python code during deserialization
- **Mitigation:** Only load models you trained yourself or from verified sources
- **Warning:** Runtime warnings are logged when loading models
- **Future:** Migration to ONNX format planned for v0.5.0

**Safe Usage:**

```python
# ✅ SAFE: Load your own model
poetry run trinity train --dataset-path data/training_dataset.csv
model = joblib.load("models/layout_risk_predictor_20251126_142539.pkl")

# ❌ UNSAFE: Load untrusted model from internet
wget https://random-site.com/model.pkl  # DO NOT DO THIS
model = joblib.load("model.pkl")  # Can execute malicious code
```

#### LLM Endpoint Configuration

Trinity Core connects to local LLM servers (e.g., LM Studio). Ensure endpoints are trusted:

- **Default:** `http://192.168.100.12:1234` (local network only)
- **Risk:** Malicious LLM endpoint could inject harmful content
- **Mitigation:** Use localhost (`127.0.0.1`) or verify TLS certificates for remote endpoints

#### Docker Container Security

- Containers run as non-root user `trinityuser` (UID 1000)
- No privileged mode required
- Network isolation enabled by default
- Volume mounts are read-only where possible

### Dependency Security

Automated dependency scanning via GitHub Dependabot:
- Python packages monitored via `pyproject.toml`
- Security advisories reviewed weekly
- Critical updates applied within 48 hours

### GDPR / Privacy Compliance

**Data Collection:**
- No user data is collected or transmitted
- Training datasets are generated locally
- LLM requests stay on local network (no cloud API calls by default)
- Generated HTML files contain no tracking scripts

**Data Storage:**
- Training data: `data/training_dataset.csv` (local filesystem only)
- ML models: `models/*.pkl` (local filesystem only)
- Output HTML: `output/*.html` (static files, no server-side state)

**Data Deletion:**
- Delete `data/` folder to remove training data
- Delete `models/` folder to remove ML models
- No remote databases or cloud storage

### Responsible Disclosure

We appreciate security researchers who:
- Follow responsible disclosure practices
- Provide detailed reproduction steps
- Allow reasonable time for fixes before public disclosure

**Credit Policy:**
- Acknowledged in release notes (if desired)
- CVE assignment for confirmed vulnerabilities
- Public recognition in SECURITY.md Hall of Fame

### Hall of Fame

_No vulnerabilities reported yet. Be the first!_

---

**Last Updated:** 2025-11-26  
**Contact:** `security@yourdomain.com` (replace with actual email)
