.PHONY: help install dev test lint format type-check dashboard api docker-up docker-down clean

# Default target
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Setup
# ============================================================================

install: ## Install production dependencies
	pip install -e .

dev: ## Install dev + production dependencies
	pip install -e ".[dev,collab]"
	pre-commit install

# ============================================================================
# Quality
# ============================================================================

test: ## Run test suite
	pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage report
	pytest tests/ -v --cov=scrapers --cov=services --cov-report=html --cov-report=term

lint: ## Run linter (ruff)
	ruff check scrapers/ services/ tests/

format: ## Format code (black + ruff fix)
	black scrapers/ services/ tests/
	ruff check --fix scrapers/ services/ tests/

type-check: ## Run mypy type checker
	mypy scrapers/ services/

check: lint type-check test ## Run all checks (lint + type-check + test)

# ============================================================================
# Services
# ============================================================================

dashboard: ## Run Plotly Dash dashboard (http://127.0.0.1:8050)
	python -m services.dashboard.app

api: ## Run FastAPI server (http://127.0.0.1:8000)
	uvicorn services.api.main:app --reload --host 127.0.0.1 --port 8000

# ============================================================================
# Docker
# ============================================================================

docker-up: ## Start all services (PostgreSQL, LocalStack, dashboard, API)
	docker compose up -d

docker-down: ## Stop all services
	docker compose down

docker-logs: ## Tail logs from all services
	docker compose logs -f

# ============================================================================
# Database
# ============================================================================

db-migrate: ## Run Alembic migrations
	alembic upgrade head

db-rollback: ## Rollback last migration
	alembic downgrade -1

db-revision: ## Create a new migration (usage: make db-revision msg="add xyz table")
	alembic revision --autogenerate -m "$(msg)"

# ============================================================================
# Data
# ============================================================================

scrape-catalog: ## Run all catalog scrapers
	python -m scrapers.wine_society.catalog_scraper
	python -m scrapers.berry_bros.catalog_scraper
	python -m scrapers.majestic.catalog_scraper

import-csv: ## Import Wine Society CSV export
	python -m scrapers.wine_society.csv_importer

# ============================================================================
# Cleanup
# ============================================================================

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info/ htmlcov/ .coverage
