#!/bin/bash
# Trinity Core - Git History Cleanup Script
# This script removes sensitive data from git history using git-filter-repo

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}⚠️  Trinity Core - Git History Cleanup${NC}"
echo ""
echo "This script will remove sensitive data from git history:"
echo "  • Hardcoded IP addresses (192.168.100.12)"
echo "  • API keys and secrets (if any)"
echo "  • Passwords and tokens (if any)"
echo ""
echo -e "${RED}WARNING: This will rewrite git history!${NC}"
echo "  • All commit SHAs will change"
echo "  • You'll need to force push to remote"
echo "  • Collaborators will need to re-clone"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

# Check if git-filter-repo is installed
if ! command -v git-filter-repo &> /dev/null; then
    echo -e "${YELLOW}Installing git-filter-repo...${NC}"
    pip install git-filter-repo
fi

# Backup current branch
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${GREEN}Creating backup branch: backup-before-cleanup${NC}"
git branch -f backup-before-cleanup

# Create expressions file for sensitive data
cat > /tmp/trinity-sensitive-patterns.txt << 'EOF'
# IP addresses
regex:192\.168\.100\.12==>localhost
regex:192\.168\.\d{1,3}\.\d{1,3}==>localhost

# Common secret patterns (if found)
regex:api[_-]?key\s*[=:]\s*["']?[a-zA-Z0-9_-]{32,}["']?==>api_key=REDACTED
regex:password\s*[=:]\s*["']?[^"'\s]{8,}["']?==>password=REDACTED
regex:token\s*[=:]\s*["']?[a-zA-Z0-9_-]{20,}["']?==>token=REDACTED
regex:sk-[a-zA-Z0-9]{32,}==>sk-REDACTED
EOF

echo -e "${GREEN}Running git-filter-repo to clean history...${NC}"
git-filter-repo --replace-text /tmp/trinity-sensitive-patterns.txt --force

# Clean up
rm /tmp/trinity-sensitive-patterns.txt

echo ""
echo -e "${GREEN}✅ Git history cleaned!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review the changes: git log --all --oneline"
echo "  2. Test the repository: ./scripts/demo.sh"
echo "  3. Force push to remote: git push --force --all"
echo "  4. Force push tags: git push --force --tags"
echo ""
echo "To restore from backup if needed:"
echo "  git reset --hard backup-before-cleanup"
echo ""
echo -e "${YELLOW}⚠️  Remember to notify collaborators to re-clone!${NC}"
