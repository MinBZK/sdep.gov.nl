.PHONY: install \
        .check-postgres upgrade downgrade revision show-history show-current show-postgres show-postgres-full \
        clean-stale up down \
        test-crud test-services test-api test-security test test-coverage \
        format lint typecheck check \
        clean help

.DEFAULT_GOAL := help

# Load common variables
include ../.env

# Define specific variables
APP_NAME := sdep-backend

##@ Dependency management

install: ## Install dependencies
	@echo "📦 Installing dependencies..."
	uv sync
	@echo "✅ Dependencies installed!"

##@ Alembic

.check-postgres: ## Check if postgres container is running
	@echo "Checking if PostgreSQL container 'sdep-postgres' is running..."
	@if ! docker ps --format "table {{.Names}}" | grep -q "^sdep-postgres$$"; then \
		echo "❌ PostgreSQL container 'sdep-postgres' is not running."; \
		exit 1; \
	fi
	@echo "✅ PostgreSQL container 'sdep-postgres' is running."

upgrade: .check-postgres ## Upgrade
	@export SQLALCHEMY_URL="$(POSTGRES_URL)" && \
	uv run alembic upgrade head

downgrade: .check-postgres ## Downgrade
	@echo "Downgrading database by one revision..."
	@export SQLALCHEMY_URL="$(POSTGRES_URL)" && uv run alembic downgrade -1

revision: .check-postgres ## Create revision
	@echo "Creating new migration revision..."
	@if [ -z "$(MSG)" ]; then \
		echo "Usage: make revision MSG='Description of changes'"; \
		exit 1; \
	fi
	@export SQLALCHEMY_URL="$(POSTGRES_URL)" && uv run alembic revision --autogenerate -m "$(MSG)"

show-current: .check-postgres ## Show current
	@echo "Showing current database revision..."
	@export SQLALCHEMY_URL="$(POSTGRES_URL)" && uv run alembic current

show-history: .check-postgres ## Show history
	@echo "Showing migration history..."
	@export SQLALCHEMY_URL="$(POSTGRES_URL)" && uv run alembic history

show-postgres: .check-postgres ## Smoke test
	@echo "Showing database migration status and tables..."
	@docker exec sdep-postgres psql -U $(POSTGRES_DB_USER) -d $(POSTGRES_DB_NAME) -c "\\dt"
	@echo ""
	@echo "Showing structure of each table..."
	@docker exec sdep-postgres psql -U $(POSTGRES_DB_USER) -d $(POSTGRES_DB_NAME) -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public'" | \
	while read -r table; do \
		if [ -n "$$table" ]; then \
			echo ""; \
			echo "=== Table: $$table ==="; \
			docker exec sdep-postgres psql -U $(POSTGRES_DB_USER) -d $(POSTGRES_DB_NAME) -c "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name='$$table' ORDER BY ordinal_position"; \
		fi; \
	done

show-postgres-full: .check-postgres ## Smoke test (full)
	@echo "Showing database migration status and tables..."
	@docker exec sdep-postgres psql -U $(POSTGRES_DB_USER) -d $(POSTGRES_DB_NAME) -c "\\dt"
	@echo ""
	@echo "Showing structure of each table..."
	@docker exec sdep-postgres psql -U $(POSTGRES_DB_USER) -d $(POSTGRES_DB_NAME) -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public'" | \
	while read -r table; do \
		if [ -n "$$table" ]; then \
			echo ""; \
			echo "=== Table: $$table ==="; \
			docker exec sdep-postgres psql -U $(POSTGRES_DB_USER) -d $(POSTGRES_DB_NAME) -c "\\d+ $$table"; \
		fi; \
	done

##@ Backend

check: ## Format, lint, type check
	@echo "🧪 Checking backend quality..."
	uv run ruff format . ## Format code and auto-fix
	uv run ruff format --check . ## Verify formatting is correct
	uv run ruff check --select I --fix-only . ## Organize imports
	uv run pyright . ## Check typing
	uv run ruff check . ## Lint (check for errors and style issues)
	uvx ty check ## Verify type completeness
	@echo "✅ Quality check completed!"

