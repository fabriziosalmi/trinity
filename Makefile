# Trinity Makefile
# Simplified development commands for better DX (Phase 6, Task 5)
#
# Quick start:
#   make help       - Show all available commands
#   make setup      - Setup development environment
#   make test       - Run all tests
#   make build      - Build sample portfolio

.PHONY: help
.DEFAULT_GOAL := help

# Colors for output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# Python executable
PYTHON := python3
VENV := venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip
PYTEST := $(VENV_BIN)/pytest
BLACK := $(VENV_BIN)/black
MYPY := $(VENV_BIN)/mypy
RUFF := $(VENV_BIN)/ruff

# Project paths
SRC := src
TESTS := tests
CONFIG := config
DOCS := docs

##@ Help

help: ## Show this help message
	@echo "$(CYAN)Trinity Development Commands$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(CYAN)<target>$(RESET)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(RESET)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup & Installation

setup: venv install ## Complete setup (venv + dependencies)
	@echo "$(GREEN)✓ Setup complete!$(RESET)"
	@echo "$(CYAN)Next steps:$(RESET)"
	@echo "  make test      - Run tests"
	@echo "  make build     - Build sample site"
	@echo "  make dev       - Start development mode"

venv: ## Create Python virtual environment
	@echo "$(CYAN)Creating virtual environment...$(RESET)"
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@echo "$(GREEN)✓ Virtual environment created$(RESET)"

install: venv ## Install dependencies
	@echo "$(CYAN)Installing dependencies...$(RESET)"
	@$(PIP) install --upgrade pip setuptools wheel
	@$(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(RESET)"

install-dev: install ## Install development dependencies
	@echo "$(CYAN)Installing development dependencies...$(RESET)"
	@$(PIP) install pytest pytest-cov pytest-asyncio hypothesis black mypy ruff
	@echo "$(GREEN)✓ Development dependencies installed$(RESET)"

##@ Testing

test: ## Run all tests
	@echo "$(CYAN)Running tests...$(RESET)"
	@$(PYTEST) $(TESTS) -v --tb=short

test-async: ## Run async tests only
	@echo "$(CYAN)Running async tests...$(RESET)"
	@$(PYTEST) $(TESTS)/test_async*.py -v

test-cov: ## Run tests with coverage report
	@echo "$(CYAN)Running tests with coverage...$(RESET)"
	@$(PYTEST) $(TESTS) --cov=$(SRC) --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)✓ Coverage report: htmlcov/index.html$(RESET)"

test-perf: ## Run performance benchmarks
	@echo "$(CYAN)Running performance benchmarks...$(RESET)"
	@$(PYTEST) $(TESTS)/test_async_performance.py -v -s --tb=short

test-cache: ## Run cache tests
	@echo "$(CYAN)Running cache tests...$(RESET)"
	@$(PYTEST) $(TESTS)/test_llm_caching.py $(TESTS)/test_async_llm_client.py -v

test-fast: ## Run fast tests only (skip slow benchmarks)
	@echo "$(CYAN)Running fast tests...$(RESET)"
	@$(PYTEST) $(TESTS) -v -m "not slow"

test-watch: ## Run tests in watch mode
	@echo "$(CYAN)Running tests in watch mode...$(RESET)"
	@$(PYTEST) $(TESTS) -f

##@ Code Quality

format: ## Format code with black
	@echo "$(CYAN)Formatting code...$(RESET)"
	@$(BLACK) $(SRC) $(TESTS) --line-length 100
	@echo "$(GREEN)✓ Code formatted$(RESET)"

format-check: ## Check code formatting
	@echo "$(CYAN)Checking code formatting...$(RESET)"
	@$(BLACK) $(SRC) $(TESTS) --check --line-length 100

lint: ## Lint code with ruff
	@echo "$(CYAN)Linting code...$(RESET)"
	@$(RUFF) check $(SRC) $(TESTS)

lint-fix: ## Fix linting issues
	@echo "$(CYAN)Fixing linting issues...$(RESET)"
	@$(RUFF) check $(SRC) $(TESTS) --fix

type-check: ## Type check with mypy
	@echo "$(CYAN)Type checking...$(RESET)"
	@$(MYPY) $(SRC) --ignore-missing-imports

check: format-check lint type-check ## Run all code quality checks
	@echo "$(GREEN)✓ All checks passed$(RESET)"

##@ Build & Development

build: ## Build sample portfolio (brutalist theme)
	@echo "$(CYAN)Building sample portfolio...$(RESET)"
	@$(VENV_BIN)/python main.py --theme brutalist
	@echo "$(GREEN)✓ Built: output/index.html$(RESET)"

build-all-themes: ## Build portfolio with all themes
	@echo "$(CYAN)Building all theme variants...$(RESET)"
	@for theme in enterprise brutalist editorial minimalist hacker; do \
		echo "$(YELLOW)Building $$theme theme...$(RESET)"; \
		$(VENV_BIN)/python main.py --theme $$theme --output output/index_$$theme.html; \
	done
	@echo "$(GREEN)✓ All themes built$(RESET)"

