from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.emails.models import Email
from services.gmail_service import GmailAuthError, GmailService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_gmail_inbox(self, user_id: int) -> None:
    """Sincroniza inbox do Gmail para um usuário. Disparado via API ou beat."""
    try:
        profile = UserProfile.objects.select_related("user").get(user_id=user_id)
    except UserProfile.DoesNotExist:
        logger.warning("sync_gmail_inbox: profile not found for user %d", user_id)
        return

    if not profile.is_gmail_connected:
        return

    try:
        service = GmailService(profile)
        messages = service.fetch_new_messages(after=profile.last_sync_at)
    except GmailAuthError as exc:
        logger.error("sync_gmail_inbox: auth error for user %d: %s", user_id, exc)
        return
    except Exception as exc:
        logger.warning("sync_gmail_inbox: error for user %d: %s — retrying", user_id, exc)
        raise self.retry(exc=exc)

    created = 0
    for msg in messages:
        gmail_id = msg["gmail_id"]
        msg_fields = {k: v for k, v in msg.items() if k != "gmail_id"}
        _, was_created = Email.objects.get_or_create(
            gmail_id=gmail_id,
            defaults={"user": profile.user, **msg_fields},
        )
        if was_created:
            created += 1

    profile.last_sync_at = timezone.now()
    profile.save(update_fields=["last_sync_at"])

    logger.info("sync_gmail_inbox: user=%d new_emails=%d", user_id, created)


@shared_task
def sync_gmail_inbox_all_users() -> None:
    """Itera sobre usuários com Gmail conectado e despacha sync individual."""
    uid_list = list(
        UserProfile.objects.filter(gmail_sync_enabled=True)
        .exclude(gmail_access_token="")
        .values_list("user_id", flat=True)
    )
    for uid in uid_list:
        sync_gmail_inbox.delay(uid)
    logger.info("sync_gmail_inbox_all_users: dispatched %d sync tasks", len(uid_list))