clean-stale: # Kill any stale uvicorn/backend processes
	@echo "🧹 Cleaning stale backend processes..."
	@# Method 1: Kill by process name pattern
	@ps aux | grep -E "uvicorn.*app.main|python.*uvicorn.*app.main" | grep -v grep | awk '{print $$2}' | while read pid; do \
		USER=$$(ps -o user= -p $$pid 2>/dev/null || echo ""); \
		if [ -n "$$USER" ] && [ "$$USER" != "root" ]; then \
			kill -9 $$pid 2>/dev/null || true; \
		elif [ "$$USER" = "root" ]; then \
			echo "⚠️  Killing root process $$pid - this may require password"; \
			sudo kill -9 $$pid 2>/dev/null || echo "❌ Failed to kill root process $$pid"; \
		fi; \
	done
	@# Method 2: Kill by port using lsof
	@lsof -ti:8000 2>/dev/null | while read pid; do \
		USER=$$(ps -o user= -p $$pid 2>/dev/null || echo ""); \
		if [ -n "$$USER" ] && [ "$$USER" != "root" ]; then \
			kill -9 $$pid 2>/dev/null || true; \
		elif [ "$$USER" = "root" ]; then \
			echo "⚠️  Killing root process $$pid on port 8000 - this may require password"; \
			sudo kill -9 $$pid 2>/dev/null || echo "❌ Failed to kill root process $$pid"; \
		fi; \
	done
	@echo "✅ Stale processes cleaned!"

up: clean-stale ## Start backend
	@# Safety check: prevent running as root
	@if [ "$$(id -u)" = "0" ]; then \
		echo "❌ Error: Do not run uvicorn as root!"; \
		echo "   Please run 'make up' as a regular user, not with sudo."; \
		exit 1; \
	fi
	@echo "🚀 Starting backend..."
	uv run uvicorn app.main:app --reload --no-server-header
	@echo "✅ Backend started!"

down: ## Stop backend
	@echo "🛑 Stopping backend..."
	@PID=$$(pgrep -f "uvicorn app.main:app --reload$$" 2>/dev/null | head -1); \
	if [ -n "$$PID" ]; then \
		kill -TERM $$PID 2>/dev/null && echo "✅ API server stopped!" || echo "Failed to stop API server"; \
	else \
		echo "API server was not running"; \
	fi
	@echo "✅ Backend stopped!"

##@ Unit testing

test-crud: ## Run CRUD tests only
	@echo "🧪 Running CRUD tests..."
	uv run python -m pytest test/crud/ -n auto
	@echo "✅ CRUD tests completed!"

test-services: ## Run service tests only
	@echo "🧪 Running service tests..."
	uv run python -m pytest test/services/ -n auto
	@echo "✅ Service tests completed!"

test-api: ## Run API tests only
	@echo "🧪 Running API tests..."
	uv run python -m pytest test/api/ -n auto
	@echo "✅ API tests completed!"

test-security: ## Run security tests only
	@echo "🧪 Running security tests..."
	uv run python -m pytest test/security/ -n auto
	@echo "✅ Security tests completed!"

test-verbose: ## Run all tests
	@echo "🧪 Running tests... (please wait)"
	uv run python -m pytest -n auto
	@echo "✅ All tests completed!"

test: ## Run all tests (quiet)
	@echo "🧪 Running tests... (please wait)"
	@uv run python -m pytest -n auto -q --tb=line --no-header 2>&1 | tail -20
	@echo "✅ All tests completed!"

test-coverage: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	uv run python -m pytest -n auto --cov=app --cov-report=term-missing --cov-report=html --cov-report=xml
	@echo "✅ Coverage tests completed! Coverage report in htmlcov/"

##@ Housekeeping

clean: ## Clean up generated files
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup completed!"

##@ Help

help: ## Show help
	@echo "🤖 Make"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