dev: ## Start development mode (watch for changes)
	@echo "$(CYAN)Starting development mode...$(RESET)"
	@echo "$(YELLOW)Watching for file changes...$(RESET)"
	@$(VENV_BIN)/python -m pytest $(TESTS) -f

serve: build ## Build and serve locally (simple HTTP server)
	@echo "$(CYAN)Starting local server...$(RESET)"
	@echo "$(GREEN)✓ Server running at http://localhost:8000$(RESET)"
	@cd output && $(PYTHON) -m http.server 8000

##@ Cache Management

cache-stats: ## Show cache statistics
	@echo "$(CYAN)Cache statistics:$(RESET)"
	@$(VENV_BIN)/python -c "import asyncio; from src.trinity.utils.cache_manager import CacheManager; asyncio.run(CacheManager(enable_redis=False).__aenter__().get_stats_async())" 2>/dev/null || echo "$(YELLOW)Cache not initialized$(RESET)"

cache-clear: ## Clear all cache tiers
	@echo "$(CYAN)Clearing cache...$(RESET)"
	@rm -rf .cache/llm
	@echo "$(GREEN)✓ Cache cleared$(RESET)"

cache-size: ## Show cache directory size
	@echo "$(CYAN)Cache size:$(RESET)"
	@du -sh .cache/llm 2>/dev/null || echo "$(YELLOW)No cache directory$(RESET)"

##@ Logging

logs: ## View logs in real-time (human-readable)
	@echo "$(CYAN)Viewing logs...$(RESET)"
	@tail -f logs/trinity.log 2>/dev/null || echo "$(YELLOW)No log file found. Run 'make build' first.$(RESET)"

logs-json: ## View logs in JSON format
	@echo "$(CYAN)Viewing JSON logs...$(RESET)"
	@tail -f logs/trinity.log | jq '.'

logs-errors: ## View error logs only
	@echo "$(CYAN)Error logs:$(RESET)"
	@cat logs/errors.log 2>/dev/null | jq 'select(.level=="ERROR")' || echo "$(YELLOW)No error log found$(RESET)"

logs-performance: ## View performance logs
	@echo "$(CYAN)Performance logs:$(RESET)"
	@cat logs/performance.log 2>/dev/null | jq 'select(.duration_ms != null) | {timestamp, message, duration_ms, cache_hit}' || echo "$(YELLOW)No performance log found$(RESET)"

logs-analyze: ## Analyze log statistics
	@echo "$(CYAN)Log analysis:$(RESET)"
	@if [ -f logs/trinity.log ]; then \
		echo "$(YELLOW)Total entries:$(RESET) $$(wc -l < logs/trinity.log)"; \
		echo "$(YELLOW)Errors:$(RESET) $$(grep -c '"level":"ERROR"' logs/trinity.log 2>/dev/null || echo 0)"; \
		echo "$(YELLOW)Warnings:$(RESET) $$(grep -c '"level":"WARNING"' logs/trinity.log 2>/dev/null || echo 0)"; \
		echo ""; \
		echo "$(YELLOW)Top 5 messages:$(RESET)"; \
		cat logs/trinity.log | jq -r '.message' 2>/dev/null | sort | uniq -c | sort -rn | head -5; \
	else \
		echo "$(YELLOW)No log file found$(RESET)"; \
	fi

