#!/bin/bash
# dev.sh - Trinity Core Development Helper Script
# Rule #96: Explicit commands with error handling

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_status() {
    echo -e "${BLUE}[Trinity]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Command functions
cmd_start() {
    print_status "Starting Trinity Core services..."
    docker-compose up -d
    
    # Wait for services to be healthy
    print_status "Waiting for services to be ready..."
    sleep 3
    
    # Check health
    cmd_status
}

cmd_stop() {
    print_status "Stopping Trinity Core services..."
    docker-compose down
    print_success "Services stopped"
}

cmd_restart() {
    print_status "Restarting Trinity Core services..."
    docker-compose restart
    sleep 2
    cmd_status
}

cmd_status() {
    print_status "Checking service health..."
    echo ""
    
    # Check builder
    if docker-compose ps trinity-builder | grep -q "Up"; then
        print_success "Builder service: Running"
    else
        print_error "Builder service: Stopped"
    fi
    
    # Check web server
    if docker-compose ps trinity-web | grep -q "Up"; then
        print_success "Web server: Running (http://localhost:8080)"
    else
        print_error "Web server: Stopped"
    fi
    
    # Check LM Studio connection
    echo ""
    print_status "Testing LM Studio connection..."
    if docker-compose exec -T trinity-builder curl -s http://host.docker.internal:1234/v1/models > /dev/null 2>&1; then
        print_success "LM Studio: Connected (http://localhost:1234)"
    else
        print_warning "LM Studio: Not reachable (start LM Studio on host)"
    fi
    
    echo ""
}

cmd_build() {
    local theme="${1:-brutalist}"
    local flags="${2:---demo}"
    
    print_status "Building site with theme: $theme"
    print_status "Command: python main.py $flags --theme $theme"
    
    docker-compose exec trinity-builder python main.py $flags --theme "$theme"
    
    print_success "Build complete! View at: http://localhost:8080"
}

cmd_build_llm() {
    local theme="${1:-brutalist}"
    
    print_status "Building with LLM content generation..."
    print_status "Theme: $theme"
    
    docker-compose exec trinity-builder python main.py --use-llm --theme "$theme"
    
    print_success "LLM build complete! View at: http://localhost:8080"
}

cmd_guardian() {
    local theme="${1:-brutalist}"
    
    print_status "Running Guardian QA inspection..."
    print_status "Theme: $theme"
    
    docker-compose exec trinity-builder python main.py --demo --theme "$theme" --guardian
    
    print_success "Guardian inspection complete!"
}

cmd_chaos() {
    print_status "Running CHAOS TEST with Guardian..."
    print_warning "This test uses intentionally broken content to verify Guardian detection"
    
    docker-compose exec trinity-builder python main.py \
        --static-json \
        --input data/chaos_content.json \
        --theme brutalist \
        --guardian \
        --guardian-only-dom
    
    print_success "Chaos test complete! Check logs for Guardian verdict."
}

cmd_logs() {
    local service="${1:-trinity-builder}"
    
    print_status "Tailing logs for: $service"
    docker-compose logs -f "$service"
}

cmd_shell() {
    print_status "Opening shell in builder container..."
    docker-compose exec trinity-builder /bin/bash
}

cmd_clean() {
    print_status "Cleaning generated files..."
    rm -rf output/*.html
    rm -rf logs/*.log
    print_success "Clean complete"
}

cmd_rebuild() {
    print_status "Rebuilding Docker images..."
    docker-compose build --no-cache
    print_success "Rebuild complete"
}

cmd_help() {
    cat << EOF
Trinity Core - Development Script

USAGE:
    ./dev.sh <command> [arguments]

COMMANDS:
    start               Start all services (builder + web)
    stop                Stop all services
    restart             Restart all services
    status              Check service health and LM Studio connection
    
    build [theme]       Build with demo data (default: brutalist)
    build-llm [theme]   Build with LLM content generation
    guardian [theme]    Run Guardian QA inspection
    chaos               Run chaos test with intentionally broken layout
    
    logs [service]      Tail logs (default: trinity-builder)
    shell               Open bash shell in builder container
    clean               Remove generated files
    rebuild             Rebuild Docker images from scratch
    
    help                Show this help message

EXAMPLES:
    ./dev.sh start
    ./dev.sh build brutalist
    ./dev.sh build-llm editorial
    ./dev.sh guardian brutalist
    ./dev.sh chaos
    ./dev.sh logs trinity-web
    ./dev.sh shell

URLS:
    Web Server:  http://localhost:8080
    LM Studio:   http://localhost:1234

EOF
}

# Main command router
case "${1:-help}" in
    start)      cmd_start ;;
    stop)       cmd_stop ;;
    restart)    cmd_restart ;;
    status)     cmd_status ;;
    build)      cmd_build "$2" "$3" ;;
    build-llm)  cmd_build_llm "$2" ;;
    guardian)   cmd_guardian "$2" ;;
    chaos)      cmd_chaos ;;
    logs)       cmd_logs "$2" ;;
    shell)      cmd_shell ;;
    clean)      cmd_clean ;;
    rebuild)    cmd_rebuild ;;
    help)       cmd_help ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        cmd_help
        exit 1
        ;;
esac
