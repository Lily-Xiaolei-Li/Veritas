# ============================================================================
# Agent B - Makefile
# ============================================================================
#
# Common development tasks for Agent B
#
# Windows users: Install make via chocolatey (choco install make) or use
# Git Bash which includes make. Alternatively, run commands manually.
#
# ============================================================================

.PHONY: help install dev test test-watch lint format docker-check clean \
        frontend-install frontend-dev frontend-build frontend-test frontend-lint frontend-clean \
        install-all dev-all clean-all

# Default target
.DEFAULT_GOAL := help

# ============================================================================
# Help
# ============================================================================

help: ## Show this help message
	@echo "Agent B - Development Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Installation and Setup
# ============================================================================

install: ## Install Python dependencies
	@echo "Installing dependencies..."
	pip install -r backend/requirements.txt
	@echo "✓ Dependencies installed"

install-dev: ## Install development dependencies (linters, formatters, etc.)
	@echo "Installing development dependencies..."
	pip install -r backend/requirements.txt
	pip install ruff black pytest-watch pytest-cov
	@echo "✓ Development dependencies installed"

setup: ## First-time setup (install + create .env)
	@echo "Setting up Agent B..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ Created .env from .env.example"; \
	else \
		echo "✓ .env already exists"; \
	fi
	$(MAKE) install
	@echo "✓ Setup complete"

# ============================================================================
# Development Server
# ============================================================================

dev: ## Start development server with auto-reload
	@echo "Starting development server..."
	uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

dev-log: ## Start development server with verbose logging
	@echo "Starting development server with verbose logging..."
	LOG_LEVEL=DEBUG uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# ============================================================================
# Testing
# ============================================================================

test: ## Run all tests
	@echo "Running tests..."
	pytest backend/tests/ -v

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@echo "Running tests in watch mode..."
	@command -v ptw >/dev/null 2>&1 || { echo "Installing pytest-watch..."; pip install pytest-watch; }
	ptw backend/tests/ -- -v

test-cov: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	pytest backend/tests/ --cov=backend --cov-report=html --cov-report=term
	@echo "✓ Coverage report generated in htmlcov/index.html"

test-unit: ## Run only unit tests
	@echo "Running unit tests..."
	pytest backend/tests/ -v -m "not integration"

test-integration: ## Run only integration tests
	@echo "Running integration tests..."
	pytest backend/tests/ -v -m "integration"

# ============================================================================
# Code Quality
# ============================================================================

lint: ## Run code linters
	@echo "Running linters..."
	@command -v ruff >/dev/null 2>&1 || { echo "Installing ruff..."; pip install ruff; }
	ruff check backend/
	@echo "✓ Linting complete"

format: ## Auto-format code with black
	@echo "Formatting code..."
	@command -v black >/dev/null 2>&1 || { echo "Installing black..."; pip install black; }
	black backend/
	@echo "✓ Formatting complete"

format-check: ## Check if code is formatted (CI)
	@echo "Checking code formatting..."
	@command -v black >/dev/null 2>&1 || { echo "Installing black..."; pip install black; }
	black --check backend/
	@echo "✓ Format check complete"

type-check: ## Run type checker (mypy)
	@echo "Running type checker..."
	@command -v mypy >/dev/null 2>&1 || { echo "Installing mypy..."; pip install mypy; }
	mypy backend/app/ --ignore-missing-imports
	@echo "✓ Type check complete"

# ============================================================================
# Docker and System Checks
# ============================================================================

docker-check: ## Verify Docker installation and permissions
	@echo "Checking Docker status..."
	python -m backend.cli.health

docker-info: ## Show Docker system information
	@echo "Docker system information:"
	docker info

# ============================================================================
# Database (Future - B0.0.2+)
# ============================================================================

db-setup: ## Initialize database (not yet implemented)
	@echo "Database setup not yet implemented (Milestone B0.0.2)"

db-migrate: ## Run database migrations (not yet implemented)
	@echo "Database migrations not yet implemented (Milestone B0.0.2)"

db-reset: ## Reset database (not yet implemented)
	@echo "Database reset not yet implemented (Milestone B0.0.2)"

# ============================================================================
# Cleanup
# ============================================================================

clean: ## Remove cache files and build artifacts
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "✓ Cleanup complete"

clean-all: clean ## Remove cache, build artifacts, and virtual environment
	@echo "Deep cleaning..."
	rm -rf venv/ env/ .venv/ 2>/dev/null || true
	@echo "✓ Deep cleanup complete"

# ============================================================================
# Development Workflow
# ============================================================================

check: lint format-check test ## Run all checks (lint, format, test)
	@echo "✓ All checks passed"

pre-commit: format lint test ## Prepare for commit (format, lint, test)
	@echo "✓ Pre-commit checks complete"

# ============================================================================
# Documentation
# ============================================================================

docs: ## Open documentation in browser
	@echo "Opening documentation..."
	@echo "PRD: file://$(PWD)/PRD.md"
	@echo "Roadmap: file://$(PWD)/roadmap.md"
	@echo "Devlog: file://$(PWD)/devlog.md"

# ============================================================================
# Utility
# ============================================================================

env: ## Show current environment info
	@echo "Environment Information:"
	@echo "  Python version: $$(python --version)"
	@echo "  pip version: $$(pip --version)"
	@echo "  Docker version: $$(docker --version 2>/dev/null || echo 'Not installed')"
	@echo "  Virtual env: $${VIRTUAL_ENV:-Not activated}"
	@echo "  Working dir: $(PWD)"

status: ## Show project status
	@echo "Agent B - Project Status"
	@echo ""
	@echo "Git Status:"
	@git status --short
	@echo ""
	@echo "Recent Commits:"
	@git log --oneline -5
	@echo ""
	@echo "Current Milestone:"
	@grep "Current Milestone:" roadmap.md | head -1

# ============================================================================
# Frontend Commands (B1.0+)
# ============================================================================

frontend-install: ## Install frontend dependencies
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✓ Frontend dependencies installed"

frontend-dev: ## Start frontend development server
	@echo "Starting frontend development server..."
	cd frontend && npm run dev

frontend-build: ## Build frontend for production
	@echo "Building frontend..."
	cd frontend && npm run build
	@echo "✓ Frontend build complete"

frontend-test: ## Run frontend tests
	@echo "Running frontend tests..."
	cd frontend && npm test

frontend-lint: ## Lint frontend code
	@echo "Linting frontend code..."
	cd frontend && npm run lint

frontend-clean: ## Clean frontend build artifacts
	@echo "Cleaning frontend build artifacts..."
	cd frontend && rm -rf .next node_modules
	@echo "✓ Frontend cleaned"

# ============================================================================
# Combined Commands
# ============================================================================

install-all: install frontend-install ## Install all dependencies (backend + frontend)

dev-all: ## Run backend and frontend development servers
	@echo "Starting both backend and frontend..."
	@echo "Backend will run on http://localhost:8000"
	@echo "Frontend will run on http://localhost:3000"
	@echo ""
	@echo "Note: Run these in separate terminals:"
	@echo "  Terminal 1: make dev"
	@echo "  Terminal 2: make frontend-dev"

clean-all: clean frontend-clean ## Clean all build artifacts

# ============================================================================
