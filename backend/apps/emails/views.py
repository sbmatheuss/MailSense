from django.conf import settings
from django.db.models import Count, Avg
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
    serializer_class = EmailDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Email.objects.filter(user=self.request.user)
            .select_related("classification")
            .prefetch_related("actions")
        )


class EmailSyncView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from tasks.sync import sync_gmail_inbox
        sync_gmail_inbox.delay(request.user.pk)
        return Response({"detail": "Sincronização iniciada."})


class EmailReplyView(APIView):
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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Email.objects.filter(user=request.user)
        # Single aggregation query instead of 4 separate counts
        from django.db.models import Count, Q
        result = qs.aggregate(
            total=Count("id"),
            urgent=Count("id", filter=Q(classification__priority__in=["critical", "high"])),
            pending_action=Count("id", filter=Q(classification__requires_action=True)),
            classified=Count("id", filter=Q(status="classified")),
        )
        return Response(result)


class DashboardByCategoryView(APIView):
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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        avg_ms = (
            EmailClassification.objects.filter(email__user=request.user)
            .aggregate(avg=Avg("processing_time_ms"))["avg"]
        )
        return Response({"avg_processing_time_ms": round(avg_ms or 0)})


class DashboardTopSendersView(APIView):
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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.DEBUG:
            return Response({"detail": "Disponível apenas em modo DEBUG."}, status=status.HTTP_403_FORBIDDEN)
        from django.core.management import call_command
        call_command("seed_demo", user_id=request.user.pk)
        return Response({"detail": "Dados demo gerados com sucesso."})


class DemoResetView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.DEBUG:
            return Response({"detail": "Disponível apenas em modo DEBUG."}, status=status.HTTP_403_FORBIDDEN)
        Email.objects.filter(user=request.user).delete()
        return Response({"detail": "Dados demo removidos."})