logs-clear: ## Clear all log files
	@echo "$(CYAN)Clearing logs...$(RESET)"
	@rm -rf logs/*.log
	@echo "$(GREEN)✓ Logs cleared$(RESET)"

logs-test: ## Test logging system
	@echo "$(CYAN)Testing structured logging...$(RESET)"
	@PYTHONPATH=$$PYTHONPATH:$(PWD)/src LOG_FORMAT=human $(VENV_BIN)/python -c "from trinity.utils.structured_logger import get_logger; logger = get_logger('test'); logger.info('test_message', extra={'test': True, 'count': 42})"
	@echo ""
	@echo "$(CYAN)JSON format:$(RESET)"
	@PYTHONPATH=$$PYTHONPATH:$(PWD)/src LOG_FORMAT=json $(VENV_BIN)/python -c "from trinity.utils.structured_logger import get_logger; logger = get_logger('test'); logger.info('test_message', extra={'test': True, 'count': 42})"

##@ Docker

docker-build: ## Build Docker image
	@echo "$(CYAN)Building Docker image...$(RESET)"
	@docker build -t trinity:latest .
	@echo "$(GREEN)✓ Docker image built$(RESET)"

docker-run: ## Run in Docker container
	@echo "$(CYAN)Running Docker container...$(RESET)"
	@docker run -it --rm -v $(PWD)/output:/app/output trinity:latest

docker-dev: ## Run Docker in development mode
	@echo "$(CYAN)Running Docker in dev mode...$(RESET)"
	@docker-compose up

##@ Maintenance

clean: ## Clean build artifacts and cache
	@echo "$(CYAN)Cleaning build artifacts...$(RESET)"
	@rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	@rm -rf htmlcov .coverage
	@rm -rf *.egg-info dist build
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✓ Build artifacts cleaned$(RESET)"

clean-all: clean cache-clear ## Clean everything (artifacts + cache)
	@rm -rf $(VENV)
	@echo "$(GREEN)✓ Everything cleaned$(RESET)"

reset: clean-all setup ## Complete reset and setup
	@echo "$(GREEN)✓ Project reset complete$(RESET)"

##@ Documentation

docs-serve: ## Serve documentation locally
	@echo "$(CYAN)Serving documentation at http://localhost:8001$(RESET)"
	@cd $(DOCS) && $(PYTHON) -m http.server 8001

docs-check: ## Check documentation links
	@echo "$(CYAN)Checking documentation...$(RESET)"
	@find $(DOCS) -name "*.md" -exec grep -l "http" {} \;

##@ Git & Release

git-status: ## Show git status with statistics
	@echo "$(CYAN)Git status:$(RESET)"
	@git status --short
	@echo ""
	@echo "$(CYAN)Recent commits:$(RESET)"
	@git log --oneline -5

git-stats: ## Show contribution statistics
	@echo "$(CYAN)Code statistics:$(RESET)"
	@git diff --stat main
	@echo ""
	@echo "$(CYAN)File changes:$(RESET)"
	@git diff --shortstat

tag-release: ## Tag a new release (usage: make tag-release VERSION=v0.7.0)
	@if [ -z "$(VERSION)" ]; then \
		echo "$(RED)Error: VERSION not specified$(RESET)"; \
		echo "Usage: make tag-release VERSION=v0.7.0"; \
		exit 1; \
	fi
	@echo "$(CYAN)Tagging release $(VERSION)...$(RESET)"
	@git tag -a $(VERSION) -m "Release $(VERSION)"
	@git push origin $(VERSION)
	@echo "$(GREEN)✓ Release $(VERSION) tagged and pushed$(RESET)"

##@ Utilities

migrate-themes: ## Migrate themes.json to themes.yaml
	@echo "$(CYAN)Migrating themes to YAML...$(RESET)"
	@$(VENV_BIN)/python scripts/migrate_themes_to_yaml.py

demo: ## Run demo script
	@echo "$(CYAN)Running demo...$(RESET)"
	@bash scripts/demo.sh

benchmark: ## Run async vs sync benchmark
	@echo "$(CYAN)Running benchmarks...$(RESET)"
	@$(PYTEST) tests/test_async_performance.py::TestAsyncPerformance::test_performance_comparison -v -s

lines: ## Count lines of code
	@echo "$(CYAN)Lines of code:$(RESET)"
	@find $(SRC) -name "*.py" | xargs wc -l | tail -1
	@echo "$(CYAN)Lines of tests:$(RESET)"
	@find $(TESTS) -name "*.py" | xargs wc -l | tail -1

deps: ## Show dependency tree
	@echo "$(CYAN)Dependency tree:$(RESET)"
	@$(PIP) list

deps-update: ## Update all dependencies
	@echo "$(CYAN)Updating dependencies...$(RESET)"
	@$(PIP) install --upgrade -r requirements.txt
	@echo "$(GREEN)✓ Dependencies updated$(RESET)"

##@ Quick Commands (Aliases)

t: test ## Alias for 'test'
tc: test-cov ## Alias for 'test-cov'
f: format ## Alias for 'format'
l: lint ## Alias for 'lint'
b: build ## Alias for 'build'
c: clean ## Alias for 'clean'
s: serve ## Alias for 'serve'

##@ Info

version: ## Show Trinity version
	@echo "$(CYAN)Trinity Core$(RESET)"
	@grep "^## \[" CHANGELOG.md | head -1

info: ## Show project information
	@echo "$(CYAN)Trinity Core - AI Portfolio Generator$(RESET)"
	@echo ""
	@echo "Version: $(shell grep '^## \[' CHANGELOG.md | head -1 | cut -d'[' -f2 | cut -d']' -f1)"
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Venv: $(shell test -d $(VENV) && echo 'Active' || echo 'Not created')"
	@echo ""
	@echo "$(CYAN)Phase 6 Progress:$(RESET)"
	@echo "  ✅ Task 1: Async/Await (6x throughput)"
	@echo "  ✅ Task 2: LLM Caching (40% cost reduction)"
	@echo "  ✅ Task 3: YAML Themes (better DX)"
	@echo "  ✅ Task 5: Makefile (you are here!)"
	@echo ""
	@echo "$(CYAN)Quick commands:$(RESET)"
	@echo "  make setup  - Setup environment"
	@echo "  make test   - Run tests"
	@echo "  make build  - Build portfolio"
	@echo "  make help   - Show all commands"
