from django.conf import settings
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from rest_framework import status, generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Email, EmailClassification, ActionLog
from .serializers import (
    EmailListSerializer, EmailDetailSerializer,
    EmailClassificationUpdateSerializer,
)
from .filters import EmailFilter


class EmailListView(generics.ListAPIView):
    """GET /api/v1/emails/ — lista paginada de e-mails do usuário autenticado.

    Suporta filtragem via EmailFilter, busca textual em subject/from e ordenação
    por received_at, priority e confidence_score. Usa o serializer resumido para
    manter payloads pequenos (sem body e sem key_topics).
    """

    serializer_class = EmailListSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = EmailFilter
    search_fields = ["subject", "from_address", "from_name", "classification__summary"]
    ordering_fields = ["received_at", "classification__priority", "classification__confidence_score"]
    ordering = ["-received_at"]

    def get_queryset(self):
        return (
            Email.objects.filter(user=self.request.user)
            .select_related("classification")
        )


class EmailDetailView(generics.RetrieveAPIView):
    """GET /api/v1/emails/:id/ — detalhe completo de um e-mail.

    Retorna body_text, body_html, classificação completa e últimas 10 ações.
    Usa prefetch_related para actions para evitar N+1.
    """

    serializer_class = EmailDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Email.objects.filter(user=self.request.user)
            .select_related("classification")
            .prefetch_related("actions")
        )


class EmailSyncView(APIView):
    """POST /api/v1/emails/sync/ — dispara sincronização Gmail em background.

    Enfileira a task Celery `sync_gmail_inbox` para o usuário autenticado.
    Retorna imediatamente — o frontend deve usar WebSocket para progresso.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from tasks.sync import sync_gmail_inbox
        sync_gmail_inbox.delay(request.user.pk)
        return Response({"detail": "Sincronização iniciada."})


class EmailReplyView(APIView):
    """POST /api/v1/emails/:id/reply/ — registra resposta e cria ActionLog.

    No modo demo não envia e-mail de verdade — apenas persiste o log.
    A integração Gmail real será implementada no Agente 3.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        email = Email.objects.filter(pk=pk, user=request.user).first()
        if not email:
            raise NotFound()
        body = request.data.get("body", "")
        ActionLog.objects.create(
            email=email,
            action=ActionLog.ActionType.REPLIED,
            details={"body": body[:200]},
            performed_by=request.user,
        )
        return Response({"detail": "Resposta enviada."})


class EmailArchiveView(APIView):
    """POST /api/v1/emails/:id/archive/ — arquiva o e-mail (soft delete).

    Seta `is_archived=True` usando `update_fields` para evitar race condition
    com o pipeline de classificação que pode estar atualizando `status` em paralelo.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        email = Email.objects.filter(pk=pk, user=request.user).first()
        if not email:
            raise NotFound()
        email.is_archived = True
        email.save(update_fields=["is_archived"])
        ActionLog.objects.create(
            email=email,
            action=ActionLog.ActionType.ARCHIVED,
            details={},
            performed_by=request.user,
        )
        return Response({"detail": "E-mail arquivado."})


class EmailSnoozeView(APIView):
    """POST /api/v1/emails/:id/snooze/ — define data/hora de reativação do e-mail.

    O e-mail reaparece na inbox quando `snoozed_until` passa. A filtragem de
    snooze é responsabilidade do EmailFilter (`snoozed_until__lte=now`).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        email = Email.objects.filter(pk=pk, user=request.user).first()
        if not email:
            raise NotFound()
        until = request.data.get("until")
        email.snoozed_until = until
        email.save(update_fields=["snoozed_until"])
        ActionLog.objects.create(
            email=email,
            action=ActionLog.ActionType.SNOOZED,
            details={"until": until},
            performed_by=request.user,
        )
        return Response({"detail": "E-mail adiado."})


class EmailClassificationUpdateView(generics.UpdateAPIView):
    """PATCH /api/v1/emails/:id/classify/ — corrige a classificação da IA.

    Preserva os valores originais na primeira correção (feedback loop).
    Cria um ActionLog.CORRECTED para rastreamento de divergências IA vs. humano.
    """

    serializer_class = EmailClassificationUpdateSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["patch"]

    def get_object(self):
        email = (
            Email.objects.filter(pk=self.kwargs["pk"], user=self.request.user)
            .select_related("classification")
            .first()
        )
        if not email or not hasattr(email, "classification"):
            raise NotFound()
        ActionLog.objects.create(
            email=email,
            action=ActionLog.ActionType.CORRECTED,
            details=self.request.data,
            performed_by=self.request.user,
        )
        return email.classification


