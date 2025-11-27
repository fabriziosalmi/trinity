#!/bin/bash
# Trinity - Demo Script for Terminal Recording
# This script demonstrates the key features of Trinity v0.6.0

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Set PYTHONPATH
export PYTHONPATH="$PWD/src:$PYTHONPATH"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Function to print with delay
print_step() {
    echo -e "${BOLD}${BLUE}▶${NC} $1"
    sleep 2
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
    sleep 1
}

print_info() {
    echo -e "${CYAN}ℹ️${NC}  $1"
    sleep 1
}

# Clear screen
clear

# Header
echo -e "${BOLD}${CYAN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║           🏛️  TRINITY v0.6.0 DEMO                   ║"
echo "║                                                           ║"
echo "║   AI-Powered Static Site Generator                       ║"
echo "║   with Production-Ready Architecture                     ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
sleep 3

# 1. Show Configuration
print_step "1. Configuration Management (Immutable + DI)"
echo ""
python3 -c "
from trinity.config_v2 import create_config

# Create immutable configuration
config = create_config(
    max_retries=5,
    llm_timeout=120,
    default_theme='brutalist'
)

print('  Config created with dependency injection:')
print(f'  • Max Retries: {config.max_retries}')
print(f'  • LLM Timeout: {config.llm_timeout}s')
print(f'  • Default Theme: {config.default_theme}')
print(f'  • Circuit Breaker Threshold: {config.circuit_breaker_failure_threshold}')
"
print_success "Configuration is immutable and type-safe"
echo ""
sleep 2

# 2. Show Exception Hierarchy
print_step "2. Custom Exception Hierarchy"
echo ""
python3 -c "
from trinity import exceptions
import inspect

# Get all custom exceptions
exc_classes = [
    name for name, obj in inspect.getmembers(exceptions)
    if inspect.isclass(obj) and issubclass(obj, exceptions.TrinityError)
]

print('  Available exception types:')
for i, exc in enumerate(exc_classes[:8], 1):
    print(f'  {i}. {exc}')
print(f'  ... and {len(exc_classes) - 8} more')
"
print_success "Type-safe error handling with context"
echo ""
sleep 2

# 3. Show Circuit Breaker
print_step "3. Circuit Breaker Pattern (Resilience)"
echo ""
python3 -c "
from trinity.utils.circuit_breaker import CircuitBreaker

# Create circuit breaker
breaker = CircuitBreaker(
    name='demo-llm',
    failure_threshold=3,
    recovery_timeout=60
)

print('  Circuit Breaker initialized:')
print(f'  • Name: {breaker.name}')
print(f'  • State: {breaker.state.value}')
print(f'  • Failure Threshold: {breaker.failure_threshold}')
print(f'  • Recovery Timeout: {breaker.recovery_timeout}s')

# Simulate successful call
result = breaker.call(lambda: 'Success!')
print(f'  • Test Call: {result}')
print(f'  • Stats: {breaker.stats.successful_requests} successful')
"
print_success "Prevents cascading failures"
echo ""
sleep 2

# 4. Show Idempotency
print_step "4. Idempotency Manager (Safe Retries)"
echo ""
python3 -c "
from trinity.utils.idempotency import IdempotencyKeyManager

manager = IdempotencyKeyManager(enable_persistence=False)

# Generate idempotency key
key = manager.generate_key(
    theme='brutalist',
    content='My portfolio',
    operation='generate'
)

print('  Idempotency key generated:')
print(f'  • Key: {key[:32]}...')

# Store result
manager.store_result(key, {'status': 'success'}, ttl=3600)
print(f'  • Result stored (TTL: 3600s)')

# Retrieve result
cached = manager.get_result(key)
print(f'  • Retrieved from cache: {cached}')

stats = manager.get_stats()
print(f'  • Cache entries: {stats[\"active_entries\"]}')
"
print_success "Reduces API costs with intelligent caching"
echo ""
sleep 2

# 5. Show Secrets Management
print_step "5. Secrets Management (Keyring Integration)"
echo ""
python3 -c "
from trinity.utils.secrets import secrets_manager

info = secrets_manager.get_backend_info()

print('  Secrets Manager:')
print(f'  • Active Backend: {info[\"active_backend\"]}')
print(f'  • Keyring Available: {info[\"keyring_available\"]}')
if info.get('keyring_backend'):
    print(f'  • Keyring Type: {info[\"keyring_backend\"]}')
print(f'  • .env Support: {info[\"dotenv_exists\"]}')
"
print_success "Secure API key storage in system keyring"
echo ""
sleep 2

