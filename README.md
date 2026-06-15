# Lego Architecture

Mono-repo de microservicios standalone pero componibles, construidos con Clean Architecture.

## Filosofía

Cada servicio es independiente — su propia DB, su propia API, su propio ciclo de vida.
Se "ensamblan" vía HTTP + contratos versionados.

```
┌──────────────┐
│   Adapters   │  Flask (in) → repos (out)
├──────────────┤
│   Domain     │  Use cases, entities — 0 dependencias externas
├──────────────┤
│   Ports      │  Interfaces abstractas
└──────────────┘
```

## Servicios

| # | Servicio | Status |
|---|----------|--------|
| P1 | Auth Service | En construcción |
| P1 | API Gateway | Pendiente |
| P2 | User Service | Pendiente |
| P2 | File Service | Pendiente |
| P3 | Notification Service | Pendiente |
| P3 | Payment Service | Pendiente |

## Quickstart

```bash
# Copiar y configurar env
cp .env.example .env

# Levantar auth service
make run-auth

# Correr tests
make test
```

## Stack

- **Python 3.13** + **Flask**
- **PostgreSQL** (interfaz para swap)
- **Docker** + **Docker Compose**
- **pytest** + **TDD** + **100% coverage**
