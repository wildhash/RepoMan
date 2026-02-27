.PHONY: install lint test serve docker-up docker-down wait-es demo clean

COMPOSE_API_SERVICE ?= api
DEMO_REPO ?= https://github.com/wildhash/RepoMan
DEMO_ISSUES_LIMIT ?= 25

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

wait-es:
	@for i in $$(seq 1 60); do \
		if curl -fsS "http://localhost:9200" >/dev/null; then \
			exit 0; \
		fi; \
		sleep 2; \
	done; \
	echo "Elasticsearch did not start" >&2; \
	exit 1

demo: docker-up wait-es
	@echo "Using compose service: $(COMPOSE_API_SERVICE)" >&2
	@echo "Demo repo: $(DEMO_REPO) (issues-limit=$(DEMO_ISSUES_LIMIT))" >&2
	docker compose exec -T $(COMPOSE_API_SERVICE) repoman es setup
	docker compose exec -T $(COMPOSE_API_SERVICE) repoman es ingest $(DEMO_REPO) --issues-limit $(DEMO_ISSUES_LIMIT) --analyze

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
