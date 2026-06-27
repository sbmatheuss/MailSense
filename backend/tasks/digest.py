from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone

from apps.emails.models import Email

logger = logging.getLogger(__name__)


@shared_task
def generate_daily_digest(user_id: int) -> None:
    """Gera resumo diário: e-mails recebidos, urgentes, pendentes de ação."""
    since = timezone.now() - timedelta(hours=24)
    emails_qs = Email.objects.filter(user_id=user_id, received_at__gte=since)

    total = emails_qs.count()
    classified_qs = emails_qs.filter(status=Email.Status.CLASSIFIED)
    critical = classified_qs.filter(classification__priority="critical").count()
    require_action = classified_qs.filter(classification__requires_action=True).count()

    logger.info(
        "generate_daily_digest: user=%d total=%d critical=%d require_action=%d",
        user_id, total, critical, require_action,
    )
    # Future: send digest email / push notification with summary stats.


@shared_task
def generate_daily_digest_all() -> None:
    """Dispara digest para todos os usuários ativos."""
    uid_list = list(
        User.objects.filter(is_active=True, profile__gmail_sync_enabled=True)
        .values_list("id", flat=True)
    )
    for uid in uid_list:
        generate_daily_digest.delay(uid)
    logger.info("generate_daily_digest_all: dispatched %d digest tasks", len(uid_list))
