# MailSense

**AI-powered email management platform** — automatically classifies incoming emails, suggests replies, flags urgencies, and presents everything in a real-time dashboard.

> **Demo mode:** runs entirely with synthetic data — no Gmail account required to explore the full UI.

---

## Features

- **Automatic classification** — every email is categorised (support, billing, bug, feature, sales, internal, newsletter, spam) with priority (critical → low), sentiment and confidence score
- **AI-suggested replies** — Claude generates a context-aware draft reply for each classified email
- **Real-time critical alerts** — WebSocket push notification + toast the moment a critical email arrives
- **Smart dashboard** — charts by category, priority and 30-day trend; top senders table
- **Feedback loop** — users can correct AI classifications; originals are preserved for prompt refinement
- **Demo seed** — one command generates 150 realistic emails with coherent category↔classification pairs
- **Full test suite** — pytest (backend) + vitest (frontend), CI via GitHub Actions

---

## Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, Django 5.1, Django REST Framework |
| **Async tasks** | Celery 5, Redis, Celery Beat |
| **Real-time** | Django Channels 4 (WebSocket), channels-redis |
| **AI** | Anthropic Claude API (`claude-sonnet-4-6`) |
| **Database** | PostgreSQL 16 |
| **Frontend** | React 18, TypeScript, Vite, TailwindCSS |
| **State** | Zustand (persisted auth), TanStack Query (server state) |
| **Charts** | Recharts |
| **Infra** | Docker, Docker Compose, Nginx, GitHub Actions |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser (React)                          │
│  TanStack Query ◄──── REST API ────► Django DRF                 │
│  Zustand Store  ◄──── WebSocket ───► Django Channels             │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │     PostgreSQL       │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │  Celery Beat   │ │Celery Worker│ │  Channel     │
    │ (every 5 min) │ │             │ │  Layer Redis │
    └─────────┬──────┘ └──────┬──────┘ └─────────────┘
              │                │
              │    classify_pending_batch
              │                │
              └────────────────▼
                    ┌──────────────────┐
                    │   Claude API      │
                    │ (sonnet-4-6)     │
                    │  batch of 5 →    │
                    │  JSON array      │
                    └──────────────────┘
```

**Data flow:**

1. `Celery Beat` triggers `sync_gmail_inbox_all_users` every 5 min → emails saved as `PENDING`
2. `classify_pending_batch` picks batches of 5 → single Claude API call → `EmailClassification` saved
3. On `BatchParseError`, falls back to individual `classify_email_task` per email (exponential backoff, max 2 retries)
4. Critical emails trigger `notify_critical_email` → Django Channels `group_send` → WebSocket frame → React toast + cache invalidation

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- An [Anthropic API key](https://console.anthropic.com/)

### 1. Clone and configure

```bash
git clone https://github.com/sbmatheuss/MailSense.git
cd MailSense

cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Start all services

```bash
make up
```

This starts: `postgres`, `redis`, `web` (Django), `worker` (Celery), `beat` (Celery Beat), `frontend` (Vite dev server).

### 3. Apply migrations and seed demo data

```bash
make migrate
make seed
```

### 4. Open the app

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000/api/v1/ |
| Swagger docs | http://localhost:8000/api/docs/ |

**Default demo credentials** — register a new account via the UI, then call `POST /api/v1/demo/seed/` or run `make seed` to populate 150 emails for that user.

---

## Development Commands

```bash
make up            # Start all services (dev)
make down          # Stop and remove containers
make build         # Rebuild Docker images
make logs          # Tail all service logs
make migrate       # Apply Django migrations
make makemigrations  # Create new migrations
make seed          # Populate 150 demo emails
make shell         # Django management shell
make bash          # Bash inside web container

make test          # Run full test suite (backend + frontend)
make test-back     # pytest only
make test-front    # vitest only

make lint          # ruff + eslint
make format        # ruff format
```

### Without Docker (backend)

```bash
cd backend
pip install -r requirements/dev.txt
export DJANGO_SETTINGS_MODULE=config.settings.dev
export DATABASE_URL=postgresql://...
python manage.py runserver
```

### Without Docker (frontend)

```bash
cd frontend
npm install
npm run dev
```

---

## Project Structure

```
MailSense/
├── backend/
│   ├── apps/
│   │   ├── accounts/          # Auth, UserProfile, Gmail OAuth
│   │   └── emails/            # Email, EmailClassification, ActionLog
│   │       ├── models.py
│   │       ├── views.py        # DRF views (list, detail, archive, reply, dashboard)
│   │       ├── serializers.py
│   │       ├── filters.py
│   │       └── management/commands/seed_demo.py
│   ├── config/
│   │   ├── settings/          # base, dev, prod
│   │   ├── asgi.py            # Channels + TokenAuthMiddleware
│   │   └── celery.py
│   ├── services/
│   │   └── llm_service.py     # LLMService — Anthropic wrapper
│   ├── tasks/
│   │   ├── classify.py        # classify_email_task, classify_pending_batch
│   │   ├── sync.py            # sync_gmail_inbox
│   │   ├── notifications.py   # notify_critical_email (WebSocket push)
│   │   └── digest.py          # generate_daily_digest
│   └── tests/
│       ├── test_llm_service.py
│       ├── test_email_api.py
│       ├── test_classify_tasks.py
│       └── test_seed_command.py
│
├── frontend/
│   └── src/
│       ├── api/               # TanStack Query hooks (emails, dashboard)
│       ├── components/
│       │   ├── layout/        # Sidebar, Header
│       │   └── ui/            # Toast, Skeleton
│       ├── hooks/
│       │   └── useWebSocket.ts
│       ├── pages/             # DashboardPage, InboxPage, LoginPage
│       └── stores/            # useAuthStore, useUIStore, useToastStore
│
├── docs/
│   ├── architecture.md
│   └── adr/                   # ADR-001 → ADR-006
│
├── nginx/
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── Makefile
```

