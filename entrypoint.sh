#!/bin/sh
set -e

APP_USER=${APP_USER:-appuser}
PYTHON_BIN=${PYTHON_BIN:-python}

# If running as root, prep writable dirs, run setup tasks, then drop privileges.
if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/staticfiles
    mkdir -p /app/media
    chown -R "$APP_USER:$APP_USER" /app/staticfiles
    chown -R "$APP_USER:$APP_USER" /app/media

    if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
        gosu "$APP_USER" "$PYTHON_BIN" manage.py migrate --noinput
    fi

    if [ "${DJANGO_COLLECTSTATIC:-0}" = "1" ]; then
        gosu "$APP_USER" "$PYTHON_BIN" manage.py collectstatic --noinput
    fi

    chown -R "$APP_USER:$APP_USER" /app/staticfiles
    chown -R "$APP_USER:$APP_USER" /app/media
    exec gosu "$APP_USER" "$@"
fi

# If already non-root (e.g., custom user), just run.
exec "$@"
