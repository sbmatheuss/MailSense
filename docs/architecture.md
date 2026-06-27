# MailSense — Arquitetura do Sistema

**Versão:** 1.0 (Fase 1 — Fundação)
**Data:** 2026-06-26
**Agente:** 1 — Infraestrutura (Opus) via `/system-design`

---

## Visão Geral

O MailSense é uma plataforma web fullstack que classifica e-mails automaticamente usando IA (Claude API), sugere respostas e apresenta tudo em um dashboard inteligente.

**Público-alvo:** recrutadores e tech leads avaliando portfólio técnico.
**Modo demo:** funciona sem Gmail real, com 150 e-mails fictícios pré-classificados.

---

## Requisitos

### Funcionais
- Sincronizar e-mails do Gmail a cada 5 minutos (ou simular via dados demo)
- Classificar e-mails automaticamente: categoria, prioridade, sentimento, resumo, resposta sugerida
- Dashboard com métricas e gráficos em tempo real
- Notificação WebSocket para e-mails críticos
- Modo demo sem OAuth

### Não-Funcionais
- Latência de classificação: < 30s após recebimento
- Volume: 500 e-mails/dia
- Disponibilidade: best-effort (portfólio, sem SLA de produção)
- Deploy em Railway ou Fly.io (single region)

---

## Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USUÁRIO (Browser)                           │
│                    React 18 + TypeScript + Vite                     │
│                                                                     │
│  ┌────────────┐  ┌───────────────────┐  ┌──────────┐  ┌─────────┐  │
│  │ Dashboard  │  │ Inbox (split view)│  │ Settings │  │  Demo   │  │
│  └────────────┘  └───────────────────┘  └──────────┘  └─────────┘  │
│                                                                     │
│  React Query (cache + refetch)  │  Zustand (UI state)              │
│  Recharts (gráficos)            │  WebSocket hook (notificações)   │
└─────────────────────┬───────────────────────────────┬──────────────┘
                      │ HTTPS                         │ WebSocket
                      ▼                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        NGINX (reverse proxy)                        │
│                                                                     │
│  /api/*    →  Django :8000    │  /*  → React static (dist/)        │
│  /admin/*  →  Django :8000    │  /ws/ → Django Channels (ASGI)     │
└──────────────┬──────────────────────────────────┬───────────────────┘
               │                                  │
               ▼                                  ▼
┌──────────────────────────┐    ┌──────────────────────────────────────┐
│   Django 5 + DRF (WSGI)  │    │   Django Channels (ASGI)             │
│                          │    │   WebSocket Consumers                │
│  /api/v1/auth/           │    │   ws/notifications/                  │
│  /api/v1/emails/         │    │                                      │
│  /api/v1/dashboard/      │◄───│   Push críticos → browser            │
│  /api/v1/demo/           │    └──────────────────────────────────────┘
│  /api/docs/ (Swagger)    │
└──────────┬───────────────┘
           │ psycopg3 (ORM)
           ▼
┌─────────────────────┐   ┌─────────────────────────────────────────────┐
│   PostgreSQL 16      │   │                 Redis 7                     │
│                     │   │  ├── Celery broker (task queue)             │
│  emails             │   │  ├── Celery result backend                  │
│  email_classification│   │  ├── Django Channels layer (WebSocket)     │
│  action_logs        │   │  └── Cache (dashboard queries, TTL 5min)   │
│  user_profiles      │   └─────────────────────────────────────────────┘
│  auth_token         │                        ▲
│  django_celery_beat │                        │ broker
└─────────────────────┘                        │
                              ┌────────────────┴──────────────────────────┐
                              │              CELERY                        │
                              │                                           │
                              │  Worker                Beat               │
                              │  ├── classify_email    ├── */5min sync    │
                              │  ├── classify_batch    ├── */2min classify│
                              │  ├── notify_critical   └── 08:00 digest   │
                              │  └── generate_digest                      │
                              └─────────────────┬─────────────────────────┘
                                                │
                               ┌────────────────┴────────────────┐
                               │                                 │
                               ▼                                 ▼
                 ┌─────────────────────────┐   ┌──────────────────────────────┐
                 │      Gmail API          │   │    Anthropic Claude API      │
                 │  (OAuth2, messages,     │   │  claude-sonnet-4-6           │
                 │   send, mark-read)      │   │  classify_email / batch      │
                 │                         │   │  generate_reply              │
                 └─────────────────────────┘   └──────────────────────────────┘
```

---

## Data Flow — Classificação de um E-mail

```
 1. Celery Beat dispara sync_gmail_inbox_all_users (*/5min)
    │
 2. GmailService.fetch_new_messages() → Gmail API
    │
 3. Email salvo no PostgreSQL  [status = PENDING]
    │
 4. classify_email_task.delay(email_id) → Redis queue
    │
 5. Celery Worker consome task
    │
 6. LLMService.classify_email() → Anthropic API
    │
 7. Resposta JSON estruturada recebida
    │
 8. EmailClassification salvo no PostgreSQL
 9. Email atualizado  [status = CLASSIFIED]
    │
10. Se priority == critical:
    └── notify_critical_email.delay(email_id)
        └── Django Channels group_send → WebSocket push
            └── React: badge pulsante + invalidate React Query cache
