# MailSense — Backend Data Model & API Contracts

**Versão:** 1.0 (Fase 2 — Backend)
**Data:** 2026-06-26
**Agente:** 2 — Backend (Opus) via `/system-design`

---

## Data Model Completo

### Diagrama de Entidades

```
User (Django auth_user)
│
└──▶ UserProfile          (1:1)    tokens Gmail, sync state
│
└──▶ Email[]              (1:N)    e-mails sincronizados
      │
      ├──▶ EmailClassification (1:1)    resultado da IA
      │
      └──▶ ActionLog[]         (1:N)    auditoria de ações
```

---

### UserProfile

```python
UserProfile
  user              OneToOne(User)       # Django built-in User
  gmail_access_token  TextField(blank)   # OAuth2 access token (criptografar em v2)
  gmail_refresh_token TextField(blank)   # OAuth2 refresh token
  gmail_connected_at  DateTimeField?     # quando conectou o Gmail
  gmail_sync_enabled  BooleanField       # default: False
  last_sync_at        DateTimeField?     # última sync bem-sucedida
  timezone            CharField(50)      # default: "America/Sao_Paulo"
```

**Decisão de segurança:** Tokens Gmail em texto simples no banco são suficientes para portfólio (HTTPS + acesso restrito ao DB). Em produção real, usar `django-fernet-fields` para encryption at rest — registrado como tech debt.

---

### Email

```python
Email
  # Identidade
  user              FK(User)
  gmail_id          CharField(255, unique)    # ID único do Gmail — deduplicação no sync
  thread_id         CharField(255)            # agrupamento de threads

  # Remetente/Destinatário
  from_address      EmailField
  from_name         CharField(255, blank)
  to_address        JSONField(list)           # lista de endereços
  cc_address        JSONField(list)

  # Conteúdo
  subject           CharField(500)
  body_text         TextField                 # sempre presente
  body_html         TextField(blank)          # pode não ter HTML
  raw_headers       JSONField(dict)           # headers originais para debug

  # Estado
  received_at       DateTimeField
  is_read           BooleanField             # default: False
  is_archived       BooleanField             # default: False — controla visibilidade no inbox
  snoozed_until     DateTimeField?           # None = não snoozed
  has_attachments   BooleanField             # default: False
  status            TextChoices              # pending → processing → classified | failed

  # Metadata
  created_at        DateTimeField(auto)
```

**Índices (justificativa):**

| Nome | Campos | Query que serve |
|---|---|---|
| `email_inbox_idx` | `(user, is_archived, received_at)` | `GET /emails/?is_archived=false` — inbox padrão |
| `email_status_idx` | `(user, status)` | `classify_pending_batch` — busca emails PENDING |
| `email_thread_idx` | `(user, thread_id)` | Agrupamento de threads na inbox |
| UNIQUE constraint | `gmail_id` | Deduplicação no sync (também cria índice automático) |

**Por que `received_at` no índice e não `created_at`?**
`received_at` é a data que o e-mail chegou na caixa do usuário. `created_at` é quando nosso sistema registrou. Para ordenação do inbox, a data real de recebimento é o critério correto.

---

### EmailClassification

```python
EmailClassification
  email             OneToOne(Email)          # CASCADE on delete

  # Classificação da IA
  category          TextChoices              # support|billing|bug|feature|sales|internal|newsletter|spam|other
  priority          TextChoices              # critical|high|medium|low
  sentiment         TextChoices              # positive|neutral|negative|urgent
  confidence_score  FloatField               # 0.0–1.0 (precision suficiente para display)
  summary           TextField                # ≤ 2 frases
  key_topics        JSONField(list)          # ["tópico1", "tópico2"] — 2 a 5 tags
  suggested_reply   TextField(blank)         # resposta sugerida pela IA
  urgency_reason    TextField(blank)         # preenchido apenas quando priority=critical|high

  # Ação recomendada
  requires_action   BooleanField             # default: False

  # Feedback loop — valores originais antes de correção manual
  user_corrected    BooleanField             # default: False
  original_category CharField(20, blank)
  original_priority CharField(20, blank)
  original_sentiment CharField(20, blank)

  # Métricas de processamento
  processed_at      DateTimeField(auto)
  processing_time_ms IntegerField            # para monitorar performance da API Claude
```

