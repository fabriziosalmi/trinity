# Git History Cleanup - Trinity Core

## Overview

This document explains how to clean sensitive data from the Trinity Core git history, specifically:

- **Hardcoded IP addresses** (192.168.100.12 → localhost)
- **API keys and secrets** (if accidentally committed)
- **Passwords and tokens** (if found)

## Why Clean Git History?

Even after removing sensitive data from current files, it remains in git history:
- Anyone with repository access can see historical commits
- Forks and clones contain the full history
- Automated scanners can find secrets in old commits

## Pre-Cleanup Checklist

✅ **Before running cleanup:**

1. Ensure all team members have pushed their changes
2. Notify collaborators that history will be rewritten
3. Make sure you have a backup (script creates one automatically)
4. Close any open pull requests (they'll need to be recreated)

## Current Status

**Files cleaned in working tree (v0.6.0):**
- ✅ `src/trinity/config_v2.py` - Removed hardcoded IP
- ✅ `src/trinity/config.py` - Removed hardcoded IP
- ✅ `src/trinity/components/brain.py` - Removed hardcoded IP
- ✅ `src/trinity/components/guardian.py` - Removed hardcoded IP
- ✅ `src/content_engine.py` - Removed hardcoded IP
- ✅ `src/guardian.py` - Removed hardcoded IP
- ✅ `config/settings.yaml` - Removed hardcoded IP
- ✅ All documentation files (*.md)
- ✅ All shell scripts (*.sh, *.bat)

**Still in history (pre-v0.6.0 commits):**
- ❌ 192.168.100.12 appears in 100+ historical commits
- ❌ Possibly other sensitive data patterns

## Cleanup Methods

### Method 1: Automated Script (Recommended)

Use the provided cleanup script:

```bash
# Run the cleanup script
./scripts/cleanup-git-history.sh

# Follow prompts and review changes
git log --all --oneline

# If satisfied, force push
git push --force --all
git push --force --tags
```

**What the script does:**
1. Creates backup branch: `backup-before-cleanup`
2. Installs `git-filter-repo` if needed
3. Replaces sensitive patterns across all history
4. Preserves commit structure and timestamps

### Method 2: Manual with BFG Repo-Cleaner

Alternative tool for large repositories:

```bash
# Install BFG
brew install bfg

# Create replacements file
cat > replacements.txt << EOF
192.168.100.12==>localhost
api_key=*******==>api_key=REDACTED
password=*******==>password=REDACTED
EOF

# Run BFG
bfg --replace-text replacements.txt

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push
git push --force --all
```

### Method 3: Manual with git-filter-repo

For fine-grained control:

```bash
# Install git-filter-repo
pip install git-filter-repo

# Replace specific text
git-filter-repo --replace-text <(echo '192.168.100.12==>localhost')

# Or use regex patterns
git-filter-repo --replace-text <(cat << EOF
regex:192\.168\.100\.12==>localhost
regex:api[_-]key\s*=\s*["']([^"']+)["']==>api_key="REDACTED"
EOF
)

# Force push
git push --force --all
```

## Post-Cleanup Steps

### 1. Verify Cleanup

```bash
# Search for sensitive data in history
git log -S "192.168.100.12" --all
git log -S "api_key" --all

# Should return no results
```

### 2. Update Remote

```bash
# Force push to origin
git push --force --all origin
git push --force --tags origin

# If using multiple remotes, push to all
git remote | xargs -I {} git push --force --all {}
```

### 3. Notify Collaborators

Send this message to team members:

```
⚠️ Git history has been rewritten to remove sensitive data.

Action required:
1. Backup any local uncommitted changes
2. Delete your local repository
3. Re-clone from GitHub:
   git clone https://github.com/fabriziosalmi/trinity.git

DO NOT try to pull or merge - this will not work with rewritten history.
```

### 4. Clean Up Backups

Once confirmed working:

```bash
# Delete local backup branch
git branch -D backup-before-cleanup

# Delete old remote backups (if any)
git push origin --delete backup-before-cleanup
```

## Rollback Procedure

If something goes wrong:

```bash
# Restore from automatic backup
git reset --hard backup-before-cleanup

# Or restore from specific commit (if known)
git reset --hard <commit-sha>

# Force push to restore remote
git push --force --all origin
```

## Prevention

To prevent future leaks:

### 1. Update .gitignore

Already configured in Trinity:

```gitignore
# Secrets and environment
.env
.env.local
.env.*.local
*.key
*.pem
secrets/
```

### 2. Use Pre-commit Hooks

Install `detect-secrets`:

```bash
pip install detect-secrets

# Scan repository
detect-secrets scan > .secrets.baseline

# Add to pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
detect-secrets-hook --baseline .secrets.baseline
EOF

chmod +x .git/hooks/pre-commit
```

### 3. Use Environment Variables

Always use `.env` for configuration:

```bash
# .env (never commit this)
LM_STUDIO_URL=http://192.168.100.12:1234/v1
OPENAI_API_KEY=sk-actual-key-here

# .env.example (commit this)
LM_STUDIO_URL=http://localhost:1234/v1
OPENAI_API_KEY=sk-your-key-here
```

### 4. Use Secrets Manager

Trinity now includes secure secrets management:

```python
from trinity.utils.secrets import secrets_manager

# Store securely in system keyring
secrets_manager.set_secret("openai_api_key", "sk-...")

# Retrieve from keyring
api_key = secrets_manager.get_secret("openai_api_key")
```

## GitHub Security Features

### 1. Enable Secret Scanning

GitHub Settings → Security → Secret scanning:
- ✅ Enable secret scanning
- ✅ Enable push protection
- ✅ Enable secret scanning for users

### 2. Review Security Alerts

Check GitHub Security tab for:
- Leaked secrets
- Dependency vulnerabilities
- Code scanning alerts

### 3. Invalidate Exposed Secrets

If API keys were exposed:
1. Immediately rotate all keys
2. Revoke old keys
3. Update keys in secrets manager
4. Monitor for unauthorized usage

## References

- **git-filter-repo**: https://github.com/newren/git-filter-repo
- **BFG Repo-Cleaner**: https://rtyley.github.io/bfg-repo-cleaner/
- **GitHub Secret Scanning**: https://docs.github.com/en/code-security/secret-scanning
- **detect-secrets**: https://github.com/Yelp/detect-secrets

## Summary

✅ **Completed:**
- Removed hardcoded IPs from all current files
- Created `.env.example` with localhost defaults
- Implemented secrets manager with keyring
- Created automated cleanup script

⚠️ **Still Required:**
- Run cleanup script to purge history
- Force push to remote
- Notify collaborators to re-clone

🔒 **Prevention:**
- Use environment variables
- Use secrets manager
- Enable pre-commit hooks
- Enable GitHub secret scanning
