.PHONY: up down build logs shell migrate seed test lint format help

help:
	@echo "MailSense — Comandos disponíveis:"
	@echo "  make up        Sobe todos os serviços (dev)"
	@echo "  make down      Para e remove containers"
	@echo "  make build     Rebuild das imagens"
	@echo "  make logs      Logs de todos os serviços"
	@echo "  make shell     Shell Django (manage.py shell)"
	@echo "  make bash      Bash no container web"
	@echo "  make migrate   Roda migrations"
	@echo "  make seed      Popula dados demo"
	@echo "  make test      Roda todos os testes (backend + frontend)"
	@echo "  make test-back Apenas testes backend"
	@echo "  make test-front Apenas testes frontend"
	@echo "  make lint      Lint (ruff + eslint)"
	@echo "  make format    Formata código (ruff format)"

up:
	docker compose up

upd:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

shell:
	docker compose exec web python manage.py shell

bash:
	docker compose exec web bash

migrate:
	docker compose exec web python manage.py migrate

makemigrations:
	docker compose exec web python manage.py makemigrations

seed:
	docker compose exec web python manage.py seed_demo

createsuperuser:
	docker compose exec web python manage.py createsuperuser

collectstatic:
	docker compose exec web python manage.py collectstatic --noinput

test: test-back test-front

test-back:
	docker compose exec web pytest --cov=. --cov-report=term-missing -v

test-front:
	docker compose exec frontend npm test

lint:
	docker compose exec web ruff check .
	docker compose exec frontend npm run lint

format:
	docker compose exec web ruff format .

ps:
	docker compose ps