**Por que salvar `original_*`?**
O feedback loop permite medir a accuracy real da IA em produção: `user_corrected=True` + `original_category != category` = classificação errada. Isso alimenta refinamento de prompts no Agente 3.

---

### ActionLog

```python
ActionLog
  email           FK(Email)                 # CASCADE on delete
  action          TextChoices               # replied|archived|unarchived|escalated|snoozed|starred|corrected
  details         JSONField(dict)           # payload específico da ação (body truncado, until date, etc.)
  performed_by    FK(User)
  performed_at    DateTimeField(auto)

  # Índice
  # (email_id, performed_at) — timeline de ações por e-mail
```

---

## API Contracts

### Autenticação

```
POST   /api/v1/auth/register/
  Body: { username, email, password }
  201:  { token, user_id }

POST   /api/v1/auth/login/
  Body: { username, password }
  200:  { token, user_id }
  401:  { detail: "Credenciais inválidas." }

POST   /api/v1/auth/logout/
  Header: Authorization: Token <token>
  204:  (token deletado do banco)

GET    /api/v1/auth/profile/
  200:  { username, email, is_gmail_connected, gmail_connected_at, last_sync_at, timezone }

POST   /api/v1/auth/gmail/connect/
  200:  { auth_url }

GET    /api/v1/auth/gmail/callback/?code=...
  302:  redirect para frontend com status

POST   /api/v1/auth/gmail/disconnect/
  200:  { detail }
```

### E-mails

```
GET    /api/v1/emails/
  Query params:
    category=support,billing          (CSV, OR entre valores)
    priority=critical,high            (CSV, OR entre valores)
    sentiment=negative
    status=classified
    requires_action=true
    is_archived=false                 (default inbox exclui arquivados)
    user_corrected=true               (para análise de feedback loop)
    date_from=2025-01-01T00:00:00Z
    date_to=2025-06-01T00:00:00Z
    search=texto livre                (subject, from, summary)
    ordering=-received_at             (ou classification__priority, confidence_score)
    page=1&page_size=20
  200: {
    count: N,
    next: url | null,
    previous: url | null,
    results: [EmailList]
  }

GET    /api/v1/emails/{id}/
  200: EmailDetail (inclui body_html, classification completa, últimas 10 actions)

POST   /api/v1/emails/sync/
  200: { detail: "Sincronização iniciada." }

POST   /api/v1/emails/{id}/reply/
  Body: { body: string }
  200: { detail }

POST   /api/v1/emails/{id}/archive/
  200: { detail }           # sets is_archived=True + cria ActionLog

POST   /api/v1/emails/{id}/snooze/
  Body: { until: ISO8601 }
  200: { detail }           # sets snoozed_until + cria ActionLog

PATCH  /api/v1/emails/{id}/classification/
  Body: { category?, priority?, sentiment? }
  200: EmailClassification  # salva originals, sets user_corrected=True + cria ActionLog

POST   /api/v1/emails/bulk-action/
  Body: { ids: [N], action: "archived"|"starred" }
  200: { detail: "N e-mails atualizados." }
```

### Dashboard

```
GET    /api/v1/dashboard/overview/
  200: { total, urgent, pending_action, classified }
  Cache: 5 min (Redis)

GET    /api/v1/dashboard/by-category/
  200: [{ category, count }]
  Cache: 5 min

GET    /api/v1/dashboard/by-priority/
  200: [{ priority, count }]
  Cache: 5 min

GET    /api/v1/dashboard/trends/?days=30
  200: [{ day: "2025-01-01", count: N }]
  Cache: 5 min

GET    /api/v1/dashboard/response-time/
  200: { avg_processing_time_ms: N }

GET    /api/v1/dashboard/top-senders/
  200: [{ from_address, from_name, count }]
```

### Demo

```
POST   /api/v1/demo/seed/        (somente DEBUG=True)
  200: { detail: "Dados demo gerados com sucesso." }

POST   /api/v1/demo/reset/       (somente DEBUG=True)
  200: { detail: "Dados demo removidos." }
```

---

## Serializers — List vs Detail

