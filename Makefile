# Makefile for Kairos: The Context Keeper

.PHONY: help install dev test lint format clean build docker run stop status setup-dev setup-prod

# Default target
help:
	@echo "🌌 Kairos: The Context Keeper - Available Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  setup-dev     Set up development environment"
	@echo "  setup-prod    Set up production environment"
	@echo "  install       Install Python dependencies"
	@echo ""
	@echo "Development Commands:"
	@echo "  dev           Start development server"
	@echo "  test          Run test suite"
	@echo "  lint          Run linting checks"
	@echo "  format        Format code with black"
	@echo "  type-check    Run mypy type checking"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker        Build and run with Docker Compose"
	@echo "  docker-build  Build Docker images"
	@echo "  docker-up     Start all services"
	@echo "  docker-down   Stop all services"
	@echo "  docker-logs   View logs"
	@echo ""
	@echo "Service Commands:"
	@echo "  run           Start Kairos daemon"
	@echo "  stop          Stop Kairos daemon"
	@echo "  status        Check system status"
	@echo "  restart       Restart daemon"
	@echo ""
	@echo "Maintenance Commands:"
	@echo "  clean         Clean build artifacts"
	@echo "  migrate       Run database migrations"
	@echo "  backup        Backup data"
	@echo "  restore       Restore from backup"

# Setup Commands
setup-dev:
	@echo "🛠️ Setting up development environment..."
	python -m venv venv
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	@echo "🗄️ Setting up database..."
	make migrate
	@echo "✅ Development environment ready!"

setup-prod:
	@echo "🚀 Setting up production environment..."
	pip install -r requirements.txt
	@echo "🗄️ Setting up database..."
	make migrate
	@echo "🔧 Running production checks..."
	make test
	@echo "✅ Production environment ready!"

install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

# Development Commands
dev:
	@echo "🚀 Starting development server..."
	python src/main.py --no-detach

test:
	@echo "🧪 Running test suite..."
	pytest tests/ -v --tb=short
	@echo "📊 Running coverage..."
	pytest --cov=src tests/ --cov-report=html

test-unit:
	@echo "🧪 Running unit tests..."
	pytest tests/unit/ -v

test-integration:
	@echo "🧪 Running integration tests..."
	pytest tests/integration/ -v

test-e2e:
	@echo "🧪 Running end-to-end tests..."
	pytest tests/e2e/ -v

lint:
	@echo "🔍 Running linting checks..."
	flake8 src/ tests/ --max-line-length=100
	@echo "📝 Checking code style..."
	black --check src/ tests/
	@echo "🔧 Running isort check..."
	isort --check-only src/ tests/

format:
	@echo "🎨 Formatting code..."
	black src/ tests/
	isort src/ tests/
	@echo "✅ Code formatted!"

type-check:
	@echo "🔍 Running type checks..."
	mypy src/ --ignore-missing-imports

# Docker Commands
docker: docker-build docker-up

docker-build:
	@echo "🐳 Building Docker images..."
	docker-compose build

docker-up:
	@echo "🚀 Starting all services..."
	docker-compose up -d
	@echo "📊 Services starting..."
	docker-compose ps

docker-down:
	@echo "🛑 Stopping all services..."
	docker-compose down

docker-logs:
	@echo "📋 Viewing logs..."
	docker-compose logs -f

docker-clean:
	@echo "🧹 Cleaning Docker resources..."
	docker-compose down -v
	docker system prune -f

# Service Commands
run:
	@echo "🚀 Starting Kairos daemon..."
	python cli.py start

stop:
	@echo "🛑 Stopping Kairos daemon..."
	python cli.py stop

status:
	@echo "📊 Checking system status..."
	python cli.py status

restart:
	@echo "🔄 Restarting Kairos daemon..."
	python cli.py restart

# Database Commands
migrate:
	@echo "🗄️ Running database migrations..."
	python src/db/db_manager.py --migrate

migrate-rollback:
	@echo "🔄 Rolling back last migration..."
	python src/db/db_manager.py --rollback

migrate-status:
	@echo "📊 Checking migration status..."
	python src/db/db_manager.py --status

