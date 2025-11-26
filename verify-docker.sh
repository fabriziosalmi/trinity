#!/bin/bash
# verify-docker.sh - Verify Docker setup before first run
# Rule #96: Explicit validation with clear error messages

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==============================================================${NC}"
echo -e "${BLUE}Trinity Core - Docker Setup Verification${NC}"
echo -e "${BLUE}==============================================================${NC}"
echo ""

# Check 1: Docker installed
echo -n "Checking Docker installation... "
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
    docker --version
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}ERROR: Docker not found. Install from https://docker.com${NC}"
    exit 1
fi
echo ""

# Check 2: Docker Compose installed
echo -n "Checking Docker Compose... "
if docker compose version &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
    docker compose version
elif command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
    docker-compose --version
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}ERROR: Docker Compose not found${NC}"
    exit 1
fi
echo ""

# Check 3: Docker running
echo -n "Checking Docker daemon... "
if docker info &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}ERROR: Docker daemon not running. Start Docker Desktop.${NC}"
    exit 1
fi
echo ""

# Check 4: Required files
echo -n "Checking required files... "
missing_files=0
for file in Dockerfile.dev docker-compose.yml .dockerignore dev.sh; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}✗${NC}"
        echo -e "${RED}ERROR: Missing $file${NC}"
        missing_files=$((missing_files + 1))
    fi
done

if [ $missing_files -eq 0 ]; then
    echo -e "${GREEN}✓${NC}"
else
    exit 1
fi
echo ""

# Check 5: LM Studio connection (warning only)
echo -n "Checking LM Studio connection... "
if curl -s http://192.168.100.12:1234/v1/models > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
    echo "  LM Studio is running at http://192.168.100.12:1234"
else
    echo -e "${YELLOW}⚠${NC}"
    echo -e "${YELLOW}  WARNING: LM Studio not reachable${NC}"
    echo "  Make sure LM Studio is running for LLM features"
    echo "  You can still use --demo mode without LM Studio"
fi
echo ""

# Check 6: Port availability
echo -n "Checking port 8080 availability... "
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠${NC}"
    echo -e "${YELLOW}  WARNING: Port 8080 is in use${NC}"
    echo "  You may need to change the port in docker-compose.yml"
else
    echo -e "${GREEN}✓${NC}"
fi
echo ""

# Check 7: Disk space
echo -n "Checking disk space... "
available_gb=$(df -h . | awk 'NR==2 {print $4}' | sed 's/G.*//')
if [ "$available_gb" -gt 5 ]; then
    echo -e "${GREEN}✓${NC}"
    echo "  Available space: ${available_gb}GB"
else
    echo -e "${YELLOW}⚠${NC}"
    echo -e "${YELLOW}  WARNING: Low disk space (${available_gb}GB)${NC}"
    echo "  Docker images require ~2-3GB"
fi
echo ""

# Summary
echo -e "${BLUE}==============================================================${NC}"
echo -e "${GREEN}✓ Verification Complete!${NC}"
echo -e "${BLUE}==============================================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Start services:    ./dev.sh start"
echo "  2. Check status:      ./dev.sh status"
echo "  3. Build demo site:   ./dev.sh build brutalist"
echo "  4. View result:       http://localhost:8080"
echo ""
echo "For full documentation, see: docs/DOCKER.md"
echo ""
