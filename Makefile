.PHONY: install test run run-auth clean

SERVICE ?= auth

install:
	cd services/$(SERVICE) && pip install -r requirements.txt
	pip install -e shared/python/

install-all:
	@for dir in services/*/; do \
		echo "Installing $$dir..."; \
		cd $$dir && pip install -r requirements.txt; \
		cd ../..; \
	done
	pip install -e shared/python/

test:
	cd services/$(SERVICE) && python -m pytest tests/ -v --cov=domain --cov=adapters --cov-report=term --cov-report=html

test-auth:
	cd services/auth && python -m pytest tests/ -v --cov=domain --cov=adapters --cov-report=term

run:
	cd services/$(SERVICE) && python -m flask run --port 8000

run-auth:
	docker compose -f docker-compose.auth.yml up --build

run-auth-db:
	docker compose -f docker-compose.auth.yml up -d auth-db

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .egg-info -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage coverage.xml
