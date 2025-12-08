SHELL := /bin/bash

.PHONY: help up down restart status test logs infra postgres-up postgres-down keycloak-up keycloak-down backend-up backend-down \
        down-except-keycloak postgres-reset .build .is-up .clean-stale .drop-sdep-database .migrate-sdep-database .load-sdep-test-data \
        .keycloak-wait .keycloak-realm .keycloak-admin .keycloak-roles .keycloak-clients \
        test-security test-str test-ca test test-and-teardown \
        postgres-login postgres-status postgres-status-full \
        backend-logs postgres-logs keycloak-logs kind

.DEFAULT_GOAL := help

# Helpers

.clean-stale: ## Remove stale containers
	@echo "🧹 Cleaning stale containers..."
	@set -a && . .env && set +a && \
	docker ps -a --filter "name=$$APP_PREFIX" --filter "status=exited" -q | xargs -r docker rm -f || true
	@docker-compose rm -f initdb 2>/dev/null || true
	@echo "✅ Stale containers cleaned!"


.drop-sdep-database: ## Drop database
	@set -a && . .env && set +a && \
	echo "🧹 Cleaning database $$POSTGRES_DB_NAME..." && \
	docker exec -i sdep-postgres psql -U $$POSTGRES_SUPER_USER -d postgres < postgres/clean.sql
	@echo "✅ Database cleaned!"

.migrate-sdep-database: ## Migrate database (create/update tables)
	@echo "🔄 Running database migrations..."
	@docker exec -i $$(docker-compose ps -q backend) alembic upgrade head
	@echo "✅ Database migrations completed!"