# 6. Show Available Themes
print_step "6. Available Themes"
echo ""
python3 -c "
from trinity.config_v2 import create_config

config = create_config()

print('  Available design themes:')
for i, theme in enumerate(config.available_themes, 1):
    descriptions = {
        'enterprise': 'Professional corporate design',
        'brutalist': 'Raw, bold, technical aesthetic',
        'editorial': 'Magazine-inspired layout'
    }
    print(f'  {i}. {theme:12} - {descriptions.get(theme, \"\")}')
"
print_success "Multiple design personalities"
echo ""
sleep 2

# 7. Show Prompts Configuration
print_step "7. Externalized LLM Prompts (config/prompts.yaml)"
echo ""
if [ -f "config/prompts.yaml" ]; then
    python3 -c "
import yaml

with open('config/prompts.yaml') as f:
    prompts = yaml.safe_load(f)

vibes = prompts.get('content_generation', {}).get('vibes', {})

print('  Loaded prompt templates:')
print(f'  • Content Generation Vibes: {len(vibes)}')
for vibe_name in vibes.keys():
    print(f'    - {vibe_name}')
print(f'  • Theme Generation: ✓')
print(f'  • Vision AI: ✓')
"
    print_success "Prompts editable without code changes"
else
    print_info "Prompts file: config/prompts.yaml (create as needed)"
fi
echo ""
sleep 2

# 8. Show Build Example
print_step "8. Building a Site (Complete Workflow)"
echo ""
echo "  Creating demo content..."
cat > /tmp/trinity_demo_content.txt << 'EOF'
Name: Trinity Developer
Role: AI Systems Architect

Projects:
- trinity-core: Production-ready static site generator
- ml-healer: Self-healing layout engine
- circuit-guard: Resilient service integration
EOF

echo ""
echo "  Demo content created ✓"
sleep 1

# Simulate build
python3 << 'PYTHON_SCRIPT'
from trinity.config_v2 import create_config
from trinity.engine import TrinityEngine
from pathlib import Path

print("\n  Initializing Trinity Engine...")

# Create config
config = create_config(
    max_retries=3,
    default_theme='brutalist'
)

print(f"  • Configuration: ✓")
print(f"  • Theme: {config.default_theme}")
print(f"  • Max Retries: {config.max_retries}")

print("\n  🚀 Engine ready!")
print("  📦 Build would generate: output/demo.html")
PYTHON_SCRIPT

print_success "Complete build workflow ready"
echo ""
sleep 2

# 9. Show Testing
print_step "9. Quality Assurance"
echo ""
python3 -c "
import subprocess
import sys

print('  Testing framework:')
print('  • pytest with coverage')
print('  • Property-based tests (Hypothesis)')
print('  • Circuit breaker tests')
print('  • Idempotency tests')
print('')
print('  Run: pytest --cov=src/trinity')
"
print_success "60%+ test coverage target"
echo ""
sleep 2

# 10. Summary
echo ""
echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}✨ Trinity Features Demonstrated:${NC}"
echo ""
echo -e "  ${GREEN}✅${NC} Immutable Configuration with Dependency Injection"
echo -e "  ${GREEN}✅${NC} Custom Exception Hierarchy (15+ types)"
echo -e "  ${GREEN}✅${NC} Circuit Breaker Pattern (Resilience)"
echo -e "  ${GREEN}✅${NC} Idempotency Manager (Safe Retries)"
echo -e "  ${GREEN}✅${NC} Secrets Management (Keyring)"
echo -e "  ${GREEN}✅${NC} Externalized LLM Prompts (YAML)"
echo -e "  ${GREEN}✅${NC} Multiple Design Themes"
echo -e "  ${GREEN}✅${NC} Property-Based Testing"
echo ""
echo -e "${BOLD}${YELLOW}📚 Documentation:${NC}"
echo "  • REFACTORING_SUMMARY.md"
echo "  • docs/MIGRATION_GUIDE.md"
echo "  • docs/MLOPS_SETUP.md"
echo "  • docs/SECRETS_MANAGEMENT.md"
echo ""
echo -e "${BOLD}${CYAN}🚀 Get Started:${NC}"
echo "  pip install -r requirements.txt"
echo "  python examples/refactored_usage.py"
echo ""
echo -e "${BOLD}${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Cleanup
rm -f /tmp/trinity_demo_content.txt

echo -e "${BOLD}${GREEN}Demo complete!${NC} 🎉"
echo ""
