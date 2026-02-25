.PHONY: install lint test serve docker-up docker-down clean

install:
	pip install -e ".[dev]"

lint:
	ruff check repoman tests

format:
	ruff format repoman tests

type-check:
	mypy repoman --ignore-missing-imports

test:
	pytest tests/unit -v --cov=repoman --cov-report=term-missing

test-all:
	pytest tests/ -v

serve:
	repoman serve

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
