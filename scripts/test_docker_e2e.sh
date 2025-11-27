#!/usr/bin/env bash
#
# Docker E2E Test Script
# Tests Trinity inside Docker container to validate production deployment
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_IMAGE="trinity:test"
CONTAINER_NAME="trinity-e2e-test"
TEST_OUTPUT_DIR="./test_docker_output"

# Cleanup function
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
    rm -rf "$TEST_OUTPUT_DIR"
}

# Register cleanup on exit
trap cleanup EXIT

echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Trinity Docker E2E Test Suite                   ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Build Docker image
echo -e "${YELLOW}📦 Step 1: Building Docker image...${NC}"
if docker build -t "$DOCKER_IMAGE" -f Dockerfile.dev .; then
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
else
    echo -e "${RED}❌ Failed to build Docker image${NC}"
    exit 1
fi
echo ""

# Step 2: Test model training in container
echo -e "${YELLOW}🎓 Step 2: Testing model training in container...${NC}"
if docker run --rm \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/models:/app/models" \
    "$DOCKER_IMAGE" \
    python -m trinity.cli train --dataset /app/data/training_dataset.csv; then
    echo -e "${GREEN}✅ Model training successful${NC}"
else
    echo -e "${RED}❌ Model training failed${NC}"
    exit 1
fi
echo ""

# Step 3: Test prediction in container
echo -e "${YELLOW}🔮 Step 3: Testing prediction in container...${NC}"
docker run --rm \
    -v "$(pwd)/models:/app/models" \
    "$DOCKER_IMAGE" \
    python -c "
from trinity.components.predictor import LayoutRiskPredictor
predictor = LayoutRiskPredictor(model_dir='/app/models')
content = {
    'hero': {'title': 'Test', 'subtitle': 'Docker E2E'},
    'body': {'sections': [{'title': 'Section 1', 'content': 'Test content'}]}
}
result = predictor.predict_best_strategy(content)
print(f\"Prediction: {result['recommended_strategy']} (confidence: {result['confidence']:.2%})\")
assert 'recommended_strategy' in result
print('✅ Prediction test passed')
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Prediction test successful${NC}"
else
    echo -e "${RED}❌ Prediction test failed${NC}"
    exit 1
fi
echo ""

# Step 4: Test site build in container
echo -e "${YELLOW}🔨 Step 4: Testing site build in container...${NC}"
mkdir -p "$TEST_OUTPUT_DIR"

# Create test content
cat > "$TEST_OUTPUT_DIR/test_content.json" <<EOF
{
  "hero": {
    "title": "Docker E2E Test Portfolio",
    "subtitle": "Testing Trinity in Docker"
  },
  "body": {
    "sections": [
      {
        "title": "About",
        "content": "This is a test portfolio generated in Docker for E2E testing."
      },
      {
        "title": "Skills",
        "content": "Docker, Python, Machine Learning, CI/CD"
      },
      {
        "title": "Projects",
        "content": "Trinity: AI-powered site generator that works in production."
      }
    ]
  }
}
EOF

# Build site
if docker run --rm \
    -v "$(pwd)/config:/app/config" \
    -v "$(pwd)/library:/app/library" \
    -v "$(pwd)/models:/app/models" \
    -v "$(pwd)/$TEST_OUTPUT_DIR:/app/output" \
    "$DOCKER_IMAGE" \
    python -m trinity.cli build \
        --content /app/output/test_content.json \
        --theme brutalist \
        --output /app/output/docker_test.html; then
    echo -e "${GREEN}✅ Site build successful${NC}"
else
    echo -e "${RED}❌ Site build failed${NC}"
    exit 1
fi
echo ""

# Step 5: Validate output
echo -e "${YELLOW}✅ Step 5: Validating output...${NC}"

if [ -f "$TEST_OUTPUT_DIR/docker_test.html" ]; then
    FILE_SIZE=$(stat -f%z "$TEST_OUTPUT_DIR/docker_test.html" 2>/dev/null || stat -c%s "$TEST_OUTPUT_DIR/docker_test.html" 2>/dev/null)
    echo -e "${GREEN}✅ Output file created: $FILE_SIZE bytes${NC}"
    
    # Check if file contains expected content
    if grep -q "Docker E2E Test Portfolio" "$TEST_OUTPUT_DIR/docker_test.html"; then
        echo -e "${GREEN}✅ Output contains expected content${NC}"
    else
        echo -e "${RED}❌ Output missing expected content${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Output file not found${NC}"
    exit 1
fi
echo ""

# Step 6: Test with Guardian
echo -e "${YELLOW}🛡️  Step 6: Testing with Guardian enabled...${NC}"
if docker run --rm \
    -v "$(pwd)/config:/app/config" \
    -v "$(pwd)/library:/app/library" \
    -v "$(pwd)/models:/app/models" \
    -v "$(pwd)/$TEST_OUTPUT_DIR:/app/output" \
    "$DOCKER_IMAGE" \
    python -m trinity.cli build \
        --content /app/output/test_content.json \
        --theme enterprise \
        --guardian \
        --output /app/output/guardian_test.html; then
    echo -e "${GREEN}✅ Guardian build successful${NC}"
else
    echo -e "${RED}❌ Guardian build failed${NC}"
    exit 1
fi
echo ""

# Step 7: Run pytest in container
echo -e "${YELLOW}🧪 Step 7: Running pytest in container...${NC}"
if docker run --rm \
    -v "$(pwd)/tests:/app/tests" \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/models:/app/models" \
    "$DOCKER_IMAGE" \
    pytest tests/test_multiclass_pipeline.py -v --tb=short; then
    echo -e "${GREEN}✅ Pytest tests passed${NC}"
else
    echo -e "${RED}❌ Pytest tests failed${NC}"
    exit 1
fi
echo ""

# Success summary
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ All Docker E2E Tests Passed!                  ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Test Results:${NC}"
echo -e "  ✅ Docker image build"
echo -e "  ✅ Model training"
echo -e "  ✅ Prediction"
echo -e "  ✅ Site build"
echo -e "  ✅ Output validation"
echo -e "  ✅ Guardian build"
echo -e "  ✅ Pytest suite"
echo ""
echo -e "${YELLOW}📂 Test output saved to: $TEST_OUTPUT_DIR${NC}"
echo -e "${YELLOW}🐳 Docker image: $DOCKER_IMAGE${NC}"
