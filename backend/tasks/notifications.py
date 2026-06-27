from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer

from apps.emails.models import Email

logger = logging.getLogger(__name__)


@shared_task
def notify_critical_email(email_id: int) -> None:
    """Envia notificação via WebSocket (Django Channels) para e-mails críticos."""
    try:
        email = Email.objects.get(pk=email_id)
    except Email.DoesNotExist:
        logger.warning("notify_critical_email: email %d not found", email_id)
        return

    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.error("notify_critical_email: channel layer not configured")
        return

    group_name = f"user_{email.user_id}"
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "critical_email",
            "email_id": email_id,
            "subject": email.subject,
        },
    )
    logger.info(
        "notify_critical_email: sent to group=%s email_id=%d", group_name, email_id
    )
