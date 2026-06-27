# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MailSense — plataforma web fullstack que classifica e-mails automaticamente com IA (Claude API), sugere respostas, identifica urgências e apresenta tudo em um dashboard inteligente. Projeto de portfólio com modo demo (sem Gmail real).

## Tech Stack

- **Backend:** Python 3.12, Django 5.x, Django REST Framework, Celery, Redis, PostgreSQL, Django Channels (WebSocket)
- **Frontend:** React 18 + TypeScript, Vite, TailwindCSS, Shadcn/UI, Recharts, React Query (TanStack Query)
- **IA:** Anthropic Claude API (`claude-sonnet-4-6` para classificação, `claude-opus-4-6` para decisões arquiteturais)
- **Infra:** Docker (multi-stage), Docker Compose, Nginx, GitHub Actions (CI/CD)
- **Deploy:** Railway ou Fly.io

## Development Commands

```bash
# Subir todos os serviços (dev)
make up

# Parar containers
make down

# Aplicar migrations
make migrate

# Criar migrations
make makemigrations

# Rodar todos os testes
make test

# Apenas backend
make test-back

# Apenas frontend
make test-front

# Lint
make lint

# Formatar código
make format

# Seed de dados demo
make seed

# Django shell
make shell
```

### Sem Docker (backend)
```bash
cd backend
pip install -r requirements/dev.txt
DJANGO_SETTINGS_MODULE=config.settings.dev python manage.py runserver
```

### Sem Docker (frontend)
```bash
cd frontend
npm install
npm run dev
```

## Architecture

Monorepo com dois artefatos principais:

```
backend/   → Django + DRF + Celery (porta 8000)
frontend/  → React + Vite (porta 5173 em dev)
nginx/     → Reverse proxy (porta 80/443 em prod)
docs/adr/  → Architecture Decision Records
```

**Data flow principal:**
1. Celery Beat sincroniza Gmail a cada 5 min → e-mails salvos com `status=PENDING`
2. Task `classify_pending_batch` pega lotes de 5 → chama Claude API → salva `EmailClassification`
3. E-mails críticos disparam WebSocket push via Django Channels → React Query invalida cache
4. Frontend React Query re-fetcha e atualiza dashboard e inbox em tempo real

**Documentação de arquitetura:** `docs/architecture.md`
**ADRs:** `docs/adr/`

## Multi-agent Strategy

Este projeto usa dois modelos Claude de forma estratégica:
- **Opus** (`claude-opus-4-6`): decisões arquiteturais, ADRs, design de prompts, code review final
- **Sonnet** (`claude-sonnet-4-6`): implementação de models, views, componentes, tasks, testes

Ao receber instrução "Atue como Agente N no modo X", seguir as responsabilidades em `mailsense-prompt.md.txt`.
