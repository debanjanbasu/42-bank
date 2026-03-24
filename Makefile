.PHONY: help install dev test test-quick test-mcp test-a2a lint format typecheck clean docker-build docker-up docker-down mobile-install mobile-start mobile-typecheck

PYTHON := uv run python
PYTEST := uv run pytest

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────────────────────────────

install: ## Install all dependencies (Python + mobile)
	uv sync
	cd mobile && npm install

bootstrap: ## Initialize the database with seed data
	$(PYTHON) bootstrap.py

# ── Development ───────────────────────────────────────────────────────────────

dev: ## Start backend dev server (alice)
	./dev.sh alice

dev-cosmos: ## Start backend with Cosmos emulator
	DB_MODE=cosmos ./dev.sh alice

# ── Testing ───────────────────────────────────────────────────────────────────

test: ## Run all tests
	$(PYTEST) tests/ -v

test-quick: ## Run fast MCP tool tests only
	$(PYTEST) tests/test_mcp_tools.py -v

test-mcp: ## Run MCP-tagged tests
	$(PYTEST) tests/ -m mcp -v

test-a2a: ## Run A2A agent tests
	$(PYTEST) tests/ -m a2a -v

test-cov: ## Run tests with coverage report
	$(PYTEST) tests/ -v --cov=. --cov-report=term-missing --cov-report=html

# ── Code Quality ──────────────────────────────────────────────────────────────

lint: ## Run ruff linter
	uv run ruff check .

format: ## Format code with ruff
	uv run ruff format .

typecheck: ## Run pyright type checker
	uv run pyright

lint-fix: ## Auto-fix lint issues
	uv run ruff check --fix .

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build: ## Build Docker image
	docker build -f Dockerfile -t 42bank:latest .

docker-up: ## Start Cosmos emulator
	docker-compose up -d cosmos-emulator

docker-down: ## Stop all containers
	docker-compose down

docker-logs: ## Tail container logs
	docker-compose logs -f

# ── Mobile ────────────────────────────────────────────────────────────────────

mobile-install: ## Install mobile dependencies
	cd mobile && npm install

mobile-start: ## Start Expo dev server
	cd mobile && npm start

mobile-ios: ## Run on iOS simulator
	cd mobile && npm run ios

mobile-android: ## Run on Android emulator
	cd mobile && npm run android

mobile-typecheck: ## Type check mobile app
	cd mobile && npm run typecheck

mobile-lint: ## Lint mobile app
	cd mobile && npm run lint

mobile-test: ## Run mobile tests
	cd mobile && npm test

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean: ## Remove cache and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage
	@echo "Clean complete."
