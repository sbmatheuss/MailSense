from celery import shared_task


@shared_task
def notify_critical_email(email_id: int) -> None:
    """Envia notificação via WebSocket (Django Channels) para e-mails críticos."""
    raise NotImplementedError
