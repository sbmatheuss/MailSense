from __future__ import annotations

import logging
import time

from celery import shared_task
from django.db import transaction

from apps.emails.models import Email, EmailClassification
from services.llm_service import BatchParseError, ClassificationResult, LLMService

logger = logging.getLogger(__name__)

BATCH_SIZE = 5


def _exponential_backoff(attempt: int) -> int:
    """Retry delays in seconds: 30s, 60s, 120s."""
    return [30, 60, 120][min(attempt, 2)]


@shared_task(bind=True, max_retries=2)
def classify_email_task(self, email_id: int) -> None:
    """Classifica um e-mail individual via LLMService."""
    try:
        with transaction.atomic():
            email = Email.objects.select_for_update().get(pk=email_id)
            if email.status not in (
                Email.Status.PENDING,
                Email.Status.PROCESSING,
                Email.Status.FAILED,
            ):
                return
            email.status = Email.Status.PROCESSING
            email.save(update_fields=["status"])
    except Email.DoesNotExist:
        logger.warning("classify_email_task: email %d not found", email_id)
        return

    try:
        result = LLMService().classify_email(email.subject, email.body_text)
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.error("classify_email_task: max retries exceeded for email %d", email_id)
            Email.objects.filter(pk=email_id).update(status=Email.Status.FAILED)
            return
        delay = _exponential_backoff(self.request.retries)
        logger.warning(
            "classify_email_task: error for email %d (attempt %d): %s — retrying in %ds",
            email_id, self.request.retries, exc, delay,
        )
        Email.objects.filter(pk=email_id).update(status=Email.Status.PENDING)
        raise self.retry(exc=exc, countdown=delay)

    _persist_classification(email, result)

    if result.priority == "critical":
        from tasks.notifications import notify_critical_email
        notify_critical_email.delay(email_id)


@shared_task
def classify_pending_batch() -> None:
    """Pega até 5 e-mails PENDING e classifica em batch.

    Hybrid strategy (ADR-005):
    - Primary: single API call for all N emails → parse JSON array
    - Fallback: if batch JSON parse fails, dispatch individual tasks per email
    - API errors (rate limit, 5xx) bubble up and Celery retries the whole task
    """
    with transaction.atomic():
        emails = list(
            Email.objects.select_for_update(skip_locked=True)
            .filter(status=Email.Status.PENDING)
            .order_by("received_at")[:BATCH_SIZE]
        )
        if not emails:
            return
        email_ids = [e.pk for e in emails]
        Email.objects.filter(pk__in=email_ids).update(status=Email.Status.PROCESSING)

    email_dicts = [
        {"id": e.pk, "subject": e.subject, "body_text": e.body_text}
        for e in emails
    ]

    try:
        results = LLMService().classify_batch(email_dicts, batch_size=BATCH_SIZE)
    except BatchParseError as exc:
        logger.warning(
            "classify_pending_batch: batch JSON parse failed (%s) — falling back to individual", exc
        )
        _fallback_individual(emails)
        return
    except Exception as exc:
        logger.error("classify_pending_batch: API error: %s — requeueing %d emails", exc, len(emails))
        Email.objects.filter(pk__in=email_ids).update(status=Email.Status.PENDING)
        raise

    for email, result in zip(emails, results):
        _persist_classification(email, result)
        if result.priority == "critical":
            from tasks.notifications import notify_critical_email
            notify_critical_email.delay(email.pk)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _persist_classification(email: Email, result: ClassificationResult) -> None:
    with transaction.atomic():
        EmailClassification.objects.update_or_create(
            email=email,
            defaults={
                "category": result.category,
                "priority": result.priority,
                "sentiment": result.sentiment,
                "confidence_score": result.confidence,
                "summary": result.summary,
                "key_topics": result.key_topics,
                "suggested_reply": result.suggested_reply,
                "urgency_reason": result.urgency_reason,
                "requires_action": result.requires_action,
                "processing_time_ms": result.processing_time_ms,
            },
        )
        email.status = Email.Status.CLASSIFIED
        email.save(update_fields=["status"])


def _fallback_individual(emails: list[Email]) -> None:
    """Dispatch individual tasks for emails still marked PROCESSING.

    Emails remain PROCESSING so classify_pending_batch won't double-pick them.
    Each individual task handles PROCESSING status and takes ownership via SELECT FOR UPDATE.
    """
    for email in emails:
        classify_email_task.delay(email.pk)
    logger.info("classify_pending_batch: dispatched %d individual fallback tasks", len(emails))
