# Simple justfile to manage docker-compose workflows

set shell := ["/bin/sh", "-c"]

compose_cmd := "docker compose"

# Build and start the stack
up:
	{{compose_cmd}} up --build

# Start without rebuilding
up-no-build:
	{{compose_cmd}} up

# Stop containers (keep volumes)
down:
	{{compose_cmd}} down

# Stop containers and remove volumes
down-clean:
	{{compose_cmd}} down -v

# Rebuild fresh (down -v + up --build)
rebuild:
	{{compose_cmd}} down -v
	{{compose_cmd}} up --build

# Run migrations
migrate:
	{{compose_cmd}} exec gunicorn python manage.py migrate

# Create superuser interactively
createsuperuser:
	{{compose_cmd}} exec gunicorn python manage.py createsuperuser

# Tail logs
logs:
	{{compose_cmd}} logs -f

# Tail a specific service (usage: just logs-service gunicorn)
logs-service service="gunicorn":
	{{compose_cmd}} logs -f {{service}}

# Run Django shell
shell:
	{{compose_cmd}} exec gunicorn python manage.py shell

# Collect static
collectstatic:
	{{compose_cmd}} exec gunicorn python manage.py collectstatic --noinput

# Open a DB psql shell
psql:
	{{compose_cmd}} exec db psql -U ${POSTGRES_USER:-okrcoach} -d ${POSTGRES_DB:-okrcoach}
