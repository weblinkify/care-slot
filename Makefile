# CareSlot developer entry points. Run `make help` to list targets.
# Every CI step calls one of these targets, so "works on my machine" == "works in CI".

UV ?= uv
BACKEND := cd backend &&
FRONTEND := cd frontend &&

.DEFAULT_GOAL := help
.PHONY: help install env up up-observability down reset logs seed migrate test test-unit test-integration test-contract \
        e2e lint fmt typecheck check openapi

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install backend + frontend dependencies and the git pre-commit hooks
	$(BACKEND) $(UV) sync
	$(FRONTEND) npm ci
	$(BACKEND) $(UV) run pre-commit install

env: ## Create .env with freshly generated local-only encryption keys (if missing)
	@test -f .env || { cp .env.example .env && \
	  echo "CARESLOT_KEKS=v1:$$(openssl rand -base64 32)" >> .env && \
	  echo "CARESLOT_BLIND_INDEX_KEY=$$(openssl rand -base64 32)" >> .env && \
	  echo "Created .env with new random local keys"; }

up: env ## Start the whole stack (db, api, web) with Docker Compose
	docker compose up --build -d
	@echo "API  -> http://localhost:8000/api/v1/docs"
	@echo "Web  -> http://localhost:5173"

up-observability: env ## Start the stack plus Jaeger; traces at http://localhost:16686
	CARESLOT_OTEL_EXPORTER_ENDPOINT=http://jaeger:4318 docker compose --profile observability up --build -d
	@echo "Jaeger -> http://localhost:16686"

down: ## Stop the stack
	docker compose down

reset: ## Wipe local data and start fresh: stop, delete the DB volume, start, migrate, seed
	docker compose down -v
	$(MAKE) up
	@until curl -sf http://localhost:8000/ready >/dev/null; do sleep 2; done
	$(MAKE) seed

logs: ## Tail stack logs
	docker compose logs -f

migrate: ## Apply database migrations (local stack)
	docker compose exec api alembic upgrade head

seed: ## Load synthetic demo data (no real patient data, ever)
	docker compose exec api python -m careslot.seed

test: test-unit test-integration test-contract ## Run all backend tests

test-unit: ## Fast unit tests (no Docker)
	$(BACKEND) $(UV) run pytest tests/unit -q

test-integration: ## Integration tests against real PostgreSQL (Testcontainers)
	$(BACKEND) $(UV) run pytest tests/integration -q -m integration

test-contract: ## API contract tests generated from the OpenAPI spec
	$(BACKEND) $(UV) run pytest tests/contract -q -m contract

openapi: ## Regenerate api/openapi.json and the frontend's TypeScript types from the code
	$(BACKEND) $(UV) run python -m careslot.openapi > ../api/openapi.json
	$(FRONTEND) npm run gen:api

e2e: ## Playwright end-to-end tests (needs `make up`)
	$(FRONTEND) npx playwright test

lint: ## Lint everything (ruff, import boundaries, eslint, prettier)
	$(BACKEND) $(UV) run ruff check . && $(UV) run ruff format --check . && $(UV) run lint-imports
	$(FRONTEND) npm run lint

fmt: ## Auto-format everything
	$(BACKEND) $(UV) run ruff format . && $(UV) run ruff check --fix .
	$(FRONTEND) npm run format

typecheck: ## Static types (mypy strict, tsc strict)
	$(BACKEND) $(UV) run mypy
	$(FRONTEND) npm run typecheck

check: lint typecheck test ## Everything CI runs, locally
