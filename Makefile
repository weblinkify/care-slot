# CareSlot developer entry points. Run `make help` to list targets.
# Every CI step calls one of these targets, so "works on my machine" == "works in CI".

UV ?= uv
BACKEND := cd backend &&
FRONTEND := cd frontend &&

.DEFAULT_GOAL := help
.PHONY: help install up down logs seed migrate test test-unit test-integration test-contract \
        e2e lint fmt typecheck check

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install backend + frontend dependencies
	$(BACKEND) $(UV) sync
	$(FRONTEND) npm ci

up: ## Start the whole stack (db, api, web) with Docker Compose
	@test -f .env || cp .env.example .env
	docker compose up --build -d
	@echo "API  -> http://localhost:8000/api/v1/docs"
	@echo "Web  -> http://localhost:5173"

down: ## Stop the stack
	docker compose down

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