### EmailListSerializer (GET /emails/)
Campos retornados por item na listagem:
```json
{
  "id": 1,
  "gmail_id": "abc123",
  "from_address": "remetente@empresa.com",
  "from_name": "João Silva",
  "subject": "Assunto do e-mail",
  "received_at": "2025-01-15T10:30:00Z",
  "is_read": false,
  "is_archived": false,
  "has_attachments": false,
  "status": "classified",
  "classification": {
    "category": "support",
    "priority": "high",
    "sentiment": "negative",
    "confidence_score": 0.92,
    "summary": "Cliente reporta falha no login. Precisa de suporte urgente.",
    "requires_action": true
  }
}
```

**Omitidos do list** (disponíveis apenas no detail): `thread_id`, `to_address`, `cc_address`, `body_text`, `body_html`, `snoozed_until`, `created_at`, `key_topics`, `suggested_reply`, `urgency_reason`, `user_corrected`, `processed_at`, `processing_time_ms`, `actions`.

### EmailDetailSerializer (GET /emails/{id}/)
Inclui tudo do list mais:
- `body_text`, `body_html`, `thread_id`, `to_address`, `cc_address`, `snoozed_until`
- `classification` completa com `key_topics`, `suggested_reply`, `urgency_reason`, `user_corrected`, `processed_at`, `processing_time_ms`
- `actions[]` (últimas 10)

---

## Filtros e Paginação

### Paginação
`PageNumberPagination` com `page_size=20`. Parâmetros: `?page=N&page_size=N` (max 100).

### Filtros
Implementados via `django-filter` com `EmailFilter`:

| Param | Tipo | Campo DB |
|---|---|---|
| `category` | CSV string | `classification__category__in` |
| `priority` | CSV string | `classification__priority__in` |
| `sentiment` | exact string | `classification__sentiment` |
| `status` | exact string | `status` |
| `requires_action` | boolean | `classification__requires_action` |
| `is_archived` | boolean | `is_archived` |
| `user_corrected` | boolean | `classification__user_corrected` |
| `date_from` | ISO datetime | `received_at__gte` |
| `date_to` | ISO datetime | `received_at__lte` |
| `search` | free text | `subject`, `from_address`, `from_name`, `classification__summary` |
| `ordering` | field name | `received_at`, `classification__priority`, `classification__confidence_score` |

### Throttling
- Anônimo: 20 req/min
- Autenticado: 100 req/min
- Dashboard endpoints: cache Redis 5min (reduz queries de agregação)

---

## Storage Choices

| Dado | Storage | Motivo |
|---|---|---|
| E-mails, classificações, logs | PostgreSQL 16 | Relacional, filtros compostos, transações ACID |
| Tokens de auth | PostgreSQL (authtoken) | Revogação imediata, trivial com DRF |
| Tokens OAuth Gmail | PostgreSQL (UserProfile) | Mesmo banco, simplifica queries |
| Task queue (Celery) | Redis 7 | Broker padrão Celery, baixa latência |
| Channel layer (WebSocket) | Redis 7 | Django Channels padrão |
| Cache dashboard | Redis 7 (DB 1, TTL 5min) | Queries de agregação custosas |
| Attachments | Fora de escopo (v1) | Complexidade desnecessária para portfólio |

**Uso de JSONField:**
- `to_address`, `cc_address`: lista de strings sem queries internas
- `key_topics`: lista de tags sem queries
- `raw_headers`: dict de debug, nunca filtrado
- `details` (ActionLog): payload variável por tipo de ação

JSONField escolhido sobre tabelas relacionais porque nenhum desses campos é alvo de queries por seus elementos internos — são dados de display apenas.

---

## Queries N+1 — Pontos de atenção

| View | Estratégia |
|---|---|
| `EmailListView` | `select_related("classification")` |
| `EmailDetailView` | `select_related("classification")` + `prefetch_related("actions")` |
| `EmailClassificationUpdateView` | `select_related("classification")` antes de retornar objeto |
| `DashboardOverviewView` | Uma única query com `Count(..., filter=Q(...))` |
| `EmailBulkActionView` | `bulk_create` para ActionLogs, `queryset.update()` para campos |

---

## Decisões Pendentes para Fase 3 (Agente 3)

- **ADR-005:** Batch vs Individual vs Híbrido para classificação
- **ADR-006:** Claude vs OpenAI vs Multi-provider
- Definição final dos prompts de classificação (system + user)
- Estratégia de retry e dead letter queue