---

## API Reference

Full OpenAPI schema at `GET /api/schema/` · Swagger UI at `/api/docs/`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/login/` | Obtain DRF token |
| `POST` | `/api/v1/auth/register/` | Create account |
| `GET` | `/api/v1/emails/` | Paginated inbox (filters: priority, category, search) |
| `GET` | `/api/v1/emails/:id/` | Full email detail + classification |
| `POST` | `/api/v1/emails/:id/archive/` | Archive email |
| `POST` | `/api/v1/emails/:id/reply/` | Log reply (demo: no real send) |
| `PATCH` | `/api/v1/emails/:id/classification/` | Correct AI classification |
| `POST` | `/api/v1/emails/bulk-action/` | Bulk archive / star |
| `GET` | `/api/v1/dashboard/overview/` | Total, urgent, pending, classified counts |
| `GET` | `/api/v1/dashboard/by-category/` | Email count by category |
| `GET` | `/api/v1/dashboard/by-priority/` | Email count by priority |
| `GET` | `/api/v1/dashboard/trends/?days=30` | Daily volume trend |
| `GET` | `/api/v1/dashboard/top-senders/` | Top 10 senders |
| `POST` | `/api/v1/demo/seed/` | Generate 150 demo emails (DEBUG only) |
| `POST` | `/api/v1/demo/reset/` | Delete all demo emails (DEBUG only) |

**WebSocket:** `ws://localhost:8000/ws/notifications/?token=<drf-token>`

---

## Testing

```bash
# Backend — requires PostgreSQL (run inside Docker or set DATABASE_URL)
make test-back
# or directly:
cd backend && pytest --cov=. --cov-report=term-missing -v

# Frontend — no external dependencies
make test-front
# or directly:
cd frontend && npm test
```

**Backend coverage** (~55 tests):

| File | What's tested |
|---|---|
| `test_llm_service.py` | `classify_email`, `classify_batch` (BatchParseError, count mismatch, chunking, max_tokens), `generate_reply`, body truncation, temperature=0 |
| `test_email_api.py` | Auth, user isolation, filters, pagination, archive, reply, classification correction, dashboard aggregations, demo seed/reset |
| `test_classify_tasks.py` | Happy path, retry on API error, FAILED on max retries, batch fallback to individual, PROCESSING status during call, critical notification |
| `test_seed_command.py` | 150 emails created, all classified, idempotency, category distribution, cross-user isolation |

**Frontend coverage** (30 tests):

| File | What's tested |
|---|---|
| `uiStore.test.ts` | `useAuthStore`, `useUIStore`, `useToastStore` (add, deduplicate by id, remove) |
| `Skeleton.test.tsx` | CSS classes, `EmailListSkeleton` (6 rows), `DashboardSkeleton` |
| `Toast.test.tsx` | Render, close button, auto-dismiss after 5 s (fake timers), border class per type |

---

## Architecture Decisions

| ADR | Decision |
|---|---|
| [ADR-001](docs/adr/ADR-001.md) | PostgreSQL over MongoDB — structured schema fits email metadata |
| [ADR-002](docs/adr/ADR-002.md) | Celery + Redis over Django Q — mature ecosystem, Beat scheduler |
| [ADR-003](docs/adr/ADR-003.md) | Django Channels for WebSocket — native Django integration |
| [ADR-004](docs/adr/ADR-004.md) | TanStack Query for frontend state — stale-while-revalidate, cache invalidation |
| [ADR-005](docs/adr/ADR-005.md) | Hybrid batch classification — batch-first with individual fallback on parse error |
| [ADR-006](docs/adr/ADR-006.md) | `claude-sonnet-4-6`, `temperature=0`, body truncated to 2000 chars |

---

## Multi-Agent Development

This project was built using a multi-model Claude strategy:

- **Opus** (`claude-opus-4-6`) — architectural decisions, ADR writing, prompt design, code review
- **Sonnet** (`claude-sonnet-4-6`) — all implementation: models, views, tasks, components, tests

Each "agent" owned a vertical slice of the system, with Opus acting as tech lead between phases.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | ✅ | Django secret key |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_URL` | ✅ | Redis connection string |
| `ANTHROPIC_API_KEY` | ✅ | Anthropic API key (for live classification) |
| `GOOGLE_CLIENT_ID` | ⬜ | Gmail OAuth client ID (optional — demo mode works without) |
| `GOOGLE_CLIENT_SECRET` | ⬜ | Gmail OAuth secret |
| `DJANGO_DEBUG` | ⬜ | `True` for dev (enables demo endpoints) |
| `ALLOWED_HOSTS` | ⬜ | Comma-separated hosts for production |

---

## License

MIT
