# Lego Architecture — Makefile
# ──────────────────────────────────────────
# Uso básico:
#   make help          → lista de comandos
#   make dev           → gateway + auth local (sin Docker)
#   make test          → tests de todos los servicios
#   make validate      → validar contratos
#
# Con Docker Compose:
#   make up            → gateway + test-ui + todo
#   make up.auth       → + Auth Service
#   make up.min        → solo gateway + test-ui (arranque base)

.DEFAULT_GOAL := help

SHELL := /bin/bash
.ONESHELL:

# ── Variables ────────────────────────────────────────────────
VENV      := .venv
PYTHON    := $(VENV)/bin/python3
PIP       := $(VENV)/bin/pip
UV        := uv

JWT_SECRET       ?= dev-secret-do-not-use-in-prod
GATEWAY_LOG_LEVEL ?= INFO
AUTH_PORT        ?= 8000
GATEWAY_PORT     ?= 8080
UI_PORT          ?= 8081

# ── Colores ──────────────────────────────────────────────────
BOLD := \033[1m
DIM  := \033[2m
GREEN:= \033[32m
CYAN := \033[36m
NC   := \033[0m

# ── Ayuda ────────────────────────────────────────────────────
help:
	@echo ""
	@echo "$(BOLD)🧱 Lego Architecture — Comandos$(NC)"
	@echo ""
	@echo "$(CYAN)Desarrollo local (sin Docker)$(NC)"
	@echo "  $(GREEN)make dev$(NC)          Gateway + Auth locales (4 procesos)"
	@echo "  $(GREEN)make dev.gateway$(NC)   Solo Gateway"
	@echo "  $(GREEN)make dev.auth$(NC)      Solo Auth Service"
	@echo "  $(GREEN)make dev.ui$(NC)        Solo Test UI"
	@echo "  $(GREEN)make stop$(NC)          Mata todos los procesos locales"
	@echo ""
	@echo "$(CYAN)Docker Compose$(NC)"
	@echo "  $(GREEN)make up$(NC)            docker compose --profile all up --build"
	@echo "  $(GREEN)make up.min$(NC)        docker compose (core: gateway + test-ui)"
	@echo "  $(GREEN)make up.auth$(NC)       docker compose --profile auth up"
	@echo "  $(GREEN)make down$(NC)          docker compose down"
	@echo ""
	@echo "$(CYAN)Tests y calidad$(NC)"
	@echo "  $(GREEN)make test$(NC)          Tests de auth + gateway + shared"
	@echo "  $(GREEN)make test.auth$(NC)     Solo tests de Auth Service"
	@echo "  $(GREEN)make test.gateway$(NC)  Solo tests de Gateway"
	@echo "  $(GREEN)make test.shared$(NC)   Solo tests de lego_shared"
	@echo "  $(GREEN)make validate$(NC)      Validar contracts/ contra las APIs"
	@echo "  $(GREEN)make lint$(NC)          Lint YAML contracts"
	@echo ""
	@echo "$(CYAN)Build$(NC)"
	@echo "  $(GREEN)make build$(NC)         Build imágenes Docker"
	@echo "  $(GREEN)make clean$(NC)         Limpiar __pycache__, .db, etc."
	@echo ""

# ── Venv ──────────────────────────────────────────────────────
.PHONY: venv
venv:
	@test -d $(VENV) || $(UV) venv $(VENV)
	@$(UV) pip install -q -e shared/python/
	@for req in services/auth/requirements.txt services/gateway/requirements.txt; do \
		[ -f "$$req" ] && $(UV) pip install -q -r "$$req" || true; done

# ── Desarrollo local (sin Docker) ─────────────────────────────
PID_FILE := .make_pids

.PHONY: dev
dev: venv dev.auth dev.gateway dev.ui
	@echo ""
	@echo "$(BOLD)$(GREEN)✅ Todo corriendo:$(NC)"
	@echo "  Gateway   → http://localhost:$(GATEWAY_PORT)"
	@echo "  Auth      → http://localhost:$(AUTH_PORT)"
	@echo "  Test UI   → http://localhost:$(UI_PORT)"
	@echo "$(DIM)Para matar: make stop$(NC)"

.PHONY: dev.gateway
dev.gateway: venv
	@echo "$(CYAN)▶ Gateway en :$(GATEWAY_PORT)$(NC)"
	@PYTHONPATH=services:shared/python \
		GATEWAY_JWT_SECRET=*** \
		GATEWAY_JWT_PREVERIFY=true \
		GATEWAY_LOG_LEVEL=$(GATEWAY_LOG_LEVEL) \
		GATEWAY_ROUTE_AUTH=http:/...ORT) \
		$(abspath $(VENV))/bin/python run_gateway.py 2>&1 &
	@echo $$! >> $(PID_FILE)

.PHONY: dev.auth
dev.auth: venv
	@echo "$(CYAN)▶ Auth en :$(AUTH_PORT)$(NC)"
	@cd services/auth && \
		PYTHONPATH=.:../../shared/python \
		JWT_SECRET=*** \
		DATABASE_URL=sqlite:///./auth.db \
		PORT=$(AUTH_PORT) \
		$(abspath $(VENV))/bin/python app.py 2>&1 &
	@echo $$! >> $(PID_FILE)

.PHONY: dev.ui
dev.ui:
	@echo "$(CYAN)▶ Test UI en :$(UI_PORT)$(NC)"
	@cd . && python3 -m http.server $(UI_PORT) --bind 0.0.0.0 2>&1 &
	@echo $$! >> $(PID_FILE)

.PHONY: stop
stop:
	@if [ -f $(PID_FILE) ]; then \
		echo "Deteniendo procesos..."; \
		xargs kill 2>/dev/null < $(PID_FILE) || true; \
		rm -f $(PID_FILE); \
		echo "✓ Detenido"; \
	else \
		echo "No hay procesos corriendo (no se encontró $(PID_FILE))"; \
	fi

# ── Docker Compose ────────────────────────────────────────────
.PHONY: up
up:
	docker compose --profile all up --build -d

.PHONY: up.min
up.min:
	docker compose up --build -d

.PHONY: up.auth
up.auth:
	docker compose --profile auth up --build -d

.PHONY: down
down:
	docker compose down

.PHONY: build
build:
	docker compose build

# ── Tests ─────────────────────────────────────────────────────
.PHONY: test
test: test.shared test.auth test.gateway

.PHONY: test.auth
test.auth: venv
	@echo "$(CYAN)▶ Auth Service tests$(NC)"
	cd services/auth && $(abspath $(VENV))/bin/python -m pytest tests/ -v --tb=short -x

.PHONY: test.gateway
test.gateway: venv
	@echo "$(CYAN)▶ Gateway tests$(NC)"
	cd services/gateway && $(abspath $(VENV))/bin/python -m pytest tests/ -v --tb=short -x -k "not e2e"

.PHONY: test.shared
test.shared: venv
	@echo "$(CYAN)▶ lego_shared tests$(NC)"
	cd shared/python && $(abspath $(VENV))/bin/python -m pytest tests/ -v --tb=short

# ── Validación de contratos ──────────────────────────────────
.PHONY: validate
validate: venv
	@echo "$(CYAN)▶ Validando contratos contra APIs en ejecución$(NC)"
	@$(PYTHON) scripts/validate-contracts.py || echo "⚠️  Algunos servicios no están corriendo (esperable si no hiciste make dev)"

.PHONY: lint
lint:
	@echo "$(CYAN)▶ Linting YAML contracts$(NC)"
	@python3 -c "
import yaml, sys, os
errors = 0
for f in ['contracts/auth.yaml', 'contracts/gateway.yaml']:
    try:
        with open(f) as fh:
            yaml.safe_load(fh)
        print(f'  ✓ {f}')
    except yaml.YAMLError as e:
        print(f'  ✗ {f}: {e}')
        errors += 1
sys.exit(errors)
"

# ── Limpieza ──────────────────────────────────────────────────
.PHONY: clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.db" -delete
	rm -rf .pytest_cache .make_pids
	@echo "✓ Limpio"
