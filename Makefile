.PHONY: help install dev-install test coverage lint format clean deploy local-test

help:
	@echo "Available commands:"
	@echo "  make install       Install dependencies"
	@echo "  make dev-install   Install dev dependencies"
	@echo "  make test          Run tests"
	@echo "  make coverage      Run tests with coverage report"
	@echo "  make lint          Run linting checks"
	@echo "  make format        Format code with black"
	@echo "  make clean         Clean build artifacts"
	@echo "  make deploy        Deploy to Lambda"
	@echo "  make local-test    Test locally"

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v

coverage:
	pytest tests/ --cov=lambda --cov-report=html

lint:
	flake8 lambda/ tests/
	mypy lambda/

format:
	black lambda/ tests/ scripts/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache build dist *.egg-info
	rm -f lambda-deployment.zip

deploy: clean
	python scripts/deploy.py

local-test:
	python scripts/local_test.py
