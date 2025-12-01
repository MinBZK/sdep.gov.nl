SHELL := /bin/bash

.PHONY: help build up down restart status test logs infra postgres keycloak backend-up backend-down \
        down-except-keycloak postgres-reset .clean-stale .drop-database .migrate-database .load-test-data \
        .wait-keycloak keycloak-realm keycloak-roles keycloak-clients \
        test-security test-str test-ca test test-and-teardown \
        postgres-login postgres-status postgres-status-full \
        backend-logs postgres-logs keycloak-logs kind

.DEFAULT_GOAL := help

# Load environment variables
include .env

# Helpers

.clean-stale: ## Remove stale containers
	@echo "🧹 Cleaning stale containers..."
	@docker ps -a --filter "name=$(APP_PREFIX)" --filter "status=exited" -q | xargs -r docker rm -f || true
	@docker-compose rm -f initdb 2>/dev/null || true
	@echo "✅ Stale containers cleaned!"

.wait-keycloak: ## Wait for keycloak
	@./keycloak/wait.sh

##@ Postgres

postgres: build .clean-stale ## Start postgres only
	@echo "🚀 Starting postgres..."
	docker-compose up -d postgres
	@echo "✅ Postgres started!"
	@echo "🚀 Showing postgres status..."
	@$(MAKE) --no-print-directory status
	@echo "✅ Postgres status shown!"

postgres-login: ## Login to PostgreSQL database
	@echo "🔐 Connecting to PostgreSQL..."
	docker exec -it $$(docker-compose ps -q postgres) psql -U postgres -d sdep-data

postgres-status: ## Show postgres tables with column info
	@echo "Showing tables for database $(POSTGRES_DB_NAME)..."
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

postgres-status-full: ## Show postgres tables with full details
	@echo "Showing tables and indexes for database $(POSTGRES_DB_NAME)..."
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

postgres-reset: .clean-stale ## Reset postgres (drop, migrate, master data, test data)
	@echo "🚀 Resetting database ..."
	$(MAKE) --no-print-directory .drop-database .migrate-database .load-test-data
	@echo "✅ Database reset!"

postgres-logs: ## Show postgres logs
	docker-compose logs -f sdep-postgres

##@ Keycloak

keycloak: build .clean-stale ## Start keycloak only
	@echo "🚀 Starting keycloak..."
	docker-compose up -d keycloak
	@echo "✅ Keycloak started!"
	@echo "🚀 Configuring keycloak..."
	@$(MAKE) --no-print-directory keycloak-realm || echo Realm already added
	@$(MAKE) --no-print-directory keycloak-roles || echo Roles already added
	@$(MAKE) --no-print-directory keycloak-clients || echo Clients already added
	@echo "✅ Keycloak configured!"
	@echo "🚀 Showing keycloak status..."
	@$(MAKE) --no-print-directory status
	@echo "✅ Keycloak status shown!"

keycloak-realm: .wait-keycloak ## Add Keycloak realm (idempotent)
	@./keycloak/add-realm.sh

keycloak-roles: .wait-keycloak ## Add Keycloak realm roles
	@./keycloak/add-roles.sh

keycloak-clients: keycloak-roles ## Add Keycloak clients from keycloak/client.yaml
	@./keycloak/add-clients.sh

keycloak-logs: ## Show keycloak logs
	docker-compose logs -f sdep-keycloak

infra: postgres keycloak ## Start postgres and keycloak

##@ Backend

backend-up: build .clean-stale ## Start backend only (force restart)
	@echo "🚀 Starting backend..."
	docker-compose up -d backend
	@echo "✅ Backend started!"

backend-down: ## Stop and remove backend only
	@echo "🛑 Stopping backend..."
	docker-compose stop backend
	docker-compose rm -f backend
	@echo "✅ Backend stopped and removed!"

.drop-database: ## Helper to drop database tables
	@echo "🧹 Cleaning database $(POSTGRES_DB_NAME)..."
	@docker exec -i sdep-postgres psql -U $(POSTGRES_SUPER_USER) -d postgres < postgres/clean.sql
	@echo "✅ Database cleaned!"

.migrate-database: ## Helper to migrate the database (create/update tables)
	@echo "🔄 Running database migrations..."
	@docker exec -i $$(docker-compose ps -q backend) alembic upgrade head
	@echo "✅ Database migrations completed!"

