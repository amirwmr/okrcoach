ARG PYTHON_VERSION=3.13-alpine

FROM python:${PYTHON_VERSION} AS python-base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# --------------------
FROM python-base AS builder
WORKDIR /app

COPY requirements.txt .

RUN set -eux; \
    apk add --no-cache build-base libpq-dev; \
    python -m venv /opt/venv; \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip; \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt; \
    apk del build-base

# --------------------
FROM python-base AS runtime
ENV PATH="/opt/venv/bin:${PATH}"
WORKDIR /app

RUN set -eux; \
    apk add --no-cache libpq gosu; \
    adduser -D -u 10001 appuser

COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN set -eux; \
    chmod +x /app/entrypoint.sh; \
    chown -R appuser /app

EXPOSE 8000 8001

ENTRYPOINT ["/app/entrypoint.sh"]
