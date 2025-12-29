# SetuPranali - Development Commands
# Usage: make <target>

.PHONY: help install dev test lint format typecheck clean docker-build docker-run docs

# Default target
help:
	@echo "SetuPranali - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install      Install production dependencies"
	@echo "  make dev          Install all dependencies (including dev)"
	@echo ""
	@echo "Development:"
	@echo "  make run          Start development server"
	@echo "  make test         Run test suite"
	@echo "  make test-cov     Run tests with coverage"
	@echo "  make lint         Run linters (black, isort, flake8)"
	@echo "  make format       Auto-format code"
	@echo "  make typecheck    Run type checker (mypy)"
	@echo "  make check        Run all checks (lint + typecheck + test)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build Build Docker image"
	@echo "  make docker-run   Run with Docker Compose"
	@echo "  make docker-stop  Stop Docker Compose"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs         Serve documentation locally"
	@echo "  make docs-build   Build documentation"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean        Remove build artifacts"

# =============================================================================
# Setup
# =============================================================================

install:
	pip install -r requirements.txt

dev: install
	pip install -r requirements-dev.txt
	pip install -r requirements-docs.txt
	pre-commit install

# =============================================================================
# Development
# =============================================================================

run:
	uvicorn app.main:app --reload --port 8080

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

lint:
	black --check app/ tests/
	isort --check-only app/ tests/
	flake8 app/ tests/

format:
	black app/ tests/
	isort app/ tests/

typecheck:
	mypy app/ --ignore-missing-imports

check: lint typecheck test

# =============================================================================
# Docker
# =============================================================================

docker-build:
	docker build -t setupranali/connector:dev .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

# =============================================================================
# Documentation
# =============================================================================

docs:
	mkdocs serve

docs-build:
	mkdocs build

# =============================================================================
# Cleanup
# =============================================================================

clean:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	rm -rf site
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# =============================================================================
# Release (for maintainers)
# =============================================================================

release-patch:
	@echo "Bump patch version and create tag"
	@echo "TODO: Implement version bumping"

release-minor:
	@echo "Bump minor version and create tag"
	@echo "TODO: Implement version bumping"

release-major:
	@echo "Bump major version and create tag"
	@echo "TODO: Implement version bumping"

