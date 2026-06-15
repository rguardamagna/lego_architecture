FROM python:3.13-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Instalar shared kernel primero
COPY shared/python/ /shared/python/
RUN pip install -e /shared/python/

# Instalar dependencias del service
COPY services/auth/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del service
COPY services/auth/ .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "adapters.flask.app:create_app()"]