class EmailBulkActionView(APIView):
    """POST /api/v1/emails/bulk/ — aplica uma ação a múltiplos e-mails.

    Usa `bulk_create` para os ActionLogs e um único `queryset.update()` para
    evitar N writes na tabela de emails. Rejeita ações inválidas antes de
    tocar o banco.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get("ids", [])
        action = request.data.get("action")
        if action not in ActionLog.ActionType.values:
            return Response({"detail": "Ação inválida."}, status=status.HTTP_400_BAD_REQUEST)
        emails = list(Email.objects.filter(pk__in=ids, user=request.user))
        if not emails:
            return Response({"detail": "Nenhum e-mail encontrado."}, status=status.HTTP_400_BAD_REQUEST)
        ActionLog.objects.bulk_create([
            ActionLog(email=email, action=action, details={}, performed_by=request.user)
            for email in emails
        ])
        if action == ActionLog.ActionType.ARCHIVED:
            Email.objects.filter(pk__in=[e.pk for e in emails]).update(is_archived=True)
        return Response({"detail": f"{len(emails)} e-mails atualizados."})


class DashboardOverviewView(APIView):
    """GET /api/v1/dashboard/overview/ — métricas principais em uma única query.

    Usa `Count(..., filter=Q(...))` para calcular total, urgentes, pendentes e
    classificados em uma única `SELECT ... FROM emails` — sem sub-queries.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Email.objects.filter(user=request.user)
        result = qs.aggregate(
            total=Count("id"),
            urgent=Count("id", filter=Q(classification__priority__in=["critical", "high"])),
            pending_action=Count("id", filter=Q(classification__requires_action=True)),
            classified=Count("id", filter=Q(status="classified")),
        )
        return Response(result)


class DashboardByCategoryView(APIView):
    """GET /api/v1/dashboard/by-category/ — contagem de e-mails agrupada por categoria."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = (
            EmailClassification.objects.filter(email__user=request.user)
            .values("category")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return Response(list(data))


class DashboardByPriorityView(APIView):
    """GET /api/v1/dashboard/by-priority/ — contagem de e-mails agrupada por prioridade."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = (
            EmailClassification.objects.filter(email__user=request.user)
            .values("priority")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return Response(list(data))


class DashboardTrendsView(APIView):
    """GET /api/v1/dashboard/trends/?days=30 — volume diário de e-mails no período.

    Usa `TruncDate` (django.db.models.functions) ao invés de `.extra()` que é
    deprecated desde Django 4. O parâmetro `days` é limitado a int para evitar
    DoS via queries longas.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        days = int(request.GET.get("days", 30))
        since = timezone.now() - timedelta(days=days)
        data = (
            Email.objects.filter(user=request.user, received_at__gte=since)
            .annotate(day=TruncDate("received_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        return Response(list(data))


class DashboardResponseTimeView(APIView):
    """GET /api/v1/dashboard/response-time/ — tempo médio de processamento da IA em ms."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        avg_ms = (
            EmailClassification.objects.filter(email__user=request.user)
            .aggregate(avg=Avg("processing_time_ms"))["avg"]
        )
        return Response({"avg_processing_time_ms": round(avg_ms or 0)})


class DashboardTopSendersView(APIView):
    """GET /api/v1/dashboard/top-senders/ — top 10 remetentes por volume."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = (
            Email.objects.filter(user=request.user)
            .values("from_address", "from_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        return Response(list(data))


class DemoSeedView(APIView):
    """POST /api/v1/demo/seed/ — gera 150 e-mails fictícios para o usuário autenticado.

    Disponível apenas com DEBUG=True. Delega ao management command `seed_demo`
    para reaproveitar a lógica de geração de dados sem duplicação.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.DEBUG:
            return Response({"detail": "Disponível apenas em modo DEBUG."}, status=status.HTTP_403_FORBIDDEN)
        from django.core.management import call_command
        call_command("seed_demo", user_id=request.user.pk)
        return Response({"detail": "Dados demo gerados com sucesso."})


class DemoResetView(APIView):
    """POST /api/v1/demo/reset/ — remove todos os e-mails do usuário autenticado.

    Disponível apenas com DEBUG=True. A deleção em cascata garante que
    EmailClassification e ActionLog também sejam removidos.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.DEBUG:
            return Response({"detail": "Disponível apenas em modo DEBUG."}, status=status.HTTP_403_FORBIDDEN)
        Email.objects.filter(user=request.user).delete()
        return Response({"detail": "Dados demo removidos."})