# Backup and Restore
backup:
	@echo "💾 Creating backup..."
	mkdir -p backups
	timestamp=$$(date +%Y%m%d_%H%M%S) && \
	pg_dump kairos_db > backups/kairos_backup_$$timestamp.sql && \
	cp -r data backups/data_backup_$$timestamp && \
	echo "✅ Backup created: backups/kairos_backup_$$timestamp.sql"

restore:
	@echo "🔄 Restoring from backup..."
	@echo "⚠️  This will overwrite current data!"
	@read -p "Enter backup timestamp (YYYYMMDD_HHMMSS): " timestamp && \
	psql -d kairos_db -f backups/kairos_backup_$$timestamp.sql && \
	rm -rf data && \
	cp -r backups/data_backup_$$timestamp data && \
	echo "✅ Restored from backup: $$timestamp"

# Maintenance Commands
clean:
	@echo "🧹 Cleaning build artifacts..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.log" -delete
	rm -rf build/
	rm -rf dist/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	@echo "✅ Cleaned!"

clean-data:
	@echo "⚠️  This will delete all data!"
	@read -p "Are you sure? [y/N]: " confirm && \
	if [ "$$confirm" = "y" ]; then \
		rm -rf data/; \
		echo "✅ Data cleaned!"; \
	else \
		echo "❌ Cancelled"; \
	fi

# Monitoring Commands
logs:
	@echo "📋 Viewing application logs..."
	tail -f kairos.log

logs-error:
	@echo "❌ Viewing error logs..."
	grep ERROR kairos.log | tail -20

monitor:
	@echo "📊 Starting monitoring..."
	@echo "Dashboard: http://localhost:8000/dashboard"  
	@echo "Grafana: http://localhost:3001"
	@echo "Prometheus: http://localhost:9091"

# Performance Commands
benchmark:
	@echo "⚡ Running performance benchmarks..."
	python scripts/benchmark.py

profile:
	@echo "📈 Profiling application..."
	python -m cProfile -o profile.stats src/main.py &
	sleep 30
	kill %%
	python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

# Plugin Commands
plugin-list:
	@echo "🔌 Listing available plugins..."
	python -c "from src.plugins.plugin_loader import PluginLoader; pl = PluginLoader(); print(pl.discover_plugins())"

plugin-install:
	@echo "🔌 Installing plugin..."
	@read -p "Enter plugin name: " name && \
	cp plugins/$$name src/plugins/ -r && \
	echo "✅ Plugin $$name installed"

# Security Commands
security-scan:
	@echo "🔒 Running security scan..."
	bandit -r src/ -f json -o security_report.json
	safety check

update-deps:
	@echo "📦 Updating dependencies..."
	pip-review --auto
	pip freeze > requirements.txt

# Documentation Commands
docs:
	@echo "📚 Building documentation..."
	mkdocs build
	@echo "✅ Documentation built in site/"

docs-serve:
	@echo "📚 Serving documentation..."
	mkdocs serve

docs-deploy:
	@echo "🚀 Deploying documentation..."
	mkdocs gh-deploy

# Release Commands
release-check:
	@echo "🔍 Checking release readiness..."
	make lint
	make test
	make security-scan
	@echo "✅ Release ready!"

release-build:
	@echo "📦 Building release..."
	python setup.py sdist bdist_wheel
	@echo "✅ Release built in dist/"

release-upload:
	@echo "🚀 Uploading to PyPI..."
	twine upload dist/*

# Development Tools
shell:
	@echo "🐚 Starting interactive shell..."
	python -c "from src.main import *; import IPython; IPython.embed()"

debug:
	@echo "🐛 Starting in debug mode..."
	KAIROS_DEBUG=1 python src/main.py --no-detach

# Quick Commands
quick-start: install migrate run
quick-stop: stop clean
quick-reset: stop clean-data migrate run

# Version Commands
version:
	@echo "📌 Current version:"
	@python -c "from src.config_loader import config; print(config.get('general.version', '0.5.0'))"

version-bump:
	@echo "📈 Bumping version..."
	@python scripts/bump_version.py

# Environment Commands
env-check:
	@echo "🔍 Checking environment..."
	@python scripts/env_check.py

env-export:
	@echo "📋 Exporting environment..."
	pip freeze > requirements-frozen.txt
	@echo "Environment exported to requirements-frozen.txt"