.load-test-data: ## Helper to load testdata
	@echo "📊 Loading test data into $(POSTGRES_DB_NAME)..."
	@for sql_file in ./test-data/*.sql; do \
		if [ -f "$$sql_file" ]; then \
			echo "Executing $$sql_file..."; \
			docker exec -i sdep-postgres psql -U $(POSTGRES_SUPER_USER) -d $(POSTGRES_DB_NAME) < "$$sql_file" || exit 1; \
		fi; \
	done
	@echo "✅ Test data loaded!"

backend-logs: ## Show backend logs
	docker-compose logs -f backend

##@ Fullstack (infra + backend + database)

build: ## Build
	@echo "🐳 Building fullstack..."
	docker-compose build
	@echo "✅ Fullstack built successfully!"
	@echo "📊 Images"
	docker images | grep $(APP_PREFIX)

up: build .clean-stale ## Start
	@echo "🚀 Starting full-stack..."
	docker-compose up -d
	@echo "✅ Fullstack started!"

	@echo "🚀 Configuring keycloak..."
	@$(MAKE) --no-print-directory keycloak-realm
	@$(MAKE) --no-print-directory keycloak-roles
	@$(MAKE) --no-print-directory keycloak-clients
	@echo "✅ Keycloak configured!"

	@echo "🚀 Initializing database..."
	@$(MAKE) --no-print-directory postgres-reset
	@echo "✅ Database initialized!"

	@echo "🚀 Showing stack status..."
	@$(MAKE) --no-print-directory status
	@echo "✅ Stack status shown!"

down: ## Stop
	@echo "🛑 Stopping full-stack..."
	docker-compose down -v # Includes volume deletion
	@echo "✅ Fullstack stopped!"

down-except-keycloak: ## Stop (but keep keycloak running)
	@echo "🛑 Stopping full-stack (except keycloak)..."
	docker-compose stop backend postgres
	docker-compose rm -f backend
	@echo "✅ Fullstack stopped! (but kept keycloak running)"

restart: down up ## Down and up

status: ## Show status
	@echo ""
	@echo "🔍 Images:"BACKEND_TEST_REPO
	@docker-compose ps
	@echo ""
	@echo "🔍 Use these URLs when images are running:"
	@printf "  %-30s %s\n" "Backend API docs:" "${BACKEND_BASE_URL}/api/v0/docs"
	@printf "  %-30s %s\n" "Backend health:" "${BACKEND_BASE_URL}/api/health"
	@printf "  %-30s %s\n" "Backend health (restore):" "${BACKEND_BASE_URL}/api/health-br"
	@printf "  %-30s %s\n" "Keycloak:" "${KEYCLOAK_BASE_URL}/admin"
	@echo ""

logs: ## Show logs
	docker-compose logs -f

##@ Test

test-security: ## Test security (headers, unauthorized, credentials)
	@set -a && . ./.env && set +a && set -o pipefail && \
	OUTPUT_FILE=$$(mktemp) && \
	trap "rm -f $$OUTPUT_FILE" EXIT && \
	echo "🔒 Testing security..." && \
	echo "BACKEND_BASE_URL: $(BACKEND_BASE_URL)" && \
	echo "" && \
	echo "Testing security headers..." && \
	./test/auth-headers.sh 2>&1 | tee $$OUTPUT_FILE && \
	echo "" && \
	echo "Testing unauthorized access..." && \
	./test/auth-unauthorized.sh 2>&1 | tee $$OUTPUT_FILE && \
	echo "" && \
	echo "Testing credentials..." && \
	./test/auth-credentials.sh 2>&1 | tee $$OUTPUT_FILE && \
	echo "✅ Security tested"

test-str: ## Test STR endpoints
	@set -a && . ./.env && set +a && set -o pipefail && \
	OUTPUT_FILE=$$(mktemp) && \
	trap "rm -f $$OUTPUT_FILE" EXIT && \
	echo "🏘️  Testing STR endpoints..." && \
	echo "BACKEND_BASE_URL: $(BACKEND_BASE_URL)" && \
	echo "" && \
	if CLIENT_ID=$$STR_CLIENT_ID CLIENT_SECRET=$$STR_CLIENT_SECRET ./test/auth-client.sh; then \
		echo "✅ STR client authorized"; \
	else \
		echo "❌ STR client authorization failed"; \
		exit 1; \
	fi && \
	./test/health-ping.sh 2>&1 | tee $$OUTPUT_FILE && \
	./test/str-areas.sh 2>&1 | tee $$OUTPUT_FILE && \
	./test/str-activity-data.sh 2>&1 | tee $$OUTPUT_FILE && \
	echo "✅ STR endpoints tested"

test-ca: ## Test CA endpoints
	@set -a && . ./.env && set +a && set -o pipefail && \
	OUTPUT_FILE=$$(mktemp) && \
	trap "rm -f $$OUTPUT_FILE" EXIT && \
	echo "🏛️  Testing CA endpoints..." && \
	echo "BACKEND_BASE_URL: $(BACKEND_BASE_URL)" && \
	echo "" && \
	if CLIENT_ID=$$CA_CLIENT_ID CLIENT_SECRET=$$CA_CLIENT_SECRET ./test/auth-client.sh; then \
		echo "✅ CA client authorized"; \
	else \
		echo "❌ CA client authorization failed"; \
		exit 1; \
	fi && \
	./test/health-ping.sh 2>&1 | tee $$OUTPUT_FILE && \
	./test/ca-activity-data.sh 2>&1 | tee $$OUTPUT_FILE && \
	echo "✅ CA endpoints tested"

test: up ## Test all and stay up (up, test)
	@set -a && . ./.env && set +a && set -o pipefail && \
	RESULTS_FILE=$$(mktemp) && \
	FAILED_TESTS_FILE=$$(mktemp) && \
	OUTPUT_FILE=$$(mktemp) && \
	trap "rm -f $$RESULTS_FILE $$FAILED_TESTS_FILE $$OUTPUT_FILE" EXIT && \
	echo "🧪 Running all tests..." && \
	echo "" && \
	if $(MAKE) --no-print-directory test-security 2>&1 | tee $$OUTPUT_FILE; then \
		grep -E "^\s*(Total|Passed|Failed):" $$OUTPUT_FILE >> $$RESULTS_FILE || true; \
	else \
		grep -E "^\s*(Total|Passed|Failed):" $$OUTPUT_FILE >> $$RESULTS_FILE || true; \
		echo "test-security" >> $$FAILED_TESTS_FILE; \
	fi && \
	echo "" && \
	if $(MAKE) --no-print-directory test-str 2>&1 | tee $$OUTPUT_FILE; then \
		grep -E "^\s*(Total|Passed|Failed):" $$OUTPUT_FILE >> $$RESULTS_FILE || true; \
	else \
		grep -E "^\s*(Total|Passed|Failed):" $$OUTPUT_FILE >> $$RESULTS_FILE || true; \
		echo "test-str" >> $$FAILED_TESTS_FILE; \
	fi && \
	echo "" && \
	if $(MAKE) --no-print-directory test-ca 2>&1 | tee $$OUTPUT_FILE; then \
		grep -E "^\s*(Total|Passed|Failed):" $$OUTPUT_FILE >> $$RESULTS_FILE || true; \
	else \
		grep -E "^\s*(Total|Passed|Failed):" $$OUTPUT_FILE >> $$RESULTS_FILE || true; \
		echo "test-ca" >> $$FAILED_TESTS_FILE; \
	fi && \
	GRAND_TOTAL=$$(grep "Total:" $$RESULTS_FILE 2>/dev/null | awk '{sum += $$2} END {print sum+0}') && \
	GRAND_PASSED=$$(grep "Passed:" $$RESULTS_FILE 2>/dev/null | awk '{sum += $$2} END {print sum+0}') && \
	GRAND_FAILED=$$(grep "Failed:" $$RESULTS_FILE 2>/dev/null | awk '{sum += $$2} END {print sum+0}') && \
	echo "" && \
	echo "════════════════════════════════════════════" && \
	echo "GRAND TOTAL - All Tests:" && \
	echo "  Test suites:	$$GRAND_TOTAL" && \
	echo "  Tests passed:	$$GRAND_PASSED ✅" && \
	echo "  Tests failed: $$GRAND_FAILED ❌" && \
	echo "════════════════════════════════════════════" && \
	if [ -s $$FAILED_TESTS_FILE ]; then \
		echo "" && \
		echo "Failed test suites:" && \
		cat $$FAILED_TESTS_FILE | while read test; do echo "  ❌ $$test"; done && \
		echo "" && \
		echo "❌ Some tests failed!" && \
		exit 1; \
	else \
		echo "✅ All tests passed!"; \
	fi

test-and-teardown: down test down ## Test all and tear-town (down, up, test, down)

##@ Kind

kind: ## Load fullstack images into Kind
	@echo "🐳 Loading fullstack..."
	kind load docker-image ${BACKEND_IMAGE_NAME}:${BACKEND_IMAGE_VERSION}
	@echo "✅ Docker image loaded: $(BACKEND_IMAGE_NAME):$(BACKEND_IMAGE_VERSION)"
	@echo "📤 Take next steps in sdep-deployment"

##@ Help

help: ## Show help
	@echo "🤖 Make"
	@echo ""
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