```

---

## Modelo de Dados (Resumo)

```
User (Django auth)
 └── UserProfile         # tokens Gmail, sync state
      └── Email          # gmail_id, thread_id, from, subject, body
           └── EmailClassification  # category, priority, sentiment, summary, reply
           └── ActionLog[]          # replied, archived, escalated, corrected
```

**Índices críticos:**
- `emails(user_id, status)` — filtro mais comum
- `emails(user_id, received_at)` — ordenação padrão
- `emails(gmail_id)` — deduplicação no sync (UNIQUE)
- `emails(thread_id)` — agrupamento de threads

---

## Decisões de Storage

| Dado | Storage | Justificativa |
|---|---|---|
| E-mails e classificações | PostgreSQL | Relacional, queries de filtro, transações |
| Sessões / tokens | PostgreSQL (authtoken) | Simplicidade, não precisa de Redis para tokens DRF |
| Task queue | Redis | Celery padrão, low-latency |
| WebSocket channel layer | Redis | Django Channels padrão |
| Dashboard cache | Redis (TTL 5min) | Queries de agregação custosas, atualização não-crítica |
| Attachments | Fora de escopo (v1) | Complexidade desnecessária para portfólio |

---

## Decisões de API

- **DRF** com serializers separados para list (leve) e detail (completo)
- **django-filter** para filtros compostos (`?category=support,billing&priority=critical`)
- **Paginação:** `PageNumberPagination`, `page_size=20`
- **Throttling:** 100 req/min autenticado, 20 req/min anônimo
- **Auth:** Token (DRF `authtoken`) — simples e suficiente para portfólio
- **Schema:** drf-spectacular → Swagger em `/api/docs/`, Redoc em `/api/redoc/`

---

## Estrutura de Pastas Validada

```
mailsense/
├── .github/workflows/ci.yml       # CI: lint + test + docker build
├── docs/
│   ├── adr/                       # Architecture Decision Records
│   │   ├── ADR-001.md             # Monorepo vs Poly-repo
│   │   └── ADR-002.md             # Docker multi-stage strategy
│   └── architecture.md            # Este documento
├── nginx/nginx.conf               # Reverse proxy
├── backend/
│   ├── apps/
│   │   ├── accounts/              # Auth, UserProfile, Gmail OAuth2
│   │   └── emails/                # Email, Classification, ActionLog, views
│   ├── config/
│   │   ├── settings/base|dev|prod # Split de ambientes
│   │   ├── celery.py              # Celery + beat schedule
│   │   ├── urls.py                # URL root
│   │   ├── asgi.py                # Channels ASGI
│   │   └── wsgi.py                # Gunicorn WSGI
│   ├── services/
│   │   ├── gmail_service.py       # Gmail API wrapper (Agente 2)
│   │   └── llm_service.py         # Anthropic API wrapper (Agente 3)
│   ├── tasks/
│   │   ├── sync.py                # Gmail sync tasks (Agente 3)
│   │   ├── classify.py            # Classification tasks (Agente 3)
│   │   ├── digest.py              # Daily digest (Agente 3)
│   │   └── notifications.py       # WebSocket push (Agente 3)
│   ├── tests/                     # pytest + factory_boy (Agente 6)
│   └── requirements/base|dev|prod
├── frontend/
│   └── src/
│       ├── api/                   # React Query hooks por domínio
│       ├── components/
│       │   ├── common/            # Badge, EmptyState, Toast, Spinner, ErrorBoundary
│       │   ├── emails/            # EmailList, EmailDetail, ClassificationBadge...
│       │   ├── dashboard/         # OverviewCards, Charts...
│       │   └── layout/            # Sidebar, Header, MainLayout
│       ├── hooks/                 # useWebSocket, useEmailFilters, useKeyboardShortcuts
│       ├── pages/                 # LoginPage, DashboardPage, InboxPage, SettingsPage, DemoPage
│       ├── stores/uiStore.ts      # Zustand: auth + UI state
│       ├── types/index.ts         # TypeScript types
│       └── utils/                 # formatters, constants
├── Dockerfile.backend             # multi-stage: base → dev → prod
├── Dockerfile.frontend            # multi-stage: deps → builder → nginx
├── docker-compose.yml             # Dev: hot reload, volumes
├── docker-compose.prod.yml        # Prod: target production
├── Makefile                       # make up|test|migrate|seed|lint
└── .env.example                   # Todas as variáveis necessárias
```

---

## ADRs Planejados (Próximas Fases)

| # | Decisão | Fase | Status |
|---|---|---|---|
| ADR-001 | Monorepo vs Poly-repo | Fase 1 | ✅ Aceito |
| ADR-002 | Docker multi-stage strategy | Fase 1 | ✅ Aceito |
| ADR-003 | Framework backend: DRF vs Django Ninja vs FastAPI | Fase 2 | ✅ Aceito (DRF) |
| ADR-004 | Autenticação: JWT vs Session vs DRF Token | Fase 2 | ✅ Aceito (DRF Token) |
| ADR-005 | Classificação: Batch vs Individual vs Híbrido | Fase 3 | Pendente |
| ADR-006 | Provider LLM: Claude vs OpenAI vs Multi-provider | Fase 3 | Pendente |
| ADR-007 | State management: Zustand vs Redux vs React Query only | Fase 4 | Pendente |
| ADR-008 | Deploy: Railway vs Fly.io vs Render | Fase 6 | Pendente |