.load-sdep-test-data: ## Load testdata
	@set -a && . .env && set +a && \
	echo "📊 Loading test data into $$POSTGRES_DB_NAME..." && \
	for sql_file in ./test-data/*.sql; do \
		if [ -f "$$sql_file" ]; then \
			echo "Executing $$sql_file..."; \
			docker exec -i sdep-postgres psql -U $$POSTGRES_SUPER_USER -d $$POSTGRES_DB_NAME < "$$sql_file" || exit 1; \
		fi; \
	done
	@echo "✅ Test data loaded!"

.keycloak-wait: ## Wait until keycloak allows to authenticate
	@echo "🚀 Waiting for keycloak ready..."
	@./keycloak/wait.sh
	@set -a && . .env && . keycloak/.env && set +a && echo "✅ $$KC_BASE_URL"

.keycloak-realm: .keycloak-wait ## Add Keycloak realm (idempotent)
	@set -a && . .env && . keycloak/.env && set +a && ./keycloak/add-realm.sh

.keycloak-admin: .keycloak-realm ## Create app-realm CI/CD account
	@mkdir -p ./tmp
	@set -a && . .env && . keycloak/.env && set +a && \
	KC_APP_REALM_ADMIN_PASSWORD=$$(bash keycloak/add-realm-admin.sh | grep "Client Secret:" | cut -d' ' -f3) && \
	echo "$$KC_APP_REALM_ADMIN_PASSWORD" > ./tmp/KC_APP_REALM_ADMIN_password.txt

.keycloak-roles: .keycloak-admin ## Add Keycloak realm roles
	@set -a && . .env && . keycloak/.env && set +a && \
	export KC_APP_REALM_ADMIN_PASSWORD=$$(cat ./tmp/KC_APP_REALM_ADMIN_password.txt) && \
	./keycloak/add-realm-roles.sh

.keycloak-clients: .keycloak-roles ## Add Keycloak clients from keycloak/clients.yaml
	@set -a && . .env && . keycloak/.env && set +a && \
	export KC_APP_REALM_ADMIN_PASSWORD=$$(cat ./tmp/KC_APP_REALM_ADMIN_password.txt) && \
	./keycloak/add-realm-clients.sh

.is-up: ## Check services running
	@echo "🔍 Checking if services are up..."
	@set -a && . .env && set +a && \
	POSTGRES_STATUS=$$(docker inspect --format='{{.State.Health.Status}}' $$POSTGRES_CONTAINER_NAME 2>&1 | grep -v "^Error" || echo "not-running"); \
	KC_STATUS=$$(docker inspect --format='{{.State.Status}}' $$KC_CONTAINER_NAME 2>&1 | grep -v "^Error" || echo "not-running"); \
	BACKEND_STATUS=$$(docker inspect --format='{{.State.Health.Status}}' $$BACKEND_CONTAINER_NAME 2>&1 | grep -v "^Error" || echo "not-running"); \
	ALL_UP=true; \
	echo ""; \
	printf "  %-15s %s\n" "Postgres:" "$$POSTGRES_STATUS"; \
	if [ "$$POSTGRES_STATUS" != "healthy" ]; then ALL_UP=false; fi; \
	printf "  %-15s %s\n" "Keycloak:" "$$KC_STATUS"; \
	if [ "$$KC_STATUS" != "running" ]; then ALL_UP=false; fi; \
	printf "  %-15s %s\n" "Backend:" "$$BACKEND_STATUS"; \
	if [ "$$BACKEND_STATUS" != "healthy" ]; then ALL_UP=false; fi; \
	echo ""; \
	if [ "$$ALL_UP" = "true" ]; then \
		echo "✅ All services are up and healthy!"; \
		exit 0; \
	else \
		echo "❌ Some services are not healthy!"; \
		echo ""; \
		echo "Please start all services first with:"; \
		echo "  make up"; \
		echo ""; \
		exit 1; \
	fi

.build: ## Build
	@echo "🐳 Building fullstack..."
	docker-compose build
	@echo "✅ Fullstack built successfully!"
	@echo "📊 Images"
	@set -a && . .env && set +a && docker images | grep $$APP_PREFIX

##@ Postgres

postgres-up: .clean-stale ## Start postgres
	@echo "🚀 Starting postgres..."
	docker-compose up -d postgres
	@echo "✅ Postgres started!"

postgres-down: ## Stop and remove postgres (including volumes)
	@echo "🛑 Stopping postgres..."
	docker-compose stop postgres
	docker-compose rm -f -v postgres
	@docker volume rm $$(docker volume ls -q | grep postgres_data) 2>/dev/null || true
	@echo "✅ Postgres stopped, removed, and volumes cleaned!"

postgres-login: ## Login to postgres
	@echo "🔐 Connecting to PostgreSQL..."
	docker exec -it $$(docker-compose ps -q postgres) psql -U postgres -d sdep-data

postgres-status: ## Show postgres tables (SDEP)
	@set -a && . .env && set +a && \
	echo "Showing tables for database $$POSTGRES_DB_NAME..." && \
	docker exec sdep-postgres psql -U $$POSTGRES_DB_USER -d $$POSTGRES_DB_NAME -c "\\dt"
	@echo ""
	@echo "Showing structure of each table..."
	@set -a && . .env && set +a && \
	docker exec sdep-postgres psql -U $$POSTGRES_DB_USER -d $$POSTGRES_DB_NAME -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public'" | \
	while read -r table; do \
		if [ -n "$$table" ]; then \
			echo ""; \
			echo "=== Table: $$table ==="; \
			docker exec sdep-postgres psql -U $$POSTGRES_DB_USER -d $$POSTGRES_DB_NAME -c "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_schema='public' AND table_name='$$table' ORDER BY ordinal_position"; \
		fi; \
	done

postgres-status-full: postgres-status ## Show postgres tables with full details (SDEP)
	@echo ""
	@echo "Showing full structure of each table..."
	@set -a && . .env && set +a && \
	docker exec sdep-postgres psql -U $$POSTGRES_DB_USER -d $$POSTGRES_DB_NAME -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public'" | \
	while read -r table; do \
		if [ -n "$$table" ]; then \
			echo ""; \
			echo "=== Table: $$table (full details) ==="; \
			docker exec sdep-postgres psql -U $$POSTGRES_DB_USER -d $$POSTGRES_DB_NAME -c "\\d+ $$table"; \
		fi; \
	done

postgres-reset: .clean-stale ## Reset postgres (drop, migrate, test data - SDEP)
	@echo "🚀 Resetting sdep-database in postgres ..."
	$(MAKE) --no-print-directory .drop-sdep-database .migrate-sdep-database .load-sdep-test-data
	@echo "✅ SDEP database reset!"

postgres-logs: ## Show postgres logs
	docker-compose logs -f sdep-postgres

##@ Keycloak

keycloak-up: postgres-up ## Start keycloak
	@echo "🚀 Starting keycloak..."
	docker-compose up -d keycloak
	@echo "✅ Keycloak started!"
	@echo "🚀 Configuring keycloak..."
	@$(MAKE) --no-print-directory .keycloak-realm || echo Realm already added
	@$(MAKE) --no-print-directory .keycloak-roles || echo Roles already added
	@$(MAKE) --no-print-directory .keycloak-clients || echo Clients already added
	@echo "✅ Keycloak configured!"

keycloak-down: ## Stop and remove keycloak (including volumes)
	@echo "🛑 Stopping keycloak..."
	docker-compose stop keycloak
	docker-compose rm -f -v keycloak
	@echo "✅ Keycloak stopped, removed, and volumes cleaned!"

keycloak-logs: ## Show keycloak logs
	docker-compose logs -f sdep-keycloak

##@ Backend

backend-up: .build .clean-stale ## Start backend
	@echo "🚀 Starting backend..."
	docker-compose up -d backend
	@echo "✅ Backend started!"

backend-down: ## Stop and remove backend (including volumes)
	@echo "🛑 Stopping backend..."
	docker-compose stop backend
	docker-compose rm -f -v backend
	@echo "✅ Backend stopped, removed, and volumes cleaned!"

backend-logs: ## Show backend logs
	docker-compose logs -f backend

##@ Fullstack (keycloak + postgres + backend)

up: .build .clean-stale ## Start
	@echo "🚀 Starting full-stack..."
	docker-compose up -d
	@echo "✅ Fullstack started!"

	@echo "🚀 Configuring keycloak..."
	@$(MAKE) --no-print-directory .keycloak-realm
	@$(MAKE) --no-print-directory .keycloak-roles
	@$(MAKE) --no-print-directory .keycloak-clients
	@echo "✅ Keycloak configured!"

	@echo "🚀 Initializing database..."
	@$(MAKE) --no-print-directory postgres-reset
	@echo "✅ Database initialized!"

	@echo "🚀 Showing stack status..."
	@$(MAKE) --no-print-directory status
	@echo "✅ Status shown!"

down: ## Stop and remove
	@echo "🛑 Stopping full-stack..."
	docker-compose down -v # Includes volume deletion
	@echo "✅ Fullstack stopped!"

restart: down up ## Stop and start

status: ## Show status
	@echo ""
	@echo "🔍 Images:"BACKEND_TEST_REPO
	@docker-compose ps
	@echo ""
	@echo "🔍 Use these URLs when images are running:"
	@set -a && . .env && set +a && \
	printf "  %-30s %s\n" "Backend API docs:" "$$BACKEND_BASE_URL/api/v0/docs" && \
	printf "  %-30s %s\n" "Backend health:" "$$BACKEND_BASE_URL/api/health" && \
	printf "  %-30s %s\n" "Backend health (restore):" "$$BACKEND_BASE_URL/api/health-br" && \
	printf "  %-30s %s\n" "Keycloak:" "$$KC_BASE_URL/admin"
	@echo ""

logs: ## Show logs
	docker-compose logs -f

##@ Test

test-security: ## Test security (headers, unauthorized, credentials)
	@set -a && . ./.env && set +a && set -o pipefail && \
	OUTPUT_FILE=$$(mktemp) && \
	trap "rm -f $$OUTPUT_FILE" EXIT && \
	echo "🔒 Testing security..." && \
	echo "BACKEND_BASE_URL: $$BACKEND_BASE_URL" && \
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

test-str: .is-up postgres-reset ## Test STR endpoints
	@set -a && . ./.env && set +a && set -o pipefail && \
	OUTPUT_FILE=$$(mktemp) && \
	trap "rm -f $$OUTPUT_FILE" EXIT && \
	echo "🏘️  Testing STR endpoints..." && \
	echo "BACKEND_BASE_URL: $$BACKEND_BASE_URL" && \
	echo "" && \
	if CLIENT_ID=$$STR_CLIENT_ID CLIENT_SECRET=$$STR_CLIENT_SECRET ./test/auth-client.sh; then # Using STR_CLIENT_ID and STR_CLIENT_SECRET from .env \
		echo "✅ STR client authorized"; \
	else \
		echo "❌ STR client authorization failed"; \
		exit 1; \
	fi && \
	./test/health-ping.sh 2>&1 | tee $$OUTPUT_FILE && \
	./test/str-areas.sh 2>&1 | tee $$OUTPUT_FILE && \
	./test/str-activity-data.sh 2>&1 | tee $$OUTPUT_FILE && \
	echo "✅ STR endpoints tested"

test-ca: .is-up test-str ## Test CA endpoints (builds upon test-str)
	@set -a && . ./.env && set +a && set -o pipefail && \
	OUTPUT_FILE=$$(mktemp) && \
	trap "rm -f $$OUTPUT_FILE" EXIT && \
	echo "🏛️  Testing CA endpoints..." && \
	echo "BACKEND_BASE_URL: $$BACKEND_BASE_URL" && \
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

test: .is-up ## Test all
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

##@ Help

help: ## Show help
	@echo "🤖 Make"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
